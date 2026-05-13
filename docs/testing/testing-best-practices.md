---
title: "Testing Best Practices"
description: "Patterns and standards for testing Hermes Agent with local and remote models"
revision: 0.1.0
last_updated: 2026-05-12
---

# Testing Best Practices

This guide documents proven patterns for testing Hermes Agent, with specific guidance for local model testing.

## Core Testing Principles

### 1. Test Isolation

**Always use isolated test environments** to prevent tests from interfering with production data or each other.

```python
# Good: Uses isolated HERMES_HOME via fixture
def test_model_configuration(tmp_path, monkeypatch):
    fake_home = tmp_path / "hermes_test"
    fake_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(fake_home))
    
    # Test runs in isolated environment
    config = load_config()
    assert config is not None

# Bad: Writes to real ~/.hermes/
def test_model_configuration_bad():
    config_path = Path.home() / ".hermes" / "config.yaml"
    # This modifies real user config!
```

**Using the `_isolate_hermes_home` fixture:**

The test suite automatically isolates `HERMES_HOME` for every test:

```python
# tests/conftest.py provides this automatically
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

### 2. Avoid Live API Calls

**Never call real LLM APIs in unit tests.** Use mocks or fixtures instead.

```python
# Good: Mocked response
def test_chat_completion(monkeypatch):
    def mock_completion(*args, **kwargs):
        return {"choices": [{"message": {"content": "test response"}}]}
    
    monkeypatch.setattr("openai.ChatCompletion.create", mock_completion)
    response = agent.chat("test")
    assert response == "test response"

# Bad: Real API call (slow, flaky, costs money)
def test_chat_completion_bad():
    response = agent.chat("test")  # Calls real API!
    assert len(response) > 0
```

**For integration tests that DO need real endpoints:**

```python
# Use environment variable gating
@pytest.mark.integration
def test_real_endpoint():
    base_url = os.getenv("QWEN27B_TEST_BASE_URL")
    if not base_url:
        pytest.skip("QWEN27B_TEST_BASE_URL not set")
    
    # Test with real endpoint
    response = requests.get(f"{base_url}/models")
    assert response.status_code == 200
```

### 3. Fast Tests

**Keep unit tests fast** (<100ms per test). Slow tests discourage running them frequently.

```python
# Good: Fast unit test
def test_model_name_parsing():
    provider, model = parse_model_input("custom:qwen36_27b", "openrouter")
    assert provider == "custom"
    assert model == "qwen36_27b"

# Bad: Slow integration test disguised as unit test
def test_model_name_parsing_bad():
    # Don't actually call API to validate parsing logic!
    response = requests.get("http://localhost:8085/v1/models")
    models = response.json()["data"]
    # ... parsing test
```

**Time budget guidelines:**
- Unit tests: <100ms
- Integration tests: <5s
- E2E tests: <30s
- Benchmarks: No limit (but report duration)

### 4. Descriptive Test Names

**Use clear, descriptive test names** that explain what is being tested and expected behavior.

```python
# Good: Clear intent
def test_custom_provider_returns_context_window_from_models_endpoint():
    """Verify that context window is correctly extracted from /models response."""
    pass

def test_preflight_script_exits_nonzero_when_models_endpoint_unreachable():
    """Ensure script reports failure when /models cannot be reached."""
    pass

# Bad: Vague names
def test_provider():
    pass

def test_preflight():
    pass
```

---

## Fixtures and Test Utilities

### Using `mock_config` Fixture

```python
# Available in tests/conftest.py
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

# Usage in tests
def test_agent_initialization(mock_config):
    agent = AIAgent(**mock_config)
    assert agent.max_iterations == 10
    assert "terminal" in agent.enabled_toolsets
```

### Using `tmp_dir` Fixture

```python
# Provides a clean temporary directory for each test
def test_file_operations(tmp_dir):
    test_file = tmp_dir / "test.txt"
    test_file.write_text("content")
    
    # Test file operations
    result = read_file(str(test_file))
    assert result == "content"
    
    # tmp_dir is automatically cleaned up after test
