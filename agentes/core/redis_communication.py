"""
Sistema de comunicación Redis para agentes.

Este módulo proporciona comunicación en tiempo real entre agentes usando Redis,
con fallback automático a archivos si Redis no está disponible.
"""

import json
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time

logger = logging.getLogger("agentes.redis_communication")

# Intentar importar Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class RedisConnectionManager:
    """
    Gestor de conexión a Redis con fallback automático.
    """
    
    _instance: Optional['RedisConnectionManager'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        """Inicializa el gestor de conexión."""
        self.redis_client: Optional[Any] = None
        self.redis_available: bool = False
        self._connect()
    
    def _connect(self) -> None:
        """Intenta conectar a Redis."""
        if not REDIS_AVAILABLE:
            logger.warning("⚠️ Redis no está instalado. Usando modo archivo.")
            return
        
        try:
            # Intentar obtener configuración desde config.py
            try:
                from app.backend.core.config import settings
                redis_host = settings.redis.HOST
                redis_port = settings.redis.PORT
                redis_db = settings.redis.DB
                redis_password = settings.redis.PASSWORD
            except Exception as e:
                # Valores por defecto si no se puede obtener configuración
                logger.debug(f"No se pudo obtener configuración de Redis desde settings: {e}")
                redis_host = 'localhost'
                redis_port = 6379
                redis_db = 0
                redis_password = None
            
            # Crear cliente Redis
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
                health_check_interval=30
            )
            
            # Test de conexión
            self.redis_client.ping()
            self.redis_available = True
            logger.info(f"✅ Conectado a Redis: {redis_host}:{redis_port}/{redis_db}")
        
        except Exception as e:
            logger.warning(f"⚠️ Redis no disponible: {e}. Usando modo archivo.")
            self.redis_client = None
            self.redis_available = False
    
    @classmethod
    def get_instance(cls) -> 'RedisConnectionManager':
        """Obtiene instancia singleton del gestor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get_client(self) -> Optional[Any]:
        """Obtiene el cliente Redis o None si no está disponible."""
        if not self.redis_available or self.redis_client is None:
            return None
        
        # Verificar conexión
        try:
            self.redis_client.ping()
            return self.redis_client
        except Exception:
            logger.warning("⚠️ Conexión Redis perdida. Reintentando...")
            self._connect()
            return self.redis_client if self.redis_available else None
    
    def is_available(self) -> bool:
        """Verifica si Redis está disponible."""
        return self.redis_available and self.get_client() is not None


class AgentRedisCommunication:
    """
    Gestor de comunicación Redis para un agente específico.
    
    Proporciona:
    - Pub/Sub para comunicación en tiempo real
    - Almacenamiento de estado
    - Triggers y notificaciones
    - Locks para coordinación
    - Colas de tareas
    """
    
    def __init__(
        self,
        agent_id: str,
        redis_manager: Optional[RedisConnectionManager] = None,
        fallback_dir: str = "agentes/communication"
    ):
        """
        Inicializa comunicación Redis para un agente.
        
        Args:
            agent_id: ID del agente
            redis_manager: Gestor de Redis (opcional, usa singleton si None)
            fallback_dir: Directorio para fallback a archivos
        """
        self.agent_id = agent_id
        self.redis_manager = redis_manager or RedisConnectionManager.get_instance()
        self.fallback_dir = Path(fallback_dir)
        self.fallback_dir.mkdir(parents=True, exist_ok=True)
        
        # Pub/Sub
        self.pubsub: Optional[Any] = None
        self.subscribed_channels: List[str] = []
        self.message_handlers: Dict[str, Callable] = {}
        
        # Thread para escuchar mensajes
        self.listener_thread: Optional[threading.Thread] = None
        self.listening = False
    
    def _get_redis(self) -> Optional[Any]:
        """Obtiene cliente Redis o None."""
        return self.redis_manager.get_client()
    
    def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """
        Publica un mensaje a un canal Redis.
        
        Args:
            channel: Canal Redis
            message: Mensaje a publicar
            
        Returns:
            True si se publicó, False si fallback a archivo
        """
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                message_json = json.dumps(message, ensure_ascii=False)
                redis_client.publish(channel, message_json)
                logger.debug(f"📤 Publicado a {channel}: {message.get('type', 'message')}")
                return True
            except Exception as e:
                logger.error(f"❌ Error publicando a Redis: {e}")
                return self._publish_to_file(channel, message)
        else:
            return self._publish_to_file(channel, message)
    
    def _publish_to_file(self, channel: str, message: Dict[str, Any]) -> bool:
        """Fallback: publica mensaje a archivo."""
        try:
            # Crear estructura de archivo
            file_data = {
                "channel": channel,
                "timestamp": datetime.now().isoformat(),
                "agent_id": self.agent_id,
                "message": message
            }
            
            # Nombre de archivo basado en canal
            safe_channel = channel.replace(":", "_").replace("*", "all")
            filename = f"{safe_channel}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.fallback_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(file_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"📁 Mensaje guardado en archivo: {filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando mensaje en archivo: {e}")
            return False
    
    def subscribe(self, channels: List[str], handler: Callable[[str, Dict[str, Any]], None]) -> bool:
        """
        Se suscribe a canales Redis.
        
        Args:
            channels: Lista de canales a escuchar
            handler: Función que maneja mensajes recibidos
            
        Returns:
            True si se suscribió correctamente
        """
        redis_client = self._get_redis()
        
        if not redis_client:
            logger.warning("⚠️ Redis no disponible. No se puede suscribir.")
            return False
        
        try:
            if self.pubsub is None:
                self.pubsub = redis_client.pubsub()
            
            # Suscribirse a canales
            for channel in channels:
                if channel not in self.subscribed_channels:
                    self.pubsub.subscribe(channel)
                    self.subscribed_channels.append(channel)
                    logger.info(f"📡 Suscrito a canal: {channel}")
            
            # Guardar handler
            for channel in channels:
                self.message_handlers[channel] = handler
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error suscribiéndose a canales: {e}")
            return False
    
    def start_listening(self) -> None:
        """Inicia thread para escuchar mensajes."""
        if self.listening or self.pubsub is None:
            return
        
        self.listening = True
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listener_thread.start()
        logger.info(f"👂 Escuchando mensajes Redis para {self.agent_id}")
    
    def stop_listening(self) -> None:
        """Detiene el listener."""
        self.listening = False
        if self.pubsub:
            try:
                self.pubsub.unsubscribe()
                self.pubsub.close()
            except Exception:
                pass
        logger.info(f"🛑 Detenido listener Redis para {self.agent_id}")
    
    def _listen_loop(self) -> None:
        """Loop principal para escuchar mensajes."""
        while self.listening:
            try:
                if self.pubsub:
                    message = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    
                    if message and message['type'] == 'message':
                        channel = message['channel']
                        try:
                            data = json.loads(message['data'])
                            # Llamar handler si existe
                            if channel in self.message_handlers:
                                self.message_handlers[channel](channel, data)
                            else:
                                # Handler por defecto
                                logger.debug(f"📥 Mensaje recibido en {channel}: {data.get('type', 'unknown')}")
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ Error decodificando mensaje: {e}")
                
                time.sleep(0.1)  # Pequeño delay para no consumir CPU
            
            except Exception as e:
                if self.listening:  # Solo loguear si aún estamos escuchando
                    logger.error(f"❌ Error en listener Redis: {e}")
                time.sleep(1)
    
    # ==================== ESTADO ====================
    
    def set_status(self, status: str, task_id: Optional[str] = None, **kwargs) -> bool:
        """
        Establece el estado del agente.
        
        Args:
            status: Estado del agente (active, idle, processing, error)
            task_id: ID de tarea actual (opcional)
            **kwargs: Datos adicionales
            
        Returns:
            True si se guardó correctamente
        """
        status_data = {
            "agent_id": self.agent_id,
            "status": status,
            "task_id": task_id,
            "last_activity": datetime.now().isoformat(),
            **kwargs
        }
        
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                key = f"agent:status:{self.agent_id}"
                redis_client.hset(key, mapping=status_data)
                redis_client.expire(key, 7200)  # TTL 2 horas
                
                # Notificar cambio de estado
                self.publish("agent:all:status", {
                    "type": "status_update",
                    **status_data
                })
                
                logger.debug(f"✅ Estado actualizado: {self.agent_id} -> {status}")
                return True
            except Exception as e:
                logger.error(f"❌ Error guardando estado en Redis: {e}")
        
        # Fallback a archivo
        return self._save_status_to_file(status_data)
    
    def get_status(self, agent_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado de un agente.
        
        Args:
            agent_id: ID del agente (default: self.agent_id)
            
        Returns:
            Estado del agente o None
        """
        agent = agent_id or self.agent_id
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                key = f"agent:status:{agent}"
                status = redis_client.hgetall(key)
                return status if status else None
            except Exception:
                pass
        
        # Fallback: leer de archivo
        return self._load_status_from_file(agent)
    
    def _save_status_to_file(self, status_data: Dict[str, Any]) -> bool:
        """Guarda estado en archivo."""
        try:
            filename = f"{self.agent_id}_status.json"
            filepath = self.fallback_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando estado en archivo: {e}")
            return False
    
    def _load_status_from_file(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Carga estado desde archivo."""
        try:
            filename = f"{agent_id}_status.json"
            filepath = self.fallback_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return None
    
    # ==================== TRIGGERS ====================
    
    def create_trigger(self, event_type: str, file_path: str, data: Optional[Dict[str, Any]] = None) -> str:
        """
        Crea un trigger para el agente.
        
        Args:
            event_type: Tipo de evento (file_modified, file_created, etc.)
            file_path: Ruta del archivo
            data: Datos adicionales
            
        Returns:
            ID del trigger creado
        """
        trigger_id = f"{self.agent_id}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{id(self)}"
        
        trigger_data = {
            "trigger_id": trigger_id,
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "event_type": event_type,
            "file_path": file_path,
            "data": data or {},
            "status": "pending"
        }
        
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                # Guardar trigger
                key = f"agent:triggers:{trigger_id}"
                redis_client.hset(key, mapping=trigger_data)
                redis_client.expire(key, 3600)  # TTL 1 hora
                
                # Publicar trigger
                channel = f"agent:{self.agent_id}:trigger"
                self.publish(channel, {
                    "type": "trigger",
                    **trigger_data
                })
                
                logger.info(f"✅ Trigger creado: {trigger_id}")
                return trigger_id
            except Exception as e:
                logger.error(f"❌ Error creando trigger en Redis: {e}")
        
        # Fallback a archivo
        self._save_trigger_to_file(trigger_data)
        return trigger_id
    
    def _save_trigger_to_file(self, trigger_data: Dict[str, Any]) -> None:
        """Guarda trigger en archivo."""
        try:
            filename = f"{self.agent_id}_trigger_{trigger_data['trigger_id']}.json"
            filepath = self.fallback_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(trigger_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Error guardando trigger: {e}")
    
    # ==================== LOCKS ====================
    
    def acquire_lock(self, lock_name: str, timeout: int = 300) -> bool:
        """
        Adquiere un lock distribuido.
        
        Args:
            lock_name: Nombre del lock
            timeout: Tiempo de expiración en segundos
            
        Returns:
            True si adquirió el lock, False si ya está tomado
        """
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                key = f"lock:{lock_name}"
                # Intentar adquirir lock (SET con NX y EX)
                result = redis_client.set(key, self.agent_id, nx=True, ex=timeout)
                if result:
                    logger.debug(f"🔒 Lock adquirido: {lock_name}")
                return bool(result)
            except Exception as e:
                logger.error(f"❌ Error adquiriendo lock: {e}")
        
        # Fallback: usar archivo de lock (básico)
        return self._acquire_file_lock(lock_name)
    
    def release_lock(self, lock_name: str) -> bool:
        """
        Libera un lock.
        
        Args:
            lock_name: Nombre del lock
            
        Returns:
            True si se liberó correctamente
        """
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                key = f"lock:{lock_name}"
                # Verificar que somos el dueño del lock
                current_owner = redis_client.get(key)
                if current_owner == self.agent_id:
                    redis_client.delete(key)
                    logger.debug(f"🔓 Lock liberado: {lock_name}")
                    return True
                else:
                    logger.warning(f"⚠️ No se puede liberar lock {lock_name}: no somos el dueño")
                    return False
            except Exception as e:
                logger.error(f"❌ Error liberando lock: {e}")
        
        # Fallback: liberar lock de archivo
        return self._release_file_lock(lock_name)
    
    def _acquire_file_lock(self, lock_name: str) -> bool:
        """Adquiere lock usando archivo."""
        lock_file = self.fallback_dir / f"lock_{lock_name}.lock"
        if lock_file.exists():
            return False
        
        try:
            lock_file.write_text(self.agent_id)
            return True
        except Exception:
            return False
    
    def _release_file_lock(self, lock_name: str) -> bool:
        """Libera lock de archivo."""
        lock_file = self.fallback_dir / f"lock_{lock_name}.lock"
        try:
            if lock_file.exists() and lock_file.read_text() == self.agent_id:
                lock_file.unlink()
                return True
        except Exception:
            pass
        return False
    
    # ==================== COLAS ====================
    
    def push_task(self, queue_name: str, task_data: Dict[str, Any]) -> bool:
        """
        Agrega una tarea a una cola.
        
        Args:
            queue_name: Nombre de la cola
            task_data: Datos de la tarea
            
        Returns:
            True si se agregó correctamente
        """
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                queue_key = f"agent:queue:{queue_name}"
                task_json = json.dumps(task_data, ensure_ascii=False)
                redis_client.rpush(queue_key, task_json)
                logger.debug(f"📥 Tarea agregada a cola: {queue_name}")
                return True
            except Exception as e:
                logger.error(f"❌ Error agregando tarea a cola: {e}")
        
        # Fallback a archivo
        return self._save_task_to_file(queue_name, task_data)
    
    def pop_task(self, queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
        """
        Obtiene y remueve una tarea de la cola.
        
        Args:
            queue_name: Nombre de la cola
            timeout: Tiempo de espera en segundos (0 = no esperar)
            
        Returns:
            Datos de la tarea o None
        """
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                queue_key = f"agent:queue:{queue_name}"
                if timeout > 0:
                    result = redis_client.blpop(queue_key, timeout=timeout)
                    if result:
                        _, task_json = result
                        return json.loads(task_json)
                else:
                    task_json = redis_client.lpop(queue_key)
                    if task_json:
                        return json.loads(task_json)
            except Exception as e:
                logger.error(f"❌ Error obteniendo tarea de cola: {e}")
        
        # Fallback: leer de archivo
        return self._load_task_from_file(queue_name)
    
    def _save_task_to_file(self, queue_name: str, task_data: Dict[str, Any]) -> bool:
        """Guarda tarea en archivo."""
        try:
            filename = f"{queue_name}_queue.json"
            filepath = self.fallback_dir / filename
            
            # Leer tareas existentes
            tasks = []
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
            
            # Agregar nueva tarea
            tasks.append({
                "timestamp": datetime.now().isoformat(),
                **task_data
            })
            
            # Guardar
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando tarea: {e}")
            return False
    
    def _load_task_from_file(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Carga tarea desde archivo."""
        try:
            filename = f"{queue_name}_queue.json"
            filepath = self.fallback_dir / filename
            
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                
                if tasks:
                    # Remover primera tarea
                    task = tasks.pop(0)
                    
                    # Guardar lista actualizada
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(tasks, f, indent=2, ensure_ascii=False)
                    
                    return task
        except Exception:
            pass
        return None


def get_redis_communication(agent_id: str) -> AgentRedisCommunication:
    """
    Función de conveniencia para obtener comunicación Redis de un agente.
    
    Args:
        agent_id: ID del agente
        
    Returns:
        Instancia de AgentRedisCommunication
    """
    return AgentRedisCommunication(agent_id)

