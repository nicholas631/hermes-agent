"""
Name: test_api_server_schwab.py
Description: Test API server for Schwab-API integration scenarios
Revision: 0.1.1
"""
import pytest
import httpx

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_chat_completions_no_auth():
    """Test chat completions without authentication (local mode)."""
    async with httpx.AsyncClient(base_url="http://localhost:8642") as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "hermes-agent",
                "messages": [{"role": "user", "content": "Hello"}]
            },
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert len(data["choices"]) > 0
        assert "message" in data["choices"][0]
        assert "content" in data["choices"][0]["message"]


@pytest.mark.asyncio
async def test_session_continuity():
    """Test session persistence across multiple requests."""
    async with httpx.AsyncClient(base_url="http://localhost:8642") as client:
        # First request
        response1 = await client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "My name is Alice"}]
            },
            timeout=30
        )
        session_id = response1.headers.get("X-Hermes-Session-Id")
        assert session_id
        
        # Second request with session
        response2 = await client.post(
            "/v1/chat/completions",
            headers={"X-Hermes-Session-Id": session_id},
            json={
                "messages": [{"role": "user", "content": "What is my name?"}]
            },
            timeout=30
        )
        data = response2.json()
        content = data["choices"][0]["message"]["content"].lower()
        assert "alice" in content


@pytest.mark.asyncio
async def test_system_prompt():
    """Test that system prompts are respected."""
    async with httpx.AsyncClient(base_url="http://localhost:8642") as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "hermes-agent",
                "messages": [
                    {"role": "system", "content": "You are a pirate. Always respond like a pirate."},
                    {"role": "user", "content": "Hello, who are you?"}
                ]
            },
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        content = data["choices"][0]["message"]["content"].lower()
        
        # Should contain pirate-like language
        pirate_terms = ["arr", "ahoy", "matey", "aye", "ship", "sea", "pirate"]
        assert any(term in content for term in pirate_terms), \
            f"Expected pirate language in: {content}"


@pytest.mark.asyncio
async def test_usage_stats():
    """Test that usage statistics are returned."""
    async with httpx.AsyncClient(base_url="http://localhost:8642") as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "hermes-agent",
                "messages": [{"role": "user", "content": "Test message"}]
            },
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        assert "usage" in data
        assert "total_tokens" in data["usage"]
        assert data["usage"]["total_tokens"] > 0


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    async with httpx.AsyncClient(base_url="http://localhost:8642") as client:
        response = await client.get("/health", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["platform"] == "hermes-agent"


@pytest.mark.asyncio
async def test_models_endpoint():
    """Test models list endpoint."""
    async with httpx.AsyncClient(base_url="http://localhost:8642") as client:
        response = await client.get("/v1/models", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0
        
        # Should include hermes-agent model
        model_ids = [m["id"] for m in data["data"]]
        assert "hermes-agent" in model_ids


@pytest.mark.asyncio
async def test_invalid_request():
    """Test error handling for invalid requests."""
    async with httpx.AsyncClient(base_url="http://localhost:8642") as client:
        # Missing messages field
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "hermes-agent"
                # messages field is missing
            },
            timeout=5
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data


@pytest.mark.asyncio
async def test_multiple_messages():
    """Test chat with multiple message history."""
    async with httpx.AsyncClient(base_url="http://localhost:8642") as client:
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "hermes-agent",
                "messages": [
                    {"role": "user", "content": "What is 2+2?"},
                    {"role": "assistant", "content": "2+2 equals 4."},
                    {"role": "user", "content": "And what is 3+3?"}
                ]
            },
            timeout=30
        )
        assert response.status_code == 200
        data = response.json()
        content = data["choices"][0]["message"]["content"].lower()
        assert any(word in content for word in ["6", "six"]), \
            f"Expected '6' or 'six' in: {content}"