```

### Creating Custom Fixtures

```python
# For local model testing
@pytest.fixture
def local_model_config():
    """Configuration for testing with local Qwen endpoint."""
    return {
        "model": {
            "provider": "custom",
            "model": "qwen36_27b",
            "base_url": "http://localhost:8085/v1",
            "context_window": 262144,
        }
    }

@pytest.fixture
def mock_models_response():
    """Mock response from /v1/models endpoint."""
    return {
        "data": [
            {
                "id": "qwen36_27b",
                "object": "model",
                "context_length": 262144,
            },
            {
                "id": "qwen36_27b_otq",
                "object": "model",
                "context_length": 262144,
            },
        ]
    }
```

---

## Local Model-Specific Testing

### Environment Variable Configuration

**Always use environment variables for test endpoints** to make tests runnable across different environments.

```python
# Good: Configurable via environment
BASE_URL = os.getenv("QWEN27B_TEST_BASE_URL", "").strip()
MODEL_ID = os.getenv("QWEN27B_TEST_MODEL", "qwen36_27b").strip()
API_KEY = os.getenv("QWEN27B_TEST_API_KEY", "").strip()

@pytest.fixture(scope="module", autouse=True)
def _skip_if_endpoint_unavailable():
    if not BASE_URL:
        pytest.skip("QWEN27B_TEST_BASE_URL not set")
    
    try:
        response = requests.get(f"{BASE_URL}/models", timeout=5)
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(f"Endpoint unreachable: {exc}")

# Bad: Hardcoded endpoint (breaks in CI, different dev machines)
def test_local_model_bad():
    response = requests.get("http://localhost:8085/v1/models")
    # What if port is different? What if testing remotely?
```

**Environment variable naming convention:**
- `<FEATURE>_TEST_<PARAM>` for test-specific variables
- Example: `QWEN27B_TEST_BASE_URL`, `QWEN27B_TEST_MODEL`
- Keeps test config separate from runtime config

### Graceful Test Skipping

**Skip tests gracefully when prerequisites are missing**, rather than failing.

```python
# Good: Skip with informative message
@pytest.fixture(scope="module", autouse=True)
def _check_service_availability():
    base_url = os.getenv("QWEN27B_TEST_BASE_URL")
    if not base_url:
        pytest.skip(
            "QWEN27B_TEST_BASE_URL not set; skipping local model tests. "
            "Set environment variable to run these tests."
        )
    
    try:
        response = requests.get(f"{base_url}/models", timeout=5)
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(
            f"Local model endpoint at {base_url} is unreachable: {exc}. "
            "Ensure service is running before running integration tests."
        )

# Bad: Failing test with confusing error
def test_local_model_bad():
    # This fails with ConnectionError - unclear if test or setup issue
    response = requests.get("http://localhost:8085/v1/models")
    assert response.status_code == 200
```

### Performance Assertion Strategies

**Use ranges rather than exact values** for performance tests, as latency varies.

```python
# Good: Range-based assertion
def test_completion_latency():
    start = time.time()
    response = run_completion("test prompt")
    latency = time.time() - start
    
    # Allow reasonable variance
    assert 5 < latency < 30, f"Latency {latency}s outside expected range"
    assert response is not None

# Bad: Exact timing (flaky)
def test_completion_latency_bad():
    start = time.time()
    response = run_completion("test prompt")
    latency = time.time() - start
    
    assert latency == 15.5  # Will fail on different hardware!
```

**Performance test patterns:**
```python
# Pattern 1: Baseline comparison
def test_performance_within_baseline():
    baseline_tps = 6.0  # tokens/sec from benchmark
    tolerance = 0.3  # 30% variance allowed
    
    actual_tps = measure_throughput()
    min_acceptable = baseline_tps * (1 - tolerance)
    max_acceptable = baseline_tps * (1 + tolerance)
    
    assert min_acceptable <= actual_tps <= max_acceptable, \
        f"Throughput {actual_tps} outside {min_acceptable}-{max_acceptable}"

# Pattern 2: Relative comparison
def test_no_performance_regression(benchmark_results):
    previous_latency = benchmark_results["latency_ms"]
    current_latency = measure_latency()
    
    # Allow 20% regression
    assert current_latency < previous_latency * 1.2, \
        f"Performance regression: {current_latency}ms vs {previous_latency}ms"
