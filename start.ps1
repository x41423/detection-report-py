$ErrorActionPreference = "SilentlyContinue"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontendUsesHttps = Test-Path "$projectDir\frontend\certs\dev-server.pfx"
$frontendScheme = if ($frontendUsesHttps) { "https" } else { "http" }
$frontendUrl = "${frontendScheme}://localhost:5173"
$backendHost = "0.0.0.0"
$venvPython = Join-Path $projectDir ".venv\Scripts\python.exe"
$backendExecutable = "uvicorn"
$backendArguments = @("backend.main:app", "--host", $backendHost, "--port", "8000")
$backendRuntime = "global uvicorn"
if (Test-Path $venvPython) {
    $backendExecutable = $venvPython
    $backendArguments = @("-m", "uvicorn", "backend.main:app", "--host", $backendHost, "--port", "8000")
    $backendRuntime = ".venv"
}
$speechEnvFile = if (Test-Path "$projectDir\.env.local") {
    ".env.local"
} elseif (Test-Path "$projectDir\.env") {
    ".env"
} else {
    ""
}

Set-Location $projectDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Detection Report Tool Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

& powershell -NoProfile -ExecutionPolicy Bypass -File "$projectDir\scripts\ensure_lan_firewall.ps1" -Ports 5173,8000

& powershell -NoProfile -ExecutionPolicy Bypass -File "$projectDir\scripts\stop_backend_port.ps1" -Port 8000 -ProjectDir $projectDir
& powershell -NoProfile -ExecutionPolicy Bypass -File "$projectDir\scripts\stop_frontend_port.ps1" -Port 5173 -ProjectDir $projectDir

$viteCacheDir = Join-Path $projectDir "frontend\node_modules\.vite"
if (Test-Path $viteCacheDir) {
    Remove-Item -LiteralPath $viteCacheDir -Recurse -Force -ErrorAction SilentlyContinue
}

$backend = Start-Process -FilePath $backendExecutable -ArgumentList $backendArguments `
    -WorkingDirectory $projectDir -PassThru -WindowStyle Hidden
Write-Host "[1/2] Backend started (PID: $($backend.Id)) on 0.0.0.0:8000 using $backendRuntime" -ForegroundColor Green

Start-Sleep -Seconds 3

$frontend = Start-Process -FilePath "npm" -ArgumentList "run", "dev", "--", "--force" `
    -WorkingDirectory "$projectDir\frontend" -PassThru -WindowStyle Hidden
Write-Host "[2/2] Frontend started (PID: $($frontend.Id)) on :5173" -ForegroundColor Green

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Services are running" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend:  http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Frontend: $frontendUrl" -ForegroundColor White
Write-Host "  API Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
& powershell -NoProfile -ExecutionPolicy Bypass -File "$projectDir\scripts\show-lan-urls.ps1" -FrontendPort 5173 -BackendPort 8000 -Scheme $frontendScheme
if ($speechEnvFile) {
    Write-Host "  Local STT: overrides loaded from $speechEnvFile" -ForegroundColor White
} else {
    Write-Host "  Local STT: using built-in defaults; requires faster-whisper package" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  Press Ctrl+C to stop both services." -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Start-Process $frontendUrl

try {
    Write-Host "Waiting... (Ctrl+C to stop)"
    while ($true) {
        if ($backend.HasExited -and $frontend.HasExited) {
            Write-Host "Both services have stopped." -ForegroundColor Yellow
            break
        }
        Start-Sleep -Seconds 2
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped." -ForegroundColor Green
}
