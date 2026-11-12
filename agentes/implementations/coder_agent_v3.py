"""
Coder Agent v3.0 - Con Executable Feedback

Genera código y lo ejecuta iterativamente para auto-corrección.
"""

import logging
from typing import Dict, Any, Optional
from core.llm_client_v3 import get_llm_client
from core.code_executor import CodeExecutor
from core.feedback_analyzer import FeedbackAnalyzer
from core.toon_parser import to_toon, from_toon
from core.sop_validator import SOPValidator

logger = logging.getLogger(__name__)


class CoderAgentV3:
    """
    Agente Coder con executable feedback loop.
    
    Workflow:
    1. Generar código inicial basado en blueprint
    2. Ejecutar código en sandbox Docker
    3. Si hay errores: analizar y corregir (max 3 iteraciones)
    4. Retornar código validado y ejecutable
    """
    
    def __init__(
        self,
        enable_executable_feedback: bool = True,
        max_iterations: int = 3,
        timeout: int = 60
    ):
        """
        Inicializa agente coder.
        
        Args:
            enable_executable_feedback: Habilitar feedback loop
            max_iterations: Máximo de iteraciones de corrección
            timeout: Timeout de ejecución en segundos
        """
        self.agent_id = "coder"
        self.llm = get_llm_client(self.agent_id)
        self.executor = CodeExecutor(timeout=timeout) if enable_executable_feedback else None
        self.feedback_analyzer = FeedbackAnalyzer() if enable_executable_feedback else None
        self.sop_validator = SOPValidator()
        self.enable_executable_feedback = enable_executable_feedback
        self.max_iterations = max_iterations
        
        logger.info(
            f"Coder Agent v3.0 initialized "
            f"(executable_feedback={'enabled' if enable_executable_feedback else 'disabled'}, "
            f"max_iterations={max_iterations})"
        )
    
    def process(
        self,
        blueprint: Dict[str, Any],
        risk_assessment: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Procesa blueprint y genera código.
        
        Args:
            blueprint: Blueprint del arquitecto
            risk_assessment: Assessment del sentinel
            
        Returns:
            Code artifacts con resultados de ejecución
        """
        logger.info(f"Processing blueprint: {blueprint.get('name', 'unnamed')}")
        
        # 1. Generar código inicial
        code_artifacts = self._generate_code(blueprint, risk_assessment)
        
        # 2. Si executable feedback está habilitado, iterar
        if self.enable_executable_feedback and self.executor:
            code_artifacts = self._executable_feedback_loop(
                code_artifacts,
                blueprint
            )
        
        # 3. Validar SOP
        is_valid, errors, score = self.sop_validator.validate_output(
            self.agent_id,
            code_artifacts
        )
        
        code_artifacts["sop_compliance_score"] = score
        
        return code_artifacts
    
    def _generate_code(
        self,
        blueprint: Dict[str, Any],
        risk_assessment: Optional[Dict]
    ) -> Dict[str, Any]:
        """Genera código inicial basado en blueprint."""
        
        system_prompt = """Eres un ingeniero de software senior experto en Python.

Tu tarea es generar código production-ready basado en blueprints técnicos.

Requisitos de calidad:
- Type hints en todas las funciones
- Docstrings completos (Google style)
- Manejo de errores apropiado
- Código limpio y bien estructurado
- Tests unitarios básicos

Output en formato TOON:
code_artifacts
  language "python"
  files
    "path/to/file.py" "contenido del archivo"
  structure[N]
    "directorio/subdirectorio"
"""
        
        user_prompt = f"""Blueprint:
{to_toon(blueprint)}

{f"Risk Assessment: {to_toon(risk_assessment)}" if risk_assessment else ""}

Genera código Python completo con:
1. Archivos principales
2. Tests unitarios
3. Requirements.txt si es necesario

Output en formato TOON."""
        
        response = self.llm.generate_with_retry(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=4000
        )
        
        try:
            code_artifacts = from_toon(response)
            logger.info(f"Code generated: {len(code_artifacts.get('files', {}))} files")
            return code_artifacts
        except Exception as e:
            logger.error(f"Error parsing code artifacts: {e}")
            return {
                "language": "python",
                "files": {},
                "error": str(e)
            }
    
    def _executable_feedback_loop(
        self,
        code_artifacts: Dict[str, Any],
        blueprint: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Loop de executable feedback.
        
        Ejecuta código y corrige errores iterativamente.
        """
        logger.info("Starting executable feedback loop...")
        
        files = code_artifacts.get("files", {})
        if not files:
            logger.warning("No files to execute")
            return code_artifacts
        
        # Encontrar archivo principal (main.py, app.py, etc.)
        main_file = self._find_main_file(files)
        if not main_file:
            logger.warning("No main file found, skipping execution")
            return code_artifacts
        
        code = files[main_file]
        language = code_artifacts.get("language", "python")
        
        execution_history = []
        
        for iteration in range(self.max_iterations):
            logger.info(f"Iteration {iteration + 1}/{self.max_iterations}")
            
            # Ejecutar código
            result = self.executor.execute(code, language)
            
            execution_history.append({
                "iteration": iteration + 1,
                "success": result.success,
                "runtime_ms": result.runtime_ms,
                "stdout": result.stdout[:500],  # Limitar tamaño
                "stderr": result.stderr[:500]
            })
            
            if result.success:
                logger.info(f"✓ Code executed successfully in {result.runtime_ms}ms")
                code_artifacts["execution_results"] = {
                    "success": True,
                    "iterations": iteration + 1,
                    "runtime_ms": result.runtime_ms,
                    "history": execution_history
                }
                return code_artifacts
            
            # Analizar errores
            analyses = self.feedback_analyzer.analyze(
                stderr=result.stderr,
                stdout=result.stdout,
                code=code
            )
            
            if not analyses:
                logger.warning("No error analysis available")
                break
            
            # Generar feedback
            feedback = self.feedback_analyzer.generate_feedback(analyses, code)
            logger.info(f"Feedback generated: {len(analyses)} errors found")
            
            # Corregir código
            code = self._fix_code(code, feedback, blueprint)
            files[main_file] = code
        
        # Si llegamos aquí, no se pudo corregir
        logger.warning(f"Failed to fix code after {self.max_iterations} iterations")
        code_artifacts["execution_results"] = {
            "success": False,
            "iterations": self.max_iterations,
            "history": execution_history
        }
        
        return code_artifacts
    
    def _find_main_file(self, files: Dict[str, str]) -> Optional[str]:
        """Encuentra archivo principal para ejecutar."""
        # Prioridad: main.py, app.py, __main__.py, primer .py
        priorities = ["main.py", "app.py", "__main__.py"]
        
        for priority in priorities:
            for filepath in files.keys():
                if filepath.endswith(priority):
                    return filepath
        
        # Si no hay prioridad, tomar primer .py
        for filepath in files.keys():
            if filepath.endswith(".py"):
                return filepath
        
        return None
    
    def _fix_code(
        self,
        code: str,
        feedback: str,
        blueprint: Dict[str, Any]
    ) -> str:
        """Corrige código basado en feedback."""
        
        fix_prompt = f"""El código tiene errores. Por favor corrígelos.

Blueprint original:
{to_toon(blueprint)}

Código actual:
```python
{code}
```

Errores encontrados:
{feedback}

Genera el código corregido completo (solo el código, sin explicaciones)."""
        
        response = self.llm.generate_with_retry(
            prompt=fix_prompt,
            temperature=0.1,
            max_tokens=4000
        )
        
        # Limpiar código (remover markdown si existe)
        fixed_code = self._clean_code(response)
        
        return fixed_code
    
    def _clean_code(self, code: str) -> str:
        """Limpia código de markdown y otros artefactos."""
        # Remover bloques de código markdown
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]
        
        return code.strip()
