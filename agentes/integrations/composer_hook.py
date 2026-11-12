"""
Hook para Composer que detecta automáticamente comandos del Master Agent.

Cuando el usuario escribe en Cursor, este módulo detecta si es un comando
para el Master Agent y lo procesa automáticamente.
"""

import sys
import logging
from typing import Optional

logger = logging.getLogger("agentes.composer_hook")

# Flag para indicar si el hook está activo
_composer_hook_active = False


def activate_composer_hook():
    """Activa el hook para Composer."""
    global _composer_hook_active
    
    if _composer_hook_active:
        return
    
    try:
        # Esto se ejecutará cuando Composer procese el mensaje del usuario
        _composer_hook_active = True
        logger.info("✅ Composer hook activado")
    except Exception as e:
        logger.error(f"❌ Error activando Composer hook: {e}")


def process_user_message_in_composer(user_message: str) -> Optional[str]:
    """
    Procesa el mensaje del usuario en Composer y detecta comandos Master Agent.
    
    Esta función debe ser llamada cuando Composer recibe un mensaje del usuario.
    
    Args:
        user_message: Mensaje del usuario
        
    Returns:
        Respuesta formateada si es un comando Master Agent, None en caso contrario
    """
    if not _composer_hook_active:
        return None
    
    try:
        from agentes.integrations.cursor_auto import auto_process_if_master_command
        return auto_process_if_master_command(user_message)
    except Exception as e:
        logger.error(f"❌ Error en Composer hook: {e}")
        return None


# Auto-activar cuando se importa
activate_composer_hook()

