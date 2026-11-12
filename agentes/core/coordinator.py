"""
Coordinador Maestro

Orquesta el flujo completo del framework multi-agente.
Gestiona estado, routing y recuperación ante errores.
"""

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from agentes.core.state_manager import get_state_manager, TaskStatus
from agentes.core.event_bus import get_event_bus, EventType
from agentes.core.risk_calculator import RiskLevel
from agentes.implementations.arquitecto_agent import ArquitectoAgent
from agentes.implementations.sentinel_agent import SentinelAgent
from agentes.implementations.coder_agent import CoderAgent
from agentes.implementations.linter_agent import LinterAgent
from agentes.implementations.tester_agent import TesterAgent

logger = logging.getLogger(__name__)


class Coordinator:
    """Coordinador maestro del framework."""
    
    def __init__(self):
        """Inicializa el coordinador."""
        self.state_manager = get_state_manager()
        self.event_bus = get_event_bus()
        
        # Inicializar agentes
        self.arquitecto = ArquitectoAgent()
        self.sentinel = SentinelAgent()
        self.coder = CoderAgent()
        self.linter = LinterAgent()
        self.tester = TesterAgent()
        
        logger.info("Coordinator initialized")
    
    def create_task(self, requirement: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Crea una nueva tarea.
        
        Args:
            requirement: Requerimiento en lenguaje natural
            context: Contexto adicional
            
        Returns:
            Task ID
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        # Crear tarea en state manager
        self.state_manager.create_task(task_id, requirement, context)
        
        # Publicar evento
        self.event_bus.publish_dict(
            EventType.TASK_CREATED,
            task_id=task_id,
            requirement=requirement
        )
        
        logger.info(f"Task created: {task_id}")
        return task_id
    
    def process_task(self, task_id: str) -> Dict[str, Any]:
        """
        Procesa una tarea completa.
        
        Args:
            task_id: ID de la tarea
            
        Returns:
            Resultado final
        """
        logger.info(f"Processing task: {task_id}")
        
        try:
            # Obtener tarea
            task = self.state_manager.get_task(task_id)
            if not task:
                raise ValueError(f"Task not found: {task_id}")
            
            requirement = task["requirement"]
            context = task.get("context", {})
            
            # Actualizar estado
            self.state_manager.update_task(task_id, status=TaskStatus.PROCESSING)
            self.event_bus.publish_dict(EventType.TASK_STARTED, task_id=task_id)
            
            # Fase 1: Arquitecto genera blueprint
            logger.info(f"[{task_id}] Phase 1: Arquitecto")
            self.state_manager.update_task(task_id, current_agent="arquitecto")
            self.event_bus.publish_dict(
                EventType.AGENT_STARTED,
                task_id=task_id,
                agent_id="arquitecto"
            )
            
            blueprint = self.arquitecto.process(requirement, context)
            
            self.state_manager.update_task(task_id, blueprint=blueprint)
            self.event_bus.publish_dict(
                EventType.AGENT_COMPLETED,
                task_id=task_id,
                agent_id="arquitecto",
                blueprint=blueprint
            )
            
            # Fase 2: Sentinel evalúa riesgo
            logger.info(f"[{task_id}] Phase 2: Sentinel")
            self.state_manager.update_task(task_id, current_agent="sentinel")
            self.event_bus.publish_dict(
                EventType.AGENT_STARTED,
                task_id=task_id,
                agent_id="sentinel"
            )
            
            risk_assessment = self.sentinel.process(blueprint)
            risk_score = risk_assessment["total_score"]
            risk_level = risk_assessment["level"]
            decision = risk_assessment["decision"]
            
            self.state_manager.update_task(task_id, risk_score=risk_score)
            self.event_bus.publish_dict(
                EventType.RISK_CALCULATED,
                task_id=task_id,
                agent_id="sentinel",
                risk_score=risk_score,
                risk_level=risk_level,
                decision=decision
            )
            
            # Fase 3: Routing basado en riesgo
            logger.info(f"[{task_id}] Risk score: {risk_score:.2f} ({risk_level}) -> {decision}")
            
            if decision == "human_approval":
                logger.info(f"[{task_id}] Human approval required (risk > 70)")
                self.event_bus.publish_dict(
                    EventType.HUMAN_APPROVAL_REQUESTED,
                    task_id=task_id,
                    risk_score=risk_score
                )
                # En MVP, simular aprobación automática
                logger.info(f"[{task_id}] [MVP] Auto-approving for demonstration")
                self.event_bus.publish_dict(
                    EventType.HUMAN_APPROVAL_RECEIVED,
                    task_id=task_id,
                    approver="mvp_auto",
                    decision="approved"
                )
            
            # Fase 4: Coder genera código
            logger.info(f"[{task_id}] Phase 3: Coder")
            self.state_manager.update_task(task_id, current_agent="coder")
            self.event_bus.publish_dict(
                EventType.AGENT_STARTED,
                task_id=task_id,
                agent_id="coder"
            )
            
            code_artifacts = self.coder.process(blueprint)
            
            self.event_bus.publish_dict(
                EventType.CODE_GENERATED,
                task_id=task_id,
                agent_id="coder",
                files_count=len(code_artifacts.get("files", {}))
            )
            
            # Fase 5: Linter analiza código
            logger.info(f"[{task_id}] Phase 4: Linter")
            self.state_manager.update_task(task_id, current_agent="linter")
            self.event_bus.publish_dict(
                EventType.AGENT_STARTED,
                task_id=task_id,
                agent_id="linter"
            )
            
            linter_report = self.linter.process(code_artifacts)
            
            self.event_bus.publish_dict(
                EventType.CODE_VALIDATED,
                task_id=task_id,
                agent_id="linter",
                quality_score=linter_report["quality_score"],
                issues_count=len(linter_report["issues"])
            )
            
            # Fase 6: Tester genera tests
            logger.info(f"[{task_id}] Phase 5: Tester")
            self.state_manager.update_task(task_id, current_agent="tester")
            self.event_bus.publish_dict(
                EventType.AGENT_STARTED,
                task_id=task_id,
                agent_id="tester"
            )
            
            test_report = self.tester.process(code_artifacts)
            
            # Agregar tests a artifacts
            code_artifacts["files"].update(test_report["test_files"])
            
            self.event_bus.publish_dict(
                EventType.TEST_EXECUTED,
                task_id=task_id,
                agent_id="tester",
                total_tests=test_report["total_tests"],
                coverage=test_report["coverage"]
            )
            
            # Fase 7: Completar tarea
            logger.info(f"[{task_id}] Task completed successfully")
            self.state_manager.update_task(task_id, status=TaskStatus.COMPLETED)
            self.event_bus.publish_dict(EventType.TASK_COMPLETED, task_id=task_id)
            
            # Construir resultado final
            result = {
                "task_id": task_id,
                "status": "completed",
                "requirement": requirement,
                "blueprint": blueprint,
                "risk_assessment": risk_assessment,
                "code_artifacts": code_artifacts,
                "linter_report": linter_report,
                "test_report": test_report,
                "summary": self._generate_summary(
                    task_id, blueprint, risk_assessment, code_artifacts, linter_report, test_report
                )
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            self.state_manager.update_task(task_id, status=TaskStatus.FAILED)
            self.event_bus.publish_dict(
                EventType.TASK_FAILED,
                task_id=task_id,
                error=str(e)
            )
            raise
    
    def _generate_summary(
        self,
        task_id: str,
        blueprint: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        code_artifacts: Dict[str, Any],
        linter_report: Dict[str, Any],
        test_report: Dict[str, Any]
    ) -> str:
        """Genera resumen ejecutivo de la tarea."""
        lines = []
        
        lines.append(f"=== Task Summary: {task_id} ===")
        lines.append("")
        lines.append(f"Blueprint: {blueprint.get('name', 'unnamed')}")
        lines.append(f"  Type: {blueprint.get('type', 'unknown')}")
        lines.append(f"  Components: {len(blueprint.get('components', {}))}")
        lines.append("")
        lines.append(f"Risk Assessment:")
        lines.append(f"  Score: {risk_assessment['total_score']:.2f}/100")
        lines.append(f"  Level: {risk_assessment['level']}")
        lines.append(f"  Decision: {risk_assessment['decision']}")
        lines.append("")
        lines.append(f"Code Generated:")
        lines.append(f"  Files: {len(code_artifacts.get('files', {}))}")
        lines.append(f"  Language: {code_artifacts.get('language', 'unknown')}")
        lines.append("")
        lines.append(f"Quality Analysis:")
        lines.append(f"  Quality Score: {linter_report['quality_score']:.2f}/100")
        lines.append(f"  Issues: {len(linter_report['issues'])}")
        lines.append("")
        lines.append(f"Testing:")
        lines.append(f"  Tests Generated: {test_report['total_tests']}")
        lines.append(f"  Coverage: {test_report['coverage']:.1f}%")
        lines.append("")
        lines.append("Status: ✅ COMPLETED")
        
        return "\n".join(lines)
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de una tarea.
        
        Args:
            task_id: ID de la tarea
            
        Returns:
            Estado de la tarea
        """
        return self.state_manager.get_task(task_id)
    
    def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 10) -> list:
        """
        Lista tareas.
        
        Args:
            status: Filtrar por estado
            limit: Límite de resultados
            
        Returns:
            Lista de tareas
        """
        return self.state_manager.list_tasks(status, limit)
