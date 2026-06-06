@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PD=%~dp0"
if "!PD:~-1!"=="\" set "PD=!PD:~0,-1!"
set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"
set "BACKEND_APP=backend.main:app"
set "APP_DB_DRIVER=sqlite"
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

echo [STEP 1/7] Running data migration...
pushd "!PD!"
set APP_DB_DRIVER=sqlite && "!PD!\.venv-win10\Scripts\python.exe" scripts\migrate.py check >nul 2>&1
if errorlevel 1 (
    set APP_DB_DRIVER=sqlite && "!PD!\.venv-win11\Scripts\python.exe" scripts\migrate.py check >nul 2>&1
)
if errorlevel 1 (
    set APP_DB_DRIVER=sqlite && "!PD!\.venv\Scripts\python.exe" scripts\migrate.py check >nul 2>&1
)
if errorlevel 1 (
    where.exe py >nul 2>&1 && set APP_DB_DRIVER=sqlite && py -3 scripts\migrate.py check >nul 2>&1
)
if not errorlevel 1 (
    set APP_DB_DRIVER=sqlite && "!PD!\.venv-win10\Scripts\python.exe" scripts\migrate.py run >nul 2>&1
    if errorlevel 1 (
        set APP_DB_DRIVER=sqlite && "!PD!\.venv-win11\Scripts\python.exe" scripts\migrate.py run >nul 2>&1
    )
    if errorlevel 1 (
        set APP_DB_DRIVER=sqlite && "!PD!\.venv\Scripts\python.exe" scripts\migrate.py run >nul 2>&1
    )
    if errorlevel 1 (
        where.exe py >nul 2>&1 && set APP_DB_DRIVER=sqlite && py -3 scripts\migrate.py run >nul 2>&1
    )
) else (
    echo [WARN] Migration check failed, continuing startup...
)
popd
echo.

echo [STEP 2/7] Resolving backend Python runtime...
if exist "!BACKEND_IMPORT_ERROR_FILE!" del /f /q "!BACKEND_IMPORT_ERROR_FILE!" >nul 2>&1
REM ---- Try .venv-win11 ----
if not defined BP if exist "!PD!\.venv-win11\Scripts\python.exe" (
    pushd "!PD!"
    set APP_DB_DRIVER=sqlite && "!PD!\.venv-win11\Scripts\python.exe" -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
        set "BP=!PD!\.venv-win11\Scripts\python.exe"
        set "BR=.venv-win11"
    )
    popd
)
REM ---- Try .venv-win10 ----
if not defined BP if exist "!PD!\.venv-win10\Scripts\python.exe" (
    pushd "!PD!"
    set APP_DB_DRIVER=sqlite && "!PD!\.venv-win10\Scripts\python.exe" -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
        set "BP=!PD!\.venv-win10\Scripts\python.exe"
        set "BR=.venv-win10"
    )
    popd
)
REM ---- Try generic .venv ----
if not defined BP if exist "!PD!\.venv\Scripts\python.exe" (
    pushd "!PD!"
    set APP_DB_DRIVER=sqlite && "!PD!\.venv\Scripts\python.exe" -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
        set "BP=!PD!\.venv\Scripts\python.exe"
        set "BR=.venv"
    )
    popd
)
REM ---- Try py launcher ----
if not defined BP (
    where.exe py >nul 2>&1 && (
        pushd "!PD!"
        set APP_DB_DRIVER=sqlite && py -3 -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
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
        set APP_DB_DRIVER=sqlite && py -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
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
        set APP_DB_DRIVER=sqlite && python -c "import backend.main" >nul 2>"!BACKEND_IMPORT_ERROR_FILE!" && (
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

echo [STEP 3/7] Checking npm...
set "NPM_EXE=npm"
where.exe npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found! Please install Node.js
    pause
    exit /b 1
)
echo [OK] npm found.

echo [STEP 4/7] Checking frontend dependencies...
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
echo [STEP 5/7] Starting MinIO storage service...
call :check_port 9000 "MinIO"
if errorlevel 1 (
    if exist "!PD!\deploy\minio\minio.exe" (
        echo   Starting MinIO on ports 9000/9001...
        start "minio" cmd /k ""!PD!\deploy\minio\start-minio.bat""
        echo [OK] MinIO started. Console: http://localhost:9001
    ) else (
        echo [WARN] MinIO not found at deploy\minio\minio.exe, skipping.
    )
)
echo.

echo [STEP 6/7] Starting backend server on port !BACKEND_PORT!...
call :check_port !BACKEND_PORT! "Backend"
if errorlevel 1 (
    if defined BA (
        echo   Command: "!BP!" !BA! -m uvicorn !BACKEND_APP! --host !BACKEND_HOST! --port !BACKEND_PORT!
        start "backend" cmd /k "cd /d "!PD!" && set HF_HUB_OFFLINE=1 && set APP_DB_DRIVER=sqlite && echo [BACKEND] Starting backend via !BR!... && "!BP!" !BA! -m uvicorn !BACKEND_APP! --host !BACKEND_HOST! --port !BACKEND_PORT!"
    ) else (
        echo   Command: "!BP!" -m uvicorn !BACKEND_APP! --host !BACKEND_HOST! --port !BACKEND_PORT!
        start "backend" cmd /k "cd /d "!PD!" && set HF_HUB_OFFLINE=1 && set APP_DB_DRIVER=sqlite && echo [BACKEND] Starting backend via !BR!... && "!BP!" -m uvicorn !BACKEND_APP! --host !BACKEND_HOST! --port !BACKEND_PORT!"
    )
    echo [INFO] Waiting for backend to initialize...
    ping -n 5 127.0.0.1 >nul 2>&1
)
echo.

echo [STEP 7/7] Starting frontend server on port !FRONTEND_PORT!...
call :check_port !FRONTEND_PORT! "Frontend"
if errorlevel 1 (
    if "!FRONTEND_FORCE_HTTP!"=="1" (
        echo   Mode: HTTP ^(forced by start.bat for cross-Windows compatibility^)
    ) else (
        echo   Mode: HTTPS ^(using frontend dev certificate^)
    )
    echo   Command: npm run dev
    start "frontend" cmd /k "cd /d "!PD!\frontend" && echo [FRONTEND] Starting Vite dev server... && set VITE_DEV_FORCE_HTTP=!FRONTEND_FORCE_HTTP! && npm run dev"
    echo [INFO] Waiting for frontend to initialize...
    ping -n 7 127.0.0.1 >nul 2>&1
)

echo.
echo ========================================
echo   All services started!
echo.
echo   Backend:   http://127.0.0.1:!BACKEND_PORT!
echo   Frontend:  !FRONTEND_URL!
echo   API Docs:  http://127.0.0.1:!BACKEND_PORT!/docs
echo   MinIO:     http://localhost:9001
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
echo   Close the terminal windows to stop services.
echo ========================================
echo.
echo [INFO] Opening browser...
start "" "!FRONTEND_URL!"

echo.
echo [OK] Startup complete. This window will close in 3 seconds...
ping -n 4 127.0.0.1 >nul 2>&1
exit /b 0

exit /b 0

REM ============================================================
REM Helper: check if a port is already in use
REM   call :check_port <port> <name>
REM   errorlevel 0 = port in use (already running)
REM   errorlevel 1 = port free (need to start)
REM ============================================================
:check_port
set "CHECK_PORT=%~1"
set "CHECK_NAME=%~2"
netstat -ano 2>nul | findstr /R /C:":!CHECK_PORT! " | findstr /C:"LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [SKIP] !CHECK_NAME! already running on port !CHECK_PORT!.
    exit /b 0
)
exit /b 1
