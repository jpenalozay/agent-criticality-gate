"""
Módulo compartido para tracking de métricas de costos y tiempos por agente.

Este módulo proporciona una interfaz estandarizada para que todos los agentes
trackeen sus métricas de ejecución, costos y tiempos.
"""

import time
import json
import psutil
import os
from datetime import datetime
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class AgentMetrics:
    """Estructura estándar para métricas de un agente."""
    agent_id: str
    execution_id: str
    timestamp: str
    execution_time_ms: float
    cpu_time_ms: Optional[float] = None
    memory_mb: Optional[float] = None
    cost_usd: Optional[float] = None
    success: bool = True
    operations_count: Optional[int] = None
    custom_metrics: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    # Métricas del agente LLM (el agente mismo es un LLM)
    llm_tokens_used: Optional[int] = None  # Tokens consumidos por el agente LLM
    llm_cost_per_token: Optional[float] = None  # Costo por token del agente LLM
    llm_total_cost: Optional[float] = None  # Costo total del agente LLM
    query_times: Optional[List[float]] = None  # Tiempo de cada consulta/operación individual
    total_query_time_ms: Optional[float] = None  # Tiempo total de todas las consultas


class MetricsTracker:
    """
    Tracker de métricas para agentes.
    
    Uso:
        tracker = MetricsTracker(agent_id="db")
        tracker.start()
        # ... ejecutar operaciones ...
        tracker.add_custom_metric("queries_count", 5)
        tracker.add_cost(0.05)
        metrics = tracker.finish(success=True)
        tracker.publish()
    """
    
    def __init__(
        self,
        agent_id: str,
        execution_id: Optional[str] = None,
        publish_to_redis: bool = True,
        save_to_file: bool = True,
        storage_dir: Optional[str] = None
    ):
        """
        Inicializa el tracker de métricas.
        
        Args:
            agent_id: ID del agente (ej: "db", "openai")
            execution_id: ID único de ejecución (auto-generado si None)
            publish_to_redis: Si publicar a Redis
            save_to_file: Si guardar a archivo JSON
            storage_dir: Directorio para guardar métricas (default: agentes/data/metrics/)
        """
        self.agent_id = agent_id
        self.execution_id = execution_id or self._generate_execution_id()
        self.publish_to_redis = publish_to_redis
        self.save_to_file = save_to_file
        self.storage_dir = Path(storage_dir or "agentes/data/metrics")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Estado de tracking
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.start_cpu_time: Optional[float] = None
        self.start_memory: Optional[float] = None
        self.cost_usd: float = 0.0
        self.operations_count: int = 0
        self.custom_metrics: Dict[str, Any] = {}
        self.success: bool = True
        self.error_message: Optional[str] = None
        
        # Tracking del agente LLM (el agente mismo es un LLM)
        self.llm_tokens_used: int = 0  # Tokens consumidos por el agente LLM
        self.llm_cost_per_token: float = 0.000002  # Costo por token ($0.002 por 1K tokens)
        self.llm_operations: List[Dict[str, Any]] = []  # Lista de operaciones con tiempos
        
        # Proceso actual para tracking de recursos
        self.process = psutil.Process(os.getpid())
    
    def _generate_execution_id(self) -> str:
        """Genera un ID único de ejecución."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"{self.agent_id}_{timestamp}"
    
    def start(self) -> None:
        """Inicia el tracking de métricas."""
        self.start_time = time.time()
        self.start_cpu_time = time.process_time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
    
    def add_cost(self, cost: float) -> None:
        """Agrega costo en USD."""
        self.cost_usd += cost
    
    def add_operation(self, count: int = 1) -> None:
        """Incrementa el contador de operaciones."""
        self.operations_count += count
    
    def add_llm_tokens(self, tokens: int, operation_name: Optional[str] = None, query_time_ms: Optional[float] = None) -> None:
        """
        Agrega tokens consumidos por el agente LLM.
        
        Args:
            tokens: Número de tokens consumidos por esta operación
            operation_name: Nombre de la operación (opcional)
            query_time_ms: Tiempo de la consulta/operación en ms (opcional)
        """
        self.llm_tokens_used += tokens
        
        # Trackear operación individual
        if operation_name or query_time_ms:
            operation = {
                "operation_name": operation_name or "unknown",
                "tokens": tokens,
                "query_time_ms": query_time_ms,
                "timestamp": datetime.now().isoformat()
            }
            self.llm_operations.append(operation)
    
    def add_query_time(self, query_time_ms: float, operation_name: Optional[str] = None) -> None:
        """
        Agrega tiempo de una consulta/operación individual.
        
        Args:
            query_time_ms: Tiempo de la consulta en ms
            operation_name: Nombre de la operación (opcional)
        """
        if "query_times" not in self.custom_metrics:
            self.custom_metrics["query_times"] = []
        self.custom_metrics["query_times"].append({
            "time_ms": query_time_ms,
            "operation": operation_name or "unknown",
            "timestamp": datetime.now().isoformat()
        })
    
    def set_llm_cost_per_token(self, cost_per_token: float) -> None:
        """
        Configura el costo por token del agente LLM.
        
        Args:
            cost_per_token: Costo por token (default: $0.000002 por token)
        """
        self.llm_cost_per_token = cost_per_token
    
    def add_custom_metric(self, key: str, value: Any) -> None:
        """Agrega una métrica personalizada."""
        self.custom_metrics[key] = value
    
    def set_error(self, error_message: str) -> None:
        """Marca la ejecución como fallida con mensaje de error."""
        self.success = False
        self.error_message = error_message
    
    def finish(self, success: bool = True, error_message: Optional[str] = None) -> AgentMetrics:
        """
        Finaliza el tracking y retorna las métricas.
        
        Args:
            success: Si la ejecución fue exitosa
            error_message: Mensaje de error si falló
            
        Returns:
            AgentMetrics: Objeto con todas las métricas
        """
        if self.start_time is None:
            raise ValueError("Must call start() before finish()")
        
        self.end_time = time.time()
        self.success = success
        
        if error_message:
            self.set_error(error_message)
        
        # Calcular métricas
        execution_time_ms = (self.end_time - self.start_time) * 1000
        
        end_cpu_time = time.process_time()
        cpu_time_ms = (end_cpu_time - self.start_cpu_time) * 1000 if self.start_cpu_time else None
        
        end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_mb = end_memory - self.start_memory if self.start_memory else None
        
        # Calcular costo total del agente LLM
        llm_total_cost = None
        if self.llm_tokens_used > 0:
            llm_total_cost = self.llm_tokens_used * self.llm_cost_per_token
        
        # Calcular tiempo total de consultas
        query_times_list = []
        total_query_time_ms = None
        if self.llm_operations:
            query_times_list = [op.get("query_time_ms", 0) for op in self.llm_operations if op.get("query_time_ms")]
            if query_times_list:
                total_query_time_ms = sum(query_times_list)
        
        # Si hay query_times en custom_metrics, también sumarlos
        if "query_times" in self.custom_metrics:
            custom_query_times = [q.get("time_ms", 0) for q in self.custom_metrics["query_times"] if isinstance(q, dict)]
            if custom_query_times:
                if query_times_list:
                    query_times_list.extend(custom_query_times)
                else:
                    query_times_list = custom_query_times
                if total_query_time_ms:
                    total_query_time_ms += sum(custom_query_times)
                else:
                    total_query_time_ms = sum(custom_query_times)
        
        metrics = AgentMetrics(
            agent_id=self.agent_id,
            execution_id=self.execution_id,
            timestamp=datetime.now().isoformat(),
            execution_time_ms=execution_time_ms,
            cpu_time_ms=cpu_time_ms,
            memory_mb=memory_mb,
            cost_usd=self.cost_usd if self.cost_usd > 0 else None,
            success=self.success,
            operations_count=self.operations_count if self.operations_count > 0 else None,
            custom_metrics=self.custom_metrics if self.custom_metrics else None,
            error_message=self.error_message,
            # Métricas del agente LLM
            llm_tokens_used=self.llm_tokens_used if self.llm_tokens_used > 0 else None,
            llm_cost_per_token=self.llm_cost_per_token if self.llm_tokens_used > 0 else None,
            llm_total_cost=llm_total_cost,
            query_times=query_times_list if query_times_list else None,
            total_query_time_ms=total_query_time_ms
        )
        
        return metrics
    
    def publish(self, metrics: Optional[AgentMetrics] = None) -> None:
        """
        Publica las métricas a Redis y/o archivo.
        
        Args:
            metrics: Métricas a publicar (si None, llama finish() primero)
        """
        if metrics is None:
            metrics = self.finish()
        
        metrics_dict = asdict(metrics)
        
        # Publicar a Redis
        if self.publish_to_redis:
            self._publish_to_redis(metrics_dict)
        
        # Guardar a archivo
        if self.save_to_file:
            self._save_to_file(metrics_dict)
    
    def _publish_to_redis(self, metrics_dict: Dict[str, Any]) -> None:
        """Publica métricas a Redis."""
        try:
            from agentes.core.redis_communication import get_redis_communication
            
            redis_comm = get_redis_communication(self.agent_id)
            channel = f"agent:{self.agent_id}:metrics"
            redis_comm.publish(channel, {
                "type": "metrics",
                "execution_id": self.execution_id,
                **metrics_dict
            })
        except Exception as e:
            import logging
            logger = logging.getLogger("agentes.metrics_tracker")
            logger.debug(f"⚠️ Redis no disponible para publicar métricas: {e}")
    
    def _save_to_file(self, metrics_dict: Dict[str, Any]) -> None:
        """Guarda métricas a archivo JSON."""
        try:
            # Archivo por día
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = self.storage_dir / f"{self.agent_id}_metrics_{date_str}.json"
            
            # Cargar métricas existentes o crear lista nueva
            if filename.exists():
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []
            
            # Agregar nueva métrica
            data.append(metrics_dict)
            
            # Guardar
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando métricas a archivo: {e}")
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Obtiene métricas actuales sin finalizar el tracking.
        
        Returns:
            Dict con métricas parciales
        """
        if self.start_time is None:
            return {}
        
        current_time = time.time()
        execution_time_ms = (current_time - self.start_time) * 1000
        
        return {
            "agent_id": self.agent_id,
            "execution_id": self.execution_id,
            "execution_time_ms": execution_time_ms,
            "cost_usd": self.cost_usd,
            "operations_count": self.operations_count,
            "custom_metrics": self.custom_metrics.copy() if self.custom_metrics else {}
        }


