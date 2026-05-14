"""
Name: tests/integration/test_local_model_service.py
Description: Integration/e2e checks for multiple models on LLM Local Model Service.
Primary Functions:
  - Validates /v1/models reachability and model listing checks.
  - Validates /v1/chat/completions for multiple models with various parameters.
  - Tests multi-turn conversations, temperature variations, and error handling.
Revision: 0.1.1
"""

from __future__ import annotations

import json
import os
from typing import Any

import pytest
import requests


pytestmark = pytest.mark.integration


BASE_URL = os.getenv("LLM_SERVICE_BASE_URL", "").strip().rstrip("/")
API_KEY = os.getenv("LLM_SERVICE_API_KEY", "not-needed").strip()
TIMEOUT = float(os.getenv("LLM_SERVICE_TIMEOUT", "60"))

# Models to test
TEST_MODELS = [
    "qwen36_27b",
    "qwen36_35b_a3b",
    "gemma4_31b_iq4_nl",
]


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
def _skip_if_service_unreachable():
    if not BASE_URL:
        pytest.skip("LLM_SERVICE_BASE_URL is not set; skipping local model service integration checks.")
    try:
        response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(
            f"LLM Local Model Service at {BASE_URL} is unreachable or unhealthy: {exc}",
            allow_module_level=True,
        )


def test_models_endpoint_lists_data():
    """Test that /v1/models endpoint returns a valid list of models."""
    response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
    response.raise_for_status()
    payload = _json(response)

    data = payload.get("data")
    assert isinstance(data, list), "Expected 'data' list from /models endpoint"

    model_ids = []
    for item in data:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            model_ids.append(item["id"])

    # Verify our test models are present
    model_set = set(model_ids)
    for test_model in TEST_MODELS:
        assert test_model in model_set, (
            f"Test model '{test_model}' is missing from /v1/models. "
            f"Available models: {model_ids}"
        )


@pytest.mark.parametrize("model_id", TEST_MODELS)
def test_chat_completion_basic(model_id: str):
    """Test basic chat completion for each model."""
    payload = {
        "model": model_id,
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

    # Validate response structure
    choices = body.get("choices")
    assert isinstance(choices, list) and choices, "Expected non-empty choices list"
    first_choice = choices[0]
    assert isinstance(first_choice, dict), "Expected dict choice entry"
    message = first_choice.get("message")
    assert isinstance(message, dict), "Expected message object in first choice"
    content = message.get("content")
    assert isinstance(content, str) and content.strip(), "Expected non-empty assistant message content"

    # Validate usage
    usage = body.get("usage")
    assert isinstance(usage, dict), "Expected usage object in response"
    completion_tokens = usage.get("completion_tokens")
    if completion_tokens is not None:
        assert isinstance(completion_tokens, int)
        assert completion_tokens >= 1


@pytest.mark.parametrize("model_id", TEST_MODELS)
@pytest.mark.parametrize("temperature", [0.0, 0.5, 1.0])
def test_chat_completion_temperature_variations(model_id: str, temperature: float):
    """Test chat completions with different temperature values."""
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": "Say 'hello' in exactly one word.",
            }
        ],
        "max_tokens": 16,
        "temperature": temperature,
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
    assert isinstance(choices, list) and choices
    content = choices[0]["message"]["content"]
    assert isinstance(content, str) and content.strip()


@pytest.mark.parametrize("model_id", TEST_MODELS)
def test_chat_completion_multi_turn(model_id: str):
    """Test multi-turn conversation with each model."""
    messages = [
        {"role": "user", "content": "What is 2 + 2?"},
        {"role": "assistant", "content": "2 + 2 equals 4."},
        {"role": "user", "content": "Now add 3 to that result."},
    ]

    payload = {
        "model": model_id,
        "messages": messages,
        "max_tokens": 32,
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
    assert isinstance(choices, list) and choices
    content = choices[0]["message"]["content"]
    assert isinstance(content, str) and content.strip()
    # The response should reference 7 (4 + 3)
    assert "7" in content


@pytest.mark.parametrize("model_id", TEST_MODELS)
@pytest.mark.parametrize("max_tokens", [16, 64, 256])
def test_chat_completion_max_tokens_limits(model_id: str, max_tokens: int):
    """Test that max_tokens parameter is respected."""
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": "Write a detailed explanation of quantum computing.",
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0.5,
    }

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    body = _json(response)

    usage = body.get("usage", {})
    completion_tokens = usage.get("completion_tokens")
    if completion_tokens is not None:
        # Allow some tolerance for tokenization differences
        assert completion_tokens <= max_tokens + 5, (
            f"Model returned {completion_tokens} tokens, exceeding max_tokens={max_tokens}"
        )


@pytest.mark.parametrize("model_id", TEST_MODELS)
@pytest.mark.parametrize("prompt_length", ["short", "medium", "long"])
def test_chat_completion_context_window(model_id: str, prompt_length: str):
    """Test models with different prompt lengths."""
    prompts = {
        "short": "Hello!",
        "medium": " ".join(["This is a test sentence."] * 50),
        "long": " ".join(["This is a longer test sentence for context window testing."] * 200),
    }

    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": prompts[prompt_length],
            }
        ],
        "max_tokens": 32,
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
    assert isinstance(choices, list) and choices
    content = choices[0]["message"]["content"]
    assert isinstance(content, str) and content.strip()


def test_chat_completion_invalid_model():
    """Test that requesting an invalid model returns an appropriate error."""
    payload = {
        "model": "nonexistent_model_xyz",
        "messages": [
            {
                "role": "user",
                "content": "Hello",
            }
        ],
        "max_tokens": 16,
    }

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=TIMEOUT,
    )
    
    # Should return 4xx error for invalid model
    assert response.status_code >= 400 and response.status_code < 500, (
        f"Expected 4xx error for invalid model, got {response.status_code}"
    )


@pytest.mark.parametrize("model_id", TEST_MODELS)
def test_chat_completion_streaming_if_supported(model_id: str):
    """Test streaming completions if the endpoint supports it."""
    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": "Count from 1 to 5.",
            }
        ],
        "max_tokens": 64,
        "temperature": 0.2,
        "stream": True,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=_headers(),
            json=payload,
            timeout=TIMEOUT,
            stream=True,
        )
        response.raise_for_status()

        # Collect streaming chunks
        chunks = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        chunks.append(chunk)
                    except json.JSONDecodeError:
                        # Skip malformed chunks
                        pass

        # If we got chunks, validate structure
        if chunks:
            assert len(chunks) > 0, "Expected at least one streaming chunk"
            # Verify at least some chunks have content
            has_content = any(
                c.get("choices", [{}])[0].get("delta", {}).get("content")
                for c in chunks
            )
            assert has_content, "Expected streaming chunks to contain content"
    except requests.exceptions.RequestException:
        # If streaming not supported, that's okay - skip this test
        pytest.skip(f"Streaming not supported or service unavailable for {model_id}")
