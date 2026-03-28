param(
    [string]$TargetSsid = "KFCandWatermelon",
    [string]$InterfaceAlias = "Wi-Fi",
    [int]$ConnectWaitSeconds = 15,
    [string]$LogPath = "",
    [switch]$SetPrivate
)

$ErrorActionPreference = "Stop"

$script:ResolvedInterfaceAlias = $null

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
            Where-Object { $_.InterfaceAlias -eq $script:ResolvedInterfaceAlias } |
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

function Test-SsidMatch {
    param(
        [string]$Observed,
        [string]$Expected
    )

    if ([string]::IsNullOrWhiteSpace($Observed) -or [string]::IsNullOrWhiteSpace($Expected)) {
        return $false
    }

    if ($Observed -eq $Expected) {
        return $true
    }

    if ($Observed -like "$Expected *") {
        return $true
    }

    return $false
}

function Resolve-WifiInterfaceAlias {
    param([string]$PreferredAlias)

    try {
        $adapters = Get-NetAdapter -ErrorAction Stop
    } catch {
        Write-Log "Get-NetAdapter failed: $($_.Exception.Message)"
        return $PreferredAlias
    }

    if ($PreferredAlias) {
        $exact = $adapters | Where-Object { $_.Name -eq $PreferredAlias } | Select-Object -First 1
        if ($exact) {
            return $exact.Name
        }
    }

    $candidates = $adapters | Where-Object {
        $_.InterfaceDescription -match 'Wireless|Wi-?Fi|WLAN|802\.11' -or $_.Name -match 'Wi-?Fi|WLAN'
    }

    if (-not $candidates) {
        Write-Log "No wireless adapter candidates found. Falling back to preferred alias '$PreferredAlias'."
        return $PreferredAlias
    }

    $connectedCandidate = $candidates | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1
    if ($connectedCandidate) {
        Write-Log "Auto-detected wireless adapter '$($connectedCandidate.Name)'."
        return $connectedCandidate.Name
    }

    $firstCandidate = $candidates | Select-Object -First 1
    Write-Log "Using first wireless adapter candidate '$($firstCandidate.Name)'."
    return $firstCandidate.Name
}

$script:ResolvedInterfaceAlias = Resolve-WifiInterfaceAlias -PreferredAlias $InterfaceAlias

$currentSsid = Get-CurrentWifiSsid
if (Test-SsidMatch -Observed $currentSsid -Expected $TargetSsid) {
    Write-Log "Already connected to target network ('$currentSsid')."
    if ($SetPrivate) {
        Ensure-PrivateProfile -ExpectedSsid $TargetSsid -ExpectedInterfaceAlias $script:ResolvedInterfaceAlias
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

Write-Log "Current SSID '$currentSsid' is not '$TargetSsid'. Attempting reconnect via '$script:ResolvedInterfaceAlias'."
$connectOutput = netsh wlan connect name="$TargetSsid" ssid="$TargetSsid" interface="$script:ResolvedInterfaceAlias" | Out-String
Write-Log ($connectOutput.Trim())

Start-Sleep -Seconds $ConnectWaitSeconds
$newSsid = Get-CurrentWifiSsid
if (-not (Test-SsidMatch -Observed $newSsid -Expected $TargetSsid)) {
    Write-Log "Reconnect failed. Current SSID is '$newSsid'."
    exit 1
}

Write-Log "Connected to '$TargetSsid' successfully."
if ($SetPrivate) {
    Ensure-PrivateProfile -ExpectedSsid $TargetSsid -ExpectedInterfaceAlias $script:ResolvedInterfaceAlias
}

exit 0
