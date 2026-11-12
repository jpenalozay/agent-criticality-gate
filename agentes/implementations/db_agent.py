"""
DB Agent - Implementación con tracking de métricas.

Este módulo implementa las funciones del DB Agent con tracking
automático de queries, tiempos y recursos usando MetricsTracker.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Importar el tracker de métricas
from agentes.core import MetricsTracker, ContextManagerMetricsTracker


class DBAgent:
    """Agente especializado en validación y optimización de base de datos."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el DB Agent.
        
        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.agent_id = "db"
        self.config = self._load_config(config_path)
        self.tracker_config = self.config.get("metrics_tracking", {})
        self.query_count = 0
        self.query_time_total = 0.0
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Carga la configuración del agente."""
        if config_path is None:
            config_path = "agentes/specs/agents/db_agent.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def validate_model(self, model_file: str, **kwargs) -> Dict[str, Any]:
        """
        Valida el modelo de datos.
        
        Args:
            model_file: Ruta al archivo del modelo
            
        Returns:
            Dict con resultados de validación y métricas
        """
        with ContextManagerMetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.tracker_config.get("publish_to_redis", True),
            save_to_file=self.tracker_config.get("save_to_file", True)
        ) as tracker:
            try:
                # El agente LLM ejecuta esta función - consume tokens
                query_start = time.time()
                
                # Simular validación de modelo
                # En producción, aquí se validaría el modelo SQLAlchemy
                time.sleep(0.15)
                
                query_time = (time.time() - query_start) * 1000  # ms
                
                # Estimar tokens consumidos por el agente LLM para esta operación
                # Estimación: ~700 tokens para análisis de modelo de datos
                llm_tokens_consumed = 700
                tracker.add_llm_tokens(llm_tokens_consumed, "validate_model", query_time)
                tracker.add_query_time(query_time, "validate_model")
                
                tracker.add_custom_metric("model_validations", 1)
                tracker.add_custom_metric("model_file", model_file)
                tracker.add_operation(1)
                
                return {
                    "status": "valid",
                    "model_file": model_file,
                    "errors": [],
                    "warnings": [],
                    "suggestions": [],
                    "success": True
                }
            except Exception as e:
                tracker.set_error(str(e))
                raise
    
    def execute_query(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta una query SQL y trackea métricas.
        
        Args:
            query: Query SQL a ejecutar
            
        Returns:
            Dict con resultados y métricas
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
            
            # Simular ejecución de query (operación del agente LLM)
            time.sleep(0.02)  # Tiempo del agente LLM procesando
            llm_query_time = (time.time() - llm_query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~400 tokens para ejecutar y validar query
            llm_tokens_consumed = 400
            tracker.add_llm_tokens(llm_tokens_consumed, "execute_query", llm_query_time)
            tracker.add_query_time(llm_query_time, "execute_query")
            
            # Ahora ejecutar la query real a la base de datos
            db_query_start = time.time()
            time.sleep(0.05)  # Simular tiempo de query DB
            db_query_time = (time.time() - db_query_start) * 1000  # ms
            
            self.query_count += 1
            self.query_time_total += db_query_time
            
            # Trackear tiempo de query DB también
            tracker.add_query_time(db_query_time, "db_query_execution")
            
            tracker.add_custom_metric("queries_executed", 1)
            tracker.add_custom_metric("query_time_ms", db_query_time)  # Tiempo de query DB
            tracker.add_custom_metric("llm_query_time_ms", llm_query_time)  # Tiempo del agente LLM
            tracker.add_custom_metric("avg_query_time_ms", self.query_time_total / self.query_count)
            tracker.add_custom_metric("db_operations", 1)
            tracker.add_custom_metric("connections_used", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "query": query[:100] + "..." if len(query) > 100 else query,
                "query_time_ms": db_query_time,  # Tiempo de query DB
                "llm_query_time_ms": llm_query_time,  # Tiempo del agente LLM
                "llm_tokens_used": metrics.llm_tokens_used,
                "llm_total_cost": metrics.llm_total_cost,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def suggest_improvements(self, model_file: str, **kwargs) -> Dict[str, Any]:
        """
        Sugiere mejoras al modelo de datos.
        
        Args:
            model_file: Ruta al archivo del modelo
            
        Returns:
            Dict con sugerencias y métricas
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.tracker_config.get("publish_to_redis", True),
            save_to_file=self.tracker_config.get("save_to_file", True)
        )
        tracker.start()
        
        try:
            # Simular análisis y sugerencias
            time.sleep(0.2)
            
            suggestions = [
                {
                    "type": "index",
                    "table": "messages",
                    "column": "conversation_id",
                    "recommendation": "Add index for foreign key"
                }
            ]
            
            tracker.add_custom_metric("model_validations", 1)
            tracker.add_custom_metric("suggestions_count", len(suggestions))
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "model_file": model_file,
                "suggestions": suggestions,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def analyze_performance(self, **kwargs) -> Dict[str, Any]:
        """
        Analiza performance de queries y detecta bottlenecks.
        
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
            # Simular análisis de performance
            time.sleep(0.3)
            
            bottlenecks = []
            if self.query_count > 0:
                avg_time = self.query_time_total / self.query_count
                if avg_time > 500:  # Si promedio > 500ms
                    bottlenecks.append({
                        "type": "slow_queries",
                        "avg_time_ms": avg_time,
                        "recommendation": "Optimize queries or add indexes"
                    })
            
            tracker.add_custom_metric("queries_executed", self.query_count)
            tracker.add_custom_metric("query_time_ms", self.query_time_total)
            tracker.add_custom_metric("avg_query_time_ms", self.query_time_total / self.query_count if self.query_count > 0 else 0)
            tracker.add_custom_metric("bottlenecks_detected", len(bottlenecks))
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "total_queries": self.query_count,
                "total_query_time_ms": self.query_time_total,
                "avg_query_time_ms": self.query_time_total / self.query_count if self.query_count > 0 else 0,
                "bottlenecks": bottlenecks,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def apply_migration(self, migration_file: str, **kwargs) -> Dict[str, Any]:
        """
        Aplica una migración y trackea métricas.
        
        Args:
            migration_file: Ruta al archivo de migración
            
        Returns:
            Dict con resultados y métricas
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.tracker_config.get("publish_to_redis", True),
            save_to_file=self.tracker_config.get("save_to_file", True)
        )
        tracker.start()
        
        try:
            # Simular aplicación de migración
            time.sleep(0.25)
            
            tracker.add_custom_metric("migrations_applied", 1)
            tracker.add_custom_metric("migration_file", migration_file)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "migration_file": migration_file,
                "status": "applied",
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
    agent = DBAgent()
    
    # Ejemplo de uso
    print("Testing DB Agent...")
    
    # Validar modelo
    result = agent.validate_model("app/backend/models/current.py")
    print(f"Model validation: {result['status']}")
    
    # Ejecutar queries
    result = agent.execute_query("SELECT * FROM users LIMIT 10")
    print(f"Query executed in {result['query_time_ms']:.2f}ms")
    
    result = agent.execute_query("SELECT COUNT(*) FROM messages")
    print(f"Query executed in {result['query_time_ms']:.2f}ms")
    
    # Analizar performance
    result = agent.analyze_performance()
    print(f"Avg query time: {result['avg_query_time_ms']:.2f}ms")
    print(f"Bottlenecks: {len(result['bottlenecks'])}")
    
    # Sugerir mejoras
    result = agent.suggest_improvements("app/backend/models/current.py")
    print(f"Suggestions: {len(result['suggestions'])}")


if __name__ == "__main__":
    main()

