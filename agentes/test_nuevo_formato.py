"""
Script de prueba para verificar el nuevo formato de comandos.
"""

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentes.integrations.cursor_auto import detect_master_agent_command
from agentes.integrations.cursor_integration import CursorMasterAgentIntegration

def test_detection():
    """Prueba la detección de comandos."""
    tests = [
        'agents, analizar todo el proyecto',
        'agents coordina db y backend',
        'agent, valida integracion',
        'agents status',
        'Hola, ¿cómo estás?'
    ]
    
    print('Pruebas de detección:')
    print('=' * 60)
    for test in tests:
        result = detect_master_agent_command(test)
        status = '✅ Detectado' if result else '❌ No detectado'
        print(f'{test[:40]:<40} -> {status}')
    print('=' * 60)
    print()

def test_interpretation():
    """Prueba la interpretación de comandos."""
    integration = CursorMasterAgentIntegration()
    
    tests = [
        'agents, analizar todo el proyecto',
        'agents coordina db y backend',
        'agent, valida integracion',
        'agents, estado de todos los agentes'
    ]
    
    print('Pruebas de interpretación:')
    print('=' * 60)
    for test in tests:
        result = integration._interpret_message(test)
        command = result.get('command', 'unknown')
        coord = result.get('parameters', {}).get('coordinate_agents', False)
        print(f'{test[:35]:<35} -> {command} (coord: {coord})')
    print('=' * 60)

if __name__ == "__main__":
    test_detection()
    print()
    test_interpretation()

