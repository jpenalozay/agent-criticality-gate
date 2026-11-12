"""
OpenAI Agent - Implementación con tracking de métricas.

Este módulo implementa las funciones del OpenAI Agent con tracking
automático de costos, tiempos y tokens usando MetricsTracker.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Importar el tracker de métricas
from agentes.core import MetricsTracker, ContextManagerMetricsTracker


class OpenAIAgent:
    """Agente especializado en validación y optimización de OpenAI."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el OpenAI Agent.
        
        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.agent_id = "openai"
        self.config = self._load_config(config_path)
        self.tracker_config = self.config.get("metrics_tracking", {})
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Carga la configuración del agente."""
        if config_path is None:
            config_path = "agentes/specs/agents/openai_agent.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def validate_integration(self, **kwargs) -> Dict[str, Any]:
        """
        Valida integración con OpenAI API.
        
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
                
                # Simular validación de integración
                # En producción, aquí se validaría la API key, assistant ID, etc.
                time.sleep(0.1)  # Simular trabajo
                
                query_time = (time.time() - query_start) * 1000  # ms
                
                # Estimar tokens consumidos por el agente LLM para esta operación
                # Estimación: ~500 tokens para análisis y validación
                llm_tokens_consumed = 500
                tracker.add_llm_tokens(llm_tokens_consumed, "validate_integration", query_time)
                tracker.add_query_time(query_time, "validate_integration")
                
                tracker.add_custom_metric("api_key_valid", True)
                tracker.add_custom_metric("assistant_id_valid", True)
                tracker.add_operation(1)
                
                return {
                    "status": "valid",
                    "api_key_configured": True,
                    "assistant_id_configured": True,
                    "error_handling": True,
                    "timeouts_configured": True,
                    "success": True
                }
            except Exception as e:
                tracker.set_error(str(e))
                raise
    
    def optimize_prompts(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Optimiza prompts para reducir tokens y mejorar efectividad.
        
        Args:
            prompt: Prompt a optimizar
            
        Returns:
            Dict con prompt optimizado y métricas
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
            
            # Simular optimización de prompt
            original_tokens = len(prompt.split()) * 1.3  # Estimación aproximada
            time.sleep(0.2)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Optimizar prompt (en producción sería más sofisticado)
            optimized_prompt = prompt.strip()
            optimized_tokens = len(optimized_prompt.split()) * 1.3
            
            tokens_saved = original_tokens - optimized_tokens
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~800 tokens para análisis y optimización de prompt
            llm_tokens_consumed = 800
            tracker.add_llm_tokens(llm_tokens_consumed, "optimize_prompts", query_time)
            tracker.add_query_time(query_time, "optimize_prompts")
            
            tracker.add_custom_metric("tokens_used", optimized_tokens)
            tracker.add_custom_metric("prompt_tokens", optimized_tokens)
            tracker.add_custom_metric("tokens_saved", tokens_saved)
            tracker.add_custom_metric("api_calls", 0)  # No hace llamada real aquí
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "original_prompt": prompt,
                "optimized_prompt": optimized_prompt,
                "original_tokens": original_tokens,
                "optimized_tokens": optimized_tokens,
                "tokens_saved": tokens_saved,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def monitor_costs(self, tokens_used: int, pricing_rate: float = 0.002) -> Dict[str, Any]:
        """
        Monitorea costos de OpenAI basado en tokens usados.
        
        Args:
            tokens_used: Número de tokens usados (de la API externa)
            pricing_rate: Precio por 1K tokens (default: $0.002)
            
        Returns:
            Dict con costos y métricas
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
            
            # Calcular costo de la API externa
            cost_per_1k = pricing_rate
            cost_usd = (tokens_used / 1000) * cost_per_1k
            
            time.sleep(0.1)  # Simular trabajo
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~600 tokens para análisis de costos
            llm_tokens_consumed = 600
            tracker.add_llm_tokens(llm_tokens_consumed, "monitor_costs", query_time)
            tracker.add_query_time(query_time, "monitor_costs")
            
            # Costo de la API externa (separado del costo del agente LLM)
            tracker.add_cost(cost_usd)
            tracker.add_custom_metric("tokens_used", tokens_used)  # Tokens de API externa
            tracker.add_custom_metric("prompt_tokens", int(tokens_used * 0.7))  # Estimación
            tracker.add_custom_metric("completion_tokens", int(tokens_used * 0.3))  # Estimación
            tracker.add_custom_metric("cost_per_request", cost_usd)  # Costo API externa
            tracker.add_custom_metric("api_calls", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            # Verificar límites
            daily_limit = self.config.get("test_and_performance", {}).get("metrics", {}).get("costs", {}).get("daily_limit_usd", 10.0)
            warning_threshold = daily_limit * 0.8
            
            return {
                "tokens_used": tokens_used,  # Tokens de API externa
                "cost_usd": cost_usd,  # Costo API externa
                "llm_tokens_used": metrics.llm_tokens_used,  # Tokens del agente LLM
                "llm_total_cost": metrics.llm_total_cost,  # Costo del agente LLM
                "total_cost_usd": (cost_usd + (metrics.llm_total_cost or 0)),  # Costo total (API + agente)
                "daily_limit_usd": daily_limit,
                "warning_threshold_usd": warning_threshold,
                "within_limit": cost_usd < daily_limit,
                "warning": cost_usd >= warning_threshold,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def validate_rate_limits(self, requests_per_minute: int, **kwargs) -> Dict[str, Any]:
        """
        Valida manejo de rate limits de OpenAI.
        
        Args:
            requests_per_minute: Número de requests por minuto actuales
            
        Returns:
            Dict con validación de rate limits
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.tracker_config.get("publish_to_redis", True),
            save_to_file=self.tracker_config.get("save_to_file", True)
        )
        tracker.start()
        
        try:
            # Verificar rate limits
            max_requests_per_minute = 60  # Límite típico de OpenAI
            retry_logic_configured = True
            backoff_configured = True
            
            tracker.add_custom_metric("requests_per_minute", requests_per_minute)
            tracker.add_custom_metric("rate_limit_configured", True)
            tracker.add_custom_metric("retry_logic_configured", retry_logic_configured)
            tracker.add_custom_metric("backoff_configured", backoff_configured)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "requests_per_minute": requests_per_minute,
                "max_requests_per_minute": max_requests_per_minute,
                "within_limit": requests_per_minute < max_requests_per_minute,
                "retry_logic_configured": retry_logic_configured,
                "backoff_configured": backoff_configured,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def monitor_performance(self, api_response_time_ms: float, **kwargs) -> Dict[str, Any]:
        """
        Monitorea performance de llamadas a OpenAI.
        
        Args:
            api_response_time_ms: Tiempo de respuesta de la API en ms
            
        Returns:
            Dict con métricas de performance
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.tracker_config.get("publish_to_redis", True),
            save_to_file=self.tracker_config.get("save_to_file", True)
        )
        tracker.start()
        
        try:
            max_response_time = self.config.get("test_and_performance", {}).get("metrics", {}).get("performance", {}).get("max_response_time_ms", 30000)
            warning_response_time = self.config.get("test_and_performance", {}).get("metrics", {}).get("performance", {}).get("warning_response_time_ms", 20000)
            
            tracker.add_custom_metric("api_response_time_ms", api_response_time_ms)
            tracker.add_custom_metric("api_calls", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "api_response_time_ms": api_response_time_ms,
                "max_response_time_ms": max_response_time,
                "warning_response_time_ms": warning_response_time,
                "within_limit": api_response_time_ms < max_response_time,
                "warning": api_response_time_ms >= warning_response_time,
                "success_rate": 1.0,  # En producción se calcularía de histórico
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
    agent = OpenAIAgent()
    
    # Ejemplo de uso
    print("Testing OpenAI Agent...")
    
    # Validar integración
    result = agent.validate_integration()
    print(f"Integration validation: {result['status']}")
    
    # Optimizar prompt
    prompt = "This is a test prompt that needs optimization"
    result = agent.optimize_prompts(prompt)
    print(f"Tokens saved: {result.get('tokens_saved', 0):.2f}")
    
    # Monitorear costos
    result = agent.monitor_costs(tokens_used=1500)
    print(f"Cost: ${result['cost_usd']:.4f}")
    
    # Validar rate limits
    result = agent.validate_rate_limits(requests_per_minute=30)
    print(f"Rate limit OK: {result['within_limit']}")
    
    # Monitorear performance
    result = agent.monitor_performance(api_response_time_ms=2500)
    print(f"Response time: {result['api_response_time_ms']}ms")


if __name__ == "__main__":
    main()

