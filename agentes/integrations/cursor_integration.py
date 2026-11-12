"""
Módulo de integración con Cursor para comunicación conversacional con Master Agent.

Este módulo permite que los usuarios interactúen con el Master Agent
directamente desde el chat de Cursor usando lenguaje natural.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

logger = logging.getLogger("agentes.cursor_integration")


class CursorMasterAgentIntegration:
    """
    Integración con Cursor para comunicación conversacional con Master Agent.
    
    Convierte mensajes del chat de Cursor en comandos estructurados
    que el Master Agent puede procesar.
    """
    
    def __init__(
        self,
        communication_dir: str = "agentes/communication",
        input_file: str = "master_agent_input.json",
        output_file: str = "master_agent_output.json"
    ):
        """
        Inicializa la integración con Cursor.
        
        Args:
            communication_dir: Directorio de comunicación
            input_file: Nombre del archivo de entrada
            output_file: Nombre del archivo de salida
        """
        self.communication_dir = Path(communication_dir)
        self.communication_dir.mkdir(parents=True, exist_ok=True)
        
        self.input_file = self.communication_dir / input_file
        self.output_file = self.communication_dir / output_file
        
        logger.info(f"✅ Cursor integration inicializada")
        logger.info(f"   Input: {self.input_file}")
        logger.info(f"   Output: {self.output_file}")
    
    def process_user_message(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Procesa un mensaje del usuario en Cursor y genera comando para Master Agent.
        
        Args:
            user_message: Mensaje del usuario en lenguaje natural
            context: Contexto adicional (opcional)
            
        Returns:
            Dict con información del comando generado
        """
        # Generar ID único para esta tarea
        task_id = f"cursor-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        
        # Interpretar mensaje y determinar comando
        command_structure = self._interpret_message(user_message)
        
        # Crear estructura de entrada
        input_data = {
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
            "type": command_structure.get("type", "command"),
            "command": command_structure.get("command"),
            "user_input": user_message,
            "parameters": command_structure.get("parameters", {}),
            "context": context or {},
            "source": "cursor_chat",
            "expected_output": command_structure.get("expected_output", "response")
        }
        
        # Guardar archivo de entrada
        try:
            with open(self.input_file, 'w', encoding='utf-8') as f:
                json.dump(input_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Comando generado: {task_id}")
            logger.info(f"   Comando: {command_structure.get('command')}")
            
            return {
                "task_id": task_id,
                "status": "sent",
                "command": command_structure.get("command"),
                "input_file": str(self.input_file)
            }
        
        except Exception as e:
            logger.error(f"❌ Error guardando comando: {e}")
            return {
                "task_id": task_id,
                "status": "error",
                "error": str(e)
            }
    
    def wait_for_response(self, task_id: str, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """
        Espera la respuesta del Master Agent.
        
        Args:
            task_id: ID de la tarea
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            Respuesta del Master Agent o None si timeout
        """
        import time
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.output_file.exists():
                try:
                    with open(self.output_file, 'r', encoding='utf-8') as f:
                        output_data = json.load(f)
                    
                    # Verificar que es la respuesta correcta
                    if output_data.get("task_id") == task_id:
                        logger.info(f"✅ Respuesta recibida: {task_id}")
                        return output_data
                
                except Exception as e:
                    logger.error(f"❌ Error leyendo respuesta: {e}")
            
            time.sleep(0.5)  # Polling cada 500ms
        
        logger.warning(f"⏱️ Timeout esperando respuesta: {task_id}")
        return None
    
    def format_response_for_cursor(self, response: Dict[str, Any]) -> str:
        """
        Formatea la respuesta del Master Agent para mostrar en Cursor.
        
        Args:
            response: Respuesta del Master Agent
            
        Returns:
            Texto formateado para mostrar en Cursor
        """
        if not response:
            return "❌ No se recibió respuesta del Master Agent"
        
        status = response.get("status", "unknown")
        result = response.get("result", {})
        
        # Formato básico
        lines = []
        lines.append(f"✅ **Estado**: {status.upper()}")
        lines.append("")
        
        # Información de ejecución
        if "execution_time_ms" in response:
            exec_time = response["execution_time_ms"]
            lines.append(f"⏱️ **Tiempo de ejecución**: {exec_time:.2f}ms ({exec_time/1000:.2f}s)")
        
        if "cost_usd" in response:
            cost = response.get("cost_usd", 0)
            lines.append(f"💰 **Costo**: ${cost:.6f}")
        
        if "llm_tokens_used" in response:
            tokens = response.get("llm_tokens_used", 0)
            lines.append(f"🔢 **Tokens LLM**: {tokens:,}")
        
        lines.append("")
        
        # Resultados principales
        if isinstance(result, dict):
            if "suggestions" in result:
                lines.append("💡 **Sugerencias**:")
                for i, suggestion in enumerate(result["suggestions"][:5], 1):
                    lines.append(f"   {i}. {suggestion}")
            
            if "agents_activated" in result:
                agents = result["agents_activated"]
                lines.append(f"🤖 **Agentes activados**: {', '.join(agents)}")
            
            if "analysis" in result:
                analysis = result["analysis"]
                lines.append("📊 **Análisis**:")
                if isinstance(analysis, dict):
                    for key, value in analysis.items():
                        lines.append(f"   - {key}: {value}")
                else:
                    lines.append(f"   {analysis}")
        
        lines.append("")
        lines.append(f"📄 **Task ID**: `{response.get('task_id')}`")
        
        return "\n".join(lines)
    
    def _interpret_message(self, message: str) -> Dict[str, Any]:
        """
        Interpreta un mensaje en lenguaje natural y lo convierte en comando.
        
        Esta es una implementación básica usando palabras clave.
        En producción, se podría usar un LLM para interpretación más avanzada.
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            Estructura de comando interpretada
        """
        message_lower = message.lower()
        
        # Detectar tipo de comando
        # NUEVO: Detecta "agents" o "agent" al inicio del mensaje
        if message_lower.startswith("agents,") or message_lower.startswith("agent,") or message_lower.startswith("agents ") or message_lower.startswith("agent "):
            # Remover el prefijo para procesar el resto del mensaje
            remaining_message = message_lower.split(",", 1)[-1].strip() if "," in message_lower else message_lower.split(" ", 1)[-1].strip()
            
            if any(word in remaining_message for word in ["analiza", "analizar", "analyze"]):
                if "arquitectura" in remaining_message or "architecture" in remaining_message or "proyecto" in remaining_message or "project" in remaining_message:
                    return {
                        "type": "analysis",
                        "command": "analyze_architecture",
                        "parameters": {
                            "check_structure": True,
                            "provide_suggestions": True,
                            "coordinate_agents": True  # Coordinar agentes automáticamente
                        },
                        "expected_output": "suggestions"
                    }
                elif "performance" in remaining_message or "performance" in remaining_message:
                    return {
                        "type": "analysis",
                        "command": "analyze_performance",
                        "parameters": {},
                        "expected_output": "analysis"
                    }
            
            elif any(word in remaining_message for word in ["coordina", "coordinar", "coordinate"]):
                return {
                    "type": "coordination",
                    "command": "coordinate_task",
                    "parameters": {
                        "agents_required": self._extract_agents(remaining_message),
                        "task_description": message
                    },
                    "expected_output": "coordination_result"
                }
            
            elif any(word in remaining_message for word in ["valida", "validar", "validate"]):
                return {
                    "type": "validation",
                    "command": "validate_integration",
                    "parameters": {
                        "check_all_agents": True
                    },
                    "expected_output": "validation_result"
                }
            
            elif any(word in remaining_message for word in ["estado", "status", "están"]):
                return {
                    "type": "query",
                    "command": "manage_agents",
                    "parameters": {
                        "action": "status"
                    },
                    "expected_output": "status_report"
                }
            
            elif any(word in remaining_message for word in ["costo", "cost", "costos"]):
                return {
                    "type": "report",
                    "command": "generate_cost_time_report",
                    "parameters": {
                        "date": "today"
                    },
                    "expected_output": "cost_report"
                }
            
            elif any(word in remaining_message for word in ["conflicto", "conflict", "conflictos"]):
                return {
                    "type": "analysis",
                    "command": "detect_conflicts",
                    "parameters": {
                        "check_all": True
                    },
                    "expected_output": "conflicts_report"
                }
            
            # Comando genérico si solo dice "agents" sin acción específica
            return {
                "type": "command",
                "command": "coordinate_task",
                "parameters": {
                    "agents_required": ["all"],
                    "task_description": remaining_message
                },
                "expected_output": "general_response"
            }
        
        # Mantener compatibilidad con "Master Agent" por si acaso
        if any(word in message_lower for word in ["master agent", "master"]):
            if any(word in message_lower for word in ["analiza", "analizar", "analyze"]):
                if "arquitectura" in message_lower or "architecture" in message_lower or "proyecto" in message_lower or "project" in message_lower:
                    return {
                        "type": "analysis",
                        "command": "analyze_architecture",
                        "parameters": {
                            "check_structure": True,
                            "provide_suggestions": True,
                            "coordinate_agents": True
                        },
                        "expected_output": "suggestions"
                    }
            elif any(word in message_lower for word in ["coordina", "coordinar", "coordinate"]):
                return {
                    "type": "coordination",
                    "command": "coordinate_task",
                    "parameters": {
                        "agents_required": self._extract_agents(message_lower),
                        "task_description": message
                    },
                    "expected_output": "coordination_result"
                }
        
        # Comando por defecto: análisis general
        return {
            "type": "command",
            "command": "coordinate_task",
            "parameters": {
                "task_description": message
            },
            "expected_output": "general_response"
        }
    
    def _extract_agents(self, message: str) -> List[str]:
        """Extrae nombres de agentes mencionados en el mensaje."""
        agent_keywords = {
            "db": ["db", "database", "base de datos", "modelo"],
            "backend": ["backend", "back-end", "api"],
            "frontend": ["frontend", "front-end", "html", "css", "js"],
            "performance": ["performance", "rendimiento", "velocidad"],
            "openai": ["openai", "gpt", "ai"],
            "whatsapp": ["whatsapp"],
            "code_quality": ["calidad", "quality", "pep8"],
            "tests": ["test", "prueba", "coverage"]
        }
        
        agents_found = []
        for agent_id, keywords in agent_keywords.items():
            if any(keyword in message for keyword in keywords):
                agents_found.append(agent_id)
        
        return agents_found if agents_found else ["all"]


def send_command_to_master_agent(user_message: str, wait_for_response: bool = True) -> Dict[str, Any]:
    """
    Función de conveniencia para enviar comando al Master Agent desde Cursor.
    
    Args:
        user_message: Mensaje del usuario
        wait_for_response: Si True, espera respuesta (default: True)
        
    Returns:
        Respuesta del Master Agent o información del comando enviado
    """
    integration = CursorMasterAgentIntegration()
    
    # Procesar mensaje y generar comando
    command_info = integration.process_user_message(user_message)
    
    if command_info.get("status") != "sent":
        return command_info
    
    if wait_for_response:
        # Esperar respuesta
        response = integration.wait_for_response(command_info["task_id"])
        
        if response:
            # Formatear para mostrar en Cursor
            formatted = integration.format_response_for_cursor(response)
            return {
                "task_id": command_info["task_id"],
                "status": "completed",
                "response": response,
                "formatted_response": formatted
            }
        else:
            return {
                "task_id": command_info["task_id"],
                "status": "timeout",
                "message": "El Master Agent no respondió a tiempo"
            }
    
    return command_info

