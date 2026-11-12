"""
Agente Sentinel

Evalúa el riesgo de blueprints usando el sistema de scoring tridimensional.
Determina el routing apropiado (auto/peer/human).
"""

import logging
from typing import Dict, Any
from agentes.core.risk_calculator import RiskCalculator, RiskLevel

logger = logging.getLogger(__name__)


class SentinelAgent:
    """Agente evaluador de riesgo."""
    
    def __init__(self):
        """Inicializa el agente sentinel."""
        self.agent_id = "sentinel"
        self.calculator = RiskCalculator()
    
    def process(self, blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa el riesgo de un blueprint.
        
        Args:
            blueprint: Blueprint a evaluar
            
        Returns:
            Dict con risk assessment completo
        """
        logger.info(f"Sentinel evaluating blueprint: {blueprint.get('name', 'unnamed')}")
        
        # Calcular risk score desde blueprint
        risk_assessment = self.calculator.calculate_from_blueprint(blueprint)
        
        # Agregar recomendaciones
        risk_assessment["recommendations"] = self._generate_recommendations(
            risk_assessment, blueprint
        )
        
        # Agregar análisis detallado
        risk_assessment["analysis"] = self._analyze_components(blueprint)
        
        logger.info(
            f"Risk assessment complete: score={risk_assessment['total_score']:.2f}, "
            f"level={risk_assessment['level']}, decision={risk_assessment['decision']}"
        )
        
        return risk_assessment
    
    def _generate_recommendations(
        self,
        risk_assessment: Dict[str, Any],
        blueprint: Dict[str, Any]
    ) -> list:
        """
        Genera recomendaciones de mitigación.
        
        Args:
            risk_assessment: Assessment de riesgo
            blueprint: Blueprint evaluado
            
        Returns:
            Lista de recomendaciones
        """
        recommendations = []
        score = risk_assessment["total_score"]
        breakdown = risk_assessment["breakdown"]
        
        # Recomendaciones por impacto
        if breakdown["impact"] > 70:
            recommendations.append({
                "type": "impact",
                "severity": "high",
                "message": "Alto impacto detectado. Considerar implementación por fases.",
                "actions": [
                    "Dividir en componentes más pequeños",
                    "Implementar feature flags",
                    "Plan de rollback detallado"
                ]
            })
        
        # Recomendaciones por complejidad
        if breakdown["complexity"] > 70:
            recommendations.append({
                "type": "complexity",
                "severity": "high",
                "message": "Alta complejidad detectada. Requiere revisión exhaustiva.",
                "actions": [
                    "Code review obligatorio",
                    "Aumentar cobertura de tests a 90%+",
                    "Documentación detallada requerida"
                ]
            })
        
        # Recomendaciones por sensibilidad
        if breakdown["sensitivity"] > 70:
            recommendations.append({
                "type": "sensitivity",
                "severity": "critical",
                "message": "Datos sensibles detectados. Medidas de seguridad críticas.",
                "actions": [
                    "Encriptación de datos en reposo y tránsito",
                    "Audit logging completo",
                    "Security scan obligatorio",
                    "Compliance review requerido"
                ]
            })
        
        # Recomendación general por nivel
        if score > 70:
            recommendations.append({
                "type": "general",
                "severity": "high",
                "message": "Score de riesgo alto. Aprobación humana requerida.",
                "actions": [
                    "Revisión por arquitecto senior",
                    "Validación de seguridad",
                    "Plan de contingencia documentado"
                ]
            })
        elif score > 30:
            recommendations.append({
                "type": "general",
                "severity": "medium",
                "message": "Score de riesgo medio. Peer review automático.",
                "actions": [
                    "Revisión por agente IA secundario",
                    "Tests de integración completos"
                ]
            })
        else:
            recommendations.append({
                "type": "general",
                "severity": "low",
                "message": "Score de riesgo bajo. Auto-aprobación permitida.",
                "actions": [
                    "Tests unitarios estándar",
                    "Linting automático"
                ]
            })
        
        return recommendations
    
    def _analyze_components(self, blueprint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza componentes individuales del blueprint.
        
        Args:
            blueprint: Blueprint a analizar
            
        Returns:
            Análisis por componente
        """
        analysis = {
            "total_components": 0,
            "high_risk_components": [],
            "medium_risk_components": [],
            "low_risk_components": [],
            "security_concerns": [],
            "complexity_hotspots": []
        }
        
        components = blueprint.get("components", {})
        analysis["total_components"] = len(components)
        
        for comp_name, comp_data in components.items():
            comp_type = comp_data.get("type", "service")
            criticality = comp_data.get("criticality", "MEDIUM")
            
            # Clasificar por criticidad
            if criticality == "HIGH":
                analysis["high_risk_components"].append(comp_name)
            elif criticality == "MEDIUM":
                analysis["medium_risk_components"].append(comp_name)
            else:
                analysis["low_risk_components"].append(comp_name)
            
            # Detectar concerns de seguridad
            if comp_type in ["auth", "payment", "database"]:
                analysis["security_concerns"].append({
                    "component": comp_name,
                    "reason": f"Componente crítico de tipo {comp_type}"
                })
            
            # Detectar hotspots de complejidad
            if "complex" in comp_data.get("description", "").lower():
                analysis["complexity_hotspots"].append(comp_name)
        
        return analysis
    
    def recalculate(
        self,
        blueprint: Dict[str, Any],
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recalcula el riesgo después de cambios.
        
        Args:
            blueprint: Blueprint actualizado
            changes: Cambios realizados
            
        Returns:
            Nuevo risk assessment
        """
        logger.info(f"Recalculating risk after changes: {list(changes.keys())}")
        
        # Recalcular
        new_assessment = self.process(blueprint)
        
        # Agregar información de cambios
        new_assessment["recalculated"] = True
        new_assessment["changes_applied"] = changes
        
        return new_assessment