```

### Testing Across Model Variants

**Parameterize tests to run across multiple model variants.**

```python
@pytest.mark.parametrize("model_id", [
    "qwen36_27b",
    "qwen36_27b_otq",
    pytest.param("qwen36_27b_dflash", marks=pytest.mark.xfail(reason="Experimental")),
])
def test_model_variant_availability(model_id):
    """Verify each model variant is accessible."""
    base_url = os.getenv("QWEN27B_TEST_BASE_URL")
    response = requests.post(
        f"{base_url}/chat/completions",
        json={
            "model": model_id,
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": 10,
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
```

---

## Cross-Platform Compatibility

### Platform-Specific Imports

**Handle platform-specific modules gracefully.**

```python
# Good: Conditional import with fallback
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

@pytest.mark.skipif(not HAS_FCNTL, reason="fcntl not available on Windows")
def test_file_locking():
    # Test that requires fcntl
    pass

# Alternative: Platform check
import platform

@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Unix-specific test"
)
def test_unix_signals():
    # Test Unix signal handling
    pass
```

### Path Handling

**Always use `pathlib.Path` for cross-platform path operations.**

```python
# Good: Cross-platform paths
from pathlib import Path

def test_config_loading(tmp_dir):
    config_file = tmp_dir / "config.yaml"
    config_file.write_text("model: test")
    
    loaded = load_config(config_file)
    assert loaded["model"] == "test"

# Bad: Platform-specific path separators
def test_config_loading_bad(tmp_dir):
    config_file = f"{tmp_dir}/config.yaml"  # Fails on Windows
    # ...
```

### Profile-Safe Paths

**Never hardcode `~/.hermes` paths** - always use `get_hermes_home()`.

```python
# Good: Profile-aware
from hermes_constants import get_hermes_home

def test_config_location():
    config_path = get_hermes_home() / "config.yaml"
    assert config_path.parent.name in {".hermes", "hermes_test"}

# Bad: Hardcoded path (breaks profiles and tests)
def test_config_location_bad():
    config_path = Path.home() / ".hermes" / "config.yaml"
    # Breaks: multi-profile setups, test isolation
```

---

## Test Organization

### Directory Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast, isolated tests
│   ├── test_model_tools.py
│   └── test_config.py
├── integration/             # Tests requiring external services
│   ├── test_qwen27b_custom_endpoint.py
│   └── test_openrouter_provider.py
├── e2e/                     # End-to-end workflows
│   └── test_agent_conversation.py
└── benchmarks/              # Performance tests
    └── test_model_performance.py
```

### Test Markers

**Use pytest markers to categorize tests.**

```python
# Mark integration tests
@pytest.mark.integration
def test_api_endpoint():
    pass

# Mark slow tests
@pytest.mark.slow
def test_large_context():
    pass

# Mark tests requiring specific services
@pytest.mark.requires_local_model
def test_qwen_completion():
    pass

# Run specific categories
# pytest -m "integration"
# pytest -m "not slow"
# pytest -m "integration and requires_local_model"
```

**Register markers in `pytest.ini`:**
```ini
[pytest]
markers =
    integration: Integration tests requiring external services
    e2e: End-to-end tests
    slow: Tests that take >5 seconds
    requires_local_model: Tests requiring local LLM service
    requires_gpu: Tests requiring GPU hardware
```

---

## Mocking Strategies

### Mocking API Responses

```python
# Pattern 1: Mock requests library
def test_models_endpoint(monkeypatch):
    class MockResponse:
        status_code = 200
        def json(self):
            return {"data": [{"id": "qwen36_27b"}]}
    
    def mock_get(*args, **kwargs):
        return MockResponse()
    
    monkeypatch.setattr(requests, "get", mock_get)
    
    models = fetch_models("http://localhost:8085/v1")
    assert "qwen36_27b" in models

# Pattern 2: Mock at function level
def test_agent_chat(monkeypatch):
    def mock_completion(*args, **kwargs):
        return {"choices": [{"message": {"content": "mocked"}}]}
    
    monkeypatch.setattr(
        "agent.anthropic_adapter.create_completion",
        mock_completion
    )
    
    response = agent.chat("test")
    assert response == "mocked"
```

### Mocking File System

```python
# Use tmp_path for real filesystem operations
def test_save_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    save_config({"model": "test"}, config_file)
    
    assert config_file.exists()
    content = config_file.read_text()
    assert "model: test" in content

# Or mock for pure logic tests
def test_config_validation(monkeypatch):
    def mock_exists(path):
        return True
    
    monkeypatch.setattr(Path, "exists", mock_exists)
    
    # Test validation logic without real filesystem
```

---

## Debugging Failed Tests

### Verbose Output

```bash
# Show full output
pytest -vv -s

# Show local variables on failure
pytest --showlocals

# Drop into debugger on failure
pytest --pdb

# Show all test output (not just failures)
pytest -rA
```

### Capturing Logs

```python
# Enable logging in tests
def test_with_logging(caplog):
    import logging
    caplog.set_level(logging.DEBUG)
    
    # Test code that logs
    result = function_that_logs()
    
    # Assert on logs
    assert "expected message" in caplog.text
```

### Isolating Failures

```bash
# Run only failed tests from last run
pytest --lf

# Run failed tests first, then rest
pytest --ff

# Stop on first failure
pytest -x

# Stop after N failures
pytest --maxfail=3
```

---

## CI/CD Integration

### Fast Feedback Loop

```yaml
# .github/workflows/tests.yml
jobs:
  quick-tests:
    # Run fast unit tests on every push
    runs-on: ubuntu-latest
    steps:
      - name: Unit tests
        run: pytest tests/unit/ -v --tb=short
  
  integration-tests:
    # Run slower integration tests on PR
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - name: Integration tests
        run: pytest -m integration tests/ -v
```

### Parallel Execution

```bash
# Use pytest-xdist for parallel execution
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU count)
pytest -n auto

# Specific number of workers
pytest -n 4
```

### Coverage Reporting

```bash
# Install coverage tool
pip install pytest-cov

# Run with coverage
pytest --cov=agent --cov=model_tools --cov-report=html

# View report
open htmlcov/index.html
```

---

## Common Pitfalls

### 1. Shared State Between Tests

**Problem**: Tests pass individually but fail when run together.

```python
# Bad: Shared global state
_cache = {}

def test_a():
    _cache["key"] = "value_a"
    assert _cache["key"] == "value_a"

def test_b():
    # Fails if test_a ran first!
    assert "key" not in _cache

# Good: Isolated state
def test_a(tmp_path, monkeypatch):
    cache_file = tmp_path / "cache.json"
    monkeypatch.setenv("CACHE_FILE", str(cache_file))
    # Each test gets own cache file
```

### 2. Timing-Dependent Tests

**Problem**: Tests are flaky due to timing assumptions.

```python
# Bad: Race condition
def test_async_operation():
    start_async_task()
    time.sleep(1)  # Might not be enough!
    assert task_completed()

# Good: Poll with timeout
def test_async_operation():
    start_async_task()
    
    for _ in range(10):  # Try for 10 seconds
        if task_completed():
            break
        time.sleep(1)
    else:
        pytest.fail("Task did not complete in time")
```

### 3. Overly Broad Mocks

**Problem**: Mock too much and test becomes meaningless.

```python
# Bad: Mocking everything
def test_chat_bad(monkeypatch):
    monkeypatch.setattr(agent, "chat", lambda x: "mocked")
    result = agent.chat("test")
    assert result == "mocked"  # What did we actually test?

# Good: Mock only external dependencies
def test_chat_good(monkeypatch):
    def mock_api_call(*args, **kwargs):
        return {"content": "response"}
    
    monkeypatch.setattr("openai.ChatCompletion.create", mock_api_call)
    
    # Test actual agent logic with mocked API
    result = agent.chat("test")
    assert len(result) > 0
```

---

## Additional Resources

- **Test Suite**: [`tests/`](../../tests/)
- **Fixtures**: [`tests/conftest.py`](../../tests/conftest.py)
- **Integration Tests**: [`tests/integration/`](../../tests/integration/)
- **Contributing Guide**: [`website/docs/developer-guide/contributing.md`](../../website/docs/developer-guide/contributing.md)
- **Local Model Testing**: [`local-model-testing-guide.md`](local-model-testing-guide.md)
