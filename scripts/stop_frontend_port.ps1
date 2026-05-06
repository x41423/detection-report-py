[CmdletBinding()]
param(
    [int]$Port = 5173,
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "SilentlyContinue"

$resolvedProjectDir = (Resolve-Path -LiteralPath $ProjectDir).Path
$processIds = New-Object System.Collections.Generic.HashSet[int]

$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($listener in $listeners) {
    if ($listener.OwningProcess -gt 0) {
        [void]$processIds.Add([int]$listener.OwningProcess)
    }
}

$expanded = $true
while ($expanded) {
    $expanded = $false
    $knownIds = @($processIds)
    $related = Get-CimInstance Win32_Process |
        Where-Object {
            ($knownIds -contains [int]$_.ParentProcessId) -or
            ($knownIds -contains [int]$_.ProcessId)
        }
    foreach ($process in $related) {
        if ($process.CommandLine -and $process.CommandLine.Contains($resolvedProjectDir)) {
            if ($processIds.Add([int]$process.ProcessId)) {
                $expanded = $true
            }
            if ($process.ParentProcessId -gt 0) {
                [void]$processIds.Add([int]$process.ParentProcessId)
            }
        }
    }
}

$processes = Get-CimInstance Win32_Process |
    Where-Object {
        $processIds.Contains([int]$_.ProcessId) -and
        $_.CommandLine -and
        $_.CommandLine.Contains($resolvedProjectDir) -and
        ($_.CommandLine -match "vite|npm|frontend")
    } |
    Sort-Object ProcessId -Descending

foreach ($process in $processes) {
    Write-Host "[FRONTEND] Stopping old PID $($process.ProcessId): $($process.Name)" -ForegroundColor Yellow
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}
