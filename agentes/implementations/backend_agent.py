"""
Backend Agent - Implementación con tracking de métricas.

Este módulo implementa las funciones del Backend Agent con tracking
automático de validaciones, código generado y endpoints usando MetricsTracker.
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Importar el tracker de métricas
from agentes.core import MetricsTracker, ContextManagerMetricsTracker


class BackendAgent:
    """Agente especializado en validación y generación de código backend."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el Backend Agent.
        
        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.agent_id = "backend"
        self.config = self._load_config(config_path)
        self.tracker_config = self.config.get("metrics_tracking", {})
        self.files_analyzed = 0
        self.errors_found = 0
        self.warnings_found = 0
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Carga la configuración del agente."""
        if config_path is None:
            config_path = "agentes/specs/agents/backend_agent.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def validate_code(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Valida código Python según mejores prácticas y seguridad.
        
        Args:
            file_path: Ruta al archivo a validar
            
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
            
            # Simular validación de código
            time.sleep(0.2)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~800 tokens para análisis de código Python
            llm_tokens_consumed = 800
            tracker.add_llm_tokens(llm_tokens_consumed, "validate_code", query_time)
            tracker.add_query_time(query_time, "validate_code")
            
            errors = []
            warnings = []
            
            # Simular detección de problemas
            if "password" in file_path.lower():
                warnings.append({
                    "type": "security",
                    "message": "Verify password hashing is used",
                    "line": 45
                })
            
            self.files_analyzed += 1
            self.errors_found += len(errors)
            self.warnings_found += len(warnings)
            
            tracker.add_custom_metric("files_analyzed", 1)
            tracker.add_custom_metric("code_validations", 1)
            tracker.add_custom_metric("errors_found", len(errors))
            tracker.add_custom_metric("warnings_found", len(warnings))
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "file_path": file_path,
                "status": "valid" if len(errors) == 0 else "invalid",
                "errors": errors,
                "warnings": warnings,
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
    
    def validate_endpoints(self, endpoints: List[str], **kwargs) -> Dict[str, Any]:
        """
        Valida endpoints API.
        
        Args:
            endpoints: Lista de endpoints a validar
            
        Returns:
            Dict con validación de endpoints y métricas
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
            
            # Simular validación de endpoints
            time.sleep(0.15)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~600 tokens para validación de endpoints API
            llm_tokens_consumed = 600
            tracker.add_llm_tokens(llm_tokens_consumed, "validate_endpoints", query_time)
            tracker.add_query_time(query_time, "validate_endpoints")
            
            validated_endpoints = []
            issues = []
            
            for endpoint in endpoints:
                validated_endpoints.append({
                    "endpoint": endpoint,
                    "status": "valid",
                    "has_auth": True,
                    "has_validation": True
                })
            
            tracker.add_custom_metric("endpoints_validated", len(endpoints))
            tracker.add_custom_metric("code_validations", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "endpoints": validated_endpoints,
                "total_endpoints": len(endpoints),
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
    
    def check_security(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Verifica seguridad del código.
        
        Args:
            file_path: Ruta al archivo a verificar
            
        Returns:
            Dict con verificación de seguridad y métricas
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
            
            # Simular verificación de seguridad
            time.sleep(0.18)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~900 tokens para análisis de seguridad
            llm_tokens_consumed = 900
            tracker.add_llm_tokens(llm_tokens_consumed, "check_security", query_time)
            tracker.add_query_time(query_time, "check_security")
            
            security_issues = []
            score = 100
            
            # Simular detección de problemas
            if "sql" in file_path.lower():
                security_issues.append({
                    "type": "potential_sql_injection",
                    "severity": "high",
                    "recommendation": "Use parameterized queries"
                })
                score -= 30
            
            tracker.add_custom_metric("security_checks", 1)
            tracker.add_custom_metric("files_analyzed", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "file_path": file_path,
                "security_score": score,
                "security_issues": security_issues,
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
    
    def generate_code(self, template: str, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Genera código basado en template y contexto.
        
        Args:
            template: Template de código
            context: Contexto para el template
            
        Returns:
            Dict con código generado y métricas
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
            
            # Simular generación de código
            time.sleep(0.25)
            
            query_time = (time.time() - query_start) * 1000  # ms
            
            # Estimar tokens consumidos por el agente LLM para esta operación
            # Estimación: ~1200 tokens para generación de código (más complejo)
            llm_tokens_consumed = 1200
            tracker.add_llm_tokens(llm_tokens_consumed, "generate_code", query_time)
            tracker.add_query_time(query_time, "generate_code")
            
            generated_code = f"# Generated code\n{template}"
            
            tracker.add_custom_metric("code_generated", 1)
            tracker.add_custom_metric("files_analyzed", 1)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "generated_code": generated_code,
                "template": template,
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
    agent = BackendAgent()
    
    # Ejemplo de uso
    print("Testing Backend Agent...")
    
    # Validar código
    result = agent.validate_code("app/backend/services/internal/user_service.py")
    print(f"Validation status: {result['status']}")
    print(f"Errors: {len(result['errors'])}, Warnings: {len(result['warnings'])}")
    
    # Validar endpoints
    endpoints = ["/api/users", "/api/conversations", "/api/messages"]
    result = agent.validate_endpoints(endpoints)
    print(f"Endpoints validated: {result['total_endpoints']}")
    
    # Verificar seguridad
    result = agent.check_security("app/backend/database/connection.py")
    print(f"Security score: {result['security_score']}")
    
    # Generar código
    result = agent.generate_code("def {function_name}(): pass", {"function_name": "test"})
    print(f"Code generated: {len(result['generated_code'])} chars")


if __name__ == "__main__":
    main()

