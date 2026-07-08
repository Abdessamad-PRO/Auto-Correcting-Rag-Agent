@echo off
:: =============================================================================
:: RAG OS — One-shot launcher
:: Starts the FastAPI backend (uv) and the Angular frontend (npm) in two
:: separate console windows so logs from each stay readable.
::
:: Usage:   run.bat            (start both)
::          run.bat backend    (start backend only)
::          run.bat frontend   (start frontend only)
::          run.bat install    (sync deps for both then exit)
:: =============================================================================

setlocal
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%auto-corrector-rag-frontend"

if /I "%~1"=="install"  goto :install
if /I "%~1"=="backend"  goto :backend_only
if /I "%~1"=="frontend" goto :frontend_only
goto :both

:install
echo [install] syncing backend dependencies (uv)...
pushd "%BACKEND%" || (echo Backend folder missing & exit /b 1)
call uv sync
popd
echo.
echo [install] installing frontend dependencies (npm)...
pushd "%FRONTEND%" || (echo Frontend folder missing & exit /b 1)
call npm install
popd
echo.
echo [install] done.
exit /b 0

:backend_only
call :check_env || exit /b 1
echo [backend] starting FastAPI on http://localhost:8000 ...
pushd "%BACKEND%"
call uv run rag-api
popd
exit /b 0

:frontend_only
echo [frontend] starting Angular on http://localhost:4200 ...
pushd "%FRONTEND%"
call npm start
popd
exit /b 0

:both
call :check_env || exit /b 1
echo.
echo  ====================================================
echo   RAG OS  -  starting backend + frontend
echo   Backend  : http://localhost:8000   (Swagger: /docs)
echo   Frontend : http://localhost:4200
echo  ====================================================
echo.
start "RAG-OS  backend  (FastAPI / uv)" cmd /k "cd /d %BACKEND% && uv run rag-api"
timeout /t 2 /nobreak >nul
start "RAG-OS  frontend (Angular)"    cmd /k "cd /d %FRONTEND% && npm start"
echo.
echo Two new windows have been opened. Close them to stop the services.
exit /b 0

:: ----- helpers --------------------------------------------------------------

:check_env
if not exist "%BACKEND%\.env" (
    echo.
    echo [WARN] backend\.env is missing. The backend will start with defaults.
    echo        To use Gemini/OpenAI/Grok, copy backend\.env.example to backend\.env
    echo        and set GEMINI_API_KEY / OPENAI_API_KEY / GROK_API_KEY or set LOCAL=true for Ollama.
    echo.
)
exit /b 0
