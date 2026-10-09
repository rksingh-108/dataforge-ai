@echo off
REM ============================================================================
REM  DataForge AI - STOP.bat
REM ----------------------------------------------------------------------------
REM  Stops the local development stack WITHOUT destroying anything.
REM
REM  What this does:
REM      - stops the db, redis, api, worker, ai-service and web containers
REM
REM  What this deliberately does NOT do:
REM      - it does NOT delete source code
REM      - it does NOT delete Docker volumes
REM      - it does NOT delete PostgreSQL / Redis / media data
REM      - it does NOT run any destructive cleanup command
REM
REM  Your development database, uploaded documents and Redis data survive, so
REM  the next START.bat brings the same environment back.
REM
REM  To start again:  START.bat
REM
REM  Usage:  STOP.bat        (works from any directory: the script cd's to its
REM                           own folder via %~dp0 before doing anything)
REM ============================================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "PROJECT_ROOT=%CD%"
set "COMPOSE=docker compose"

echo.
echo ============================================================================
echo   DataForge AI - stopping local development environment
echo ============================================================================
echo   Project root: %PROJECT_ROOT%
echo.

REM ---------------------------------------------------------------------------
REM 1. Docker must be available to talk to the stack.
REM ---------------------------------------------------------------------------
echo [1/4] Checking Docker...

where docker >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [ERROR] Docker was not found on PATH, so the stack cannot be stopped.
    echo   Install Docker Desktop: https://docs.docker.com/get-docker/
    echo.
    goto :fail
)

docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo   [WARN] The Docker daemon is not reachable. If Docker Desktop was
    echo          already closed, the containers are already stopped - nothing
    echo          to do. Otherwise start Docker Desktop and run STOP.bat again.
    echo.
    set "RC=0"
    goto :done
)
echo       Docker is available.
echo.

REM ---------------------------------------------------------------------------
REM 2. Is anything actually running? (graceful when already stopped)
REM ---------------------------------------------------------------------------
echo [2/4] Checking stack status...

set "RUNNING="
for /f "delims=" %%i in ('%COMPOSE% ps --status running -q 2^>nul') do set "RUNNING=%%i"

if not defined RUNNING (
    echo       No DataForge services are running - nothing to stop.
    goto :preserved
)
echo       Running services found.
echo.

REM ---------------------------------------------------------------------------
REM 3. Stop the services. `docker compose stop` keeps containers, networks and
REM    volumes intact; it is the least destructive way to shut the stack down.
REM ---------------------------------------------------------------------------
echo [3/4] Stopping services (this can take a few seconds)...

%COMPOSE% stop
if errorlevel 1 (
    echo.
    echo   [ERROR] Failed to stop one or more services. Current status:
    %COMPOSE% ps
    echo   Retry with:  %COMPOSE% stop
    echo.
    goto :fail
)
echo.

REM Verify the stop actually took effect: no service may still be running.
set "STILL_RUNNING="
for /f "delims=" %%i in ('%COMPOSE% ps --status running -q 2^>nul') do set "STILL_RUNNING=%%i"

if defined STILL_RUNNING (
    echo   [ERROR] Some services are still running after "docker compose stop":
    %COMPOSE% ps
    echo.
    goto :fail
)

echo       Services stopped. Current status:
%COMPOSE% ps -a --format "      {{.Service}}: {{.State}}"
echo.

:preserved
REM ---------------------------------------------------------------------------
REM 4. Confirm that persistent data is still present.
REM ---------------------------------------------------------------------------
echo [4/4] Confirming your development data is preserved...
echo.

set "FOUND_VOLUME="
for /f "delims=" %%v in ('docker volume ls --filter "name=dataforge_" --format "{{.Name}}" 2^>nul') do (
    echo       kept: %%v
    set "FOUND_VOLUME=1"
)

if not defined FOUND_VOLUME (
    echo       No dataforge_* volumes found yet. They are created on first start.
)

echo.
echo ============================================================================
echo   DataForge AI is stopped - your data was NOT deleted
echo ============================================================================
echo.
echo   Preserved:  PostgreSQL data, Redis data and uploaded media.
echo   Start again:  START.bat
echo.
echo   Volumes are only removed by an explicit, destructive command such as
echo   "docker compose down -v" (or "make clean"). STOP.bat never does this.
echo.
set "RC=0"
goto :done


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
REM see only a flash. In that case %CMDCMDLINE% contains this script's full path
REM and we wait for a keypress. When the script is run from an already-open
REM terminal the window stays open on its own, so scripted use is unaffected.
call :maybe_pause
exit /b %RC%

:maybe_pause
echo %CMDCMDLINE% | "%SystemRoot%\System32\find.exe" /i "%~f0" >nul
if not errorlevel 1 (
    echo.
    pause
)
exit /b 0