class MetricsAggregator:
    """
    Agregador de métricas para el Master Agent.
    
    Recopila y agrega métricas de todos los agentes.
    """
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Inicializa el agregador.
        
        Args:
            storage_dir: Directorio donde están las métricas (default: agentes/data/metrics/)
        """
        self.storage_dir = Path(storage_dir or "agentes/data/metrics")
    
    def get_agent_metrics(
        self,
        agent_id: str,
        date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene métricas de un agente específico.
        
        Args:
            agent_id: ID del agente
            date: Fecha en formato YYYY-MM-DD (default: hoy)
            limit: Número máximo de métricas a retornar
            
        Returns:
            Lista de métricas del agente
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        filename = self.storage_dir / f"{agent_id}_metrics_{date}.json"
        
        if not filename.exists():
            return []
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data[-limit:]  # Últimas N métricas
        except Exception as e:
            print(f"⚠️ Error leyendo métricas: {e}")
            return []
    
    def aggregate_daily_metrics(
        self,
        agent_id: str,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Agrega métricas diarias de un agente.
        
        Args:
            agent_id: ID del agente
            date: Fecha en formato YYYY-MM-DD (default: hoy)
            
        Returns:
            Dict con métricas agregadas
        """
        metrics = self.get_agent_metrics(agent_id, date)
        
        if not metrics:
            return {
                "agent_id": agent_id,
                "date": date or datetime.now().strftime("%Y-%m-%d"),
                "total_executions": 0,
                "total_cost_usd": 0.0,
                "avg_execution_time_ms": 0.0,
                "success_rate": 0.0,
                "total_llm_tokens": 0,
                "total_llm_cost_usd": 0.0,
                "total_query_time_ms": 0.0,
                "avg_query_time_ms": 0.0
            }
        
        total_executions = len(metrics)
        total_cost = sum(m.get("cost_usd", 0) or 0 for m in metrics)
        total_time = sum(m.get("execution_time_ms", 0) for m in metrics)
        successful = sum(1 for m in metrics if m.get("success", True))
        
        # Agregar métricas del agente LLM
        total_llm_tokens = sum(m.get("llm_tokens_used", 0) or 0 for m in metrics)
        total_llm_cost = sum(m.get("llm_total_cost", 0) or 0 for m in metrics)
        
        # Agregar tiempos de consultas
        all_query_times = []
        for m in metrics:
            if m.get("query_times"):
                all_query_times.extend([q.get("time_ms", 0) if isinstance(q, dict) else q for q in m["query_times"]])
            elif m.get("total_query_time_ms"):
                all_query_times.append(m["total_query_time_ms"])
        
        total_query_time_ms = sum(all_query_times)
        avg_query_time_ms = total_query_time_ms / len(all_query_times) if all_query_times else 0.0
        
        return {
            "agent_id": agent_id,
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "total_executions": total_executions,
            "total_cost_usd": total_cost,
            "avg_execution_time_ms": total_time / total_executions if total_executions > 0 else 0.0,
            "min_execution_time_ms": min(m.get("execution_time_ms", 0) for m in metrics) if metrics else 0.0,
            "max_execution_time_ms": max(m.get("execution_time_ms", 0) for m in metrics) if metrics else 0.0,
            "success_rate": successful / total_executions if total_executions > 0 else 0.0,
            "total_operations": sum(m.get("operations_count", 0) or 0 for m in metrics),
            # Métricas del agente LLM
            "total_llm_tokens": total_llm_tokens,
            "total_llm_cost_usd": total_llm_cost,
            "avg_llm_cost_per_token": total_llm_cost / total_llm_tokens if total_llm_tokens > 0 else 0.0,
            # Métricas de consultas
            "total_query_time_ms": total_query_time_ms,
            "avg_query_time_ms": avg_query_time_ms,
            "total_queries": len(all_query_times),
            "min_query_time_ms": min(all_query_times) if all_query_times else 0.0,
            "max_query_time_ms": max(all_query_times) if all_query_times else 0.0
        }
    
    def aggregate_all_agents_metrics(
        self,
        agent_ids: List[str],
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Agrega métricas de todos los agentes.
        
        Args:
            agent_ids: Lista de IDs de agentes
            date: Fecha en formato YYYY-MM-DD (default: hoy)
            
        Returns:
            Dict con métricas agregadas de todos los agentes
        """
        aggregated = {}
        total_cost = 0.0
        total_executions = 0
        total_llm_tokens = 0
        total_llm_cost = 0.0
        total_query_time_ms = 0.0
        total_queries = 0
        
        for agent_id in agent_ids:
            agent_metrics = self.aggregate_daily_metrics(agent_id, date)
            aggregated[agent_id] = agent_metrics
            total_cost += agent_metrics["total_cost_usd"]
            total_executions += agent_metrics["total_executions"]
            total_llm_tokens += agent_metrics.get("total_llm_tokens", 0)
            total_llm_cost += agent_metrics.get("total_llm_cost_usd", 0)
            total_query_time_ms += agent_metrics.get("total_query_time_ms", 0)
            total_queries += agent_metrics.get("total_queries", 0)
        
        return {
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "agents": aggregated,
            "totals": {
                "total_cost_usd": total_cost,
                "total_executions": total_executions,
                "agents_count": len(agent_ids),
                # Totales del agente LLM
                "total_llm_tokens": total_llm_tokens,
                "total_llm_cost_usd": total_llm_cost,
                "avg_llm_cost_per_token": total_llm_cost / total_llm_tokens if total_llm_tokens > 0 else 0.0,
                # Totales de consultas
                "total_query_time_ms": total_query_time_ms,
                "total_queries": total_queries,
                "avg_query_time_ms": total_query_time_ms / total_queries if total_queries > 0 else 0.0
            }
        }

