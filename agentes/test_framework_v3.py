"""
Test básico del Framework v3.0

Valida que los componentes core funcionan correctamente.
"""

import sys
import os

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv()

# Agregar path del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_llm_client():
    """Test del LLM client con DeepSeek."""
    print("\n=== Test 1: LLM Client ===")
    
    try:
        from core.llm_client_v3 import get_llm_client
        
        # Obtener cliente
        client = get_llm_client()
        print(f"✓ LLM Client initialized: {client.config.provider}/{client.config.model}")
        
        # Test simple
        response = client.generate(
            prompt="Di 'Hola Framework v3.0' en una línea",
            temperature=0.1,
            max_tokens=50
        )
        print(f"✓ LLM Response: {response[:100]}...")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_sop_validator():
    """Test del validador de SOPs."""
    print("\n=== Test 2: SOP Validator ===")
    
    try:
        from core.sop_validator import SOPValidator
        
        validator = SOPValidator()
        print(f"✓ SOP Validator initialized with {len(validator.sops)} SOPs")
        
        # Test validación de blueprint
        test_blueprint = {
            "name": "test_api",
            "type": "api",
            "components": {
                "main": {
                    "type": "backend",
                    "tech": "fastapi"
                }
            }
        }
        
        is_valid, errors, score = validator.validate_output("arquitecto", test_blueprint)
        print(f"✓ Validation result: valid={is_valid}, score={score:.2f}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_code_executor():
    """Test del ejecutor de código."""
    print("\n=== Test 3: Code Executor ===")
    
    try:
        from core.code_executor import CodeExecutor
        
        executor = CodeExecutor()
        
        if not executor.client:
            print("⚠ Docker not available, skipping execution test")
            return True
        
        print("✓ Code Executor initialized")
        
        # Test código simple
        test_code = """
print("Hello from sandbox!")
result = 2 + 2
print(f"2 + 2 = {result}")
"""
        
        result = executor.execute(test_code)
        print(f"✓ Execution result: success={result.success}, runtime={result.runtime_ms}ms")
        if result.stdout:
            print(f"  Output: {result.stdout[:100]}")
        
        return result.success
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_toon_parser():
    """Test del parser TOON."""
    print("\n=== Test 4: TOON Parser ===")
    
    try:
        from core.toon_parser import to_toon, from_toon
        
        # Test serialización
        test_data = {
            "name": "test_system",
            "type": "api",
            "components": {
                "service": {
                    "type": "backend",
                    "tech": "python"
                }
            }
        }
        
        toon_str = to_toon(test_data)
        print(f"✓ TOON serialization: {len(toon_str)} chars")
        print(f"  Preview: {toon_str[:100]}...")
        
        # Test deserialización
        parsed = from_toon(toon_str)
        print(f"✓ TOON deserialization: {len(parsed)} keys")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def main():
    """Ejecuta todos los tests."""
    print("=" * 60)
    print("Framework v3.0 - Tests Básicos")
    print("=" * 60)
    
    tests = [
        ("LLM Client", test_llm_client),
        ("SOP Validator", test_sop_validator),
        ("Code Executor", test_code_executor),
        ("TOON Parser", test_toon_parser),
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
    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Todos los tests pasaron!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
