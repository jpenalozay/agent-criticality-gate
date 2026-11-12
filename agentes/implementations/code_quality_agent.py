"""
Code Quality Agent - Implementación con tracking de métricas.

Este módulo implementa las funciones del Code Quality Agent con tracking
automático de análisis, PEP8, duplicación y complejidad usando MetricsTracker.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Importar el tracker de métricas
from agentes.core import MetricsTracker, ContextManagerMetricsTracker


class CodeQualityAgent:
    """Agente especializado en validación de calidad de código."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el Code Quality Agent.
        
        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.agent_id = "code_quality"
        self.config = self._load_config(config_path)
        self.tracker_config = self.config.get("metrics_tracking", {})
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Carga la configuración del agente."""
        if config_path is None:
            config_path = "agentes/specs/agents/code_quality_agent.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def validate_pep8(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Valida código según PEP 8.
        
        Args:
            file_path: Ruta al archivo a validar
            
        Returns:
            Dict con validación PEP8 y métricas
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
            
            # Simular validación PEP8
            time.sleep(0.2)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~700 tokens para validación PEP8
            llm_tokens_consumed = 700
            tracker.add_llm_tokens(llm_tokens_consumed, "validate_pep8", query_time)
            tracker.add_query_time(query_time, "validate_pep8")
            
            violations = []
            
            # Simular detección de violaciones
            violations.append({
                "line": 45,
                "code": "E501",
                "message": "Line too long (120 > 79 characters)"
            })
            
            tracker.add_custom_metric("files_analyzed", 1)
            tracker.add_custom_metric("pep8_violations", len(violations))
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "file_path": file_path,
                "pep8_compliance": 95.0,
                "violations": violations,
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
    
    def detect_duplication(self, file_paths: List[str], **kwargs) -> Dict[str, Any]:
        """
        Detecta código duplicado.
        
        Args:
            file_paths: Lista de archivos a analizar
            
        Returns:
            Dict con duplicación detectada y métricas
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
            
            # Simular detección de duplicación
            time.sleep(0.3)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~1000 tokens para detección de duplicación (análisis múltiples archivos)
            llm_tokens_consumed = 1000
            tracker.add_llm_tokens(llm_tokens_consumed, "detect_duplication", query_time)
            tracker.add_query_time(query_time, "detect_duplication")
            
            duplicates = []
            if len(file_paths) > 1:
                duplicates.append({
                    "type": "function_duplication",
                    "files": file_paths[:2],
                    "lines": [45, 50],
                    "similarity": 0.85
                })
            
            tracker.add_custom_metric("files_analyzed", len(file_paths))
            tracker.add_custom_metric("duplication_blocks", len(duplicates))
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "files_analyzed": len(file_paths),
                "duplicates": duplicates,
                "duplication_percentage": 3.5,
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
    
    def analyze_complexity(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Analiza complejidad ciclomática del código.
        
        Args:
            file_path: Ruta al archivo a analizar
            
        Returns:
            Dict con análisis de complejidad y métricas
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
            
            # Simular análisis de complejidad
            time.sleep(0.25)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~850 tokens para análisis de complejidad ciclomática
            llm_tokens_consumed = 850
            tracker.add_llm_tokens(llm_tokens_consumed, "analyze_complexity", query_time)
            tracker.add_query_time(query_time, "analyze_complexity")
            
            complexity_issues = []
            avg_complexity = 7.5
            
            if avg_complexity > 8:
                complexity_issues.append({
                    "function": "process_data",
                    "complexity": 12,
                    "recommendation": "Refactor to reduce complexity"
                })
            
            tracker.add_custom_metric("files_analyzed", 1)
            tracker.add_custom_metric("complexity_issues", len(complexity_issues))
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "file_path": file_path,
                "average_complexity": avg_complexity,
                "complexity_issues": complexity_issues,
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
    
    def suggest_refactoring(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Sugiere refactorings para mejorar calidad del código.
        
        Args:
            file_path: Ruta al archivo a analizar
            
        Returns:
            Dict con sugerencias de refactoring y métricas
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
            time.sleep(0.22)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~950 tokens para sugerencias de refactoring
            llm_tokens_consumed = 950
            tracker.add_llm_tokens(llm_tokens_consumed, "suggest_refactoring", query_time)
            tracker.add_query_time(query_time, "suggest_refactoring")
            
            suggestions = [
                {
                    "type": "extract_method",
                    "location": "app/main.py:120",
                    "description": "Extract complex logic into separate method"
                },
                {
                    "type": "reduce_parameters",
                    "location": "app/main.py:145",
                    "description": "Consider using a configuration object"
                }
            ]
            
            tracker.add_custom_metric("files_analyzed", 1)
            tracker.add_custom_metric("refactoring_suggestions", len(suggestions))
            tracker.add_custom_metric("code_smells", 2)
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
    agent = CodeQualityAgent()
    
    # Ejemplo de uso
    print("Testing Code Quality Agent...")
    
    # Validar PEP8
    result = agent.validate_pep8("app/main.py")
    print(f"PEP8 compliance: {result['pep8_compliance']}%")
    print(f"Violations: {len(result['violations'])}")
    
    # Detectar duplicación
    files = ["app/main.py", "app/backend/services/internal/user_service.py"]
    result = agent.detect_duplication(files)
    print(f"Duplication: {result['duplication_percentage']}%")
    print(f"Duplicate blocks: {len(result['duplicates'])}")
    
    # Analizar complejidad
    result = agent.analyze_complexity("app/main.py")
    print(f"Average complexity: {result['average_complexity']}")
    print(f"Complexity issues: {len(result['complexity_issues'])}")
    
    # Sugerir refactoring
    result = agent.suggest_refactoring("app/main.py")
    print(f"Refactoring suggestions: {len(result['suggestions'])}")


if __name__ == "__main__":
    main()

