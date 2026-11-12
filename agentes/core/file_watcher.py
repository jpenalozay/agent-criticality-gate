"""
Sistema de File Watchers para activación automática de agentes.

Este módulo monitorea archivos del proyecto y activa automáticamente
los agentes correspondientes cuando se detectan cambios en archivos
monitoreados según la configuración de cada agente.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Callable
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
import fnmatch

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
    FILE_WATCHER_AVAILABLE = True  # Alias para compatibilidad
except ImportError:
    WATCHDOG_AVAILABLE = False
    FILE_WATCHER_AVAILABLE = False
    # Crear clases dummy para evitar errores de importación
    class FileSystemEventHandler:
        pass
    class FileSystemEvent:
        pass
    class Observer:
        pass


@dataclass
class AgentFileConfig:
    """Configuración de monitoreo de archivos para un agente."""
    agent_id: str
    patterns: List[str]
    specific_files: List[str]
    exclude_patterns: List[str]
    directories: List[str]
    triggers: Dict[str, bool]
    debounce_ms: int = 2000
    enabled: bool = True


class AgentFileWatcher(FileSystemEventHandler):
    """
    Watcher de archivos para un agente específico.
    
    Monitorea archivos según la configuración del agente y activa
    el agente cuando se detectan cambios relevantes.
    """
    
    def __init__(
        self,
        agent_id: str,
        config: AgentFileConfig,
        activation_callback: Callable[[str, str], None],
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el watcher para un agente.
        
        Args:
            agent_id: ID del agente
            config: Configuración de monitoreo
            activation_callback: Función a llamar cuando se activa el agente
            logger: Logger opcional
        """
        self.agent_id = agent_id
        self.config = config
        self.activation_callback = activation_callback
        self.logger = logger or logging.getLogger(f"watcher.{agent_id}")
        
        # Cache de archivos monitoreados para evitar procesamiento repetido
        self.monitored_files: Set[str] = set()
        
        # Sistema de debounce para evitar múltiples activaciones
        self.last_activation: Dict[str, float] = {}
        self.lock = Lock()
        
        # Compilar patrones de exclusión
        self.exclude_patterns = [fnmatch.translate(p) for p in config.exclude_patterns]
    
    def _should_monitor_file(self, file_path: str) -> bool:
        """
        Verifica si un archivo debe ser monitoreado.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            True si debe ser monitoreado, False en caso contrario
        """
        # Normalizar path
        normalized_path = str(Path(file_path).resolve())
        
        # Verificar exclusiones primero
        for exclude_pattern in self.exclude_patterns:
            if fnmatch.fnmatch(normalized_path, exclude_pattern):
                return False
        
        # Verificar archivos específicos
        for specific in self.config.specific_files:
            specific_path = str(Path(specific).resolve())
            if normalized_path == specific_path or normalized_path.endswith(specific_path):
                return True
        
        # Verificar patrones
        for pattern in self.config.patterns:
            # Convertir patrón glob a formato fnmatch
            # Ejemplo: "app/backend/**/*.py" -> "app/backend/*/*.py" o "app/backend/**/*.py"
            pattern_normalized = pattern.replace("**/", "*/").replace("/**", "/*")
            if fnmatch.fnmatch(normalized_path, pattern_normalized):
                return True
        
        return False
    
    def _should_trigger(self, event_type: str) -> bool:
        """
        Verifica si el tipo de evento debe activar el agente.
        
        Args:
            event_type: Tipo de evento ('created', 'modified', 'deleted')
            
        Returns:
            True si debe activar, False en caso contrario
        """
        trigger_map = {
            'created': 'on_file_created' if 'on_file_created' in self.config.triggers else 'file_created',
            'modified': 'on_file_modified' if 'on_file_modified' in self.config.triggers else 'file_modified',
            'deleted': 'on_file_deleted' if 'on_file_deleted' in self.config.triggers else 'file_deleted',
        }
        
        trigger_key = trigger_map.get(event_type)
        if trigger_key:
            return self.config.triggers.get(trigger_key, False)
        
        return False
    
    def _debounce_check(self, file_path: str) -> bool:
        """
        Verifica si debe activar el agente considerando debounce.
        
        Args:
            file_path: Ruta del archivo
            
        Returns:
            True si debe activar, False si está en período de debounce
        """
        current_time = time.time()
        
        with self.lock:
            last_time = self.last_activation.get(file_path, 0)
            debounce_seconds = self.config.debounce_ms / 1000.0
            
            if current_time - last_time < debounce_seconds:
                return False
            
            self.last_activation[file_path] = current_time
            return True
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Se llama cuando se crea un archivo."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if self._should_monitor_file(file_path) and self._should_trigger('created'):
            if self._debounce_check(file_path):
                self.logger.info(f"📁 Archivo creado: {file_path} -> Activando {self.agent_id}")
                self.activation_callback(self.agent_id, file_path)
    
    def on_modified(self, event: FileSystemEvent) -> None:
        """Se llama cuando se modifica un archivo."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if self._should_monitor_file(file_path) and self._should_trigger('modified'):
            if self._debounce_check(file_path):
                self.logger.info(f"✏️ Archivo modificado: {file_path} -> Activando {self.agent_id}")
                self.activation_callback(self.agent_id, file_path)
    
    def on_deleted(self, event: FileSystemEvent) -> None:
        """Se llama cuando se elimina un archivo."""
        if event.is_directory:
            return
        
        file_path = event.src_path
        if self._should_monitor_file(file_path) and self._should_trigger('deleted'):
            if self._debounce_check(file_path):
                self.logger.info(f"🗑️ Archivo eliminado: {file_path} -> Activando {self.agent_id}")
                self.activation_callback(self.agent_id, file_path)


class FileWatcherManager:
    """
    Gestor centralizado de file watchers para todos los agentes.
    
    Carga la configuración de cada agente y crea watchers individuales
    para monitorear los archivos relevantes.
    """
    
    def __init__(
        self,
        specs_dir: str = "agentes/specs/agents",
        root_dir: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Inicializa el gestor de watchers.
        
        Args:
            specs_dir: Directorio donde están los archivos JSON de configuración
            root_dir: Directorio raíz del proyecto (default: directorio actual)
            logger: Logger opcional
        """
        if not WATCHDOG_AVAILABLE:
            raise ImportError("Biblioteca 'watchdog' no está instalada. Instala con: pip install watchdog")
        
        self.specs_dir = Path(specs_dir)
        self.root_dir = Path(root_dir) if root_dir else Path.cwd()
        self.logger = logger or logging.getLogger("FileWatcherManager")
        
        self.observers: List[Observer] = []
        self.watchers: Dict[str, AgentFileWatcher] = {}
        self.agent_configs: Dict[str, AgentFileConfig] = {}
        
        # Callback para activación de agentes
        self.activation_callback: Optional[Callable[[str, str], None]] = None
    
    def load_agent_config(self, agent_id: str) -> Optional[AgentFileConfig]:
        """
        Carga la configuración de monitoreo de un agente.
        
        Args:
            agent_id: ID del agente
            
        Returns:
            Configuración del agente o None si no se encuentra
        """
        config_file = self.specs_dir / f"{agent_id}_agent.json"
        
        if not config_file.exists():
            self.logger.warning(f"⚠️ Archivo de configuración no encontrado: {config_file}")
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Verificar si el agente está habilitado
            if not config_data.get("enabled", True):
                self.logger.info(f"⏸️ Agente {agent_id} está deshabilitado")
                return None
            
            monitoring = config_data.get("monitoring", {})
            files_config = monitoring.get("files", {})
            triggers = monitoring.get("triggers", {})
            
            return AgentFileConfig(
                agent_id=agent_id,
                patterns=files_config.get("patterns", []),
                specific_files=files_config.get("specific", []),
                exclude_patterns=files_config.get("exclude", []),
                directories=monitoring.get("directories", []),
                triggers=triggers,
                debounce_ms=triggers.get("debounce_ms", 2000),
                enabled=True
            )
        except Exception as e:
            self.logger.error(f"❌ Error cargando configuración de {agent_id}: {e}")
            return None
    
    def load_all_agent_configs(self) -> Dict[str, AgentFileConfig]:
        """
        Carga la configuración de todos los agentes disponibles.
        
        Returns:
            Diccionario con configuraciones de agentes
        """
        configs = {}
        
        # Lista de agentes conocidos
        agent_ids = [
            "db", "backend", "frontend", "performance",
            "openai", "whatsapp", "code_quality", "tests", "master"
        ]
        
        for agent_id in agent_ids:
            config = self.load_agent_config(agent_id)
            if config:
                configs[agent_id] = config
        
        self.logger.info(f"✅ Configuraciones cargadas: {len(configs)} agentes")
        return configs
    
    def setup_watcher(self, agent_id: str, config: AgentFileConfig) -> bool:
        """
        Configura un watcher para un agente.
        
        Args:
            agent_id: ID del agente
            config: Configuración de monitoreo
            
        Returns:
            True si se configuró correctamente, False en caso contrario
        """
        if not config.enabled:
            return False
        
        # Crear watcher
        watcher = AgentFileWatcher(
            agent_id=agent_id,
            config=config,
            activation_callback=self._on_file_change,
            logger=self.logger
        )
        
        # Crear observer
        observer = Observer()
        
        # Agregar directorios a observar
        directories_added = 0
        for directory in config.directories:
            dir_path = self.root_dir / directory
            if dir_path.exists() and dir_path.is_dir():
                observer.schedule(watcher, str(dir_path), recursive=True)
                directories_added += 1
                self.logger.debug(f"📂 Monitoreando directorio: {dir_path}")
            else:
                self.logger.warning(f"⚠️ Directorio no encontrado: {dir_path}")
        
        # Si no hay directorios específicos, monitorear directorio raíz
        if directories_added == 0:
            observer.schedule(watcher, str(self.root_dir), recursive=True)
            self.logger.info(f"📂 Monitoreando directorio raíz: {self.root_dir}")
        
        self.watchers[agent_id] = watcher
        self.observers.append(observer)
        
        self.logger.info(f"✅ Watcher configurado para {agent_id}")
        return True
    
    def _on_file_change(self, agent_id: str, file_path: str) -> None:
        """
        Callback llamado cuando se detecta un cambio en un archivo.
        
        Args:
            agent_id: ID del agente a activar
            file_path: Ruta del archivo que cambió
        """
        if self.activation_callback:
            try:
                self.activation_callback(agent_id, file_path)
            except Exception as e:
                self.logger.error(f"❌ Error en callback de activación para {agent_id}: {e}")
        else:
            self.logger.warning(f"⚠️ No hay callback configurado para activar {agent_id}")
    
    def set_activation_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Establece el callback para activar agentes cuando se detectan cambios.
        
        Args:
            callback: Función que recibe (agent_id, file_path)
        """
        self.activation_callback = callback
    
    def start(self) -> None:
        """Inicia todos los watchers."""
        if not self.watchers:
            self.logger.warning("⚠️ No hay watchers configurados")
            return
        
        for observer in self.observers:
            observer.start()
        
        self.logger.info(f"🚀 File watchers iniciados: {len(self.observers)} observers activos")
    
    def stop(self) -> None:
        """Detiene todos los watchers."""
        for observer in self.observers:
            observer.stop()
            observer.join()
        
        self.logger.info("🛑 File watchers detenidos")
    
    def setup_all_watchers(self) -> int:
        """
        Configura watchers para todos los agentes disponibles.
        
        Returns:
            Número de watchers configurados
        """
        configs = self.load_all_agent_configs()
        self.agent_configs = configs
        
        watchers_setup = 0
        for agent_id, config in configs.items():
            if self.setup_watcher(agent_id, config):
                watchers_setup += 1
        
        return watchers_setup


def activate_agent(agent_id: str, file_path: str) -> None:
    """
    Función de ejemplo para activar un agente.
    
    Esta función debe ser reemplazada por la lógica real de activación
    de agentes según la arquitectura del proyecto.
    
    Args:
        agent_id: ID del agente a activar
        file_path: Archivo que causó la activación
    """
    print(f"🤖 Activando agente: {agent_id}")
    print(f"   Archivo: {file_path}")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    
    # Aquí iría la lógica real de activación del agente
    # Por ejemplo:
    # from agentes.implementations import get_agent_by_id
    # agent = get_agent_by_id(agent_id)
    # agent.process_file_change(file_path)


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger("main")
    
    try:
        # Crear gestor de watchers
        manager = FileWatcherManager()
        
        # Configurar callback de activación
        manager.set_activation_callback(activate_agent)
        
        # Configurar todos los watchers
        watchers_count = manager.setup_all_watchers()
        
        if watchers_count == 0:
            logger.error("❌ No se configuraron watchers. Verifica las configuraciones.")
            exit(1)
        
        logger.info(f"✅ {watchers_count} watchers configurados")
        
        # Iniciar monitoreo
        manager.start()
        
        logger.info("👀 Monitoreando archivos... (Ctrl+C para detener)")
        
        # Mantener ejecución
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n🛑 Deteniendo watchers...")
            manager.stop()
            logger.info("✅ Watchers detenidos")
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        exit(1)

