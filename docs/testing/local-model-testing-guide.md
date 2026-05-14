---
title: "Local Model Testing Guide"
description: "Comprehensive guide for testing Hermes Agent with local LLM endpoints"
revision: 0.1.1
last_updated: 2026-05-13
---

# Testing Hermes with Local Models

This guide covers end-to-end testing of Hermes Agent with local LLM services, including configuration, validation, and performance benchmarking.

## Quick Start

### 1. Configure Custom Provider Endpoint

```bash
# Option 1: Interactive configuration
hermes model
# Select: Custom endpoint
# Enter base URL: http://localhost:8085/v1
# Enter model: qwen36_27b

# Option 2: Direct configuration
hermes config set model.provider custom
hermes config set model.base_url http://localhost:8085/v1
hermes config set model.model qwen36_27b
```

### 2. Run Preflight Validation

```bash
# Basic preflight check
python scripts/qwen27b_preflight.py

# With JSON output for CI/automation
python scripts/qwen27b_preflight.py --json-out preflight-report.json

# Test specific model
python scripts/qwen27b_preflight.py --model qwen36_27b_otq
```

### 3. Execute Integration Test Suite

```bash
# Set test environment variables
export QWEN27B_TEST_BASE_URL="http://localhost:8085/v1"
export QWEN27B_TEST_MODEL="qwen36_27b"

# Run integration tests
pytest tests/integration/test_qwen27b_custom_endpoint.py -v

# Run with markers
pytest -m integration tests/integration/test_qwen27b_custom_endpoint.py -v
```

### 4. Benchmark Performance

```bash
# Run comprehensive benchmark
python scripts/benchmark_local_model.py \
  --base-url http://localhost:8085/v1 \
  --model qwen36_27b \
  --output benchmark-results.json

# Quick benchmark (basic metrics only)
python scripts/benchmark_local_model.py --quick
```

---

## Test Categories

### Preflight Checks

**Purpose**: Validate endpoint connectivity and model availability before running full tests.

**What it checks:**
- `/models` endpoint is reachable
- Target model is listed in available models
- Basic chat completion works
- Token usage metrics are returned
- Response latency is reasonable

**When to run:**
- After configuring a new local model endpoint
- Before running integration or e2e tests
- As part of CI/CD pipelines
- When troubleshooting connectivity issues

**Expected results:**
```
Qwen 27B preflight report
============================================================
Base URL:              http://localhost:8085/v1
Model:                 qwen36_27b
/models reachable:     True
Model listed:          True
Models returned:       3
Detected context:      262144
/chat completion ok:   True
Prompt tokens:         18
Completion tokens:     96
Total tokens:          114
Latency (ms):          15234.5
Tokens / second:       6.3
Response preview:      Deterministic test harnesses improve model...
```

### Integration Tests

**Purpose**: Validate that Hermes Agent can successfully interact with local models through the custom provider interface.

**Test coverage:**
- Model listing and discovery
- Chat completion requests
- Tool calling with local models
- Context window handling
- Error handling and retries
- Token usage tracking

**Running integration tests:**
```bash
# All integration tests
pytest -m integration tests/integration/ -v

# Qwen-specific tests
pytest tests/integration/test_qwen27b_custom_endpoint.py -v

# With coverage
pytest -m integration tests/integration/ --cov=agent --cov=model_tools -v
```

**Expected behavior:**
- Tests skip gracefully if endpoint is not configured
- Tests fail fast if endpoint is unreachable
- Token metrics are validated when available
- Responses contain expected structure

### Performance Benchmarks

**Purpose**: Measure and track performance characteristics of local models over time.

**Metrics captured:**
- Time to first token (TTFT)
- Tokens per second (throughput)
- Context length vs. latency curves
- Tool invocation round-trip time
- Memory usage profile
- Model load time (cold start)

**Benchmark scenarios:**
1. **Simple Completion**: Basic chat completion with minimal context
2. **Tool Calling**: Multi-turn conversation with tool invocations
3. **Long Context**: Stress test with 50k+ token contexts
4. **Multi-turn**: Sustained conversation with history accumulation

**Interpreting results:**

For Qwen 3.6 27B (Q4_K_M), expected baseline:
```
Load Time:        22.6 seconds (first request)
VRAM Usage:       13.2 GB
Tokens/Second:    ~6 tokens/sec
Context Window:   262,144 tokens
Max Tested:       50,000 tokens
```

