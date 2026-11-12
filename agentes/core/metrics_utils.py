"""
Módulo de utilidades para tracking de métricas de agentes.

Este módulo proporciona funciones helper y decoradores para facilitar
el tracking de métricas en los agentes.
"""

import functools
import time
from typing import Callable, Any, Optional
from .metrics_tracker import MetricsTracker


def track_execution(
    agent_id: str,
    track_cost: bool = False,
    track_operations: bool = False
):
    """
    Decorador para trackear automáticamente la ejecución de una función.
    
    Args:
        agent_id: ID del agente
        track_cost: Si trackear costos (requiere que la función retorne costo)
        track_operations: Si trackear número de operaciones
        
    Ejemplo:
        @track_execution(agent_id="db", track_cost=True)
        def validate_model():
            # ... código ...
            return {"success": True, "cost": 0.05}
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            tracker = MetricsTracker(agent_id=agent_id)
            tracker.start()
            
            try:
                result = func(*args, **kwargs)
                
                # Si track_cost y el resultado tiene costo
                if track_cost and isinstance(result, dict):
                    cost = result.get("cost")
                    if cost:
                        tracker.add_cost(cost)
                
                # Si track_operations y el resultado tiene operaciones
                if track_operations and isinstance(result, dict):
                    operations = result.get("operations_count")
                    if operations:
                        tracker.add_operation(operations)
                
                metrics = tracker.finish(success=True)
                tracker.publish(metrics)
                
                return result
            except Exception as e:
                tracker.set_error(str(e))
                metrics = tracker.finish(success=False)
                tracker.publish(metrics)
                raise
        
        return wrapper
    return decorator


class ContextManagerMetricsTracker:
    """
    Context manager para tracking de métricas.
    
    Uso:
        with ContextManagerMetricsTracker("db") as tracker:
            tracker.add_cost(0.05)
            tracker.add_operation(5)
            # ... código ...
    """
    
    def __init__(self, agent_id: str, **kwargs):
        self.tracker = MetricsTracker(agent_id=agent_id, **kwargs)
    
    def __enter__(self):
        self.tracker.start()
        return self.tracker
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        error_message = str(exc_val) if exc_val else None
        metrics = self.tracker.finish(success=success, error_message=error_message)
        self.tracker.publish(metrics)
        return False  # No suprime excepciones

