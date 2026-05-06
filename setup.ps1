$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $projectDir ".venv\Scripts\python.exe"

Set-Location $projectDir

if (-not (Test-Path $venvPython)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        py -3 -m venv .venv
    } else {
        python -m venv .venv
    }
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

if (Test-Path "$projectDir\frontend\package.json") {
    Push-Location "$projectDir\frontend"
    try {
        npm install
    } finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "Setup completed. Start the project with: .\start.ps1" -ForegroundColor Green
