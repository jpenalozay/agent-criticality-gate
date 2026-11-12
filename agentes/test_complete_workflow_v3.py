"""
Test Completo del Framework v3.0 - TODOS LOS AGENTES

Prueba el flujo completo con los 8 agentes implementados.
"""

import sys
import os

# Cargar variables de entorno
from dotenv import load_dotenv
load_dotenv()

# Agregar path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_complete_8_agent_workflow():
    """Test del flujo completo con TODOS los 8 agentes."""
    print("\n" + "="*70)
    print("TEST COMPLETO: Flujo con TODOS LOS 8 AGENTES v3.0")
    print("="*70)
    
    try:
        # Importar todos los agentes
        from implementations.arquitecto_agent_v3 import ArquitectoAgentV3
        from implementations.ui_ux_designer_agent import UIUXDesignerAgent
        from implementations.sentinel_agent_v3 import SentinelAgent
        from implementations.coder_agent_v3 import CoderAgentV3
        from implementations.test_designer_agent import TestDesignerAgent
        from implementations.test_executor import TestExecutorAgent
        from implementations.linter_agent import LinterAgent
        from implementations.auditor_agent import AuditorAgent
        
        # Requerimiento de prueba
        requirement = "Crear una calculadora simple con operaciones básicas (+, -, *, /)"
        
        print(f"\n📋 Requerimiento: {requirement}")
        print("\n" + "-"*70)
        
        # Inicializar Auditor
        print("\n[0/8] 📝 AUDITOR (inicialización)...")
        auditor = AuditorAgent()
        events = []
        print("✓ Auditor inicializado")
        
        # 1. ARQUITECTO
        print("\n[1/8] 🏗️  ARQUITECTO...")
        arquitecto = ArquitectoAgentV3(enable_peer_review=False)
        blueprint = arquitecto.process(requirement)
        events.append({
            "actor": "arquitecto",
            "action": "blueprint_generated",
            "resource": blueprint.get('name', 'unnamed'),
            "details": {"components": len(blueprint.get('components', {}))}
        })
        print(f"✓ Blueprint: {blueprint.get('name', 'unnamed')}")
        print(f"  SOP Score: {blueprint.get('sop_compliance_score', 0):.2f}")
        
        # 2. UI/UX DESIGNER
        print("\n[2/8] 🎨 UI/UX DESIGNER...")
        ui_designer = UIUXDesignerAgent(enable_peer_review=False)
        ui_ux_spec = ui_designer.process(blueprint, requirement)
        events.append({
            "actor": "ui_ux_designer",
            "action": "ui_design_generated",
            "resource": blueprint.get('name', 'unnamed'),
            "details": {"wireframes": len(ui_ux_spec.get('wireframes', []))}
        })
        print(f"✓ UI/UX Design:")
        print(f"  Wireframes: {len(ui_ux_spec.get('wireframes', []))}")
        print(f"  SOP Score: {ui_ux_spec.get('sop_compliance_score', 0):.2f}")
        
        # 3. SENTINEL
        print("\n[3/8] 🛡️  SENTINEL...")
        sentinel = SentinelAgent()
        risk_assessment = sentinel.process(blueprint)
        events.append({
            "actor": "sentinel",
            "action": "risk_assessed",
            "resource": blueprint.get('name', 'unnamed'),
            "details": {
                "score": risk_assessment.get('total_score', 0),
                "level": risk_assessment.get('level', 'UNKNOWN')
            }
        })
        print(f"✓ Risk: {risk_assessment.get('total_score', 0):.1f} ({risk_assessment.get('level', 'UNKNOWN')})")
        print(f"  Decision: {risk_assessment.get('decision', 'unknown')}")
        
        # 4. CODER
        print("\n[4/8] 💻 CODER...")
        coder = CoderAgentV3(enable_executable_feedback=False)
        code_artifacts = coder.process(blueprint, risk_assessment)
        events.append({
            "actor": "coder",
            "action": "code_generated",
            "resource": blueprint.get('name', 'unnamed'),
            "details": {"files": len(code_artifacts.get('files', {}))}
        })
        print(f"✓ Code: {len(code_artifacts.get('files', {}))} files")
        print(f"  Language: {code_artifacts.get('language', 'unknown')}")
        
        # 5. TEST DESIGNER
        print("\n[5/8] 🧪 TEST DESIGNER...")
        test_designer = TestDesignerAgent(enable_peer_review=False)
        test_suite = test_designer.process(blueprint, requirement)
        events.append({
            "actor": "test_designer",
            "action": "tests_designed",
            "resource": blueprint.get('name', 'unnamed'),
            "details": {"total_tests": test_suite.get('total_tests', 0)}
        })
        print(f"✓ Tests: {test_suite.get('total_tests', 0)} tests")
        print(f"  Expected Coverage: {test_suite.get('expected_coverage', 0):.0%}")
        
        # 6. TEST EXECUTOR
        print("\n[6/8] ⚙️  TEST EXECUTOR...")
        test_executor = TestExecutorAgent()
        test_results = test_executor.process(code_artifacts, test_suite)
        events.append({
            "actor": "test_executor",
            "action": "tests_executed",
            "resource": blueprint.get('name', 'unnamed'),
            "details": {
                "passed": test_results.get('passed', 0),
                "total": test_results.get('total_tests', 0)
            }
        })
        print(f"✓ Tests Executed: {test_results.get('passed', 0)}/{test_results.get('total_tests', 0)}")
        print(f"  Coverage: {test_results.get('coverage', 0):.0%}")
        
        # 7. LINTER
        print("\n[7/8] 🔍 LINTER...")
        linter = LinterAgent()
        lint_results = linter.process(code_artifacts)
        events.append({
            "actor": "linter",
            "action": "code_linted",
            "resource": blueprint.get('name', 'unnamed'),
            "details": {
                "quality_score": lint_results.get('quality_score', 0),
                "issues": len(lint_results.get('issues', []))
            }
        })
        print(f"✓ Quality Score: {lint_results.get('quality_score', 0):.1f}/100")
        print(f"  Issues: {len(lint_results.get('issues', []))}")
        
        # 8. AUDITOR (registro de eventos)
        print("\n[8/8] 📝 AUDITOR (logging events)...")
        audit_summary = auditor.process(events)
        print(f"✓ Events Logged: {audit_summary.get('events_logged', 0)}")
        print(f"  Integrity: {audit_summary.get('integrity', 0):.0%}")
        
        # RESUMEN FINAL
        print("\n" + "="*70)
        print("✅ FLUJO COMPLETO CON 8 AGENTES EXITOSO")
        print("="*70)
        print("\n📊 Resumen del Flujo:")
        print(f"  1. Blueprint: {len(blueprint.get('components', {}))} componentes")
        print(f"  2. UI/UX: {len(ui_ux_spec.get('wireframes', []))} wireframes")
        print(f"  3. Risk: {risk_assessment.get('total_score', 0):.1f} ({risk_assessment.get('level', 'UNKNOWN')})")
        print(f"  4. Code: {len(code_artifacts.get('files', {}))} archivos")
        print(f"  5. Tests: {test_suite.get('total_tests', 0)} tests diseñados")
        print(f"  6. Execution: {test_results.get('passed', 0)}/{test_results.get('total_tests', 0)} passed")
        print(f"  7. Quality: {lint_results.get('quality_score', 0):.1f}/100")
        print(f"  8. Audit: {audit_summary.get('events_logged', 0)} events logged")
        
        print("\n🎉🎉🎉 FRAMEWORK v3.0 COMPLETO FUNCIONANDO! 🎉🎉🎉")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error en flujo completo: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_individual_mechanical_agents():
    """Test individual de agentes mecánicos."""
    print("\n" + "="*70)
    print("TEST: Agentes Mecánicos (Test Executor, Linter, Auditor)")
    print("="*70)
    
    results = []
    
    # Test Test Executor
    try:
        print("\n[1/3] Testing Test Executor...")
        from implementations.test_executor import TestExecutorAgent
        executor = TestExecutorAgent()
        result = executor.process(
            {"files": {"main.py": "print('hello')"}},
            {"test_files": {"test_main.py": "assert True"}}
        )
        print(f"✓ Test Executor: OK")
        results.append(("Test Executor", True))
    except Exception as e:
        print(f"✗ Test Executor: FAIL - {e}")
        results.append(("Test Executor", False))
    
    # Test Linter
    try:
        print("\n[2/3] Testing Linter...")
        from implementations.linter_agent import LinterAgent
        linter = LinterAgent()
        result = linter.process({"files": {"main.py": "print('hello')"}})
        print(f"✓ Linter: OK (Score: {result.get('quality_score', 0):.1f})")
        results.append(("Linter", True))
    except Exception as e:
        print(f"✗ Linter: FAIL - {e}")
        results.append(("Linter", False))
    
    # Test Auditor
    try:
        print("\n[3/3] Testing Auditor...")
        from implementations.auditor_agent import AuditorAgent
        auditor = AuditorAgent()
        result = auditor.process([
            {"actor": "test", "action": "test_action", "resource": "test", "details": {}}
        ])
        print(f"✓ Auditor: OK (Events: {result.get('events_logged', 0)})")
        results.append(("Auditor", True))
    except Exception as e:
        print(f"✗ Auditor: FAIL - {e}")
        results.append(("Auditor", False))
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN AGENTES MECÁNICOS")
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
    print("FRAMEWORK v3.0 - TEST COMPLETO CON 8 AGENTES")
    print("="*70)
    
    # Test agentes mecánicos
    mechanical_ok = test_individual_mechanical_agents()
    
    # Test flujo completo
    workflow_ok = test_complete_8_agent_workflow()
    
    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)
    print(f"Agentes Mecánicos: {'✓ PASS' if mechanical_ok else '✗ FAIL'}")
    print(f"Flujo Completo (8 agentes): {'✓ PASS' if workflow_ok else '✗ FAIL'}")
    
    if mechanical_ok and workflow_ok:
        print("\n🎉🎉🎉 TODOS LOS TESTS PASARON! 🎉🎉🎉")
        print("\n✅ Framework v3.0 COMPLETO y FUNCIONAL con 8 agentes:")
        print("   1. Arquitecto (LLM + Peer Review)")
        print("   2. UI/UX Designer (LLM + Peer Review)")
        print("   3. Sentinel (LLM + 3D Risk)")
        print("   4. Coder (LLM + Executable Feedback)")
        print("   5. Test Designer (LLM + Peer Review)")
        print("   6. Test Executor (Mecánico)")
        print("   7. Linter (Mecánico)")
        print("   8. Auditor (Mecánico)")
        return 0
    else:
        print("\n⚠️  Algunos tests fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
