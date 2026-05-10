<#
.SYNOPSIS
Check how far the local main branch has diverged from upstream.

.DESCRIPTION
Fetches the latest from origin and reports ahead/behind counts.
Warns if the branch is more than 50 commits behind upstream,
suggesting it's time to run the periodic sync workflow.

.EXAMPLE
powershell scripts/check_upstream.ps1

.NOTES
File: scripts/check_upstream.ps1
Description: Periodic upstream drift checker for Hermes-Agent
Primary Functions:
  - Fetches latest from origin
  - Reports ahead/behind divergence counts
  - Warns when threshold exceeded (>50 commits behind)
Revision: 0.1.1
#>

Write-Host "Checking upstream drift..." -ForegroundColor Cyan
Write-Host ""

# Fetch latest from origin
Write-Host "Fetching from origin..." -ForegroundColor Gray
git fetch origin 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to fetch from origin" -ForegroundColor Red
    exit 1
}

# Get current branch
$currentBranch = git rev-parse --abbrev-ref HEAD 2>$null

if ($currentBranch -ne "main") {
    Write-Host "WARNING: Not on main branch (currently on: $currentBranch)" -ForegroundColor Yellow
    Write-Host "Switch to main to check upstream drift" -ForegroundColor Yellow
    exit 0
}

# Calculate divergence
$BEHIND = (git rev-list --count HEAD..origin/main 2>$null)
$AHEAD = (git rev-list --count origin/main..HEAD 2>$null)

if (-not $BEHIND) { $BEHIND = 0 } else { $BEHIND = [int]$BEHIND }
if (-not $AHEAD) { $AHEAD = 0 } else { $AHEAD = [int]$AHEAD }

Write-Host "Main branch status:" -ForegroundColor Cyan
Write-Host "  Ahead:  $AHEAD commits" -ForegroundColor $(if ($AHEAD -eq 0) { "Green" } else { "Yellow" })
Write-Host "  Behind: $BEHIND commits" -ForegroundColor $(if ($BEHIND -eq 0) { "Green" } elseif ($BEHIND -gt 50) { "Red" } else { "Yellow" })
Write-Host ""

# Warning for large divergence
if ($BEHIND -gt 50) {
    Write-Host "WARNING: More than 50 commits behind upstream!" -ForegroundColor Yellow
    Write-Host "Consider running upstream sync workflow:" -ForegroundColor Yellow
    Write-Host "  1. Review recent upstream changes:" -ForegroundColor Gray
    Write-Host "     git log --oneline --graph HEAD..origin/main | Select-Object -First 20" -ForegroundColor Gray
    Write-Host "  2. For small syncs (<50 commits):" -ForegroundColor Gray
    Write-Host "     git merge origin/main" -ForegroundColor Gray
    Write-Host "  3. For large syncs (>50 commits):" -ForegroundColor Gray
    Write-Host "     Use worktree-based merge strategy (see docs/plans/)" -ForegroundColor Gray
    Write-Host ""
} elseif ($BEHIND -eq 0) {
    Write-Host "✓ Up to date with upstream" -ForegroundColor Green
} else {
    Write-Host "ℹ Behind upstream but within acceptable range (<50 commits)" -ForegroundColor Cyan
}

# Show recent upstream commits if behind
if ($BEHIND -gt 0 -and $BEHIND -le 10) {
    Write-Host ""
    Write-Host "Recent upstream commits:" -ForegroundColor Cyan
    git log --oneline --decorate HEAD..origin/main --max-count 10
}

exit 0
