param(
    [int[]]$PreferredPorts = @(8001, 8010, 8020, 8050, 8080)
)

$ErrorActionPreference = 'Stop'

$repoRoot = 'C:\Dev\Mnemorized'
$requirementsPath = Join-Path $repoRoot 'backend\requirements.txt'
$envPath = Join-Path $repoRoot 'backend\.env'
$envExamplePath = Join-Path $repoRoot 'backend\.env.example'

function Test-PortAvailable {
    param([int]$Port)

    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener) {
            $listener.Stop()
        }
    }
}

function Select-AppPort {
    param([int[]]$Ports)

    foreach ($port in $Ports) {
        if (Test-PortAvailable -Port $port) {
            return $port
        }
    }

    throw "None of the preferred local ports were available: $($Ports -join ', ')"
}

try {
    if (-not (Test-Path -LiteralPath $repoRoot)) {
        throw "The Mnemorized repo was not found at $repoRoot."
    }

    Set-Location -LiteralPath $repoRoot

    if ($host.Name -ne 'ServerRemoteHost') {
        $host.UI.RawUI.WindowTitle = 'Mnemorized Local App'
    }

    Write-Host "Mnemorized repo: $repoRoot" -ForegroundColor Cyan

    if (-not (Test-Path -LiteralPath $requirementsPath)) {
        throw "Could not find Python requirements at $requirementsPath."
    }

    if (-not (Test-Path -LiteralPath $envPath)) {
        if (Test-Path -LiteralPath $envExamplePath) {
            Copy-Item -LiteralPath $envExamplePath -Destination $envPath
            Write-Host "Created backend\.env from backend\.env.example." -ForegroundColor Yellow
            Write-Host "Add real API keys there when you want provider generation or saved library features." -ForegroundColor Yellow
        } else {
            Write-Warning "backend\.env is missing, and backend\.env.example was not found."
        }
    }

    Write-Host "Installing/updating Python requirements..." -ForegroundColor Cyan
    python -m pip install -r $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed with exit code $LASTEXITCODE."
    }

    $port = Select-AppPort -Ports $PreferredPorts
    $baseUrl = "http://127.0.0.1:$port"
    $forgeUrl = "$baseUrl/forge"

    Write-Host "Starting Mnemorized on $baseUrl" -ForegroundColor Green
    Write-Host "Opening $forgeUrl once the server responds..." -ForegroundColor DarkGray
    Write-Host "Leave this PowerShell window open while testing. Press Ctrl+C here to stop the app." -ForegroundColor DarkGray

    Start-Job -ScriptBlock {
        param([string]$HealthUrl, [string]$OpenUrl)

        for ($attempt = 1; $attempt -le 60; $attempt++) {
            try {
                Invoke-WebRequest -UseBasicParsing -Uri $HealthUrl -TimeoutSec 2 | Out-Null
                Start-Process $OpenUrl
                return
            } catch {
                Start-Sleep -Seconds 1
            }
        }
    } -ArgumentList "$baseUrl/api/health", $forgeUrl | Out-Null

    python -m uvicorn backend.app.main:app --host 127.0.0.1 --port $port --reload
    exit $LASTEXITCODE
} catch {
    Write-Error $_.Exception.Message
    Write-Host "Press Enter to close this window." -ForegroundColor DarkGray
    [void][System.Console]::ReadLine()
    exit 1
}
