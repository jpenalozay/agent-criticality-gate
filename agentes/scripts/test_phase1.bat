@echo off
REM Script para ejecutar tests de la Fase 1 en Windows

echo 🧪 Ejecutando tests de Fase 1...
echo.

REM Verificar que Docker esté corriendo
docker ps >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker no está corriendo
    echo Por favor inicia Docker Desktop y vuelve a intentar
    exit /b 1
)

REM Verificar que los servicios estén corriendo
echo 📊 Verificando servicios...
cd docker
docker-compose -f docker-compose.infra.yml ps

REM Esperar a que los servicios estén listos
echo.
echo ⏳ Esperando a que los servicios estén listos...
timeout /t 5 /nobreak >nul

REM Volver a la raíz
cd ..

REM Ejecutar tests de Go
echo.
echo 🐹 Ejecutando tests de Go...
echo.

REM Event Bus tests
echo Testing Event Bus...
go test ./go/eventbus -v -timeout=30s

REM State Manager tests
echo.
echo Testing State Manager...
go test ./go/state -v -timeout=30s

REM Document Store tests
echo.
echo Testing Document Store...
go test ./go/docstore -v -timeout=30s

REM Benchmarks
echo.
echo 📈 Ejecutando benchmarks...
echo.

echo Benchmark Event Bus...
go test ./go/eventbus -bench=. -benchmem -benchtime=5s

echo.
echo Benchmark State Manager...
go test ./go/state -bench=. -benchmem -benchtime=5s

REM Coverage
echo.
echo 📊 Generando reporte de coverage...
go test ./go/... -coverprofile=coverage.out
go tool cover -func=coverage.out

echo.
echo ✅ Tests completados!
echo.
echo Para ver el reporte de coverage en HTML:
echo   go tool cover -html=coverage.out

pause
