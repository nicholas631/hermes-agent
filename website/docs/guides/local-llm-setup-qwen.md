---
title: "Local LLM Setup - Qwen 3.6 27B"
description: "Quick start guide for running Hermes Agent with local Qwen 3.6 27B models"
sidebar_position: 5
revision: 1.0.1
last_updated: 2026-05-13
---

# Local LLM Setup - Qwen 3.6 27B

Run Hermes Agent with a local Qwen 3.6 27B model for complete privacy, no API costs, and offline operation.

## Prerequisites

### Required

| Item | Requirement |
|------|-------------|
| **Hermes Agent** | Installed and configured |
| **Local LLM Service** | Running Qwen 3.6 27B on OpenAI-compatible endpoint |
| **Python** | 3.11+ |

### Hardware Requirements

For optimal performance with Qwen 3.6 27B (Q4_K_M quantization):

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **GPU VRAM** | 16 GB | 24 GB+ (RTX 3090, 4090) |
| **System RAM** | 16 GB | 32 GB+ |
| **Storage** | 20 GB free | 50 GB+ SSD |

---

## 5-Minute Setup

### Step 1: Verify Local LLM Service

Ensure your local LLM service is running and accessible:

```powershell
# Test health endpoint
curl http://localhost:8085/v1/health

# List available models
curl http://localhost:8085/v1/models
```

Expected response should include:
```json
{
  "data": [
    {"id": "qwen36_27b", "object": "model"},
    {"id": "qwen36_27b_otq", "object": "model"},
    {"id": "qwen36_27b_dflash", "object": "model"}
  ]
}
```

### Step 2: Configure Hermes Agent

**Option A: Interactive Configuration (Recommended)**

```powershell
# Launch model selection wizard
hermes model

# Select: Custom endpoint
# Enter base URL: http://localhost:8085/v1
# Enter model name: qwen36_27b
```

**Option B: Direct Configuration**

```powershell
hermes config set model.provider custom
hermes config set model.base_url http://localhost:8085/v1
hermes config set model.model qwen36_27b
```

**Option C: Manual Config File Edit**

Edit `~/.hermes/config.yaml`:

```yaml
model:
  provider: custom
  model: qwen36_27b
  base_url: http://localhost:8085/v1
  context_window: 262144  # Optional: auto-detected if omitted
  max_output_tokens: 8192  # Optional: uses model default
```

### Step 3: Validate Connection

Run the preflight check script:

```powershell
python scripts\qwen27b_preflight.py
```

