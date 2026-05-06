@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PD=%~dp0"
if "!PD:~-1!"=="\" set "PD=!PD:~0,-1!"
set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"
set "BACKEND_APP=backend.main:app"
set "BP="
set "BA="
set "BR="
set "NPM_EXE="
set "SPEECH_ENV_FILE="
set "FRONTEND_FORCE_HTTP=0"
set "BACKEND_IMPORT_ERROR_FILE=%TEMP%\detection_report_backend_import_error.txt"

if /I "%~1"=="https" set "FRONTEND_FORCE_HTTP=0"
if /I "%~1"=="http" set "FRONTEND_FORCE_HTTP=1"

echo ========================================
echo   BinXian Detection Tool - Launcher
echo ========================================
echo.

echo [INFO] Working directory: %cd%
echo [INFO] Script location: !PD!
if "!FRONTEND_FORCE_HTTP!"=="1" (
    echo [INFO] Frontend mode: HTTP ^(default compatibility mode^)
) else (
    echo [INFO] Frontend mode: HTTPS ^(requested^)
)
echo.

if not exist "!PD!\backend\main.py" (
    echo [ERROR] backend\main.py not found!
    pause
    exit /b 1
)

if not exist "!PD!\frontend\package.json" (
    echo [ERROR] frontend\package.json not found!
    pause
    exit /b 1
)

echo [STEP 1/5] Resolving backend Python runtime...
if exist "!BACKEND_IMPORT_ERROR_FILE!" del /f /q "!BACKEND_IMPORT_ERROR_FILE!" >nul 2>&1
REM ---- Try .venv-win11 ----
if not defined BP if exist "!PD!\.venv-win11\Scripts\python.exe" (
    pushd "!PD!"
    "!PD!\.venv-win11\Scripts\python.exe" -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
        set "BP=!PD!\.venv-win11\Scripts\python.exe"
        set "BR=.venv-win11"
    )
    popd
)
REM ---- Try .venv-win10 ----
if not defined BP if exist "!PD!\.venv-win10\Scripts\python.exe" (
    pushd "!PD!"
    "!PD!\.venv-win10\Scripts\python.exe" -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
        set "BP=!PD!\.venv-win10\Scripts\python.exe"
        set "BR=.venv-win10"
    )
    popd
)
REM ---- Try generic .venv ----
if not defined BP if exist "!PD!\.venv\Scripts\python.exe" (
    pushd "!PD!"
    "!PD!\.venv\Scripts\python.exe" -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
        set "BP=!PD!\.venv\Scripts\python.exe"
        set "BR=.venv"
    )
    popd
)
REM ---- Try py launcher ----
if not defined BP (
    where.exe py >nul 2>&1 && (
        pushd "!PD!"
        py -3 -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
            set "BP=py"
            set "BA=-3"
            set "BR=py -3"
        )
        popd
    )
)
if not defined BP (
    where.exe py >nul 2>&1 && (
        pushd "!PD!"
        py -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
            set "BP=py"
            set "BR=py"
        )
        popd
    )
)
REM ---- Try python ----
if not defined BP (
    where.exe python >nul 2>&1 && (
        pushd "!PD!"
        python -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
            set "BP=python"
            set "BR=python"
        )
        popd
    )
)

if not defined BP (
    echo [ERROR] Could not resolve a usable backend runtime.
    if exist "!BACKEND_IMPORT_ERROR_FILE!" (
        echo [ERROR] Python was found, but importing backend.main failed:
        type "!BACKEND_IMPORT_ERROR_FILE!"
    ) else (
        echo [ERROR] No usable Python launcher or interpreter was found.
    )
    echo [ERROR] If this repo is shared between Win10 and Win11, the project .venv may point to Python from the other system.
    echo [ERROR] If the import failed because of missing dependencies, run:
    echo         py -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo [OK] Backend will use !BR!.

echo [STEP 2/5] Checking npm...
set "NPM_EXE=npm"
where.exe npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found! Please install Node.js
    pause
    exit /b 1
)
echo [OK] npm found.

