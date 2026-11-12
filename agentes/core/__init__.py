"""
Módulo principal de métricas para agentes.

Este módulo debe ser importado por todos los agentes para trackear métricas.
"""

from .metrics_tracker import MetricsTracker, AgentMetrics, MetricsAggregator
from .metrics_utils import track_execution, ContextManagerMetricsTracker

# Importar file watcher si está disponible
try:
    from .file_watcher import FileWatcherManager, AgentFileWatcher, AgentFileConfig
    from .agent_activation import (
        activate_agent_on_file_change,
        get_agent_instance,
        start_file_watchers
    )
    FILE_WATCHER_AVAILABLE = True
except ImportError:
    FILE_WATCHER_AVAILABLE = False
    FileWatcherManager = None
    AgentFileWatcher = None
    AgentFileConfig = None
    activate_agent_on_file_change = None
    get_agent_instance = None
    start_file_watchers = None

# Importar comunicación Redis
try:
    from .redis_communication import (
        RedisConnectionManager,
        AgentRedisCommunication,
        get_redis_communication
    )
    REDIS_COMMUNICATION_AVAILABLE = True
except ImportError:
    REDIS_COMMUNICATION_AVAILABLE = False
    RedisConnectionManager = None
    AgentRedisCommunication = None
    get_redis_communication = None

# Importar procesador de comandos
try:
    from .command_processor import MasterAgentCommandProcessor
    COMMAND_PROCESSOR_AVAILABLE = True
except ImportError:
    COMMAND_PROCESSOR_AVAILABLE = False
    MasterAgentCommandProcessor = None

__all__ = [
    "MetricsTracker",
    "AgentMetrics",
    "MetricsAggregator",
    "track_execution",
    "ContextManagerMetricsTracker",
    "FileWatcherManager",
    "AgentFileWatcher",
    "AgentFileConfig",
    "activate_agent_on_file_change",
    "get_agent_instance",
    "start_file_watchers",
    "FILE_WATCHER_AVAILABLE",
    "RedisConnectionManager",
    "AgentRedisCommunication",
    "get_redis_communication",
    "REDIS_COMMUNICATION_AVAILABLE",
    "MasterAgentCommandProcessor",
    "COMMAND_PROCESSOR_AVAILABLE"
]

