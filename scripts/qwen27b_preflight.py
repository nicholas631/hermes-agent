#!/usr/bin/env python3
"""
Name: scripts/qwen27b_preflight.py
Description: Repeatable preflight checks for Qwen 3.5 27B custom endpoints.
Primary Functions:
  - Probe OpenAI-compatible /models and /chat/completions endpoints.
  - Validate configured model availability and completion behavior.
  - Emit human-readable and JSON reports with latency/token metrics.
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


DEFAULT_BASE_URL = os.getenv("QWEN27B_BASE_URL", "http://127.0.0.1:8085/v1").rstrip("/")
DEFAULT_MODEL = os.getenv("QWEN27B_MODEL", "qwen3.5:27b")
DEFAULT_API_KEY = os.getenv("QWEN27B_API_KEY", os.getenv("OPENAI_API_KEY", "ollama"))
DEFAULT_PROMPT = os.getenv(
    "QWEN27B_PROMPT",
    "Explain in 40 words why deterministic test harnesses improve model rollout safety.",
)


@dataclass
class PreflightReport:
    base_url: str
    model: str
    models_endpoint_ok: bool
    model_listed: bool
    listed_model_count: int
    detected_context_length: Optional[int]
    chat_endpoint_ok: bool
    completion_tokens: Optional[int]
    prompt_tokens: Optional[int]
    total_tokens: Optional[int]
    latency_ms: Optional[float]
    tokens_per_second: Optional[float]
    response_preview: Optional[str]
    error: Optional[str]


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
    except Exception as exc:  # pragma: no cover - defensive parsing
        raise RuntimeError(f"Failed to parse JSON response: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Unexpected JSON payload shape (expected object).")
    return payload


def _probe_models(
    base_url: str,
    model_id: str,
    headers: dict[str, str],
    timeout_seconds: float,
) -> tuple[bool, bool, int, Optional[int], Optional[str]]:
    url = f"{base_url}/models"
    try:
        response = requests.get(url, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        payload = _safe_json(response)
    except Exception as exc:
        return False, False, 0, None, f"/models probe failed: {exc}"

    data = payload.get("data")
    if not isinstance(data, list):
        return False, False, 0, None, "Model listing did not contain a 'data' array."

    model_ids: list[str] = []
    context_hint: Optional[int] = None
    for item in data:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if isinstance(item_id, str) and item_id:
            model_ids.append(item_id)
            if item_id == model_id:
                context_hint = _extract_context_length(item)

    return True, model_id in set(model_ids), len(model_ids), context_hint, None


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


def run_preflight(
    base_url: str,
    model_id: str,
    api_key: str,
    prompt: str,
    max_tokens: int,
    timeout_seconds: float,
) -> PreflightReport:
    headers = _headers(api_key)

    (
        models_ok,
        model_listed,
        listed_count,
        context_hint,
        models_error,
    ) = _probe_models(base_url, model_id, headers, timeout_seconds)

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

    error = chat_error or models_error
    return PreflightReport(
        base_url=base_url,
        model=model_id,
        models_endpoint_ok=models_ok,
        model_listed=model_listed,
        listed_model_count=listed_count,
        detected_context_length=context_hint,
        chat_endpoint_ok=chat_ok,
        completion_tokens=completion_tokens,
        prompt_tokens=prompt_tokens,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        tokens_per_second=tps,
        response_preview=preview,
        error=error,
    )


def _print_report(report: PreflightReport) -> None:
    print("Qwen 27B preflight report")
    print("=" * 60)
    print(f"Base URL:              {report.base_url}")
    print(f"Model:                 {report.model}")
    print(f"/models reachable:     {report.models_endpoint_ok}")
    print(f"Model listed:          {report.model_listed}")
    print(f"Models returned:       {report.listed_model_count}")
    print(f"Detected context:      {report.detected_context_length}")
    print(f"/chat completion ok:   {report.chat_endpoint_ok}")
    print(f"Prompt tokens:         {report.prompt_tokens}")
    print(f"Completion tokens:     {report.completion_tokens}")
    print(f"Total tokens:          {report.total_tokens}")
    print(f"Latency (ms):          {report.latency_ms}")
    print(f"Tokens / second:       {report.tokens_per_second}")
    print(f"Response preview:      {report.response_preview}")
    if report.error:
        print(f"Error:                 {report.error}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Qwen 27B endpoint preflight checks")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI-compatible endpoint base URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model ID to test")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="Bearer token for endpoint auth")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt for completion smoke test")
    parser.add_argument("--max-tokens", type=int, default=96, help="Max completion tokens for smoke test")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional output path for JSON report",
    )
    parser.add_argument(
        "--require-model-listed",
        action="store_true",
        help="Fail if /models does not list the configured model ID",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = run_preflight(
        base_url=args.base_url.rstrip("/"),
        model_id=args.model.strip(),
        api_key=args.api_key.strip(),
        prompt=args.prompt,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout,
    )

    _print_report(report)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(asdict(report), handle, indent=2)
        print(f"JSON report written to: {args.json_out}")

    if not report.chat_endpoint_ok:
        return 1
    if args.require_model_listed and not report.model_listed:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
