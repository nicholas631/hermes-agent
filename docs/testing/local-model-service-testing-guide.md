# Local Model Service Testing Guide

**Version**: 0.1.1  
**Date**: 2026-05-13  
**Target Service**: LLM Local Model Service

## Overview

This guide covers comprehensive testing of three models from the LLM Local Model Service:

1. **qwen36_27b** - Qwen 3.6 27B (262k context, 35-40 tok/s)
2. **qwen36_35b_a3b** - Qwen 3.6 35B A3B (131k context, 50-60 tok/s)
3. **gemma4_31b_iq4_nl** - Gemma 4 31B (256k context, ~35 tok/s)

The testing infrastructure includes:
- **Smoke tests** - Basic API validation (scripts/multi_model_preflight.py)
- **Integration tests** - Multi-turn conversations and parameter testing (tests/integration/test_local_model_service.py)
- **Performance benchmarks** - Speed and quality comparison (scripts/benchmark_local_models.py)

## Prerequisites

### 1. Service Running

Ensure the LLM Local Model Service is running on port 8085:

```powershell
# Check if service is running
curl http://127.0.0.1:8085/v1/health

# If not running, start it from the service directory
cd <path-to-your-llm-service>
python run_stack.py
```

### 2. Environment Variables

Set the base URL for the local service:

```powershell
$env:LLM_SERVICE_BASE_URL="http://127.0.0.1:8085/v1"
$env:LLM_SERVICE_API_KEY="not-needed"
```

### 3. Python Environment

Activate the Hermes Agent virtual environment:

```powershell
cd <path-to-hermes-agent>
venv\Scripts\Activate.ps1
```

## Running Tests

### Smoke Tests (Basic Validation)

The smoke test script validates that all three models are available and responding correctly.

**Basic usage:**

```powershell
python scripts\multi_model_preflight.py
```

**With JSON output:**

```powershell
python scripts\multi_model_preflight.py --json-out results\preflight_report.json
```

**Custom models:**

```powershell
python scripts\multi_model_preflight.py --models qwen36_27b gemma4_31b_iq4_nl
```

**Expected output:**

```
================================================================================
Multi-Model Preflight Report
================================================================================
Base URL:              http://127.0.0.1:8085/v1
Timestamp:             2026-05-13 22:00:00 UTC
/models reachable:     True
Models returned:       15
Tested models:         3
Overall success:       True

--- Model 1/3: qwen36_27b ---
  Listed in /v1/models:  True
  Detected context:      262144
  Chat completion ok:    True
  Prompt tokens:         25
  Completion tokens:     48
  Total tokens:          73
  Latency (ms):          1245.67
  Tokens / second:       38.54
  Response preview:      Deterministic test harnesses ensure...

--- Model 2/3: qwen36_35b_a3b ---
  Listed in /v1/models:  True
  Detected context:      131072
  Chat completion ok:    True
  Prompt tokens:         25
  Completion tokens:     52
  Total tokens:          77
  Latency (ms):          945.32
  Tokens / second:       55.01
  Response preview:      Test harnesses with deterministic...

--- Model 3/3: gemma4_31b_iq4_nl ---
  Listed in /v1/models:  True
  Detected context:      262144
  Chat completion ok:    True
  Prompt tokens:         25
  Completion tokens:     46
  Total tokens:          71
  Latency (ms):          1302.45
  Tokens / second:       35.32
  Response preview:      Deterministic testing frameworks...
```

**Exit codes:**
- `0` - All tests passed
- `1` - /v1/models endpoint unreachable
- `2` - One or more models failed (when --require-all-models is set)

### Integration Tests (pytest)

The integration test suite validates multi-turn conversations, temperature variations, and error handling.

**Run all integration tests:**

```powershell
python -m pytest tests\integration\test_local_model_service.py -v
```

**Run tests for a specific model:**

```powershell
python -m pytest tests\integration\test_local_model_service.py -v -k "qwen36_27b"
```

**Run only multi-turn tests:**

```powershell
python -m pytest tests\integration\test_local_model_service.py -v -k "multi_turn"
```

**Skip if service unavailable:**

The tests automatically skip if `LLM_SERVICE_BASE_URL` is not set or if the service is unreachable.

**Expected output:**

