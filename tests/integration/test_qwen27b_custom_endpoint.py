"""
Name: tests/integration/test_qwen27b_custom_endpoint.py
Description: Integration/e2e checks for Qwen 27B on a custom OpenAI-compatible endpoint.
Primary Functions:
  - Validates /models reachability and optional model listing checks.
  - Validates /chat/completions returns a usable assistant response and usage payload.
Revision: 0.1.0
"""

from __future__ import annotations

import os
from typing import Any

import pytest
import requests


pytestmark = pytest.mark.integration


BASE_URL = os.getenv("QWEN27B_TEST_BASE_URL", "").strip().rstrip("/")
MODEL_ID = os.getenv("QWEN27B_TEST_MODEL", "qwen3.5:27b").strip()
API_KEY = os.getenv("QWEN27B_TEST_API_KEY", os.getenv("OPENAI_API_KEY", "ollama")).strip()
TIMEOUT = float(os.getenv("QWEN27B_TEST_TIMEOUT", "20"))
REQUIRE_MODEL_LISTED = os.getenv("QWEN27B_REQUIRE_MODEL_LISTED", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def _json(response: requests.Response) -> dict[str, Any]:
    payload = response.json()
    assert isinstance(payload, dict), "Expected JSON object payload"
    return payload


@pytest.fixture(scope="module", autouse=True)
def _skip_if_endpoint_unreachable():
    if not BASE_URL:
        pytest.skip("QWEN27B_TEST_BASE_URL is not set; skipping Qwen endpoint integration checks.")
    try:
        response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(
            f"Qwen endpoint at {BASE_URL} is unreachable or unhealthy: {exc}",
            allow_module_level=True,
        )


def test_models_endpoint_lists_data():
    response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
    response.raise_for_status()
    payload = _json(response)

    data = payload.get("data")
    assert isinstance(data, list), "Expected 'data' list from /models endpoint"

    model_ids = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            model_ids.append(item["id"])

    if REQUIRE_MODEL_LISTED:
        assert MODEL_ID in set(model_ids), (
            f"Configured model '{MODEL_ID}' is missing from /models. "
            "Set QWEN27B_REQUIRE_MODEL_LISTED=0 if your server uses hidden aliases."
        )


def test_chat_completion_returns_content_and_usage():
    payload = {
        "model": MODEL_ID,
        "messages": [
            {
                "role": "user",
                "content": "In one concise sentence, describe why rollout checklists matter for LLM deployments.",
            }
        ],
        "max_tokens": 64,
        "temperature": 0.2,
    }

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    body = _json(response)

    choices = body.get("choices")
    assert isinstance(choices, list) and choices, "Expected non-empty choices list"
    first_choice = choices[0]
    assert isinstance(first_choice, dict), "Expected dict choice entry"
    message = first_choice.get("message")
    assert isinstance(message, dict), "Expected message object in first choice"
    content = message.get("content")
    assert isinstance(content, str) and content.strip(), "Expected non-empty assistant message content"

    usage = body.get("usage")
    assert isinstance(usage, dict), "Expected usage object in response"
    completion_tokens = usage.get("completion_tokens")
    if completion_tokens is not None:
        assert isinstance(completion_tokens, int)
        assert completion_tokens >= 1
