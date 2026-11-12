"""
Test Executor Agent - Mecánico

Ejecuta tests en sandbox y calcula coverage.
NO usa LLM - ejecución mecánica.
"""

import logging
import subprocess
import tempfile
import os
from typing import Dict, Any
from core.code_executor import CodeExecutor

logger = logging.getLogger(__name__)


class TestExecutorAgent:
    """
    Agente Test Executor (mecánico).
    
    Workflow:
    1. Recibe código y tests
    2. Ejecuta tests en sandbox
    3. Captura resultados
    4. Calcula coverage
    5. Genera feedback si hay fallos
    
    NO USA LLM - Ejecución mecánica
    """
    
    def __init__(self):
        """Inicializa Test Executor."""
        self.agent_id = "test_executor"
        self.executor = CodeExecutor()
        logger.info("Test Executor Agent initialized (mechanical)")
    
    def process(
        self,
        code_artifacts: Dict[str, Any],
        test_suite: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ejecuta tests y genera reporte.
        
        Args:
            code_artifacts: Código del Coder
            test_suite: Tests del Test Designer
            
        Returns:
            Resultados de ejecución
        """
        logger.info("Executing tests...")
        
        # Combinar código y tests
        all_files = {}
        all_files.update(code_artifacts.get("files", {}))
        all_files.update(test_suite.get("test_files", {}))
        
        if not all_files:
            logger.warning("No files to execute")
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "coverage": 0.0,
                "errors": []
            }
        
        # Ejecutar con pytest si está disponible
        try:
            result = self._execute_with_pytest(all_files)
        except Exception as e:
            logger.warning(f"Pytest execution failed: {e}, trying basic execution")
            result = self._execute_basic(all_files)
        
        logger.info(
            f"Tests executed: {result['passed']}/{result['total_tests']} passed, "
            f"coverage: {result['coverage']:.1%}"
        )
        
        return result
    
    def _execute_with_pytest(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Ejecuta tests con pytest y coverage."""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Escribir archivos
            for filepath, content in files.items():
                full_path = os.path.join(tmpdir, filepath)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Ejecutar pytest con coverage
            try:
                result = subprocess.run(
                    ['pytest', '--cov=.', '--cov-report=term', '-v'],
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                # Parsear output
                output = result.stdout + result.stderr
                
                # Extraer métricas
                total_tests = output.count('PASSED') + output.count('FAILED')
                passed = output.count('PASSED')
                failed = output.count('FAILED')
                
                # Extraer coverage (buscar línea "TOTAL")
                coverage = 0.0
                for line in output.split('\n'):
                    if 'TOTAL' in line:
                        parts = line.split()
                        for part in parts:
                            if '%' in part:
                                coverage = float(part.replace('%', '')) / 100
                                break
                
                errors = []
                if failed > 0:
                    errors.append(f"{failed} tests failed")
                
                return {
                    "total_tests": total_tests,
                    "passed": passed,
                    "failed": failed,
                    "coverage": coverage,
                    "errors": errors,
                    "output": output[:500]  # Limitar tamaño
                }
                
            except subprocess.TimeoutExpired:
                return {
                    "total_tests": 0,
                    "passed": 0,
                    "failed": 0,
                    "coverage": 0.0,
                    "errors": ["Timeout executing tests"]
                }
            except Exception as e:
                raise  # Re-raise para fallback
    
    def _execute_basic(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Ejecución básica sin pytest."""
        
        # Encontrar archivo de test
        test_file = None
        for filepath in files.keys():
            if 'test' in filepath.lower():
                test_file = filepath
                break
        
        if not test_file:
            return {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "coverage": 0.0,
                "errors": ["No test file found"]
            }
        
        # Ejecutar archivo de test
        result = self.executor.execute(files[test_file])
        
        # Estimar resultados basándose en output
        if result.success:
            return {
                "total_tests": 1,
                "passed": 1,
                "failed": 0,
                "coverage": 0.5,  # Estimado
                "errors": []
            }
        else:
            return {
                "total_tests": 1,
                "passed": 0,
                "failed": 1,
                "coverage": 0.0,
                "errors": [result.stderr[:200]]
            }
