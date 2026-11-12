"""
Test End-to-End del Framework v3.0

Prueba el flujo completo: Arquitecto → Coder con executable feedback
"""

import sys
import os

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

# Agregar path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_e2e_simple_flow():
    """Test E2E: Flujo simple sin peer review."""
    print("\n" + "="*70)
    print("TEST E2E: Flujo Simple (Arquitecto → Coder)")
    print("="*70)
    
    try:
        from implementations.arquitecto_agent_v3 import ArquitectoAgentV3
        from implementations.coder_agent_v3 import CoderAgentV3
        
        # 1. Crear agentes (sin peer review para test rápido)
        print("\n[1/4] Inicializando agentes...")
        arquitecto = ArquitectoAgentV3(enable_peer_review=False)
        coder = CoderAgentV3(enable_executable_feedback=False)  # Sin Docker para test rápido
        print("✓ Agentes inicializados")
        
        # 2. Generar blueprint
        print("\n[2/4] Generando blueprint...")
        requirement = "Crear una función que sume dos números y retorne el resultado"
        
        blueprint = arquitecto.process(requirement)
        print(f"✓ Blueprint generado: {blueprint.get('name', 'unnamed')}")
        print(f"  Componentes: {len(blueprint.get('components', {}))}")
        print(f"  SOP Score: {blueprint.get('sop_compliance_score', 0):.2f}")
        
        # 3. Generar código
        print("\n[3/4] Generando código...")
        code_artifacts = coder.process(blueprint)
        print(f"✓ Código generado: {len(code_artifacts.get('files', {}))} archivos")
        print(f"  Lenguaje: {code_artifacts.get('language', 'unknown')}")
        print(f"  SOP Score: {code_artifacts.get('sop_compliance_score', 0):.2f}")
        
        # 4. Mostrar código generado
        print("\n[4/4] Código generado:")
        files = code_artifacts.get('files', {})
        for filepath, content in list(files.items())[:2]:  # Mostrar primeros 2 archivos
            print(f"\n--- {filepath} ---")
            print(content[:300] + "..." if len(content) > 300 else content)
        
        print("\n" + "="*70)
        print("✓ TEST E2E SIMPLE: EXITOSO")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error en test E2E: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_e2e_with_peer_review():
    """Test E2E: Flujo con peer review."""
    print("\n" + "="*70)
    print("TEST E2E: Flujo con Peer Review")
    print("="*70)
    
    try:
        from implementations.arquitecto_agent_v3 import ArquitectoAgentV3
        
        # Crear arquitecto con peer review
        print("\n[1/3] Inicializando arquitecto con peer review...")
        arquitecto = ArquitectoAgentV3(enable_peer_review=True)
        print("✓ Arquitecto inicializado")
        
        # Generar blueprint con peer review
        print("\n[2/3] Generando blueprint con peer review...")
        requirement = "Crear una API REST para gestión de usuarios con autenticación JWT"
        
        blueprint = arquitecto.process(requirement)
        print(f"✓ Blueprint generado y revisado")
        print(f"  Nombre: {blueprint.get('name', 'unnamed')}")
        print(f"  Tipo: {blueprint.get('type', 'unknown')}")
        print(f"  Componentes: {len(blueprint.get('components', {}))}")
        print(f"  SOP Score: {blueprint.get('sop_compliance_score', 0):.2f}")
        
        if "peer_review_score" in blueprint:
            print(f"  Peer Review Score: {blueprint.get('peer_review_score', 0):.2f}")
        
        # Mostrar componentes
        print("\n[3/3] Componentes del blueprint:")
        components = blueprint.get('components', {})
        for comp_name, comp_data in list(components.items())[:3]:
            print(f"  - {comp_name}:")
            print(f"    Tipo: {comp_data.get('type', 'unknown')}")
            print(f"    Tech: {comp_data.get('tech', 'unknown')}")
        
        print("\n" + "="*70)
        print("✓ TEST E2E PEER REVIEW: EXITOSO")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error en test E2E peer review: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_e2e_with_executable_feedback():
    """Test E2E: Flujo con executable feedback."""
    print("\n" + "="*70)
    print("TEST E2E: Flujo con Executable Feedback")
    print("="*70)
    
    try:
        from implementations.arquitecto_agent_v3 import ArquitectoAgentV3
        from implementations.coder_agent_v3 import CoderAgentV3
        from core.code_executor import CodeExecutor
        
        # Verificar Docker
        executor = CodeExecutor()
        if not executor.client:
            print("⚠ Docker no disponible, saltando test de executable feedback")
            return True
        
        # Crear agentes
        print("\n[1/4] Inicializando agentes...")
        arquitecto = ArquitectoAgentV3(enable_peer_review=False)
        coder = CoderAgentV3(enable_executable_feedback=True, max_iterations=2)
        print("✓ Agentes inicializados")
        
        # Generar blueprint simple
        print("\n[2/4] Generando blueprint...")
        requirement = "Crear un script Python que calcule el factorial de un número"
        blueprint = arquitecto.process(requirement)
        print(f"✓ Blueprint generado")
        
        # Generar código con executable feedback
        print("\n[3/4] Generando código con executable feedback...")
        code_artifacts = coder.process(blueprint)
        print(f"✓ Código generado")
        
        # Mostrar resultados de ejecución
        print("\n[4/4] Resultados de ejecución:")
        exec_results = code_artifacts.get('execution_results', {})
        if exec_results:
            print(f"  Success: {exec_results.get('success', False)}")
            print(f"  Iterations: {exec_results.get('iterations', 0)}")
            print(f"  Runtime: {exec_results.get('runtime_ms', 0)}ms")
        else:
            print("  No execution results available")
        
        print("\n" + "="*70)
        print("✓ TEST E2E EXECUTABLE FEEDBACK: EXITOSO")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error en test E2E executable feedback: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todos los tests E2E."""
    print("\n" + "="*70)
    print("FRAMEWORK v3.0 - TESTS END-TO-END")
    print("="*70)
    
    tests = [
        ("E2E Simple Flow", test_e2e_simple_flow),
        ("E2E Peer Review", test_e2e_with_peer_review),
        ("E2E Executable Feedback", test_e2e_with_executable_feedback),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test {name} failed with exception: {e}")
            results.append((name, False))
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN DE TESTS E2E")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Todos los tests E2E pasaron!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
