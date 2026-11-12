#!/usr/bin/env python3
"""
Script principal de inicialización del Sistema de Agentes.

Este script verifica e inicia todos los servicios necesarios para que
el Master Agent esté completamente operativo.

Ejecuta:
    python agentes/main.py
    # o
    python -m agentes.main
"""

import sys
import time
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple

# Agregar el directorio raíz al path
_root_dir = Path(__file__).parent.parent if Path(__file__).parent.name == "agentes" else Path.cwd()
if str(_root_dir) not in sys.path:
    sys.path.insert(0, str(_root_dir))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("agentes.main")


class SystemChecker:
    """Verificador del sistema de agentes."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        # Determinar directorio raíz correctamente
        if Path(__file__).parent.name == "agentes":
            self.root_dir = Path(__file__).parent.parent
        else:
            self.root_dir = Path.cwd()
        self.docker_dir = self.root_dir / "agentes" / "docker"
    
    def check_python_version(self) -> bool:
        """Verifica versión de Python."""
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 9):
            self.errors.append(f"Python 3.9+ requerido. Tienes {version.major}.{version.minor}")
            return False
        logger.info(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    
    def check_dependencies(self) -> bool:
        """Verifica dependencias Python."""
        required = [
            ("redis", "redis"),
            ("watchdog", "watchdog"),
            ("psutil", "psutil"),
        ]
        
        missing = []
        for module_name, package_name in required:
            try:
                __import__(module_name)
                logger.info(f"✅ {package_name} instalado")
            except ImportError:
                missing.append(package_name)
                self.errors.append(f"Falta instalar: {package_name}")
        
        if missing:
            logger.error(f"❌ Falta instalar: {', '.join(missing)}")
            logger.info(f"💡 Ejecuta: pip install {' '.join(missing)}")
            return False
        
        return True
    
    def check_docker_available(self) -> bool:
        """Verifica que Docker esté disponible."""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✅ Docker disponible: {result.stdout.strip()}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        self.warnings.append("Docker no está disponible. Redis debe estar corriendo manualmente.")
        return False
    
    def check_docker_compose_available(self) -> bool:
        """Verifica que Docker Compose esté disponible."""
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"✅ Docker Compose disponible: {result.stdout.strip()}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        self.warnings.append("Docker Compose no está disponible.")
        return False
    
    def check_redis_running(self) -> Tuple[bool, bool]:
        """
        Verifica si Redis está corriendo.
        
        Returns:
            (está_corriendo, está_en_docker)
        """
        # Intentar conectar a Redis
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=2)
            r.ping()
            logger.info("✅ Redis está corriendo y accesible")
            
            # Verificar si está en Docker
            docker_running = self._check_redis_in_docker()
            return True, docker_running
        except Exception as e:
            logger.warning(f"⚠️ Redis no está accesible: {e}")
            return False, False
    
    def _check_redis_in_docker(self) -> bool:
        """Verifica si Redis está corriendo en Docker."""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=chatbot_redis", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "chatbot_redis" in result.stdout
        except Exception:
            return False
    
    def start_redis_docker(self) -> bool:
        """Inicia Redis usando Docker Compose."""
        if not self.docker_dir.exists():
            logger.error(f"❌ Directorio Docker no encontrado: {self.docker_dir}")
            return False
        
        logger.info("🚀 Iniciando Redis con Docker Compose...")
        try:
            result = subprocess.run(
                ["docker-compose", "up", "-d", "redis"],
                cwd=self.docker_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info("✅ Redis iniciado correctamente")
                # Esperar a que Redis esté listo
                time.sleep(3)
                return True
            else:
                logger.error(f"❌ Error iniciando Redis: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"❌ Error ejecutando Docker Compose: {e}")
            return False
    
    def check_redis_connection(self) -> bool:
        """Verifica conexión a Redis desde Python."""
        try:
            from agentes.core.redis_communication import RedisConnectionManager
            manager = RedisConnectionManager.get_instance()
            if manager.is_available():
                logger.info("✅ Conexión Redis funcionando desde Python")
                return True
            else:
                # Intentar reconectar
                manager._connect()
                if manager.is_available():
                    logger.info("✅ Conexión Redis funcionando desde Python (reconectado)")
                    return True
                else:
                    self.errors.append("Redis no está disponible desde Python")
                    logger.error("❌ Redis no está disponible desde Python")
                    return False
        except Exception as e:
            logger.error(f"❌ Error verificando Redis: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self.errors.append(f"Error verificando Redis: {e}")
            return False
    
    def check_agent_configs(self) -> bool:
        """Verifica que existan las configuraciones de agentes."""
        specs_dir = self.root_dir / "agentes" / "specs" / "agents"
        required_agents = [
            "master_agent.json",
            "db_agent.json",
            "backend_agent.json",
            "frontend_agent.json"
        ]
        
        missing = []
        for agent_file in required_agents:
            if not (specs_dir / agent_file).exists():
                missing.append(agent_file)
        
        if missing:
            self.errors.append(f"Faltan configuraciones: {', '.join(missing)}")
            return False
        
        logger.info("✅ Configuraciones de agentes encontradas")
        return True
    
    def check_env_file(self) -> bool:
        """Verifica archivo .env."""
        env_file = self.root_dir / ".env"
        if not env_file.exists():
            self.warnings.append("Archivo .env no encontrado. Se usarán valores por defecto.")
            return False
        
        logger.info("✅ Archivo .env encontrado")
        return True
    
    def check_file_watchers(self) -> bool:
        """Verifica que el módulo de file watchers esté disponible."""
        try:
            from agentes.core.file_watcher import FILE_WATCHER_AVAILABLE
            if FILE_WATCHER_AVAILABLE:
                logger.info("✅ File watchers disponibles")
                return True
            else:
                self.warnings.append("File watchers no disponibles (watchdog no instalado)")
                return False
        except Exception as e:
            self.warnings.append(f"Error verificando file watchers: {e}")
            return False


class AgentOrchestrator:
    """Orquestador principal del sistema de agentes."""
    
    def __init__(self):
        self.checker = SystemChecker()
        self.file_watcher_process = None
    
    def initialize(self) -> bool:
        """Inicializa todo el sistema."""
        logger.info("=" * 60)
        logger.info("🚀 INICIALIZANDO SISTEMA DE AGENTES")
        logger.info("=" * 60)
        logger.info("")
        
        # 1. Verificar Python
        logger.info("📋 Verificando Python...")
        if not self.checker.check_python_version():
            return False
        
        # 2. Verificar dependencias
        logger.info("")
        logger.info("📦 Verificando dependencias...")
        if not self.checker.check_dependencies():
            return False
        
        # 3. Verificar Docker
        logger.info("")
        logger.info("🐳 Verificando Docker...")
        docker_available = self.checker.check_docker_available()
        docker_compose_available = self.checker.check_docker_compose_available()
        
        # 4. Verificar/iniciar Redis
        logger.info("")
        logger.info("🔴 Verificando Redis...")
        redis_running, redis_in_docker = self.checker.check_redis_running()
        
        if not redis_running:
            if docker_available and docker_compose_available:
                logger.info("")
                logger.info("🚀 Iniciando Redis con Docker Compose...")
                if not self.checker.start_redis_docker():
                    self.checker.errors.append("No se pudo iniciar Redis")
                    return False
                redis_running = True
            else:
                self.checker.errors.append("Redis no está corriendo y Docker no está disponible")
                logger.error("❌ Redis no está corriendo")
                logger.error("💡 Inicia Redis manualmente o instala Docker")
                return False
        
        # 5. Verificar conexión Redis
        logger.info("")
        logger.info("🔌 Verificando conexión Redis...")
        if not self.checker.check_redis_connection():
            return False
        
        # 6. Verificar configuraciones
        logger.info("")
        logger.info("📄 Verificando configuraciones...")
        if not self.checker.check_agent_configs():
            return False
        
        # 7. Verificar .env
        logger.info("")
        logger.info("⚙️ Verificando archivo .env...")
        self.checker.check_env_file()
        
        # 8. Verificar file watchers
        logger.info("")
        logger.info("👀 Verificando file watchers...")
        self.checker.check_file_watchers()
        
        # 9. Iniciar file watchers
        logger.info("")
        logger.info("🚀 Iniciando file watchers...")
        self.start_file_watchers()
        
        # 10. Iniciar procesador de comandos Master Agent
        logger.info("")
        logger.info("📥 Iniciando procesador de comandos Master Agent...")
        self.start_command_processor()
        
        # Resumen
        logger.info("")
        logger.info("=" * 60)
        if self.checker.errors:
            logger.error("❌ ERRORES ENCONTRADOS:")
            for error in self.checker.errors:
                logger.error(f"   - {error}")
            logger.info("")
            logger.error("❌ El sistema no está completamente operativo")
            return False
        
        if self.checker.warnings:
            logger.warning("⚠️ ADVERTENCIAS:")
            for warning in self.checker.warnings:
                logger.warning(f"   - {warning}")
            logger.info("")
        
        logger.info("✅ SISTEMA LISTO PARA USAR")
        logger.info("")
        logger.info("=" * 60)
        logger.info("")
        logger.info("🎉 Master Agent está listo para recibir comandos!")
        logger.info("")
        logger.info("💬 En Cursor, escribe:")
        logger.info('   "Master Agent, analiza la arquitectura del proyecto"')
        logger.info('   "Master Agent, coordina los agentes DB y Backend"')
        logger.info('   "Master Agent, ¿cuál es el estado de todos los agentes?"')
        logger.info("")
        logger.info("📖 Para más información:")
        logger.info("   Ver: docs/GUIA_INICIO_RAPIDO.md")
        logger.info("")
        logger.info("=" * 60)
        logger.info("")
        logger.info("⚠️  Presiona Ctrl+C para detener el sistema")
        logger.info("")
        
        return True
    
    def start_command_processor(self) -> None:
        """Inicia el procesador de comandos Master Agent."""
        try:
            from agentes.core.command_processor import MasterAgentCommandProcessor
            
            self.command_processor = MasterAgentCommandProcessor()
            self.command_processor.start_processing()
            logger.info("✅ Procesador de comandos iniciado")
        except Exception as e:
            logger.warning(f"⚠️ Error iniciando procesador de comandos: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def start_file_watchers(self) -> None:
        """Inicia file watchers en segundo plano."""
        try:
            from agentes.core.file_watcher import FILE_WATCHER_AVAILABLE
            if not FILE_WATCHER_AVAILABLE:
                logger.warning("⚠️ File watchers no disponibles (watchdog no instalado)")
                return
            
            logger.info("   Iniciando file watchers...")
            # Importar y configurar file watchers
            from agentes.core.agent_activation import start_file_watchers
            manager = start_file_watchers(use_custom_activation=True)
            
            if manager and len(manager.watchers) > 0:
                logger.info(f"✅ File watchers iniciados ({len(manager.watchers)} agentes monitoreados)")
                self.file_watcher_manager = manager
            else:
                logger.warning("⚠️ No se pudieron iniciar file watchers")
        except Exception as e:
            logger.warning(f"⚠️ Error iniciando file watchers: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def run(self) -> None:
        """Ejecuta el orquestador."""
        if not self.initialize():
            logger.error("")
            logger.error("❌ El sistema no se pudo inicializar correctamente")
            logger.error("   Revisa los errores arriba y corrige los problemas")
            sys.exit(1)
        
        # Mantener ejecución
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("")
            logger.info("🛑 Deteniendo sistema...")
            self.shutdown()
    
    def shutdown(self) -> None:
        """Detiene todos los servicios."""
        logger.info("")
        logger.info("🔴 Deteniendo procesador de comandos...")
        if hasattr(self, 'command_processor'):
            try:
                self.command_processor.stop_processing()
                logger.info("✅ Procesador de comandos detenido")
            except Exception as e:
                logger.warning(f"⚠️ Error deteniendo procesador de comandos: {e}")
        
        logger.info("")
        logger.info("🔴 Deteniendo file watchers...")
        if hasattr(self, 'file_watcher_manager'):
            try:
                self.file_watcher_manager.stop()
                logger.info("✅ File watchers detenidos")
            except Exception as e:
                logger.warning(f"⚠️ Error deteniendo file watchers: {e}")
        
        logger.info("")
        logger.info("✅ Sistema detenido")
        logger.info("")


def main():
    """Función principal."""
    orchestrator = AgentOrchestrator()
    orchestrator.run()


if __name__ == "__main__":
    main()

