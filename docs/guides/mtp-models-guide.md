# MTP Models Guide - Faster Inference with Multi-Token Prediction

**Version**: 1.0.0  
**Date**: 2026-05-14  
**Target**: Hermes Agent with LLM Local Model Service  
**Status**: Production Ready ✅

---

## Overview

Multi-Token Prediction (MTP) models provide **21-130% speedup** over baseline models through speculative decoding. Your local LLM service now offers MTP variants for all Qwen 3.6 models.

### What is MTP?

MTP is a speculative decoding technique where the model predicts multiple tokens ahead simultaneously:
1. Main model generates hidden states
2. MTP head predicts 2 draft tokens ahead
3. Main model validates predictions
4. Accepted tokens are "free" (no generation needed)
5. Rejected tokens fall back to standard generation

**Result**: 1.21-2.31x faster inference with **zero quality loss**.

---

## Quick Start (5 Minutes)

### Step 1: Verify MTP Models Available

Check that your LLM service has MTP models:

```powershell
curl http://localhost:8085/v1/models | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object id | Where-Object { $_.id -like "*mtp*" }
```

Expected output:
```
id
--
qwen36_27b_mtp
qwen36_27b_mtp_draft1
qwen36_35b_a3b_mtp
qwen36_35b_a3b_mtp_draft1
```

### Step 2: Switch to MTP Model

**Option A: Interactive Configuration**

```powershell
hermes model

# Select: Custom endpoint
# Base URL: http://localhost:8085/v1
# Model: qwen36_27b_mtp  # Choose MTP variant
```

**Option B: Direct Configuration**

```powershell
hermes config set model.model qwen36_27b_mtp
```

**Option C: Config File**

Edit `~/.hermes/config.yaml`:

```yaml
model:
  provider: custom
  model: qwen36_27b_mtp  # Changed from qwen36_27b
  base_url: http://localhost:8085/v1
```

### Step 3: Test Performance

```powershell
# Test prompt
hermes

> Write a Python function to validate email addresses
```

**Expected**: Response 20-130% faster than baseline (depending on model)

---

## Available MTP Models

### Qwen 3.6 27B MTP Models

#### qwen36_27b_mtp (draft_n=2) ⭐ Recommended

- **Speedup**: 1.21x faster (27.75 tok/s vs 22.86 tok/s baseline)
- **Acceptance Rate**: 75.6% (excellent)
- **VRAM**: ~13.2 GB (same as baseline)
- **Context**: 65,536 tokens (reduced for MTP overhead)
- **Best For**: General use, balanced speed improvement

**Configure:**
```powershell
hermes config set model.model qwen36_27b_mtp
```

#### qwen36_27b_mtp_draft1 (draft_n=1)

- **Speedup**: ~1.15x faster (expected)
- **Acceptance Rate**: ~85% (higher acceptance, lower speedup)
- **VRAM**: ~13.2 GB
- **Context**: 65,536 tokens
- **Best For**: Maximum prediction accuracy, consistent speedup

**Configure:**
```powershell
hermes config set model.model qwen36_27b_mtp_draft1
```

### Qwen 3.6 35B-A3B MTP Models

#### qwen36_35b_a3b_mtp (draft_n=2) 🚀 Best Speedup

- **Speedup**: 2.31x faster (64.22 tok/s vs 27.86 tok/s baseline)
- **Acceptance Rate**: 57.6% (good for MoE)
- **VRAM**: ~20 GB
- **Context**: 32,768 tokens (reduced for MTP overhead)
- **Best For**: Maximum performance, faster inference

**Configure:**
```powershell
hermes config set model.model qwen36_35b_a3b_mtp
```

#### qwen36_35b_a3b_mtp_draft1 (draft_n=1)

- **Speedup**: ~1.17x faster (expected)
- **Acceptance Rate**: ~82% (expected)
- **VRAM**: ~20 GB
- **Context**: 32,768 tokens
- **Best For**: MoE with higher prediction accuracy

**Configure:**
```powershell
hermes config set model.model qwen36_35b_a3b_mtp_draft1
```

---

## Performance Comparison

### Qwen 3.6 27B: Baseline vs MTP

| Metric | Baseline | MTP (draft_n=2) | Improvement |
|--------|----------|-----------------|-------------|
| **Speed** | 22.86 tok/s | 27.75 tok/s | **+21%** ⚡ |
| **Acceptance** | N/A | 75.6% | ✅ Excellent |
| **VRAM** | 13.2 GB | 13.2 GB | Same |
| **Context** | 262k tokens | 65k tokens | ⚠️ Reduced |
| **Quality** | ✅ | ✅ | **Identical** |

### Qwen 3.6 35B-A3B: Baseline vs MTP

