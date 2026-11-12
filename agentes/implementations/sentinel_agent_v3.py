"""
Sentinel Agent v3.0 - Risk Assessment

Evalúa riesgo de blueprints usando 3D Risk Scoring.
"""

import logging
from typing import Dict, Any, List
from core.llm_client_v3 import get_llm_client
from core.toon_parser import to_toon, from_toon
from core.sop_validator import SOPValidator

logger = logging.getLogger(__name__)


class SentinelAgent:
    """
    Agente Sentinel para evaluación de riesgo.
    
    Workflow:
    1. Analiza blueprint
    2. Calcula 3D Risk Score:
       - Impact (40%): Impacto en sistema
       - Complexity (30%): Complejidad técnica
       - Sensitivity (30%): Datos sensibles
    3. Determina nivel de riesgo (LOW/MEDIUM/HIGH)
    4. Decide routing (auto_approve/peer_review/human_approval)
    """
    
    def __init__(self):
        """Inicializa agente Sentinel."""
        self.agent_id = "sentinel"
        self.llm = get_llm_client(self.agent_id)
        self.sop_validator = SOPValidator()
        
        # Thresholds
        self.low_threshold = 40
        self.high_threshold = 70
        
        logger.info("Sentinel Agent initialized")
    
    def process(self, blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa riesgo del blueprint.
        
        Args:
            blueprint: Blueprint del arquitecto
            
        Returns:
            Risk assessment con score y decisión
        """
        logger.info(f"Assessing risk for: {blueprint.get('name', 'unnamed')}")
        
        # 1. Calcular risk score
        risk_assessment = self._calculate_risk(blueprint)
        
        # 2. Validar SOP
        is_valid, errors, score = self.sop_validator.validate_output(
            self.agent_id,
            risk_assessment
        )
        
        if not is_valid:
            logger.warning(f"SOP validation failed: {errors}")
        
        risk_assessment["sop_compliance_score"] = score
        
        return risk_assessment
    
    def _calculate_risk(self, blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula 3D risk score."""
        
        # Analizar con LLM para identificar factores
        system_prompt = """Eres un analista de riesgo senior experto en seguridad.

Tu tarea es evaluar el riesgo de un blueprint técnico usando 3D Risk Scoring.

Dimensiones (0-100):
1. IMPACT (40%): Impacto en el sistema
   - Modifica autenticación: +30
   - Maneja datos sensibles: +25
   - Afecta múltiples usuarios: +20
   - Modifica infraestructura crítica: +25

2. COMPLEXITY (30%): Complejidad técnica
   - Múltiples componentes: +20
   - Integración con DB: +15
   - APIs externas: +15
   - Lógica compleja: +20
   - Nuevas tecnologías: +15

3. SENSITIVITY (30%): Datos sensibles
   - Datos personales (PII): +30
   - Credenciales: +25
   - Datos financieros: +30
   - Datos de salud: +35

Fórmula:
Total Score = (Impact × 0.4) + (Complexity × 0.3) + (Sensitivity × 0.3)

Niveles:
- LOW: 0-39 → auto_approve
- MEDIUM: 40-69 → peer_review
- HIGH: 70-100 → human_approval

Output en formato TOON:
risk_assessment
  total_score N.N
  level LOW|MEDIUM|HIGH
  decision auto_approve|peer_review|human_approval
  dimensions
    impact
      score N
      factors[N] "factor"
    complexity
      score N
      factors[N] "factor"
    sensitivity
      score N
      factors[N] "factor"
  recommendations[N] "recomendación"
"""
        
        user_prompt = f"""Blueprint a evaluar:
{to_toon(blueprint)}

Calcula el 3D Risk Score y proporciona recomendaciones.

Output en formato TOON."""
        
        response = self.llm.generate_with_retry(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=2000
        )
        
        try:
            risk_assessment = from_toon(response)
            
            # Validar y ajustar score si es necesario
            total_score = risk_assessment.get("total_score", 0)
            
            # Determinar nivel basado en score
            if total_score < self.low_threshold:
                level = "LOW"
                decision = "auto_approve"
            elif total_score < self.high_threshold:
                level = "MEDIUM"
                decision = "peer_review"
            else:
                level = "HIGH"
                decision = "human_approval"
            
            risk_assessment["level"] = level
            risk_assessment["decision"] = decision
            
            logger.info(
                f"Risk assessment: score={total_score:.1f}, "
                f"level={level}, decision={decision}"
            )
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"Error calculating risk: {e}")
            # Fallback: riesgo medio por defecto
            return {
                "total_score": 50.0,
                "level": "MEDIUM",
                "decision": "peer_review",
                "dimensions": {
                    "impact": {"score": 50, "factors": []},
                    "complexity": {"score": 50, "factors": []},
                    "sensitivity": {"score": 50, "factors": []}
                },
                "recommendations": ["Manual review recommended"],
                "error": str(e)
            }
