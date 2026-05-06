@echo off
setlocal
echo Starting JSON-to-DB migration (Phase 1)...
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"
if exist "scripts\migrate_json_to_db.py" (
    if not exist "logs" mkdir logs
    echo Running migration script...
    python -u "scripts\migrate_json_to_db.py" > "logs\migration.log" 2>&1
    echo Migration finished. See logs\migration.log for details.
else (
    echo Migration script not found: scripts\migrate_json_to_db.py
)
pause
