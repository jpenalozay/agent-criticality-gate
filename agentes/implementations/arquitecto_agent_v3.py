"""
Arquitecto Agent v3.0 - Con Peer Review

Genera blueprints técnicos con validación cruzada de otro LLM.
"""

import logging
from typing import Dict, Any, Optional
from core.llm_client_v3 import get_llm_client, get_reviewer_llm_client
from core.toon_parser import to_toon, from_toon
from core.sop_validator import SOPValidator
from core.peer_review import PeerReview

logger = logging.getLogger(__name__)


class ArquitectoAgentV3:
    """
    Agente Arquitecto con peer review.
    
    Workflow:
    1. Arquitecto principal genera blueprint
    2. Reviewer revisa y sugiere mejoras
    3. Consensus mechanism decide si aprobar
    4. Retorna blueprint validado
    """
    
    def __init__(self, enable_peer_review: bool = True):
        """
        Inicializa agente arquitecto.
        
        Args:
            enable_peer_review: Habilitar peer review
        """
        self.agent_id = "arquitecto"
        self.llm_principal = get_llm_client(self.agent_id)
        self.llm_reviewer = get_reviewer_llm_client(self.agent_id) if enable_peer_review else None
        self.sop_validator = SOPValidator()
        self.peer_review = PeerReview() if enable_peer_review else None
        self.enable_peer_review = enable_peer_review
        
        logger.info(
            f"Arquitecto Agent v3.0 initialized "
            f"(peer_review={'enabled' if enable_peer_review else 'disabled'})"
        )
    
    def process(self, requirement: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Procesa requerimiento y genera blueprint.
        
        Args:
            requirement: Requerimiento del usuario
            context: Contexto adicional
            
        Returns:
            Blueprint validado
        """
        logger.info(f"Processing requirement: {requirement[:100]}...")
        
        # 1. Generar blueprint con arquitecto principal
        blueprint_principal = self._generate_blueprint(requirement, context)
        
        # 2. Si peer review está habilitado, revisar
        if self.enable_peer_review and self.llm_reviewer:
            blueprint_final = self._peer_review_blueprint(
                blueprint_principal,
                requirement,
                context
            )
        else:
            blueprint_final = blueprint_principal
        
        # 3. Validar SOP
        is_valid, errors, score = self.sop_validator.validate_output(
            self.agent_id,
            blueprint_final
        )
        
        if not is_valid:
            logger.warning(f"SOP validation failed: {errors}")
        
        blueprint_final["sop_compliance_score"] = score
        
        return blueprint_final
    
    def _generate_blueprint(
        self,
        requirement: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Genera blueprint con arquitecto principal."""
        
        system_prompt = """Eres un arquitecto de software senior experto.

Tu tarea es analizar requerimientos y generar blueprints técnicos estructurados.

Sigue este SOP:
1. Analizar requerimiento
2. Identificar componentes del sistema
3. Definir tecnologías apropiadas
4. Mapear dependencias entre componentes
5. Especificar consideraciones de seguridad

Output en formato TOON:
blueprint#nombre:tipo
  description "..."
  components
    component_name
      type backend|frontend|database|service
      tech tecnologia
      criticality LOW|MEDIUM|HIGH
      description "..."
  dependencies[N]
    from component_a
    to component_b
    type uses|depends_on|calls
  data[N]
    "tipo_de_dato"
  security[N]
    "consideracion_de_seguridad"
"""
        
        user_prompt = f"""Requerimiento: {requirement}

{f"Contexto adicional: {context}" if context else ""}

Genera un blueprint técnico completo en formato TOON."""
        
        response = self.llm_principal.generate_with_retry(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=4000
        )
        
        # Parsear TOON a dict
        try:
            blueprint = from_toon(response)
            logger.info(f"Blueprint generated: {blueprint.get('name', 'unnamed')}")
            return blueprint
        except Exception as e:
            logger.error(f"Error parsing blueprint: {e}")
            # Fallback: retornar estructura mínima
            return {
                "name": "error_blueprint",
                "type": "unknown",
                "components": {},
                "error": str(e)
            }
    
    def _peer_review_blueprint(
        self,
        blueprint: Dict[str, Any],
        requirement: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Realiza peer review del blueprint."""
        
        logger.info("Starting peer review...")
        
        # Generar review con segundo LLM
        review_prompt = f"""Eres un arquitecto senior revisando un blueprint técnico.

Requerimiento original: {requirement}

Blueprint propuesto:
{to_toon(blueprint)}

Analiza el blueprint y proporciona:
1. ¿Está completo? ¿Faltan componentes?
2. ¿Las tecnologías son apropiadas?
3. ¿Las dependencias están bien mapeadas?
4. ¿Hay consideraciones de seguridad faltantes?
5. Sugerencias de mejora

Output en formato TOON con tus sugerencias."""
        
        review_response = self.llm_reviewer.generate_with_retry(
            prompt=review_prompt,
            temperature=0.1,
            max_tokens=2000
        )
        
        try:
            review = from_toon(review_response)
        except:
            # Si falla el parsing, aprobar blueprint original
            logger.warning("Failed to parse review, using original blueprint")
            return blueprint
        
        # Consensus mechanism
        approved, merged, score = self.peer_review.review(blueprint, review)
        
        logger.info(f"Peer review complete: approved={approved}, score={score:.2f}")
        
        if approved:
            return merged
        else:
            # Si no se aprueba, retornar original con nota
            blueprint["peer_review_status"] = "rejected"
            blueprint["peer_review_score"] = score
            return blueprint
    
    def to_toon(self, blueprint: Dict[str, Any]) -> str:
        """Convierte blueprint a formato TOON."""
        return to_toon(blueprint)