```
tests/integration/test_local_model_service.py::test_models_endpoint_lists_data PASSED
tests/integration/test_local_model_service.py::test_chat_completion_basic[qwen36_27b] PASSED
tests/integration/test_local_model_service.py::test_chat_completion_basic[qwen36_35b_a3b] PASSED
tests/integration/test_local_model_service.py::test_chat_completion_basic[gemma4_31b_iq4_nl] PASSED
tests/integration/test_local_model_service.py::test_chat_completion_temperature_variations[qwen36_27b-0.0] PASSED
tests/integration/test_local_model_service.py::test_chat_completion_temperature_variations[qwen36_27b-0.5] PASSED
tests/integration/test_local_model_service.py::test_chat_completion_temperature_variations[qwen36_27b-1.0] PASSED
... (more tests)

============================== 45 passed in 180.23s ===============================
```

### Performance Benchmarks

The benchmark script runs standardized prompts across all models and generates comparison reports.

**Basic usage:**

```powershell
python scripts\benchmark_local_models.py
```

**With detailed output:**

```powershell
python scripts\benchmark_local_models.py --detailed
```

**Custom output location:**

```powershell
python scripts\benchmark_local_models.py --json-out results\my_benchmark.json
```

**Expected output:**

```
========================================================================================================================
LLM LOCAL MODEL SERVICE BENCHMARK
========================================================================================================================
Base URL: http://127.0.0.1:8085/v1
Models:   qwen36_27b, qwen36_35b_a3b, gemma4_31b_iq4_nl
Tasks:    4
========================================================================================================================

Benchmarking model: qwen36_27b
  Running task: Code Generation
    ✓ Completed in 6234ms (41.1 tok/s)
  Running task: Logical Reasoning
    ✓ Completed in 5892ms (43.5 tok/s)
  Running task: Long-form Writing
    ✓ Completed in 12045ms (42.5 tok/s)
  Running task: Structured Output
    ✓ Completed in 4567ms (56.1 tok/s)

Benchmarking model: qwen36_35b_a3b
  Running task: Code Generation
    ✓ Completed in 4532ms (56.5 tok/s)
... (more results)

========================================================================================================================
BENCHMARK COMPARISON TABLE
========================================================================================================================

Code Generation (code):
------------------------------------------------------------------------------------------------------------------------
Model                     Latency (ms)    Tok/s      Tokens     Status    
------------------------------------------------------------------------------------------------------------------------
qwen36_27b                6234            41.1       256        ✓ Pass    
qwen36_35b_a3b            4532            56.5       256        ✓ Pass    
gemma4_31b_iq4_nl         7123            36.0       256        ✓ Pass    

Logical Reasoning (reasoning):
------------------------------------------------------------------------------------------------------------------------
Model                     Latency (ms)    Tok/s      Tokens     Status    
------------------------------------------------------------------------------------------------------------------------
qwen36_27b                5892            43.5       256        ✓ Pass    
qwen36_35b_a3b            4289            59.7       256        ✓ Pass    
gemma4_31b_iq4_nl         6745            37.9       256        ✓ Pass    

... (more tables)

JSON report written to: results\model_benchmarks\benchmark_20260513_220000.json
```

## Interpreting Results

### Smoke Test Results

**Success criteria:**
- All models listed in /v1/models endpoint
- All models return valid chat completions
- Response contains non-empty content
- Usage statistics are present (prompt_tokens, completion_tokens)

**Common issues:**
- **Model not listed**: Model may not be loaded in the service. Check service logs.
- **Timeout**: Model may be slow to respond. Increase `--timeout` parameter.
- **Connection refused**: Service is not running. Start the service first.

### Integration Test Results

**Success criteria:**
- Multi-turn conversations maintain context
- Temperature variations produce different outputs
- Max tokens limits are respected
- Invalid models return appropriate errors

**Common issues:**
- **Tests skipped**: `LLM_SERVICE_BASE_URL` not set or service unreachable.
- **Timeout errors**: Increase `LLM_SERVICE_TIMEOUT` environment variable.
- **Token count mismatches**: Allow tolerance in assertions (tokenization differences).

### Benchmark Results

**Key metrics:**

1. **Latency (ms)**: Total time to complete the request
   - Lower is better
   - Expected: 4000-12000ms depending on prompt length and model

2. **Tokens/second**: Generation speed
   - Higher is better
   - Expected ranges:
     - qwen36_27b: 35-40 tok/s
     - qwen36_35b_a3b: 50-60 tok/s
     - gemma4_31b_iq4_nl: 30-35 tok/s

3. **Response quality**: Subjective evaluation of output
   - Check response previews in detailed output
   - Verify JSON structure for structured output tasks

**Model comparison:**

