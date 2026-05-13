# Git Fork Workflow

This document describes the fork-based git workflow for developing custom features while staying synchronized with the upstream NousResearch/hermes-agent repository.

## Remote Structure

Our repository has two remotes configured:

- **origin**: Your personal fork (https://github.com/nicholas631/hermes-agent)
  - This is where you **push** your custom work
  - Safe place to experiment and develop features
  
- **upstream**: Official NousResearch repository (https://github.com/NousResearch/hermes-agent)
  - This is where you **pull** updates from
  - Read-only for most developers

Verify your remotes:
```powershell
git remote -v
```

Expected output:
```
origin    https://github.com/nicholas631/hermes-agent.git (fetch)
origin    https://github.com/nicholas631/hermes-agent.git (push)
upstream  https://github.com/NousResearch/hermes-agent.git (fetch)
upstream  https://github.com/NousResearch/hermes-agent.git (push)
```

## Daily Development Workflow

### Starting New Feature Work

```powershell
# Ensure main is up to date
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/my-feature-name

# Make your changes
# ... edit files ...

# Commit your work
git add .
git commit -m "feat: add my feature"

# Push to your fork
git push origin feature/my-feature-name
```

### Making Changes to Existing Code

```powershell
# Work on your branch
git checkout feature/my-feature

# Make changes and commit
git add .
git commit -m "fix: improve feature implementation"

# Push updates to your fork
git push origin feature/my-feature
```

## Weekly Upstream Sync

**Important**: Sync with upstream regularly (weekly or bi-weekly) to avoid large merge conflicts.

### Check for Upstream Changes

Use the monitoring script:
```powershell
powershell scripts/check_upstream.ps1
```

This shows how many commits you're ahead/behind upstream.

### Sync Main Branch with Upstream

```powershell
# Fetch latest from upstream
git fetch upstream

# Switch to main branch
git checkout main

# Merge upstream changes
git merge upstream/main

# If there are conflicts, resolve them, then:
git add .
git commit -m "Merge upstream changes"

# Push updated main to your fork
git push origin main
```

### Sync Feature Branch with Updated Main

After syncing main with upstream, update your feature branches:

```powershell
# Switch to your feature branch
git checkout feature/my-feature

# Merge updated main into feature branch
git merge main

# Resolve any conflicts if they occur
# Then push updated feature branch
git push origin feature/my-feature
```

## Contributing Back to Upstream (Pull Requests)

When you have a feature that's ready to contribute back to NousResearch:

1. **Ensure feature branch is up to date**:
   ```powershell
   git checkout feature/my-feature
   git merge main
   git push origin feature/my-feature
   ```

2. **Create Pull Request on GitHub**:
   - Visit https://github.com/nicholas631/hermes-agent
   - Click "Pull requests" → "New pull request"
   - Click "compare across forks"
   - Set base repository: `NousResearch/hermes-agent` base: `main`
   - Set head repository: `nicholas631/hermes-agent` compare: `feature/my-feature`
   - Fill in PR description with:
     - What the feature does
     - Why it's useful
     - How to test it
   - Submit the PR

3. **Respond to review feedback**:
   ```powershell
   # Make requested changes
   git add .
   git commit -m "fix: address review feedback"
   git push origin feature/my-feature
   ```
   
   The PR will automatically update.

## Important Git Aliases

Add helpful aliases to your git config:

```powershell
# Show all remotes clearly
git config --local alias.remotes "remote -v"

# Show sync status with both remotes
git config --local alias.sync-status "!git fetch upstream && git status"

# Quick log showing divergence
git config --local alias.diverge "log --oneline --graph --decorate HEAD..upstream/main"
```

## Safety Best Practices

### Before Major Operations

Always create safety tags before risky operations:

```powershell
# Before major upstream sync
git tag -a "pre-sync-$(Get-Date -Format yyyyMMdd)" -m "Backup before upstream sync"

# Push tags to fork for safety
git push origin --tags
```

### Rollback Procedures

If something goes wrong:

```powershell
# Option 1: Reset to a tag
git reset --hard pre-sync-20260513

# Option 2: Reset to specific commit
git log --oneline  # find the commit hash
git reset --hard <commit-hash>

# Option 3: Restore from backup branch
git checkout backup/my-backup-branch
git checkout -b recovery
```

## Custom Qwen 27B Work

Our fork contains custom Qwen 27B testing infrastructure:

- [`scripts/qwen27b_preflight.py`](../../scripts/qwen27b_preflight.py) - Endpoint testing tool
- [`scripts/safe_upgrade_rehearsal.py`](../../scripts/safe_upgrade_rehearsal.py) - Upgrade safety helper  
- [`scripts/check_upstream.ps1`](../../scripts/check_upstream.ps1) - Periodic sync monitoring
- [`tests/integration/test_qwen27b_custom_endpoint.py`](../../tests/integration/test_qwen27b_custom_endpoint.py) - Integration tests
- [`test_qwen.py`](../../test_qwen.py) - Compatibility wrapper
- [`docs/ai-change-log.md`](../ai-change-log.md) - Custom change tracking

These files are specific to our fork and won't be pushed upstream unless explicitly decided.

## Branch Naming Conventions

Use descriptive branch names:

- `feature/` - New features (e.g., `feature/qwen-27b-integration`)
- `fix/` - Bug fixes (e.g., `fix/memory-leak-in-tool`)
- `docs/` - Documentation updates (e.g., `docs/update-setup-guide`)
- `refactor/` - Code refactoring (e.g., `refactor/simplify-auth-flow`)
- `test/` - Test additions/improvements (e.g., `test/add-integration-tests`)
- `backup/` - Safety backup branches (e.g., `backup/pre-phase3-upstream-sync-20260407`)

## Common Scenarios

### Scenario 1: Accidentally Committed to Main

```powershell
# Create branch from current main
git branch feature/accidental-work

# Reset main to upstream
git checkout main
git reset --hard upstream/main

# Switch back to feature branch
git checkout feature/accidental-work

# Push feature branch
git push origin feature/accidental-work
```

### Scenario 2: Need to Undo Last Commit

```powershell
# Undo last commit but keep changes
git reset --soft HEAD~1

# Or undo last commit and discard changes
git reset --hard HEAD~1
```

### Scenario 3: Want to Test Upstream Changes Without Merging

```powershell
# Fetch upstream
git fetch upstream

# Create temporary branch from upstream/main
git checkout -b test-upstream upstream/main

# Test the changes
# ...

# Go back to your work
git checkout main

# Delete test branch if not needed
git branch -D test-upstream
```

## Troubleshooting

### "Your branch and 'origin/main' have diverged"

This is normal after syncing with upstream. Just push:
```powershell
git push origin main
```

### "fatal: refusing to merge unrelated histories"

Use the allow-unrelated-histories flag:
```powershell
git merge upstream/main --allow-unrelated-histories
```

### "Repository not found" when pushing

Verify your fork exists and remotes are correct:
```powershell
git remote -v
```

If wrong, update:
```powershell
git remote set-url origin https://github.com/nicholas631/hermes-agent.git
```

## Team Collaboration

### For Team Members Joining

If you're joining this project:

1. **Fork from nicholas631/hermes-agent** (not NousResearch) to get custom Qwen work
2. Clone your fork:
   ```powershell
   git clone https://github.com/YOUR_USERNAME/hermes-agent.git
   cd hermes-agent
   ```
3. Add both remotes:
   ```powershell
   git remote add nicholas631 https://github.com/nicholas631/hermes-agent.git
   git remote add upstream https://github.com/NousResearch/hermes-agent.git
   ```
4. Fetch all:
   ```powershell
   git fetch --all
   ```

### Syncing with Team Lead's Fork

Pull updates from nicholas631's fork:
```powershell
git fetch nicholas631
git merge nicholas631/main
```

## Resources

- **Monitor Drift**: Run `powershell scripts/check_upstream.ps1` weekly
- **Safety Backups**: All tags backed up on fork
- **Upstream Sync Plan**: See [`docs/plans/`](../plans/) for detailed upstream sync procedures
- **Change Log**: See [`docs/ai-change-log.md`](../ai-change-log.md) for history of custom changes

## Questions?

If you encounter issues not covered here, check:
1. Git status: `git status -sb`
2. Remote configuration: `git remote -v`
3. Branch tracking: `git branch -vv`
4. Recent changes: `git log --oneline -n 10 --graph --all --decorate`

---

**Last Updated**: 2026-05-13  
**Maintainer**: nicholas631
