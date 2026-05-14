---
title: "Troubleshooting Local Models"
description: "Solutions to common issues when running Hermes Agent with local LLM endpoints"
sidebar_position: 6
revision: 1.0.1
last_updated: 2026-05-13
---

# Troubleshooting Local Models

Comprehensive troubleshooting guide for resolving issues with local LLM endpoints in Hermes Agent.

## Quick Diagnostic Commands

Run these commands to gather diagnostic information:

```powershell
# Check if service is reachable
curl http://localhost:8085/v1/health

# List available models
curl http://localhost:8085/v1/models

# Run preflight diagnostics
python scripts\qwen27b_preflight.py --json-out report.json

# Check Hermes configuration
hermes config list

# Test with verbose logging
$env:HERMES_LOG_LEVEL = "DEBUG"
hermes chat -q "test"
```

---

## Connection Issues

### Issue: Connection Refused

**Symptoms:**
- `ConnectionError: Failed to establish connection`
- `Connection refused to localhost:8085`
- Hermes can't reach the local model

**Diagnosis:**

```powershell
# Check if service is running
curl http://localhost:8085/v1/health

# Check listening ports
Get-NetTCPConnection -LocalPort 8085

# Expected output: Local address 0.0.0.0:8085 or 127.0.0.1:8085
```

**Solutions:**

1. **Start the LLM service:**
   ```powershell
   cd <path-to-your-llm-service>
   .\start-service.ps1
   ```

2. **Verify service started successfully:**
   ```powershell
   # Check service logs
   cat logs\service.log

   # Look for: "Server started on port 8085"
   ```

3. **Check firewall settings:**
   ```powershell
   # Allow port 8085 in Windows Firewall
   New-NetFirewallRule -DisplayName "LLM Service" -Direction Inbound -LocalPort 8085 -Protocol TCP -Action Allow
   ```

4. **Verify base URL is correct:**
   ```powershell
   hermes config get model.base_url
   # Should be: http://localhost:8085/v1 (note the /v1 suffix!)
   ```

### Issue: Timeout Errors

**Symptoms:**
- `ReadTimeout: Request timed out after 30 seconds`
- Requests hang indefinitely

**Diagnosis:**

```powershell
# Test with longer timeout
curl http://localhost:8085/v1/models --max-time 60

# Check GPU utilization during request
nvidia-smi
```

**Solutions:**

1. **Increase timeout in Hermes config:**
   ```yaml
   # ~/.hermes/config.yaml
   model:
     timeout: 120  # Increase to 120 seconds
   ```

2. **Check if model is still loading:**
   - First request after service start takes 20-30 seconds
   - Wait until model fully loads before using Hermes

3. **Verify GPU is being utilized:**
   ```powershell
   # During a request, GPU utilization should be 90-100%
   nvidia-smi --query-gpu=utilization.gpu --format=csv --loop=1
   ```

4. **Check system resources:**
   - VRAM: Should have 16GB+ free
   - RAM: Should have 16GB+ free
   - CPU: Not maxed out

### Issue: SSL/Certificate Errors

**Symptoms:**
- `SSL: CERTIFICATE_VERIFY_FAILED`
- HTTPS connection errors

**Solutions:**

1. **Use HTTP (not HTTPS) for local services:**
   ```yaml
   base_url: http://localhost:8085/v1  # Correct
   # base_url: https://localhost:8085/v1  # Wrong for local
   ```

2. **If using remote service with self-signed cert:**
   ```powershell
   # Disable SSL verification (not recommended for production)
   $env:PYTHONHTTPSVERIFY = "0"
   ```

---

## Model Configuration Issues

### Issue: Model Not Found

**Symptoms:**
- `Model 'qwen36_27b' not found`
- `Invalid model identifier`

**Diagnosis:**

```powershell
# List exactly what models are available
curl http://localhost:8085/v1/models | ConvertFrom-Json | 
  Select-Object -ExpandProperty data | 
  Select-Object id

# Check configured model
hermes config get model.model
```

**Solutions:**

1. **Use exact model name from service:**
   ```powershell
   # Get available models
   $models = curl http://localhost:8085/v1/models | ConvertFrom-Json
   $models.data | ForEach-Object { $_.id }

   # Configure with exact name (case-sensitive!)
   hermes config set model.model qwen36_27b
   ```

2. **Verify model is loaded in service:**
   ```powershell
   # Check service logs for model loading messages
   cat logs\service.log | Select-String "model loaded"
   ```

