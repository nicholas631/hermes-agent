---
title: "Integration Test Templates"
description: "Reusable patterns for testing Hermes Agent with local and remote models"
revision: 0.1.0
last_updated: 2026-05-12
---

# Integration Test Templates

This guide provides reusable templates for writing integration tests with Hermes Agent, based on proven patterns from [`tests/integration/test_qwen27b_custom_endpoint.py`](../../tests/integration/test_qwen27b_custom_endpoint.py).

## Template 1: Basic Model Availability Test

**Purpose**: Verify that a local model endpoint is responsive and returns model listings.

**When to use**: First test to write when integrating a new local model endpoint.

```python
"""
Name: tests/integration/test_my_local_model.py
Description: Integration tests for My Local Model endpoint.
Revision: 0.1.0
"""

from __future__ import annotations

import os
from typing import Any

import pytest
import requests


pytestmark = pytest.mark.integration


# Configuration from environment
BASE_URL = os.getenv("MY_MODEL_TEST_BASE_URL", "").strip().rstrip("/")
MODEL_ID = os.getenv("MY_MODEL_TEST_MODEL", "my-model").strip()
API_KEY = os.getenv("MY_MODEL_TEST_API_KEY", "").strip()
TIMEOUT = float(os.getenv("MY_MODEL_TEST_TIMEOUT", "20"))


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
            "MY_MODEL_TEST_BASE_URL not set; skipping integration tests. "
            "Set environment variable to enable these tests."
        )
    
    try:
        response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(
            f"Endpoint at {BASE_URL} is unreachable or unhealthy: {exc}. "
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
```

## Template 2: Chat Completion Test

**Purpose**: Validate that basic chat completions work correctly.

**When to use**: After verifying model availability, test actual inference.

```python
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
```

## Template 3: Tool Calling Validation

**Purpose**: Test model's ability to handle tool/function calling.

**When to use**: When validating models that support function calling.

```python
def test_model_supports_function_calling():
    """Verify model can handle function/tool definitions."""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City name, e.g. San Francisco",
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Temperature unit",
                        },
                    },
                    "required": ["location"],
                },
            },
        }
    ]
    
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "user", "content": "What's the weather in Paris?"}
        ],
        "tools": tools,
        "max_tokens": 100,
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
    
    # Verify response structure
    assert "choices" in data
    choice = data["choices"][0]
    message = choice["message"]
    
    # Model should either call the function or respond with text
    # Check if function was called
    if "tool_calls" in message:
        tool_calls = message["tool_calls"]
        assert isinstance(tool_calls, list), "'tool_calls' should be a list"
        assert len(tool_calls) > 0, "Should have at least one tool call"
        
        # Validate tool call structure
        tool_call = tool_calls[0]
        assert "function" in tool_call, "Tool call should have 'function'"
        assert tool_call["function"]["name"] == "get_weather", \
            "Should call get_weather function"
    else:
        # Model responded with text instead - still valid
        assert "content" in message
        assert len(message["content"]) > 0
```

## Template 4: Context Window Handling

**Purpose**: Test model behavior with large context sizes.

**When to use**: When validating models with large context windows (>100k tokens).

```python
@pytest.mark.slow
@pytest.mark.parametrize("context_size", [1000, 10000, 50000])
def test_model_handles_large_context(context_size: int):
    """Verify model can handle large context sizes without errors."""
    # Generate synthetic context (rough estimate: 4 chars per token)
    filler_text = "The quick brown fox jumps over the lazy dog. " * (context_size // 10)
    prompt = f"{filler_text}\n\nSummarize the above text in one sentence."
    
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 100,
        "temperature": 0.2,
    }
    
    # Use longer timeout for large contexts
    timeout = TIMEOUT * (1 + context_size // 10000)
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=timeout,
    )
    
    # Should not fail with context length errors
    assert response.status_code != 400, \
        f"Context size {context_size} should not cause 400 error"
    
    if response.status_code == 200:
        data = _json(response)
        assert "choices" in data
        assert len(data["choices"][0]["message"]["content"]) > 0
        
        # Verify token usage reflects large context
        usage = data.get("usage", {})
        if usage:
            actual_prompt_tokens = usage.get("prompt_tokens", 0)
            # Should be close to target (allow 20% variance due to tokenization)
            assert actual_prompt_tokens > context_size * 0.8, \
                f"Expected ~{context_size} tokens, got {actual_prompt_tokens}"
```

