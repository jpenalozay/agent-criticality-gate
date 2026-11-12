"""
Coordinator v3 - Orquestador Principal

Coordina el flujo completo de todos los agentes.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Importar todos los agentes
from implementations.arquitecto_agent_v3 import ArquitectoAgentV3
from implementations.ui_ux_designer_agent import UIUXDesignerAgent
from implementations.sentinel_agent_v3 import SentinelAgent
from implementations.coder_agent_v3 import CoderAgentV3
from implementations.test_designer_agent import TestDesignerAgent
from implementations.test_executor import TestExecutorAgent
from implementations.linter_agent import LinterAgent
from implementations.auditor_agent import AuditorAgent

logger = logging.getLogger(__name__)


class CoordinatorV3:
    """
    Coordinador v3.0 - Orquestador principal del framework.
    
    Workflow completo:
    1. Recibe requerimiento del usuario
    2. Arquitecto genera blueprint
    3. UI/UX Designer diseña interfaz
    4. Sentinel evalúa riesgo
    5. Coder genera código (con executable feedback si riesgo es bajo/medio)
    6. Test Designer genera tests
    7. Test Executor ejecuta tests
    8. Linter analiza calidad
    9. Auditor registra todo
    10. Retorna resultado completo
    """
    
    def __init__(
        self,
        enable_peer_review: bool = True,
        enable_executable_feedback: bool = True
    ):
        """
        Inicializa Coordinator.
        
        Args:
            enable_peer_review: Habilitar peer review en agentes críticos
            enable_executable_feedback: Habilitar executable feedback en Coder
        """
        self.coordinator_id = "coordinator_v3"
        
        # Inicializar agentes
        logger.info("Initializing all agents...")
        
        self.arquitecto = ArquitectoAgentV3(enable_peer_review=enable_peer_review)
        self.ui_ux_designer = UIUXDesignerAgent(enable_peer_review=enable_peer_review)
        self.sentinel = SentinelAgent()
        self.coder = CoderAgentV3(enable_executable_feedback=enable_executable_feedback)
        self.test_designer = TestDesignerAgent(enable_peer_review=enable_peer_review)
        self.test_executor = TestExecutorAgent()
        self.linter = LinterAgent()
        self.auditor = AuditorAgent()
        
        self.enable_peer_review = enable_peer_review
        self.enable_executable_feedback = enable_executable_feedback
        
        logger.info(
            f"Coordinator v3.0 initialized "
            f"(peer_review={enable_peer_review}, "
            f"executable_feedback={enable_executable_feedback})"
        )
    
    def process(self, requirement: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Procesa requerimiento completo a través de todos los agentes.
        
        Args:
            requirement: Requerimiento del usuario
            context: Contexto adicional
            
        Returns:
            Resultado completo con outputs de todos los agentes
        """
        start_time = datetime.utcnow()
        task_id = self._generate_task_id(requirement)
        
        logger.info(f"Processing task {task_id}: {requirement[:50]}...")
        
        # Eventos para auditoría
        events = []
        
        try:
            # 1. ARQUITECTO
            logger.info("[1/8] Running Arquitecto...")
            blueprint = self.arquitecto.process(requirement, context)
            events.append({
                "actor": "arquitecto",
                "action": "blueprint_generated",
                "resource": task_id,
                "details": {
                    "name": blueprint.get('name', 'unnamed'),
                    "components": len(blueprint.get('components', {})),
                    "sop_score": blueprint.get('sop_compliance_score', 0)
                }
            })
            
            # 2. UI/UX DESIGNER
            logger.info("[2/8] Running UI/UX Designer...")
            ui_ux_spec = self.ui_ux_designer.process(blueprint, requirement, context)
            events.append({
                "actor": "ui_ux_designer",
                "action": "ui_design_generated",
                "resource": task_id,
                "details": {
                    "personas": len(ui_ux_spec.get('personas', [])),
                    "wireframes": len(ui_ux_spec.get('wireframes', [])),
                    "sop_score": ui_ux_spec.get('sop_compliance_score', 0)
                }
            })
            
            # 3. SENTINEL
            logger.info("[3/8] Running Sentinel...")
            risk_assessment = self.sentinel.process(blueprint)
            events.append({
                "actor": "sentinel",
                "action": "risk_assessed",
                "resource": task_id,
                "details": {
                    "score": risk_assessment.get('total_score', 0),
                    "level": risk_assessment.get('level', 'UNKNOWN'),
                    "decision": risk_assessment.get('decision', 'unknown')
                }
            })
            
            # 4. CODER
            logger.info("[4/8] Running Coder...")
            code_artifacts = self.coder.process(blueprint, risk_assessment)
            events.append({
                "actor": "coder",
                "action": "code_generated",
                "resource": task_id,
                "details": {
                    "files": len(code_artifacts.get('files', {})),
                    "language": code_artifacts.get('language', 'unknown'),
                    "sop_score": code_artifacts.get('sop_compliance_score', 0)
                }
            })
            
            # 5. TEST DESIGNER
            logger.info("[5/8] Running Test Designer...")
            test_suite = self.test_designer.process(blueprint, requirement, context)
            events.append({
                "actor": "test_designer",
                "action": "tests_designed",
                "resource": task_id,
                "details": {
                    "total_tests": test_suite.get('total_tests', 0),
                    "expected_coverage": test_suite.get('expected_coverage', 0),
                    "sop_score": test_suite.get('sop_compliance_score', 0)
                }
            })
            
            # 6. TEST EXECUTOR
            logger.info("[6/8] Running Test Executor...")
            test_results = self.test_executor.process(code_artifacts, test_suite)
            events.append({
                "actor": "test_executor",
                "action": "tests_executed",
                "resource": task_id,
                "details": {
                    "total": test_results.get('total_tests', 0),
                    "passed": test_results.get('passed', 0),
                    "failed": test_results.get('failed', 0),
                    "coverage": test_results.get('coverage', 0)
                }
            })
            
            # 7. LINTER
            logger.info("[7/8] Running Linter...")
            lint_results = self.linter.process(code_artifacts)
            events.append({
                "actor": "linter",
                "action": "code_linted",
                "resource": task_id,
                "details": {
                    "quality_score": lint_results.get('quality_score', 0),
                    "issues": len(lint_results.get('issues', []))
                }
            })
            
            # 8. AUDITOR
            logger.info("[8/8] Running Auditor...")
            audit_summary = self.auditor.process(events)
            
            # Calcular tiempo total
            end_time = datetime.utcnow()
            total_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Compilar resultado final
            result = {
                "task_id": task_id,
                "requirement": requirement,
                "status": "completed",
                "total_time_ms": total_time_ms,
                "agents": {
                    "arquitecto": blueprint,
                    "ui_ux_designer": ui_ux_spec,
                    "sentinel": risk_assessment,
                    "coder": code_artifacts,
                    "test_designer": test_suite,
                    "test_executor": test_results,
                    "linter": lint_results,
                    "auditor": audit_summary
                },
                "summary": self._generate_summary(
                    blueprint, ui_ux_spec, risk_assessment,
                    code_artifacts, test_suite, test_results,
                    lint_results, audit_summary
                )
            }
            
            logger.info(
                f"Task {task_id} completed in {total_time_ms}ms "
                f"(Quality: {lint_results.get('quality_score', 0):.1f}/100, "
                f"Tests: {test_results.get('passed', 0)}/{test_results.get('total_tests', 0)})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            
            # Log error event
            events.append({
                "actor": "coordinator",
                "action": "task_failed",
                "resource": task_id,
                "details": {"error": str(e)}
            })
            self.auditor.process(events)
            
            return {
                "task_id": task_id,
                "requirement": requirement,
                "status": "failed",
                "error": str(e),
                "agents": {},
                "summary": {}
            }
    
    def _generate_task_id(self, requirement: str) -> str:
        """Genera ID único para la tarea."""
        import hashlib
        timestamp = datetime.utcnow().isoformat()
        data = f"{requirement}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:12]
    
    def _generate_summary(
        self,
        blueprint: Dict,
        ui_ux_spec: Dict,
        risk_assessment: Dict,
        code_artifacts: Dict,
        test_suite: Dict,
        test_results: Dict,
        lint_results: Dict,
        audit_summary: Dict
    ) -> Dict[str, Any]:
        """Genera resumen ejecutivo del resultado."""
        return {
            "architecture": {
                "name": blueprint.get('name', 'unnamed'),
                "components": len(blueprint.get('components', {})),
                "sop_compliance": blueprint.get('sop_compliance_score', 0)
            },
            "ui_ux": {
                "personas": len(ui_ux_spec.get('personas', [])),
                "wireframes": len(ui_ux_spec.get('wireframes', [])),
                "accessibility": ui_ux_spec.get('accessibility', {}).get('wcag_level', 'N/A')
            },
            "risk": {
                "score": risk_assessment.get('total_score', 0),
                "level": risk_assessment.get('level', 'UNKNOWN'),
                "decision": risk_assessment.get('decision', 'unknown')
            },
            "code": {
                "files": len(code_artifacts.get('files', {})),
                "language": code_artifacts.get('language', 'unknown')
            },
            "testing": {
                "tests_designed": test_suite.get('total_tests', 0),
                "tests_passed": test_results.get('passed', 0),
                "tests_failed": test_results.get('failed', 0),
                "coverage": test_results.get('coverage', 0)
            },
            "quality": {
                "score": lint_results.get('quality_score', 0),
                "issues": len(lint_results.get('issues', []))
            },
            "audit": {
                "events_logged": audit_summary.get('events_logged', 0),
                "integrity": audit_summary.get('integrity', 0)
            }
        }