3. **Restart service if model not loading:**
   ```powershell
   # Stop service
   Stop-Process -Name "llm-service" -Force

   # Clear cache (optional)
   Remove-Item cache\* -Recurse -Force

   # Restart service
   .\start-service.ps1
   ```

### Issue: Context Window Not Detected

**Symptoms:**
- Hermes uses wrong context limit
- "Context length exceeded" errors with small prompts

**Diagnosis:**

```powershell
# Check what model metadata reports
curl http://localhost:8085/v1/models | 
  ConvertFrom-Json | 
  Select-Object -ExpandProperty data | 
  Where-Object { $_.id -eq "qwen36_27b" }
```

**Solutions:**

1. **Let Hermes auto-detect:**
   ```powershell
   # Remove manual setting
   hermes config unset model.context_window

   # Hermes will query /models endpoint
   ```

2. **Manually set context window:**
   ```yaml
   # ~/.hermes/config.yaml
   model:
     context_window: 262144  # For Qwen 3.6 27B
   ```

3. **Verify service reports context correctly:**
   ```powershell
   # Model metadata should include context_length field
   curl http://localhost:8085/v1/models
   
   # Should see: "context_length": 262144
   ```

---

## Performance Issues

### Issue: Very Slow Responses

**Symptoms:**
- Responses take >60 seconds
- Much slower than expected (~6 tokens/sec baseline)

**Diagnosis:**

```powershell
# Check GPU utilization
nvidia-smi

# Check VRAM usage
nvidia-smi --query-gpu=memory.used,memory.total --format=csv

# Run benchmark
python scripts\benchmark_local_model.py --quick
```

**Solutions:**

1. **Ensure GPU is being used:**
   ```powershell
   # During generation:
   # GPU Utilization should be 90-100%
   # VRAM usage should be ~13.2 GB
   ```

2. **Check for thermal throttling:**
   ```powershell
   # GPU temperature should be < 85°C
   nvidia-smi --query-gpu=temperature.gpu --format=csv
   ```
   
   If throttling:
   - Improve case cooling
   - Clean GPU fans
   - Reduce ambient temperature

3. **Close other GPU applications:**
   ```powershell
   # Check what's using GPU
   nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
   
   # Close unnecessary GPU applications
   ```

4. **Verify correct quantization:**
   - Q4_K_M should give ~6 tokens/sec
   - Lower quantization (Q2, Q3) will be slower
   - Check service config for quantization setting

5. **Check for memory swapping:**
   ```powershell
   # System RAM usage
   Get-Counter '\Memory\Available MBytes'
   
   # Should have at least 4GB free
   ```

### Issue: First Request Very Slow

**Symptoms:**
- First request takes 30+ seconds
- Subsequent requests are fast

**This is normal!**

**Explanation:**
- Model loads into VRAM on first request (~20-30 seconds)
- Cached in VRAM for subsequent requests
- This is expected behavior

**Solutions:**

1. **Warm up the model after service start:**
   ```powershell
   # Send a simple request to load model
   curl http://localhost:8085/v1/chat/completions `
     -H "Content-Type: application/json" `
     -d '{"model":"qwen36_27b","messages":[{"role":"user","content":"hi"}],"max_tokens":5}'
   
   # Wait 30 seconds, then use Hermes normally
   ```

2. **Configure service to pre-load model:**
   ```yaml
   # LLM service config
   preload_models:
     - qwen36_27b
   ```

### Issue: Out of Memory Errors

**Symptoms:**
- `CUDA out of memory`
- `RuntimeError: CUDA error: out of memory`
- Service crashes during generation

**Diagnosis:**

```powershell
# Check available VRAM
nvidia-smi --query-gpu=memory.free --format=csv

# Qwen 3.6 27B Q4_K_M requires ~13.2 GB
# Need 16GB+ VRAM total
```

**Solutions:**

1. **Close other GPU applications:**
   ```powershell
   # List GPU processes
   nvidia-smi

   # Close unnecessary ones (browsers, games, etc.)
   ```

2. **Use smaller model variant:**
   ```powershell
   # Try optimized quantization (slightly lower VRAM)
   hermes config set model.model qwen36_27b_otq
   ```

3. **Reduce context size:**
   ```yaml
   # Limit context to reduce VRAM usage
   model:
     context_window: 131072  # Half the default
   ```

4. **Enable offloading (if service supports it):**
   ```yaml
   # LLM service config
   offload_layers: 10  # Offload some layers to system RAM
   ```

---

## Tool Calling Issues

### Issue: Tool Calls Not Working

