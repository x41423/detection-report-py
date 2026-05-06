<#
.SYNOPSIS
    Drop-in fix for "所有语音识别模型都失败" / stub-source errors.

.DESCRIPTION
    Clears stale __pycache__ entries for the ASR stack, then runs the
    strict self-check so any remaining inconsistency is reported immediately.
    Intended to be invoked from the repo root:

        PS> .\scripts\asr_doctor.ps1

    Exits with code 0 on success and non-zero when the self-check still fails.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repoRoot

Write-Host "[asr_doctor] repo = $repoRoot"

$cacheTargets = @(
    'backend/services/__pycache__/qwen3_asr_provider*.pyc',
    'backend/services/__pycache__/speech_to_text_service*.pyc',
    'backend/services/__pycache__/daily_intake_asr_service*.pyc',
    'backend/funasr_lab/__pycache__/service*.pyc'
)

$removed = 0
foreach ($pattern in $cacheTargets) {
    Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "[asr_doctor] removing $($_.FullName)"
        Remove-Item -Force -LiteralPath $_.FullName
        $removed += 1
    }
}
Write-Host "[asr_doctor] cleared $removed cached bytecode file(s)"

$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Warning "[asr_doctor] .venv\Scripts\python.exe not found, falling back to 'python'"
    $python = 'python'
}

Write-Host "[asr_doctor] running strict self-check..."
& $python -c "from backend.diagnostics.asr_self_check import run_asr_self_check; import json; print(json.dumps(run_asr_self_check(strict=True), ensure_ascii=False, indent=2))"
$code = $LASTEXITCODE

if ($code -eq 0) {
    Write-Host "[asr_doctor] OK — ASR stack is healthy. Restart uvicorn to drop the stale process."
} else {
    Write-Error "[asr_doctor] self-check failed (exit $code). See output above."
}

exit $code
