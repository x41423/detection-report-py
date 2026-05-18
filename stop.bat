@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
title Detection Report Tool - Stop Services

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "FRONTEND_PORT=5173"
set "BACKEND_PORT=8000"
set "DRY_RUN=0"
set "HAD_ERROR=0"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="--dry-run" set "DRY_RUN=1"

echo ========================================
echo   Detection Report Tool - Stop Services
echo ========================================
echo.
echo [INFO] Project:  "%PROJECT_DIR%"
echo [INFO] Ports:    frontend %FRONTEND_PORT%, backend %BACKEND_PORT%
if "%DRY_RUN%"=="1" echo [INFO] Dry run: commands will be printed only.
echo.

set "STOP_DEV_SCRIPT=%PROJECT_DIR%\scripts\stop_dev_port.ps1"

if not exist "%STOP_DEV_SCRIPT%" (
    echo [ERROR] Missing script: scripts\stop_dev_port.ps1
    set "HAD_ERROR=1"
    goto :fallback
)

echo [STEP] Stopping project services by port...
if "%DRY_RUN%"=="1" (
    echo powershell -NoProfile -ExecutionPolicy Bypass -File "%STOP_DEV_SCRIPT%" -Ports %FRONTEND_PORT%,%BACKEND_PORT% -ProjectDir "%PROJECT_DIR%"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%STOP_DEV_SCRIPT%" -Ports %FRONTEND_PORT%,%BACKEND_PORT% -ProjectDir "%PROJECT_DIR%"
    if errorlevel 1 (
        echo [WARN] PowerShell stop step failed.
        set "HAD_ERROR=1"
    )
)

:fallback
echo.
echo [STEP] Window-title fallback for services started by start.bat...
call :run_taskkill "backend"
call :run_taskkill "frontend"

echo.
if "%HAD_ERROR%"=="0" (
    echo [OK] Stop commands completed.
) else (
    echo [WARN] Stop completed with one or more errors. Check the messages above.
)
if "%DRY_RUN%"=="1" exit /b %HAD_ERROR%
timeout /t 2 /nobreak >nul
exit /b %HAD_ERROR%

:run_taskkill
set "WINDOW_TITLE=%~1"
if "%DRY_RUN%"=="1" (
    echo taskkill /FI "WINDOWTITLE eq %WINDOW_TITLE%" /T /F
    exit /b 0
)
taskkill /FI "WINDOWTITLE eq %WINDOW_TITLE%" /T /F >nul 2>&1
if not errorlevel 1 (
    echo [OK] Stopped window titled "%WINDOW_TITLE%".
) else (
    echo [INFO] No "%WINDOW_TITLE%" window found.
)
exit /b 0

:help
echo Usage:
echo   stop.bat              Stop backend/frontend services for this project.
echo   stop.bat --dry-run    Print stop commands without killing anything.
echo   stop.bat --help       Show this help.
exit /b 0
