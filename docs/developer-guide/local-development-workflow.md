---
title: "Local Development Workflow"
description: "Developer onboarding guide for testing and developing Hermes Agent with local models"
revision: 0.1.1
last_updated: 2026-05-13
---

# Local Development Workflow

This guide covers the complete workflow for developing and testing Hermes Agent with local LLM endpoints.

## Development Environment Setup

### Prerequisites

| Requirement | Version | Installation |
|-------------|---------|--------------|
| **Python** | 3.11+ | `uv python install 3.11` |
| **uv** | Latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Git** | Any | System package manager |
| **Node.js** | 18+ | Optional, for browser tools |

### Initial Setup

```powershell
# 1. Clone repository
git clone --recurse-submodules https://github.com/NousResearch/hermes-agent.git
cd hermes-agent

# 2. Create virtual environment
uv venv venv --python 3.11
.\.venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/macOS

# 3. Install in editable mode with all extras
uv pip install -e ".[all,dev]"
uv pip install -e "./tinker-atropos"

# 4. Optional: Install browser tools
npm install
```

### Configure Development Environment

```powershell
# 1. Create Hermes directories
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.hermes\cron"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.hermes\sessions"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.hermes\logs"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.hermes\memories"
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.hermes\skills"

# 2. Create config file (if not exists)
if (-not (Test-Path "$env:USERPROFILE\.hermes\config.yaml")) {
    Copy-Item "cli-config.yaml.example" "$env:USERPROFILE\.hermes\config.yaml"
}

# 3. Create .env file for API keys
New-Item -ItemType File -Force -Path "$env:USERPROFILE\.hermes\.env"
```

### Configure Local Model Endpoint

```powershell
# Option 1: Using Hermes CLI
hermes config set model.provider custom
hermes config set model.base_url http://localhost:8085/v1
hermes config set model.model qwen36_27b

# Option 2: Edit config.yaml directly
# ~/.hermes/config.yaml
```

Add to `~/.hermes/config.yaml`:
```yaml
model:
  provider: custom
  model: qwen36_27b
  base_url: http://localhost:8085/v1
  context_window: 262144  # Auto-detected if omitted
```

### Verify Installation

```powershell
# 1. Check Hermes command is available
hermes --version

# 2. Run doctor to check setup
hermes doctor

# 3. Test configuration
hermes config list

# 4. Verify local model endpoint (if running)
python scripts\qwen27b_preflight.py
```

---

## Testing Your Changes

### Understanding the Test Suite

Hermes has 554+ tests organized by purpose:

```
tests/
├── conftest.py              # Shared fixtures (MUST READ)
├── agent/                   # Agent core tests
│   ├── test_model_metadata.py
│   └── test_prompt_builder.py
├── hermes_cli/             # CLI tests
│   ├── test_config.py
│   └── test_models.py
├── tools/                  # Tool implementation tests
│   ├── test_terminal_tool.py
│   └── test_file_tools.py
├── gateway/                # Messaging platform tests
│   ├── test_telegram.py
│   └── test_discord.py
├── integration/            # Integration tests (require services)
│   └── test_qwen27b_custom_endpoint.py
└── e2e/                    # End-to-end tests
    └── test_agent_conversation.py
```

### Key Testing Fixtures

#### `_isolate_hermes_home` (Autouse)

**Automatically isolates HERMES_HOME** for every test:

```python
# tests/conftest.py
@pytest.fixture(autouse=True)
def _isolate_hermes_home(tmp_path, monkeypatch):
    """Redirect HERMES_HOME to a temp dir so tests never write to ~/.hermes/."""
    fake_home = tmp_path / "hermes_test"
    fake_home.mkdir()
    (fake_home / "sessions").mkdir()
    (fake_home / "cron").mkdir()
    (fake_home / "memories").mkdir()
    (fake_home / "skills").mkdir()
    monkeypatch.setenv("HERMES_HOME", str(fake_home))
```

**Usage in your tests:**
```python
# No import needed - automatically applied to all tests
def test_my_feature():
    # This test runs in isolated HERMES_HOME
    config = load_config()  # Loads from temp dir, not ~/.hermes
    assert config is not None
```

#### `mock_config` Fixture

**Provides consistent test configuration:**

