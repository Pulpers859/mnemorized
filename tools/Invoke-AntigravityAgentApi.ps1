param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("NewConversation", "SendMessage", "Metadata", "PrintEnv")]
    [string]$Command,

    [string]$ConversationId,
    [string]$Title = "Mnemorized Visual QA",
    [string]$Prompt,
    [string]$PromptFile,
    [string]$Model = "pro",
    [string]$ProjectId = "79655949-1be7-444b-817e-c0ecd5768c5c",
    [switch]$PassPromptFileAsAtPath
)

$ErrorActionPreference = "Stop"

function Get-AgentApiPath {
    $candidates = @(
        (Join-Path $env:USERPROFILE ".gemini\antigravity\bin\agentapi.bat"),
        "C:\Users\PATRIC~1\.gemini\antigravity\bin\agentapi.bat"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "Could not find Antigravity agentapi.bat. Checked: $($candidates -join ', ')"
}

function Get-AntigravityLanguageServer {
    $processes = Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -ieq "language_server.exe" -and
            $_.CommandLine -match "\bagentapi\b|--csrf_token|--csrf-token"
        }

    if (-not $processes) {
        $processes = Get-CimInstance Win32_Process |
            Where-Object { $_.Name -ieq "language_server.exe" }
    }

    if (-not $processes) {
        throw "Antigravity language_server.exe is not running. Launch Antigravity first."
    }

    $selected = $processes | Sort-Object ProcessId -Descending | Select-Object -First 1
    $commandLine = [string]$selected.CommandLine
    $csrf = $null

    if ($commandLine -match "--csrf_token[=\s]+(`"([^`"]+)`"|([^\s]+))") {
        $csrf = if ($Matches[2]) { $Matches[2] } else { $Matches[3] }
    } elseif ($commandLine -match "--csrf-token[=\s]+(`"([^`"]+)`"|([^\s]+))") {
        $csrf = if ($Matches[2]) { $Matches[2] } else { $Matches[3] }
    }

    if (-not $csrf) {
        throw "Could not extract --csrf_token from language_server.exe command line for PID $($selected.ProcessId)."
    }

    $ports = @()
    try {
        $ports = Get-NetTCPConnection -OwningProcess $selected.ProcessId -State Listen -ErrorAction Stop |
            Where-Object { $_.LocalAddress -in @("127.0.0.1", "0.0.0.0", "::1", "::") } |
            Select-Object -ExpandProperty LocalPort
    } catch {
        $netstat = netstat -ano | Select-String -Pattern "\sLISTENING\s+$($selected.ProcessId)$"
        foreach ($line in $netstat) {
            if ($line.Line -match "^\s*\S+\s+\S+:(\d+)\s+") {
                $ports += [int]$Matches[1]
            }
        }
    }

    $ports = @($ports | Sort-Object -Unique)
    if (-not $ports) {
        throw "Could not find a listening port for language_server.exe PID $($selected.ProcessId)."
    }

    # Antigravity exposes multiple localhost ports. The higher listening port has
    # been the HTTPS language-server port used by agentapi.
    $httpsPort = @($ports | Sort-Object -Descending)[0]

    [pscustomobject]@{
        ProcessId = $selected.ProcessId
        Address = "127.0.0.1:$httpsPort"
        CsrfToken = $csrf
        Ports = $ports
    }
}

function Get-PromptArgument {
    if ($PromptFile) {
        $resolvedPromptFile = (Resolve-Path -LiteralPath $PromptFile).Path
        if ($PassPromptFileAsAtPath) {
            return "@$resolvedPromptFile"
        }
        return (Get-Content -LiteralPath $resolvedPromptFile -Raw)
    }

    if ($Prompt) {
        return $Prompt
    }

    throw "Provide -Prompt or -PromptFile for $Command."
}

$agentApi = Get-AgentApiPath
$server = Get-AntigravityLanguageServer

$env:ANTIGRAVITY_LS_ADDRESS = $server.Address
$env:ANTIGRAVITY_CSRF_TOKEN = $server.CsrfToken
$env:ANTIGRAVITY_PROJECT_ID = $ProjectId

if ($Command -eq "PrintEnv") {
    [pscustomobject]@{
        AgentApi = $agentApi
        ANTIGRAVITY_LS_ADDRESS = $env:ANTIGRAVITY_LS_ADDRESS
        ANTIGRAVITY_CSRF_TOKEN = $env:ANTIGRAVITY_CSRF_TOKEN
        ANTIGRAVITY_PROJECT_ID = $env:ANTIGRAVITY_PROJECT_ID
        LanguageServerPid = $server.ProcessId
        ListeningPorts = ($server.Ports -join ",")
    }
    exit 0
}

switch ($Command) {
    "NewConversation" {
        $promptArg = Get-PromptArgument
        & $agentApi new-conversation "--model=$Model" "--title=$Title" $promptArg
        exit $LASTEXITCODE
    }
    "SendMessage" {
        if (-not $ConversationId) {
            throw "Provide -ConversationId for SendMessage."
        }
        $promptArg = Get-PromptArgument
        & $agentApi send-message $ConversationId $promptArg
        exit $LASTEXITCODE
    }
    "Metadata" {
        if (-not $ConversationId) {
            throw "Provide -ConversationId for Metadata."
        }
        & $agentApi get-conversation-metadata $ConversationId
        exit $LASTEXITCODE
    }
}
