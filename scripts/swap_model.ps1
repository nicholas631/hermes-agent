#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Quick model swapper for Hermes Agent
    
.DESCRIPTION
    Easily switch between baseline and MTP models for the local LLM service.
    Updates Hermes configuration and validates the model is available.
    
.PARAMETER Model
    Target model to switch to. Supported values:
    - 27b, 27b-base, qwen36_27b (baseline 27B)
    - 27b-mtp, qwen36_27b_mtp (27B MTP draft_n=2)
    - 27b-mtp1, qwen36_27b_mtp_draft1 (27B MTP draft_n=1)
    - 35b, 35b-base, qwen36_35b_a3b (baseline 35B-A3B)
    - 35b-mtp, qwen36_35b_a3b_mtp (35B-A3B MTP draft_n=2)
    - 35b-mtp1, qwen36_35b_a3b_mtp_draft1 (35B-A3B MTP draft_n=1)
    
.PARAMETER BaseUrl
    LLM service base URL (default: http://localhost:8085/v1)
    
.PARAMETER Verify
    Verify the model is available before switching (default: true)
    
.PARAMETER ShowInfo
    Display detailed model information after switching
    
.EXAMPLE
    .\swap_model.ps1 27b-mtp
    Switch to Qwen 3.6 27B MTP model
    
.EXAMPLE
    .\swap_model.ps1 35b-mtp -ShowInfo
    Switch to 35B-A3B MTP and show performance info
    
.EXAMPLE
    .\swap_model.ps1 27b
    Switch back to baseline 27B model
    
.NOTES
    Version: 1.0.0
    Date: 2026-05-14
    Requires: Hermes Agent installed, LLM service running
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Model,
    
    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "http://localhost:8085/v1",
    
    [Parameter(Mandatory=$false)]
    [bool]$Verify = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$ShowInfo
)

# Model mapping
$ModelMap = @{
    # Baseline 27B
    "27b" = "qwen36_27b"
    "27b-base" = "qwen36_27b"
    "qwen36_27b" = "qwen36_27b"
    
    # MTP 27B (draft_n=2)
    "27b-mtp" = "qwen36_27b_mtp"
    "qwen36_27b_mtp" = "qwen36_27b_mtp"
    
    # MTP 27B (draft_n=1)
    "27b-mtp1" = "qwen36_27b_mtp_draft1"
    "qwen36_27b_mtp_draft1" = "qwen36_27b_mtp_draft1"
    
    # Baseline 35B-A3B
    "35b" = "qwen36_35b_a3b"
    "35b-base" = "qwen36_35b_a3b"
    "qwen36_35b_a3b" = "qwen36_35b_a3b"
    
    # MTP 35B-A3B (draft_n=2)
    "35b-mtp" = "qwen36_35b_a3b_mtp"
    "qwen36_35b_a3b_mtp" = "qwen36_35b_a3b_mtp"
    
    # MTP 35B-A3B (draft_n=1)
    "35b-mtp1" = "qwen36_35b_a3b_mtp_draft1"
    "qwen36_35b_a3b_mtp_draft1" = "qwen36_35b_a3b_mtp_draft1"
}

# Model info
$ModelInfo = @{
    "qwen36_27b" = @{
        Name = "Qwen 3.6 27B (Baseline)"
        Speed = "~23 tok/s"
        VRAM = "13.2 GB"
        Context = "262,144 tokens"
        Type = "Baseline"
        Speedup = "N/A"
    }
    "qwen36_27b_mtp" = @{
        Name = "Qwen 3.6 27B MTP (draft_n=2)"
        Speed = "~28 tok/s"
        VRAM = "13.2 GB"
        Context = "65,536 tokens"
        Type = "MTP"
        Speedup = "1.21x (+21%)"
    }
    "qwen36_27b_mtp_draft1" = @{
        Name = "Qwen 3.6 27B MTP (draft_n=1)"
        Speed = "~26 tok/s"
        VRAM = "13.2 GB"
        Context = "65,536 tokens"
        Type = "MTP"
        Speedup = "~1.15x (+15%)"
    }
    "qwen36_35b_a3b" = @{
        Name = "Qwen 3.6 35B-A3B (Baseline)"
        Speed = "~28 tok/s"
        VRAM = "20 GB"
        Context = "131,072 tokens"
        Type = "Baseline"
        Speedup = "N/A"
    }
    "qwen36_35b_a3b_mtp" = @{
        Name = "Qwen 3.6 35B-A3B MTP (draft_n=2)"
        Speed = "~64 tok/s"
        VRAM = "20 GB"
        Context = "32,768 tokens"
        Type = "MTP"
        Speedup = "2.31x (+130%)"
    }
    "qwen36_35b_a3b_mtp_draft1" = @{
        Name = "Qwen 3.6 35B-A3B MTP (draft_n=1)"
        Speed = "~33 tok/s"
        VRAM = "20 GB"
        Context = "32,768 tokens"
        Type = "MTP"
        Speedup = "~1.17x (+17%)"
    }
}

