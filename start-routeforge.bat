@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8000"
set "FRONTEND_HOST=127.0.0.1"
set "FRONTEND_PORT=5173"
set "BACKEND_URL=http://%BACKEND_HOST%:%BACKEND_PORT%"
set "FRONTEND_URL=http://%FRONTEND_HOST%:%FRONTEND_PORT%"
set "OLLAMA_URL=http://127.0.0.1:11434"
set "VALHALLA_URL=http://127.0.0.1:8002"
set "CHECK_ONLY=0"

if /I "%~1"=="--check-only" set "CHECK_ONLY=1"

echo.
echo RouteForge AI startup
echo =====================
echo Project: %ROOT_DIR%
echo.

call :require_command python "Python was not found. Activate the RouteForge AI environment or install Python 3.12+."
if errorlevel 1 goto fatal

call :require_command npm "npm was not found. Install Node.js/npm before starting the frontend."
if errorlevel 1 goto fatal

call :check_backend_dependencies
if errorlevel 1 goto fatal

call :check_database
if errorlevel 1 goto fatal

call :check_node_dependencies
if errorlevel 1 goto fatal

call :check_http "Ollama" "%OLLAMA_URL%/api/tags"
call :check_http "Valhalla" "%VALHALLA_URL%/status"

if "%CHECK_ONLY%"=="1" (
  echo.
  echo Check-only mode complete. Startup commands were not launched.
  goto done
)

echo.
echo Starting FastAPI backend on %BACKEND_URL% ...
start "RouteForge AI Backend" cmd /k "cd /d ""%ROOT_DIR%"" && python -m uvicorn backend.main:app --host %BACKEND_HOST% --port %BACKEND_PORT%"

echo Starting Vite frontend on %FRONTEND_URL% ...
start "RouteForge AI Frontend" cmd /k "cd /d ""%ROOT_DIR%frontend"" && npm run dev -- --port %FRONTEND_PORT%"

echo Waiting for services to start...
timeout /t 4 /nobreak >nul

echo Opening %FRONTEND_URL% ...
start "" "%FRONTEND_URL%"

echo.
echo RouteForge AI startup commands were launched.
echo Backend window: RouteForge AI Backend
echo Frontend window: RouteForge AI Frontend
echo.
goto done

:require_command
where %1 >nul 2>nul
if errorlevel 1 (
  echo ERROR: %~2
  exit /b 1
)
echo OK: Found %1.
exit /b 0

:check_backend_dependencies
echo.
echo Checking backend Python dependencies...
python -c "import fastapi, uvicorn, sqlalchemy, pydantic_settings, ortools; print('OK: Backend dependencies are importable.')" 2>nul
if errorlevel 1 (
  echo ERROR: Backend dependencies are missing or not importable.
  echo        Expected: fastapi, uvicorn, sqlalchemy, pydantic-settings, ortools.
  echo        Activate the correct Python environment or install the project dependencies.
  exit /b 1
)
exit /b 0

:check_database
echo.
echo Checking SQLite database...
python -c "import sqlite3; conn=sqlite3.connect('routeforge.db'); conn.execute('select 1').fetchone(); conn.close(); print('OK: SQLite database is readable.')" 2>nul
if errorlevel 1 (
  echo ERROR: Could not open routeforge.db with SQLite.
  echo        Confirm the file exists and this user can read/write the project directory.
  exit /b 1
)
exit /b 0

:check_node_dependencies
echo.
echo Checking frontend dependencies...
if not exist "%ROOT_DIR%frontend\node_modules" (
  echo ERROR: frontend\node_modules is missing.
  echo        Run npm install in the frontend directory before starting RouteForge AI.
  exit /b 1
)
echo OK: Frontend dependencies directory exists.
exit /b 0

:check_http
set "SERVICE_NAME=%~1"
set "SERVICE_URL=%~2"
echo.
echo Checking %SERVICE_NAME% at %SERVICE_URL% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $response = Invoke-WebRequest -Uri '%SERVICE_URL%' -UseBasicParsing -TimeoutSec 3; if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { exit 0 } else { exit 1 } } catch { exit 1 }"
if errorlevel 1 (
  echo WARNING: %SERVICE_NAME% is OFFLINE or not reachable.
  echo          RouteForge AI will start, but related features may be unavailable.
) else (
  echo OK: %SERVICE_NAME% is reachable.
)
exit /b 0

:fatal
echo.
echo RouteForge AI startup stopped because a required check failed.
echo Fix the error above and run start-routeforge.bat again.
echo.
pause
exit /b 1

:done
endlocal
