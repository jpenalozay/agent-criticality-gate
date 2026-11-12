"""
SOP Validator - Validador de Standard Operating Procedures

Valida que los outputs de los agentes cumplan con sus SOPs definidos.
"""

import logging
from typing import Dict, Any, List, Tuple
import yaml
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)


class SOPValidator:
    """Validador de SOPs para agentes."""
    
    def __init__(self, sop_definitions_path: str = "config/sop_definitions.yaml"):
        """
        Inicializa validador de SOPs.
        
        Args:
            sop_definitions_path: Ruta al archivo de definiciones de SOPs
        """
        self.sops = self._load_sops(sop_definitions_path)
        logger.info(f"SOP Validator initialized with {len(self.sops)} SOPs")
    
    def _load_sops(self, path: str) -> Dict[str, Dict]:
        """Carga definiciones de SOPs desde archivo YAML."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"SOP definitions file not found: {path}")
            return self._get_default_sops()
    
    def _get_default_sops(self) -> Dict[str, Dict]:
        """Retorna SOPs por defecto si no hay archivo."""
        return {
            "arquitecto": {
                "output_schema": {
                    "type": "object",
                    "required": ["name", "type", "components"],
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "components": {"type": "object"},
                        "dependencies": {"type": "array"}
                    }
                }
            },
            "coder": {
                "output_schema": {
                    "type": "object",
                    "required": ["files", "language"],
                    "properties": {
                        "files": {"type": "object"},
                        "language": {"type": "string"}
                    }
                }
            }
        }
    
    def validate_output(
        self,
        agent_id: str,
        output: Dict[str, Any]
    ) -> Tuple[bool, List[str], float]:
        """
        Valida output de un agente contra su SOP.
        
        Args:
            agent_id: ID del agente
            output: Output del agente
            
        Returns:
            Tuple de (is_valid, errors, compliance_score)
        """
        if agent_id not in self.sops:
            logger.warning(f"No SOP defined for agent: {agent_id}")
            return True, [], 1.0
        
        sop = self.sops[agent_id]
        errors = []
        
        # Validar schema si existe
        if "output_schema" in sop:
            try:
                validate(instance=output, schema=sop["output_schema"])
            except ValidationError as e:
                errors.append(f"Schema validation error: {e.message}")
        
        # Validar reglas de validación si existen
        if "validation_rules" in sop:
            rule_errors = self._validate_rules(output, sop["validation_rules"])
            errors.extend(rule_errors)
        
        # Calcular compliance score
        is_valid = len(errors) == 0
        compliance_score = self._calculate_compliance_score(output, sop, errors)
        
        if not is_valid:
            logger.warning(
                f"SOP validation failed for {agent_id}: {len(errors)} errors"
            )
        
        return is_valid, errors, compliance_score
    
    def _validate_rules(
        self,
        output: Dict[str, Any],
        rules: List[str]
    ) -> List[str]:
        """Valida reglas custom del SOP."""
        errors = []
        
        for rule in rules:
            # Implementar validaciones custom aquí
            # Por ahora, solo logging
            logger.debug(f"Validating rule: {rule}")
        
        return errors
    
    def _calculate_compliance_score(
        self,
        output: Dict[str, Any],
        sop: Dict,
        errors: List[str]
    ) -> float:
        """
        Calcula score de cumplimiento del SOP (0-1).
        
        Args:
            output: Output del agente
            sop: Definición del SOP
            errors: Errores encontrados
            
        Returns:
            Score de 0.0 a 1.0
        """
        if not errors:
            return 1.0
        
        # Score basado en número de errores
        # Cada error reduce el score
        max_errors = 10
        error_penalty = min(len(errors) / max_errors, 1.0)
        
        return max(0.0, 1.0 - error_penalty)
