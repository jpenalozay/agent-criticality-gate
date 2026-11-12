"""
Code Executor - Ejecuta código en sandbox Docker

Ejecuta código generado en un contenedor Docker aislado con límites de recursos.
"""

import logging
import docker
import tempfile
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Resultado de ejecución de código."""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    runtime_ms: int
    errors: list


class CodeExecutor:
    """
    Ejecutor de código en sandbox Docker.
    
    Características:
    - Aislamiento completo
    - Límites de recursos (CPU, memoria, tiempo)
    - Captura de stdout/stderr
    - Timeout configurable
    """
    
    def __init__(
        self,
        image: str = "python:3.11-slim",
        timeout: int = 60,
        max_memory: str = "512m",
        max_cpu: float = 1.0
    ):
        """
        Inicializa executor.
        
        Args:
            image: Imagen Docker a usar
            timeout: Timeout en segundos
            max_memory: Límite de memoria
            max_cpu: Límite de CPU
        """
        try:
            self.client = docker.from_env()
            self.image = image
            self.timeout = timeout
            self.max_memory = max_memory
            self.max_cpu = max_cpu
            
            # Verificar que la imagen existe
            try:
                self.client.images.get(self.image)
            except docker.errors.ImageNotFound:
                logger.info(f"Pulling image: {self.image}")
                self.client.images.pull(self.image)
            
            logger.info(f"Code Executor initialized with image: {self.image}")
            
        except Exception as e:
            logger.error(f"Error initializing Docker client: {e}")
            logger.warning("Code execution will be disabled")
            self.client = None
    
    def execute(
        self,
        code: str,
        language: str = "python",
        filename: str = "main.py"
    ) -> ExecutionResult:
        """
        Ejecuta código en sandbox.
        
        Args:
            code: Código a ejecutar
            language: Lenguaje (python, javascript, etc)
            filename: Nombre del archivo
            
        Returns:
            Resultado de la ejecución
        """
        if not self.client:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="Docker not available",
                exit_code=-1,
                runtime_ms=0,
                errors=["Docker client not initialized"]
            )
        
        start_time = time.time()
        
        try:
            # Crear directorio temporal
            with tempfile.TemporaryDirectory() as tmpdir:
                # Escribir código a archivo
                code_path = os.path.join(tmpdir, filename)
                with open(code_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                # Ejecutar en container
                try:
                    container = self.client.containers.run(
                        image=self.image,
                        command=self._get_command(language, filename),
                        volumes={tmpdir: {'bind': '/code', 'mode': 'rw'}},
                        working_dir='/code',
                        mem_limit=self.max_memory,
                        cpu_quota=int(self.max_cpu * 100000),
                        network_disabled=True,
                        detach=True,
                        remove=True
                    )
                    
                    # Esperar resultado con timeout
                    result = container.wait(timeout=self.timeout)
                    exit_code = result['StatusCode']
                    
                    # Obtener logs
                    logs = container.logs()
                    stdout = logs.decode('utf-8', errors='ignore')
                    stderr = ""
                    
                    runtime_ms = int((time.time() - start_time) * 1000)
                    
                    success = exit_code == 0
                    errors = [] if success else [f"Exit code: {exit_code}"]
                    
                    return ExecutionResult(
                        success=success,
                        stdout=stdout,
                        stderr=stderr,
                        exit_code=exit_code,
                        runtime_ms=runtime_ms,
                        errors=errors
                    )
                    
                except docker.errors.ContainerError as e:
                    runtime_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=str(e),
                        exit_code=e.exit_status,
                        runtime_ms=runtime_ms,
                        errors=[f"Container error: {e}"]
                    )
                
                except Exception as e:
                    runtime_ms = int((time.time() - start_time) * 1000)
                    return ExecutionResult(
                        success=False,
                        stdout="",
                        stderr=str(e),
                        exit_code=-1,
                        runtime_ms=runtime_ms,
                        errors=[f"Execution error: {e}"]
                    )
        
        except Exception as e:
            runtime_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Error executing code: {e}")
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                runtime_ms=runtime_ms,
                errors=[f"Setup error: {e}"]
            )
    
    def _get_command(self, language: str, filename: str) -> list:
        """Obtiene comando de ejecución según lenguaje."""
        if language == "python":
            return ["python", filename]
        elif language == "javascript":
            return ["node", filename]
        else:
            return ["sh", "-c", f"cat {filename}"]
    
    def execute_with_tests(
        self,
        code: str,
        tests: str,
        language: str = "python"
    ) -> ExecutionResult:
        """
        Ejecuta código con tests.
        
        Args:
            code: Código principal
            tests: Código de tests
            language: Lenguaje
            
        Returns:
            Resultado de ejecución de tests
        """
        # Combinar código y tests
        combined_code = f"{code}\n\n{tests}"
        
        return self.execute(combined_code, language, "test_main.py")
