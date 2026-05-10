---
file: docs/plans/2026-03-31-qwen27b-phase2-upgrade-plan.md
description: Phase 2 execution plan to resolve blockers and safely upgrade Hermes after Qwen 27B readiness work.
primary_functions:
  - Prioritizes next testing and setup actions from current blocker data.
  - Defines a Windows-safe and WSL2-preferred remediation workflow.
  - Specifies non-destructive upgrade sequencing with release gating.
revision: 0.1.0
last_updated: 2026-03-31
---

# Qwen 27B Phase 2 Upgrade Plan

## Prompt Summary

Complete the current Qwen 27B readiness plan and create the next plan. This plan defines the immediate follow-on work to unblock release readiness and execute a safe upgrade.

## Confirmed Current State

- Qwen 27B validation path is now in place:
  - `scripts/qwen27b_preflight.py`
  - `tests/integration/test_qwen27b_custom_endpoint.py`
  - `scripts/safe_upgrade_rehearsal.py`
- Latest remote state after fetch:
  - Branch divergence: `ahead 3`, `behind 35`
  - Upgrade is required before release.
- Full suite baseline on native Windows currently blocked:
  - `11 failed, 1675 passed, 24 skipped, 30 errors`
  - ACP import errors (`acp` module missing)
  - `fcntl` import error in memory tool tests
  - `which rg` usage causing `WinError 2` in hidden-dir tests
  - Gateway Feishu/Email/Pairing failures requiring triage

## Top 8 Next Testing and Setup Items (Priority Order)

1. **Environment parity first (WSL2 + toolchain baseline)**
   - Run the primary regression lane in WSL2 for parity with supported platform policy.
2. **Fix ACP dependency/test import lane**
   - Ensure ACP extras/dependencies are installed or tests are correctly gated when missing.
3. **Harden platform-specific imports**
   - Address `fcntl` usage for Windows by conditional import or platform-safe shim in tested paths.
4. **Make hidden-dir search tests cross-platform**
   - Replace `which rg` assumptions with cross-platform discovery (`shutil.which("rg")`).
5. **Triage gateway failures by category**
   - Separate behavior regressions vs environment differences in Feishu/Email/Pairing tests.
6. **Run Qwen endpoint integration in controlled env**
   - Execute integration lane with explicit `QWEN27B_TEST_*` variables and collect baseline metrics.
7. **Perform isolated upgrade rehearsal with worktree**
   - Rehearse merge/rebase against `origin/main` in worktree before touching primary branch.
8. **Gate final upgrade on regression thresholds**
   - Require targeted suites green and blocker-count reduction trend before final branch upgrade.

## Phase Execution Plan

## Phase A - Platform and Dependency Stabilization

- Establish two lanes:
  - **Lane 1:** native Windows smoke + targeted tests
  - **Lane 2:** WSL2 full regression lane (authoritative)
- Validate dependencies for ACP and optional tool modules in the active venv.

## Phase B - Blocker Remediation

- ACP test import blockers:
  - add dependency gating or install profile for ACP tests.
- Memory tool portability:
  - remove unconditional `fcntl` path from Windows test collection.
- Hidden-dir tests:
  - make command discovery cross-platform.
- Gateway test triage:
  - isolate deterministic failures and patch or fixture-align.

## Phase C - Upgrade Rehearsal and Integration

- Use worktree-first merge/rebase rehearsal against `origin/main`.
- Re-run targeted suites + Qwen integration lane.
- Promote changes to primary branch only when rehearsal and gates pass.

## Recommended Command Sequence (PowerShell)

```powershell
# 1) Refresh and inspect divergence
git fetch origin
git status --short --branch
git log --oneline --decorate HEAD..origin/main --max-count 25

# 2) Create isolated rehearsal tree
git worktree add ..\Hermes_Agent_phase2_rehearsal origin/main

# 3) In rehearsal tree, run targeted blocker lanes first
cd ..\Hermes_Agent_phase2_rehearsal
.\.venv\Scripts\python.exe -m pytest tests\acp -q
.\.venv\Scripts\python.exe -m pytest tests\tools\test_memory_tool.py tests\tools\test_search_hidden_dirs.py -q
.\.venv\Scripts\python.exe -m pytest tests\gateway\test_feishu.py tests\gateway\test_email.py tests\gateway\test_pairing.py -q

# 4) Run Qwen integration lane (when endpoint configured)
$env:QWEN27B_TEST_BASE_URL="http://127.0.0.1:8085/v1"
$env:QWEN27B_TEST_MODEL="qwen3.5:27b"
.\.venv\Scripts\python.exe -m pytest -m integration tests\integration\test_qwen27b_custom_endpoint.py -q

# 5) Full regression gate
.\.venv\Scripts\python.exe -m pytest tests\ -q
```

## Risk Controls

- Do not run destructive update/reset commands on the primary branch.
- Keep backup branch and baseline tag before merge/rebase execution.
- Keep Qwen endpoint integration opt-in via environment variables.
- Use WSL2 as final validation authority before release upgrade decision.

## Exit Criteria

- ACP, memory tool, hidden-dir, and gateway blocker lanes are green or explicitly waived with rationale.
- Qwen 27B preflight and integration lane pass in configured environment.
- Worktree rehearsal upgrade path is verified non-destructively.
- Full-suite failure/error counts reduced to acceptable release threshold.