| Metric | Baseline | MTP (draft_n=2) | Improvement |
|--------|----------|-----------------|-------------|
| **Speed** | 27.86 tok/s | 64.22 tok/s | **+130%** 🚀 |
| **Acceptance** | N/A | 57.6% | ✅ Good |
| **VRAM** | 20 GB | 20 GB | Same |
| **Context** | 131k tokens | 32k tokens | ⚠️ Reduced |
| **Quality** | ✅ | ✅ | **Identical** |

**Key Finding**: MTP models maintain identical output quality - the speedup is "free" from a quality perspective.

---

## When to Use MTP Models

### ✅ Use MTP When:

1. **Speed is Priority**
   - Need faster responses for interactive use
   - Processing many similar queries
   - Time-sensitive applications

2. **Context Under 32k-65k Tokens**
   - Your typical prompts fit in reduced context window
   - Don't need maximum 262k context capacity
   - Most Hermes Agent tasks fall into this category

3. **Quality is Critical**
   - MTP maintains identical output quality
   - No accuracy trade-off
   - Same model weights, just faster inference

4. **VRAM is Available**
   - 16GB+ for 27B models
   - 24GB+ for 35B-A3B models
   - Same VRAM as baseline models

### ⚠️ Consider Baseline When:

1. **Need Maximum Context**
   - Working with very large codebases (>65k tokens)
   - Processing entire books or long documents
   - Multi-file analysis with deep context

2. **Prefer Stability Over Speed**
   - MTP is production-ready but newer technology
   - Baseline has more extensive field testing
   - Risk-averse production environments

3. **GPU Memory Constrained**
   - Running on exactly 12GB VRAM (tight fit)
   - Multiple models loaded simultaneously
   - Other GPU workloads running

---

## Switching Between Models

### Quick Model Swap

Switch between baseline and MTP variants easily:

```powershell
# Switch to MTP
hermes config set model.model qwen36_27b_mtp

# Switch back to baseline
hermes config set model.model qwen36_27b

# Verify current model
hermes config get model.model
```

### Profile-Based Switching

Create separate profiles for different use cases:

```powershell
# Setup: Create MTP profile
hermes -p fast config set model.provider custom
hermes -p fast config set model.base_url http://localhost:8085/v1
hermes -p fast config set model.model qwen36_27b_mtp

# Setup: Create baseline profile with max context
hermes -p deep config set model.provider custom
hermes -p deep config set model.base_url http://localhost:8085/v1
hermes -p deep config set model.model qwen36_27b

# Usage: Fast interactive sessions
hermes -p fast

# Usage: Deep analysis with max context
hermes -p deep
```

### Environment Variable Override

Temporarily override model without changing config:

```powershell
# Set environment variable
$env:HERMES_MODEL="qwen36_27b_mtp"

# Run Hermes (uses MTP model)
hermes

# Unset to return to config default
Remove-Item Env:\HERMES_MODEL
```

### Multi-Model Testing Script

Test multiple models and compare performance:

```powershell
# Test baseline vs MTP
python scripts\run_multi_model_tests.py `
    --models qwen36_27b qwen36_27b_mtp qwen36_35b_a3b qwen36_35b_a3b_mtp `
    --output-dir results\mtp_comparison

# View results
cat results\mtp_comparison\*_summary.json
```

---

## Configuration Examples

### Example 1: Fast Interactive Use (MTP)

Optimized for speed, typical Hermes Agent tasks:

```yaml
# ~/.hermes/config.yaml
model:
  provider: custom
  model: qwen36_27b_mtp  # MTP for speed
  base_url: http://localhost:8085/v1
  context_window: 65536   # MTP default
  max_output_tokens: 4096
  temperature: 0.7
```

**Best For**: Code generation, questions, conversations, tool use

### Example 2: Deep Analysis (Baseline)

Optimized for maximum context, complex tasks:

```yaml
# ~/.hermes/config.yaml
model:
  provider: custom
  model: qwen36_27b  # Baseline for max context
  base_url: http://localhost:8085/v1
  context_window: 262144  # Full 262k context
  max_output_tokens: 8192
  temperature: 0.7

compression:
  enabled: true
  target_tokens: 200000  # Compress above 200k
```

**Best For**: Codebase analysis, documentation review, large file processing

### Example 3: Maximum Speed (35B-A3B MTP)

Fastest possible inference:

```yaml
# ~/.hermes/config.yaml
model:
  provider: custom
  model: qwen36_35b_a3b_mtp  # 2.3x speedup!
  base_url: http://localhost:8085/v1
  context_window: 32768
  max_output_tokens: 2048  # Shorter for even faster
  temperature: 0.7
```

**Best For**: Rapid prototyping, testing, interactive exploration

### Example 4: Balanced Approach (draft_n=1)

Higher acceptance rate, consistent speedup:

```yaml
# ~/.hermes/config.yaml
model:
  provider: custom
  model: qwen36_27b_mtp_draft1  # draft_n=1 variant
  base_url: http://localhost:8085/v1
  context_window: 65536
  max_output_tokens: 4096
  temperature: 0.7
```

**Best For**: Production use, predictable performance, conservative approach

---

## Performance Testing

### Quick Benchmark

Test your MTP model performance:

```powershell
# Benchmark MTP model
python scripts\benchmark_local_model.py `
    --model qwen36_27b_mtp `
    --output results\mtp_benchmark.json

# Compare baseline vs MTP
python scripts\benchmark_local_models.py `
    --models qwen36_27b qwen36_27b_mtp `
    --output results\comparison.json
```

### Expected Results

Based on RTX 3090 testing:

| Model | Load Time | Avg Speed | 100 Token Gen |
|-------|-----------|-----------|---------------|
| qwen36_27b | 35s | 22.86 tok/s | ~4.4s |
| qwen36_27b_mtp | 20s | 27.75 tok/s | **~3.6s** ⚡ |
| qwen36_35b_a3b | 42s | 27.86 tok/s | ~3.6s |
| qwen36_35b_a3b_mtp | 21s | 64.22 tok/s | **~1.6s** 🚀 |

---

## Integration Testing

### Smoke Test All MTP Models

```powershell
# Update preflight script to include MTP
python scripts\multi_model_preflight.py `
    --models qwen36_27b qwen36_27b_mtp qwen36_35b_a3b qwen36_35b_a3b_mtp
```

### Integration Test Suite

```powershell
# Set test environment for MTP model
$env:LOCAL_MODEL_TEST_BASE_URL="http://127.0.0.1:8085/v1"
$env:LOCAL_MODEL_TEST_MODEL="qwen36_27b_mtp"

# Run integration tests
pytest tests\integration\test_local_model_endpoint.py -v

# Test with 35B-A3B MTP
$env:LOCAL_MODEL_TEST_MODEL="qwen36_35b_a3b_mtp"
pytest tests\integration\test_local_model_endpoint.py -v
```

### Automated Multi-Model Tests

```powershell
# Test all variants automatically
python scripts\run_multi_model_tests.py `
    --models qwen36_27b_mtp qwen36_35b_a3b_mtp `
    --tests basic performance tool_calling `
    --output-dir results\mtp_validation
```

---

## Troubleshooting

### MTP Model Not Found

**Symptom**: `Model not found` error for MTP model

**Solution**:
```powershell
# 1. Check available models
curl http://localhost:8085/v1/models | ConvertFrom-Json | Select-Object -ExpandProperty data | Select-Object id

# 2. Verify MTP models in list
# Should see: qwen36_27b_mtp, qwen36_27b_mtp_draft1, etc.

# 3. If missing, check LLM service is updated
curl http://localhost:8085/v1/health

# 4. Verify exact model name (case-sensitive)
hermes config set model.model qwen36_27b_mtp  # Correct
# hermes config set model.model qwen36_27b_MTP  # Wrong case
```

### Slower Than Expected

**Symptom**: MTP model not showing speedup

**Diagnosis**:
```powershell
# Check model is actually MTP variant
hermes config get model.model
# Should return: qwen36_27b_mtp (not qwen36_27b)

# Verify GPU utilization
nvidia-smi

# Should show high GPU usage during generation
```

**Solution**:
1. Ensure you're using MTP model (not baseline)
2. First request after model load is always slower
3. MTP speedup is most visible for longer generations (50+ tokens)
4. Very short completions (< 20 tokens) may not show speedup

### Context Window Errors

**Symptom**: "Context window exceeded" errors with MTP

**Explanation**: MTP models have reduced context (32k-65k vs 262k baseline) due to draft context overhead.

**Solution**:
```yaml
# Option 1: Explicitly set reduced context in config
model:
  model: qwen36_27b_mtp
  context_window: 65536  # Match MTP default

# Option 2: Enable compression for large inputs
compression:
  enabled: true
  target_tokens: 50000

# Option 3: Switch to baseline for large context needs
model:
  model: qwen36_27b  # Use baseline for >65k context
  context_window: 262144
```

### Load Failures

**Symptom**: MTP model fails to load or timeouts

**Solution**:
```powershell
# 1. Check LLM service logs
# Look for VRAM errors or GPU issues

# 2. Verify VRAM available
nvidia-smi

# 3. Unload other models first
curl -X POST http://localhost:8085/v1/admin/unload

# 4. Try loading again
curl -X POST http://localhost:8085/v1/admin/load `
    -H "Content-Type: application/json" `
    -d '{"model_name": "qwen36_27b_mtp"}'

# 5. If still fails, check service status
curl http://localhost:8085/v1/health
```

---

## Technical Details

### How MTP Works

