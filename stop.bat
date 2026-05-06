@echo off
chcp 65001 >nul
title 检测工具 - 停止服务

echo 正在停止后端服务...
taskkill /FI "WINDOWTITLE eq backend" /F >nul 2>&1

echo 正在停止前端服务...
taskkill /FI "WINDOWTITLE eq frontend" /F >nul 2>&1

echo.
echo 所有服务已停止。
timeout /t 2 /nobreak >nul
