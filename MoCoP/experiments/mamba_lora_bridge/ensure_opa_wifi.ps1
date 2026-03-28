param(
    [string]$TargetSsid = "KFCandWatermelon",
    [string]$InterfaceAlias = "Wi-Fi",
    [int]$ConnectWaitSeconds = 15,
    [string]$LogPath = "",
    [switch]$SetPrivate
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message)

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$timestamp] $Message"
    Write-Host $line

    if ($LogPath) {
        $logDir = Split-Path -Parent $LogPath
        if ($logDir -and -not (Test-Path $logDir)) {
            New-Item -ItemType Directory -Path $logDir -Force | Out-Null
        }
        Add-Content -Path $LogPath -Value $line -Encoding UTF8
    }
}

function Get-CurrentWifiSsid {
    try {
        $output = netsh wlan show interfaces | Out-String
        foreach ($line in ($output -split "`r?`n")) {
            if ($line -match '^\s*SSID\s*:\s*(.+)$' -and $line -notmatch '^\s*BSSID\s*:') {
                $ssid = $Matches[1].Trim()
                if ($ssid) {
                    return $ssid
                }
            }
        }
    } catch {
        Write-Log "netsh wlan show interfaces failed: $($_.Exception.Message)"
    }

    try {
        $profile = Get-NetConnectionProfile |
            Where-Object { $_.InterfaceAlias -eq $InterfaceAlias } |
            Select-Object -First 1

        if ($profile -and $profile.Name) {
            Write-Log "Falling back to Get-NetConnectionProfile for current SSID detection."
            return $profile.Name.Trim()
        }
    } catch {
        Write-Log "Get-NetConnectionProfile fallback failed: $($_.Exception.Message)"
    }

    return $null
}

function Get-VisibleWifiSsids {
    $ssids = New-Object System.Collections.Generic.HashSet[string] ([System.StringComparer]::Ordinal)

    try {
        $output = netsh wlan show networks mode=bssid | Out-String
        foreach ($line in ($output -split "`r?`n")) {
            if ($line -match '^\s*SSID\s+\d+\s*:\s*(.*)$') {
                $ssid = $Matches[1].Trim()
                if ($ssid) {
                    [void]$ssids.Add($ssid)
                }
            }
        }
    } catch {
        Write-Log "netsh wlan show networks failed: $($_.Exception.Message)"
    }

    return @($ssids)
}

function Ensure-PrivateProfile {
    param(
        [string]$ExpectedSsid,
        [string]$ExpectedInterfaceAlias
    )

    try {
        $profile = Get-NetConnectionProfile |
            Where-Object { $_.InterfaceAlias -eq $ExpectedInterfaceAlias -and $_.Name -eq $ExpectedSsid } |
            Select-Object -First 1

        if ($null -eq $profile) {
            Write-Log "No matching network profile found for SSID '$ExpectedSsid' on '$ExpectedInterfaceAlias'."
            return
        }

        if ($profile.NetworkCategory -ne "Private") {
            Set-NetConnectionProfile -InterfaceAlias $ExpectedInterfaceAlias -NetworkCategory Private
            Write-Log "Set network profile for '$ExpectedSsid' on '$ExpectedInterfaceAlias' to Private."
        } else {
            Write-Log "Network profile for '$ExpectedSsid' on '$ExpectedInterfaceAlias' is already Private."
        }
    } catch {
        Write-Log "Failed to set Private profile: $($_.Exception.Message)"
    }
}

$currentSsid = Get-CurrentWifiSsid
if ($currentSsid -eq $TargetSsid) {
    Write-Log "Already connected to '$TargetSsid'."
    if ($SetPrivate) {
        Ensure-PrivateProfile -ExpectedSsid $TargetSsid -ExpectedInterfaceAlias $InterfaceAlias
    }
    exit 0
}

$visibleSsids = Get-VisibleWifiSsids
if ($visibleSsids.Count -gt 0 -and $visibleSsids -notcontains $TargetSsid) {
    Write-Log "Target SSID '$TargetSsid' is not currently visible. Current SSID: '$currentSsid'."
    exit 2
}

if ($visibleSsids.Count -eq 0) {
    Write-Log "Visible SSID scan returned no data. Proceeding with stored-profile reconnect attempt."
}

Write-Log "Current SSID '$currentSsid' is not '$TargetSsid'. Attempting reconnect via '$InterfaceAlias'."
$connectOutput = netsh wlan connect name="$TargetSsid" ssid="$TargetSsid" interface="$InterfaceAlias" | Out-String
Write-Log ($connectOutput.Trim())

Start-Sleep -Seconds $ConnectWaitSeconds
$newSsid = Get-CurrentWifiSsid
if ($newSsid -ne $TargetSsid) {
    Write-Log "Reconnect failed. Current SSID is '$newSsid'."
    exit 1
}

Write-Log "Connected to '$TargetSsid' successfully."
if ($SetPrivate) {
    Ensure-PrivateProfile -ExpectedSsid $TargetSsid -ExpectedInterfaceAlias $InterfaceAlias
}

exit 0
