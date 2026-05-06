<#
    Simple one-click migration runner for Phase 1 migration.
    Runs migrate_json_to_db.py and logs output.
#>
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'scripts/migrate_json_to_db.py'
$logDir = Join-Path $PSScriptRoot 'logs'
$log = Join-Path $logDir 'migration.log'

Write-Host 'Starting JSON-to-DB migration (Phase 1)...'

try {
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir | Out-Null
    }

    if (Test-Path $script) {
        & python -u $script 2>&1 | Tee-Object -FilePath $log
        Write-Host 'Migration finished. See' $log 'for details.'
    } else {
        Write-Host 'Migration script not found: ' $script
    }
} catch {
    Write-Host 'Migration failed:' $_.Exception.Message
    Add-Content -Path $log -Value ("ERROR: " + $_.Exception.Message)
}

Pause
