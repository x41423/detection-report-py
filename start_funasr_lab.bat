@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_funasr_lab.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] FunASR test page launcher failed.
    pause
)
