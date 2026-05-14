#!/usr/bin/env python3
"""
Name: scripts/benchmark_local_models.py
Description: Performance benchmarking for multiple models from LLM Local Model Service.
Primary Functions:
  - Run standardized prompts across multiple models.
  - Measure TTFT, completion time, tokens/sec, and quality.
  - Generate comparison reports with tables and detailed JSON results.
Revision: 0.1.0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import requests


DEFAULT_BASE_URL = os.getenv("LLM_SERVICE_BASE_URL", "http://127.0.0.1:8085/v1").rstrip("/")
DEFAULT_API_KEY = os.getenv("LLM_SERVICE_API_KEY", "not-needed")
DEFAULT_MODELS = [
    "qwen36_27b",
    "qwen36_27b_mtp",           # NEW: MTP variant (draft_n=2)
    "qwen36_35b_a3b",
    "qwen36_35b_a3b_mtp",       # NEW: MTP variant (draft_n=2)
    "gemma4_31b_iq4_nl",
]

# Benchmark prompts
BENCHMARK_PROMPTS = {
    "code": {
        "name": "Code Generation",
        "prompt": "Write a Python function to validate email addresses using regex, with docstring and type hints.",
        "max_tokens": 256,
    },
    "reasoning": {
        "name": "Logical Reasoning",
        "prompt": "If all Bloops are Razzies and all Razzies are Lazzies, are all Bloops definitely Lazzies? Explain your reasoning step-by-step.",
        "max_tokens": 256,
    },
    "longform": {
        "name": "Long-form Writing",
        "prompt": "Write a 300-word technical explanation of how attention mechanisms work in transformer models.",
        "max_tokens": 512,
    },
    "structured": {
        "name": "Structured Output",
        "prompt": "List 5 benefits of automated testing in JSON format with 'benefit' and 'description' fields.",
        "max_tokens": 256,
    },
}


@dataclass
class BenchmarkResult:
    model: str
    task: str
    task_name: str
    success: bool
    time_to_first_token_ms: Optional[float]
    total_completion_time_ms: Optional[float]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]
    total_tokens: Optional[int]
    tokens_per_second: Optional[float]
    response_preview: Optional[str]
    full_response: Optional[str]
    error: Optional[str]


@dataclass
class BenchmarkReport:
    base_url: str
    timestamp: str
    models_tested: list[str]
    tasks_run: list[str]
    results: list[BenchmarkResult]
    overall_success: bool


def _headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception as exc:
        raise RuntimeError(f"Failed to parse JSON response: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected JSON payload shape (expected object).")
    return payload


def _run_benchmark_task(
    base_url: str,
    model_id: str,
    task_id: str,
    task_config: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
) -> BenchmarkResult:
    """Run a single benchmark task for a model."""
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": task_config["prompt"]}],
        "max_tokens": task_config["max_tokens"],
        "temperature": 0.2,
    }

    # Measure time to first token and total time
    started = time.perf_counter()
    ttft = None
    
    try:
        # For non-streaming, we can't measure TTFT separately, so we approximate
        response = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
        first_byte_time = time.perf_counter()
        response.raise_for_status()
        body = _safe_json(response)
        completed = time.perf_counter()
        
        # Approximate TTFT as time to first byte
        ttft = round((first_byte_time - started) * 1000.0, 2)
        total_time = round((completed - started) * 1000.0, 2)
        
    except Exception as exc:
        return BenchmarkResult(
            model=model_id,
            task=task_id,
            task_name=task_config["name"],
            success=False,
            time_to_first_token_ms=None,
            total_completion_time_ms=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            tokens_per_second=None,
            response_preview=None,
            full_response=None,
            error=f"Request failed: {exc}",
        )

    # Extract response data
    usage = body.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")

    tokens_per_second = None
    if completion_tokens and total_time > 0:
        tokens_per_second = round(completion_tokens / (total_time / 1000.0), 2)

    full_response = None
    preview = None
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    full_response = content.strip()
                    preview = full_response.replace("\n", " ")[:160]

    return BenchmarkResult(
        model=model_id,
        task=task_id,
        task_name=task_config["name"],
        success=True,
        time_to_first_token_ms=ttft,
        total_completion_time_ms=total_time,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        tokens_per_second=tokens_per_second,
        response_preview=preview,
        full_response=full_response,
        error=None,
    )


def run_benchmarks(
    base_url: str,
    model_ids: list[str],
    api_key: str,
    timeout_seconds: float,
) -> BenchmarkReport:
    """Run all benchmark tasks for all models."""
    headers = _headers(api_key)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    
    results = []
    for model_id in model_ids:
        print(f"Benchmarking model: {model_id}")
        for task_id, task_config in BENCHMARK_PROMPTS.items():
            print(f"  Running task: {task_config['name']}")
            result = _run_benchmark_task(
                base_url,
                model_id,
                task_id,
                task_config,
                headers,
                timeout_seconds,
            )
            results.append(result)
            if result.success:
                print(f"    [OK] Completed in {result.total_completion_time_ms}ms ({result.tokens_per_second} tok/s)")
            else:
                print(f"    [FAIL] Failed: {result.error}")

    overall_success = all(r.success for r in results)
    
    return BenchmarkReport(
        base_url=base_url,
        timestamp=timestamp,
        models_tested=model_ids,
        tasks_run=list(BENCHMARK_PROMPTS.keys()),
        results=results,
        overall_success=overall_success,
    )


def _print_comparison_table(report: BenchmarkReport) -> None:
    """Print a comparison table of results."""
    print("\n" + "=" * 120)
    print("BENCHMARK COMPARISON TABLE")
    print("=" * 120)
    
    # Group results by task
    for task_id, task_config in BENCHMARK_PROMPTS.items():
        print(f"\n{task_config['name']} ({task_id}):")
        print("-" * 120)
        print(f"{'Model':<25} {'Latency (ms)':<15} {'Tok/s':<10} {'Tokens':<10} {'Status':<10}")
        print("-" * 120)
        
        for result in report.results:
            if result.task == task_id:
                status = "[PASS]" if result.success else "[FAIL]"
                latency = f"{result.total_completion_time_ms:.0f}" if result.total_completion_time_ms else "N/A"
                tps = f"{result.tokens_per_second:.1f}" if result.tokens_per_second else "N/A"
                tokens = f"{result.completion_tokens}" if result.completion_tokens else "N/A"
                print(f"{result.model:<25} {latency:<15} {tps:<10} {tokens:<10} {status:<10}")
    
    print("\n" + "=" * 120)


def _print_detailed_report(report: BenchmarkReport) -> None:
    """Print detailed report with all metrics."""
    print("\n" + "=" * 120)
    print("DETAILED BENCHMARK REPORT")
    print("=" * 120)
    print(f"Base URL:         {report.base_url}")
    print(f"Timestamp:        {report.timestamp}")
    print(f"Models tested:    {len(report.models_tested)}")
    print(f"Tasks run:        {len(report.tasks_run)}")
    print(f"Overall success:  {report.overall_success}")
    
    for result in report.results:
        print("\n" + "-" * 120)
        print(f"Model: {result.model}")
        print(f"Task:  {result.task_name} ({result.task})")
        print(f"Success:              {result.success}")
        if result.success:
            print(f"TTFT (ms):            {result.time_to_first_token_ms}")
            print(f"Total time (ms):      {result.total_completion_time_ms}")
            print(f"Prompt tokens:        {result.prompt_tokens}")
            print(f"Completion tokens:    {result.completion_tokens}")
            print(f"Total tokens:         {result.total_tokens}")
            print(f"Tokens/second:        {result.tokens_per_second}")
            print(f"Response preview:     {result.response_preview}")
        else:
            print(f"Error:                {result.error}")
    
    print("\n" + "=" * 120)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark multiple models from LLM Local Model Service")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI-compatible endpoint base URL")
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Model IDs to benchmark (space-separated)",
    )
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Bearer token for endpoint auth")
    parser.add_argument("--timeout", type=float, default=120.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional output path for JSON report",
    )
    parser.add_argument(
        "--output-dir",
        default="results/model_benchmarks",
        help="Output directory for benchmark results",
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Print detailed report in addition to comparison table",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    
    print("=" * 120)
    print("LLM LOCAL MODEL SERVICE BENCHMARK")
    print("=" * 120)
    print(f"Base URL: {args.base_url}")
    print(f"Models:   {', '.join(args.models)}")
    print(f"Tasks:    {len(BENCHMARK_PROMPTS)}")
    print("=" * 120)
    print()
    
    report = run_benchmarks(
        base_url=args.base_url.rstrip("/"),
        model_ids=[m.strip() for m in args.models],
        api_key=args.api_key.strip(),
        timeout_seconds=args.timeout,
    )
    
    # Print comparison table
    _print_comparison_table(report)
    
    # Print detailed report if requested
    if args.detailed:
        _print_detailed_report(report)
    
    # Save JSON report
    if args.json_out:
        json_path = args.json_out
    else:
        # Auto-generate filename with timestamp
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"benchmark_{timestamp}.json"
    
    report_dict = {
        "base_url": report.base_url,
        "timestamp": report.timestamp,
        "models_tested": report.models_tested,
        "tasks_run": report.tasks_run,
        "results": [asdict(r) for r in report.results],
        "overall_success": report.overall_success,
    }
    
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report_dict, handle, indent=2)
    print(f"\nJSON report written to: {json_path}")
    
    return 0 if report.overall_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
