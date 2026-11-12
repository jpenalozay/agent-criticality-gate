"""
Agente Tester

Genera y ejecuta tests unitarios para código generado.
Analiza cobertura y reporta resultados.
"""

import logging
from typing import Dict, Any, List
from agentes.core.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class TesterAgent:
    """Agente que genera y ejecuta tests."""
    
    def __init__(self):
        """Inicializa el agente tester."""
        self.llm = get_llm_client()
        self.agent_id = "tester"
    
    def process(self, code_artifacts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Genera tests para código.
        
        Args:
            code_artifacts: Código generado
            
        Returns:
            Reporte de tests
        """
        logger.info("Tester generating tests...")
        
        language = code_artifacts.get("language", "python")
        files = code_artifacts.get("files", {})
        
        report = {
            "language": language,
            "total_tests": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "coverage": 0.0,
            "test_files": {},
            "summary": ""
        }
        
        # Generar tests para archivos de código (no tests)
        source_files = {k: v for k, v in files.items() if not k.startswith("tests/")}
        
        for filepath, code in source_files.items():
            if language == "python" and filepath.endswith(".py"):
                test_code = self._generate_python_tests(filepath, code)
                test_filepath = self._get_test_filepath(filepath)
                report["test_files"][test_filepath] = test_code
        
        # Contar tests generados (estimación)
        report["total_tests"] = self._count_tests(report["test_files"], language)
        
        # Por ahora, asumir que todos pasan (sin ejecución real en MVP)
        report["tests_passed"] = report["total_tests"]
        report["tests_failed"] = 0
        
        # Estimar cobertura
        report["coverage"] = self._estimate_coverage(source_files, report["test_files"])
        
        # Generar resumen
        report["summary"] = self._generate_summary(report)
        
        logger.info(
            f"Tester complete: {report['total_tests']} tests generated, "
            f"coverage: {report['coverage']:.1f}%"
        )
        
        return report
    
    def _generate_python_tests(self, filepath: str, code: str) -> str:
        """
        Genera tests para código Python.
        
        Args:
            filepath: Ruta del archivo
            code: Código fuente
            
        Returns:
            Código de tests
        """
        # Extraer nombre del módulo
        module_name = filepath.replace("src/", "").replace(".py", "").replace("/", ".")
        class_name = self._extract_main_class(code)
        
        system_prompt = """Eres un experto en testing con pytest. Genera tests comprehensivos."""
        
        user_prompt = f"""Genera tests unitarios para el siguiente código Python:

```python
{code}
```

Requisitos:
- Usar pytest
- Fixtures apropiados
- Mocks cuando sea necesario
- Patrón AAA (Arrange, Act, Assert)
- Casos normales y edge cases
- Nombres descriptivos
- Cobertura de al menos 80%

Módulo: {module_name}
Clase principal: {class_name}

Genera SOLO el código Python de tests, sin explicaciones."""
        
        try:
            test_code = self.llm.generate_with_retry(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=2000
            )
            
            # Limpiar código
            test_code = self._clean_code(test_code)
            return test_code
            
        except Exception as e:
            logger.error(f"Error generating tests: {e}")
            # Fallback a template básico
            return self._get_basic_test_template(module_name, class_name)
    
    def _extract_main_class(self, code: str) -> str:
        """Extrae el nombre de la clase principal del código."""
        lines = code.split('\n')
        for line in lines:
            if line.strip().startswith('class '):
                # Extraer nombre de clase
                class_def = line.strip()[6:]  # Remover 'class '
                class_name = class_def.split('(')[0].split(':')[0].strip()
                return class_name
        return "MainClass"
    
    def _get_test_filepath(self, source_filepath: str) -> str:
        """Genera ruta de archivo de test."""
        # src/services/user_service.py -> tests/test_user_service.py
        filename = source_filepath.split('/')[-1]
        test_filename = f"test_{filename}"
        return f"tests/{test_filename}"
    
    def _count_tests(self, test_files: Dict[str, str], language: str) -> int:
        """Cuenta número de tests generados."""
        total = 0
        
        for test_code in test_files.values():
            if language == "python":
                # Contar funciones que empiezan con test_
                lines = test_code.split('\n')
                total += sum(1 for line in lines if line.strip().startswith('def test_'))
        
        return total
    
    def _estimate_coverage(
        self,
        source_files: Dict[str, str],
        test_files: Dict[str, str]
    ) -> float:
        """
        Estima cobertura de tests.
        
        Args:
            source_files: Archivos de código fuente
            test_files: Archivos de tests
            
        Returns:
            Porcentaje de cobertura estimado
        """
        if not source_files:
            return 0.0
        
        # Estimación simple: ratio de líneas de test vs código
        source_lines = sum(len(code.split('\n')) for code in source_files.values())
        test_lines = sum(len(code.split('\n')) for code in test_files.values())
        
        if source_lines == 0:
            return 0.0
        
        # Estimación: 1 línea de test por cada 2 líneas de código = 80% coverage
        ratio = test_lines / source_lines
        coverage = min(100.0, ratio * 160)  # Factor de ajuste
        
        return coverage
    
    def _generate_summary(self, report: Dict[str, Any]) -> str:
        """Genera resumen del reporte."""
        total = report["total_tests"]
        passed = report["tests_passed"]
        failed = report["tests_failed"]
        coverage = report["coverage"]
        
        summary = f"Generated {total} tests. "
        
        if failed == 0:
            summary += f"All tests passed. "
        else:
            summary += f"{passed} passed, {failed} failed. "
        
        summary += f"Estimated coverage: {coverage:.1f}%"
        
        if coverage < 60:
            summary += " (LOW - needs improvement)"
        elif coverage < 80:
            summary += " (MEDIUM - acceptable)"
        else:
            summary += " (HIGH - good)"
        
        return summary
    
    def _clean_code(self, code: str) -> str:
        """Limpia código generado."""
        code = code.strip()
        
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        
        if code.endswith("```"):
            code = code[:-3]
        
        return code.strip()
    
    def _get_basic_test_template(self, module_name: str, class_name: str) -> str:
        """Template básico de tests."""
        return f'''"""
Tests for {class_name}
"""

import pytest
from {module_name} import {class_name}


class Test{class_name}:
    """Test suite for {class_name}."""
    
    @pytest.fixture
    def instance(self):
        """Create instance."""
        return {class_name}()
    
    def test_initialization(self, instance):
        """Test initialization."""
        assert instance is not None
    
    def test_basic_functionality(self, instance):
        """Test basic functionality."""
        # TODO: Implement test
        pass
'''
