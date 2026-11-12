"""
Feedback Analyzer - Analiza errores de ejecución

Analiza errores de ejecución de código y genera feedback para corrección.
"""

import logging
import re
from typing import Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ErrorAnalysis:
    """Análisis de un error."""
    error_type: str
    message: str
    line_number: int
    suggestions: List[str]
    severity: str  # low, medium, high


class FeedbackAnalyzer:
    """
    Analiza errores de ejecución y genera feedback.
    
    Características:
    - Identifica tipo de error
    - Extrae línea problemática
    - Genera sugerencias de corrección
    """
    
    def __init__(self):
        """Inicializa analyzer."""
        self.error_patterns = self._init_error_patterns()
        logger.info("Feedback Analyzer initialized")
    
    def _init_error_patterns(self) -> Dict[str, Dict]:
        """Inicializa patrones de errores comunes."""
        return {
            "NameError": {
                "pattern": r"NameError: name '(\w+)' is not defined",
                "suggestions": [
                    "Verificar que la variable esté definida antes de usarla",
                    "Revisar imports necesarios",
                    "Verificar scope de la variable"
                ]
            },
            "TypeError": {
                "pattern": r"TypeError: (.+)",
                "suggestions": [
                    "Verificar tipos de datos",
                    "Revisar argumentos de función",
                    "Agregar type hints"
                ]
            },
            "AttributeError": {
                "pattern": r"AttributeError: '(\w+)' object has no attribute '(\w+)'",
                "suggestions": [
                    "Verificar que el objeto tenga el atributo",
                    "Revisar documentación del objeto",
                    "Verificar que el objeto esté inicializado"
                ]
            },
            "ImportError": {
                "pattern": r"ImportError: (.+)|ModuleNotFoundError: (.+)",
                "suggestions": [
                    "Verificar que el módulo esté instalado",
                    "Revisar nombre del módulo",
                    "Agregar módulo a requirements.txt"
                ]
            },
            "SyntaxError": {
                "pattern": r"SyntaxError: (.+)",
                "suggestions": [
                    "Revisar sintaxis de Python",
                    "Verificar paréntesis, corchetes y llaves",
                    "Revisar indentación"
                ]
            },
            "IndentationError": {
                "pattern": r"IndentationError: (.+)",
                "suggestions": [
                    "Verificar indentación consistente",
                    "Usar 4 espacios por nivel",
                    "No mezclar tabs y espacios"
                ]
            }
        }
    
    def analyze(
        self,
        stderr: str,
        stdout: str = "",
        code: str = ""
    ) -> List[ErrorAnalysis]:
        """
        Analiza errores de ejecución.
        
        Args:
            stderr: Error output
            stdout: Standard output
            code: Código ejecutado
            
        Returns:
            Lista de análisis de errores
        """
        if not stderr:
            return []
        
        analyses = []
        
        # Dividir stderr en líneas
        error_lines = stderr.split('\n')
        
        # Buscar patrones de error
        for error_type, pattern_info in self.error_patterns.items():
            pattern = pattern_info["pattern"]
            
            for line in error_lines:
                match = re.search(pattern, line)
                if match:
                    # Extraer número de línea si está disponible
                    line_number = self._extract_line_number(error_lines)
                    
                    analysis = ErrorAnalysis(
                        error_type=error_type,
                        message=match.group(0),
                        line_number=line_number,
                        suggestions=pattern_info["suggestions"],
                        severity=self._determine_severity(error_type)
                    )
                    
                    analyses.append(analysis)
                    break
        
        # Si no se identificó ningún error conocido, crear análisis genérico
        if not analyses and stderr:
            analyses.append(ErrorAnalysis(
                error_type="Unknown",
                message=stderr[:200],
                line_number=0,
                suggestions=["Revisar el error completo", "Verificar la lógica del código"],
                severity="medium"
            ))
        
        return analyses
    
    def _extract_line_number(self, error_lines: List[str]) -> int:
        """Extrae número de línea del traceback."""
        for line in error_lines:
            match = re.search(r'line (\d+)', line)
            if match:
                return int(match.group(1))
        return 0
    
    def _determine_severity(self, error_type: str) -> str:
        """Determina severidad del error."""
        high_severity = ["SyntaxError", "IndentationError", "ImportError"]
        medium_severity = ["NameError", "TypeError", "AttributeError"]
        
        if error_type in high_severity:
            return "high"
        elif error_type in medium_severity:
            return "medium"
        else:
            return "low"
    
    def generate_feedback(
        self,
        analyses: List[ErrorAnalysis],
        code: str = ""
    ) -> str:
        """
        Genera feedback textual para el LLM.
        
        Args:
            analyses: Lista de análisis de errores
            code: Código original
            
        Returns:
            Feedback formateado para el LLM
        """
        if not analyses:
            return "Código ejecutado exitosamente sin errores."
        
        feedback_parts = ["El código tiene los siguientes errores:\n"]
        
        for i, analysis in enumerate(analyses, 1):
            feedback_parts.append(f"\n{i}. {analysis.error_type}:")
            feedback_parts.append(f"   Mensaje: {analysis.message}")
            
            if analysis.line_number > 0:
                feedback_parts.append(f"   Línea: {analysis.line_number}")
            
            feedback_parts.append(f"   Severidad: {analysis.severity}")
            feedback_parts.append("   Sugerencias:")
            
            for suggestion in analysis.suggestions:
                feedback_parts.append(f"   - {suggestion}")
        
        feedback_parts.append("\nPor favor, corrige estos errores y genera el código nuevamente.")
        
        return "\n".join(feedback_parts)
    
    def to_dict(self, analyses: List[ErrorAnalysis]) -> List[Dict[str, Any]]:
        """Convierte análisis a diccionario."""
        return [
            {
                "error_type": a.error_type,
                "message": a.message,
                "line_number": a.line_number,
                "suggestions": a.suggestions,
                "severity": a.severity
            }
            for a in analyses
        ]
