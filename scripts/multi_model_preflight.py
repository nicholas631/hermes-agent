#!/usr/bin/env python3
"""
Name: scripts/multi_model_preflight.py
Description: Repeatable preflight checks for multiple models from LLM Local Model Service.
Primary Functions:
  - Probe OpenAI-compatible /models and /chat/completions endpoints.
  - Validate configured models' availability and completion behavior.
  - Emit human-readable and JSON reports with latency/token metrics per model.
Revision: 0.1.0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional

import requests


DEFAULT_BASE_URL = os.getenv("LLM_SERVICE_BASE_URL", "http://127.0.0.1:8085/v1").rstrip("/")
DEFAULT_API_KEY = os.getenv("LLM_SERVICE_API_KEY", "not-needed")
DEFAULT_MODELS = [
    "qwen36_27b",
    "qwen36_35b_a3b",
    "gemma4_31b_iq4_nl"
]
DEFAULT_PROMPT = os.getenv(
    "LLM_SERVICE_PROMPT",
    "Explain in 40 words why deterministic test harnesses improve model rollout safety.",
)


@dataclass
class ModelReport:
    model: str
    models_endpoint_ok: bool
    model_listed: bool
    detected_context_length: Optional[int]
    chat_endpoint_ok: bool
    completion_tokens: Optional[int]
    prompt_tokens: Optional[int]
    total_tokens: Optional[int]
    latency_ms: Optional[float]
    tokens_per_second: Optional[float]
    response_preview: Optional[str]
    error: Optional[str]


@dataclass
class PreflightReport:
    base_url: str
    timestamp: str
    models_endpoint_ok: bool
    listed_model_count: int
    tested_models: list[str]
    model_reports: list[ModelReport]
    overall_success: bool


def _headers(api_key: str) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _extract_context_length(model_obj: dict[str, Any]) -> Optional[int]:
    direct_keys = (
        "context_length",
        "max_context_length",
        "max_input_tokens",
        "context_window",
    )
    for key in direct_keys:
        value = model_obj.get(key)
        if isinstance(value, int) and value > 0:
            return value

    nested = model_obj.get("metadata")
    if isinstance(nested, dict):
        for key in direct_keys:
            value = nested.get(key)
            if isinstance(value, int) and value > 0:
                return value
    return None


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception as exc:
        raise RuntimeError(f"Failed to parse JSON response: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected JSON payload shape (expected object).")
    return payload


def _probe_models(
    base_url: str,
    headers: dict[str, str],
    timeout_seconds: float,
) -> tuple[bool, set[str], dict[str, int], int, Optional[str]]:
    """
    Probe /v1/models endpoint.
    Returns: (success, model_ids_set, model_contexts_dict, total_count, error_msg)
    """
    url = f"{base_url}/models"
    try:
        response = requests.get(url, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        payload = _safe_json(response)
    except Exception as exc:
        return False, set(), {}, 0, f"/models probe failed: {exc}"

    data = payload.get("data")
    if not isinstance(data, list):
        return False, set(), {}, 0, "Model listing did not contain a 'data' array."

    model_ids: set[str] = set()
    model_contexts: dict[str, int] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if isinstance(item_id, str) and item_id:
            model_ids.add(item_id)
            context_hint = _extract_context_length(item)
            if context_hint:
                model_contexts[item_id] = context_hint

    return True, model_ids, model_contexts, len(data), None


def _run_chat_completion(
    base_url: str,
    model_id: str,
    prompt: str,
    max_tokens: int,
    headers: dict[str, str],
    timeout_seconds: float,
) -> tuple[bool, Optional[int], Optional[int], Optional[int], Optional[float], Optional[float], Optional[str], Optional[str]]:
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    started = time.perf_counter()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout_seconds)
        response.raise_for_status()
        body = _safe_json(response)
    except Exception as exc:
        return False, None, None, None, None, None, None, f"/chat/completions failed: {exc}"

    latency_ms = round((time.perf_counter() - started) * 1000.0, 2)
    usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
    prompt_tokens = usage.get("prompt_tokens") if isinstance(usage.get("prompt_tokens"), int) else None
    completion_tokens = usage.get("completion_tokens") if isinstance(usage.get("completion_tokens"), int) else None
    total_tokens = usage.get("total_tokens") if isinstance(usage.get("total_tokens"), int) else None

    tokens_per_second = None
    if completion_tokens is not None and latency_ms and latency_ms > 0:
        tokens_per_second = round(completion_tokens / (latency_ms / 1000.0), 2)

    preview = None
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message")
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    preview = content.strip().replace("\n", " ")[:160]

    return True, completion_tokens, prompt_tokens, total_tokens, latency_ms, tokens_per_second, preview, None


def _test_single_model(
    base_url: str,
    model_id: str,
    model_listed: bool,
    context_hint: Optional[int],
    prompt: str,
    max_tokens: int,
    headers: dict[str, str],
    timeout_seconds: float,
) -> ModelReport:
    """Test a single model and return its report."""
    if not model_listed:
        return ModelReport(
            model=model_id,
            models_endpoint_ok=True,
            model_listed=False,
            detected_context_length=None,
            chat_endpoint_ok=False,
            completion_tokens=None,
            prompt_tokens=None,
            total_tokens=None,
            latency_ms=None,
            tokens_per_second=None,
            response_preview=None,
            error=f"Model '{model_id}' not listed in /v1/models endpoint",
        )

    (
        chat_ok,
        completion_tokens,
        prompt_tokens,
        total_tokens,
        latency_ms,
        tps,
        preview,
        chat_error,
    ) = _run_chat_completion(
        base_url,
        model_id,
        prompt,
        max_tokens,
        headers,
        timeout_seconds,
    )

    return ModelReport(
        model=model_id,
        models_endpoint_ok=True,
        model_listed=True,
        detected_context_length=context_hint,
        chat_endpoint_ok=chat_ok,
        completion_tokens=completion_tokens,
        prompt_tokens=prompt_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        tokens_per_second=tps,
        response_preview=preview,
        error=chat_error,
    )


def run_preflight(
    base_url: str,
    model_ids: list[str],
    api_key: str,
    prompt: str,
    max_tokens: int,
    timeout_seconds: float,
) -> PreflightReport:
    headers = _headers(api_key)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    # Probe /v1/models
    models_ok, available_model_ids, model_contexts, listed_count, models_error = _probe_models(
        base_url, headers, timeout_seconds
    )

    if not models_ok:
        # If /v1/models fails, we can't test any models
        failed_reports = [
            ModelReport(
                model=mid,
                models_endpoint_ok=False,
                model_listed=False,
                detected_context_length=None,
                chat_endpoint_ok=False,
                completion_tokens=None,
                prompt_tokens=None,
                total_tokens=None,
                latency_ms=None,
                tokens_per_second=None,
                response_preview=None,
                error=models_error,
            )
            for mid in model_ids
        ]
        return PreflightReport(
            base_url=base_url,
            timestamp=timestamp,
            models_endpoint_ok=False,
            listed_model_count=0,
            tested_models=model_ids,
            model_reports=failed_reports,
            overall_success=False,
        )

    # Test each model
    model_reports = []
    for model_id in model_ids:
        model_listed = model_id in available_model_ids
        context_hint = model_contexts.get(model_id)
        report = _test_single_model(
            base_url,
            model_id,
            model_listed,
            context_hint,
            prompt,
            max_tokens,
            headers,
            timeout_seconds,
        )
        model_reports.append(report)

    # Overall success = all models passed
    overall_success = all(
        r.models_endpoint_ok and r.model_listed and r.chat_endpoint_ok and not r.error
        for r in model_reports
    )

    return PreflightReport(
        base_url=base_url,
        timestamp=timestamp,
        models_endpoint_ok=models_ok,
        listed_model_count=listed_count,
        tested_models=model_ids,
        model_reports=model_reports,
        overall_success=overall_success,
    )


def _print_report(report: PreflightReport) -> None:
    print("=" * 80)
    print("Multi-Model Preflight Report")
    print("=" * 80)
    print(f"Base URL:              {report.base_url}")
    print(f"Timestamp:             {report.timestamp}")
    print(f"/models reachable:     {report.models_endpoint_ok}")
    print(f"Models returned:       {report.listed_model_count}")
    print(f"Tested models:         {len(report.tested_models)}")
    print(f"Overall success:       {report.overall_success}")
    print()

    for i, model_report in enumerate(report.model_reports, 1):
        print(f"--- Model {i}/{len(report.model_reports)}: {model_report.model} ---")
        print(f"  Listed in /v1/models:  {model_report.model_listed}")
        print(f"  Detected context:      {model_report.detected_context_length}")
        print(f"  Chat completion ok:    {model_report.chat_endpoint_ok}")
        print(f"  Prompt tokens:         {model_report.prompt_tokens}")
        print(f"  Completion tokens:     {model_report.completion_tokens}")
        print(f"  Total tokens:          {model_report.total_tokens}")
        print(f"  Latency (ms):          {model_report.latency_ms}")
        print(f"  Tokens / second:       {model_report.tokens_per_second}")
        print(f"  Response preview:      {model_report.response_preview}")
        if model_report.error:
            print(f"  Error:                 {model_report.error}")
        print()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Multi-model endpoint preflight checks")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI-compatible endpoint base URL")
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Model IDs to test (space-separated)",
    )
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Bearer token for endpoint auth")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt for completion smoke test")
    parser.add_argument("--max-tokens", type=int, default=96, help="Max completion tokens for smoke test")
    parser.add_argument("--timeout", type=float, default=60.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional output path for JSON report",
    )
    parser.add_argument(
        "--require-all-models",
        action="store_true",
        help="Fail if any model is not listed or fails chat completion",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = run_preflight(
        base_url=args.base_url.rstrip("/"),
        model_ids=[m.strip() for m in args.models],
        api_key=args.api_key.strip(),
        prompt=args.prompt,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout,
    )

    _print_report(report)

    if args.json_out:
        # Convert to JSON-serializable dict
        report_dict = {
            "base_url": report.base_url,
            "timestamp": report.timestamp,
            "models_endpoint_ok": report.models_endpoint_ok,
            "listed_model_count": report.listed_model_count,
            "tested_models": report.tested_models,
            "model_reports": [asdict(r) for r in report.model_reports],
            "overall_success": report.overall_success,
        }
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(report_dict, handle, indent=2)
        print(f"JSON report written to: {args.json_out}")

    # Exit codes
    if not report.models_endpoint_ok:
        return 1
    if args.require_all_models and not report.overall_success:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
