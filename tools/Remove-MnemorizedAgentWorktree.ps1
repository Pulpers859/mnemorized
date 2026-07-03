param(
    [Parameter(Mandatory = $true)]
    [string]$NameOrPath,

    [string]$WorktreeRoot = 'C:\Dev\.agent-sandboxes\Mnemorized',

    [switch]$DeleteBranch,

    [switch]$Force
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

if (Test-Path -LiteralPath $NameOrPath) {
    $worktreePath = (Resolve-Path -LiteralPath $NameOrPath).Path
} else {
    $slug = ConvertTo-WorktreeSlug -Value $NameOrPath
    $worktreePath = Join-Path $WorktreeRoot $slug
}

if (-not (Test-Path -LiteralPath $worktreePath)) {
    throw "No worktree was found at $worktreePath."
}

$reportedRoot = (& git -C $worktreePath rev-parse --show-toplevel).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "$worktreePath is not a git worktree."
}

$normalizedWorktreePath = ($worktreePath -replace '\\', '/').TrimEnd('/')
if ($reportedRoot.TrimEnd('/') -ne $normalizedWorktreePath) {
    throw "Refusing to remove $worktreePath because git reported a different root: $reportedRoot."
}

$branchName = ((& git -C $worktreePath branch --show-current) | Out-String).Trim()
$status = (& git -C $worktreePath status --porcelain)
if ($status -and -not $Force) {
    throw "Worktree '$worktreePath' has local changes. Review them first or rerun with -Force."
}

$removeArgs = @('worktree', 'remove', $worktreePath)
if ($Force) {
    $removeArgs += '--force'
}

Invoke-GitChecked -Arguments $removeArgs

if ($DeleteBranch -and $branchName) {
    if ($branchName -notlike 'agent/*') {
        Write-Warning "Branch '$branchName' does not use the agent/ prefix, so it was not deleted."
    } else {
        $deleteMode = if ($Force) { '-D' } else { '-d' }
        Invoke-GitChecked -Arguments @('branch', $deleteMode, $branchName)
    }
}

Write-Host "Removed Mnemorized agent worktree: $worktreePath" -ForegroundColor Green
if ($DeleteBranch -and $branchName -like 'agent/*') {
    Write-Host "Deleted branch: $branchName" -ForegroundColor Green
}
