#!/usr/bin/env bash
# Script de ayuda para Docker Compose

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_help() {
    echo "🐳 Docker Compose Helper para Sistema de Agentes"
    echo ""
    echo "Uso: ./docker-helper.sh [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo "  start [service]    - Inicia servicios (redis, all, tools)"
    echo "  stop [service]     - Detiene servicios"
    echo "  restart [service]  - Reinicia servicios"
    echo "  logs [service]     - Muestra logs"
    echo "  status            - Muestra estado de servicios"
    echo "  clean              - Elimina contenedores y volúmenes"
    echo "  shell [service]    - Abre shell en contenedor"
    echo "  redis-cli          - Abre redis-cli"
    echo "  test               - Prueba conexión a Redis"
    echo ""
    echo "Ejemplos:"
    echo "  ./docker-helper.sh start redis"
    echo "  ./docker-helper.sh start tools"
    echo "  ./docker-helper.sh logs redis"
    echo "  ./docker-helper.sh redis-cli"
}

start_service() {
    local service="${1:-redis}"
    
    case "$service" in
        redis)
            echo -e "${GREEN}🚀 Iniciando Redis...${NC}"
            docker-compose up -d redis
            ;;
        tools)
            echo -e "${GREEN}🚀 Iniciando Redis + Redis Commander...${NC}"
            docker-compose --profile tools up -d
            ;;
        all)
            echo -e "${GREEN}🚀 Iniciando todos los servicios...${NC}"
            docker-compose up -d
            ;;
        *)
            echo -e "${GREEN}🚀 Iniciando servicio: $service...${NC}"
            docker-compose up -d "$service"
            ;;
    esac
    
    echo -e "${GREEN}✅ Servicios iniciados${NC}"
    docker-compose ps
}

stop_service() {
    local service="${1:-}"
    
    if [ -z "$service" ]; then
        echo -e "${YELLOW}🛑 Deteniendo todos los servicios...${NC}"
        docker-compose stop
    else
        echo -e "${YELLOW}🛑 Deteniendo servicio: $service...${NC}"
        docker-compose stop "$service"
    fi
    
    echo -e "${GREEN}✅ Servicios detenidos${NC}"
}

restart_service() {
    local service="${1:-redis}"
    
    echo -e "${YELLOW}🔄 Reiniciando servicio: $service...${NC}"
    docker-compose restart "$service"
    echo -e "${GREEN}✅ Servicio reiniciado${NC}"
}

show_logs() {
    local service="${1:-}"
    
    if [ -z "$service" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$service"
    fi
}

show_status() {
    echo -e "${GREEN}📊 Estado de servicios:${NC}"
    docker-compose ps
    echo ""
    echo -e "${GREEN}📦 Volúmenes:${NC}"
    docker volume ls | grep redis_data || echo "  No hay volúmenes"
}

clean_all() {
    echo -e "${RED}⚠️  Esto eliminará todos los contenedores y volúmenes${NC}"
    read -p "¿Estás seguro? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🧹 Limpiando...${NC}"
        docker-compose down -v
        echo -e "${GREEN}✅ Limpieza completada${NC}"
    else
        echo "Cancelado"
    fi
}

shell_service() {
    local service="${1:-redis}"
    
    case "$service" in
        redis)
            echo -e "${GREEN}🐚 Abriendo shell en Redis...${NC}"
            docker-compose exec redis sh
            ;;
        *)
            echo -e "${GREEN}🐚 Abriendo shell en $service...${NC}"
            docker-compose exec "$service" sh
            ;;
    esac
}

redis_cli() {
    echo -e "${GREEN}🔧 Abriendo redis-cli...${NC}"
    docker-compose exec redis redis-cli
}

test_redis() {
    echo -e "${GREEN}🧪 Probando conexión a Redis...${NC}"
    
    if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
        echo -e "${GREEN}✅ Redis está funcionando correctamente${NC}"
        
        echo ""
        echo "Información del servidor:"
        docker-compose exec -T redis redis-cli INFO server | head -10
        
        echo ""
        echo "Uso de memoria:"
        docker-compose exec -T redis redis-cli INFO memory | grep used_memory_human
        
        echo ""
        echo "Conexiones:"
        docker-compose exec -T redis redis-cli INFO clients | grep connected_clients
        
        echo ""
        echo "Keys existentes:"
        key_count=$(docker-compose exec -T redis redis-cli DBSIZE)
        echo "  Total keys: $key_count"
    else
        echo -e "${RED}❌ Redis no está respondiendo${NC}"
        exit 1
    fi
}

# Main
case "${1:-help}" in
    start)
        start_service "${2:-redis}"
        ;;
    stop)
        stop_service "${2:-}"
        ;;
    restart)
        restart_service "${2:-redis}"
        ;;
    logs)
        show_logs "${2:-}"
        ;;
    status)
        show_status
        ;;
    clean)
        clean_all
        ;;
    shell)
        shell_service "${2:-redis}"
        ;;
    redis-cli)
        redis_cli
        ;;
    test)
        test_redis
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo -e "${RED}❌ Comando desconocido: $1${NC}"
        echo ""
        print_help
        exit 1
        ;;
esac

