---
file: docs/ai-change-log.md
description: Running log of AI-authored code and documentation changes.
primary_functions:
  - Records prompt summaries and implementation outcomes.
  - Tracks touched files with revision numbers.
revision: 0.1.4
last_updated: 2026-05-09
---

# AI Change Log

## 2026-05-09 - Qwen Preflight Error Reporting and Exit Code Fixes

### Prompt Summary

Fix error message loss when both preflight endpoints fail, and add missing exit code check for `/models` endpoint failures.

### Change Summary

Fixed two bugs in the Qwen 27B preflight script: (1) Changed error assignment logic from short-circuit `or` to explicit conditional that preserves both error messages when both endpoints fail, providing complete diagnostic context. (2) Added exit code check for `models_endpoint_ok` so the script properly fails (returns non-zero) when the `/models` endpoint is unreachable, making it a reliable readiness gate.

### Files Modified

- `scripts/qwen27b_preflight.py` (revision `0.1.1`)
- `docs/ai-change-log.md` (revision `0.1.4`)

## 2026-05-09 - Repository Cleanup (Personal Artifacts Removal)

### Prompt Summary

Verify and remove personal utility scripts with hardcoded drive paths and accidental diagnostic artifacts from the repository.

### Change Summary

Removed three accidentally committed personal files: two model download scripts with hardcoded `K:\` drive paths (`download_hermes36b.py`, `download_nemotron.py`) and an empty diagnostic output file (`doctor_output.txt`). These files had no project relevance and would fail on any machine without the specific local drive configuration.

### Files Modified

- `download_hermes36b.py` (deleted - personal utility with hardcoded `K:\models\hermes_4_3_36b`)
- `download_nemotron.py` (deleted - personal utility with hardcoded `K:\models\nemotron_cascade`)
- `doctor_output.txt` (deleted - empty diagnostic artifact)
- `docs/ai-change-log.md` (revision `0.1.3`)

## 2026-03-31 - Qwen 27B Testing and Safe Upgrade Path

### Prompt Summary (Phase 2)

Implement the attached Qwen 27B testing and safe upgrade plan end-to-end, keep todos updated as work progresses, and deliver a concrete report with prioritized setup/testing guidance.

### Change Summary (Phase 2)

Added a Qwen 27B preflight harness, integration/e2e coverage with safe skip behavior, and a non-destructive upgrade rehearsal helper, then executed targeted and full-suite regression gates with blocker classification in the rollout report.

### Files Modified (Phase 2)

- `docs/plans/2026-03-31-qwen27b-safe-upgrade-report.md` (revision `0.1.1`)
- `scripts/qwen27b_preflight.py` (revision `0.1.0`)
- `test_qwen.py` (revision `0.1.0`)
- `tests/integration/test_qwen27b_custom_endpoint.py` (revision `0.1.0`)
- `scripts/safe_upgrade_rehearsal.py` (revision `0.1.0`)
- `docs/ai-change-log.md` (revision `0.1.1`)

## 2026-03-31 - Plan Completion and Phase 2

### Prompt Summary (max 2 sentences)

Complete the current Qwen 27B plan/report and create the next plan. Keep the existing plan artifacts intact while defining the next prioritized execution path.

### Change Summary

Marked the current Qwen 27B report as completed and created a new Phase 2 plan focused on blocker remediation, WSL2 parity testing, and a safe non-destructive upgrade path from the current behind/ahead divergence.

### Files Modified

- `docs/plans/2026-03-31-qwen27b-safe-upgrade-report.md` (revision `0.1.2`)
- `docs/plans/2026-03-31-qwen27b-phase2-upgrade-plan.md` (revision `0.1.0`)
- `docs/ai-change-log.md` (revision `0.1.2`)
