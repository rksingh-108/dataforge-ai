@echo off
REM ============================================================================
REM  DataForge AI - START.bat
REM ----------------------------------------------------------------------------
REM  Starts the complete local development stack with Docker Compose.
REM
REM  Services started (see docker-compose.yml):
REM      db, redis, api, worker, ai-service, web
REM
REM  This script is a convenience wrapper around the project's own Compose
REM  configuration. It does NOT contain any credentials: all secrets come from
REM  your local `.env` file, which is git-ignored.
REM
REM  Safe to run repeatedly: `docker compose up -d` is idempotent, so an
REM  already-running stack is left as-is.
REM
REM  Usage:  START.bat
REM ============================================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PROJECT_ROOT=%CD%"
set "COMPOSE=docker compose"
set "HEALTH_TIMEOUT_SECONDS=180"

echo.
echo ============================================================================
echo   DataForge AI - starting local development environment
echo ============================================================================
echo   Project root: %PROJECT_ROOT%
echo.

REM ---------------------------------------------------------------------------
REM 1. Is Docker available and is the daemon running?
REM ---------------------------------------------------------------------------
echo [1/6] Checking Docker...

where docker >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERROR] Docker was not found on PATH.
    echo   Install Docker Desktop: https://docs.docker.com/get-docker/
    echo.
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERROR] Docker is installed but the daemon is not reachable.
    echo   Start Docker Desktop and wait for it to report "running", then retry.
    echo.
    exit /b 1
)

%COMPOSE% version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERROR] "docker compose" is unavailable. Update Docker Desktop so that
    echo   the Compose v2 plugin is installed.
    echo.
    exit /b 1
)
echo       Docker is available.
echo.

REM ---------------------------------------------------------------------------
REM 2. Ensure a .env exists. Never generate or print secrets.
REM ---------------------------------------------------------------------------
echo [2/6] Checking environment file (.env)...

if not exist "%PROJECT_ROOT%\.env" (
    echo       No .env found - creating one from .env.example.
    copy /y "%PROJECT_ROOT%\.env.example" "%PROJECT_ROOT%\.env" >nul
    if errorlevel 1 (
        echo.
        echo   [ERROR] Could not create .env from .env.example.
        echo.
        exit /b 1
    )
    echo.
    echo   [ACTION REQUIRED] .env was created with placeholder values.
    echo   Open %PROJECT_ROOT%\.env and replace the placeholder secrets, at minimum:
    echo       DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DATAFORGE_FERNET_KEY,
    echo       INTERNAL_SERVICE_TOKEN
    echo   Then run START.bat again.
    echo.
    exit /b 1
)
echo       Using existing .env.
echo.

REM ---------------------------------------------------------------------------
REM 3. Note whether the stack is already running (graceful re-run).
REM ---------------------------------------------------------------------------
echo [3/6] Checking current stack status...

set "RUNNING="
for /f "delims=" %%i in ('%COMPOSE% ps -q 2^>nul') do set "RUNNING=%%i"

if defined RUNNING (
    echo       Some DataForge services are already running; they will be reused.
) else (
    echo       No DataForge services are currently running.
)
echo.

REM ---------------------------------------------------------------------------
REM 4. Build and start the stack.
REM ---------------------------------------------------------------------------
echo [4/6] Building and starting services (first run can take a few minutes)...
echo.

%COMPOSE% up -d --build
if errorlevel 1 (
    echo.
    echo   [ERROR] "docker compose up" failed. Recent service logs:
    echo   ----------------------------------------------------------------------
    %COMPOSE% logs --tail=40
    echo   ----------------------------------------------------------------------
    echo   Fix the error above, then run START.bat again.
    echo.
    exit /b 1
)
echo.
echo       Services started.
echo.

REM ---------------------------------------------------------------------------
REM 5. Wait for readiness.
REM     - db and redis expose Docker healthchecks, so we poll their health.
REM     - api is "ready" when its /_health/ endpoint answers (it runs migrations
REM       on start, so this can take a little while on a cold database).
REM ---------------------------------------------------------------------------
echo [5/6] Waiting for services to become ready...

call :wait_for_healthy db 60
if errorlevel 1 goto :not_ready

call :wait_for_healthy redis 60
if errorlevel 1 goto :not_ready

call :wait_for_api
if errorlevel 1 goto :not_ready

echo       Database, cache and API are ready.
echo.

REM ---------------------------------------------------------------------------
REM 6. Report the URLs a developer needs.
REM ---------------------------------------------------------------------------
echo [6/6] Development environment is READY.
echo.
echo ============================================================================
echo   DataForge AI is running
echo ============================================================================
echo.
echo   Web application   : http://localhost:3000
echo   API (root)        : http://localhost:8000
echo   API health        : http://localhost:8000/_health/
echo   AI service health : http://localhost:8001/_health/
echo.
echo   Useful commands:
echo       %COMPOSE% ps                  - service status
echo       %COMPOSE% logs -f --tail=100  - follow logs
echo       %COMPOSE% exec api python manage.py seed_development
echo                                     - create the development org/users
echo       STOP.bat                      - stop the environment (data is kept)
echo.
echo   Note: the AI service needs LLM_API_KEY / EMBEDDING_API_KEY in .env to
echo   answer analyst questions. The stack runs without them; AI calls fail
echo   with a clear error until they are set.
echo.
exit /b 0


REM ===========================================================================
REM  Subroutines
REM ===========================================================================

:not_ready
echo.
echo   [ERROR] The stack did not become ready in time.
echo   Current status:
%COMPOSE% ps
echo.
echo   Recent logs:
echo   --------------------------------------------------------------------------
%COMPOSE% logs --tail=40
echo   --------------------------------------------------------------------------
echo   Inspect a single service with:  %COMPOSE% logs -f api
echo.
exit /b 1


:wait_for_healthy
REM %1 = service name, %2 = timeout seconds. Polls the container healthcheck.
set "SVC=%~1"
set "DEADLINE=%~2"
set /a "WAITED=0"
:wait_for_healthy_loop
set "CID="
for /f "delims=" %%i in ('%COMPOSE% ps -q %SVC% 2^>nul') do set "CID=%%i"
if not defined CID (
    echo       [wait] %SVC%: container not created yet...
    goto :wait_for_healthy_tick
)
for /f "delims=" %%s in ('docker inspect --format "{{.State.Health.Status}}" !CID! 2^>nul') do set "STATUS=%%s"
if /i "!STATUS!"=="healthy" (
    echo       %SVC% is healthy.
    exit /b 0
)
echo       [wait] %SVC%: !STATUS!...
:wait_for_healthy_tick
if !WAITED! GEQ !DEADLINE! exit /b 1
timeout /t 3 /nobreak >nul
set /a "WAITED+=3"
goto :wait_for_healthy_loop


:wait_for_api
REM Polls the API health endpoint; the API applies migrations on start.
set /a "WAITED=0"
:wait_for_api_loop
curl -fsS http://localhost:8000/_health/ >nul 2>&1
if not errorlevel 1 (
    echo       api is healthy.
    exit /b 0
)
echo       [wait] api: not ready yet...
if !WAITED! GEQ %HEALTH_TIMEOUT_SECONDS% exit /b 1
timeout /t 3 /nobreak >nul
set /a "WAITED+=3"
goto :wait_for_api_loop
