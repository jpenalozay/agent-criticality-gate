"""
Peer Review Mechanism - Consensus entre múltiples LLMs

Implementa el mecanismo de peer review para agentes críticos.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    """Resultado de una revisión."""
    approved: bool
    suggestions: List[str]
    concerns: List[str]
    confidence: float  # 0-1


class PeerReview:
    """
    Mecanismo de peer review con consensus.
    
    Workflow:
    1. Principal genera output
    2. Reviewer revisa y sugiere mejoras
    3. Consensus mechanism decide si aprobar o iterar
    """
    
    def __init__(self, consensus_threshold: float = 0.8):
        """
        Inicializa peer review.
        
        Args:
            consensus_threshold: Umbral de acuerdo para aprobar (0-1)
        """
        self.consensus_threshold = consensus_threshold
        logger.info(f"Peer Review initialized with threshold: {consensus_threshold}")
    
    def review(
        self,
        principal_output: Dict[str, Any],
        reviewer_output: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], float]:
        """
        Realiza peer review y consensus.
        
        Args:
            principal_output: Output del agente principal
            reviewer_output: Output del reviewer
            
        Returns:
            Tuple de (approved, merged_output, agreement_score)
        """
        # Calcular score de acuerdo
        agreement_score = self._calculate_agreement(
            principal_output,
            reviewer_output
        )
        
        logger.info(f"Agreement score: {agreement_score:.2f}")
        
        # Decidir según threshold
        if agreement_score >= self.consensus_threshold:
            # Alto acuerdo: aprobar con ajustes menores
            merged = self._merge_outputs(principal_output, reviewer_output)
            return True, merged, agreement_score
        
        elif agreement_score >= 0.5:
            # Acuerdo medio: negociar
            merged = self._negotiate(principal_output, reviewer_output)
            return True, merged, agreement_score
        
        else:
            # Bajo acuerdo: rechazar y solicitar re-trabajo
            return False, principal_output, agreement_score
    
    def _calculate_agreement(
        self,
        output1: Dict[str, Any],
        output2: Dict[str, Any]
    ) -> float:
        """
        Calcula score de acuerdo entre dos outputs (0-1).
        
        Compara:
        - Campos presentes
        - Valores similares
        - Estructura
        """
        if not output1 or not output2:
            return 0.0
        
        # Obtener keys comunes
        keys1 = set(output1.keys())
        keys2 = set(output2.keys())
        
        common_keys = keys1 & keys2
        all_keys = keys1 | keys2
        
        if not all_keys:
            return 0.0
        
        # Score basado en keys comunes
        key_score = len(common_keys) / len(all_keys)
        
        # Score basado en valores similares
        value_score = 0.0
        if common_keys:
            matching_values = 0
            for key in common_keys:
                if output1[key] == output2[key]:
                    matching_values += 1
                elif isinstance(output1[key], dict) and isinstance(output2[key], dict):
                    # Comparación recursiva para dicts
                    sub_score = self._calculate_agreement(output1[key], output2[key])
                    matching_values += sub_score
            
            value_score = matching_values / len(common_keys)
        
        # Score final (promedio de key_score y value_score)
        final_score = (key_score + value_score) / 2
        
        return final_score
    
    def _merge_outputs(
        self,
        principal: Dict[str, Any],
        reviewer: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge outputs cuando hay alto acuerdo.
        
        Estrategia:
        - Mantener estructura del principal
        - Agregar sugerencias del reviewer
        """
        merged = principal.copy()
        
        # Agregar campos del reviewer que no están en principal
        for key, value in reviewer.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(value, dict) and isinstance(merged[key], dict):
                # Merge recursivo para dicts
                merged[key] = self._merge_outputs(merged[key], value)
        
        return merged
    
    def _negotiate(
        self,
        principal: Dict[str, Any],
        reviewer: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Negocia diferencias cuando hay acuerdo medio.
        
        Estrategia:
        - Tomar campos con mayor confianza
        - Combinar sugerencias
        """
        # Por ahora, usar merge simple
        # En versión completa, podría usar LLM para negociar
        return self._merge_outputs(principal, reviewer)
    
    def extract_suggestions(
        self,
        reviewer_output: Dict[str, Any]
    ) -> List[str]:
        """
        Extrae sugerencias del reviewer.
        
        Args:
            reviewer_output: Output del reviewer
            
        Returns:
            Lista de sugerencias
        """
        suggestions = []
        
        # Buscar campo de sugerencias
        if "suggestions" in reviewer_output:
            suggestions = reviewer_output["suggestions"]
        elif "recommendations" in reviewer_output:
            suggestions = reviewer_output["recommendations"]
        elif "improvements" in reviewer_output:
            suggestions = reviewer_output["improvements"]
        
        return suggestions if isinstance(suggestions, list) else []
    
    def extract_concerns(
        self,
        reviewer_output: Dict[str, Any]
    ) -> List[str]:
        """
        Extrae preocupaciones del reviewer.
        
        Args:
            reviewer_output: Output del reviewer
            
        Returns:
            Lista de preocupaciones
        """
        concerns = []
        
        # Buscar campo de preocupaciones
        if "concerns" in reviewer_output:
            concerns = reviewer_output["concerns"]
        elif "issues" in reviewer_output:
            concerns = reviewer_output["issues"]
        elif "warnings" in reviewer_output:
            concerns = reviewer_output["warnings"]
        
        return concerns if isinstance(concerns, list) else []
