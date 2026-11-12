"""
Risk Calculator

Implementa el sistema de scoring de riesgo tridimensional:
RiskScore = (Impacto × 0.4) + (Complejidad × 0.3) + (Sensibilidad × 0.3)
"""

import logging
from typing import Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Niveles de riesgo."""
    AUTO_APPROVE = "auto_approve"  # 0-30
    PEER_REVIEW = "peer_review"    # 31-70
    HUMAN_APPROVAL = "human_approval"  # 71-100


class RiskCalculator:
    """Calculadora de riesgo para componentes de software."""
    
    # Pesos de la fórmula
    IMPACT_WEIGHT = 0.4
    COMPLEXITY_WEIGHT = 0.3
    SENSITIVITY_WEIGHT = 0.3
    
    # Umbrales
    AUTO_APPROVE_MAX = 30
    PEER_REVIEW_MAX = 70
    
    # Tablas de scoring
    IMPACT_SCORES = {
        "frontend": 10,
        "ui": 10,
        "utils": 30,
        "helpers": 30,
        "business_logic": 60,
        "service": 60,
        "database": 80,
        "cache": 80,
        "auth": 90,
        "core": 100,
        "payment": 100,
    }
    
    SENSITIVITY_SCORES = {
        "public": 0,
        "internal": 30,
        "pii": 70,
        "personal": 70,
        "financial": 100,
        "medical": 100,
        "health": 100,
    }
    
    @staticmethod
    def calculate_impact(component_type: str, component_name: str = "") -> float:
        """
        Calcula el score de impacto (0-100).
        
        Args:
            component_type: Tipo de componente (frontend, database, etc.)
            component_name: Nombre del componente (opcional)
            
        Returns:
            Score de impacto (0-100)
        """
        component_lower = component_type.lower()
        name_lower = component_name.lower()
        
        # Buscar en tabla de scores
        for key, score in RiskCalculator.IMPACT_SCORES.items():
            if key in component_lower or key in name_lower:
                logger.debug(f"Impact score for '{component_type}': {score} (matched '{key}')")
                return float(score)
        
        # Default: business logic
        logger.debug(f"Impact score for '{component_type}': 60 (default)")
        return 60.0
    
    @staticmethod
    def calculate_complexity(
        lines_of_code: int = 0,
        num_dependencies: int = 0,
        has_complex_logic: bool = False
    ) -> float:
        """
        Calcula el score de complejidad (0-100).
        
        Args:
            lines_of_code: Número de líneas de código
            num_dependencies: Número de dependencias
            has_complex_logic: Si tiene lógica compleja
            
        Returns:
            Score de complejidad (0-100)
        """
        score = 0.0
        
        # Por líneas de código
        if lines_of_code < 10:
            score += 10
        elif lines_of_code < 100:
            score += 30
        elif lines_of_code < 500:
            score += 60
        else:
            score += 80
        
        # Por dependencias
        if num_dependencies > 5:
            score += 10
        elif num_dependencies > 10:
            score += 20
        
        # Por lógica compleja
        if has_complex_logic:
            score += 20
        
        # Normalizar a 0-100
        score = min(100.0, score)
        
        logger.debug(
            f"Complexity score: {score} "
            f"(loc={lines_of_code}, deps={num_dependencies}, complex={has_complex_logic})"
        )
        return score
    
    @staticmethod
    def calculate_sensitivity(data_types: List[str]) -> float:
        """
        Calcula el score de sensibilidad (0-100).
        
        Args:
            data_types: Lista de tipos de datos manejados
            
        Returns:
            Score de sensibilidad (0-100)
        """
        if not data_types:
            return 0.0
        
        max_score = 0.0
        
        for data_type in data_types:
            data_lower = data_type.lower()
            
            for key, score in RiskCalculator.SENSITIVITY_SCORES.items():
                if key in data_lower:
                    max_score = max(max_score, float(score))
                    logger.debug(f"Sensitivity score for '{data_type}': {score} (matched '{key}')")
                    break
        
        if max_score == 0.0:
            # Default: internal data
            max_score = 30.0
            logger.debug(f"Sensitivity score: 30 (default)")
        
        return max_score
    
    @staticmethod
    def calculate_risk_score(
        component_type: str,
        component_name: str = "",
        lines_of_code: int = 0,
        num_dependencies: int = 0,
        has_complex_logic: bool = False,
        data_types: List[str] = None
    ) -> Dict[str, Any]:
        """
        Calcula el risk score completo.
        
        Args:
            component_type: Tipo de componente
            component_name: Nombre del componente
            lines_of_code: Líneas de código
            num_dependencies: Número de dependencias
            has_complex_logic: Si tiene lógica compleja
            data_types: Tipos de datos manejados
            
        Returns:
            Dict con score total y desglose
        """
        if data_types is None:
            data_types = []
        
        # Calcular componentes
        impact = RiskCalculator.calculate_impact(component_type, component_name)
        complexity = RiskCalculator.calculate_complexity(
            lines_of_code, num_dependencies, has_complex_logic
        )
        sensitivity = RiskCalculator.calculate_sensitivity(data_types)
        
        # Fórmula ponderada
        total_score = (
            impact * RiskCalculator.IMPACT_WEIGHT +
            complexity * RiskCalculator.COMPLEXITY_WEIGHT +
            sensitivity * RiskCalculator.SENSITIVITY_WEIGHT
        )
        
        # Determinar nivel
        if total_score <= RiskCalculator.AUTO_APPROVE_MAX:
            level = RiskLevel.AUTO_APPROVE
            decision = "auto_merge"
        elif total_score <= RiskCalculator.PEER_REVIEW_MAX:
            level = RiskLevel.PEER_REVIEW
            decision = "peer_review"
        else:
            level = RiskLevel.HUMAN_APPROVAL
            decision = "human_approval"
        
        result = {
            "total_score": round(total_score, 2),
            "level": level.value,
            "decision": decision,
            "breakdown": {
                "impact": round(impact, 2),
                "complexity": round(complexity, 2),
                "sensitivity": round(sensitivity, 2)
            },
            "weights": {
                "impact": RiskCalculator.IMPACT_WEIGHT,
                "complexity": RiskCalculator.COMPLEXITY_WEIGHT,
                "sensitivity": RiskCalculator.SENSITIVITY_WEIGHT
            }
        }
        
        logger.info(
            f"Risk score calculated: {total_score:.2f} ({level.value}) - "
            f"Impact: {impact:.2f}, Complexity: {complexity:.2f}, Sensitivity: {sensitivity:.2f}"
        )
        
        return result
    
    @staticmethod
    def calculate_from_blueprint(blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula risk score desde un blueprint TOON.
        
        Args:
            blueprint: Blueprint en formato dict
            
        Returns:
            Dict con risk score
        """
        # Extraer información del blueprint
        component_type = blueprint.get("type", "service")
        component_name = blueprint.get("name", "")
        
        # Estimar complejidad desde componentes
        components = blueprint.get("components", {})
        num_components = len(components) if isinstance(components, dict) else 0
        
        # Estimar sensibilidad desde datos
        data_types = []
        if "data" in blueprint:
            data_types = blueprint["data"] if isinstance(blueprint["data"], list) else []
        
        # Detectar lógica compleja
        has_complex_logic = (
            "complex" in str(blueprint).lower() or
            num_components > 5 or
            "algorithm" in str(blueprint).lower()
        )
        
        return RiskCalculator.calculate_risk_score(
            component_type=component_type,
            component_name=component_name,
            lines_of_code=num_components * 50,  # Estimación
            num_dependencies=num_components,
            has_complex_logic=has_complex_logic,
            data_types=data_types
        )
