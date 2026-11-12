#!/usr/bin/env python3
"""
Script principal para ejecutar el sistema de file watchers.

Este script inicia el monitoreo de archivos y activa automáticamente
los agentes correspondientes cuando se detectan cambios.

Uso:
    python -m agentes.watchers.main
    # o
    python agentes/watchers/main.py
"""

import sys
import logging
import signal
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

try:
    from agentes.core.agent_activation import start_file_watchers
    from agentes.core.file_watcher import FILE_WATCHER_AVAILABLE
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("Asegúrate de estar en el directorio raíz del proyecto")
    sys.exit(1)


def setup_logging(level=logging.INFO):
    """Configura el sistema de logging."""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Función principal."""
    if not FILE_WATCHER_AVAILABLE:
        print("❌ Biblioteca 'watchdog' no está instalada")
        print("Instala con: pip install watchdog")
        sys.exit(1)
    
    setup_logging()
    logger = logging.getLogger("main")
    
    logger.info("🚀 Iniciando sistema de file watchers...")
    logger.info("=" * 60)
    
    try:
        # Iniciar file watchers
        manager = start_file_watchers(
            specs_dir="agentes/specs/agents",
            root_dir=str(Path.cwd()),
            use_custom_activation=True
        )
        
        if not manager or len(manager.watchers) == 0:
            logger.error("❌ No se pudieron iniciar los watchers")
            sys.exit(1)
        
        logger.info("=" * 60)
        logger.info("👀 File watchers activos. Monitoreando archivos...")
        logger.info("   Presiona Ctrl+C para detener")
        logger.info("=" * 60)
        
        # Manejar señal de interrupción
        def signal_handler(sig, frame):
            logger.info("\n🛑 Señal de interrupción recibida")
            manager.stop()
            logger.info("✅ File watchers detenidos")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Mantener ejecución
        import time
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupción del usuario")
        if 'manager' in locals():
            manager.stop()
        logger.info("✅ File watchers detenidos")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

