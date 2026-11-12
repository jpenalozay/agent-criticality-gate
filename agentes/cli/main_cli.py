#!/usr/bin/env python3
"""
CLI Principal del Framework Multi-Agente

Interfaz de línea de comandos para interactuar con el framework.
"""

import sys
import argparse
import logging
from pathlib import Path

# Agregar directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from agentes.core.coordinator import Coordinator
from agentes.core.state_manager import TaskStatus
from agentes.core.auditor import get_auditor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_create(args):
    """Comando: crear nueva tarea."""
    requirement = args.requirement
    
    print(f"\n{'='*70}")
    print("🚀 Creating new task...")
    print(f"{'='*70}\n")
    print(f"Requirement: {requirement}\n")
    
    # Crear coordinador
    coordinator = Coordinator()
    
    # Crear tarea
    task_id = coordinator.create_task(requirement)
    print(f"✅ Task created: {task_id}\n")
    
    # Procesar tarea
    print("🔄 Processing task...\n")
    try:
        result = coordinator.process_task(task_id)
        
        # Mostrar resumen
        print(f"\n{'='*70}")
        print(result["summary"])
        print(f"{'='*70}\n")
        
        # Mostrar archivos generados
        files = result["code_artifacts"]["files"]
        print(f"📁 Files generated ({len(files)}):")
        for filepath in sorted(files.keys()):
            print(f"  - {filepath}")
        print()
        
        # Guardar archivos si se solicita
        if args.output:
            output_dir = Path(args.output)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for filepath, content in files.items():
                full_path = output_dir / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            
            print(f"✅ Files saved to: {output_dir}\n")
        
        print(f"✅ Task completed successfully!\n")
        
    except Exception as e:
        print(f"\n❌ Error processing task: {e}\n")
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


def cmd_status(args):
    """Comando: ver estado de tarea."""
    task_id = args.task_id
    
    coordinator = Coordinator()
    task = coordinator.get_task_status(task_id)
    
    if not task:
        print(f"\n❌ Task not found: {task_id}\n")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"Task Status: {task_id}")
    print(f"{'='*70}\n")
    print(f"Status: {task['status']}")
    print(f"Current Agent: {task.get('current_agent', 'N/A')}")
    print(f"Risk Score: {task.get('risk_score', 'N/A')}")
    print(f"Created: {task['created_at']}")
    print(f"Updated: {task['updated_at']}")
    
    if task.get('completed_at'):
        print(f"Completed: {task['completed_at']}")
    
    print()


def cmd_list(args):
    """Comando: listar tareas."""
    coordinator = Coordinator()
    
    # Filtrar por estado si se especifica
    status = None
    if args.status:
        status = TaskStatus(args.status)
    
    tasks = coordinator.list_tasks(status=status, limit=args.limit)
    
    print(f"\n{'='*70}")
    print(f"Tasks ({len(tasks)})")
    print(f"{'='*70}\n")
    
    if not tasks:
        print("No tasks found.\n")
        return
    
    for task in tasks:
        print(f"ID: {task['task_id']}")
        print(f"  Status: {task['status']}")
        print(f"  Risk: {task.get('risk_score', 'N/A')}")
        print(f"  Created: {task['created_at']}")
        print()


def cmd_logs(args):
    """Comando: ver logs de auditoría."""
    task_id = args.task_id
    
    auditor = get_auditor()
    report = auditor.generate_report(task_id)
    
    print(f"\n{report}\n")


def cmd_config(args):
    """Comando: mostrar configuración."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print(f"\n{'='*70}")
    print("Configuration")
    print(f"{'='*70}\n")
    
    print(f"DeepSeek API Key: {'✅ Set' if os.getenv('DEEPSEEK_API_KEY') else '❌ Not set'}")
    print(f"DeepSeek Model: {os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')}")
    print(f"Database Path: {os.getenv('DATABASE_PATH', './data/framework.db')}")
    print(f"Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    print()


def main():
    """Función principal del CLI."""
    parser = argparse.ArgumentParser(
        description="Framework Multi-Agente CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new task
  python cli/main_cli.py create "Create a REST API for user management"
  
  # Create task and save output
  python cli/main_cli.py create "Create a calculator function" --output ./output
  
  # Check task status
  python cli/main_cli.py status task_abc123
  
  # List all tasks
  python cli/main_cli.py list
  
  # List only completed tasks
  python cli/main_cli.py list --status completed
  
  # View audit logs
  python cli/main_cli.py logs task_abc123
  
  # Show configuration
  python cli/main_cli.py config
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Comando: create
    parser_create = subparsers.add_parser('create', help='Create a new task')
    parser_create.add_argument('requirement', help='Task requirement in natural language')
    parser_create.add_argument('--output', '-o', help='Output directory for generated files')
    parser_create.set_defaults(func=cmd_create)
    
    # Comando: status
    parser_status = subparsers.add_parser('status', help='Get task status')
    parser_status.add_argument('task_id', help='Task ID')
    parser_status.set_defaults(func=cmd_status)
    
    # Comando: list
    parser_list = subparsers.add_parser('list', help='List tasks')
    parser_list.add_argument('--status', '-s', help='Filter by status')
    parser_list.add_argument('--limit', '-l', type=int, default=10, help='Limit results')
    parser_list.set_defaults(func=cmd_list)
    
    # Comando: logs
    parser_logs = subparsers.add_parser('logs', help='View audit logs')
    parser_logs.add_argument('task_id', help='Task ID')
    parser_logs.set_defaults(func=cmd_logs)
    
    # Comando: config
    parser_config = subparsers.add_parser('config', help='Show configuration')
    parser_config.set_defaults(func=cmd_config)
    
    # Parsear argumentos
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Ejecutar comando
    args.func(args)


if __name__ == "__main__":
    main()
