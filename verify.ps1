$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "scripts\verify_project.ps1"

if (-not (Test-Path $script)) {
    throw "Verification script not found: $script"
}

& $script
exit $LASTEXITCODE
