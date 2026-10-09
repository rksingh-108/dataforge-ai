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
REM  Usage:  START.bat        (works from any directory: the script cd's to its
REM                           own folder via %~dp0 before doing anything)
REM
REM  Windows note: this script never calls `timeout`. Git for Windows installs a
REM  GNU `timeout.exe` that shadows the Windows one on PATH and rejects the `/t`
REM  flag, and the real Windows `timeout.exe` refuses to run when stdin is
REM  redirected (for example when the script's output is piped or captured).
REM  Delays use the full path to Windows `ping.exe` instead, which always works.
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
    goto :fail
)

docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERROR] Docker is installed but the daemon is not reachable.
    echo   Start Docker Desktop and wait for it to report "running", then retry.
    echo.
    goto :fail
)

%COMPOSE% version >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERROR] "docker compose" is unavailable. Update Docker Desktop so that
    echo   the Compose v2 plugin is installed.
    echo.
    goto :fail
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
        goto :fail
    )
    echo.
    echo   [ACTION REQUIRED] .env was created with placeholder values.
    echo   Open %PROJECT_ROOT%\.env and replace the placeholder secrets, at minimum:
    echo       DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DATAFORGE_FERNET_KEY,
    echo       INTERNAL_SERVICE_TOKEN
    echo   Then run START.bat again.
    echo.
    goto :fail
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
    goto :fail
)
echo.
echo       Services started.
echo.

REM ---------------------------------------------------------------------------
REM 5. Wait for readiness of ALL SIX services.
REM     - db, redis, api, worker and ai-service expose Docker healthchecks, so
REM       we poll their health status.
REM     - web has no container healthcheck, so we poll its HTTP port instead.
REM ---------------------------------------------------------------------------
echo [5/6] Waiting for all six services to become ready...
echo.

call :wait_healthy db 90
if errorlevel 1 goto :not_ready

call :wait_healthy redis 90
if errorlevel 1 goto :not_ready

call :wait_healthy api %HEALTH_TIMEOUT_SECONDS%
if errorlevel 1 goto :not_ready

call :wait_healthy worker %HEALTH_TIMEOUT_SECONDS%
if errorlevel 1 goto :not_ready

call :wait_healthy ai-service %HEALTH_TIMEOUT_SECONDS%
if errorlevel 1 goto :not_ready

call :wait_http web http://localhost:3000/ 120
if errorlevel 1 goto :not_ready

echo.
echo       All six services are ready: db, redis, api, worker, ai-service, web.
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
set "RC=0"
goto :done


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
goto :fail


:wait_healthy
REM %1 = service name, %2 = timeout seconds.
REM Polls the container's Docker healthcheck. A service without a healthcheck
REM reports its run state instead, so this stays safe for such services.
set "SVC=%~1"
set "DEADLINE=%~2"
set /a "WAITED=0"
:wait_healthy_loop
set "CID="
for /f "delims=" %%i in ('%COMPOSE% ps -q %SVC% 2^>nul') do set "CID=%%i"
if not defined CID (
    echo       [wait] %SVC%: container not created yet...
    goto :wait_healthy_tick
)
set "STATUS="
for /f "delims=" %%s in ('docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" !CID! 2^>nul') do set "STATUS=%%s"
if /i "!STATUS!"=="healthy" (
    echo       [ok]   %SVC% is healthy.
    exit /b 0
)
if /i "!STATUS!"=="running" (
    echo       [ok]   %SVC% is running.
    exit /b 0
)
echo       [wait] %SVC%: !STATUS!...
:wait_healthy_tick
if !WAITED! GEQ !DEADLINE! exit /b 1
call :sleep 3
set /a "WAITED+=3"
goto :wait_healthy_loop


:wait_http
REM %1 = label, %2 = URL, %3 = timeout seconds. Polls an HTTP endpoint.
set "LABEL=%~1"
set "URL=%~2"
set "DEADLINE=%~3"
set /a "WAITED=0"
:wait_http_loop
curl -fsS -o nul "%URL%"
if not errorlevel 1 (
    echo       [ok]   %LABEL% is serving at %URL%
    exit /b 0
)
echo       [wait] %LABEL%: not responding yet...
if !WAITED! GEQ !DEADLINE! exit /b 1
call :sleep 3
set /a "WAITED+=3"
goto :wait_http_loop


:sleep
REM %1 = whole seconds to pause. Uses the full path to Windows ping.exe:
REM   - Git for Windows ships a GNU `timeout.exe` that can shadow the Windows
REM     one on PATH and does not understand `/t`.
REM   - The real Windows `timeout.exe` fails when stdin is redirected (for
REM     example when this script's output is piped or captured).
REM ping has neither problem and needs no interactive console.
set /a "PING_COUNT=%~1+1"
if %PING_COUNT% LSS 2 set "PING_COUNT=2"
"%SystemRoot%\System32\ping.exe" -n %PING_COUNT% 127.0.0.1 >nul 2>&1
exit /b 0


REM ===========================================================================
REM  Exit handling
REM ===========================================================================

:fail
set "RC=1"
goto :done

:done
REM Keep the console window open when the script was launched by double-click.
REM Explorer runs a double-clicked .bat as  cmd /c "<path>"  in a brand new
REM console that closes the instant the script ends, so the user would otherwise
REM see only a flash (and any error would be unreadable). In that case
REM %CMDCMDLINE% contains this script's full path and we wait for a keypress.
REM When the script is run from an already-open terminal the window stays open on
REM its own, so no pause happens and scripted use is unaffected.
call :maybe_pause
exit /b %RC%

:maybe_pause
echo %CMDCMDLINE% | "%SystemRoot%\System32\find.exe" /i "%~f0" >nul
if not errorlevel 1 (
    echo.
    pause
)
exit /b 0
