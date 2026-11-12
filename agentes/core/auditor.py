"""
Auditor

Registra todas las decisiones, cambios y aprobaciones del sistema.
Proporciona trazabilidad completa y métricas de compliance.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from agentes.core.state_manager import get_state_manager

logger = logging.getLogger(__name__)


class Auditor:
    """Auditor del framework."""
    
    def __init__(self):
        """Inicializa el auditor."""
        self.state_manager = get_state_manager()
        self.agent_id = "auditor"
    
    def log_decision(
        self,
        task_id: str,
        agent_id: str,
        action: str,
        risk_score: Optional[float] = None,
        decision: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Registra una decisión en el log de auditoría.
        
        Args:
            task_id: ID de la tarea
            agent_id: ID del agente que tomó la decisión
            action: Acción realizada
            risk_score: Score de riesgo (opcional)
            decision: Decisión tomada (opcional)
            metadata: Metadatos adicionales (opcional)
        """
        self.state_manager.add_audit_log(
            task_id=task_id,
            agent_id=agent_id,
            action=action,
            risk_score=risk_score,
            decision=decision,
            metadata=metadata
        )
        
        logger.info(f"Audit log: {task_id} - {agent_id} - {action}")
    
    def get_audit_trail(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene el trail de auditoría completo de una tarea.
        
        Args:
            task_id: ID de la tarea
            
        Returns:
            Lista de entradas de auditoría
        """
        return self.state_manager.get_audit_log(task_id)
    
    def generate_report(self, task_id: str) -> str:
        """
        Genera un reporte de auditoría para una tarea.
        
        Args:
            task_id: ID de la tarea
            
        Returns:
            Reporte en formato texto
        """
        task = self.state_manager.get_task(task_id)
        audit_log = self.get_audit_trail(task_id)
        events = self.state_manager.get_events(task_id)
        
        lines = []
        lines.append("=" * 70)
        lines.append(f"AUDIT REPORT - Task: {task_id}")
        lines.append("=" * 70)
        lines.append("")
        
        if task:
            lines.append(f"Created: {task['created_at']}")
            lines.append(f"Status: {task['status']}")
            lines.append(f"Risk Score: {task.get('risk_score', 'N/A')}")
            lines.append("")
        
        lines.append(f"Total Events: {len(events)}")
        lines.append(f"Total Audit Entries: {len(audit_log)}")
        lines.append("")
        
        if audit_log:
            lines.append("Audit Trail:")
            lines.append("-" * 70)
            for entry in audit_log:
                lines.append(f"[{entry['timestamp']}] {entry['agent_id']}: {entry['action']}")
                if entry.get('decision'):
                    lines.append(f"  Decision: {entry['decision']}")
                if entry.get('risk_score'):
                    lines.append(f"  Risk Score: {entry['risk_score']}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# Singleton global
_global_auditor: Optional[Auditor] = None


def get_auditor() -> Auditor:
    """Obtiene el auditor global (singleton)."""
    global _global_auditor
    if _global_auditor is None:
        _global_auditor = Auditor()
    return _global_auditor
