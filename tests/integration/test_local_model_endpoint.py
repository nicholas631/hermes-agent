"""
Name: tests/integration/test_local_model_endpoint.py
Description: Generic integration tests for any local LLM endpoint (OpenAI-compatible API).
Primary Functions:
  - Test model availability via /models endpoint
  - Test chat completions with usage metrics
  - Validate error handling
Revision: 0.1.0
"""

from __future__ import annotations

import os
from typing import Any

import pytest
import requests


pytestmark = pytest.mark.integration


# Configuration from environment
BASE_URL = os.getenv("LOCAL_MODEL_TEST_BASE_URL", "").strip().rstrip("/")
MODEL_ID = os.getenv("LOCAL_MODEL_TEST_MODEL", "qwen36_27b").strip()
API_KEY = os.getenv("LOCAL_MODEL_TEST_API_KEY", "").strip()
TIMEOUT = float(os.getenv("LOCAL_MODEL_TEST_TIMEOUT", "30"))


def _headers() -> dict[str, str]:
    """Build request headers with optional authentication."""
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def _json(response: requests.Response) -> dict[str, Any]:
    """Parse and validate JSON response."""
    payload = response.json()
    assert isinstance(payload, dict), "Expected JSON object payload"
    return payload


@pytest.fixture(scope="module", autouse=True)
def _skip_if_endpoint_unreachable():
    """Skip all tests in module if endpoint is not configured or unreachable."""
    if not BASE_URL:
        pytest.skip(
            "LOCAL_MODEL_TEST_BASE_URL not set; skipping local model integration tests. "
            "Set environment variable to enable these tests."
        )
    
    try:
        response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(
            f"Local model endpoint at {BASE_URL} is unreachable or unhealthy: {exc}. "
            "Ensure service is running before running integration tests.",
            allow_module_level=True,
        )


def test_models_endpoint_returns_list():
    """Verify /models endpoint returns a list of available models."""
    response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
    response.raise_for_status()
    payload = _json(response)
    
    data = payload.get("data")
    assert isinstance(data, list), "Expected 'data' list from /models endpoint"
    assert len(data) > 0, "Expected at least one model in listing"
    
    # Verify models have required fields
    for item in data:
        assert isinstance(item, dict), "Model entry should be a dict"
        assert "id" in item, "Model entry should have 'id' field"


def test_configured_model_is_available():
    """Verify the configured model ID is listed in /models response."""
    response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
    response.raise_for_status()
    payload = _json(response)
    
    model_ids = [
        item.get("id")
        for item in payload.get("data", [])
        if isinstance(item, dict) and item.get("id")
    ]
    
    assert MODEL_ID in model_ids, (
        f"Configured model '{MODEL_ID}' not found in available models. "
        f"Available: {model_ids}"
    )


def test_chat_completion_returns_valid_response():
    """Verify /chat/completions endpoint returns a valid response structure."""
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "user", "content": "What is 2+2? Answer with just the number."}
        ],
        "max_tokens": 10,
        "temperature": 0.0,
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = _json(response)
    
    # Validate response structure
    assert "choices" in data, "Response should contain 'choices'"
    assert isinstance(data["choices"], list), "'choices' should be a list"
    assert len(data["choices"]) > 0, "Should return at least one choice"
    
    # Validate message structure
    choice = data["choices"][0]
    assert "message" in choice, "Choice should contain 'message'"
    message = choice["message"]
    assert "role" in message, "Message should have 'role'"
    assert "content" in message, "Message should have 'content'"
    assert message["role"] == "assistant", "Response role should be 'assistant'"
    assert len(message["content"]) > 0, "Response content should not be empty"


def test_chat_completion_includes_usage_metrics():
    """Verify response includes token usage metrics."""
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "user", "content": "Explain binary search in 20 words."}
        ],
        "max_tokens": 50,
        "temperature": 0.2,
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = _json(response)
    
    # Validate usage metrics
    assert "usage" in data, "Response should include 'usage' metrics"
    usage = data["usage"]
    assert isinstance(usage, dict), "'usage' should be a dict"
    
    # Check required usage fields
    assert "prompt_tokens" in usage, "Usage should include 'prompt_tokens'"
    assert "completion_tokens" in usage, "Usage should include 'completion_tokens'"
    assert "total_tokens" in usage, "Usage should include 'total_tokens'"
    
    # Verify token counts are reasonable
    assert usage["prompt_tokens"] > 0, "Prompt tokens should be positive"
    assert usage["completion_tokens"] > 0, "Completion tokens should be positive"
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"], \
        "Total tokens should equal prompt + completion"


def test_invalid_model_returns_error():
    """Verify requesting non-existent model returns appropriate error."""
    payload = {
        "model": "non-existent-model-12345",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10,
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=TIMEOUT,
    )
    
    # Should return 400 or 404 error
    assert response.status_code in (400, 404), \
        f"Invalid model should return 400 or 404, got {response.status_code}"


def test_missing_required_field_returns_400():
    """Verify missing required fields return validation error."""
    # Missing 'messages' field
    payload = {
        "model": MODEL_ID,
        "max_tokens": 10,
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=TIMEOUT,
    )
    
    assert response.status_code == 400, \
        f"Missing required field should return 400 Bad Request, got {response.status_code}"
