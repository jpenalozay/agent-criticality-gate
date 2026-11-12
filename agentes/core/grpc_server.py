"""
gRPC Server - Python

Servidor gRPC que expone el framework a servicios Go.
"""

import logging
import grpc
from concurrent import futures
import json

# Importar proto generado (requiere compilación previa)
# python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. proto/services.proto
try:
    import services_pb2
    import services_pb2_grpc
except ImportError:
    logging.warning("Proto files not compiled. Run: python -m grpc_tools.protoc -I./proto --python_out=. --grpc_python_out=. proto/services.proto")
    services_pb2 = None
    services_pb2_grpc = None

from core.coordinator_v3 import CoordinatorV3
from implementations.auditor_agent import AuditorAgent

logger = logging.getLogger(__name__)


class AgentFrameworkServicer:
    """Implementación del servicio gRPC."""
    
    def __init__(self):
        """Inicializa servicer."""
        self.coordinator = CoordinatorV3(
            enable_peer_review=True,
            enable_executable_feedback=True
        )
        self.auditor = AuditorAgent()
        self.tasks = {}  # Cache de tareas en memoria
        
        logger.info("gRPC Servicer initialized")
    
    def ProcessRequirement(self, request, context):
        """Procesa requerimiento completo."""
        try:
            logger.info(f"Processing requirement: {request.requirement[:50]}...")
            
            # Procesar con coordinator
            result = self.coordinator.process(
                requirement=request.requirement,
                context=dict(request.context) if request.context else None
            )
            
            # Guardar en cache
            task_id = result.get('task_id')
            self.tasks[task_id] = result
            
            # Convertir a proto
            return self._result_to_proto(result)
            
        except Exception as e:
            logger.error(f"Error processing requirement: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return services_pb2.ProcessResult()
    
    def GetTaskStatus(self, request, context):
        """Obtiene estado de una tarea."""
        task_id = request.task_id
        
        if task_id in self.tasks:
            result = self.tasks[task_id]
            return services_pb2.TaskStatus(
                task_id=task_id,
                status=result.get('status', 'unknown'),
                progress_percent=100 if result.get('status') == 'completed' else 50,
                current_agent='completed',
                elapsed_time_ms=result.get('total_time_ms', 0)
            )
        else:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Task {task_id} not found")
            return services_pb2.TaskStatus()
    
    def ListTasks(self, request, context):
        """Lista tareas recientes."""
        limit = request.limit if request.limit > 0 else 10
        offset = request.offset if request.offset >= 0 else 0
        
        tasks = []
        for task_id, result in list(self.tasks.items())[offset:offset+limit]:
            tasks.append(services_pb2.TaskInfo(
                task_id=task_id,
                requirement=result.get('requirement', ''),
                status=result.get('status', 'unknown'),
                created_at=0,  # TODO: agregar timestamp
                completed_at=0
            ))
        
        return services_pb2.TaskList(
            tasks=tasks,
            total=len(self.tasks)
        )
    
    def GetAuditLogs(self, request, context):
        """Obtiene logs de auditoría."""
        try:
            logs = self.auditor.get_log(limit=request.limit if request.limit > 0 else 100)
            
            events = []
            for log in logs:
                events.append(services_pb2.AuditEvent(
                    id=log.get('id', ''),
                    timestamp=log.get('timestamp', ''),
                    actor=log.get('actor', ''),
                    action=log.get('action', ''),
                    resource=log.get('resource', ''),
                    details={k: str(v) for k, v in log.get('details', {}).items()},
                    checksum=log.get('checksum', '')
                ))
            
            return services_pb2.AuditLogs(
                events=events,
                total=len(events)
            )
            
        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return services_pb2.AuditLogs()
    
    def _result_to_proto(self, result: dict):
        """Convierte resultado Python a proto."""
        # Por simplicidad, retornar estructura básica
        # En producción, mapear cada campo correctamente
        
        summary = result.get('summary', {})
        
        return services_pb2.ProcessResult(
            task_id=result.get('task_id', ''),
            status=result.get('status', 'unknown'),
            total_time_ms=result.get('total_time_ms', 0),
            summary=services_pb2.Summary(
                architecture=services_pb2.ArchitectureSummary(
                    name=summary.get('architecture', {}).get('name', ''),
                    components=summary.get('architecture', {}).get('components', 0),
                    sop_compliance=summary.get('architecture', {}).get('sop_compliance', 0)
                ),
                risk=services_pb2.RiskSummary(
                    score=summary.get('risk', {}).get('score', 0),
                    level=summary.get('risk', {}).get('level', ''),
                    decision=summary.get('risk', {}).get('decision', '')
                ),
                testing=services_pb2.TestingSummary(
                    tests_designed=summary.get('testing', {}).get('tests_designed', 0),
                    tests_passed=summary.get('testing', {}).get('tests_passed', 0),
                    tests_failed=summary.get('testing', {}).get('tests_failed', 0),
                    coverage=summary.get('testing', {}).get('coverage', 0)
                ),
                quality=services_pb2.QualitySummary(
                    score=summary.get('quality', {}).get('score', 0),
                    issues=summary.get('quality', {}).get('issues', 0)
                )
            ),
            error=result.get('error', '')
        )


def serve(port: int = 50051):
    """Inicia servidor gRPC."""
    if not services_pb2_grpc:
        logger.error("Proto files not compiled. Cannot start server.")
        return
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    services_pb2_grpc.add_AgentFrameworkServicer_to_server(
        AgentFrameworkServicer(),
        server
    )
    
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    
    logger.info(f"gRPC server started on port {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down gRPC server...")
        server.stop(0)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()
