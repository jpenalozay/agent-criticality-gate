"""
Linter Agent - Mecánico

Análisis estático de código con múltiples herramientas.
NO usa LLM - análisis mecánico.
"""

import logging
import subprocess
import tempfile
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class LinterAgent:
    """
    Agente Linter (mecánico).
    
    Workflow:
    1. Recibe código
    2. Ejecuta herramientas de linting:
       - pylint
       - flake8
       - mypy (type checking)
    3. Calcula quality score
    4. Genera recomendaciones
    
    NO USA LLM - Análisis estático
    """
    
    def __init__(self):
        """Inicializa Linter."""
        self.agent_id = "linter"
        self.tools = self._check_available_tools()
        logger.info(f"Linter Agent initialized with tools: {', '.join(self.tools)}")
    
    def _check_available_tools(self) -> List[str]:
        """Verifica qué herramientas están disponibles."""
        tools = []
        for tool in ['pylint', 'flake8', 'mypy']:
            try:
                subprocess.run([tool, '--version'], capture_output=True, timeout=5)
                tools.append(tool)
            except:
                pass
        return tools
    
    def process(self, code_artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analiza código y genera reporte.
        
        Args:
            code_artifacts: Código del Coder
            
        Returns:
            Reporte de calidad
        """
        logger.info("Linting code...")
        
        files = code_artifacts.get("files", {})
        if not files:
            return {
                "quality_score": 0.0,
                "issues": [],
                "recommendations": ["No files to lint"]
            }
        
        # Ejecutar linters
        all_issues = []
        scores = []
        
        for tool in self.tools:
            issues, score = self._run_linter(tool, files)
            all_issues.extend(issues)
            scores.append(score)
        
        # Calcular score promedio
        quality_score = sum(scores) / len(scores) if scores else 0.0
        
        # Generar recomendaciones
        recommendations = self._generate_recommendations(all_issues)
        
        logger.info(f"Linting complete: score={quality_score:.1f}, issues={len(all_issues)}")
        
        return {
            "quality_score": quality_score,
            "issues": all_issues[:20],  # Limitar a 20 issues
            "recommendations": recommendations[:10],  # Limitar a 10
            "tools_used": self.tools
        }
    
    def _run_linter(
        self,
        tool: str,
        files: Dict[str, str]
    ) -> tuple[List[Dict], float]:
        """Ejecuta un linter específico."""
        
        issues = []
        score = 100.0
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Escribir archivos Python
            python_files = []
            for filepath, content in files.items():
                if filepath.endswith('.py'):
                    full_path = os.path.join(tmpdir, filepath)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    python_files.append(full_path)
            
            if not python_files:
                return issues, score
            
            # Ejecutar linter
            try:
                if tool == 'pylint':
                    result = subprocess.run(
                        ['pylint'] + python_files,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    issues, score = self._parse_pylint(result.stdout)
                
                elif tool == 'flake8':
                    result = subprocess.run(
                        ['flake8'] + python_files,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    issues, score = self._parse_flake8(result.stdout)
                
                elif tool == 'mypy':
                    result = subprocess.run(
                        ['mypy'] + python_files,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    issues, score = self._parse_mypy(result.stdout)
                
            except subprocess.TimeoutExpired:
                logger.warning(f"{tool} timed out")
            except Exception as e:
                logger.warning(f"Error running {tool}: {e}")
        
        return issues, score
    
    def _parse_pylint(self, output: str) -> tuple[List[Dict], float]:
        """Parsea output de pylint."""
        issues = []
        score = 100.0
        
        for line in output.split('\n'):
            if 'Your code has been rated at' in line:
                # Extraer score
                parts = line.split('rated at')
                if len(parts) > 1:
                    score_str = parts[1].split('/')[0].strip()
                    try:
                        score = float(score_str) * 10  # Convertir a 0-100
                    except:
                        pass
            elif ':' in line and any(x in line for x in ['error', 'warning', 'convention']):
                issues.append({
                    "tool": "pylint",
                    "message": line[:100]
                })
        
        return issues, score
    
    def _parse_flake8(self, output: str) -> tuple[List[Dict], float]:
        """Parsea output de flake8."""
        issues = []
        
        for line in output.split('\n'):
            if line.strip():
                issues.append({
                    "tool": "flake8",
                    "message": line[:100]
                })
        
        # Score basado en número de issues
        score = max(0, 100 - len(issues) * 2)
        
        return issues, score
    
    def _parse_mypy(self, output: str) -> tuple[List[Dict], float]:
        """Parsea output de mypy."""
        issues = []
        
        for line in output.split('\n'):
            if 'error:' in line:
                issues.append({
                    "tool": "mypy",
                    "message": line[:100]
                })
        
        # Score basado en número de errores
        score = max(0, 100 - len(issues) * 3)
        
        return issues, score
    
    def _generate_recommendations(self, issues: List[Dict]) -> List[str]:
        """Genera recomendaciones basadas en issues."""
        recommendations = []
        
        # Contar tipos de issues
        error_count = sum(1 for i in issues if 'error' in i.get('message', '').lower())
        warning_count = sum(1 for i in issues if 'warning' in i.get('message', '').lower())
        
        if error_count > 0:
            recommendations.append(f"Fix {error_count} errors")
        if warning_count > 0:
            recommendations.append(f"Address {warning_count} warnings")
        
        # Recomendaciones genéricas
        if len(issues) > 10:
            recommendations.append("Consider refactoring to improve code quality")
        if any('type' in i.get('message', '').lower() for i in issues):
            recommendations.append("Add type hints for better type safety")
        
        return recommendations if recommendations else ["Code quality is good"]
