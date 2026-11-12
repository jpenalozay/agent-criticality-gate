"""
Integración automática con Cursor Composer.

Este módulo detecta automáticamente cuando el usuario escribe comandos
para el Master Agent en el chat de Cursor y los procesa automáticamente.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("agentes.cursor_auto")


def detect_master_agent_command(user_message: str) -> bool:
    """
    Detecta si el mensaje del usuario es un comando para el Master Agent.
    
    Args:
        user_message: Mensaje del usuario
        
    Returns:
        True si es un comando para Master Agent
    """
    if not user_message:
        return False
    
    message_lower = user_message.lower().strip()
    
    # NUEVO: Detectar "agents" o "agent" al inicio del mensaje
    if message_lower.startswith("agents,") or message_lower.startswith("agent,") or \
       message_lower.startswith("agents ") or message_lower.startswith("agent "):
        return True
    
    # Mantener compatibilidad con "Master Agent" por si acaso
    if message_lower.startswith("master agent") or message_lower.startswith("master"):
        return True
    
    # Palabras clave que indican comando para Master Agent
    master_keywords = [
        "analiza",
        "analizar",
        "analyze",
        "coordina",
        "coordinar",
        "coordinate",
        "valida",
        "validar",
        "validate",
        "estado",
        "status",
        "costo",
        "cost",
        "reporte",
        "report"
    ]
    
    # Si contiene palabras clave específicas
    if any(keyword in message_lower for keyword in master_keywords):
        # Verificar que no sea solo una conversación casual
        if len(message_lower.split()) > 2:  # Más de 2 palabras
            return True
    
    return False


def process_command_automatically(user_message: str) -> Optional[Dict[str, Any]]:
    """
    Procesa automáticamente un comando del usuario para el Master Agent.
    
    Args:
        user_message: Mensaje del usuario
        
    Returns:
        Resultado del comando o None si no es un comando
    """
    if not detect_master_agent_command(user_message):
        return None
    
    try:
        from agentes.integrations.cursor_integration import CursorMasterAgentIntegration
        
        logger.info(f"🤖 Comando Master Agent detectado: {user_message[:50]}...")
        
        # Crear integración
        integration = CursorMasterAgentIntegration()
        
        # Procesar mensaje y generar comando
        command_info = integration.process_user_message(user_message)
        
        if command_info.get("status") != "sent":
            logger.error(f"❌ Error enviando comando: {command_info.get('error')}")
            return {
                "status": "error",
                "error": command_info.get("error", "Unknown error")
            }
        
        logger.info(f"✅ Comando enviado: {command_info.get('command')}")
        
        # Esperar respuesta (timeout de 30 segundos)
        response = integration.wait_for_response(command_info["task_id"], timeout=30)
        
        if response:
            logger.info(f"✅ Respuesta recibida del Master Agent")
            return {
                "status": "completed",
                "task_id": command_info["task_id"],
                "response": response,
                "formatted": integration.format_response_for_cursor(response)
            }
        else:
            logger.warning("⏱️ Timeout esperando respuesta del Master Agent")
            return {
                "status": "timeout",
                "task_id": command_info["task_id"],
                "message": "El Master Agent no respondió a tiempo. Verifica que el sistema esté corriendo."
            }
            
    except Exception as e:
        logger.error(f"❌ Error procesando comando automáticamente: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }


def auto_process_if_master_command(user_message: str) -> Optional[str]:
    """
    Procesa automáticamente si es un comando Master Agent y retorna respuesta formateada.
    
    Args:
        user_message: Mensaje del usuario
        
    Returns:
        Respuesta formateada para mostrar en Cursor o None
    """
    result = process_command_automatically(user_message)
    
    if not result:
        return None
    
    if result.get("status") == "completed":
        return result.get("formatted", "✅ Comando procesado correctamente")
    elif result.get("status") == "timeout":
        return f"⏱️ {result.get('message', 'Timeout esperando respuesta')}"
    elif result.get("status") == "error":
        return f"❌ Error: {result.get('error', 'Error desconocido')}"
    
    return None

