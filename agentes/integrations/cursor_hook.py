"""
Hook para detectar cuando el usuario escribe comandos en Cursor y activar automáticamente
la integración con el Master Agent.

Este módulo debe ser importado al inicio de cualquier script de Python que interactúe con Cursor.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("agentes.cursor_hook")

# Flag para indicar si el hook está activo
_hook_active = False


def activate_cursor_hook():
    """Activa el hook para detectar comandos en Cursor."""
    global _hook_active
    
    if _hook_active:
        return
    
    try:
        # Intentar importar la integración
        from agentes.integrations.cursor_integration import send_command_to_master_agent
        
        # Agregar función al namespace global para que sea accesible desde Cursor
        sys.modules['__main__'].send_command_to_master_agent = send_command_to_master_agent
        
        logger.info("✅ Hook de Cursor activado")
        _hook_active = True
        
    except ImportError as e:
        logger.warning(f"⚠️ No se pudo activar hook de Cursor: {e}")
    except Exception as e:
        logger.error(f"❌ Error activando hook de Cursor: {e}")


def check_for_cursor_command(user_input: str) -> Optional[dict]:
    """
    Verifica si el input del usuario es un comando para el Master Agent.
    
    Args:
        user_input: Input del usuario
        
    Returns:
        Resultado del comando o None si no es un comando
    """
    if not _hook_active:
        return None
    
    # Detectar si es un comando para Master Agent
    user_input_lower = user_input.lower().strip()
    
    # Comandos que activan el Master Agent
    master_agent_keywords = [
        "master agent",
        "master",
        "analiza",
        "coordina",
        "valida",
        "estado",
        "costo"
    ]
    
    if any(keyword in user_input_lower for keyword in master_agent_keywords):
        try:
            from agentes.integrations.cursor_integration import send_command_to_master_agent
            logger.info(f"📥 Comando detectado para Master Agent: {user_input[:50]}...")
            result = send_command_to_master_agent(user_input, wait_for_response=True)
            return result
        except Exception as e:
            logger.error(f"❌ Error procesando comando: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    return None


# Auto-activar cuando se importa este módulo
if __name__ != "__main__":
    activate_cursor_hook()