## Template 5: Multi-turn Conversation

**Purpose**: Test conversation history handling across multiple turns.

**When to use**: When validating stateless models that need conversation context.

```python
def test_multi_turn_conversation_maintains_context():
    """Verify model can maintain context across multiple conversation turns."""
    messages = []
    
    # Turn 1: Set up context
    messages.append({
        "role": "user",
        "content": "I have a dog named Max. He is 3 years old."
    })
    
    response1 = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json={
            "model": MODEL_ID,
            "messages": messages,
            "max_tokens": 50,
        },
        timeout=TIMEOUT,
    )
    response1.raise_for_status()
    data1 = _json(response1)
    
    # Add assistant response to history
    assistant_msg = data1["choices"][0]["message"]
    messages.append(assistant_msg)
    
    # Turn 2: Ask about previous context
    messages.append({
        "role": "user",
        "content": "How old is my dog?"
    })
    
    response2 = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json={
            "model": MODEL_ID,
            "messages": messages,
            "max_tokens": 50,
        },
        timeout=TIMEOUT,
    )
    response2.raise_for_status()
    data2 = _json(response2)
    
    # Verify model remembered context
    content = data2["choices"][0]["message"]["content"].lower()
    assert "3" in content or "three" in content, \
        "Model should remember dog's age from previous turn"
```

## Template 6: Performance Baseline

**Purpose**: Establish and validate performance expectations.

**When to use**: For regression testing and performance monitoring.

```python
import time

def test_completion_latency_is_reasonable():
    """Verify completion latency is within expected range."""
    payload = {
        "model": MODEL_ID,
        "messages": [
            {"role": "user", "content": "Count from 1 to 5."}
        ],
        "max_tokens": 50,
        "temperature": 0.0,
    }
    
    start_time = time.perf_counter()
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=TIMEOUT,
    )
    latency_ms = (time.perf_counter() - start_time) * 1000.0
    
    response.raise_for_status()
    data = _json(response)
    
    # Calculate throughput
    usage = data.get("usage", {})
    completion_tokens = usage.get("completion_tokens", 0)
    tokens_per_second = completion_tokens / (latency_ms / 1000.0) if latency_ms > 0 else 0
    
    # Performance assertions (adjust based on your model)
    assert latency_ms < 30000, \
        f"Latency {latency_ms:.0f}ms exceeds 30s threshold"
    
    assert tokens_per_second > 1.0, \
        f"Throughput {tokens_per_second:.1f} tok/s below minimum threshold"
    
    # Log metrics for monitoring
    print(f"\nPerformance: {latency_ms:.0f}ms, {tokens_per_second:.1f} tok/s")
```

## Template 7: Error Handling

**Purpose**: Test graceful handling of invalid requests.

**When to use**: To ensure robust error responses for edge cases.

```python
def test_invalid_model_returns_404():
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
    
    assert response.status_code in (400, 404), \
        "Invalid model should return 400 or 404 status"


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
        "Missing required field should return 400 Bad Request"


def test_excessive_max_tokens_is_handled():
    """Verify requesting excessive max_tokens doesn't crash service."""
    payload = {
        "model": MODEL_ID,
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 1_000_000,  # Unreasonably large
    }
    
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        headers=_headers(),
        json=payload,
        timeout=TIMEOUT,
    )
    
    # Should either accept (and cap) or reject with clear error
    assert response.status_code in (200, 400), \
        "Service should handle excessive max_tokens gracefully"
```

---

## Full Example: Complete Integration Test Module

