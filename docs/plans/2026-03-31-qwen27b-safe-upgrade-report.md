---
file: docs/plans/2026-03-31-qwen27b-safe-upgrade-report.md
description: Execution report for Qwen 27B testing readiness and safe Hermes upgrade rehearsal.
primary_functions:
  - Records baseline git state and rollback checkpoint.
  - Defines prioritized testing/setup actions for Qwen 27B.
  - Documents a non-destructive Windows-safe upgrade rehearsal workflow.
revision: 0.1.1
last_updated: 2026-03-31
---

# Qwen 27B Testing and Safe Upgrade Report

## Prompt Summary

Review project readiness, prioritize testing with Qwen 3.5 27B, build a safe development and upgrade path, and deliver a practical report with top priority setup/testing actions.

## Baseline Snapshot (Captured 2026-03-31)

- Current commit (rollback checkpoint): `58b16c91`
- Branch state: `main...origin/main [ahead 2]`
- Divergence counts: `behind=0`, `ahead=2`
- Working tree state: no tracked file deltas shown by `git status --short --branch`

Recommended pre-upgrade safety commands:

```powershell
git tag -a qwen27b-baseline-20260331 -m "Qwen 27B baseline before safe upgrade rehearsal"
git branch backup/qwen27b-safe-upgrade-20260331
```

## Standardized Qwen 27B Runtime Contract

- Canonical model ID for Hermes custom provider testing: `qwen3.5:27b`
- Canonical provider path: `provider: custom`
- Canonical base URL shape: `http://<host>:<port>/v1`
- Compatibility note: local engine aliases such as `qwen35_27b_q4` can still be used when required by server naming, but all Hermes-oriented tests and docs should default to `qwen3.5:27b`.

## Top 8 Priority Items

1. Freeze baseline and protect rollback path before running upgrade or environment changes.
2. Standardize Qwen 27B model naming (`qwen3.5:27b`) across test tooling and config guidance.
3. Add a repeatable preflight smoke test script for endpoint, model listing, latency, and tokens/sec.
4. Add integration/e2e test coverage for custom endpoint Qwen flow with safe skip behavior.
5. Validate context-length discovery path (`/models`) and explicit overrides for Qwen endpoints.
6. Document Windows-safe workflow (WSL2 preferred, native Windows caveats explicit).
7. Rehearse upgrade using a non-destructive branch/worktree-first strategy.
8. Run prioritized targeted tests, then full suite, and gate upgrade on results.

## Windows 11 Safe Development Path

- Preferred runtime: WSL2 for parity with project support policy.
- If native Windows is used:
  - keep tests non-destructive and isolated from production `HERMES_HOME`
  - avoid force-reset upgrade flows on active branches
  - use explicit command timeouts for long-running checks
  - treat integration tests as opt-in with endpoint/env gating

## Non-Destructive Upgrade Rehearsal (PowerShell)

```powershell
# 1) Save work and refresh refs
git status --short --branch
git fetch origin

# 2) Review divergence in both directions
git log --oneline --decorate HEAD..origin/main
git log --oneline --decorate origin/main..HEAD

# 3) Rehearse in isolated worktree (recommended)
git worktree add ..\Hermes_Agent_upgrade_rehearsal origin/main
cd ..\Hermes_Agent_upgrade_rehearsal

# 4) Validate environment and tests in rehearsal tree
.\.venv\Scripts\python.exe -m pytest tests\agent -q
.\.venv\Scripts\python.exe -m pytest tests\hermes_cli -q

# 5) Return to primary tree after validation
cd ..\Hermes_Agent
```

## Verification Checklist

- Baseline checkpoint captured and rollback branch/tag commands prepared.
- Qwen 27B canonical model contract documented.
- Preflight test harness and integration test coverage added.
- Windows-safe and upgrade rehearsal path documented.
- Regression outcomes recorded after targeted and full-suite test execution.

## Implemented Assets

- `scripts/qwen27b_preflight.py`
  - Canonical default model set to `qwen3.5:27b`.
  - `/models` + `/chat/completions` checks with latency and tokens/second metrics.
  - Optional JSON report output and strict model-listing enforcement flag.
- `test_qwen.py`
  - Converted into a compatibility wrapper that delegates to the canonical preflight script.
- `tests/integration/test_qwen27b_custom_endpoint.py`
  - Added integration/e2e endpoint checks for model listing and chat completion behavior.
  - Uses safe skip guards when endpoint configuration or connectivity is missing.
- `scripts/safe_upgrade_rehearsal.py`
  - Added a read-only helper for branch/divergence snapshot and non-destructive upgrade rehearsal guidance.

## Regression Execution Results

### Targeted Validation (Pass)

- Script CLI validation:
  - `scripts/qwen27b_preflight.py --help` passed
  - `scripts/safe_upgrade_rehearsal.py --help` passed
- Targeted model tests:
  - `pytest tests/agent/test_model_metadata.py tests/hermes_cli/test_model_validation.py -q`
  - Result: `130 passed`
- Qwen integration test module:
  - `pytest -m integration tests/integration/test_qwen27b_custom_endpoint.py -q`
  - Result: `2 skipped` (no endpoint env configured in this environment)

### Full Suite Validation (Blocked)

- Command: `pytest tests/ -q`
- Outcome: `11 failed, 1675 passed, 24 skipped, 30 errors`
- Representative blockers captured:
  - ACP import errors in `tests/acp/*`
  - `tests/tools/test_search_hidden_dirs.py` repeated `FileNotFoundError` (WinError 2)
  - Gateway-related failures in Feishu/Email/Pairing tests
  - Run ended with xdist `KeyboardInterrupt` after reporting failures/errors

### Classification

- **Changes introduced in this implementation:** no failures detected in targeted tests covering modified surfaces.
- **Global suite state:** currently not release-ready on this native Windows environment due unrelated failing/erroring suites.

## Go/No-Go Recommendation

- **Go for Qwen 27B local validation path:** yes (preflight + integration harnesses are in place).
- **Go for full release upgrade merge gate:** no, hold until existing non-Qwen suite failures/errors are resolved or triaged in a controlled CI/WSL2 run.
