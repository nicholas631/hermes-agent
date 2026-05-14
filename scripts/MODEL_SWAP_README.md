# Model Swap Quick Reference

**Version**: 1.0.0  
**Date**: 2026-05-14

## Quick Start

### Switch to MTP (Faster Models)

```powershell
# Fast 27B model (21% speedup)
.\scripts\swap_model.ps1 27b-mtp

# Fastest 35B model (130% speedup)
.\scripts\swap_model.ps1 35b-mtp

# Conservative MTP (draft_n=1)
.\scripts\swap_model.ps1 27b-mtp1
```

### Switch to Baseline (Maximum Context)

```powershell
# Standard 27B (262k context)
.\scripts\swap_model.ps1 27b

# Standard 35B-A3B (131k context)
.\scripts\swap_model.ps1 35b
```

---

## Model Comparison

| Short Name | Full Model Name | Speed | Context | Speedup |
|------------|----------------|-------|---------|---------|
| `27b` | qwen36_27b | 23 tok/s | 262k | Baseline |
| `27b-mtp` | qwen36_27b_mtp | 28 tok/s | 65k | +21% ⚡ |
| `27b-mtp1` | qwen36_27b_mtp_draft1 | 26 tok/s | 65k | +15% |
| `35b` | qwen36_35b_a3b | 28 tok/s | 131k | Baseline |
| `35b-mtp` | qwen36_35b_a3b_mtp | 64 tok/s | 32k | +130% 🚀 |
| `35b-mtp1` | qwen36_35b_a3b_mtp_draft1 | 33 tok/s | 32k | +17% |

---

## Usage Examples

### Example 1: Switch with Info Display

```powershell
.\scripts\swap_model.ps1 27b-mtp -ShowInfo
```

Output:
```
[OK] Model switched to: qwen36_27b_mtp

Model Information:
  Name:       Qwen 3.6 27B MTP (draft_n=2)
  Type:       MTP
  Speed:      ~28 tok/s
  VRAM:       13.2 GB
  Context:    65,536 tokens
  Speedup:    1.21x (+21%)
```

### Example 2: Switch Without Verification

```powershell
.\scripts\swap_model.ps1 35b-mtp -Verify:$false
```

### Example 3: Custom Service URL

```powershell
.\scripts\swap_model.ps1 27b-mtp -BaseUrl http://192.168.1.100:8085/v1
```

---

## When to Use Each Model

### Use MTP Models When:
- **Speed is priority** - Need faster responses
- **Context < 65k tokens** - Your prompts fit in reduced context
- **Interactive use** - Quick back-and-forth conversations
- **Typical Hermes tasks** - Code generation, questions, tool use

### Use Baseline Models When:
- **Large context needed** - Analyzing entire codebases (>65k tokens)
- **Maximum context** - Processing long documents
- **Prefer stability** - Production environments requiring proven tech
- **VRAM constrained** - Running multiple models simultaneously

---

## Script Options

### Parameters

```powershell
.\scripts\swap_model.ps1 <Model> [-BaseUrl <url>] [-Verify <bool>] [-ShowInfo]
```

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `Model` | Yes | - | Target model (27b, 27b-mtp, 35b, 35b-mtp, etc.) |
| `BaseUrl` | No | http://localhost:8085/v1 | LLM service endpoint |
| `Verify` | No | $true | Verify model exists before switching |
| `ShowInfo` | No | $false | Display detailed model info after switch |

### Supported Model Names

**Baseline Models:**
- `27b`, `27b-base`, `qwen36_27b`
- `35b`, `35b-base`, `qwen36_35b_a3b`

**MTP Models (draft_n=2):**
- `27b-mtp`, `qwen36_27b_mtp`
- `35b-mtp`, `qwen36_35b_a3b_mtp`

**MTP Models (draft_n=1):**
- `27b-mtp1`, `qwen36_27b_mtp_draft1`
- `35b-mtp1`, `qwen36_35b_a3b_mtp_draft1`

---

## Troubleshooting

### Script Not Found

```powershell
# Ensure you're in the Hermes_Agent directory
cd D:\Python_Projects\Hermes_Agent

# Run with full path
.\scripts\swap_model.ps1 27b-mtp
```

### Model Not Available

If you get "Model not found" error:

1. **Check LLM service is running:**
   ```powershell
   curl http://localhost:8085/v1/health
   ```

2. **List available models:**
   ```powershell
   curl http://localhost:8085/v1/models
   ```

3. **Verify MTP models exist:**
   ```powershell
   curl http://localhost:8085/v1/models | ConvertFrom-Json | 
     Select-Object -ExpandProperty data | 
     Where-Object { $_.id -like "*mtp*" }
   ```

### Hermes Command Not Found

Ensure Hermes is installed and in PATH:

```powershell
# Check installation
hermes --version

# If not found, activate venv
.\venv\Scripts\Activate.ps1
```

---

## Integration with Hermes

### Current Model

Check which model is currently configured:

```powershell
hermes config get model.model
```

### Manual Configuration

You can also configure manually:

```powershell
hermes config set model.provider custom
hermes config set model.base_url http://localhost:8085/v1
hermes config set model.model qwen36_27b_mtp
```

### Config File Location

Configuration stored at:
- **Windows**: `C:\Users\<username>\.hermes\config.yaml`
- **Linux/Mac**: `~/.hermes/config.yaml`

---

## Performance Testing

### After Switching Models

Test the new model's performance:

```powershell
# Quick test
hermes

> Write a Python function to calculate fibonacci numbers

# Benchmark test
python scripts\benchmark_local_model.py --model qwen36_27b_mtp
```

### Compare Models

Compare baseline vs MTP:

```powershell
python scripts\benchmark_local_models.py `
    --models qwen36_27b qwen36_27b_mtp `
    --output results\comparison.json
```

---

## Advanced Usage

### Profile-Based Switching

Create separate profiles for different scenarios:

```powershell
# Create "fast" profile with MTP
hermes -p fast config set model.model qwen36_27b_mtp

# Create "deep" profile with baseline
hermes -p deep config set model.model qwen36_27b

# Use profiles
hermes -p fast      # Fast interactive
hermes -p deep      # Deep analysis
```

### Batch Model Testing

Test all MTP variants:

```powershell
$models = @("27b", "27b-mtp", "27b-mtp1", "35b", "35b-mtp", "35b-mtp1")
foreach ($model in $models) {
    Write-Host "Testing $model..."
    .\scripts\swap_model.ps1 $model
    python scripts\benchmark_local_model.py --quick
}
```

---

## See Also

- **[MTP Models Guide](../docs/guides/mtp-models-guide.md)** - Comprehensive MTP documentation
- **[Local LLM Setup](../website/docs/guides/local-llm-setup-qwen.md)** - Initial setup guide
- **[Local Model Testing](../docs/testing/local-model-testing-guide.md)** - Testing procedures

---

## Getting Help

Issues with model swapping:

1. **Check service health:**
   ```powershell
   curl http://localhost:8085/v1/health
   ```

2. **Verify current config:**
   ```powershell
   hermes config list
   ```

3. **Run preflight check:**
   ```powershell
   python scripts\multi_model_preflight.py
   ```

4. **Check logs:**
   ```powershell
   hermes --log-level DEBUG
   ```

---

**Last Updated**: 2026-05-14  
**Version**: 1.0.0