Expected output:
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
Response preview:      Deterministic test harnesses improve...
```

### Step 4: Start Chatting

Launch Hermes in interactive mode:

```powershell
hermes
```

Try a test prompt:
```
> Write a Python function to calculate fibonacci numbers
```

---

## Verification Checklist

Use this checklist to verify everything is working:

- [ ] `/models` endpoint returns model list
- [ ] Chat completion succeeds with valid response
- [ ] Token usage metrics are reported
- [ ] Latency is within expected range (~6 tokens/sec for Qwen 3.6 27B)
- [ ] Tool calling works (try: "What files are in the current directory?")
- [ ] Multi-turn conversation maintains context

---

## Available Models

Your local service may provide multiple Qwen 3.6 27B variants:

### qwen36_27b (Recommended for Maximum Context)

- **Description**: Standard Q4_K_M quantization
- **VRAM**: ~13.2 GB
- **Speed**: ~23 tokens/sec
- **Context**: 262,144 tokens
- **Best for**: General use, maximum context window

**Configure:**
```powershell
hermes config set model.model qwen36_27b
```

### qwen36_27b_mtp ⚡ NEW: Fastest Inference

- **Description**: Multi-Token Prediction variant (draft_n=2)
- **VRAM**: ~13.2 GB (same as baseline)
- **Speed**: ~28 tokens/sec (**21% faster!**)
- **Context**: 65,536 tokens (reduced for MTP overhead)
- **Best for**: Speed-critical applications, typical Hermes tasks
- **Quality**: Identical to baseline (zero quality loss)

**Configure:**
```powershell
hermes config set model.model qwen36_27b_mtp
```

> **What is MTP?** Multi-Token Prediction uses speculative decoding to predict multiple tokens ahead. Accepted predictions are "free" (no generation needed), resulting in 20-130% speedup with identical quality. See the [MTP Models Guide](./mtp-models-guide.md) for details.

### qwen36_27b_mtp_draft1 ⚡ NEW: Balanced MTP

- **Description**: MTP with draft_n=1 (conservative)
- **VRAM**: ~13.2 GB
- **Speed**: ~26 tokens/sec (~15% faster)
- **Context**: 65,536 tokens
- **Best for**: Predictable performance, production use

**Configure:**
```powershell
hermes config set model.model qwen36_27b_mtp_draft1
```

### qwen36_27b_otq

- **Description**: Optimized quantization variant
- **VRAM**: ~12.8 GB
- **Speed**: ~24 tokens/sec
- **Context**: 262,144 tokens
- **Best for**: Slightly faster inference with minimal quality tradeoff

**Configure:**
```powershell
hermes config set model.model qwen36_27b_otq
```

### qwen36_27b_dflash

- **Description**: DeepSpeed FlashAttention variant
- **VRAM**: ~13.5 GB
- **Speed**: ~25 tokens/sec
- **Context**: 262,144 tokens
- **Best for**: Faster inference with FlashAttention

**Configure:**
```powershell
hermes config set model.model qwen36_27b_dflash
```

### qwen36_35b_a3b_mtp 🚀 NEW: Maximum Speed

- **Description**: 35B MoE model with MTP (draft_n=2)
- **VRAM**: ~20 GB
- **Speed**: ~64 tokens/sec (**130% faster than baseline!**)
- **Context**: 32,768 tokens
- **Best for**: Maximum performance, fastest possible inference
- **Quality**: Identical to baseline

**Configure:**
```powershell
hermes config set model.model qwen36_35b_a3b_mtp
```

> **MTP Performance**: The 35B-A3B MTP variant achieves **2.31x speedup** over its baseline, making it the fastest model available. See [MTP Models Guide](./mtp-models-guide.md) for comprehensive comparison and usage recommendations.

---

## Performance Expectations

### Baseline Metrics

Based on testing with RTX 3090 (24GB VRAM):

| Metric | Value | Notes |
|--------|-------|-------|
| **Model Load Time** | 22.6 seconds | First request after service start |
| **VRAM Usage** | 13.2 GB | Steady state during inference |
| **Inference Speed** | ~6 tokens/sec | Average for 96-token completions |
| **Context Window** | 262,144 tokens | ~200,000 words |
| **Max Tested Context** | 50,000 tokens | Stable performance |

### Performance by Context Size

| Context Size | Expected Latency | Expected Throughput | Notes |
|--------------|------------------|---------------------|-------|
| < 1k tokens | ~15 seconds | 6-7 tok/s | Optimal performance |
| 1k-10k tokens | ~20 seconds | 5-6 tok/s | Normal range |
| 10k-50k tokens | ~30 seconds | 4-5 tok/s | Expected degradation |
| 50k-100k tokens | ~60 seconds | 3-4 tok/s | Noticeable slowdown |
| 100k+ tokens | Varies | 2-3 tok/s | Use with caution |

### First Request Delay

The first request after starting the LLM service will be slower (~20-30 seconds) as the model loads into VRAM. Subsequent requests will use the cached model and be much faster.

---

## Configuration Options

### Basic Configuration

Minimal setup for local model:

```yaml
model:
  provider: custom
  model: qwen36_27b
  base_url: http://localhost:8085/v1
```

### Advanced Configuration

Full configuration with all optional settings:

```yaml
model:
  provider: custom
  model: qwen36_27b
  base_url: http://localhost:8085/v1
  context_window: 262144      # Optional: auto-detected from /models
  max_output_tokens: 8192     # Optional: model's default max
  temperature: 0.7            # Optional: creativity level (0.0-2.0)
  top_p: 0.9                  # Optional: nucleus sampling
  
