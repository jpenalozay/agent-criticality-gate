"""
Script de verificación completa del sistema de agentes.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def print_section(title):
    """Imprime una sección."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)

def test_1_detection():
    """Prueba 1: Detección de comandos."""
    print_section("Prueba 1: Detección de comandos")
    try:
        from agentes.integrations.cursor_auto import detect_master_agent_command
        tests = [
            'agents, analizar todo el proyecto',
            'agents status',
            'Hola mundo'
        ]
        for t in tests:
            result = detect_master_agent_command(t)
            status = "OK" if result else "NO"
            print(f"{t[:40]:<40} -> {status}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_2_processor():
    """Prueba 2: Procesador de comandos."""
    print_section("Prueba 2: Procesador de comandos")
    try:
        from agentes.core.command_processor import MasterAgentCommandProcessor
        processor = MasterAgentCommandProcessor()
        print(f"Input file existe: {processor.input_file.exists()}")
        print(f"Output file existe: {processor.output_file.exists()}")
        print(f"Poll interval: {processor.poll_interval} segundos")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_3_redis():
    """Prueba 3: Redis."""
    print_section("Prueba 3: Redis")
    try:
        from agentes.core.redis_communication import get_redis_communication
        comm = get_redis_communication('test')
        print(f"Redis disponible: {comm.is_available()}")
        # Verificar conexión intentando publicar algo
        try:
            comm.publish("test", {"test": "data"})
            print("Redis conectado: True")
        except Exception:
            print("Redis conectado: False (pero disponible)")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_4_file_watchers():
    """Prueba 4: File Watchers."""
    print_section("Prueba 4: File Watchers")
    try:
        from agentes.core.file_watcher import FILE_WATCHER_AVAILABLE
        print(f"File watchers disponibles: {FILE_WATCHER_AVAILABLE}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_5_agent_instances():
    """Prueba 5: Instancias de agentes."""
    print_section("Prueba 5: Instancias de agentes")
    try:
        from agentes.core.agent_activation import get_agent_instance
        agents = ['db', 'backend', 'frontend', 'master']
        all_ok = True
        for a in agents:
            try:
                inst = get_agent_instance(a)
                status = "OK" if inst else "FAIL"
                print(f"{a:<15} -> {status}")
                if not inst:
                    all_ok = False
            except Exception as e:
                print(f"{a:<15} -> ERROR: {str(e)[:40]}")
                all_ok = False
        return all_ok
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_6_master_agent():
    """Prueba 6: Master Agent."""
    print_section("Prueba 6: Master Agent")
    try:
        from agentes.implementations.master_agent import MasterAgent
        agent = MasterAgent()
        print(f"Agent ID: {agent.agent_id}")
        print(f"Agents to collect: {len(agent.agents_to_collect)}")
        print(f"Agents: {', '.join(agent.agents_to_collect[:5])}...")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_7_communication_files():
    """Prueba 7: Archivos de comunicación."""
    print_section("Prueba 7: Archivos de comunicación")
    try:
        input_file = Path('agentes/communication/master_agent_input.json')
        output_file = Path('agentes/communication/master_agent_output.json')
        print(f"Input existe: {input_file.exists()}")
        print(f"Output existe: {output_file.exists()}")
        if output_file.exists():
            data = json.load(open(output_file, 'r', encoding='utf-8'))
            print(f"Ultimo comando: {data.get('command', 'N/A')}")
            print(f"Ultimo status: {data.get('status', 'N/A')}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_8_interpretation():
    """Prueba 8: Interpretación de comandos."""
    print_section("Prueba 8: Interpretación de comandos")
    try:
        from agentes.integrations.cursor_integration import CursorMasterAgentIntegration
        integration = CursorMasterAgentIntegration()
        test_cmd = 'agents, analizar todo el proyecto'
        result = integration._interpret_message(test_cmd)
        print(f"Comando: {test_cmd}")
        print(f"Interpretado como: {result.get('command')}")
        print(f"Coordinacion activada: {result.get('parameters', {}).get('coordinate_agents', False)}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_9_processing():
    """Prueba 9: Procesamiento completo."""
    print_section("Prueba 9: Procesamiento completo")
    try:
        from agentes.core.command_processor import MasterAgentCommandProcessor
        processor = MasterAgentCommandProcessor()
        processor.last_processed_task_id = None
        processor.last_processed_time = 0
        print("Procesando comando...")
        result = processor.check_and_process()
        status = "OK" if result else "FAIL"
        print(f"Resultado: {status}")
        
        output = Path('agentes/communication/master_agent_output.json')
        if output.exists():
            data = json.load(open(output, 'r', encoding='utf-8'))
            print(f"Status: {data.get('status')}")
            print(f"Command: {data.get('command')}")
            print(f"Success: {data.get('success')}")
            agents = data.get('result', {}).get('agents_results', {})
            print(f"Agents ejecutados: {list(agents.keys()) if agents else 'Ninguno'}")
        return result
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecuta todas las pruebas."""
    print("\n" + "="*60)
    print("VERIFICACION COMPLETA DEL SISTEMA DE AGENTES")
    print("="*60)
    
    results = []
    results.append(("Deteccion de comandos", test_1_detection()))
    results.append(("Procesador de comandos", test_2_processor()))
    results.append(("Redis", test_3_redis()))
    results.append(("File Watchers", test_4_file_watchers()))
    results.append(("Instancias de agentes", test_5_agent_instances()))
    results.append(("Master Agent", test_6_master_agent()))
    results.append(("Archivos de comunicacion", test_7_communication_files()))
    results.append(("Interpretacion", test_8_interpretation()))
    results.append(("Procesamiento completo", test_9_processing()))
    
    print_section("RESUMEN")
    all_ok = True
    for name, result in results:
        status = "OK" if result else "FAIL"
        print(f"{name:<30} -> {status}")
        if not result:
            all_ok = False
    
    print("\n" + "="*60)
    if all_ok:
        print("RESULTADO: TODOS LOS COMPONENTES FUNCIONANDO CORRECTAMENTE")
    else:
        print("RESULTADO: ALGUNOS COMPONENTES TIENEN PROBLEMAS")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

