"""
Auditor Agent - Mecánico

Registro inmutable de todas las decisiones del framework.
NO usa LLM - logging mecánico.
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditorAgent:
    """
    Agente Auditor (mecánico).
    
    Workflow:
    1. Recibe evento de cualquier agente
    2. Genera entrada de auditoría
    3. Calcula checksum SHA-256
    4. Append a log inmutable
    
    Características:
    - Append-only (no se puede modificar)
    - Checksummed (integridad verificable)
    - Inmutable (registro permanente)
    
    NO USA LLM - Logging mecánico
    """
    
    def __init__(self, log_file: str = "data/audit_log.jsonl"):
        """
        Inicializa Auditor.
        
        Args:
            log_file: Ruta al archivo de log
        """
        self.agent_id = "auditor"
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Crear archivo si no existe
        if not self.log_file.exists():
            self.log_file.touch()
        
        logger.info(f"Auditor Agent initialized (log: {log_file})")
    
    def log_event(
        self,
        actor: str,
        action: str,
        resource: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Registra un evento en el audit log.
        
        Args:
            actor: Agente que realizó la acción
            action: Acción realizada
            resource: Recurso afectado
            details: Detalles adicionales
            
        Returns:
            Entrada de auditoría
        """
        # Generar ID único
        timestamp = datetime.utcnow().isoformat()
        entry_id = self._generate_id(actor, action, timestamp)
        
        # Crear entrada
        entry = {
            "id": entry_id,
            "timestamp": timestamp,
            "actor": actor,
            "action": action,
            "resource": resource,
            "details": details
        }
        
        # Calcular checksum
        entry["checksum"] = self._calculate_checksum(entry)
        
        # Append a log
        self._append_to_log(entry)
        
        logger.debug(f"Audit event logged: {actor}.{action} on {resource}")
        
        return entry
    
    def get_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtiene últimas entradas del log.
        
        Args:
            limit: Número máximo de entradas
            
        Returns:
            Lista de entradas
        """
        entries = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception as e:
            logger.error(f"Error reading audit log: {e}")
        
        return entries
    
    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verifica integridad del audit log.
        
        Returns:
            Resultado de verificación
        """
        total = 0
        valid = 0
        invalid = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    
                    total += 1
                    try:
                        entry = json.loads(line)
                        stored_checksum = entry.pop("checksum", None)
                        calculated_checksum = self._calculate_checksum(entry)
                        
                        if stored_checksum == calculated_checksum:
                            valid += 1
                        else:
                            invalid.append({
                                "line": line_num,
                                "id": entry.get("id"),
                                "reason": "Checksum mismatch"
                            })
                    except json.JSONDecodeError:
                        invalid.append({
                            "line": line_num,
                            "reason": "Invalid JSON"
                        })
        except Exception as e:
            logger.error(f"Error verifying audit log: {e}")
            return {
                "total": 0,
                "valid": 0,
                "invalid": 0,
                "errors": [str(e)]
            }
        
        return {
            "total": total,
            "valid": valid,
            "invalid": len(invalid),
            "integrity": valid / total if total > 0 else 0.0,
            "invalid_entries": invalid[:10]  # Limitar a 10
        }
    
    def _generate_id(self, actor: str, action: str, timestamp: str) -> str:
        """Genera ID único para entrada."""
        data = f"{actor}:{action}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _calculate_checksum(self, entry: Dict[str, Any]) -> str:
        """Calcula checksum SHA-256 de una entrada."""
        # Crear copia sin checksum
        entry_copy = {k: v for k, v in entry.items() if k != "checksum"}
        
        # Serializar de forma determinística
        data = json.dumps(entry_copy, sort_keys=True)
        
        # Calcular hash
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _append_to_log(self, entry: Dict[str, Any]):
        """Append entrada al log (append-only)."""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Error writing to audit log: {e}")
            raise
    
    def process(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Procesa múltiples eventos.
        
        Args:
            events: Lista de eventos a registrar
            
        Returns:
            Resumen de auditoría
        """
        logged = 0
        
        for event in events:
            try:
                self.log_event(
                    actor=event.get("actor", "unknown"),
                    action=event.get("action", "unknown"),
                    resource=event.get("resource", "unknown"),
                    details=event.get("details", {})
                )
                logged += 1
            except Exception as e:
                logger.error(f"Error logging event: {e}")
        
        # Verificar integridad
        integrity = self.verify_integrity()
        
        return {
            "events_logged": logged,
            "total_events": integrity["total"],
            "integrity": integrity["integrity"],
            "log_file": str(self.log_file)
        }
