param(
    [switch]$Tests,

    [switch]$SmokeServer,

    [int]$Port = 8001
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path

if (-not (Test-Path -LiteralPath $repoRoot)) {
    throw "The Mnemorized repo was not found at $repoRoot."
}

Set-Location -LiteralPath $repoRoot

Write-Host 'Compiling backend Python files...' -ForegroundColor Cyan
python -m compileall backend
if ($LASTEXITCODE -ne 0) {
    throw "python -m compileall backend failed with exit code $LASTEXITCODE."
}

if ($Tests) {
    Write-Host 'Running pytest...' -ForegroundColor Cyan
    python -m pytest tests
    if ($LASTEXITCODE -ne 0) {
        throw "python -m pytest tests failed with exit code $LASTEXITCODE."
    }
}

if ($SmokeServer) {
    $baseUrl = "http://127.0.0.1:$Port"
    $stdoutLog = Join-Path $env:TEMP "mnemorized-uvicorn-$Port.out.log"
    $stderrLog = Join-Path $env:TEMP "mnemorized-uvicorn-$Port.err.log"
    $process = $null

    try {
        Write-Host "Starting smoke server on $baseUrl..." -ForegroundColor Cyan
        $process = Start-Process -FilePath 'python' `
            -ArgumentList @('-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', "$Port") `
            -WorkingDirectory $repoRoot `
            -WindowStyle Hidden `
            -PassThru `
            -RedirectStandardOutput $stdoutLog `
            -RedirectStandardError $stderrLog

        $ready = $false
        for ($attempt = 1; $attempt -le 30; $attempt++) {
            if ($process.HasExited) {
                throw "Smoke server exited early with code $($process.ExitCode). See $stderrLog."
            }

            try {
                Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl/api/health" -TimeoutSec 2 | Out-Null
                $ready = $true
                break
            } catch {
                Start-Sleep -Seconds 1
            }
        }

        if (-not $ready) {
            throw "Smoke server did not respond at $baseUrl/api/health within 30 seconds."
        }

        foreach ($route in @('/', '/forge', '/library', '/api/health')) {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "$baseUrl$route" -TimeoutSec 10
            if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 400) {
                throw "Route $route returned HTTP $($response.StatusCode)."
            }
            Write-Host "OK $route -> HTTP $($response.StatusCode)" -ForegroundColor Green
        }
    } finally {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
    }
}

Write-Host 'Mnemorized validation completed.' -ForegroundColor Green
