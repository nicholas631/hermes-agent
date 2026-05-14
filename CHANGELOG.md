# Hermes Agent - Change Log

This file maintains a record of all code changes made by AI assistance, including prompt summaries, change summaries, and modified files with version numbers.

---

## 2026-05-14 - Memory Monitor Deadlock Fix and Artifact Cleanup

**Prompt Summary:** Fix pipe buffer deadlock in memory monitor and remove committed development artifact containing hardcoded paths.

**Change Summary:** 
Fixed critical deadlock bug in memory monitoring subprocess that occurs when test output exceeds pipe buffer size (~64KB). When `verbose=False` (the default), the monitor created pipes for stdout/stderr but never read from them, causing the child process to block on write while the monitor waited for exit. All test commands (preflight, benchmark, pytest with `-v`) easily trigger this. Changed to always stream output directly to terminal (`stdout=None, stderr=None`) instead of buffering through pipes, eliminating the deadlock. Also removed `test_results/IMPLEMENTATION_SUMMARY.md` which was an AI-generated development artifact containing the hardcoded path `D:\Python_Projects\LLM_Local_Model_Service` that was explicitly removed from other docs, plus internal metadata like "Implementation By: AI Assistant". Added `test_results/` to `.gitignore` to prevent future test output from being tracked (only `results/` was previously added, but `run_multi_model_tests.py` outputs to `test_results/` by default).

**Files Modified:**
- `scripts/monitor_test_memory.py` (v0.1.0 → v0.1.1) - Changed `subprocess.Popen` to always use `stdout=None, stderr=None` instead of conditional `PIPE`, added explanatory comments about deadlock avoidance
- `.gitignore` (no version) - Added `test_results/` directory to development artifacts section
- `test_results/IMPLEMENTATION_SUMMARY.md` (deleted) - Removed AI-generated development artifact with hardcoded paths and internal metadata

---

## 2026-05-13 - Test Runner Timing and Environment Variable Fixes

**Prompt Summary:** Fix three critical bugs in multi-model test runner: missing end_time/duration on early returns, environment variables not passed to subprocesses, and hardcoded paths in new documentation.

**Change Summary:** 
Fixed critical bugs in the test orchestration infrastructure. The three early-return paths for aborted tests (preflight, benchmark, integration) were not setting `end_time` or `duration_seconds`, causing incorrect JSON reports and undercounting elapsed time in summary reports. The environment variables for integration tests (`LOCAL_MODEL_TEST_BASE_URL`, `LOCAL_MODEL_TEST_MODEL`) were constructed but never passed to the subprocess, causing tests to silently skip validation. Finally, the newly added testing guide reintroduced the same hardcoded developer-specific paths (`D:\Python_Projects\...`) that were intentionally removed from other documentation in this commit.

**Files Modified:**
- `scripts/run_multi_model_tests.py` (v0.1.0 → v0.1.1) - Added `end_time`/`duration_seconds` calculation to all three early-return abort paths, added optional `env` parameter to `run_test_with_monitoring()`, passed `env` to subprocess.run(), passed constructed `env` dict to integration test monitoring call
- `docs/testing/local-model-service-testing-guide.md` (v0.1.0 → v0.1.1) - Replaced six instances of hardcoded paths (`D:\Python_Projects\LLM_Local_Model_Service` and `D:\Python_Projects\Hermes_Agent`) with generic placeholders (`<path-to-your-llm-service>`, `<path-to-hermes-agent>`) and descriptive text

---

## 2026-05-13 - Critical Test Security and .gitignore Fixes

**Prompt Summary:** Fix three critical bugs: unsafe eval() usage in streaming test, silently failing test assertions, and missing .gitignore entries for development artifacts.

**Change Summary:** 
Fixed severe security and testing issues in the integration test suite. The streaming test was using `eval(data_str)` to parse SSE JSON chunks, which would execute arbitrary code from HTTP responses and fail on valid JSON due to Python vs JSON syntax differences (true/false vs True/False). Additionally, a lambda signature bug caused `TypeError` on every chunk parse, silently caught by bare `except Exception`, making all streaming assertions vacuously pass without validation. Also added missing `.gitignore` entries for `results/` (ephemeral test output) and `.cursor/` (IDE plan files) to prevent committing local development artifacts.

**Files Modified:**
- `tests/integration/test_local_model_service.py` (v0.1.0 → v0.1.1) - Replaced `eval()` with `json.loads()` for SSE chunk parsing, removed broken lambda/mock pattern, added proper `json` import, changed to specific `json.JSONDecodeError` exception handling
- `.gitignore` (no version) - Added `results/` and `.cursor/` directories to prevent committing development artifacts

---

## 2026-05-13 - Documentation Path Hardcoding Fix

**Prompt Summary:** Remove hardcoded developer-specific paths from documentation files that referenced `d:\Python_Projects\LLM_Local_Model_Service`.

**Change Summary:** 
Removed all hardcoded references to a developer's personal local path (`d:\Python_Projects\LLM_Local_Model_Service`) from documentation. These paths were meaningless for other contributors and exposed internal development setup details in public-facing documentation. Command examples now use generic placeholders (`<path-to-your-llm-service>`), and external resource links that pointed to non-existent project files were removed.

**Files Modified:**
- `docs/developer-guide/local-development-workflow.md` (v0.1.0 → v0.1.1) - Replaced hardcoded path with generic placeholder in PowerShell commands
- `website/docs/guides/troubleshooting-local-models.md` (v1.0.0 → v1.0.1) - Replaced hardcoded path with generic placeholder in troubleshooting steps
- `website/docs/guides/local-llm-setup-qwen.md` (v1.0.0 → v1.0.1) - Removed external resource link with hardcoded path
- `docs/testing/testing-scenarios.md` (v0.1.0 → v0.1.1) - Removed external resource link with hardcoded path
- `docs/testing/local-model-testing-guide.md` (v0.1.0 → v0.1.1) - Removed external resource link with hardcoded path

---