echo [STEP 3/5] Checking frontend dependencies...
if not exist "!PD!\frontend\node_modules\.bin\vite.cmd" (
    echo [ERROR] Frontend dependencies are missing or incomplete.
    echo [ERROR] Please run: npm install
    echo [ERROR] Working directory: !PD!\frontend
    pause
    exit /b 1
)
echo [OK] Frontend dependencies look ready.

if exist "!PD!\.env.local" (
    set "SPEECH_ENV_FILE=.env.local"
) else (
    if exist "!PD!\.env" set "SPEECH_ENV_FILE=.env"
)

set "FRONTEND_URL=http://localhost:!FRONTEND_PORT!"
if "!FRONTEND_FORCE_HTTP!"=="0" (
    if exist "!PD!\frontend\certs\dev-server.pfx" (
        set "FRONTEND_URL=https://localhost:!FRONTEND_PORT!"
    ) else (
        echo [WARN] HTTPS was requested, but frontend\certs\dev-server.pfx was not found.
        echo [WARN] Falling back to HTTP.
        set "FRONTEND_FORCE_HTTP=1"
    )
)

echo.
echo [STEP 4/5] Starting backend server on port !BACKEND_PORT!...
if defined BA (
    echo   Command: "!BP!" !BA! -m uvicorn !BACKEND_APP! --host !BACKEND_HOST! --port !BACKEND_PORT!
    start "backend" cmd /k "cd /d "!PD!" && set HF_HUB_OFFLINE=1 && echo [BACKEND] Starting backend via !BR!... && "!BP!" !BA! -m uvicorn !BACKEND_APP! --host !BACKEND_HOST! --port !BACKEND_PORT!"
) else (
    echo   Command: "!BP!" -m uvicorn !BACKEND_APP! --host !BACKEND_HOST! --port !BACKEND_PORT!
    start "backend" cmd /k "cd /d "!PD!" && set HF_HUB_OFFLINE=1 && echo [BACKEND] Starting backend via !BR!... && "!BP!" -m uvicorn !BACKEND_APP! --host !BACKEND_HOST! --port !BACKEND_PORT!"
)

echo [INFO] Waiting for backend to initialize...
timeout /t 4 /nobreak >nul

echo.
echo [STEP 5/5] Starting frontend server on port !FRONTEND_PORT!...
if "!FRONTEND_FORCE_HTTP!"=="1" (
    echo   Mode: HTTP ^(forced by start.bat for cross-Windows compatibility^)
) else (
    echo   Mode: HTTPS ^(using frontend dev certificate^)
)
echo   Command: npm run dev
start "frontend" cmd /k "cd /d "!PD!\frontend" && echo [FRONTEND] Starting Vite dev server... && set VITE_DEV_FORCE_HTTP=!FRONTEND_FORCE_HTTP! && npm run dev"

echo [INFO] Waiting for frontend to initialize...
timeout /t 6 /nobreak >nul

echo.
echo ========================================
echo   All services started!
echo.
echo   Backend:   http://127.0.0.1:!BACKEND_PORT!
echo   Frontend:  !FRONTEND_URL!
echo   API Docs:  http://127.0.0.1:!BACKEND_PORT!/docs
if not "!SPEECH_ENV_FILE!"=="" (
echo   Local STT: overrides loaded from !SPEECH_ENV_FILE!
) else (
echo   Local STT: using built-in defaults; requires faster-whisper package
)
if "!FRONTEND_FORCE_HTTP!"=="1" (
echo   Frontend note: running in HTTP compatibility mode.
echo   If you need the dev certificate HTTPS URL, run: start.bat https
)
echo.
echo   Two new terminal windows were opened.
echo   Close those windows to stop services.
echo ========================================
echo.
echo [INFO] Opening browser...
start "" "!FRONTEND_URL!"
pause
