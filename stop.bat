@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion

set "DRY_RUN=0"
if /I "%~1"=="--dry-run" set "DRY_RUN=1"
if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help

echo ========================================
echo    Binxian Workbench - Stop Services
echo ========================================
echo.
if "%DRY_RUN%"=="1" echo [INFO] Dry run mode.

REM ---- 1. Cloudflare Tunnel ----
echo [1/4] Stopping Cloudflare Tunnel...
taskkill /IM "cloudflared.exe" /F >nul 2>&1 && echo   [OK] cloudflared.exe || echo   [SKIP] Not running
powershell -NoProfile -Command "Get-Process cmd -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*cloudflared*' } | Stop-Process -Force" 2>nul

REM ---- 2. Nginx ----
echo.
echo [2/4] Stopping Nginx...
netstat -ano 2>nul | findstr ":8080 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8080 " ^| findstr "LISTENING"') do (
        taskkill /PID %%a /T /F >nul 2>&1
    )
    echo   [OK] Nginx stopped.
) else (
    echo   [SKIP] Nginx not running.
)

REM ---- 3. Backend ----
echo.
echo [3/4] Stopping Backend...
netstat -ano 2>nul | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000 " ^| findstr "LISTENING"') do (
        taskkill /PID %%a /T /F >nul 2>&1
    )
    echo   [OK] Backend stopped.
) else (
    echo   [SKIP] Backend not running.
)
powershell -NoProfile -Command "Get-Process cmd -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*backend*' } | Stop-Process -Force" 2>nul

REM ---- 4. MinIO ----
echo.
echo [4/4] Stopping MinIO...
for %%p in (9000 9001) do (
    netstat -ano 2>nul | findstr ":%%p " | findstr "LISTENING" >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":%%p " ^| findstr "LISTENING"') do (
            taskkill /PID %%a /T /F >nul 2>&1
        )
    )
)
taskkill /IM "minio.exe" /F >nul 2>&1
echo   [OK] MinIO stopped.

echo.
echo ========================================
echo    All services stopped.
echo ========================================
ping -n 2 127.0.0.1 >nul 2>&1
exit /b 0

:help
echo Usage: stop.bat [--dry-run] [--help]
exit /b 0