# Resolve model name
$targetModel = $null
if ($ModelMap.ContainsKey($Model.ToLower())) {
    $targetModel = $ModelMap[$Model.ToLower()]
} else {
    Write-Host "[ERROR] Unknown model: $Model" -ForegroundColor Red
    Write-Host "`nSupported models:" -ForegroundColor Yellow
    Write-Host "  Baseline:" -ForegroundColor Cyan
    Write-Host "    27b, qwen36_27b             - Qwen 3.6 27B baseline"
    Write-Host "    35b, qwen36_35b_a3b         - Qwen 3.6 35B-A3B baseline"
    Write-Host ""
    Write-Host "  MTP (Faster):" -ForegroundColor Green
    Write-Host "    27b-mtp                     - 27B MTP draft_n=2 (+21% speed)"
    Write-Host "    27b-mtp1                    - 27B MTP draft_n=1 (+15% speed)"
    Write-Host "    35b-mtp                     - 35B-A3B MTP draft_n=2 (+130% speed)"
    Write-Host "    35b-mtp1                    - 35B-A3B MTP draft_n=1 (+17% speed)"
    exit 1
}

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           Hermes Agent - Model Swap Utility                    ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Get current model
Write-Host "[1/4] Checking current configuration..." -ForegroundColor Yellow
try {
    $currentModel = hermes config get model.model 2>$null
    if ($currentModel -eq $targetModel) {
        Write-Host "      Already using model: $targetModel" -ForegroundColor Green
        Write-Host "      No change needed." -ForegroundColor Gray
        exit 0
    }
    Write-Host "      Current model: $currentModel" -ForegroundColor Gray
} catch {
    Write-Host "      No current model configured" -ForegroundColor Gray
}

# Verify model availability
if ($Verify) {
    Write-Host "[2/4] Verifying model availability..." -ForegroundColor Yellow
    try {
        $modelsUrl = $BaseUrl.TrimEnd('/') + "/models"
        $response = Invoke-RestMethod -Uri $modelsUrl -Method Get -TimeoutSec 5
        $availableModels = $response.data | ForEach-Object { $_.id }
        
        if ($availableModels -contains $targetModel) {
            Write-Host "      [OK] Model '$targetModel' is available" -ForegroundColor Green
        } else {
            Write-Host "      [WARNING] Model '$targetModel' not found in service" -ForegroundColor Red
            Write-Host "      Available models:" -ForegroundColor Gray
            $availableModels | ForEach-Object { Write-Host "        - $_" -ForegroundColor Gray }
            Write-Host ""
            $continue = Read-Host "      Continue anyway? (y/N)"
            if ($continue -ne "y" -and $continue -ne "Y") {
                Write-Host "[ABORTED] Model swap cancelled" -ForegroundColor Red
                exit 1
            }
        }
    } catch {
        Write-Host "      [WARNING] Could not verify model (service may be down)" -ForegroundColor Yellow
        Write-Host "      Error: $($_.Exception.Message)" -ForegroundColor Gray
        Write-Host ""
        $continue = Read-Host "      Continue anyway? (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            Write-Host "[ABORTED] Model swap cancelled" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "[2/4] Skipping verification (--Verify=`$false)" -ForegroundColor Gray
}

# Update Hermes config
Write-Host "[3/4] Updating Hermes configuration..." -ForegroundColor Yellow
try {
    hermes config set model.provider custom | Out-Null
    hermes config set model.base_url $BaseUrl | Out-Null
    hermes config set model.model $targetModel | Out-Null
    Write-Host "      [OK] Configuration updated successfully" -ForegroundColor Green
} catch {
    Write-Host "      [ERROR] Failed to update configuration" -ForegroundColor Red
    Write-Host "      Error: $($_.Exception.Message)" -ForegroundColor Gray
    exit 1
}

# Verify new config
Write-Host "[4/4] Verifying new configuration..." -ForegroundColor Yellow
try {
    $newModel = hermes config get model.model
    if ($newModel -eq $targetModel) {
        Write-Host "      [OK] Model switched to: $newModel" -ForegroundColor Green
    } else {
        Write-Host "      [ERROR] Verification failed (got: $newModel)" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "      [ERROR] Could not verify new configuration" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    Model Swap Successful!                      ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green

# Show model info
if ($ShowInfo -or $ModelInfo.ContainsKey($targetModel)) {
    $info = $ModelInfo[$targetModel]
    Write-Host ""
    Write-Host "Model Information:" -ForegroundColor Cyan
    Write-Host "  Name:       $($info.Name)" -ForegroundColor White
    Write-Host "  Type:       $($info.Type)" -ForegroundColor White
    Write-Host "  Speed:      $($info.Speed)" -ForegroundColor White
    Write-Host "  VRAM:       $($info.VRAM)" -ForegroundColor White
    Write-Host "  Context:    $($info.Context)" -ForegroundColor White
    if ($info.Type -eq "MTP") {
        Write-Host "  Speedup:    $($info.Speedup)" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Test the model:" -ForegroundColor Gray
Write-Host "     hermes" -ForegroundColor White
Write-Host ""
Write-Host "  2. Run benchmark:" -ForegroundColor Gray
Write-Host "     python scripts\benchmark_local_model.py --model $targetModel" -ForegroundColor White
Write-Host ""
Write-Host "  3. Switch back:" -ForegroundColor Gray
if ($targetModel -like "*mtp*") {
    $baseModel = $targetModel -replace "_mtp(_draft1)?", ""
    Write-Host "     .\scripts\swap_model.ps1 $($baseModel.Replace('qwen36_', ''))" -ForegroundColor White
} else {
    $mtpModel = "${targetModel}_mtp"
    Write-Host "     .\scripts\swap_model.ps1 $($mtpModel.Replace('qwen36_', ''))" -ForegroundColor White
}
Write-Host ""

exit 0
