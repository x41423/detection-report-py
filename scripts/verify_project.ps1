$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$projectDir = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectDir ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }
$frontendDir = Join-Path $projectDir "frontend"
$frontendBuildScript = Join-Path $frontendDir "scripts\verify-build.mjs"
$pythonCompileTargets = @(
    (Join-Path $projectDir "app"),
    (Join-Path $projectDir "backend"),
    (Join-Path $projectDir "shared"),
    (Join-Path $projectDir "scripts"),
    (Join-Path $projectDir "pachong"),
    (Join-Path $projectDir "tests"),
    (Join-Path $projectDir "main.py"),
    (Join-Path $projectDir "material_app.py")
)

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action,
        [switch]$CheckExitCode
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Action
    if ($CheckExitCode -and $LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

function Test-PythonModule {
    param(
        [string]$ModuleName
    )

    & $pythonExe -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$ModuleName') else 1)" | Out-Null
    return $LASTEXITCODE -eq 0
}

Set-Location $projectDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Project Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Python runtime: $pythonExe" -ForegroundColor White
Write-Host "Frontend dir:   $frontendDir" -ForegroundColor White

if (Test-PythonModule "pytest") {
    Invoke-Step "Python pytest (tests/)" -CheckExitCode {
        & $pythonExe -m pytest -q
    }
} else {
    Invoke-Step "Python unittest discover" -CheckExitCode {
        & $pythonExe -u -m unittest discover -s tests
    }
}

Invoke-Step "Python compileall" -CheckExitCode {
    & $pythonExe -m compileall @pythonCompileTargets
}

Invoke-Step "Python root-file compile smoke" -CheckExitCode {
    @'
from pathlib import Path
import py_compile

skip = {"main.py", "material_app.py"}
targets = sorted(path for path in Path(".").glob("*.py") if path.name not in skip)

for target in targets:
    py_compile.compile(str(target), doraise=True)
    print(f"compiled {target.name}")
'@ | & $pythonExe -
}

Invoke-Step "Python import smoke" -CheckExitCode {
    & $pythonExe -c "import backend.main; import scripts.probe_funasr_lab; print('import-smoke-ok')"
}

Invoke-Step "Frontend typecheck" -CheckExitCode {
    Push-Location $frontendDir
    try {
        & npm run typecheck
    } finally {
        Pop-Location
    }
}

Invoke-Step "Frontend build" -CheckExitCode {
    & node $frontendBuildScript
}

Write-Host ""
Write-Host "Verification completed successfully." -ForegroundColor Green
