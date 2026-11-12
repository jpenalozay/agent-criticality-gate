"""
WhatsApp Agent - Implementación con tracking de métricas.

Este módulo implementa las funciones del WhatsApp Agent con tracking
automático de mensajes, API calls y webhooks usando MetricsTracker.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Importar el tracker de métricas
from agentes.core import MetricsTracker, ContextManagerMetricsTracker


class WhatsAppAgent:
    """Agente especializado en validación y monitoreo de integración WhatsApp."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el WhatsApp Agent.
        
        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.agent_id = "whatsapp"
        self.config = self._load_config(config_path)
        self.tracker_config = self.config.get("metrics_tracking", {})
        self.messages_processed = 0
        self.api_calls = 0
        self.errors_encountered = 0
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Carga la configuración del agente."""
        if config_path is None:
            config_path = "agentes/specs/agents/whatsapp_agent.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def validate_integration(self, **kwargs) -> Dict[str, Any]:
        """
        Valida integración con WhatsApp Business API.
        
        Returns:
            Dict con resultados de validación y métricas
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
            
            # Simular validación de integración
            time.sleep(0.1)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~500 tokens para validación de integración WhatsApp
            llm_tokens_consumed = 500
            tracker.add_llm_tokens(llm_tokens_consumed, "validate_integration", query_time)
            tracker.add_query_time(query_time, "validate_integration")
            
            tracker.add_custom_metric("api_calls", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "status": "valid",
                "api_key_configured": True,
                "webhook_configured": True,
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
    
    def process_message(self, message: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Procesa un mensaje de WhatsApp y trackea métricas.
        
        Args:
            message: Mensaje a procesar
            
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
            time.sleep(0.02)  # Tiempo del agente LLM procesando
            llm_query_time = (time.time() - llm_query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~450 tokens para procesamiento de mensaje WhatsApp
            llm_tokens_consumed = 450
            tracker.add_llm_tokens(llm_tokens_consumed, "process_message", llm_query_time)
            tracker.add_query_time(llm_query_time, "process_message")
            
            # Ahora procesar mensaje con API externa
            api_start = time.time()
            time.sleep(0.05)
            api_response_time = (time.time() - api_start) * 1000  # ms
            
            # Trackear tiempo de API también
            tracker.add_query_time(api_response_time, "whatsapp_api_call")
            
            self.messages_processed += 1
            self.api_calls += 1
            
            tracker.add_custom_metric("messages_processed", 1)
            tracker.add_custom_metric("api_calls", 1)
            tracker.add_custom_metric("api_response_time_ms", api_response_time)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "message_id": message.get("id", "unknown"),
                "status": "processed",
                "api_response_time_ms": api_response_time,
                "llm_query_time_ms": llm_query_time,
                "llm_tokens_used": metrics.llm_tokens_used,
                "llm_total_cost": metrics.llm_total_cost,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            self.errors_encountered += 1
            tracker.set_error(str(e))
            tracker.add_custom_metric("errors_encountered", 1)
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def handle_webhook(self, webhook_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Maneja un evento webhook de WhatsApp.
        
        Args:
            webhook_data: Datos del webhook
            
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
            query_start = time.time()
            
            # Simular manejo de webhook
            time.sleep(0.08)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~400 tokens para manejo de webhook
            llm_tokens_consumed = 400
            tracker.add_llm_tokens(llm_tokens_consumed, "handle_webhook", query_time)
            tracker.add_query_time(query_time, "handle_webhook")
            
            tracker.add_custom_metric("webhook_events", 1)
            tracker.add_custom_metric("messages_processed", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "webhook_type": webhook_data.get("type", "unknown"),
                "status": "processed",
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
    
    def validate_rate_limiting(self, requests_per_minute: int, **kwargs) -> Dict[str, Any]:
        """
        Valida rate limiting de WhatsApp API.
        
        Args:
            requests_per_minute: Número de requests por minuto actuales
            
        Returns:
            Dict con validación de rate limiting y métricas
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
            
            # Verificar rate limits
            max_requests = self.config.get("test_and_performance", {}).get("metrics", {}).get("rate_limiting", {}).get("max_requests_per_minute", 1000)
            warning_threshold = self.config.get("test_and_performance", {}).get("metrics", {}).get("rate_limiting", {}).get("warning_requests_per_minute", 800)
            
            time.sleep(0.08)
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~350 tokens para validación de rate limiting
            llm_tokens_consumed = 350
            tracker.add_llm_tokens(llm_tokens_consumed, "validate_rate_limiting", query_time)
            tracker.add_query_time(query_time, "validate_rate_limiting")
            
            rate_limit_hits = 0
            if requests_per_minute >= max_requests:
                rate_limit_hits = 1
            
            tracker.add_custom_metric("rate_limit_hits", rate_limit_hits)
            tracker.add_custom_metric("api_calls", requests_per_minute)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "requests_per_minute": requests_per_minute,
                "max_requests_per_minute": max_requests,
                "warning_threshold": warning_threshold,
                "within_limit": requests_per_minute < max_requests,
                "warning": requests_per_minute >= warning_threshold,
                "rate_limit_hits": rate_limit_hits,
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
    agent = WhatsAppAgent()
    
    # Ejemplo de uso
    print("Testing WhatsApp Agent...")
    
    # Validar integración
    result = agent.validate_integration()
    print(f"Integration status: {result['status']}")
    
    # Procesar mensaje
    message = {"id": "msg_123", "text": "Hello", "from": "+1234567890"}
    result = agent.process_message(message)
    print(f"Message processed: {result['status']}")
    print(f"API response time: {result['api_response_time_ms']:.2f}ms")
    
    # Manejar webhook
    webhook = {"type": "message", "data": message}
    result = agent.handle_webhook(webhook)
    print(f"Webhook processed: {result['status']}")
    
    # Validar rate limiting
    result = agent.validate_rate_limiting(requests_per_minute=450)
    print(f"Rate limit OK: {result['within_limit']}")


if __name__ == "__main__":
    main()

