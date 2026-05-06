[CmdletBinding()]
param(
    [int]$FrontendPort = 5173,
    [int]$BackendPort = 8000,
    [string]$Scheme = "http"
)

$ErrorActionPreference = "SilentlyContinue"

function Test-PrivateIpv4 {
    param([Parameter(Mandatory = $true)][string]$Address)

    $parsed = $null
    if (-not [System.Net.IPAddress]::TryParse($Address, [ref]$parsed)) {
        return $false
    }

    $bytes = $parsed.GetAddressBytes()
    if ($bytes.Length -ne 4) {
        return $false
    }
    return (
        $bytes[0] -eq 10 -or
        ($bytes[0] -eq 192 -and $bytes[1] -eq 168) -or
        ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31)
    )
}

function Get-LanIpv4Addresses {
    $addresses = New-Object System.Collections.Generic.List[string]

    try {
        $preferred = Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object {
                $_.IPAddress -notlike "127.*" -and
                $_.IPAddress -notlike "169.254.*" -and
                $_.AddressState -eq "Preferred" -and
                (Test-PrivateIpv4 $_.IPAddress) -and
                $_.InterfaceAlias -notmatch "vEthernet|Virtual|VMware|Hyper-V|Loopback"
            } |
            Sort-Object -Property InterfaceMetric, InterfaceAlias, IPAddress

        foreach ($candidate in $preferred) {
            $ip = [string]$candidate.IPAddress
            if (-not $addresses.Contains($ip)) {
                $addresses.Add($ip)
            }
        }

        if ($addresses.Count -eq 0) {
            $fallback = Get-NetIPAddress -AddressFamily IPv4 |
                Where-Object {
                    $_.IPAddress -notlike "127.*" -and
                    $_.IPAddress -notlike "169.254.*" -and
                    $_.AddressState -eq "Preferred" -and
                    (Test-PrivateIpv4 $_.IPAddress)
                } |
                Sort-Object -Property InterfaceMetric, InterfaceAlias, IPAddress
            foreach ($candidate in $fallback) {
                $ip = [string]$candidate.IPAddress
                if (-not $addresses.Contains($ip)) {
                    $addresses.Add($ip)
                }
            }
        }
    }
    catch {
        $hostAddresses = [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName()) |
            Where-Object {
                $_.AddressFamily -eq [System.Net.Sockets.AddressFamily]::InterNetwork -and
                (Test-PrivateIpv4 $_.IPAddressToString)
            }
        foreach ($address in $hostAddresses) {
            $ip = [string]$address.IPAddressToString
            if (-not $addresses.Contains($ip)) {
                $addresses.Add($ip)
            }
        }
    }

    return $addresses.ToArray()
}

$ips = Get-LanIpv4Addresses
if (-not $ips -or $ips.Count -eq 0) {
    Write-Host "  LAN:      no private IPv4 address detected" -ForegroundColor Yellow
    exit 0
}

Write-Host "  LAN frontend URLs:" -ForegroundColor White
foreach ($ip in $ips) {
    Write-Host "    ${Scheme}://${ip}:$FrontendPort" -ForegroundColor White
}
Write-Host "  LAN backend docs:" -ForegroundColor White
foreach ($ip in $ips) {
    Write-Host "    http://${ip}:$BackendPort/docs" -ForegroundColor White
}
