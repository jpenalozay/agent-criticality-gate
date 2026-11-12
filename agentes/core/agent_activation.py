"""
Integración de file watchers con agentes.

Este módulo proporciona funciones para activar agentes automáticamente
cuando se detectan cambios en archivos monitoreados.
"""

import logging
from typing import Dict, Optional
from pathlib import Path

from agentes.core.file_watcher import FileWatcherManager, activate_agent as default_activate

logger = logging.getLogger("agentes.activation")


# Cache de instancias de agentes
_agent_instances: Dict[str, any] = {}


def get_agent_instance(agent_id: str):
    """
    Obtiene o crea una instancia de un agente.
    
    Args:
        agent_id: ID del agente
        
    Returns:
        Instancia del agente o None si no se encuentra
    """
    global _agent_instances
    
    if agent_id in _agent_instances:
        return _agent_instances[agent_id]
    
    try:
        # Importar según el agente
        if agent_id == "db":
            from agentes.implementations.db_agent import DBAgent
            agent = DBAgent()
        elif agent_id == "backend":
            from agentes.implementations.backend_agent import BackendAgent
            agent = BackendAgent()
        elif agent_id == "frontend":
            from agentes.implementations.frontend_agent import FrontendAgent
            agent = FrontendAgent()
        elif agent_id == "performance":
            from agentes.implementations.performance_agent import PerformanceAgent
            agent = PerformanceAgent()
        elif agent_id == "openai":
            from agentes.implementations.openai_agent import OpenAIAgent
            agent = OpenAIAgent()
        elif agent_id == "whatsapp":
            from agentes.implementations.whatsapp_agent import WhatsAppAgent
            agent = WhatsAppAgent()
        elif agent_id == "code_quality":
            from agentes.implementations.code_quality_agent import CodeQualityAgent
            agent = CodeQualityAgent()
        elif agent_id == "tests":
            from agentes.implementations.tests_agent import TestsAgent
            agent = TestsAgent()
        elif agent_id == "master":
            from agentes.implementations.master_agent import MasterAgent
            agent = MasterAgent()
        else:
            logger.warning(f"⚠️ Agente desconocido: {agent_id}")
            return None
        
        _agent_instances[agent_id] = agent
        logger.info(f"✅ Instancia creada para agente: {agent_id}")
        return agent
        
    except Exception as e:
        logger.error(f"❌ Error creando instancia de {agent_id}: {e}")
        return None


def activate_agent_on_file_change(agent_id: str, file_path: str) -> None:
    """
    Activa un agente cuando se detecta un cambio en un archivo.
    
    Esta función determina qué función del agente debe ejecutarse
    basándose en el tipo de archivo y la configuración del agente.
    
    Args:
        agent_id: ID del agente a activar
        file_path: Ruta del archivo que cambió
    """
    logger.info(f"🔄 Activando {agent_id} por cambio en: {file_path}")
    
    agent = get_agent_instance(agent_id)
    if not agent:
        logger.error(f"❌ No se pudo obtener instancia del agente: {agent_id}")
        return
    
    file_path_obj = Path(file_path)
    file_extension = file_path_obj.suffix.lower()
    
    try:
        # Determinar qué función ejecutar según el tipo de archivo y agente
        if agent_id == "db":
            if file_extension == ".py":
                if "models" in file_path or "model" in file_path.lower():
                    result = agent.validate_model(str(file_path))
                    logger.info(f"✅ DB Agent: Validación de modelo completada")
                elif "database" in file_path or "connection" in file_path.lower():
                    result = agent.validate_model(str(file_path))
                    logger.info(f"✅ DB Agent: Validación de conexión completada")
            elif file_extension == ".sql":
                logger.info(f"📝 DB Agent: Archivo SQL detectado - {file_path}")
        
        elif agent_id == "backend":
            if file_extension == ".py":
                result = agent.validate_code(str(file_path))
                logger.info(f"✅ Backend Agent: Validación de código completada")
        
        elif agent_id == "frontend":
            if file_extension == ".html":
                result = agent.validate_html(str(file_path))
                logger.info(f"✅ Frontend Agent: Validación HTML completada")
            elif file_extension == ".css":
                result = agent.validate_css(str(file_path))
                logger.info(f"✅ Frontend Agent: Validación CSS completada")
            elif file_extension == ".js":
                result = agent.validate_javascript(str(file_path))
                logger.info(f"✅ Frontend Agent: Validación JS completada")
        
        elif agent_id == "performance":
            if file_extension == ".py":
                result = agent.analyze_performance(str(file_path))
                logger.info(f"✅ Performance Agent: Análisis completado")
        
        elif agent_id == "openai":
            if file_extension == ".py" and "openai" in file_path.lower():
                result = agent.validate_integration()
                logger.info(f"✅ OpenAI Agent: Validación completada")
        
        elif agent_id == "whatsapp":
            if file_extension == ".py" and "whatsapp" in file_path.lower():
                result = agent.validate_integration()
                logger.info(f"✅ WhatsApp Agent: Validación completada")
        
        elif agent_id == "code_quality":
            if file_extension == ".py":
                result = agent.validate_pep8(str(file_path))
                logger.info(f"✅ Code Quality Agent: Validación PEP8 completada")
        
        elif agent_id == "tests":
            if file_extension == ".py" and ("test" in file_path.lower() or "tests" in file_path):
                logger.info(f"🧪 Tests Agent: Archivo de test detectado")
                # No ejecutar tests automáticamente, solo notificar
        
        elif agent_id == "master":
            logger.info(f"👑 Master Agent: Cambio detectado, coordinando...")
            # El Master Agent puede coordinar otros agentes
        
        logger.info(f"✅ Agente {agent_id} procesado exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando {agent_id}: {e}", exc_info=True)


def start_file_watchers(
    specs_dir: str = "agentes/specs/agents",
    root_dir: Optional[str] = None,
    use_custom_activation: bool = True
) -> FileWatcherManager:
    """
    Inicia el sistema de file watchers para todos los agentes.
    
    Args:
        specs_dir: Directorio de especificaciones de agentes
        root_dir: Directorio raíz del proyecto
        use_custom_activation: Si True, usa activate_agent_on_file_change
        
    Returns:
        Instancia del FileWatcherManager
    """
    manager = FileWatcherManager(specs_dir=specs_dir, root_dir=root_dir)
    
    # Configurar callback de activación
    if use_custom_activation:
        manager.set_activation_callback(activate_agent_on_file_change)
    else:
        manager.set_activation_callback(default_activate)
    
    # Configurar todos los watchers
    watchers_count = manager.setup_all_watchers()
    
    if watchers_count > 0:
        logger.info(f"✅ {watchers_count} watchers configurados")
        manager.start()
        logger.info("🚀 File watchers iniciados")
    else:
        logger.warning("⚠️ No se configuraron watchers")
    
    return manager

