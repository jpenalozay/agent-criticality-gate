"""
Event Bus

Sistema de eventos para comunicación entre componentes del framework.
Soporta publicación/suscripción y persistencia de eventos.
"""

import logging
import json
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Tipos de eventos del framework."""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    
    RISK_CALCULATED = "risk_calculated"
    RISK_RECALCULATED = "risk_recalculated"
    
    HUMAN_APPROVAL_REQUESTED = "human_approval_requested"
    HUMAN_APPROVAL_RECEIVED = "human_approval_received"
    
    CODE_GENERATED = "code_generated"
    CODE_VALIDATED = "code_validated"
    
    TEST_EXECUTED = "test_executed"
    TEST_PASSED = "test_passed"
    TEST_FAILED = "test_failed"
    
    DEPLOYMENT_READY = "deployment_ready"


class Event:
    """Representa un evento en el sistema."""
    
    def __init__(
        self,
        event_type: EventType,
        task_id: str,
        agent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Crea un nuevo evento.
        
        Args:
            event_type: Tipo de evento
            task_id: ID de la tarea relacionada
            agent_id: ID del agente que generó el evento (opcional)
            data: Datos adicionales del evento
            timestamp: Timestamp del evento (default: now)
        """
        self.event_type = event_type
        self.task_id = task_id
        self.agent_id = agent_id
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el evento a diccionario."""
        return {
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Event':
        """Crea un evento desde un diccionario."""
        return Event(
            event_type=EventType(data["event_type"]),
            task_id=data["task_id"],
            agent_id=data.get("agent_id"),
            data=data.get("data", {}),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )
    
    def __repr__(self) -> str:
        return (
            f"Event(type={self.event_type.value}, task={self.task_id}, "
            f"agent={self.agent_id}, time={self.timestamp.isoformat()})"
        )


class EventBus:
    """Bus de eventos para el framework."""
    
    def __init__(self):
        """Inicializa el event bus."""
        self.subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.event_history: List[Event] = []
        self.max_history = 1000
    
    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """
        Suscribe un handler a un tipo de evento.
        
        Args:
            event_type: Tipo de evento a escuchar
            handler: Función que maneja el evento
        """
        self.subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler to {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """
        Desuscribe un handler de un tipo de evento.
        
        Args:
            event_type: Tipo de evento
            handler: Handler a remover
        """
        if handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)
            logger.debug(f"Unsubscribed handler from {event_type.value}")
    
    def publish(self, event: Event):
        """
        Publica un evento a todos los suscriptores.
        
        Args:
            event: Evento a publicar
        """
        logger.info(f"Publishing event: {event}")
        
        # Agregar a historial
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        # Notificar suscriptores
        handlers = self.subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}", exc_info=True)
    
    def publish_dict(
        self,
        event_type: EventType,
        task_id: str,
        agent_id: Optional[str] = None,
        **data
    ):
        """
        Publica un evento desde datos simples.
        
        Args:
            event_type: Tipo de evento
            task_id: ID de la tarea
            agent_id: ID del agente (opcional)
            **data: Datos adicionales del evento
        """
        event = Event(
            event_type=event_type,
            task_id=task_id,
            agent_id=agent_id,
            data=data
        )
        self.publish(event)
    
    def get_events(
        self,
        task_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        agent_id: Optional[str] = None
    ) -> List[Event]:
        """
        Obtiene eventos filtrados.
        
        Args:
            task_id: Filtrar por task ID
            event_type: Filtrar por tipo de evento
            agent_id: Filtrar por agent ID
            
        Returns:
            Lista de eventos que cumplen los filtros
        """
        events = self.event_history
        
        if task_id:
            events = [e for e in events if e.task_id == task_id]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]
        
        return events
    
    def clear_history(self):
        """Limpia el historial de eventos."""
        self.event_history.clear()
        logger.info("Event history cleared")


# Singleton global
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Obtiene el event bus global (singleton)."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def set_event_bus(bus: EventBus):
    """Establece el event bus global."""
    global _global_event_bus
    _global_event_bus = bus
