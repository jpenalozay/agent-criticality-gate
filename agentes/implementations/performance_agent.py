"""
Performance Agent - Implementación con tracking de métricas.

Este módulo implementa las funciones del Performance Agent con tracking
automático de análisis, bottlenecks y optimizaciones usando MetricsTracker.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Importar el tracker de métricas
from agentes.core import MetricsTracker, ContextManagerMetricsTracker


class PerformanceAgent:
    """Agente especializado en análisis de performance y estabilidad."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el Performance Agent.
        
        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.agent_id = "performance"
        self.config = self._load_config(config_path)
        self.tracker_config = self.config.get("metrics_tracking", {})
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Carga la configuración del agente."""
        if config_path is None:
            config_path = "agentes/specs/agents/performance_agent.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_performance(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Analiza performance del código.
        
        Args:
            file_path: Ruta al archivo a analizar
            
        Returns:
            Dict con análisis de performance y métricas
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
            
            # Simular análisis de performance
            time.sleep(0.3)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~950 tokens para análisis de performance
            llm_tokens_consumed = 950
            tracker.add_llm_tokens(llm_tokens_consumed, "analyze_performance", query_time)
            tracker.add_query_time(query_time, "analyze_performance")
            
            # Detectar problemas comunes
            issues = []
            optimizations = []
            
            # Simular detección de N+1 queries
            if "query" in file_path.lower():
                issues.append({
                    "type": "potential_n_plus_one",
                    "severity": "medium",
                    "recommendation": "Use eager loading or batch queries"
                })
            
            # Simular detección de operaciones bloqueantes
            if "async" in file_path.lower():
                issues.append({
                    "type": "blocking_operation_in_async",
                    "severity": "high",
                    "recommendation": "Use async/await for I/O operations"
                })
            
            optimizations.append({
                "type": "add_cache",
                "description": "Consider adding Redis cache for frequently accessed data"
            })
            
            tracker.add_custom_metric("analyses_performed", 1)
            tracker.add_custom_metric("files_analyzed", 1)
            tracker.add_custom_metric("optimizations_suggested", len(optimizations))
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "file_path": file_path,
                "performance_score": 85,
                "issues": issues,
                "optimizations": optimizations,
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
    
    def detect_bottlenecks(self, **kwargs) -> Dict[str, Any]:
        """
        Detecta cuellos de botella en el sistema.
        
        Returns:
            Dict con bottlenecks detectados y métricas
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
            
            # Simular detección de bottlenecks
            time.sleep(0.4)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~1100 tokens para detección de bottlenecks (análisis complejo)
            llm_tokens_consumed = 1100
            tracker.add_llm_tokens(llm_tokens_consumed, "detect_bottlenecks", query_time)
            tracker.add_query_time(query_time, "detect_bottlenecks")
            
            bottlenecks = [
                {
                    "type": "slow_query",
                    "location": "app/backend/services/internal/user_service.py:45",
                    "query_time_ms": 1200,
                    "recommendation": "Add index on user_id column"
                },
                {
                    "type": "high_memory_usage",
                    "location": "app/main.py:120",
                    "memory_mb": 450,
                    "recommendation": "Implement pagination for large datasets"
                }
            ]
            
            tracker.add_custom_metric("analyses_performed", 1)
            tracker.add_custom_metric("bottlenecks_detected", len(bottlenecks))
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "bottlenecks": bottlenecks,
                "total_bottlenecks": len(bottlenecks),
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
    
    def check_error_handling(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Verifica manejo de errores en el código.
        
        Args:
            file_path: Ruta al archivo a verificar
            
        Returns:
            Dict con validación de manejo de errores y métricas
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
            
            # Simular verificación de manejo de errores
            time.sleep(0.2)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~650 tokens para verificación de errores
            llm_tokens_consumed = 650
            tracker.add_llm_tokens(llm_tokens_consumed, "check_error_handling", query_time)
            tracker.add_query_time(query_time, "check_error_handling")
            
            issues = []
            score = 100
            
            # Simular detección de problemas
            if "try" not in file_path.lower():
                issues.append({
                    "type": "missing_try_except",
                    "severity": "high",
                    "recommendation": "Add try/except blocks for error handling"
                })
                score -= 20
            
            tracker.add_custom_metric("error_handling_validations", 1)
            tracker.add_custom_metric("files_analyzed", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "file_path": file_path,
                "error_handling_score": score,
                "issues": issues,
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
    
    def validate_logging(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Valida logging en el código.
        
        Args:
            file_path: Ruta al archivo a validar
            
        Returns:
            Dict con validación de logging y métricas
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
            
            # Simular validación de logging
            time.sleep(0.15)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~550 tokens para validación de logging
            llm_tokens_consumed = 550
            tracker.add_llm_tokens(llm_tokens_consumed, "validate_logging", query_time)
            tracker.add_query_time(query_time, "validate_logging")
            
            issues = []
            score = 100
            
            # Simular detección de problemas
            if "logging" not in file_path.lower():
                issues.append({
                    "type": "missing_logging",
                    "severity": "medium",
                    "recommendation": "Add structured logging"
                })
                score -= 15
            
            tracker.add_custom_metric("logging_validations", 1)
            tracker.add_custom_metric("files_analyzed", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "file_path": file_path,
                "logging_score": score,
                "issues": issues,
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
    agent = PerformanceAgent()
    
    # Ejemplo de uso
    print("Testing Performance Agent...")
    
    # Analizar performance
    result = agent.analyze_performance("app/main.py")
    print(f"Performance score: {result['performance_score']}")
    print(f"Optimizations suggested: {len(result['optimizations'])}")
    
    # Detectar bottlenecks
    result = agent.detect_bottlenecks()
    print(f"Bottlenecks detected: {result['total_bottlenecks']}")
    
    # Verificar manejo de errores
    result = agent.check_error_handling("app/backend/services/internal/user_service.py")
    print(f"Error handling score: {result['error_handling_score']}")
    
    # Validar logging
    result = agent.validate_logging("app/main.py")
    print(f"Logging score: {result['logging_score']}")


if __name__ == "__main__":
    main()

