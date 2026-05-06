param(
    [string]$CudaBin = "",
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$targetDir = Join-Path $projectRoot ".runtime\nvidia\bin"
$requiredDlls = @(
    "cublas64_12.dll",
    "cudart64_12.dll"
)

function Resolve-CudaBinDirectory {
    param([string]$Override)

    if ($Override) {
        if (-not (Test-Path -LiteralPath $Override -PathType Container)) {
            throw "Specified CUDA bin directory does not exist: $Override"
        }
        return (Resolve-Path -LiteralPath $Override).Path
    }

    $defaultRoot = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"
    if (-not (Test-Path -LiteralPath $defaultRoot -PathType Container)) {
        throw "Default CUDA install root not found: $defaultRoot. Install CUDA 12.x first, or pass -CudaBin."
    }

    $candidate = Get-ChildItem -LiteralPath $defaultRoot -Directory |
        Where-Object { $_.Name -like "v12*" } |
        Sort-Object Name -Descending |
        Select-Object -First 1

    if (-not $candidate) {
        throw "No v12.x directory found under $defaultRoot. Install CUDA 12.x first, or pass -CudaBin."
    }

    $binDir = Join-Path $candidate.FullName "bin"
    if (-not (Test-Path -LiteralPath $binDir -PathType Container)) {
        throw "CUDA directory was found but the bin subdirectory is missing: $binDir"
    }

    return $binDir
}

$resolvedCudaBin = Resolve-CudaBinDirectory -Override $CudaBin

New-Item -ItemType Directory -Path $targetDir -Force | Out-Null

Write-Host "CUDA bin:  $resolvedCudaBin" -ForegroundColor Cyan
Write-Host "Target dir: $targetDir" -ForegroundColor Cyan

$copied = @()
foreach ($dllName in $requiredDlls) {
    $sourcePath = Join-Path $resolvedCudaBin $dllName
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Required DLL is missing: $sourcePath"
    }

    $targetPath = Join-Path $targetDir $dllName
    if ($WhatIf) {
        Write-Host "[WhatIf] Copy $sourcePath -> $targetPath"
    } else {
        Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
        $copied += $targetPath
        Write-Host "Copied: $dllName" -ForegroundColor Green
    }
}

if ($WhatIf) {
    Write-Host "WhatIf complete. No files were copied." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Copied DLLs:" -ForegroundColor Green
$copied | ForEach-Object { Write-Host " - $_" }
Write-Host ""
Write-Host "Next step: restart the backend, then run 'python scripts\warmup_local_stt.py'." -ForegroundColor Yellow
