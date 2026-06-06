@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "DRY_RUN=0"
if /I "%~1"=="--dry-run" set "DRY_RUN=1"
if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help

echo ========================================
echo   Binxian Workbench - Stop Services
echo ========================================
echo.
if "%DRY_RUN%"=="1" echo [INFO] Dry run mode.
echo.

REM ---- Step 1: Kill by port (most reliable) ----
echo [STEP 1/3] Stopping services by port...
call :kill_by_port 9000 "MinIO API"
call :kill_by_port 9001 "MinIO Console"
call :kill_by_port 8000 "Backend"
call :kill_by_port 5173 "Frontend"

REM ---- Step 2: Kill by process name (cleanup) ----
echo.
echo [STEP 2/3] Cleaning up remaining processes...
call :kill_by_name "minio.exe"
call :kill_by_name "uvicorn.exe"

REM ---- Step 3: Close cmd windows via PowerShell ----
echo.
echo [STEP 3/3] Closing terminal windows...
call :close_ps_window "minio"
call :close_ps_window "MinIO Object Storage"
call :close_ps_window "backend"
call :close_ps_window "frontend"

echo.
echo [OK] All services stopped.
ping -n 2 127.0.0.1 >nul 2>&1
exit /b 0

REM ============================================================
REM Kill process by port number
REM ============================================================
:kill_by_port
set "PORT=%~1"
set "NAME=%~2"
if "%DRY_RUN%"=="1" (
    echo   [DRY] Would kill process on port %PORT% ^(%NAME%^)
    exit /b 0
)
set "FOUND=0"
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":%PORT% " ^| findstr /C:"LISTENING"') do (
    set "PID=%%a"
    if not "!PID!"=="0" if not "!PID!"=="" (
        taskkill /PID !PID! /T /F >nul 2>&1
        if not errorlevel 1 (
            echo   [OK] Killed PID !PID! on port %PORT% ^(%NAME%^)
            set "FOUND=1"
        )
    )
)
if "!FOUND!"=="0" (
    for /f "tokens=4" %%a in ('netstat -ano 2^>nul ^| findstr /C:":%PORT% " ^| findstr /C:"LISTENING"') do (
        set "PID=%%a"
        if not "!PID!"=="0" if not "!PID!"=="" (
            taskkill /PID !PID! /T /F >nul 2>&1
            if not errorlevel 1 (
                echo   [OK] Killed PID !PID! on port %PORT% ^(%NAME%^)
                set "FOUND=1"
            )
        )
    )
)
exit /b 0

REM ============================================================
REM Kill process by image name
REM ============================================================
:kill_by_name
set "NAME=%~1"
if "%DRY_RUN%"=="1" (
    echo   [DRY] Would kill process %NAME%
    exit /b 0
)
taskkill /IM "%NAME%" /F >nul 2>&1
if not errorlevel 1 (
    echo   [OK] Killed process %NAME%.
)
exit /b 0

REM ============================================================
REM Close cmd window by title via PowerShell
REM Works reliably on ALL Windows language versions
REM ============================================================
:close_ps_window
set "TITLE=%~1"
if "%DRY_RUN%"=="1" (
    echo   [DRY] Would close window "%TITLE%"
    exit /b 0
)
powershell -NoProfile -Command "Get-Process cmd -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*%TITLE%*' } | ForEach-Object { Stop-Process -Id $_.Id -Force; Write-Host '  [OK] Closed window \"%TITLE%\".' }" 2>nul
exit /b 0

:help
echo Usage:
echo   stop.bat              Stop all project services.
echo   stop.bat --dry-run    Show what would be stopped.
echo   stop.bat --help       Show this help.
exit /b 0