```
Traditional Inference:
Token 1 → [Model] → Token 2 → [Model] → Token 3 → ...
Time:     1x        1x         1x

MTP Inference:
Token 1 → [Model] → Token 2 + draft(3,4) → [Validate] → Token 3,4 ✓
Time:     1x        1x                      0x (free!)

Result: 2-3 tokens in time of 2 → 1.5x speedup
```

### Acceptance Rates

| Model | draft_n | Acceptance Rate | Speedup |
|-------|---------|-----------------|---------|
| 27B | 1 | ~85% | ~1.15x |
| 27B | 2 | ~76% | ~1.21x |
| 35B-A3B | 1 | ~82% | ~1.17x |
| 35B-A3B | 2 | ~58% | ~2.31x 🚀 |

**Higher acceptance = more "free" tokens = better speedup**

### VRAM Requirements

MTP uses **same VRAM as baseline** because:
- Draft context allocated on same GPU
- Single GPU mode forces all allocation to RTX 3090 (24GB)
- Auto-fit mechanism reduces context to fit VRAM budget
- Result: No additional VRAM overhead

### Context Limitations

| Model | Baseline Context | MTP Context | Reduction |
|-------|------------------|-------------|-----------|
| 27B | 262,144 tokens | 65,536 tokens | 75% |
| 35B-A3B | 131,072 tokens | 32,768 tokens | 75% |

**Why?**: Draft context needs VRAM too. Single GPU mode limits total context to fit in 24GB.

---

## FAQ

**Q: Will MTP change my model's outputs?**  
A: No. MTP maintains **identical output quality**. The speculative tokens are validated, so rejected drafts fall back to standard generation.

**Q: Which is faster, 27B MTP or 35B-A3B MTP?**  
A: 35B-A3B MTP is much faster (64.22 vs 27.75 tok/s) but uses more VRAM (20GB vs 13GB).

**Q: Can I use MTP with very long contexts?**  
A: MTP is limited to 32k-65k context. For longer contexts, use baseline models.

**Q: Does MTP work with tool calling?**  
A: Yes! MTP is transparent to higher-level features like tool calling, streaming, etc.

**Q: Should I use draft_n=1 or draft_n=2?**  
A: draft_n=2 is recommended for best speedup. draft_n=1 offers more consistent (but smaller) speedup.

**Q: Will MTP work on my GPU?**  
A: Requires 16GB+ VRAM (27B) or 24GB+ (35B-A3B). Same as baseline models.

**Q: How do I check if MTP is actually working?**  
A: Run benchmark script and compare speeds. MTP should show 20-130% faster than baseline.

---

## Migration Checklist

Switching from baseline to MTP models:

- [ ] Verify MTP models available (`curl http://localhost:8085/v1/models`)
- [ ] Check VRAM requirements (16GB+ for 27B, 24GB+ for 35B-A3B)
- [ ] Update Hermes config (`model.model = qwen36_27b_mtp`)
- [ ] Test with simple prompt to verify faster responses
- [ ] Run benchmark to measure actual speedup
- [ ] Check if context window (32k-65k) is sufficient for your use cases
- [ ] Update profiles if using multiple configurations
- [ ] Run integration tests to verify tool calling, etc.
- [ ] Update documentation with MTP model names
- [ ] Consider creating separate profiles for MTP (fast) vs baseline (deep)

---

## Additional Resources

### Documentation
- **LLM Service MTP Resolution**: `d:\Python_Projects\LLM_Local_Model_Service\results\MTP_FINAL_RESOLUTION_20260514.md`
- **Performance Report**: `d:\Python_Projects\LLM_Local_Model_Service\results\MTP_DRAFT_COMPARISON_REPORT_20260514.md`
- **Sprint Gap Analysis**: `d:\Python_Projects\LLM_Local_Model_Service\results\SPRINT_GAP_ANALYSIS_20260514.md`

### Scripts
- **Multi-Model Preflight**: `scripts\multi_model_preflight.py`
- **Benchmark Tool**: `scripts\benchmark_local_models.py`
- **Multi-Model Tests**: `scripts\run_multi_model_tests.py`

### Integration Tests
- **Local Model Endpoint**: `tests\integration\test_local_model_endpoint.py`
- **Local Model Service**: `tests\integration\test_local_model_service.py`

---

## Getting Help

If you encounter issues with MTP models:

1. **Check this guide**: Most common issues covered in Troubleshooting section
2. **Run diagnostics**: `python scripts\multi_model_preflight.py --models qwen36_27b_mtp`
3. **Check LLM service health**: `curl http://localhost:8085/v1/health`
4. **Review service logs**: Check LLM service console for errors
5. **Test baseline first**: Verify `qwen36_27b` works before trying MTP
6. **Check VRAM**: `nvidia-smi` should show 16GB+ available

---

**Last Updated**: 2026-05-14  
**Version**: 1.0.0  
**Status**: Production Ready ✅
