"""
State Manager

Gestión de estado persistente con SQLite.
Soporta event sourcing, checkpointing y recuperación ante fallos.
"""

import sqlite3
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Estados posibles de una tarea."""
    PENDING = "pending"
    PROCESSING = "processing"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"


class StateManager:
    """Gestor de estado del framework."""
    
    def __init__(self, db_path: str = "./data/framework.db"):
        """
        Inicializa el state manager.
        
        Args:
            db_path: Ruta a la base de datos SQLite
        """
        self.db_path = db_path
        
        # Crear directorio si no existe
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Inicializar base de datos
        self._init_database()
        
        logger.info(f"State manager initialized: {db_path}")
    
    def _init_database(self):
        """Inicializa el schema de la base de datos."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabla de tareas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    current_agent TEXT,
                    risk_score REAL,
                    requirement TEXT,
                    blueprint TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    context TEXT
                )
            """)
            
            # Tabla de eventos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    agent_id TEXT,
                    data TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            """)
            
            # Tabla de auditoría
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    agent_id TEXT,
                    action TEXT NOT NULL,
                    risk_score REAL,
                    decision TEXT,
                    input_hash TEXT,
                    output_hash TEXT,
                    metadata TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            """)
            
            # Tabla de decisiones humanas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS human_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    approver_id TEXT,
                    approver_role TEXT,
                    decision TEXT NOT NULL,
                    comments TEXT,
                    override_risk BOOLEAN,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            """)
            
            # Índices
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_log(task_id)")
            
            conn.commit()
            logger.debug("Database schema initialized")
    
    def create_task(
        self,
        task_id: str,
        requirement: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crea una nueva tarea.
        
        Args:
            task_id: ID único de la tarea
            requirement: Requerimiento en lenguaje natural
            context: Contexto adicional
            
        Returns:
            Dict con datos de la tarea creada
        """
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (
                    task_id, status, requirement, created_at, updated_at, context
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                TaskStatus.PENDING.value,
                requirement,
                now,
                now,
                json.dumps(context or {})
            ))
            conn.commit()
        
        logger.info(f"Task created: {task_id}")
        return self.get_task(task_id)
    
    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        current_agent: Optional[str] = None,
        risk_score: Optional[float] = None,
        blueprint: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Actualiza una tarea existente.
        
        Args:
            task_id: ID de la tarea
            status: Nuevo estado (opcional)
            current_agent: Agente actual (opcional)
            risk_score: Score de riesgo (opcional)
            blueprint: Blueprint generado (opcional)
            context: Contexto actualizado (opcional)
        """
        updates = []
        values = []
        
        if status:
            updates.append("status = ?")
            values.append(status.value)
        
        if current_agent is not None:
            updates.append("current_agent = ?")
            values.append(current_agent)
        
        if risk_score is not None:
            updates.append("risk_score = ?")
            values.append(risk_score)
        
        if blueprint is not None:
            updates.append("blueprint = ?")
            values.append(json.dumps(blueprint))
        
        if context is not None:
            updates.append("context = ?")
            values.append(json.dumps(context))
        
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        
        if status == TaskStatus.COMPLETED or status == TaskStatus.FAILED:
            updates.append("completed_at = ?")
            values.append(datetime.now().isoformat())
        
        values.append(task_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        logger.debug(f"Task updated: {task_id}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una tarea por ID.
        
        Args:
            task_id: ID de la tarea
            
        Returns:
            Dict con datos de la tarea o None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            
            if row:
                task = dict(row)
                # Parsear JSON
                if task.get("blueprint"):
                    task["blueprint"] = json.loads(task["blueprint"])
                if task.get("context"):
                    task["context"] = json.loads(task["context"])
                return task
            
            return None
    
    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Lista tareas con filtros opcionales.
        
        Args:
            status: Filtrar por estado (opcional)
            limit: Número máximo de resultados
            
        Returns:
            Lista de tareas
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if status:
                cursor.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status.value, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            
            tasks = []
            for row in cursor.fetchall():
                task = dict(row)
                if task.get("blueprint"):
                    task["blueprint"] = json.loads(task["blueprint"])
                if task.get("context"):
                    task["context"] = json.loads(task["context"])
                tasks.append(task)
            
            return tasks
    
    def add_event(
        self,
        task_id: str,
        event_type: str,
        agent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Agrega un evento al log.
        
        Args:
            task_id: ID de la tarea
            event_type: Tipo de evento
            agent_id: ID del agente (opcional)
            data: Datos del evento (opcional)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (task_id, event_type, agent_id, data, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                task_id,
                event_type,
                agent_id,
                json.dumps(data or {}),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def get_events(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene eventos de una tarea.
        
        Args:
            task_id: ID de la tarea
            
        Returns:
            Lista de eventos
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM events WHERE task_id = ? ORDER BY timestamp ASC",
                (task_id,)
            )
            
            events = []
            for row in cursor.fetchall():
                event = dict(row)
                if event.get("data"):
                    event["data"] = json.loads(event["data"])
                events.append(event)
            
            return events
    
    def add_audit_log(
        self,
        task_id: str,
        agent_id: str,
        action: str,
        risk_score: Optional[float] = None,
        decision: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Agrega entrada al log de auditoría.
        
        Args:
            task_id: ID de la tarea
            agent_id: ID del agente
            action: Acción realizada
            risk_score: Score de riesgo (opcional)
            decision: Decisión tomada (opcional)
            metadata: Metadatos adicionales (opcional)
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_log (
                    task_id, agent_id, action, risk_score, decision, metadata, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                agent_id,
                action,
                risk_score,
                decision,
                json.dumps(metadata or {}),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def get_audit_log(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene log de auditoría de una tarea.
        
        Args:
            task_id: ID de la tarea
            
        Returns:
            Lista de entradas de auditoría
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM audit_log WHERE task_id = ? ORDER BY timestamp ASC",
                (task_id,)
            )
            
            logs = []
            for row in cursor.fetchall():
                log = dict(row)
                if log.get("metadata"):
                    log["metadata"] = json.loads(log["metadata"])
                logs.append(log)
            
            return logs


# Singleton global
_global_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Obtiene el state manager global (singleton)."""
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = StateManager()
    return _global_state_manager


def set_state_manager(manager: StateManager):
    """Establece el state manager global."""
    global _global_state_manager
    _global_state_manager = manager