Performance degradation patterns:
- **>20s latency for simple completion**: Model may be loading or VRAM constrained
- **<3 tokens/sec throughput**: Check for GPU throttling or quantization issues
- **Increasing latency with context**: Normal up to 100k tokens; investigate if severe
- **OOM errors**: Context exceeds model capacity or VRAM limit reached

### Capability Validation

**Purpose**: Verify that specific model capabilities work correctly with Hermes.

**Test areas:**
1. **Code Generation**: Generate functional code snippets
2. **Code Explanation**: Accurately describe code logic
3. **Tool Usage**: Correctly invoke and interpret tool results
4. **Multi-step Reasoning**: Chain multiple operations together
5. **Context Retention**: Reference earlier conversation turns

**Example validation workflow:**
```python
# Test code generation capability
prompt = """
Create a Python function that calculates fibonacci numbers
using dynamic programming. Include docstring and type hints.
"""

response = hermes_chat(prompt)
# Validate: response contains valid Python code
# Validate: code includes type hints
# Validate: docstring is present
```

---

## Test Execution Workflow

### Development Testing (Local)

```bash
# 1. Start local LLM service
# (Run in separate terminal)
cd ~/llm-service
./start-qwen-service.sh

# 2. Configure Hermes
hermes config set model.provider custom
hermes config set model.base_url http://localhost:8085/v1
hermes config set model.model qwen36_27b

# 3. Run preflight
python scripts/qwen27b_preflight.py

# 4. Manual validation
hermes chat -q "Write a hello world function in Python"

# 5. Automated tests
pytest tests/integration/test_qwen27b_custom_endpoint.py -v

# 6. Benchmarks (optional)
python scripts/benchmark_local_model.py
```

### CI/CD Testing

```bash
# In CI pipeline (GitHub Actions, GitLab CI, etc.)

# 1. Start mock LLM service (or skip if using remote)
docker run -d -p 8085:8085 mock-llm-service

# 2. Wait for service readiness
./scripts/wait-for-service.sh http://localhost:8085/v1/health

# 3. Run preflight with strict validation
python scripts/qwen27b_preflight.py \
  --require-model-listed \
  --json-out preflight.json

# 4. Run integration tests
export QWEN27B_TEST_BASE_URL="http://localhost:8085/v1"
export QWEN27B_TEST_MODEL="qwen36_27b"
pytest -m integration tests/integration/ -v --tb=short

# 5. Archive results
mv preflight.json $CI_ARTIFACTS_DIR/
```

### Regression Testing

**When to run:**
- Before merging changes to custom provider code
- After upgrading Hermes version
- When testing new local model versions
- Before production deployments

**Full regression suite:**
```bash
# 1. Unit tests (fast)
pytest tests/agent/test_model_metadata.py -v
pytest tests/hermes_cli/test_model_validation.py -v

# 2. Integration tests (requires endpoint)
export QWEN27B_TEST_BASE_URL="http://localhost:8085/v1"
pytest -m integration tests/integration/ -v

# 3. E2E tests (full stack)
pytest tests/e2e/ -v --tb=short

# 4. Performance validation
python scripts/benchmark_local_model.py --output baseline.json
```

---

## Configuration Templates

### Basic Custom Endpoint

```yaml
# ~/.hermes/config.yaml
model:
  provider: custom
  model: qwen36_27b
  base_url: http://localhost:8085/v1
  context_window: 262144  # Optional: auto-detected from /models
  max_output_tokens: 8192  # Optional: model default
```

### Custom Endpoint with Authentication

```yaml
# ~/.hermes/config.yaml
model:
  provider: custom
  model: qwen36_27b
  base_url: http://localhost:8085/v1

# ~/.hermes/.env
CUSTOM_API_KEY=your-api-key-here
```

### Multiple Model Profiles

```yaml
# Profile: local-qwen
model:
  provider: custom
  model: qwen36_27b
  base_url: http://localhost:8085/v1

# Switch profiles
# hermes -p local-qwen
```

---

## Expected Performance Baselines

### Qwen 3.6 27B (Q4_K_M)

Based on testing with RTX 3090 (24GB VRAM):

| Metric | Value | Notes |
|--------|-------|-------|
| **Load Time** | 22.6s | First request after service start |
| **VRAM Usage** | 13.2 GB | Steady state during inference |
| **Inference Speed** | ~6 tokens/sec | Average across 96-token completions |
| **Max Context** | 262,144 tokens | ~200k words |
| **Tested Context** | 50,000 tokens | Stable performance |
| **Model Size** | ~14 GB | Quantized (Q4_K_M) |

### Performance by Context Length

