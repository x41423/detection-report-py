[CmdletBinding()]
param(
    [int[]]$Ports = @(5173, 8000),
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "SilentlyContinue"

$resolvedProjectDir = (Resolve-Path -LiteralPath $ProjectDir).Path
$processIds = New-Object System.Collections.Generic.HashSet[int]

foreach ($port in $Ports) {
    $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($listener in $listeners) {
        if ($listener.OwningProcess -gt 0) {
            [void]$processIds.Add([int]$listener.OwningProcess)
        }
    }
}

$expanded = $true
while ($expanded) {
    $expanded = $false
    $knownIds = @($processIds)
    $children = Get-CimInstance Win32_Process |
        Where-Object { $knownIds -contains [int]$_.ParentProcessId }
    foreach ($child in $children) {
        if ($processIds.Add([int]$child.ProcessId)) {
            $expanded = $true
        }
    }
}

$processes = Get-CimInstance Win32_Process |
    Where-Object {
        ($processIds.Contains([int]$_.ProcessId)) -or
        (
            $_.CommandLine -and
            $_.CommandLine.Contains($resolvedProjectDir) -and
            ($_.CommandLine -match "vite|npm|uvicorn|backend.main:app")
        )
    }

foreach ($process in $processes) {
    if (-not $process.CommandLine -or -not $process.CommandLine.Contains($resolvedProjectDir)) {
        continue
    }
    Write-Host "[PORT] Stopping PID $($process.ProcessId): $($process.Name)" -ForegroundColor Yellow
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}