**Symptoms:**
- Model responds with text instead of calling tools
- Tool calls malformed or ignored

**Diagnosis:**

```powershell
# Test if model supports function calling
curl http://localhost:8085/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d '{
    "model":"qwen36_27b",
    "messages":[{"role":"user","content":"What is the weather?"}],
    "tools":[{
      "type":"function",
      "function":{
        "name":"get_weather",
        "description":"Get weather"
      }
    }]
  }'
```

**Solutions:**

1. **Verify model supports tool calling:**
   - Not all local models support function calling
   - Check model documentation

2. **Use explicit tool prompt:**
   ```
   > Use the terminal tool to list files in the current directory
   ```

3. **Check Hermes logs for tool invocation:**
   ```powershell
   $env:HERMES_LOG_LEVEL = "DEBUG"
   hermes chat -q "List files using terminal tool"
   
   # Look for: "Calling tool: terminal"
   ```

4. **Verify toolsets are enabled:**
   ```yaml
   # ~/.hermes/config.yaml
   enabled_toolsets:
     - terminal
     - file
     - web
   ```

---

## Response Quality Issues

### Issue: Incoherent or Incorrect Responses

**Symptoms:**
- Nonsense responses
- Incorrect code
- Hallucinated information

**Solutions:**

1. **Check temperature setting:**
   ```yaml
   model:
     temperature: 0.2  # Lower = more deterministic
     # temperature: 1.5  # Higher = more creative but less accurate
   ```

2. **Verify correct model is loaded:**
   ```powershell
   # Check service logs
   cat logs\service.log | Select-String "loaded model"
   ```

3. **Test with simple prompt:**
   ```
   > What is 2 + 2?
   ```
   
   Should return "4". If not, model may be corrupted.

4. **Clear service cache and reload:**
   ```powershell
   # Stop service
   Stop-Process -Name "llm-service" -Force

   # Clear cache
   Remove-Item cache\model\* -Recurse -Force

   # Restart service
   .\start-service.ps1
   ```

5. **Re-download model file:**
   - Model file may be corrupted
   - Download fresh copy from source

### Issue: Incomplete Responses

**Symptoms:**
- Responses cut off mid-sentence
- Code snippets incomplete

**Solutions:**

1. **Increase max_output_tokens:**
   ```yaml
   model:
     max_output_tokens: 8192  # Increase from default
   ```

2. **Check for context window issues:**
   ```powershell
   # If prompt + output > context_window, output is truncated
   hermes config get model.context_window
   ```

3. **Reduce prompt size:**
   - Use summarization for large contexts
   - Enable context compression

4. **Check service max_tokens setting:**
   ```yaml
   # LLM service config
   default_max_tokens: 8192  # Service-side limit
   ```

---

## Authentication Issues

### Issue: Unauthorized / 401 Errors

**Symptoms:**
- `401 Unauthorized`
- `API key required`

**Solutions:**

1. **For local services (usually no auth needed):**
   ```powershell
   # Remove API key if set incorrectly
   hermes config unset model.api_key
   ```

2. **If service requires authentication:**
   ```powershell
   # Set in environment
   $env:CUSTOM_API_KEY = "your-key-here"

   # Or in ~/.hermes/.env
   echo "CUSTOM_API_KEY=your-key-here" >> ~/.hermes/.env
   ```

3. **Check service configuration:**
   ```yaml
   # LLM service config
   require_auth: false  # For local development
   ```

---

## Service-Level Issues

### Issue: Service Won't Start

**Symptoms:**
- Service crashes on startup
- Port already in use

**Diagnosis:**

```powershell
# Check if port is in use
Get-NetTCPConnection -LocalPort 8085

# Check service logs
cat logs\service.log

# Look for error messages
```

**Solutions:**

1. **Port already in use:**
   ```powershell
   # Find process using port
   Get-NetTCPConnection -LocalPort 8085 | Select-Object OwningProcess
   
   # Kill process (if safe)
   Stop-Process -Id <PID>
   
   # Or use different port
   # In service config: port: 8086
   # In Hermes: base_url: http://localhost:8086/v1
   ```

2. **Model file not found:**
   ```powershell
   # Check model path in service config
   cat config.yaml

   # Verify model file exists
   Test-Path "K:\models\qwen36_27b\model.gguf"
   ```

3. **Insufficient permissions:**
   ```powershell
   # Run as administrator
   Start-Process powershell -Verb RunAs -ArgumentList "-File .\start-service.ps1"
   ```

### Issue: Service Crashes During Generation

