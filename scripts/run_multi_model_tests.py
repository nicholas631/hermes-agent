#!/usr/bin/env python3
"""
Name: scripts/run_multi_model_tests.py
Description: Sequential test runner for multiple models with memory safety and comprehensive reporting.
Primary Functions:
  - Run preflight, benchmark, and integration tests for multiple models
  - Force-unload models between tests to prevent VRAM accumulation
  - Monitor memory usage with configurable thresholds
  - Generate per-model and summary reports
Revision: 0.1.1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests


@dataclass
class TestResult:
    """Results for a single test type."""
    status: str  # "passed", "failed", "aborted", "skipped"
    exit_code: Optional[int]
    duration_seconds: float
    output_file: Optional[str]
    error_message: Optional[str] = None


@dataclass
class ModelTestResults:
    """Complete test results for one model."""
    model: str
    start_time: str
    end_time: str
    duration_seconds: float
    status: str  # "passed", "failed", "aborted"
    preflight: Optional[TestResult] = None
    benchmark: Optional[TestResult] = None
    integration: Optional[TestResult] = None
    memory_peak_vram_gb: float = 0.0
    memory_peak_ram_percent: float = 0.0
    memory_overflow: bool = False
    error_message: Optional[str] = None


@dataclass
class SummaryReport:
    """Summary report for all models tested."""
    test_suite: str
    timestamp: str
    base_url: str
    vram_threshold_gb: float
    ram_threshold_percent: float
    models_tested: int
    models_passed: int
    models_failed: int
    models_aborted: int
    total_duration_seconds: float
    results: list[ModelTestResults] = field(default_factory=list)


def force_unload_models(base_url: str, timeout: float = 10.0) -> bool:
    """
    Force unload all models from GPU.
    
    Args:
        base_url: Service base URL (e.g., http://localhost:8000/v1)
        timeout: Request timeout in seconds
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Remove /v1 suffix if present to get base URL for admin endpoint
        admin_base = base_url.replace("/v1", "")
        response = requests.post(
            f"{admin_base}/v1/admin/force-unload",
            json={},
            timeout=timeout
        )
        response.raise_for_status()
        print("✓ Models unloaded successfully")
        return True
    except Exception as exc:
        print(f"WARNING: Failed to force-unload models: {exc}")
        return False


def wait_with_progress(seconds: int, message: str = "Waiting"):
    """Wait with progress indicator."""
    print(f"{message}...", end="", flush=True)
    for i in range(seconds):
        time.sleep(1)
        print(".", end="", flush=True)
    print(" done")


def run_test_with_monitoring(
    test_name: str,
    command: list[str],
    output_dir: Path,
    model: str,
    vram_threshold: float,
    ram_threshold: float,
    timeout: Optional[float] = None,
    env: Optional[dict] = None
) -> TestResult:
    """
    Run a single test with memory monitoring.
    
    Args:
        test_name: Test name (preflight, benchmark, integration)
        command: Command to execute
        output_dir: Directory for output files
        model: Model being tested
        vram_threshold: VRAM threshold in GB
        ram_threshold: RAM threshold percentage
        timeout: Optional timeout in seconds
        env: Optional environment variables dict for subprocess
        
    Returns:
        TestResult with status and metrics
    """
    print(f"\n{'='*70}")
    print(f"Running {test_name} for {model}")
    print(f"{'='*70}")
    
    start_time = time.time()
    output_file = output_dir / f"{model}_{test_name}.json"
    memory_file = output_dir / f"{model}_{test_name}_memory.json"
    
    # Build monitored command
    monitor_cmd = [
        sys.executable,
        str(Path(__file__).parent / "monitor_test_memory.py"),
        f"--vram-threshold={vram_threshold}",
        f"--ram-threshold={ram_threshold}",
        f"--output={memory_file}",
    ]
    
    # Add timeout to the actual test command if specified
    full_command = monitor_cmd + ["--"] + command
    
    try:
        result = subprocess.run(
            full_command,
            capture_output=False,  # Let output stream through
            timeout=timeout,
            env=env,
        )
        
        duration = time.time() - start_time
        
        # Check memory report for overflow
        memory_overflow = False
        peak_vram = 0.0
        peak_ram = 0.0
        
        if memory_file.exists():
            with open(memory_file, "r") as f:
                memory_data = json.load(f)
                memory_overflow = memory_data.get("aborted", False)
                peak_vram = memory_data.get("peak_vram_gb", 0.0)
                peak_ram = memory_data.get("peak_ram_percent", 0.0)
        
        # Determine status
        if result.returncode == 2:  # Memory threshold violation
            status = "aborted"
            error = "Memory threshold exceeded"
        elif result.returncode != 0:
            status = "failed"
            error = f"Exit code {result.returncode}"
        else:
            status = "passed"
            error = None
        
        return TestResult(
            status=status,
            exit_code=result.returncode,
            duration_seconds=round(duration, 1),
            output_file=str(output_file) if output_file.exists() else None,
            error_message=error
        )
        
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return TestResult(
            status="failed",
            exit_code=None,
            duration_seconds=round(duration, 1),
            output_file=None,
            error_message=f"Timeout after {timeout}s"
        )
    except Exception as exc:
        duration = time.time() - start_time
        return TestResult(
            status="failed",
            exit_code=None,
            duration_seconds=round(duration, 1),
            output_file=None,
            error_message=str(exc)
        )


def test_model(
    model: str,
    base_url: str,
    output_dir: Path,
    vram_threshold: float,
    ram_threshold: float,
    skip_integration: bool = False
) -> ModelTestResults:
    """
    Run complete test suite for a single model.
    
    Args:
        model: Model name
        base_url: Service base URL
        output_dir: Output directory for results
        vram_threshold: VRAM threshold in GB
        ram_threshold: RAM threshold percentage
        skip_integration: Skip integration tests
        
    Returns:
        ModelTestResults with all test outcomes
    """
    print(f"\n{'#'*70}")
    print(f"# TESTING MODEL: {model}")
    print(f"{'#'*70}")
    
    start_time = datetime.now()
    model_results = ModelTestResults(
        model=model,
        start_time=start_time.isoformat(),
        end_time="",
        duration_seconds=0.0,
        status="in_progress"
    )
    
    # 1. Force unload any loaded models
    print("\n1. Unloading previous models...")
    force_unload_models(base_url)
    wait_with_progress(10, "Waiting for GPU cleanup")
    
    # 2. Run preflight check
    print("\n2. Running preflight check...")
    preflight_cmd = [
        sys.executable,
        str(Path(__file__).parent / "qwen27b_preflight.py"),
        "--base-url", base_url,
        "--model", model,
        "--json-out", str(output_dir / f"{model}_preflight.json"),
    ]
    
    model_results.preflight = run_test_with_monitoring(
        "preflight",
        preflight_cmd,
        output_dir,
        model,
        vram_threshold,
        ram_threshold,
        timeout=120
    )
    
    if model_results.preflight.status == "aborted":
        end_time = datetime.now()
        model_results.end_time = end_time.isoformat()
        model_results.duration_seconds = round((end_time - start_time).total_seconds(), 1)
        model_results.status = "aborted"
        model_results.error_message = "Aborted during preflight due to memory overflow"
        model_results.memory_overflow = True
        force_unload_models(base_url)
        return model_results
    
    # 3. Run benchmark suite
    print("\n3. Running benchmark suite...")
    benchmark_cmd = [
        sys.executable,
        str(Path(__file__).parent / "benchmark_local_model.py"),
        "--base-url", base_url,
        "--model", model,
        "--quick",  # Use quick mode for safety
        "--output", str(output_dir / f"{model}_benchmark.json"),
    ]
    
    model_results.benchmark = run_test_with_monitoring(
        "benchmark",
        benchmark_cmd,
        output_dir,
        model,
        vram_threshold,
        ram_threshold,
        timeout=600
    )
    
    if model_results.benchmark.status == "aborted":
        end_time = datetime.now()
        model_results.end_time = end_time.isoformat()
        model_results.duration_seconds = round((end_time - start_time).total_seconds(), 1)
        model_results.status = "aborted"
        model_results.error_message = "Aborted during benchmark due to memory overflow"
        model_results.memory_overflow = True
        force_unload_models(base_url)
        return model_results
    
    # 4. Run integration tests (optional)
    if not skip_integration:
        print("\n4. Running integration tests...")
        integration_cmd = [
            sys.executable,
            "-m", "pytest",
            str(Path(__file__).parent.parent / "tests" / "integration" / "test_local_model_endpoint.py"),
            "-v",
            "--tb=short",
        ]
        
        # Set environment variables for integration tests
        import os
        env = os.environ.copy()
        env["LOCAL_MODEL_TEST_BASE_URL"] = base_url
        env["LOCAL_MODEL_TEST_MODEL"] = model
        
        model_results.integration = run_test_with_monitoring(
            "integration",
            integration_cmd,
            output_dir,
            model,
            vram_threshold,
            ram_threshold,
            timeout=300,
            env=env
        )
        
        if model_results.integration.status == "aborted":
            end_time = datetime.now()
            model_results.end_time = end_time.isoformat()
            model_results.duration_seconds = round((end_time - start_time).total_seconds(), 1)
            model_results.status = "aborted"
            model_results.error_message = "Aborted during integration tests due to memory overflow"
            model_results.memory_overflow = True
            force_unload_models(base_url)
            return model_results
    
    # 5. Unload model
    print("\n5. Unloading model...")
    force_unload_models(base_url)
    wait_with_progress(10, "Waiting for GPU cleanup")
    
    # Calculate final status
    end_time = datetime.now()
    model_results.end_time = end_time.isoformat()
    model_results.duration_seconds = round((end_time - start_time).total_seconds(), 1)
    
    # Determine overall status
    test_results = [model_results.preflight, model_results.benchmark]
    if model_results.integration:
        test_results.append(model_results.integration)
    
    if all(t.status == "passed" for t in test_results if t):
        model_results.status = "passed"
    elif any(t.status == "aborted" for t in test_results if t):
        model_results.status = "aborted"
    else:
        model_results.status = "failed"
    
    # Extract memory metrics from the last memory report
    last_memory_file = output_dir / f"{model}_benchmark_memory.json"
    if last_memory_file.exists():
        with open(last_memory_file, "r") as f:
            memory_data = json.load(f)
            model_results.memory_peak_vram_gb = memory_data.get("peak_vram_gb", 0.0)
            model_results.memory_peak_ram_percent = memory_data.get("peak_ram_percent", 0.0)
    
    print(f"\n✓ Model testing complete: {model_results.status.upper()}")
    return model_results


def generate_summary_report(
    results: list[ModelTestResults],
    base_url: str,
    vram_threshold: float,
    ram_threshold: float,
    output_file: Path
) -> SummaryReport:
    """Generate and save summary report."""
    summary = SummaryReport(
        test_suite="multi_model_comprehensive",
        timestamp=datetime.now().isoformat(),
        base_url=base_url,
        vram_threshold_gb=vram_threshold,
        ram_threshold_percent=ram_threshold,
        models_tested=len(results),
        models_passed=sum(1 for r in results if r.status == "passed"),
        models_failed=sum(1 for r in results if r.status == "failed"),
        models_aborted=sum(1 for r in results if r.status == "aborted"),
        total_duration_seconds=sum(r.duration_seconds for r in results),
        results=results
    )
    
    # Save summary
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(asdict(summary), f, indent=2)
    
    # Print summary
    print("\n" + "=" * 70)
    print("MULTI-MODEL TEST SUMMARY")
    print("=" * 70)
    print(f"Models Tested:  {summary.models_tested}")
    print(f"Passed:         {summary.models_passed}")
    print(f"Failed:         {summary.models_failed}")
    print(f"Aborted:        {summary.models_aborted}")
    print(f"Total Duration: {summary.total_duration_seconds:.1f}s")
    print()
    
    for result in results:
        status_symbol = "✓" if result.status == "passed" else "✗"
        print(f"{status_symbol} {result.model}: {result.status.upper()}")
        if result.preflight:
            print(f"   Preflight:   {result.preflight.status}")
        if result.benchmark:
            print(f"   Benchmark:   {result.benchmark.status}")
        if result.integration:
            print(f"   Integration: {result.integration.status}")
        print(f"   Peak VRAM:   {result.memory_peak_vram_gb:.2f} GB")
        print(f"   Peak RAM:    {result.memory_peak_ram_percent:.1f}%")
        if result.error_message:
            print(f"   Error:       {result.error_message}")
        print()
    
    print("=" * 70)
    print(f"Summary report saved to: {output_file}")
    
    return summary


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run comprehensive tests on multiple models with memory safety"
    )
    
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000/v1",
        help="Service base URL (default: http://localhost:8000/v1)"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Model names to test (e.g., qwen36_27b qwen36_35b_a3b)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("test_results"),
        help="Output directory for results (default: test_results)"
    )
    parser.add_argument(
        "--vram-threshold",
        type=float,
        default=23.0,
        help="VRAM threshold in GB (default: 23.0)"
    )
    parser.add_argument(
        "--ram-threshold",
        type=float,
        default=90.0,
        help="System RAM threshold percentage (default: 90.0)"
    )
    parser.add_argument(
        "--skip-integration",
        action="store_true",
        help="Skip integration tests"
    )
    
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point."""
    args = parse_args(argv or sys.argv[1:])
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("MULTI-MODEL TEST SUITE")
    print("=" * 70)
    print(f"Base URL:        {args.base_url}")
    print(f"Models:          {', '.join(args.models)}")
    print(f"Output Dir:      {args.output_dir}")
    print(f"VRAM Threshold:  {args.vram_threshold} GB")
    print(f"RAM Threshold:   {args.ram_threshold}%")
    print(f"Skip Integration: {args.skip_integration}")
    print("=" * 70)
    
    # Test each model sequentially
    all_results = []
    
    for model in args.models:
        try:
            result = test_model(
                model=model,
                base_url=args.base_url,
                output_dir=args.output_dir,
                vram_threshold=args.vram_threshold,
                ram_threshold=args.ram_threshold,
                skip_integration=args.skip_integration
            )
            all_results.append(result)
            
            # If aborted, stop testing remaining models
            if result.status == "aborted":
                print(f"\nWARNING: Test suite aborted after {model} due to memory overflow")
                break
                
        except KeyboardInterrupt:
            print("\n\nTest suite interrupted by user")
            break
        except Exception as exc:
            print(f"\nWARNING: Unexpected error testing {model}: {exc}")
            # Continue with next model
    
    # Generate summary report
    summary_file = args.output_dir / "summary_report.json"
    summary = generate_summary_report(
        results=all_results,
        base_url=args.base_url,
        vram_threshold=args.vram_threshold,
        ram_threshold=args.ram_threshold,
        output_file=summary_file
    )
    
    # Return exit code based on results
    if summary.models_aborted > 0:
        return 2  # Memory overflow
    elif summary.models_failed > 0:
        return 1  # Test failures
    return 0  # All passed


if __name__ == "__main__":
    sys.exit(main())
