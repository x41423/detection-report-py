[CmdletBinding()]
param(
    [string[]]$IpAddresses,
    [string]$IpAddress,
    [string]$Password = "detect-report-dev",
    [string]$CertDir,
    [switch]$SkipTrustInstall
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($CertDir)) {
    $CertDir = Join-Path $PSScriptRoot "..\frontend\certs"
}

function Ensure-Directory {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Get-LatestCertificateByFriendlyName {
    param(
        [Parameter(Mandatory = $true)][string]$StorePath,
        [Parameter(Mandatory = $true)][string]$FriendlyName
    )

    $matches = Get-ChildItem -Path $StorePath -ErrorAction SilentlyContinue |
        Where-Object { $_.FriendlyName -eq $FriendlyName } |
        Sort-Object NotAfter -Descending

    if ($matches) {
        return $matches[0]
    }

    return $null
}

function Add-CertificateToRootStore {
    param([Parameter(Mandatory = $true)][System.Security.Cryptography.X509Certificates.X509Certificate2]$Certificate)

    $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "CurrentUser")
    $rootStore.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)

    try {
        $existing = $rootStore.Certificates | Where-Object { $_.Thumbprint -eq $Certificate.Thumbprint }
        if (-not $existing) {
            $rootStore.Add($Certificate)
        }
    }
    finally {
        $rootStore.Close()
    }
}

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
    if ($bytes[0] -eq 10) {
        return $true
    }
    if ($bytes[0] -eq 192 -and $bytes[1] -eq 168) {
        return $true
    }
    if ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) {
        return $true
    }
    return $false
}

function Get-DefaultPrivateIpv4Addresses {
    $addresses = New-Object System.Collections.Generic.List[string]

    try {
        $candidates = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object {
                $_.IPAddress -notlike "127.*" -and
                $_.IPAddress -notlike "169.254.*" -and
                $_.PrefixOrigin -ne "WellKnown" -and
                (Test-PrivateIpv4 $_.IPAddress)
            } |
            Sort-Object -Property InterfaceMetric, SkipAsSource

        foreach ($candidate in $candidates) {
            $ip = [string]$candidate.IPAddress
            if (-not [string]::IsNullOrWhiteSpace($ip) -and -not $addresses.Contains($ip)) {
                $addresses.Add($ip)
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
            if (-not [string]::IsNullOrWhiteSpace($ip) -and -not $addresses.Contains($ip)) {
                $addresses.Add($ip)
            }
        }
    }

    return $addresses.ToArray()
}

Ensure-Directory -Path $CertDir

$resolvedIpAddresses = New-Object System.Collections.Generic.List[string]
foreach ($candidate in @($IpAddresses)) {
    $value = [string]$candidate
    if (-not [string]::IsNullOrWhiteSpace($value) -and -not $resolvedIpAddresses.Contains($value)) {
        $resolvedIpAddresses.Add($value)
    }
}
if (-not [string]::IsNullOrWhiteSpace($IpAddress) -and -not $resolvedIpAddresses.Contains($IpAddress)) {
    $resolvedIpAddresses.Add($IpAddress)
}
if ($resolvedIpAddresses.Count -eq 0) {
    foreach ($candidate in Get-DefaultPrivateIpv4Addresses) {
        if (-not $resolvedIpAddresses.Contains($candidate)) {
            $resolvedIpAddresses.Add($candidate)
        }
    }
}
if ($resolvedIpAddresses.Count -eq 0) {
    $resolvedIpAddresses.Add("192.168.1.8")
}

$rootFriendlyName = "DetectionReport Dev Root CA"
$primaryIpAddress = $resolvedIpAddresses[0]
$serverFriendlyName = "DetectionReport Dev HTTPS ($primaryIpAddress)"
$rootCertPath = Join-Path $CertDir "dev-root-ca.cer"
$serverPfxPath = Join-Path $CertDir "dev-server.pfx"
$securePassword = ConvertTo-SecureString -String $Password -Force -AsPlainText

$rootCert = Get-LatestCertificateByFriendlyName -StorePath "Cert:\CurrentUser\My" -FriendlyName $rootFriendlyName
if (-not $rootCert) {
    $rootCert = New-SelfSignedCertificate `
        -Type Custom `
        -Subject "CN=$rootFriendlyName" `
        -FriendlyName $rootFriendlyName `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -KeyAlgorithm RSA `
        -KeyLength 2048 `
        -HashAlgorithm SHA256 `
        -KeyExportPolicy Exportable `
        -KeyUsage CertSign, CRLSign, DigitalSignature `
        -KeyUsageProperty Sign `
        -TextExtension @(
            "2.5.29.19={critical}{text}CA=true"
        ) `
        -NotAfter (Get-Date).AddYears(10)
}

if (-not $SkipTrustInstall) {
    Add-CertificateToRootStore -Certificate $rootCert
}

$sanEntries = New-Object System.Collections.Generic.List[string]
$sanEntries.Add("DNS=localhost")
$sanEntries.Add("IP Address=127.0.0.1")
foreach ($address in $resolvedIpAddresses) {
    if (-not $sanEntries.Contains("IP Address=$address")) {
        $sanEntries.Add("IP Address=$address")
    }
}
$sanTextExtension = "2.5.29.17={text}" + ($sanEntries -join "&")

$serverCert = New-SelfSignedCertificate `
    -Type Custom `
    -Subject "CN=$primaryIpAddress" `
    -FriendlyName $serverFriendlyName `
    -Signer $rootCert `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -KeyAlgorithm RSA `
    -KeyLength 2048 `
    -HashAlgorithm SHA256 `
    -KeyExportPolicy Exportable `
    -KeyUsage DigitalSignature, KeyEncipherment `
    -TextExtension @(
        "2.5.29.19={critical}{text}CA=false",
        "2.5.29.37={text}1.3.6.1.5.5.7.3.1",
        $sanTextExtension
    ) `
    -NotAfter (Get-Date).AddYears(2)

Export-Certificate -Cert $rootCert -FilePath $rootCertPath -Force | Out-Null
Export-PfxCertificate -Cert $serverCert -FilePath $serverPfxPath -Password $securePassword -Force | Out-Null

Write-Host ""
Write-Host "HTTPS dev certificates are ready." -ForegroundColor Green
Write-Host "Root CA:     $rootCertPath"
Write-Host "Server PFX:  $serverPfxPath"
Write-Host "Passphrase:  $Password"
Write-Host "IP SANs:     $($resolvedIpAddresses -join ', ')"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Start the HTTPS test server."
foreach ($address in $resolvedIpAddresses) {
    Write-Host "2. Open https://$address`:8000/tests/funasr-lab on the phone."
}
Write-Host "3. Install dev-root-ca.cer on the phone and mark it trusted if the browser still warns about the certificate."
Write-Host ""
