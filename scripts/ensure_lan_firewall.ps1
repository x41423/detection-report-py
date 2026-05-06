[CmdletBinding()]
param(
    [string[]]$Ports = @("5173", "8000"),
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraPorts = @()
)

$ErrorActionPreference = "SilentlyContinue"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[LAN] Firewall rule check skipped: run launcher as administrator if other devices cannot connect." -ForegroundColor Yellow
    exit 0
}

foreach ($rawPort in @($Ports + $ExtraPorts)) {
    foreach ($portText in ([string]$rawPort).Split(",", [System.StringSplitOptions]::RemoveEmptyEntries)) {
        $port = 0
        if (-not [int]::TryParse($portText.Trim(), [ref]$port)) {
            continue
        }
        $ruleName = "Detection Report Tool TCP $port"
        $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
        if ($existing) {
            Write-Host "[LAN] Firewall rule exists for TCP $port." -ForegroundColor DarkGray
            continue
        }
        New-NetFirewallRule `
            -DisplayName $ruleName `
            -Direction Inbound `
            -Action Allow `
            -Protocol TCP `
            -LocalPort $port `
            -Profile Private `
            | Out-Null
        Write-Host "[LAN] Added Private-network firewall rule for TCP $port." -ForegroundColor Green
    }
}