# Optional: Authentication (if your service requires it)
# Set in ~/.hermes/.env:
# CUSTOM_API_KEY=your-api-key-here
```

### Remote Local LLM

If your LLM service is running on another machine in your network:

```yaml
model:
  provider: custom
  model: qwen36_27b
  base_url: http://192.168.1.100:8085/v1  # Remote IP
```

---

## Common Use Cases

### Use Case 1: Code Generation

```
> Create a Python function that validates email addresses using regex
```

**Expected performance:**
- Latency: 15-20 seconds
- Quality: Production-ready code with validation, error handling
- Features: Type hints, docstrings, edge case handling

### Use Case 2: Code Review

```
> Review this code and suggest improvements:

def process(data):
    result = []
    for i in data:
        if i > 0:
            result.append(i * 2)
    return result
```

**Expected performance:**
- Latency: 10-15 seconds
- Analysis: Identifies inefficiencies, suggests list comprehension
- Quality: Provides refactored code with explanations

### Use Case 3: Debugging

```
> This function should find duplicates but returns empty list. Find the bug:

def find_duplicates(arr):
    seen = []
    dupes = []
    for item in arr:
        if item in seen:
            dupes.append(item)
        seen = []  # Bug!
    return dupes
```

**Expected performance:**
- Latency: 10-15 seconds
- Analysis: Identifies the bug (resetting seen list)
- Solution: Provides fixed code with explanation

### Use Case 4: Documentation

```
> Generate a comprehensive README for a REST API project that uses Flask,
PostgreSQL, and JWT authentication
```

**Expected performance:**
- Latency: 25-30 seconds
- Quality: Complete README with sections for setup, usage, API docs
- Formatting: Proper markdown with code examples

---

## Troubleshooting

### Connection Issues

**Symptom:** `Connection refused` or timeout errors

**Solutions:**

1. **Check if service is running:**
   ```powershell
   curl http://localhost:8085/v1/health
   ```

2. **Verify port is not blocked:**
   ```powershell
   Get-NetTCPConnection -LocalPort 8085
   ```

3. **Check Hermes configuration:**
   ```powershell
   hermes config list
   ```

4. **Ensure base URL includes `/v1`:**
   ```yaml
   base_url: http://localhost:8085/v1  # Correct
   # base_url: http://localhost:8085   # Wrong - missing /v1
   ```

### Model Not Found

**Symptom:** Error message: "Model not found" or "Model not available"

**Solutions:**

1. **List available models:**
   ```powershell
   curl http://localhost:8085/v1/models
   ```

2. **Verify exact model name:**
   ```powershell
   # Check what models are actually available
   curl http://localhost:8085/v1/models | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object id
   ```

3. **Update Hermes config with exact name:**
   ```powershell
   hermes config set model.model qwen36_27b  # Must match exactly
   ```

### Slow Performance

**Symptom:** Responses taking longer than expected

**Diagnosis:**

```powershell
# Check GPU utilization
nvidia-smi

# Should show:
# - GPU Memory Used: ~13.2 GB
# - GPU Utilization: 90-100% during generation
# - Temperature: < 85°C
```

**Solutions:**

1. **Check VRAM availability:**
   - Ensure 16GB+ VRAM available
   - Close other GPU applications

2. **Verify model is loaded:**
   - First request after service start is slower
   - Wait 30 seconds after service starts

3. **Check for thermal throttling:**
   - GPU temperature should be < 85°C
   - Improve cooling if necessary

4. **Reduce context size:**
   - Large contexts (>50k tokens) slow down inference
   - Consider summarization for very large inputs

### Context Window Exceeded

**Symptom:** Error about exceeding context length

**Solutions:**

1. **Check configured context window:**
   ```powershell
   hermes config get model.context_window
   ```

2. **Let Hermes auto-detect:**
   ```powershell
   # Remove manual setting to use auto-detection
   hermes config unset model.context_window
   ```

3. **Enable context compression:**
   ```yaml
   compression:
     enabled: true
     target_tokens: 100000  # Compress when exceeding this
   ```

---

## Advanced Topics

### Multiple Model Profiles

Switch between different models easily:

```powershell
# Create separate profile for local model
hermes -p local-qwen config set model.provider custom
hermes -p local-qwen config set model.base_url http://localhost:8085/v1
hermes -p local-qwen config set model.model qwen36_27b

