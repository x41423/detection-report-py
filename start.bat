@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion

set "PD=%~dp0"
if "%PD:~-1%"=="\" set "PD=%PD:~0,-1%"

set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8000"
set "NGINX_PORT=8080"

echo ========================================
echo    Binxian Workbench - Launcher
echo ========================================
echo.

if not exist "%PD%\backend\main.py" (
    echo [ERROR] backend\main.py not found at %PD%\backend\
    pause
    exit /b 1
)
echo [OK] Project root: %PD%
echo.

REM ---- Resolve Python ----
echo [STEP 1/6] Resolving Python...

if not defined BP if exist "F:\python 3114\python.exe" (
    pushd "%PD%"
    "F:\python 3114\python.exe" -c "import backend.main" >nul 2>&1 && (
        set "BP=F:\python 3114\python.exe"
        set "BR=F:\python 3114"
    )
    popd
)

if not defined BP if exist "%PD%\.venv\Scripts\python.exe" (
    pushd "%PD%"
    "%PD%\.venv\Scripts\python.exe" -c "import backend.main" >nul 2>&1 && (
        set "BP=%PD%\.venv\Scripts\python.exe"
        set "BR=.venv"
    )
    popd
)

if not defined BP (
    where.exe py >nul 2>&1 && (
        pushd "%PD%"
        py -3 -c "import backend.main" >nul 2>&1 && (
            set "BP=py"
            set "BA=-3"
            set "BR=py -3"
        )
        popd
    )
)

if not defined BP (
    echo [ERROR] No Python runtime. Checked F:\python 3114, .venv, py -3.
    pause
    exit /b 1
)
echo [OK] Using %BR%

REM ---- MySQL check ----
echo.
echo [STEP 2/6] Checking MySQL...
netstat -ano 2>nul | findstr ":3306 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [WARN] MySQL not running on port 3306. Start it manually.
) else (
    echo [OK] MySQL running on port 3306.
)

REM ---- MinIO ----
echo.
echo [STEP 3/6] Starting MinIO...
netstat -ano 2>nul | findstr ":9000 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    if exist "%PD%\deploy\minio\minio.exe" (
        start "minio" "%PD%\deploy\minio\minio.exe" server "%PD%\data\minio-data" --console-address :9001
        echo [OK] MinIO started.
    ) else (
        echo [SKIP] deploy\minio\minio.exe not found.
    )
) else (
    echo [SKIP] MinIO already running.
)

REM ---- Backend ----
echo.
echo [STEP 4/6] Starting Backend on port %BACKEND_PORT%...
netstat -ano 2>nul | findstr ":%BACKEND_PORT% " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    if defined BA (
        start "backend" cmd /c "cd /d "%PD%" && "%BP%" %BA% -m uvicorn backend.main:app --host %BACKEND_HOST% --port %BACKEND_PORT%"
    ) else (
        start "backend" cmd /c "cd /d "%PD%" && "%BP%" -m uvicorn backend.main:app --host %BACKEND_HOST% --port %BACKEND_PORT%"
    )
    echo [OK] Backend starting...
    ping -n 4 127.0.0.1 >nul 2>&1
) else (
    echo [SKIP] Backend already running.
)

REM ---- Nginx ----
echo.
echo [STEP 5/6] Starting Nginx on port %NGINX_PORT%...
netstat -ano 2>nul | findstr ":%NGINX_PORT% " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    if exist "%PD%\nginx\nginx.exe" (
        start "nginx" cmd /c "cd /d "%PD%\nginx" && nginx.exe"
        echo [OK] Nginx started.
    ) else (
        echo [ERROR] nginx\nginx.exe not found.
    )
) else (
    echo [SKIP] Nginx already running.
)

REM ---- Cloudflare Tunnel ----
echo.
echo [STEP 6/6] Starting Cloudflare Tunnel...
tasklist 2>nul | findstr /I "cloudflared.exe" >nul 2>&1
if errorlevel 1 (
    if exist "%PD%\tools\cloudflared.exe" (
        start "cloudflared-tunnel" "%PD%\tools\cloudflared.exe" tunnel --config "%PD%\config\cloudflared-config.yml" run
        echo [OK] Tunnel started.
    ) else (
        echo [SKIP] tools\cloudflared.exe not found.
    )
) else (
    echo [SKIP] Tunnel already running.
)

echo.
echo ========================================
echo    All services started!
echo    Backend:  http://127.0.0.1:%BACKEND_PORT%
echo    Frontend: http://127.0.0.1:%NGINX_PORT%
echo    Domain:   https://lina1126.eu.cc
echo ========================================
echo.
start "" "http://127.0.0.1:%NGINX_PORT%"
pause
exit /b 0
