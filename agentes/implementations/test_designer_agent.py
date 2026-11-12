"""
Test Designer Agent v3.0 - Independiente

Genera tests SIN ver el código (elimina sesgo).
Basado en AgentCoder paper.
"""

import logging
from typing import Dict, Any, Optional
from core.llm_client_v3 import get_llm_client, get_reviewer_llm_client
from core.toon_parser import to_toon, from_toon
from core.sop_validator import SOPValidator
from core.peer_review import PeerReview

logger = logging.getLogger(__name__)


class TestDesignerAgent:
    """
    Agente Test Designer independiente con peer review.
    
    Workflow (AgentCoder):
    1. Analiza SOLO el requerimiento y blueprint (NO el código)
    2. Genera tests básicos
    3. Genera edge cases
    4. Genera large-scale tests
    5. Peer review valida completitud
    
    Principio clave: NUNCA ver el código antes de crear tests
    """
    
    def __init__(self, enable_peer_review: bool = True):
        """Inicializa agente Test Designer."""
        self.agent_id = "test_designer"
        self.llm_principal = get_llm_client(self.agent_id)
        self.llm_reviewer = get_reviewer_llm_client(self.agent_id) if enable_peer_review else None
        self.sop_validator = SOPValidator()
        self.peer_review = PeerReview() if enable_peer_review else None
        self.enable_peer_review = enable_peer_review
        
        logger.info(
            f"Test Designer Agent initialized "
            f"(peer_review={'enabled' if enable_peer_review else 'disabled'})"
        )
    
    def process(
        self,
        blueprint: Dict[str, Any],
        requirement: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Procesa blueprint y genera tests (SIN ver código).
        
        Args:
            blueprint: Blueprint del arquitecto
            requirement: Requerimiento original
            context: Contexto adicional
            
        Returns:
            Test suite completa
        """
        logger.info(f"Generating tests for: {blueprint.get('name', 'unnamed')}")
        
        # 1. Generar tests (independiente del código)
        test_suite = self._generate_tests(blueprint, requirement, context)
        
        # 2. Peer review si está habilitado
        if self.enable_peer_review and self.llm_reviewer:
            test_suite = self._peer_review_tests(test_suite, blueprint, requirement)
        
        # 3. Validar SOP
        is_valid, errors, score = self.sop_validator.validate_output(
            self.agent_id,
            test_suite
        )
        
        if not is_valid:
            logger.warning(f"SOP validation failed: {errors}")
        
        test_suite["sop_compliance_score"] = score
        
        return test_suite
    
    def _generate_tests(
        self,
        blueprint: Dict[str, Any],
        requirement: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Genera tests basados SOLO en requerimiento y blueprint."""
        
        system_prompt = """Eres un ingeniero de testing senior experto.

Tu tarea es diseñar tests completos basándote SOLO en el requerimiento y blueprint.

REGLA CRÍTICA: NUNCA veas el código implementado antes de crear los tests.
Esto elimina el sesgo y asegura tests independientes.

Sigue este SOP:
1. Analizar requerimiento (NO código)
2. Generar basic test cases (casos normales)
3. Generar edge case tests (límites, valores nulos, errores)
4. Generar large-scale tests (carga, concurrencia)
5. Estimar coverage esperado

Categorías de tests:
- basic: Casos de uso normales
- edge_cases: Límites, valores especiales, errores
- large_scale: Performance, carga, concurrencia

Output en formato TOON:
test_suite
  test_files
    "test_file.py" "contenido del test"
  total_tests N
  categories
    basic N
    edge_cases N
    large_scale N
  expected_coverage 0.XX
"""
        
        user_prompt = f"""Requerimiento: {requirement}

Blueprint:
{to_toon(blueprint)}

{f"Contexto: {context}" if context else ""}

IMPORTANTE: Genera tests basándote SOLO en el requerimiento y blueprint.
NO asumas implementación específica.

Output en formato TOON."""
        
        response = self.llm_principal.generate_with_retry(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=4000
        )
        
        try:
            test_suite = from_toon(response)
            logger.info(
                f"Tests generated: {test_suite.get('total_tests', 0)} tests, "
                f"coverage: {test_suite.get('expected_coverage', 0):.0%}"
            )
            return test_suite
        except Exception as e:
            logger.error(f"Error parsing test suite: {e}")
            return {
                "test_files": {},
                "total_tests": 0,
                "categories": {"basic": 0, "edge_cases": 0, "large_scale": 0},
                "expected_coverage": 0.0,
                "error": str(e)
            }
    
    def _peer_review_tests(
        self,
        test_suite: Dict[str, Any],
        blueprint: Dict[str, Any],
        requirement: str
    ) -> Dict[str, Any]:
        """Realiza peer review de los tests."""
        
        logger.info("Starting test peer review...")
        
        review_prompt = f"""Eres un ingeniero de testing senior revisando una test suite.

Requerimiento: {requirement}

Blueprint: {to_toon(blueprint)}

Tests propuestos:
{to_toon(test_suite)}

Analiza:
1. ¿Están todos los casos de uso cubiertos?
2. ¿Hay edge cases faltantes?
3. ¿Los tests son independientes del código?
4. ¿El coverage esperado es realista?
5. ¿Hay tests redundantes?

Proporciona sugerencias en formato TOON."""
        
        review_response = self.llm_reviewer.generate_with_retry(
            prompt=review_prompt,
            temperature=0.1,
            max_tokens=2000
        )
        
        try:
            review = from_toon(review_response)
        except:
            logger.warning("Failed to parse review, using original tests")
            return test_suite
        
        # Consensus
        approved, merged, score = self.peer_review.review(test_suite, review)
        
        logger.info(f"Peer review complete: approved={approved}, score={score:.2f}")
        
        if approved:
            return merged
        else:
            test_suite["peer_review_status"] = "rejected"
            test_suite["peer_review_score"] = score
            return test_suite