# Use the profile
hermes -p local-qwen
```

### Benchmarking Your Setup

Test your local model performance:

```powershell
# Quick benchmark
python scripts\benchmark_local_model.py --quick

# Full benchmark with report
python scripts\benchmark_local_model.py --output my-benchmark.json

# View results
cat my-benchmark.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### Automated Testing

Verify your setup with integration tests:

```powershell
# Set test environment variables
$env:QWEN27B_TEST_BASE_URL = "http://localhost:8085/v1"
$env:QWEN27B_TEST_MODEL = "qwen36_27b"

# Run integration tests
pytest -m integration tests\integration\test_qwen27b_custom_endpoint.py -v
```

---

## Comparison: Local vs Cloud Models

| Aspect | Local (Qwen 3.6 27B) | Cloud (GPT-4, Claude) |
|--------|----------------------|----------------------|
| **Cost** | Hardware only (one-time) | Per-token pricing |
| **Privacy** | Complete (never leaves your machine) | Data sent to provider |
| **Speed** | ~6 tokens/sec | ~20-50 tokens/sec |
| **Offline** | Yes | No |
| **Context** | 262k tokens | 128k-200k tokens |
| **Quality** | Excellent for code | Excellent for code |
| **Setup** | Complex (GPU required) | Simple (API key only) |

**When to use local:**
- Privacy-sensitive projects
- No API costs desired
- Offline operation required
- Large context needs (>100k tokens)
- Experimentation and learning

**When to use cloud:**
- Maximum performance needed
- No suitable GPU available
- Multi-modal needs (vision, audio)
- Latest model versions critical

---

## Additional Resources

- **MTP Models Guide**: [MTP Models Guide](./mtp-models-guide.md) - **NEW!** Comprehensive guide to faster MTP models
- **Preflight Script**: [`scripts/qwen27b_preflight.py`](https://github.com/NousResearch/hermes-agent/blob/main/scripts/qwen27b_preflight.py)
- **Benchmark Script**: [`scripts/benchmark_local_model.py`](https://github.com/NousResearch/hermes-agent/blob/main/scripts/benchmark_local_model.py)
- **Integration Tests**: [`tests/integration/test_qwen27b_custom_endpoint.py`](https://github.com/NousResearch/hermes-agent/blob/main/tests/integration/test_qwen27b_custom_endpoint.py)
- **Testing Guide**: [Local Model Testing Guide](../../docs/testing/local-model-testing-guide.md)
- **Troubleshooting**: [Troubleshooting Local Models](./troubleshooting-local-models.md)

---

## Next Steps

1. **Explore Capabilities**: Try different prompts and see what Qwen 3.6 27B can do
2. **Benchmark Your Setup**: Run performance tests to establish your baseline
3. **Try Advanced Features**: Test tool usage, long contexts, multi-turn conversations
4. **Read Testing Guide**: See [Local Model Testing Guide](../../docs/testing/local-model-testing-guide.md)
5. **Join Community**: Share your experience and get help

---

## Getting Help

If you encounter issues:

1. **Check Troubleshooting Guide**: [troubleshooting-local-models.md](./troubleshooting-local-models.md)
2. **Run Diagnostics**: `python scripts\qwen27b_preflight.py --json-out report.json`
3. **Check Logs**: `hermes --log-level DEBUG`
4. **Search Issues**: [GitHub Issues](https://github.com/NousResearch/hermes-agent/issues)
5. **Ask Community**: [Discord Server](https://discord.gg/nous-research)
