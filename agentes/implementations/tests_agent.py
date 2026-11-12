"""
Tests Agent - Implementación con tracking de métricas.

Este módulo implementa las funciones del Tests Agent con tracking
automático de tests ejecutados, coverage y performance usando MetricsTracker.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Importar el tracker de métricas
from agentes.core import MetricsTracker, ContextManagerMetricsTracker


class TestsAgent:
    """Agente especializado en validación y ejecución de tests."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el Tests Agent.
        
        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.agent_id = "tests"
        self.config = self._load_config(config_path)
        self.tracker_config = self.config.get("metrics_tracking", {})
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Carga la configuración del agente."""
        if config_path is None:
            config_path = "agentes/specs/agents/tests_agent.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def run_tests(self, test_path: str = "tests/", **kwargs) -> Dict[str, Any]:
        """
        Ejecuta tests y trackea métricas.
        
        Args:
            test_path: Ruta al directorio de tests
            
        Returns:
            Dict con resultados de tests y métricas
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.tracker_config.get("publish_to_redis", True),
            save_to_file=self.tracker_config.get("save_to_file", True)
        )
        tracker.start()
        
        try:
            # El agente LLM ejecuta esta función - consume tokens
            llm_query_start = time.time()
            time.sleep(0.1)  # Tiempo del agente LLM procesando
            llm_query_time = (time.time() - llm_query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~600 tokens para ejecución de tests
            llm_tokens_consumed = 600
            tracker.add_llm_tokens(llm_tokens_consumed, "run_tests", llm_query_time)
            tracker.add_query_time(llm_query_time, "run_tests")
            
            # Simular ejecución de tests reales
            test_start = time.time()
            time.sleep(0.5)  # Simular tiempo de ejecución
            test_execution_time = (time.time() - test_start) * 1000  # ms
            
            # Trackear tiempo de ejecución de tests también
            tracker.add_query_time(test_execution_time, "test_execution")
            
            # Simular resultados
            tests_executed = 45
            tests_passed = 42
            tests_failed = 3
            
            tracker.add_custom_metric("tests_executed", tests_executed)
            tracker.add_custom_metric("tests_passed", tests_passed)
            tracker.add_custom_metric("tests_failed", tests_failed)
            tracker.add_custom_metric("test_execution_time_ms", test_execution_time)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "test_path": test_path,
                "tests_executed": tests_executed,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "test_execution_time_ms": test_execution_time,
                "llm_query_time_ms": llm_query_time,
                "llm_tokens_used": metrics.llm_tokens_used,
                "llm_total_cost": metrics.llm_total_cost,
                "success_rate": tests_passed / tests_executed if tests_executed > 0 else 0,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def analyze_coverage(self, **kwargs) -> Dict[str, Any]:
        """
        Analiza coverage de tests.
        
        Returns:
            Dict con análisis de coverage y métricas
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.tracker_config.get("publish_to_redis", True),
            save_to_file=self.tracker_config.get("save_to_file", True)
        )
        tracker.start()
        
        try:
            # El agente LLM ejecuta esta función - consume tokens
            query_start = time.time()
            
            # Simular análisis de coverage
            time.sleep(0.3)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~800 tokens para análisis de coverage
            llm_tokens_consumed = 800
            tracker.add_llm_tokens(llm_tokens_consumed, "analyze_coverage", query_time)
            tracker.add_query_time(query_time, "analyze_coverage")
            
            coverage_percentage = 82.5
            target_coverage = self.config.get("test_and_performance", {}).get("metrics", {}).get("coverage", {}).get("target_percentage", 80)
            
            tracker.add_custom_metric("coverage_percentage", coverage_percentage)
            tracker.add_custom_metric("tests_executed", 45)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "coverage_percentage": coverage_percentage,
                "target_coverage": target_coverage,
                "meets_target": coverage_percentage >= target_coverage,
                "llm_tokens_used": metrics.llm_tokens_used,
                "llm_total_cost": metrics.llm_total_cost,
                "query_time_ms": query_time,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def suggest_tests(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Sugiere tests faltantes para un archivo.
        
        Args:
            file_path: Ruta al archivo a analizar
            
        Returns:
            Dict con sugerencias de tests y métricas
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.tracker_config.get("publish_to_redis", True),
            save_to_file=self.tracker_config.get("save_to_file", True)
        )
        tracker.start()
        
        try:
            # El agente LLM ejecuta esta función - consume tokens
            query_start = time.time()
            
            # Simular análisis y sugerencias
            time.sleep(0.25)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~700 tokens para sugerencias de tests
            llm_tokens_consumed = 700
            tracker.add_llm_tokens(llm_tokens_consumed, "suggest_tests", query_time)
            tracker.add_query_time(query_time, "suggest_tests")
            
            suggestions = [
                {
                    "type": "unit_test",
                    "function": "process_message",
                    "description": "Add unit test for process_message function"
                },
                {
                    "type": "integration_test",
                    "component": "WhatsApp integration",
                    "description": "Add integration test for WhatsApp webhook"
                }
            ]
            
            tracker.add_custom_metric("tests_suggested", len(suggestions))
            tracker.add_custom_metric("files_analyzed", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "file_path": file_path,
                "suggestions": suggestions,
                "llm_tokens_used": metrics.llm_tokens_used,
                "llm_total_cost": metrics.llm_total_cost,
                "query_time_ms": query_time,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise


def main():
    """Función principal para testing."""
    agent = TestsAgent()
    
    # Ejemplo de uso
    print("Testing Tests Agent...")
    
    # Ejecutar tests
    result = agent.run_tests("tests/")
    print(f"Tests executed: {result['tests_executed']}")
    print(f"Tests passed: {result['tests_passed']}, failed: {result['tests_failed']}")
    print(f"Execution time: {result['test_execution_time_ms']:.2f}ms")
    
    # Analizar coverage
    result = agent.analyze_coverage()
    print(f"Coverage: {result['coverage_percentage']}%")
    print(f"Meets target: {result['meets_target']}")
    
    # Sugerir tests
    result = agent.suggest_tests("app/backend/services/internal/user_service.py")
    print(f"Test suggestions: {len(result['suggestions'])}")


if __name__ == "__main__":
    main()

