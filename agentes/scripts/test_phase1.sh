#!/bin/bash

# Script para ejecutar tests de la Fase 1

echo "🧪 Ejecutando tests de Fase 1..."
echo ""

# Verificar que Docker esté corriendo
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo"
    echo "Por favor inicia Docker Desktop y vuelve a intentar"
    exit 1
fi

# Verificar que los servicios estén corriendo
echo "📊 Verificando servicios..."
cd docker
docker-compose -f docker-compose.infra.yml ps

# Esperar a que los servicios estén listos
echo ""
echo "⏳ Esperando a que los servicios estén listos..."
sleep 5

# Volver a la raíz
cd ..

# Ejecutar tests de Go
echo ""
echo "🐹 Ejecutando tests de Go..."
echo ""

# Event Bus tests
echo "Testing Event Bus..."
go test ./go/eventbus -v -timeout=30s

# State Manager tests
echo ""
echo "Testing State Manager..."
go test ./go/state -v -timeout=30s

# Document Store tests
echo ""
echo "Testing Document Store..."
go test ./go/docstore -v -timeout=30s

# Benchmarks
echo ""
echo "📈 Ejecutando benchmarks..."
echo ""

echo "Benchmark Event Bus..."
go test ./go/eventbus -bench=. -benchmem -benchtime=5s

echo ""
echo "Benchmark State Manager..."
go test ./go/state -bench=. -benchmem -benchtime=5s

# Coverage
echo ""
echo "📊 Generando reporte de coverage..."
go test ./go/... -coverprofile=coverage.out
go tool cover -func=coverage.out

echo ""
echo "✅ Tests completados!"
echo ""
echo "Para ver el reporte de coverage en HTML:"
echo "  go tool cover -html=coverage.out"
