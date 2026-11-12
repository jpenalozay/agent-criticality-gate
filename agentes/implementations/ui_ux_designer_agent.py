"""
UI/UX Designer Agent v3.0 - Con Peer Review

Diseña interfaces de usuario completas con wireframes, user flows y accessibility.
"""

import logging
from typing import Dict, Any, Optional
from core.llm_client_v3 import get_llm_client, get_reviewer_llm_client
from core.toon_parser import to_toon, from_toon
from core.sop_validator import SOPValidator
from core.peer_review import PeerReview

logger = logging.getLogger(__name__)


class UIUXDesignerAgent:
    """
    Agente UI/UX Designer con peer review.
    
    Workflow:
    1. Analiza blueprint y requerimiento
    2. Identifica user personas
    3. Diseña user flows
    4. Crea wireframes
    5. Define design tokens
    6. Especifica accessibility (WCAG 2.1 AA)
    7. Peer review valida usabilidad
    """
    
    def __init__(self, enable_peer_review: bool = True):
        """Inicializa agente UI/UX Designer."""
        self.agent_id = "ui_ux_designer"
        self.llm_principal = get_llm_client(self.agent_id)
        self.llm_reviewer = get_reviewer_llm_client(self.agent_id) if enable_peer_review else None
        self.sop_validator = SOPValidator()
        self.peer_review = PeerReview() if enable_peer_review else None
        self.enable_peer_review = enable_peer_review
        
        logger.info(
            f"UI/UX Designer Agent initialized "
            f"(peer_review={'enabled' if enable_peer_review else 'disabled'})"
        )
    
    def process(
        self,
        blueprint: Dict[str, Any],
        requirement: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Procesa blueprint y genera diseño UI/UX completo.
        
        Args:
            blueprint: Blueprint del arquitecto
            requirement: Requerimiento original
            context: Contexto adicional
            
        Returns:
            UI/UX specification completa
        """
        logger.info(f"Processing UI/UX design for: {blueprint.get('name', 'unnamed')}")
        
        # 1. Generar diseño UI/UX
        ui_ux_spec = self._generate_design(blueprint, requirement, context)
        
        # 2. Peer review si está habilitado
        if self.enable_peer_review and self.llm_reviewer:
            ui_ux_spec = self._peer_review_design(ui_ux_spec, blueprint, requirement)
        
        # 3. Validar SOP
        is_valid, errors, score = self.sop_validator.validate_output(
            self.agent_id,
            ui_ux_spec
        )
        
        if not is_valid:
            logger.warning(f"SOP validation failed: {errors}")
        
        ui_ux_spec["sop_compliance_score"] = score
        
        return ui_ux_spec
    
    def _generate_design(
        self,
        blueprint: Dict[str, Any],
        requirement: str,
        context: Optional[Dict]
    ) -> Dict[str, Any]:
        """Genera diseño UI/UX completo."""
        
        system_prompt = """Eres un diseñador UI/UX senior experto.

Tu tarea es diseñar interfaces de usuario completas, accesibles y centradas en el usuario.

Sigue este SOP:
1. Analizar requerimiento y blueprint
2. Identificar user personas
3. Diseñar user flows completos
4. Crear wireframes detallados
5. Definir design tokens (colores, tipografía, espaciado)
6. Especificar accessibility (WCAG 2.1 AA)

Output en formato TOON:
ui_ux_spec
  personas[N]
    persona_id
      name "Nombre"
      role "Rol"
      goals[N] "objetivo"
  user_flows[N]
    flow_id
      name "Nombre del flujo"
      steps[N] "paso"
  wireframes[N]
    screen_id
      name "Nombre pantalla"
      layout "Descripción layout"
      components[N] "componente"
  component_tree
    component_name
      type "button|input|card|etc"
      props "propiedades"
  design_tokens
    colors
      primary "#hex"
      secondary "#hex"
    typography
      font_family "fuente"
      heading_size "tamaño"
    spacing
      unit "8px"
  accessibility
    wcag_level "AA"
    requirements[N] "requerimiento"
"""
        
        user_prompt = f"""Requerimiento: {requirement}

Blueprint técnico:
{to_toon(blueprint)}

{f"Contexto: {context}" if context else ""}

Diseña una interfaz de usuario completa en formato TOON."""
        
        response = self.llm_principal.generate_with_retry(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=4000
        )
        
        try:
            ui_ux_spec = from_toon(response)
            logger.info(f"UI/UX design generated: {len(ui_ux_spec.get('personas', []))} personas")
            return ui_ux_spec
        except Exception as e:
            logger.error(f"Error parsing UI/UX spec: {e}")
            return {
                "personas": [],
                "user_flows": [],
                "wireframes": [],
                "design_tokens": {},
                "accessibility": {},
                "error": str(e)
            }
    
    def _peer_review_design(
        self,
        ui_ux_spec: Dict[str, Any],
        blueprint: Dict[str, Any],
        requirement: str
    ) -> Dict[str, Any]:
        """Realiza peer review del diseño UI/UX."""
        
        logger.info("Starting UI/UX peer review...")
        
        review_prompt = f"""Eres un diseñador UI/UX senior revisando un diseño.

Requerimiento: {requirement}

Blueprint: {to_toon(blueprint)}

Diseño propuesto:
{to_toon(ui_ux_spec)}

Analiza:
1. ¿Los user flows son completos y lógicos?
2. ¿Los wireframes cubren todos los casos de uso?
3. ¿Los design tokens son consistentes?
4. ¿Cumple con WCAG 2.1 AA?
5. ¿Hay problemas de usabilidad?

Proporciona sugerencias de mejora en formato TOON."""
        
        review_response = self.llm_reviewer.generate_with_retry(
            prompt=review_prompt,
            temperature=0.1,
            max_tokens=2000
        )
        
        try:
            review = from_toon(review_response)
        except:
            logger.warning("Failed to parse review, using original design")
            return ui_ux_spec
        
        # Consensus
        approved, merged, score = self.peer_review.review(ui_ux_spec, review)
        
        logger.info(f"Peer review complete: approved={approved}, score={score:.2f}")
        
        if approved:
            return merged
        else:
            ui_ux_spec["peer_review_status"] = "rejected"
            ui_ux_spec["peer_review_score"] = score
            return ui_ux_spec
