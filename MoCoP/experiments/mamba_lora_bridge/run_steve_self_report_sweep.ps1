param(
    [double[]]$Alphas = @(0.0, 0.1, 0.2, 0.3),
    [string[]]$Concepts = @("warm", "engaged", "focused"),
    [string]$BaseUrl = "http://192.168.2.49:7860",
    [string]$ExpectedModelId = "Qwen/Qwen2.5-1.5B",
    [double]$StartupTimeoutMinutes = 6,
    [switch]$IncludeConversation,
    [bool]$UseHostSideHttp = $true,
    [switch]$LeaveRunning
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$repoRoot = "C:\Users\cerub\OneDrive\Dokumente\LLM"
$outputDir = Join-Path $repoRoot "MoCoP\experiments\mamba_lora_bridge\run_reincarnation"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$timestamp = Get-Date -Format "yyyyMMddTHHmmss"
$jsonPath = Join-Path $outputDir ("steve_self_report_sweep_{0}.json" -f $timestamp)
$mdPath = Join-Path $outputDir ("steve_self_report_sweep_{0}.md" -f $timestamp)

function Invoke-JsonRequest {
    param(
        [string]$Method,
        [string]$Url,
        [object]$Body = $null,
        [int]$TimeoutSec = 60,
        [int]$Retries = 4
    )

    $attempt = 0
    $lastError = $null
    while ($attempt -lt $Retries) {
        $attempt += 1
        try {
            if ($UseHostSideHttp) {
                $uri = [System.Uri]$Url
                $hostSideUrl = "http://127.0.0.1:{0}{1}" -f $uri.Port, $uri.PathAndQuery
                if ($null -eq $Body) {
                    $remoteScript = "`$ProgressPreference = 'SilentlyContinue'; Invoke-RestMethod -Method $Method -Uri '$hostSideUrl' | ConvertTo-Json -Depth 10 -Compress"
                } else {
                    $bodyJson = $Body | ConvertTo-Json -Depth 8 -Compress
                    $remoteScript = @"
`$ProgressPreference = 'SilentlyContinue'
`$body = @'
$bodyJson
'@
Invoke-RestMethod -Method $Method -Uri '$hostSideUrl' -ContentType 'application/json' -Body `$body | ConvertTo-Json -Depth 10 -Compress
"@
                }
                $encodedCommand = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($remoteScript))
                $raw = & ssh steve powershell -NoProfile -EncodedCommand $encodedCommand
                if ($LASTEXITCODE -ne 0) {
                    throw "host-side ssh/http exited with code $LASTEXITCODE"
                }
                if (-not $raw) {
                    throw "Empty host-side response from $hostSideUrl"
                }
                $jsonText = ($raw -split "`r?`n" | Where-Object {
                    $line = $_.Trim()
                    $line.StartsWith("{") -or $line.StartsWith("[")
                } | Select-Object -First 1)
                if (-not $jsonText) {
                    throw "No JSON payload found in host-side response from $hostSideUrl"
                }
                return $jsonText | ConvertFrom-Json
            }

            $curlArgs = @(
                "-sS",
                "--max-time", "$TimeoutSec",
                "-X", $Method
            )

            $tempBodyPath = $null
            if ($null -ne $Body) {
                $tempBodyPath = [System.IO.Path]::GetTempFileName()
                ($Body | ConvertTo-Json -Depth 8 -Compress) | Set-Content -Path $tempBodyPath -Encoding UTF8 -NoNewline
                $curlArgs += @(
                    "-H", "Content-Type: application/json",
                    "--data-binary", "@$tempBodyPath"
                )
            }
            $curlArgs += $Url

            try {
                $raw = & curl.exe @curlArgs
                if ($LASTEXITCODE -ne 0) {
                    throw "curl exited with code $LASTEXITCODE"
                }
                if (-not $raw) {
                    throw "Empty response from $Url"
                }
                return $raw | ConvertFrom-Json
            } finally {
                if ($tempBodyPath -and (Test-Path $tempBodyPath)) {
                    Remove-Item -Path $tempBodyPath -Force -ErrorAction SilentlyContinue
                }
            }
        } catch {
            $lastError = $_
            if ($attempt -ge $Retries) {
                throw
            }
            Start-Sleep -Seconds ([Math]::Min(2 * $attempt, 6))
        }
    }

    throw $lastError
}

function Get-SteveStatus {
    return Invoke-JsonRequest -Method Get -Url ($BaseUrl.TrimEnd("/") + "/status") -TimeoutSec 20 -Retries 6
}

function Set-SteveAlpha([double]$AlphaValue) {
    & ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\set_steve_chat_alpha.ps1 -Alpha $AlphaValue
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to set Steve alpha to $AlphaValue"
    }
}

function Wait-SteveChatReady {
    param(
        [double]$ExpectedAlpha,
        [double]$ExpectedTemperature,
        [string]$ExpectedModel,
        [double]$TimeoutMinutes = 6
    )

    $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
    $lastSummary = "no status response"
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Get-SteveStatus
            $alphaMatches = $false
            $temperatureMatches = $false
            if ($null -ne $resp.alpha) {
                $alphaMatches = [Math]::Abs(([double]$resp.alpha) - $ExpectedAlpha) -lt 0.0001
            }
            if ($null -ne $resp.temperature) {
                $temperatureMatches = [Math]::Abs(([double]$resp.temperature) - $ExpectedTemperature) -lt 0.0001
            }
            $modelMatches = [string]$resp.model_id -eq $ExpectedModel
            $turnsReset = [int]$resp.turns -eq 0
            $lastSummary = "running=$($resp.running) busy=$($resp.busy) stop=$($resp.stop_requested) alpha=$($resp.alpha) temp=$($resp.temperature) model=$($resp.model_id) turns=$($resp.turns)"
            if ($resp.running -and -not $resp.stop_requested -and -not $resp.busy -and $alphaMatches -and $temperatureMatches -and $modelMatches -and $turnsReset) {
                return $resp
            }
        } catch {
            $lastSummary = $_.Exception.Message
        }
        Start-Sleep -Seconds 3
    }

    throw "Steve chat did not become ready for alpha=$ExpectedAlpha within $TimeoutMinutes minute(s). Last status: $lastSummary"
}

function Invoke-SelfReport([string[]]$ProbeConcepts, [bool]$UseConversation) {
    $body = @{
        concepts = $ProbeConcepts
        include_conversation = $UseConversation
    }
    return Invoke-JsonRequest -Method Post -Url ($BaseUrl.TrimEnd("/") + "/self_report") -Body $body -TimeoutSec 60 -Retries 5
}

function Get-MonotonicFlag([object[]]$Rows) {
    for ($i = 1; $i -lt $Rows.Count; $i += 1) {
        if ([double]$Rows[$i].expected_rating -lt ([double]$Rows[$i - 1].expected_rating - 1e-9)) {
            return $false
        }
    }
    return $true
}

$restoreAlpha = 0.2
$restoreTemperature = 0.7
$sweepRows = @()

try {
    $initialStatus = Get-SteveStatus
    if ($null -ne $initialStatus.alpha) {
        $restoreAlpha = [double]$initialStatus.alpha
    }
    if ($null -ne $initialStatus.temperature) {
        $restoreTemperature = [double]$initialStatus.temperature
    }

    foreach ($alpha in $Alphas) {
        Write-Host ("`n=== Steve self-report alpha {0:0.0} ===" -f $alpha)
        Set-SteveAlpha -AlphaValue $alpha
        $readyStatus = Wait-SteveChatReady -ExpectedAlpha $alpha -ExpectedTemperature $restoreTemperature -ExpectedModel $ExpectedModelId -TimeoutMinutes $StartupTimeoutMinutes
        $report = Invoke-SelfReport -ProbeConcepts $Concepts -UseConversation:$IncludeConversation

        foreach ($result in @($report.results)) {
            $sweepRows += [pscustomobject]@{
                alpha = [double]$alpha
                concept = [string]$result.concept
                expected_rating = [double]$result.expected_rating
                raw_expected_rating = [double]$result.raw_expected_rating
                digit_mass = [double]$result.digit_mass
                top_digit = [string]$result.top_digit
                top_digit_prob = [double]$result.top_digit_prob
                turns = [int]$report.turns
                include_conversation = [bool]$report.include_transcript
                started_at = [string]$readyStatus.started_at
            }
        }
    }

    $monotonicByConcept = @{}
    foreach ($concept in $Concepts) {
        $rows = @($sweepRows | Where-Object { $_.concept -eq $concept } | Sort-Object alpha)
        if ($rows.Count -gt 0) {
            $monotonicByConcept[$concept] = Get-MonotonicFlag -Rows $rows
        }
    }

    $payload = [ordered]@{
        captured_at = (Get-Date).ToString("o")
        base_url = $BaseUrl
        expected_model_id = $ExpectedModelId
        restore_alpha = $restoreAlpha
        restore_temperature = $restoreTemperature
        include_conversation = [bool]$IncludeConversation
        concepts = $Concepts
        rows = $sweepRows
        monotonic_by_concept = $monotonicByConcept
    }
    $payload | ConvertTo-Json -Depth 8 | Set-Content -Path $jsonPath -Encoding UTF8

    $lines = @()
    $lines += "# Steve Self-Report Alpha Sweep"
    $lines += ""
    $lines += "- Captured: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz'))"
    $lines += "- Base URL: $BaseUrl"
    $lines += "- Model: $ExpectedModelId"
    $lines += "- Include conversation: $([bool]$IncludeConversation)"
    $lines += "- Restore alpha/temp: $restoreAlpha / $restoreTemperature"
    $lines += "- Raw JSON: $(Split-Path -Leaf $jsonPath)"
    $lines += ""

    foreach ($concept in $Concepts) {
        $rows = @($sweepRows | Where-Object { $_.concept -eq $concept } | Sort-Object alpha)
        if ($rows.Count -eq 0) {
            continue
        }
        $lines += "## $concept"
        $lines += ""
        $lines += "- Monotonic increasing: $($monotonicByConcept[$concept])"
        $lines += ""
        $lines += "| alpha | expected | raw_expected | digit_mass | top_digit | top_prob |"
        $lines += "|---|---:|---:|---:|---:|---:|"
        foreach ($row in $rows) {
            $lines += ("| {0:0.0} | {1:N4} | {2:N4} | {3:N4} | {4} | {5:N4} |" -f $row.alpha, $row.expected_rating, $row.raw_expected_rating, $row.digit_mass, $row.top_digit, $row.top_digit_prob)
        }
        $lines += ""
    }

    $lines -join "`r`n" | Set-Content -Path $mdPath -Encoding UTF8
    Write-Host "Wrote $jsonPath"
    Write-Host "Wrote $mdPath"
} finally {
    Write-Host ("`nRestoring Steve defaults alpha={0:0.0}" -f $restoreAlpha)
    try {
        Set-SteveAlpha -AlphaValue $restoreAlpha
        Wait-SteveChatReady -ExpectedAlpha $restoreAlpha -ExpectedTemperature $restoreTemperature -ExpectedModel $ExpectedModelId -TimeoutMinutes $StartupTimeoutMinutes | Out-Null
    } catch {
        Write-Warning "Failed to restore Steve defaults cleanly: $($_.Exception.Message)"
    }

    if (-not $LeaveRunning) {
        try {
            & ssh steve powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\tikii\bridge\stop_steve_chat_task.ps1
        } catch {
            Write-Warning "Failed to stop Steve chat task after sweep: $($_.Exception.Message)"
        }
    }
}
