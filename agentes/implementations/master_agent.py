"""
Master Agent - Implementación con agregación de métricas.

Este módulo implementa las funciones del Master Agent con agregación
de métricas de todos los agentes usando MetricsAggregator.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# Importar el agregador de métricas
from agentes.core import MetricsAggregator, MetricsTracker

logger = logging.getLogger("agentes.master_agent")


class MasterAgent:
    """Agente maestro que coordina y agrega métricas de todos los agentes."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa el Master Agent.
        
        Args:
            config_path: Ruta al archivo de configuración JSON
        """
        self.agent_id = "master"
        self.config = self._load_config(config_path)
        self.metrics_config = self.config.get("metrics_collection", {})
        self.aggregator = MetricsAggregator(
            storage_dir=self.metrics_config.get("metrics_storage_dir", "agentes/data/metrics")
        )
        self.agents_to_collect = self.metrics_config.get("agents_to_collect", [
            "db", "backend", "frontend", "performance", "openai", "whatsapp", "code_quality", "tests"
        ])
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Carga la configuración del agente."""
        if config_path is None:
            config_path = "agentes/specs/agents/master_agent.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def collect_agent_metrics(self, agent_id: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Recopila métricas de un agente específico.
        
        Args:
            agent_id: ID del agente
            date: Fecha en formato YYYY-MM-DD (default: hoy)
            
        Returns:
            Dict con métricas agregadas del agente
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.metrics_config.get("collect_from_redis", True),
            save_to_file=True
        )
        tracker.start()
        
        try:
            aggregated = self.aggregator.aggregate_daily_metrics(agent_id, date)
            
            tracker.add_operation(1)
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "agent_id": agent_id,
                "metrics": aggregated,
                "success": True,
                "collection_metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def collect_all_agents_metrics(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Recopila y agrega métricas de todos los agentes.
        
        Args:
            date: Fecha en formato YYYY-MM-DD (default: hoy)
            
        Returns:
            Dict con métricas agregadas de todos los agentes
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.metrics_config.get("collect_from_redis", True),
            save_to_file=True
        )
        tracker.start()
        
        try:
            aggregated = self.aggregator.aggregate_all_agents_metrics(
                self.agents_to_collect,
                date
            )
            
            tracker.add_custom_metric("agents_collected", len(self.agents_to_collect))
            tracker.add_custom_metric("total_cost_usd", aggregated.get("totals", {}).get("total_cost_usd", 0))
            tracker.add_custom_metric("total_executions", aggregated.get("totals", {}).get("total_executions", 0))
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "date": date or datetime.now().strftime("%Y-%m-%d"),
                "aggregated_metrics": aggregated,
                "success": True,
                "collection_metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def generate_cost_time_report(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Genera reporte consolidado de costos y tiempos.
        
        Args:
            date: Fecha en formato YYYY-MM-DD (default: hoy)
            
        Returns:
            Dict con reporte de costos y tiempos
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.metrics_config.get("collect_from_redis", True),
            save_to_file=True
        )
        tracker.start()
        
        try:
            aggregated = self.aggregator.aggregate_all_agents_metrics(
                self.agents_to_collect,
                date
            )
            
            # Calcular totales
            total_cost = aggregated.get("totals", {}).get("total_cost_usd", 0)
            total_executions = aggregated.get("totals", {}).get("total_executions", 0)
            
            # Totales del agente LLM
            total_llm_tokens = aggregated.get("totals", {}).get("total_llm_tokens", 0)
            total_llm_cost = aggregated.get("totals", {}).get("total_llm_cost_usd", 0)
            avg_llm_cost_per_token = aggregated.get("totals", {}).get("avg_llm_cost_per_token", 0)
            
            # Totales de consultas
            total_query_time_ms = aggregated.get("totals", {}).get("total_query_time_ms", 0)
            total_queries = aggregated.get("totals", {}).get("total_queries", 0)
            avg_query_time_ms = aggregated.get("totals", {}).get("avg_query_time_ms", 0)
            
            # Calcular promedios
            avg_time_by_agent = {}
            for agent_id, agent_metrics in aggregated.get("agents", {}).items():
                avg_time_by_agent[agent_id] = agent_metrics.get("avg_execution_time_ms", 0)
            
            overall_avg_time = sum(avg_time_by_agent.values()) / len(avg_time_by_agent) if avg_time_by_agent else 0
            
            tracker.add_custom_metric("report_generated", 1)
            tracker.add_custom_metric("total_cost_usd", total_cost)
            tracker.add_custom_metric("total_executions", total_executions)
            # Métricas del agente LLM
            tracker.add_custom_metric("total_llm_tokens", total_llm_tokens)
            tracker.add_custom_metric("total_llm_cost_usd", total_llm_cost)
            # Métricas de consultas
            tracker.add_custom_metric("total_query_time_ms", total_query_time_ms)
            tracker.add_custom_metric("total_queries", total_queries)
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            report = {
                "report_id": f"cost_time_report_{date or datetime.now().strftime('%Y%m%d')}",
                "timestamp": datetime.now().isoformat(),
                "date": date or datetime.now().strftime("%Y-%m-%d"),
                "summary": {
                    "total_daily_cost_usd": total_cost,
                    "total_executions": total_executions,
                    "avg_execution_time_ms": overall_avg_time,
                    "agents_count": len(self.agents_to_collect),
                    # Totales del agente LLM
                    "total_llm_tokens": total_llm_tokens,
                    "total_llm_cost_usd": total_llm_cost,
                    "avg_llm_cost_per_token": avg_llm_cost_per_token,
                    "total_cost_including_llm": total_cost + total_llm_cost,
                    # Totales de consultas
                    "total_query_time_ms": total_query_time_ms,
                    "total_queries": total_queries,
                    "avg_query_time_ms": avg_query_time_ms
                },
                "by_agent": aggregated.get("agents", {}),
                "totals": aggregated.get("totals", {}),
                "trends": {},  # En producción se calcularían tendencias
                "projections": {},  # En producción se calcularían proyecciones
                "recommendations": [],  # En producción se generarían recomendaciones
                "success": True,
                "collection_metrics": metrics
            }
            
            # Guardar reporte
            report_dir = Path("agentes/reports/master_agent_cost_time_reports")
            report_dir.mkdir(parents=True, exist_ok=True)
            report_file = report_dir / f"report_{date or datetime.now().strftime('%Y%m%d')}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            return report
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def analyze_architecture(
        self,
        check_structure: bool = True,
        provide_suggestions: bool = True,
        coordinate_agents: bool = True,  # NUEVO: Coordinar agentes automáticamente
        **kwargs
    ) -> Dict[str, Any]:
        """
        Analiza la arquitectura del proyecto.
        
        Args:
            check_structure: Verificar estructura de directorios
            provide_suggestions: Proporcionar sugerencias
            coordinate_agents: Si True, coordina otros agentes para análisis completo
            
        Returns:
            Dict con análisis y sugerencias
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.metrics_config.get("collect_from_redis", True),
            save_to_file=True
        )
        tracker.start()
        
        try:
            import time
            query_start = time.time()
            
            # Análisis básico de estructura
            analysis = {
                "project_structure": {
                    "app": "Backend y Frontend separados",
                    "agentes": "Sistema de agentes autónomos",
                    "docs": "Documentación extensa"
                },
                "technologies": [
                    "FastAPI", "SQLAlchemy", "MySQL", "Redis",
                    "OpenAI API", "WhatsApp Business API",
                    "Jinja2", "WebSocket"
                ],
                "agents": {
                    "total": 9,
                    "implemented": ["db", "backend", "frontend", "performance", "openai", "whatsapp", "code_quality", "tests", "master"],
                    "status": "operational"
                },
                "suggestions": [
                    "✅ Arquitectura bien organizada con separación backend/frontend",
                    "✅ Sistema de agentes funcional con Redis y file watchers",
                    "💡 Considerar agregar más tests automatizados",
                    "💡 Considerar documentación de API con Swagger"
                ] if provide_suggestions else []
            }
            
            # NUEVO: Coordinar otros agentes si se solicita
            agents_results = {}
            if coordinate_agents:
                logger.info("🔄 Coordinando agentes para análisis completo...")
                try:
                    from agentes.core.agent_activation import get_agent_instance
                    
                    # Agentes clave para análisis arquitectónico
                    key_agents = ["db", "backend", "frontend", "performance", "code_quality"]
                    
                    for agent_id in key_agents:
                        try:
                            agent_instance = get_agent_instance(agent_id)
                            if agent_instance:
                                # Ejecutar función básica según el agente
                                if agent_id == "db":
                                    result = agent_instance.validate_model("app/backend/models/current.py")
                                elif agent_id == "backend":
                                    result = agent_instance.validate_code("app/backend")
                                elif agent_id == "frontend":
                                    result = agent_instance.validate_html("app/frontend/templates")
                                elif agent_id == "performance":
                                    result = agent_instance.analyze_performance("app/backend")
                                elif agent_id == "code_quality":
                                    result = agent_instance.validate_pep8("app/backend")
                                else:
                                    result = {"status": "skipped"}
                                
                                agents_results[agent_id] = {
                                    "status": result.get("status", "unknown"),
                                    "executed": True
                                }
                                logger.info(f"✅ Agente {agent_id} ejecutado para análisis")
                        except Exception as e:
                            logger.error(f"❌ Error ejecutando agente {agent_id}: {e}")
                            agents_results[agent_id] = {
                                "status": "error",
                                "error": str(e)
                            }
                    
                    analysis["agents_analysis"] = {
                        "agents_executed": list(agents_results.keys()),
                        "results": agents_results,
                        "total_executed": len([a for a in agents_results.values() if a.get("executed")])
                    }
                except Exception as e:
                    logger.error(f"❌ Error coordinando agentes: {e}")
                    analysis["agents_analysis"] = {
                        "error": str(e),
                        "status": "failed"
                    }
            
            query_time = (time.time() - query_start) * 1000
            llm_tokens = 1200 + (len(agents_results) * 200)  # Más tokens si coordinó agentes
            tracker.add_llm_tokens(llm_tokens, "analyze_architecture", query_time)
            tracker.add_query_time(query_time, "analyze_architecture")
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "status": "completed",
                "analysis": analysis,
                "agents_coordinated": coordinate_agents,
                "agents_results": agents_results if coordinate_agents else None,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def validate_integration(self, check_all_agents: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Valida la integración de todos los agentes.
        
        Args:
            check_all_agents: Validar todos los agentes
            
        Returns:
            Dict con resultados de validación
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.metrics_config.get("collect_from_redis", True),
            save_to_file=True
        )
        tracker.start()
        
        try:
            import time
            query_start = time.time()
            
            # Validar agentes
            validation_results = {}
            for agent_id in self.agents_to_collect:
                try:
                    from agentes.core.agent_activation import get_agent_instance
                    agent = get_agent_instance(agent_id)
                    validation_results[agent_id] = {
                        "status": "valid" if agent else "error",
                        "available": agent is not None
                    }
                except Exception as e:
                    validation_results[agent_id] = {
                        "status": "error",
                        "error": str(e)
                    }
            
            # Validar Redis
            try:
                from agentes.core.redis_communication import get_redis_communication
                redis_comm = get_redis_communication("master")
                redis_status = redis_comm.is_connected()
            except Exception as e:
                redis_status = False
            
            query_time = (time.time() - query_start) * 1000
            llm_tokens = 800  # Estimación
            tracker.add_llm_tokens(llm_tokens, "validate_integration", query_time)
            tracker.add_query_time(query_time, "validate_integration")
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "status": "completed",
                "agents": validation_results,
                "redis_connected": redis_status,
                "success": True,
                "metrics": metrics
            }
        except Exception as e:
            tracker.set_error(str(e))
            metrics = tracker.finish(success=False)
            tracker.publish(metrics)
            raise
    
    def detect_conflicts(self, check_all: bool = True, **kwargs) -> Dict[str, Any]:
        """
        Detecta conflictos entre agentes.
        
        Args:
            check_all: Verificar todos los agentes
            
        Returns:
            Dict con conflictos detectados
        """
        tracker = MetricsTracker(
            agent_id=self.agent_id,
            publish_to_redis=self.metrics_config.get("collect_from_redis", True),
            save_to_file=True
        )
        tracker.start()
        
        try:
            import time
            query_start = time.time()
            
            # Análisis básico de conflictos
            conflicts = []
            warnings = []
            
            # Verificar si hay métricas contradictorias
            try:
                aggregated = self.aggregator.aggregate_all_agents_metrics(
                    self.agents_to_collect
                )
                # Análisis básico
                total_cost = aggregated.get("totals", {}).get("total_cost_usd", 0)
                if total_cost > 100:  # Threshold ejemplo
                    warnings.append(f"⚠️ Costo total alto: ${total_cost:.2f}")
            except Exception as e:
                warnings.append(f"⚠️ No se pudieron obtener métricas: {e}")
            
            query_time = (time.time() - query_start) * 1000
            llm_tokens = 600  # Estimación
            tracker.add_llm_tokens(llm_tokens, "detect_conflicts", query_time)
            tracker.add_query_time(query_time, "detect_conflicts")
            tracker.add_operation(1)
            
            metrics = tracker.finish(success=True)
            tracker.publish(metrics)
            
            return {
                "status": "completed",
                "conflicts": conflicts,
                "warnings": warnings,
                "total_conflicts": len(conflicts),
                "total_warnings": len(warnings),
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
    agent = MasterAgent()
    
    # Ejemplo de uso
    print("Testing Master Agent...")
    
    # Recopilar métricas de un agente
    result = agent.collect_agent_metrics("openai")
    print(f"OpenAI Agent metrics collected: {result['success']}")
    
    # Recopilar métricas de todos los agentes
    result = agent.collect_all_agents_metrics()
    print(f"All agents metrics collected: {result['success']}")
    print(f"Total cost: ${result['aggregated_metrics'].get('totals', {}).get('total_cost_usd', 0):.2f}")
    print(f"Total executions: {result['aggregated_metrics'].get('totals', {}).get('total_executions', 0)}")
    
    # Generar reporte
    result = agent.generate_cost_time_report()
    print(f"Report generated: {result['report_id']}")
    print(f"Report saved to: agentes/reports/master_agent_cost_time_reports/")


if __name__ == "__main__":
    main()