```python
@pytest.fixture()
def mock_config():
    """Return a minimal hermes config dict suitable for unit tests."""
    return {
        "model": "test/mock-model",
        "toolsets": ["terminal", "file"],
        "max_turns": 10,
        "terminal": {"backend": "local", "cwd": "/tmp", "timeout": 30},
        "compression": {"enabled": False},
        "memory": {"memory_enabled": False, "user_profile_enabled": False},
        "command_allowlist": [],
    }

# Usage
def test_agent_init(mock_config):
    agent = AIAgent(**mock_config)
    assert agent.max_iterations == 10
```

#### `tmp_dir` Fixture

**Temporary directory for file operations:**

```python
def test_file_operations(tmp_dir):
    test_file = tmp_dir / "test.txt"
    test_file.write_text("content")
    
    # Test your file operation
    result = process_file(str(test_file))
    assert result == "expected"
    
    # tmp_dir cleaned up automatically
```

### Running Tests

```powershell
# Activate virtual environment first!
.\.venv\Scripts\activate

# Run all unit tests (fast)
pytest tests/ -q

# Run specific test file
pytest tests\agent\test_model_metadata.py -v

# Run specific test function
pytest tests\agent\test_model_metadata.py::test_model_context_detection -v

# Run with coverage
pytest tests\ --cov=agent --cov=model_tools --cov-report=html

# Run integration tests (requires services)
$env:QWEN27B_TEST_BASE_URL="http://localhost:8085/v1"
pytest -m integration tests\integration\ -v

# Run tests in parallel (faster)
pytest tests\ -n auto

# Run only failed tests from last run
pytest --lf

# Stop on first failure
pytest -x
```

### Mocking Model Responses

**Pattern 1: Mock at API level**

```python
def test_chat_with_mocked_api(monkeypatch):
    """Test agent behavior with mocked model response."""
    
    def mock_completion(*args, **kwargs):
        return {
            "choices": [
                {
                    "message": {
                        "content": "Mocked response",
                        "role": "assistant",
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }
    
    monkeypatch.setattr(
        "openai.ChatCompletion.create",
        mock_completion
    )
    
    agent = AIAgent(model="test/mock-model")
    response = agent.chat("test prompt")
    
    assert response == "Mocked response"
```

**Pattern 2: Mock HTTP requests**

```python
def test_custom_provider_call(monkeypatch):
    """Test custom provider with mocked HTTP."""
    
    class MockResponse:
        status_code = 200
        def json(self):
            return {
                "choices": [{"message": {"content": "test"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
    
    def mock_post(*args, **kwargs):
        return MockResponse()
    
    monkeypatch.setattr(requests, "post", mock_post)
    
    # Test code that uses requests.post
    result = call_custom_model("http://localhost:8085/v1", "test")
    assert result["choices"][0]["message"]["content"] == "test"
```

---

## Local Model Development Loop

### Complete Development Cycle

```powershell
# 1. Start local LLM service (separate terminal)
cd <path-to-your-llm-service>
.\start-service.ps1

# 2. Configure Hermes for local model
hermes config set model.provider custom
hermes config set model.base_url http://localhost:8085/v1
hermes config set model.model qwen36_27b

# 3. Run preflight checks
python scripts\qwen27b_preflight.py

# 4. Manual testing (interactive)
hermes chat -q "Write a hello world function in Python"

# 5. Verify tool calling works
hermes chat -q "What files are in the current directory?"

# 6. Run automated tests
$env:QWEN27B_TEST_BASE_URL="http://localhost:8085/v1"
$env:QWEN27B_TEST_MODEL="qwen36_27b"
pytest tests\integration\test_qwen27b_custom_endpoint.py -v

# 7. Run benchmarks (optional)
python scripts\benchmark_local_model.py --output benchmark.json

# 8. Review results
cat benchmark.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Quick Iteration Workflow

For rapid testing during development:

```powershell
# Watch mode - re-run tests on file changes
pytest-watch tests\agent\test_model_metadata.py

# Or use a simple loop
while ($true) {
    cls
    pytest tests\agent\test_model_metadata.py -v --tb=short
    Start-Sleep -Seconds 2
}
```

### Debugging Tests

```powershell
# Run with verbose output and show print statements
pytest tests\agent\test_model_metadata.py -vv -s

# Show local variables on failure
pytest tests\agent\test_model_metadata.py --showlocals

# Drop into debugger on failure
pytest tests\agent\test_model_metadata.py --pdb

