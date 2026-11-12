"""
Listener para procesar comandos del Master Agent desde archivos JSON.

Este módulo monitorea el archivo master_agent_input.json y procesa
automáticamente los comandos cuando se crean o modifican.
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import threading

logger = logging.getLogger("agentes.command_processor")


class MasterAgentCommandProcessor:
    """
    Procesador de comandos para el Master Agent.
    
    Monitorea el archivo master_agent_input.json y procesa comandos
    cuando se detectan cambios.
    """
    
    def __init__(
        self,
        input_file: str = "agentes/communication/master_agent_input.json",
        output_file: str = "agentes/communication/master_agent_output.json",
        poll_interval: float = 1.0
    ):
        """
        Inicializa el procesador de comandos.
        
        Args:
            input_file: Archivo de entrada de comandos
            output_file: Archivo de salida de respuestas
            poll_interval: Intervalo de polling en segundos
        """
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval
        
        self.last_processed_time: float = 0
        self.last_processed_task_id: Optional[str] = None
        self.master_agent = None
        self.processing = False
        self.processor_thread: Optional[threading.Thread] = None
    
    def _get_master_agent(self):
        """Obtiene o crea instancia del Master Agent."""
        if self.master_agent is None:
            try:
                from agentes.implementations.master_agent import MasterAgent
                self.master_agent = MasterAgent()
                logger.info("✅ Master Agent instanciado")
            except Exception as e:
                logger.error(f"❌ Error creando Master Agent: {e}")
                return None
        return self.master_agent
    
    def process_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un comando del Master Agent.
        
        Args:
            command_data: Datos del comando
            
        Returns:
            Resultado del procesamiento
        """
        agent = self._get_master_agent()
        if not agent:
            return {
                "status": "error",
                "error": "Master Agent no disponible",
                "task_id": command_data.get("task_id")
            }
        
        command = command_data.get("command")
        parameters = command_data.get("parameters", {})
        task_id = command_data.get("task_id", "unknown")
        
        logger.info(f"📥 Procesando comando: {command} (task_id: {task_id})")
        
        try:
            # Ejecutar comando según tipo
            if command == "analyze_architecture":
                result = agent.analyze_architecture(**parameters)
                
            elif command == "coordinate_task":
                agents_required = parameters.get("agents_required", [])
                task_description = parameters.get("task_description", "")
                result = self._coordinate_agents(agent, agents_required, task_description)
                
            elif command == "validate_integration":
                result = agent.validate_integration(**parameters)
                
            elif command == "manage_agents":
                action = parameters.get("action", "status")
                result = self._manage_agents_status(agent)
                
            elif command == "generate_cost_time_report":
                date = parameters.get("date", "today")
                if date == "today":
                    date = None
                result = agent.generate_cost_time_report(date)
                
            elif command == "detect_conflicts":
                result = agent.detect_conflicts(**parameters)
                
            else:
                # Comando genérico - intentar coordinar tarea
                result = {
                    "status": "unknown_command",
                    "command": command,
                    "message": f"Comando '{command}' no reconocido. Usando coordinación genérica.",
                    "result": self._coordinate_agents(agent, ["all"], command_data.get("user_input", ""))
                }
            
            return {
                "task_id": task_id,
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "command": command,
                "result": result,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ Error procesando comando {command}: {e}", exc_info=True)
            return {
                "task_id": task_id,
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "command": command,
                "error": str(e),
                "success": False
            }
    
    def _coordinate_agents(self, agent: Any, agents_required: list, task_description: str) -> Dict[str, Any]:
        """
        Coordina múltiples agentes para una tarea.
        
        Args:
            agent: Instancia del Master Agent
            agents_required: Lista de agentes requeridos
            task_description: Descripción de la tarea
            
        Returns:
            Resultado de la coordinación
        """
        from agentes.core.agent_activation import get_agent_instance
        
        activated_agents = []
        results = {}
        
        # Si "all" está en la lista, activar todos los agentes
        if "all" in agents_required:
            agents_required = ["db", "backend", "frontend", "performance", "openai", "whatsapp", "code_quality", "tests"]
        
        logger.info(f"🔄 Coordinando agentes: {agents_required}")
        
        for agent_id in agents_required:
            try:
                agent_instance = get_agent_instance(agent_id)
                if agent_instance:
                    activated_agents.append(agent_id)
                    
                    # Ejecutar función básica según el agente
                    if agent_id == "db":
                        result = agent_instance.validate_model("app/backend/models/current.py")
                    elif agent_id == "backend":
                        result = agent_instance.validate_code("app/backend")
                    elif agent_id == "frontend":
                        result = agent_instance.validate_html("app/frontend/templates")
                    elif agent_id == "performance":
                        result = agent_instance.analyze_performance("app/backend")
                    elif agent_id == "openai":
                        result = agent_instance.validate_integration()
                    elif agent_id == "whatsapp":
                        result = agent_instance.validate_integration()
                    elif agent_id == "code_quality":
                        result = agent_instance.validate_pep8("app/backend")
                    elif agent_id == "tests":
                        result = {"status": "notified", "message": "Tests agent notified"}
                    else:
                        result = {"status": "unknown"}
                    
                    results[agent_id] = result
                    logger.info(f"✅ Agente {agent_id} ejecutado")
                    
            except Exception as e:
                logger.error(f"❌ Error ejecutando agente {agent_id}: {e}")
                results[agent_id] = {"status": "error", "error": str(e)}
        
        return {
            "status": "completed",
            "agents_activated": activated_agents,
            "task_description": task_description,
            "results": results,
            "total_agents": len(activated_agents)
        }
    
    def _manage_agents_status(self, agent: Any) -> Dict[str, Any]:
        """Obtiene el estado de todos los agentes."""
        from agentes.core.redis_communication import get_redis_communication
        
        agents_status = {}
        agent_ids = ["db", "backend", "frontend", "performance", "openai", "whatsapp", "code_quality", "tests", "master"]
        
        for agent_id in agent_ids:
            try:
                redis_comm = get_redis_communication(agent_id)
                status = redis_comm.get_status(agent_id)
                agents_status[agent_id] = status if status else {"status": "unknown"}
            except Exception as e:
                agents_status[agent_id] = {"status": "error", "error": str(e)}
        
        return {
            "status": "completed",
            "agents_status": agents_status,
            "total_agents": len(agent_ids)
        }
    
    def check_and_process(self) -> bool:
        """
        Verifica si hay un nuevo comando y lo procesa.
        
        Returns:
            True si procesó un comando, False en caso contrario
        """
        if not self.input_file.exists():
            return False
        
        try:
            # Leer archivo
            mtime = self.input_file.stat().st_mtime
            
            # Si ya procesamos este archivo, no hacer nada
            if mtime <= self.last_processed_time:
                return False
            
            with open(self.input_file, 'r', encoding='utf-8') as f:
                command_data = json.load(f)
            
            task_id = command_data.get("task_id")
            
            # Si ya procesamos este task_id, no hacer nada
            if task_id == self.last_processed_task_id:
                return False
            
            logger.info(f"📥 Nuevo comando detectado: {task_id}")
            
            # Procesar comando
            result = self.process_command(command_data)
            
            # Convertir AgentMetrics a dict si existe
            def convert_to_dict(obj):
                """Convierte objetos complejos a dict para JSON serialization."""
                if hasattr(obj, '__dict__'):
                    return {k: convert_to_dict(v) for k, v in obj.__dict__.items()}
                elif isinstance(obj, dict):
                    return {k: convert_to_dict(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_to_dict(item) for item in obj]
                elif hasattr(obj, 'isoformat'):  # datetime objects
                    return obj.isoformat()
                else:
                    return obj
            
            # Convertir result a dict serializable
            result_dict = convert_to_dict(result)
            
            # Guardar resultado
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Comando procesado: {task_id} -> {result.get('status')}")
            
            # Actualizar estado
            self.last_processed_time = mtime
            self.last_processed_task_id = task_id
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error decodificando JSON: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error procesando comando: {e}", exc_info=True)
            return False
    
    def start_processing(self) -> None:
        """Inicia el procesamiento en un thread separado."""
        if self.processing:
            return
        
        self.processing = True
        self.processor_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processor_thread.start()
        logger.info("👂 Procesador de comandos Master Agent iniciado")
    
    def stop_processing(self) -> None:
        """Detiene el procesamiento."""
        self.processing = False
        if self.processor_thread:
            self.processor_thread.join(timeout=2)
        logger.info("🛑 Procesador de comandos Master Agent detenido")
    
    def _processing_loop(self) -> None:
        """Loop principal de procesamiento."""
        logger.info("🔄 Iniciando loop de procesamiento de comandos...")
        
        while self.processing:
            try:
                self.check_and_process()
            except Exception as e:
                logger.error(f"❌ Error en loop de procesamiento: {e}")
            
            time.sleep(self.poll_interval)
        
        logger.info("✅ Loop de procesamiento finalizado")

