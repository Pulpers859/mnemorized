param(
    [Parameter(Mandatory = $true)]
    [string]$Name,

    [string]$BaseBranch = 'main',

    [string]$WorktreeRoot = 'C:\Dev\.agent-sandboxes\Mnemorized',

    [switch]$InstallRequirements
)

$ErrorActionPreference = 'Stop'

$repoRoot = 'C:\Dev\Mnemorized'

function ConvertTo-WorktreeSlug {
    param([string]$Value)

    $slug = $Value.Trim().ToLowerInvariant() -replace '[^a-z0-9._-]+', '-'
    $slug = $slug.Trim('-')

    if ([string]::IsNullOrWhiteSpace($slug)) {
        throw 'The worktree name must contain at least one letter or number.'
    }

    return $slug
}

function Invoke-GitChecked {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [string]$WorkingDirectory = $repoRoot
    )

    & git -C $WorkingDirectory @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path -LiteralPath $repoRoot)) {
    throw "The Mnemorized source-of-truth repo was not found at $repoRoot."
}

$actualRoot = (& git -C $repoRoot rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0 -or $actualRoot -ne ($repoRoot -replace '\\', '/')) {
    throw "Expected $repoRoot to be the Mnemorized git repo, but git reported '$actualRoot'."
}

$slug = ConvertTo-WorktreeSlug -Value $Name
$branchName = "agent/$slug"
$worktreePath = Join-Path $WorktreeRoot $slug

if (Test-Path -LiteralPath $worktreePath) {
    throw "A worktree path already exists at $worktreePath."
}

$existingBranch = ((& git -C $repoRoot branch --list $branchName) | Out-String).Trim()
if ($existingBranch) {
    throw "Branch '$branchName' already exists. Choose a different name or remove the old branch first."
}

Invoke-GitChecked -Arguments @('fetch', '--all', '--prune')
Invoke-GitChecked -Arguments @('rev-parse', '--verify', $BaseBranch)

New-Item -ItemType Directory -Force -Path $WorktreeRoot | Out-Null
Invoke-GitChecked -Arguments @('worktree', 'add', '-b', $branchName, $worktreePath, $BaseBranch)

$envExamplePath = Join-Path $worktreePath 'backend\.env.example'
$envPath = Join-Path $worktreePath 'backend\.env'
if ((Test-Path -LiteralPath $envExamplePath) -and -not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $envExamplePath -Destination $envPath
    Write-Host 'Created backend\.env from backend\.env.example with placeholders only.' -ForegroundColor Yellow
}

if ($InstallRequirements) {
    $venvPath = Join-Path $worktreePath '.venv'
    $venvPython = Join-Path $venvPath 'Scripts\python.exe'
    $requirementsPath = Join-Path $worktreePath 'backend\requirements.txt'

    & python -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Creating the virtual environment failed with exit code $LASTEXITCODE."
    }

    & $venvPython -m pip install -r $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "Installing requirements failed with exit code $LASTEXITCODE."
    }
}

Write-Host "Created Mnemorized agent worktree:" -ForegroundColor Green
Write-Host "  Path:   $worktreePath"
Write-Host "  Branch: $branchName"
Write-Host ''
Write-Host 'Suggested next commands:' -ForegroundColor Cyan
Write-Host "  Set-Location -LiteralPath '$worktreePath'"
Write-Host '  python -m compileall backend'
Write-Host '  python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001'