# Enable debug logging
$env:HERMES_LOG_LEVEL="DEBUG"
pytest tests\agent\test_model_metadata.py -v
```

---

## Common Development Patterns

### Custom Provider Implementation

Based on [`agent/models_dev.py`](../../agent/models_dev.py):

```python
# 1. Add provider mapping
PROVIDER_TO_MODELS_DEV: Dict[str, str] = {
    # ... existing providers ...
    "my-provider": "my-provider-models-dev-id",
}

# 2. Add to provider models list
_PROVIDER_MODELS = {
    "my-provider": [
        "model-1",
        "model-2",
    ],
}

# 3. Add authentication handling (if needed)
def resolve_my_provider_credentials():
    api_key = os.getenv("MY_PROVIDER_API_KEY")
    base_url = os.getenv("MY_PROVIDER_BASE_URL", "https://api.myprovider.com/v1")
    return {"api_key": api_key, "base_url": base_url}
```

### Tool Testing with Local Models

```python
@pytest.mark.integration
def test_terminal_tool_with_local_model():
    """Test terminal tool execution with local LLM."""
    
    base_url = os.getenv("QWEN27B_TEST_BASE_URL")
    if not base_url:
        pytest.skip("QWEN27B_TEST_BASE_URL not set")
    
    # Configure agent with local model
    agent = AIAgent(
        model="qwen36_27b",
        provider="custom",
        base_url=base_url,
        enabled_toolsets=["terminal"],
    )
    
    # Test tool invocation
    response = agent.chat("List files in the current directory")
    
    # Verify agent used terminal tool
    assert "terminal" in str(agent.last_tool_calls).lower()
    assert response is not None
```

### Performance Profiling

```python
import cProfile
import pstats

def profile_model_call():
    """Profile a single model completion call."""
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Code to profile
    agent = AIAgent(model="qwen36_27b", provider="custom")
    agent.chat("Explain binary search")
    
    profiler.disable()
    
    # Print stats
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions

# Run profiler
profile_model_call()
```

---

## Development Best Practices

### 1. Always Activate Virtual Environment

```powershell
# Before any development work
.\.venv\Scripts\activate

# Verify correct Python
python --version  # Should show 3.11+
which python      # Should point to venv
```

### 2. Keep Tests Fast

- **Unit tests**: <100ms each
- **Integration tests**: <5s each
- **E2E tests**: <30s each

If tests are slow, consider:
- Mocking expensive operations
- Reducing iteration counts
- Using smaller test data
- Marking slow tests with `@pytest.mark.slow`

### 3. Write Tests First

```python
# 1. Write failing test
def test_new_feature():
    result = new_feature("input")
    assert result == "expected"

# 2. Run test (should fail)
# pytest tests\test_my_feature.py::test_new_feature -v

# 3. Implement feature
def new_feature(input_data):
    return "expected"

# 4. Run test (should pass)
# pytest tests\test_my_feature.py::test_new_feature -v
```

### 4. Use Type Hints

```python
from typing import Optional, Dict, List, Any

def process_model_response(
    response: Dict[str, Any],
    model: str,
    provider: Optional[str] = None,
) -> List[str]:
    """Process model response and extract messages."""
    choices = response.get("choices", [])
    return [c.get("message", {}).get("content", "") for c in choices]
```

### 5. Follow Project Style

```python
# Good: Clear function names, type hints, docstrings
def extract_context_window(
    model_data: Dict[str, Any]
) -> Optional[int]:
    """Extract context window size from model metadata.
    
    Args:
        model_data: Model metadata from /models endpoint
        
    Returns:
        Context window size in tokens, or None if not found
    """
    limit = model_data.get("limit", {})
    return limit.get("context") if isinstance(limit, dict) else None

# Bad: Unclear names, no types, no docstring
def get_ctx(d):
    return d.get("limit", {}).get("context")
```

---

## Troubleshooting Development Issues

### Test Failures

**Issue**: Tests pass individually but fail when run together

**Cause**: Shared state between tests

**Solution**: Ensure test isolation
```python
# Use fixtures to create fresh state
def test_a(tmp_path):
    state_file = tmp_path / "state.json"
    # Each test gets own file

# Or reset global state
@pytest.fixture(autouse=True)
def reset_cache():
    global _cache
    _cache = {}
    yield
    _cache = {}