- **qwen36_27b**: Best for long-context tasks (262k context window)
- **qwen36_35b_a3b**: Fastest generation speed (50-60 tok/s)
- **gemma4_31b_iq4_nl**: Good balance of context (256k) and speed

## Troubleshooting

### Service Not Running

**Symptom:** Connection refused errors

**Solution:**
```powershell
cd <path-to-your-llm-service>
python run_stack.py
```

Wait for "Service ready" message before running tests.

### Model Not Loaded

**Symptom:** Model not listed in /v1/models, or 404 errors

**Solution:**

Check the service configuration in `LLM_Local_Model_Service\config\local_services.yaml` to ensure the model is configured. Check service logs for model loading errors.

### Timeout Errors

**Symptom:** Requests timeout, especially for long prompts

**Solution:**

Increase timeout values:

```powershell
# For smoke tests
python scripts\multi_model_preflight.py --timeout 120

# For integration tests
$env:LLM_SERVICE_TIMEOUT="120"
python -m pytest tests\integration\test_local_model_service.py

# For benchmarks
python scripts\benchmark_local_models.py --timeout 180
```

### Memory Errors

**Symptom:** Service crashes or becomes unresponsive

**Solution:**

The RTX 3090 has 24GB VRAM. Only one model can be loaded at a time. If testing multiple models, the service will automatically unload and reload models, which adds latency.

For best performance, test one model at a time:

```powershell
python scripts\multi_model_preflight.py --models qwen36_27b
```

### JSON Parse Errors

**Symptom:** "Failed to parse JSON response"

**Solution:**

Check if the service is returning HTML error pages instead of JSON. This usually indicates:
- Service is down
- Wrong port or URL
- Service is in error state

Check service logs and restart if necessary.

## Windows-Specific Notes

### PowerShell Environment Variables

Set environment variables for the current session:

```powershell
$env:LLM_SERVICE_BASE_URL="http://127.0.0.1:8085/v1"
```

Set environment variables permanently (requires admin):

```powershell
[System.Environment]::SetEnvironmentVariable("LLM_SERVICE_BASE_URL", "http://127.0.0.1:8085/v1", "User")
```

### Path Separators

All scripts accept both forward slashes (`/`) and backslashes (`\`) for paths. Windows-native paths are shown in examples, but Unix-style paths also work:

```powershell
# Both work
python scripts\benchmark_local_models.py
python scripts/benchmark_local_models.py
```

### Virtual Environment Activation

Use the Windows-specific activation script:

```powershell
venv\Scripts\Activate.ps1
```

If you get an execution policy error:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Automated Testing Workflow

For regular testing, create a PowerShell script:

**test_all_models.ps1:**

```powershell
# Set environment
$env:LLM_SERVICE_BASE_URL="http://127.0.0.1:8085/v1"

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run smoke tests
Write-Host "Running smoke tests..."
python scripts\multi_model_preflight.py --json-out results\preflight_latest.json
if ($LASTEXITCODE -ne 0) {
    Write-Host "Smoke tests failed!" -ForegroundColor Red
    exit 1
}

# Run integration tests
Write-Host "Running integration tests..."
python -m pytest tests\integration\test_local_model_service.py -v --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "Integration tests failed!" -ForegroundColor Red
    exit 1
}

# Run benchmarks
Write-Host "Running benchmarks..."
python scripts\benchmark_local_models.py --detailed
if ($LASTEXITCODE -ne 0) {
    Write-Host "Benchmarks failed!" -ForegroundColor Red
    exit 1
}

Write-Host "All tests passed!" -ForegroundColor Green
```

Run the script:

```powershell
.\test_all_models.ps1
```

## Results Storage

All test results are stored in structured directories:

```
Hermes_Agent/
├── results/
│   ├── model_benchmarks/
│   │   ├── benchmark_20260513_220000.json
│   │   ├── benchmark_20260513_230000.json
│   │   └── ...
│   ├── preflight_latest.json
│   └── ...
```

JSON results can be analyzed programmatically or imported into Excel/other tools for further analysis.

## Next Steps

After completing all tests:

1. Review benchmark comparison tables
2. Identify best model for specific use cases
3. Create baseline report (see docs/testing/model-baseline-reports/)
4. Update ai-change-log.md with test results
5. Integrate chosen models into Hermes Agent workflows

## Support

For issues or questions:
- Check service logs in your LLM service logs directory
- Review service documentation in your LLM service README.md
- Check Hermes Agent AGENTS.md for integration patterns
