#!/usr/bin/env python3
"""
Name: scripts/benchmark_local_model.py
Description: Comprehensive performance benchmarking for local LLM endpoints with Hermes Agent workloads.
Primary Functions:
  - Measure completion latency and throughput
  - Test context window scaling behavior
  - Validate tool-calling performance
  - Generate detailed performance reports
Revision: 0.1.1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

import requests

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class BenchmarkConfig:
    """Configuration for benchmark run."""
    base_url: str
    model: str
    api_key: str
    timeout: float
    quick_mode: bool
    context_sizes: list[int] = field(default_factory=lambda: [1000, 5000, 10000])
    num_iterations: int = 3


@dataclass
class LatencyMetrics:
    """Latency measurements for a single test."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    tokens_per_second: float
    time_to_first_token_ms: Optional[float] = None


@dataclass
class BenchmarkResult:
    """Complete benchmark results."""
    timestamp: str
    config: dict[str, Any]
    simple_completion: Optional[LatencyMetrics] = None
    tool_calling: Optional[LatencyMetrics] = None
    context_scaling: list[dict[str, Any]] = field(default_factory=list)
    multi_turn: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _headers(api_key: str) -> dict[str, str]:
    """Build request headers with optional authentication."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _safe_request(
    method: str,
    url: str,
    headers: dict[str, str],
    json_data: Optional[dict[str, Any]],
    timeout: float,
) -> tuple[bool, Optional[dict[str, Any]], Optional[str]]:
    """Make HTTP request with error handling."""
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=timeout)
        else:
            response = requests.post(url, headers=headers, json=json_data, timeout=timeout)
        
        response.raise_for_status()
        return True, response.json(), None
    except Exception as exc:
        return False, None, str(exc)


def benchmark_simple_completion(config: BenchmarkConfig) -> Optional[LatencyMetrics]:
    """Benchmark basic chat completion with minimal context."""
    print("  Running simple completion benchmark...")
    
    url = f"{config.base_url}/chat/completions"
    headers = _headers(config.api_key)
    
    prompt = "Explain in 50 words what a binary search tree is and its time complexity."
    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150,
        "temperature": 0.2,
    }
    
    latencies = []
    
    for i in range(config.num_iterations):
        print(f"    Iteration {i+1}/{config.num_iterations}...", end="", flush=True)
        
        start = time.perf_counter()
        success, data, error = _safe_request("POST", url, headers, payload, config.timeout)
        latency_ms = (time.perf_counter() - start) * 1000.0
        
        if not success:
            print(f" FAILED: {error}")
            continue
        
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        tokens_per_second = completion_tokens / (latency_ms / 1000.0) if latency_ms > 0 else 0
        
        latencies.append(LatencyMetrics(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            tokens_per_second=round(tokens_per_second, 2),
        ))
        
        print(f" {latency_ms:.0f}ms, {tokens_per_second:.1f} tok/s")
    
    if not latencies:
        return None
    
    # Return median result
    latencies.sort(key=lambda x: x.latency_ms)
    return latencies[len(latencies) // 2]


def benchmark_tool_calling(config: BenchmarkConfig) -> Optional[LatencyMetrics]:
    """Benchmark chat completion with tool calling overhead."""
    print("  Running tool calling benchmark...")
    
    url = f"{config.base_url}/chat/completions"
    headers = _headers(config.api_key)
    
    # Simulate tool-calling scenario
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"},
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
    ]
    
    prompt = "What's the weather like in San Francisco?"
    payload = {
        "model": config.model,
        "messages": [{"role": "user", "content": prompt}],
        "tools": tools,
        "max_tokens": 150,
        "temperature": 0.2,
    }
    
    latencies = []
    
    for i in range(config.num_iterations):
        print(f"    Iteration {i+1}/{config.num_iterations}...", end="", flush=True)
        
        start = time.perf_counter()
        success, data, error = _safe_request("POST", url, headers, payload, config.timeout)
        latency_ms = (time.perf_counter() - start) * 1000.0
        
        if not success:
            print(f" FAILED: {error}")
            continue
        
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        
        tokens_per_second = completion_tokens / (latency_ms / 1000.0) if latency_ms > 0 else 0
        
        latencies.append(LatencyMetrics(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(latency_ms, 2),
            tokens_per_second=round(tokens_per_second, 2),
        ))
        
        print(f" {latency_ms:.0f}ms, {tokens_per_second:.1f} tok/s")
    
    if not latencies:
        return None
    
    latencies.sort(key=lambda x: x.latency_ms)
    return latencies[len(latencies) // 2]


def benchmark_context_scaling(config: BenchmarkConfig) -> list[dict[str, Any]]:
    """Benchmark latency scaling with increasing context size."""
    print("  Running context scaling benchmark...")
    
    url = f"{config.base_url}/chat/completions"
    headers = _headers(config.api_key)
    
    results = []
    
    for context_size in config.context_sizes:
        print(f"    Testing {context_size} token context...", end="", flush=True)
        
        # Generate synthetic context (rough estimate: ~4 chars per token)
        filler_text = "The quick brown fox jumps over the lazy dog. " * (context_size // 10)
        prompt = f"{filler_text}\n\nSummarize the above text in one sentence."
        
        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 50,
            "temperature": 0.2,
        }
        
        start = time.perf_counter()
        success, data, error = _safe_request("POST", url, headers, payload, config.timeout * 3)
        latency_ms = (time.perf_counter() - start) * 1000.0
        
        if not success:
            print(f" FAILED: {error}")
            results.append({
                "target_context_tokens": context_size,
                "actual_prompt_tokens": None,
                "latency_ms": None,
                "tokens_per_second": None,
                "error": error,
            })
            continue
        
        usage = data.get("usage", {})
        actual_prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        tokens_per_second = completion_tokens / (latency_ms / 1000.0) if latency_ms > 0 else 0
        
        result = {
            "target_context_tokens": context_size,
            "actual_prompt_tokens": actual_prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": round(latency_ms, 2),
            "tokens_per_second": round(tokens_per_second, 2),
            "error": None,
        }
        
        results.append(result)
        print(f" {latency_ms:.0f}ms ({actual_prompt_tokens} actual tokens)")
    
    return results


def benchmark_multi_turn(config: BenchmarkConfig) -> list[dict[str, Any]]:
    """Benchmark multi-turn conversation with accumulating history."""
    print("  Running multi-turn conversation benchmark...")
    
    url = f"{config.base_url}/chat/completions"
    headers = _headers(config.api_key)
    
    messages = []
    results = []
    
    turns = [
        "What is a linked list?",
        "How does it differ from an array?",
        "What are the time complexities for insertion and deletion?",
        "Give me a Python implementation.",
    ]
    
    for turn_num, user_prompt in enumerate(turns, 1):
        print(f"    Turn {turn_num}/{len(turns)}...", end="", flush=True)
        
        messages.append({"role": "user", "content": user_prompt})
        
        payload = {
            "model": config.model,
            "messages": messages,
            "max_tokens": 150,
            "temperature": 0.2,
        }
        
        start = time.perf_counter()
        success, data, error = _safe_request("POST", url, headers, payload, config.timeout)
        latency_ms = (time.perf_counter() - start) * 1000.0
        
        if not success:
            print(f" FAILED: {error}")
            results.append({
                "turn": turn_num,
                "history_length": len(messages),
                "prompt_tokens": None,
                "latency_ms": None,
                "error": error,
            })
            break
        
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        # Add assistant response to history
        assistant_message = data.get("choices", [{}])[0].get("message", {})
        if assistant_message:
            messages.append(assistant_message)
        
        tokens_per_second = completion_tokens / (latency_ms / 1000.0) if latency_ms > 0 else 0
        
        result = {
            "turn": turn_num,
            "history_length": len(messages) - 1,  # Exclude current turn
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": round(latency_ms, 2),
            "tokens_per_second": round(tokens_per_second, 2),
            "error": None,
        }
        
        results.append(result)
        print(f" {latency_ms:.0f}ms ({prompt_tokens} prompt tokens)")
    
    return results


def run_benchmark(config: BenchmarkConfig) -> BenchmarkResult:
    """Run complete benchmark suite."""
    from datetime import datetime
    
    result = BenchmarkResult(
        timestamp=datetime.now().isoformat(),
        config={
            "base_url": config.base_url,
            "model": config.model,
            "quick_mode": config.quick_mode,
            "num_iterations": config.num_iterations,
        },
    )
    
    print("\nStarting benchmark suite...")
    print(f"Model: {config.model}")
    print(f"Endpoint: {config.base_url}")
    print(f"Iterations: {config.num_iterations}")
    print()
    
    # 1. Simple completion
    print("1. Simple Completion Benchmark")
    try:
        result.simple_completion = benchmark_simple_completion(config)
    except Exception as exc:
        error_msg = f"Simple completion benchmark failed: {exc}"
        result.errors.append(error_msg)
        print(f"  ERROR: {error_msg}")
    
    # 2. Tool calling (skip in quick mode)
    if not config.quick_mode:
        print("\n2. Tool Calling Benchmark")
        try:
            result.tool_calling = benchmark_tool_calling(config)
        except Exception as exc:
            error_msg = f"Tool calling benchmark failed: {exc}"
            result.errors.append(error_msg)
            print(f"  ERROR: {error_msg}")
    
    # 3. Context scaling (reduced in quick mode)
    print("\n3. Context Scaling Benchmark")
    try:
        if config.quick_mode:
            config.context_sizes = [1000, 10000]
        result.context_scaling = benchmark_context_scaling(config)
    except Exception as exc:
        error_msg = f"Context scaling benchmark failed: {exc}"
        result.errors.append(error_msg)
        print(f"  ERROR: {error_msg}")
    
    # 4. Multi-turn (skip in quick mode)
    if not config.quick_mode:
        print("\n4. Multi-turn Conversation Benchmark")
        try:
            result.multi_turn = benchmark_multi_turn(config)
        except Exception as exc:
            error_msg = f"Multi-turn benchmark failed: {exc}"
            result.errors.append(error_msg)
            print(f"  ERROR: {error_msg}")
    
    return result


def print_summary(result: BenchmarkResult) -> None:
    """Print human-readable summary of benchmark results."""
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"Timestamp: {result.timestamp}")
    print(f"Model: {result.config['model']}")
    print(f"Endpoint: {result.config['base_url']}")
    print()
    
    if result.simple_completion:
        print("Simple Completion:")
        print(f"  Latency:     {result.simple_completion.latency_ms:.0f} ms")
        print(f"  Throughput:  {result.simple_completion.tokens_per_second:.1f} tokens/sec")
        print(f"  Tokens:      {result.simple_completion.prompt_tokens} prompt, "
              f"{result.simple_completion.completion_tokens} completion")
        print()
    
    if result.tool_calling:
        print("Tool Calling:")
        print(f"  Latency:     {result.tool_calling.latency_ms:.0f} ms")
        print(f"  Throughput:  {result.tool_calling.tokens_per_second:.1f} tokens/sec")
        if result.simple_completion:
            print(f"  Overhead:    {result.tool_calling.latency_ms - result.simple_completion.latency_ms:.0f} ms "
                  f"vs simple completion")
        print()
    
    if result.context_scaling:
        print("Context Scaling:")
        print(f"  {'Context Size':<15} {'Actual Tokens':<15} {'Latency':<12} {'Throughput':<12}")
        print(f"  {'-'*14} {'-'*14} {'-'*11} {'-'*11}")
        for r in result.context_scaling:
            if r["latency_ms"]:
                print(f"  {r['target_context_tokens']:<15} "
                      f"{r['actual_prompt_tokens']:<15} "
                      f"{r['latency_ms']:<11.0f}ms "
                      f"{r['tokens_per_second']:<11.1f}tok/s")
            else:
                print(f"  {r['target_context_tokens']:<15} FAILED: {r['error']}")
        print()
    
    if result.multi_turn:
        print("Multi-turn Conversation:")
        print(f"  {'Turn':<8} {'History':<10} {'Prompt Tokens':<15} {'Latency':<12} {'Throughput':<12}")
        print(f"  {'-'*7} {'-'*9} {'-'*14} {'-'*11} {'-'*11}")
        for r in result.multi_turn:
            if r["latency_ms"]:
                print(f"  {r['turn']:<8} "
                      f"{r['history_length']:<10} "
                      f"{r['prompt_tokens']:<15} "
                      f"{r['latency_ms']:<11.0f}ms "
                      f"{r['tokens_per_second']:<11.1f}tok/s")
            else:
                print(f"  {r['turn']:<8} FAILED: {r['error']}")
        print()
    
    if result.errors:
        print("ERRORS:")
        for error in result.errors:
            print(f"  - {error}")
        print()
    
    print("=" * 70)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Benchmark local LLM model performance with Hermes Agent workloads"
    )
    
    parser.add_argument(
        "--base-url",
        default=os.getenv("QWEN27B_BASE_URL", "http://localhost:8000/v1"),
        help="OpenAI-compatible endpoint base URL",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("QWEN27B_MODEL", "qwen36_27b"),
        help="Model ID to benchmark",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("QWEN27B_API_KEY", ""),
        help="API key for authentication (if required)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick benchmark (fewer tests, faster)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations for latency tests",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output file for JSON results",
    )
    
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point."""
    args = parse_args(argv or sys.argv[1:])
    
    config = BenchmarkConfig(
        base_url=args.base_url.rstrip("/"),
        model=args.model.strip(),
        api_key=args.api_key.strip(),
        timeout=args.timeout,
        quick_mode=args.quick,
        num_iterations=args.iterations,
    )
    
    # Run benchmarks
    result = run_benchmark(config)
    
    # Print summary
    print_summary(result)
    
    # Save JSON output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, indent=2)
        
        print(f"\nFull results saved to: {args.output}")
    
    # Return error code if any benchmark failed
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