```

**Issue**: Import errors when running tests

**Cause**: Project root not in Python path

**Solution**:
```powershell
# Ensure you're in project root
cd d:\Python_Projects\Hermes_Agent

# Activate venv
.\.venv\Scripts\activate

# Install in editable mode
uv pip install -e .
```

### Local Model Connection Issues

**Issue**: `Connection refused` when running tests

**Diagnosis**:
```powershell
# Check if service is running
curl http://localhost:8085/v1/health

# Check listening ports
Get-NetTCPConnection -LocalPort 8085

# Check environment variables
$env:QWEN27B_TEST_BASE_URL
```

**Solutions**:
1. Start local LLM service
2. Verify base URL is correct
3. Check firewall settings
4. Ensure tests skip gracefully if service unavailable

### Performance Issues

**Issue**: Tests are very slow

**Diagnosis**:
```powershell
# Profile test execution
pytest tests\ --durations=10

# Identify slow tests
pytest tests\ -v | Select-String "PASSED.*s]"
```

**Solutions**:
1. Mock expensive operations (API calls, file I/O)
2. Use `@pytest.mark.slow` for known slow tests
3. Run unit tests separately from integration tests
4. Enable parallel execution: `pytest -n auto`

---

## CI/CD Integration

### Local CI Simulation

```powershell
# Simulate CI environment locally
$env:CI = "true"
$env:QWEN27B_TEST_BASE_URL = ""  # Disable integration tests
$env:OPENROUTER_API_KEY = ""     # Prevent live API calls

# Run test suite as CI would
pytest tests\ -q --ignore=tests\integration --ignore=tests\e2e --tb=short -n auto
```

### Pre-commit Checks

Create `.git\hooks\pre-commit` (Git Bash on Windows):
```bash
#!/bin/bash
echo "Running pre-commit checks..."

# Run unit tests
pytest tests/unit/ -q --tb=short
if [ $? -ne 0 ]; then
    echo "Unit tests failed. Commit aborted."
    exit 1
fi

# Run linter (if configured)
# ruff check .

echo "Pre-commit checks passed!"
```

---

## Additional Resources

- **Test Suite**: [`tests/`](../../tests/)
- **Test Fixtures**: [`tests/conftest.py`](../../tests/conftest.py)
- **Testing Best Practices**: [`docs/testing/testing-best-practices.md`](../testing/testing-best-practices.md)
- **Local Model Testing**: [`docs/testing/local-model-testing-guide.md`](../testing/local-model-testing-guide.md)
- **Contributing Guide**: [`website/docs/developer-guide/contributing.md`](../../website/docs/developer-guide/contributing.md)
- **Integration Tests**: [`tests/integration/test_qwen27b_custom_endpoint.py`](../../tests/integration/test_qwen27b_custom_endpoint.py)

---

## Quick Reference

### Essential Commands

```powershell
# Development
.\.venv\Scripts\activate              # Activate venv
hermes config list                    # Show config
hermes config set model.provider custom
python scripts\qwen27b_preflight.py   # Test endpoint

# Testing
pytest tests\ -q                      # All tests (quiet)
pytest tests\agent\ -v                # Agent tests (verbose)
pytest -m integration tests\ -v       # Integration only
pytest --lf                           # Re-run last failures
pytest -x                             # Stop on first failure

# Debugging
pytest -vv -s tests\test_file.py      # Verbose with output
pytest --pdb tests\test_file.py       # Debug on failure
$env:HERMES_LOG_LEVEL="DEBUG"        # Enable debug logs

# Benchmarking
python scripts\benchmark_local_model.py --quick
python scripts\benchmark_local_model.py --output results.json
```

### Key Files to Know

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Shared test fixtures |
| `agent/models_dev.py` | Model/provider registry |
| `hermes_cli/models.py` | Model catalog and validation |
| `model_tools.py` | Tool orchestration |
| `run_agent.py` | Core agent loop |
| `scripts/qwen27b_preflight.py` | Endpoint validation |

### Environment Variables

```powershell
# Development
$env:HERMES_HOME = "C:\Users\YOU\.hermes"
$env:HERMES_LOG_LEVEL = "DEBUG"

# Testing
$env:QWEN27B_TEST_BASE_URL = "http://localhost:8085/v1"
$env:QWEN27B_TEST_MODEL = "qwen36_27b"
$env:CI = "true"  # Simulate CI environment
```