**Symptoms:**
- Service stops responding mid-generation
- Connection drops during request

**Diagnosis:**

```powershell
# Check system event logs
Get-EventLog -LogName Application -Newest 10 -EntryType Error

# Check service logs
cat logs\service.log | Select-Object -Last 50
```

**Solutions:**

1. **Out of memory:**
   - Check VRAM usage (nvidia-smi)
   - Check RAM usage (Task Manager)
   - Reduce concurrent requests

2. **GPU driver crash:**
   ```powershell
   # Update GPU drivers
   # Download from NVIDIA/AMD website
   
   # Verify driver version
   nvidia-smi
   ```

3. **Corrupted model cache:**
   ```powershell
   # Clear cache
   Remove-Item cache\* -Recurse -Force
   
   # Restart service
   .\start-service.ps1
   ```

---

## Platform-Specific Issues

### Windows-Specific

**Issue: PowerShell execution policy error**

```powershell
# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Issue: Path with spaces causing issues**

```powershell
# Use quotes around paths
cd "C:\Program Files\LLM Service"
```

**Issue: Long path names (>260 chars)**

```powershell
# Enable long path support
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
  -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
```

### Linux-Specific

**Issue: Permission denied**

```bash
# Make scripts executable
chmod +x start-service.sh
chmod +x scripts/*.py

# Run with correct permissions
sudo ./start-service.sh
```

**Issue: CUDA not found**

```bash
# Verify CUDA installation
nvidia-smi

# Add to PATH if needed
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

---

## Diagnostic Procedures

### Complete Health Check

Run this comprehensive diagnostic:

```powershell
# 1. Service health
Write-Host "=== Service Health ==="
curl http://localhost:8085/v1/health

# 2. Model availability
Write-Host "`n=== Available Models ==="
curl http://localhost:8085/v1/models

# 3. Preflight check
Write-Host "`n=== Preflight Check ==="
python scripts\qwen27b_preflight.py

# 4. Hermes configuration
Write-Host "`n=== Hermes Configuration ==="
hermes config list

# 5. GPU status
Write-Host "`n=== GPU Status ==="
nvidia-smi

# 6. Test completion
Write-Host "`n=== Test Completion ==="
hermes chat -q "What is 2+2?"
```

### Performance Profiling

```powershell
# Run comprehensive benchmark
python scripts\benchmark_local_model.py --output profile.json

# Analyze results
cat profile.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Compare against baseline:
# - Simple completion: ~15 seconds
# - Tokens/second: ~6 tok/s
# - VRAM usage: ~13.2 GB
```

---

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `Connection refused` | Service not running | Start LLM service |
| `Model not found` | Wrong model name | Check `/models` endpoint |
| `Context length exceeded` | Prompt too large | Reduce context or enable compression |
| `CUDA out of memory` | Insufficient VRAM | Close GPU apps or use smaller model |
| `Timeout` | Request taking too long | Increase timeout or check GPU |
| `401 Unauthorized` | Auth mismatch | Check API key configuration |
| `400 Bad Request` | Invalid payload | Check request format |
| `500 Internal Server Error` | Service crash | Check service logs |

---

## Getting Additional Help

If you're still experiencing issues:

1. **Collect diagnostic information:**
   ```powershell
   # Run full diagnostic
   python scripts\qwen27b_preflight.py --json-out diagnostic.json
   
   # Collect logs
   hermes --log-level DEBUG > hermes.log 2>&1
   
   # GPU information
   nvidia-smi > gpu-info.txt
   ```

2. **Check existing issues:**
   - [Hermes Agent Issues](https://github.com/NousResearch/hermes-agent/issues)
   - Search for your error message

3. **Create new issue with:**
   - Error message
   - Diagnostic output
   - Hermes version: `hermes --version`
   - Python version: `python --version`
   - OS: `Windows 11 / Ubuntu 22.04 / etc`
   - GPU: `RTX 3090 / etc`

4. **Join community:**
   - [Discord Server](https://discord.gg/nous-research)
   - Ask in #help channel

---

## Additional Resources

- **Quick Start Guide**: [local-llm-setup-qwen.md](./local-llm-setup-qwen.md)
- **Testing Guide**: [Local Model Testing Guide](../../docs/testing/local-model-testing-guide.md)
- **Development Workflow**: [Local Development Workflow](../../docs/developer-guide/local-development-workflow.md)
- **Preflight Script**: [`scripts/qwen27b_preflight.py`](https://github.com/NousResearch/hermes-agent/blob/main/scripts/qwen27b_preflight.py)
