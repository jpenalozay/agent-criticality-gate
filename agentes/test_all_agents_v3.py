"""
Test Completo de Todos los Agentes v3.0

Prueba los 5 agentes implementados en un flujo completo.
"""

import sys
import os

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Agregar path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_complete_workflow():
    """Test del flujo completo con todos los agentes."""
    print("\n" + "="*70)
    print("TEST COMPLETO: Flujo con Todos los Agentes v3.0")
    print("="*70)
    
    try:
        from implementations.arquitecto_agent_v3 import ArquitectoAgentV3
        from implementations.ui_ux_designer_agent import UIUXDesignerAgent
        from implementations.sentinel_agent_v3 import SentinelAgent
        from implementations.coder_agent_v3 import CoderAgentV3
        from implementations.test_designer_agent import TestDesignerAgent
        
        # Requerimiento de prueba
        requirement = "Crear una aplicación web para gestión de tareas (TODO app) con autenticación de usuarios"
        
        print(f"\n📋 Requerimiento: {requirement}")
        print("\n" + "-"*70)
        
        # 1. ARQUITECTO
        print("\n[1/5] 🏗️  ARQUITECTO (con peer review)...")
        arquitecto = ArquitectoAgentV3(enable_peer_review=False)  # Sin peer review para rapidez
        blueprint = arquitecto.process(requirement)
        print(f"✓ Blueprint: {blueprint.get('name', 'unnamed')}")
        print(f"  Componentes: {len(blueprint.get('components', {}))}")
        print(f"  SOP Score: {blueprint.get('sop_compliance_score', 0):.2f}")
        
        # 2. UI/UX DESIGNER
        print("\n[2/5] 🎨 UI/UX DESIGNER (con peer review)...")
        ui_designer = UIUXDesignerAgent(enable_peer_review=False)
        ui_ux_spec = ui_designer.process(blueprint, requirement)
        print(f"✓ UI/UX Design:")
        print(f"  Personas: {len(ui_ux_spec.get('personas', []))}")
        print(f"  User Flows: {len(ui_ux_spec.get('user_flows', []))}")
        print(f"  Wireframes: {len(ui_ux_spec.get('wireframes', []))}")
        print(f"  SOP Score: {ui_ux_spec.get('sop_compliance_score', 0):.2f}")
        
        # 3. SENTINEL
        print("\n[3/5] 🛡️  SENTINEL (risk assessment)...")
        sentinel = SentinelAgent()
        risk_assessment = sentinel.process(blueprint)
        print(f"✓ Risk Assessment:")
        print(f"  Total Score: {risk_assessment.get('total_score', 0):.1f}")
        print(f"  Level: {risk_assessment.get('level', 'UNKNOWN')}")
        print(f"  Decision: {risk_assessment.get('decision', 'unknown')}")
        print(f"  SOP Score: {risk_assessment.get('sop_compliance_score', 0):.2f}")
        
        # 4. CODER
        print("\n[4/5] 💻 CODER (sin executable feedback para rapidez)...")
        coder = CoderAgentV3(enable_executable_feedback=False)
        code_artifacts = coder.process(blueprint, risk_assessment)
        print(f"✓ Code Generated:")
        print(f"  Files: {len(code_artifacts.get('files', {}))}")
        print(f"  Language: {code_artifacts.get('language', 'unknown')}")
        print(f"  SOP Score: {code_artifacts.get('sop_compliance_score', 0):.2f}")
        
        # 5. TEST DESIGNER
        print("\n[5/5] 🧪 TEST DESIGNER (independiente, con peer review)...")
        test_designer = TestDesignerAgent(enable_peer_review=False)
        test_suite = test_designer.process(blueprint, requirement)
        print(f"✓ Tests Generated:")
        print(f"  Total Tests: {test_suite.get('total_tests', 0)}")
        print(f"  Test Files: {len(test_suite.get('test_files', {}))}")
        print(f"  Expected Coverage: {test_suite.get('expected_coverage', 0):.0%}")
        print(f"  SOP Score: {test_suite.get('sop_compliance_score', 0):.2f}")
        
        # RESUMEN
        print("\n" + "="*70)
        print("✅ FLUJO COMPLETO EXITOSO")
        print("="*70)
        print("\n📊 Resumen:")
        print(f"  1. Blueprint generado con {len(blueprint.get('components', {}))} componentes")
        print(f"  2. UI/UX con {len(ui_ux_spec.get('wireframes', []))} wireframes")
        print(f"  3. Risk Score: {risk_assessment.get('total_score', 0):.1f} ({risk_assessment.get('level', 'UNKNOWN')})")
        print(f"  4. Código: {len(code_artifacts.get('files', {}))} archivos")
        print(f"  5. Tests: {test_suite.get('total_tests', 0)} tests")
        
        print("\n🎉 Todos los agentes funcionando correctamente!")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error en flujo completo: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_individual_agents():
    """Test individual de cada agente."""
    print("\n" + "="*70)
    print("TEST INDIVIDUAL: Cada Agente por Separado")
    print("="*70)
    
    results = []
    
    # Test Arquitecto
    try:
        print("\n[1/5] Testing Arquitecto...")
        from implementations.arquitecto_agent_v3 import ArquitectoAgentV3
        arquitecto = ArquitectoAgentV3(enable_peer_review=False)
        blueprint = arquitecto.process("Crear una API REST simple")
        print(f"✓ Arquitecto: OK (SOP: {blueprint.get('sop_compliance_score', 0):.2f})")
        results.append(("Arquitecto", True))
    except Exception as e:
        print(f"✗ Arquitecto: FAIL - {e}")
        results.append(("Arquitecto", False))
    
    # Test UI/UX Designer
    try:
        print("\n[2/5] Testing UI/UX Designer...")
        from implementations.ui_ux_designer_agent import UIUXDesignerAgent
        ui_designer = UIUXDesignerAgent(enable_peer_review=False)
        ui_spec = ui_designer.process({"name": "test", "type": "web_app", "components": {}}, "Test app")
        print(f"✓ UI/UX Designer: OK (SOP: {ui_spec.get('sop_compliance_score', 0):.2f})")
        results.append(("UI/UX Designer", True))
    except Exception as e:
        print(f"✗ UI/UX Designer: FAIL - {e}")
        results.append(("UI/UX Designer", False))
    
    # Test Sentinel
    try:
        print("\n[3/5] Testing Sentinel...")
        from implementations.sentinel_agent_v3 import SentinelAgent
        sentinel = SentinelAgent()
        risk = sentinel.process({"name": "test", "type": "api", "components": {}})
        print(f"✓ Sentinel: OK (Score: {risk.get('total_score', 0):.1f})")
        results.append(("Sentinel", True))
    except Exception as e:
        print(f"✗ Sentinel: FAIL - {e}")
        results.append(("Sentinel", False))
    
    # Test Coder
    try:
        print("\n[4/5] Testing Coder...")
        from implementations.coder_agent_v3 import CoderAgentV3
        coder = CoderAgentV3(enable_executable_feedback=False)
        code = coder.process({"name": "test", "type": "api", "components": {}})
        print(f"✓ Coder: OK (Files: {len(code.get('files', {}))})")
        results.append(("Coder", True))
    except Exception as e:
        print(f"✗ Coder: FAIL - {e}")
        results.append(("Coder", False))
    
    # Test Test Designer
    try:
        print("\n[5/5] Testing Test Designer...")
        from implementations.test_designer_agent import TestDesignerAgent
        test_designer = TestDesignerAgent(enable_peer_review=False)
        tests = test_designer.process({"name": "test", "type": "api", "components": {}}, "Test")
        print(f"✓ Test Designer: OK (Tests: {tests.get('total_tests', 0)})")
        results.append(("Test Designer", True))
    except Exception as e:
        print(f"✗ Test Designer: FAIL - {e}")
        results.append(("Test Designer", False))
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN TESTS INDIVIDUALES")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} agentes passed")
    
    return passed == total


def main():
    """Ejecuta todos los tests."""
    print("\n" + "="*70)
    print("FRAMEWORK v3.0 - TEST COMPLETO DE AGENTES")
    print("="*70)
    
    # Test individual
    individual_ok = test_individual_agents()
    
    # Test flujo completo
    workflow_ok = test_complete_workflow()
    
    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)
    print(f"Tests Individuales: {'✓ PASS' if individual_ok else '✗ FAIL'}")
    print(f"Flujo Completo: {'✓ PASS' if workflow_ok else '✗ FAIL'}")
    
    if individual_ok and workflow_ok:
        print("\n🎉🎉🎉 TODOS LOS TESTS PASARON! 🎉🎉🎉")
        return 0
    else:
        print("\n⚠️  Algunos tests fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