```python
"""
Name: tests/integration/test_local_llm_integration.py
Description: Complete integration test suite for local LLM endpoint.
Revision: 0.1.0
"""

from __future__ import annotations

import os
import time
from typing import Any

import pytest
import requests


pytestmark = pytest.mark.integration


# Configuration
BASE_URL = os.getenv("LOCAL_LLM_TEST_BASE_URL", "").strip().rstrip("/")
MODEL_ID = os.getenv("LOCAL_LLM_TEST_MODEL", "local-model").strip()
API_KEY = os.getenv("LOCAL_LLM_TEST_API_KEY", "").strip()
TIMEOUT = float(os.getenv("LOCAL_LLM_TEST_TIMEOUT", "30"))


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    return headers


def _json(response: requests.Response) -> dict[str, Any]:
    payload = response.json()
    assert isinstance(payload, dict), "Expected JSON object"
    return payload


@pytest.fixture(scope="module", autouse=True)
def _skip_if_endpoint_unavailable():
    if not BASE_URL:
        pytest.skip("LOCAL_LLM_TEST_BASE_URL not set")
    
    try:
        response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(f"Endpoint unreachable: {exc}", allow_module_level=True)


class TestModelDiscovery:
    """Test model listing and availability."""
    
    def test_models_endpoint_accessible(self):
        response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
        assert response.status_code == 200
    
    def test_models_returns_list(self):
        response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
        data = _json(response)
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
    
    def test_configured_model_is_listed(self):
        response = requests.get(f"{BASE_URL}/models", headers=_headers(), timeout=TIMEOUT)
        data = _json(response)
        model_ids = [m.get("id") for m in data.get("data", [])]
        assert MODEL_ID in model_ids


class TestChatCompletions:
    """Test chat completion functionality."""
    
    def test_simple_completion(self):
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=_headers(),
            json={
                "model": MODEL_ID,
                "messages": [{"role": "user", "content": "Say 'test'"}],
                "max_tokens": 10,
            },
            timeout=TIMEOUT,
        )
        assert response.status_code == 200
        data = _json(response)
        assert "choices" in data
        assert len(data["choices"]) > 0
    
    def test_completion_includes_usage(self):
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=_headers(),
            json={
                "model": MODEL_ID,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 20,
            },
            timeout=TIMEOUT,
        )
        data = _json(response)
        assert "usage" in data
        usage = data["usage"]
        assert usage["prompt_tokens"] > 0
        assert usage["completion_tokens"] > 0
        assert usage["total_tokens"] > 0


class TestPerformance:
    """Test performance characteristics."""
    
    def test_latency_within_threshold(self):
        start = time.perf_counter()
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=_headers(),
            json={
                "model": MODEL_ID,
                "messages": [{"role": "user", "content": "What is 1+1?"}],
                "max_tokens": 10,
            },
            timeout=TIMEOUT,
        )
        latency_ms = (time.perf_counter() - start) * 1000.0
        
        assert response.status_code == 200
        assert latency_ms < 60000, f"Latency {latency_ms:.0f}ms exceeds 60s"
        
        print(f"\nLatency: {latency_ms:.0f}ms")
```

---

## Running Integration Tests

### Basic Execution

```powershell
# Set environment variables
$env:MY_MODEL_TEST_BASE_URL = "http://localhost:8085/v1"
$env:MY_MODEL_TEST_MODEL = "my-model"

# Run all integration tests
pytest -m integration tests\integration\ -v

# Run specific test file
pytest tests\integration\test_my_local_model.py -v

# Run specific test class
pytest tests\integration\test_my_local_model.py::TestChatCompletions -v

# Run specific test
pytest tests\integration\test_my_local_model.py::test_models_endpoint_returns_list -v
```

### Advanced Execution

```powershell
# Run with coverage
pytest -m integration tests\integration\ --cov=agent --cov=model_tools -v

# Run and show output
pytest -m integration tests\integration\ -v -s

# Run in parallel
pytest -m integration tests\integration\ -n 4 -v

# Stop on first failure
pytest -m integration tests\integration\ -x -v

# Re-run only failed tests
pytest -m integration tests\integration\ --lf -v
```

---

## Additional Resources

- **Existing Integration Tests**: [`tests/integration/test_qwen27b_custom_endpoint.py`](../../tests/integration/test_qwen27b_custom_endpoint.py)
- **Testing Best Practices**: [`docs/testing/testing-best-practices.md`](testing-best-practices.md)
- **Local Model Testing**: [`docs/testing/local-model-testing-guide.md`](local-model-testing-guide.md)
- **Development Workflow**: [`docs/developer-guide/local-development-workflow.md`](../developer-guide/local-development-workflow.md)
