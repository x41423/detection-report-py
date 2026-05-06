@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0verify.ps1"
exit /b %errorlevel%
