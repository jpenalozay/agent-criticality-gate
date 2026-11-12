"""
Script de prueba para verificar el procesamiento automático de comandos.
"""

import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.insert(0, str(Path(__file__).parent.parent))

from agentes.integrations.cursor_auto import auto_process_if_master_command

def test_command(user_message: str):
    """Prueba un comando."""
    print(f"\n{'='*60}")
    print(f"🧪 Probando comando: {user_message}")
    print(f"{'='*60}\n")
    
    result = auto_process_if_master_command(user_message)
    
    if result:
        print("✅ COMANDO PROCESADO:")
        print(result)
    else:
        print("ℹ️ No es un comando Master Agent")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    # Pruebas
    test_command("Master Agent, analiza todo el proyecto")
    test_command("Master Agent, coordina los agentes DB y Backend")
    test_command("Master Agent, ¿cuál es el estado de todos los agentes?")
    test_command("Hola, ¿cómo estás?")  # No debería procesarse

