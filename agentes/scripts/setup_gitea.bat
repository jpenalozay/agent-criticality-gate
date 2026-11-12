@echo off
REM Script para setup completo de Gitea + Framework

echo 🚀 Setup de Gitea + Framework Multi-Agente
echo.

REM Verificar Docker
docker ps >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker no está corriendo
    exit /b 1
)

REM Levantar infraestructura
echo 📦 Levantando infraestructura (NATS, Redis, Postgres, Gitea)...
cd docker
docker-compose -f docker-compose.infra.yml up -d

echo.
echo ⏳ Esperando a que los servicios estén listos (30 segundos)...
timeout /t 30 /nobreak >nul

REM Verificar servicios
echo.
echo ✅ Servicios corriendo:
docker-compose -f docker-compose.infra.yml ps

cd ..

REM Compilar servicios Go
echo.
echo 🔨 Compilando servicios Go...
go build -o bin\framework.exe go\cmd\main.go

echo.
echo ✅ Setup completado!
echo.
echo 📋 Próximos pasos:
echo.
echo 1. Abrir Gitea: http://localhost:3000
echo    - Completar instalación inicial
echo    - Crear usuario admin
echo    - Crear organización 'framework'
echo    - Crear repositorio 'docs-architecture'
echo.
echo 2. Generar token de API:
echo    - Settings → Applications → Generate New Token
echo    - Copiar token
echo.
echo 3. Configurar framework:
echo    - Editar config\go_services.yaml
echo    - Pegar token en gitea.token
echo.
echo 4. Iniciar framework:
echo    - bin\framework.exe
echo.
echo 📚 Ver guía completa: SETUP_GITEA.md

pause