| Context Size | Latency | Throughput | Notes |
|--------------|---------|------------|-------|
| <1k tokens | ~15s | 6-7 tok/s | Optimal |
| 1k-10k tokens | ~20s | 5-6 tok/s | Normal |
| 10k-50k tokens | ~30s | 4-5 tok/s | Expected degradation |
| 50k-100k tokens | ~60s | 3-4 tok/s | Noticeable slowdown |
| 100k+ tokens | Varies | 2-3 tok/s | Use with caution |

---

## Troubleshooting Common Issues

### Service Not Reachable

**Symptom**: `Connection refused` or timeout errors

**Diagnosis:**
```bash
# Check if service is running
curl http://localhost:8085/v1/health

# Check listening ports
netstat -tuln | grep 8085  # Linux
Get-NetTCPConnection -LocalPort 8085  # Windows PowerShell
```

**Solutions:**
- Ensure LLM service is started
- Verify port 8085 is not blocked by firewall
- Check service logs for startup errors
- Confirm base URL includes `/v1` suffix

### Model Not Listed

**Symptom**: `Model listed: False` in preflight report

**Diagnosis:**
```bash
# Check available models
curl http://localhost:8085/v1/models | jq '.data[].id'

# Expected output:
# qwen36_27b
# qwen36_27b_otq
# qwen36_27b_dflash
```

**Solutions:**
- Verify model name matches exactly (case-sensitive)
- Check if model is properly loaded in service
- Use `--require-model-listed` flag to enforce strict validation
- Consult LLM service logs for model loading errors

### Slow Performance

**Symptom**: Tokens/second significantly below baseline

**Diagnosis:**
```bash
# Check VRAM usage
nvidia-smi  # Should show ~13GB for Qwen 3.6 27B

# Monitor GPU utilization
watch -n 1 nvidia-smi

# Profile a request
time python scripts/qwen27b_preflight.py
```

**Common causes:**
- **GPU throttling**: Check temperature and power limits
- **Model still loading**: Wait 30s after first request
- **Concurrent requests**: Ensure sequential testing
- **Incorrect quantization**: Verify Q4_K_M is loaded

### Context Window Errors

**Symptom**: Request fails with context length exceeded

**Diagnosis:**
- Check configured context window in Hermes config
- Verify model's actual context limit from `/models` endpoint
- Count tokens in your prompt (use token counter tool)

**Solutions:**
```yaml
# Explicitly set context window
model:
  context_window: 262144  # For Qwen 3.6 27B

# Or let Hermes auto-detect
# (Remove context_window key from config)
```

---

## Integration with Development Workflow

### Pre-commit Testing

```bash
# .git/hooks/pre-commit (if testing local model changes)
#!/bin/bash
if [[ -f scripts/qwen27b_preflight.py ]]; then
  echo "Running local model preflight..."
  python scripts/qwen27b_preflight.py --timeout 30
  if [ $? -ne 0 ]; then
    echo "Preflight failed. Commit aborted."
    exit 1
  fi
fi
```

### Test-Driven Development

1. **Write failing test** for new local model feature
2. **Implement feature** in custom provider code
3. **Run preflight** to validate basic connectivity
4. **Run integration tests** to verify behavior
5. **Benchmark** to ensure no performance regression
6. **Commit** when all tests pass

### Debugging Failed Tests

```bash
# Enable debug logging
export HERMES_LOG_LEVEL=DEBUG

# Run single test with full output
pytest tests/integration/test_qwen27b_custom_endpoint.py::test_chat_completion_returns_content_and_usage -vv -s

# Capture preflight report for analysis
python scripts/qwen27b_preflight.py --json-out debug-preflight.json
cat debug-preflight.json | jq .
```

---

## Additional Resources

- **Preflight Script**: [`scripts/qwen27b_preflight.py`](../../scripts/qwen27b_preflight.py)
- **Integration Tests**: [`tests/integration/test_qwen27b_custom_endpoint.py`](../../tests/integration/test_qwen27b_custom_endpoint.py)
- **Benchmark Script**: [`scripts/benchmark_local_model.py`](../../scripts/benchmark_local_model.py)
- **Testing Best Practices**: [`testing-best-practices.md`](testing-best-practices.md)

---

## Next Steps

1. **Review Testing Best Practices**: See [testing-best-practices.md](testing-best-practices.md)
2. **Explore Integration Templates**: See [integration-test-templates.md](integration-test-templates.md)
3. **Run Benchmark Suite**: Use [benchmark_local_model.py](../../scripts/benchmark_local_model.py)
4. **Set Up CI Integration**: See [CI enhancement documentation](../.github/workflows/tests.yml)
