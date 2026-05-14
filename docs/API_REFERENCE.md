# Hermes Agent API Reference

## Base URL

`http://localhost:8642/v1` (default)

## Authentication

Optional Bearer token authentication. Configure in `~/.hermes/config.yaml`:

```yaml
platforms:
  api_server:
    key: "your-secret-key"  # Optional, leave empty for local-only
```

If configured, include in requests:

```http
Authorization: Bearer your-secret-key
```

## Endpoints

### POST /v1/chat/completions

OpenAI-compatible chat completions endpoint.

**Request**:

```json
{
  "model": "hermes-agent",
  "messages": [
    {"role": "system", "content": "Optional system prompt"},
    {"role": "user", "content": "User message"}
  ],
  "stream": false
}
```

**Headers** (optional):
- `X-Hermes-Session-Id: <uuid>` - For session continuity

**Response**:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "hermes-agent",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Response text"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "total_tokens": 150
  }
}
```

**Response Headers**:
- `X-Hermes-Session-Id: <uuid>` - Session identifier for continuity

**Example**:

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8642/v1/chat/completions",
        json={
            "model": "hermes-agent",
            "messages": [
                {"role": "user", "content": "Hello, who are you?"}
            ]
        }
    )
    data = response.json()
    print(data["choices"][0]["message"]["content"])
```

### GET /health

Health check endpoint (no authentication required).

**Response**:

```json
{
  "status": "ok",
  "platform": "hermes-agent"
}
```

**Example**:

```bash
curl http://localhost:8642/health
```

### GET /v1/models

List available models.

**Response**:

```json
{
  "object": "list",
  "data": [
    {
      "id": "hermes-agent",
      "object": "model",
      "created": 1234567890,
      "owned_by": "hermes"
    }
  ]
}
```

## Session Management

Sessions enable conversation continuity:

1. **First Request**: No `X-Hermes-Session-Id` header
2. **Response**: Includes `X-Hermes-Session-Id` header
3. **Subsequent Requests**: Include the session ID header
4. **Persistence**: Sessions persist in `~/.hermes/state.db`

**Example Session Flow**:

```python
import httpx

async with httpx.AsyncClient(base_url="http://localhost:8642") as client:
    # First message
    response1 = await client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "My name is Alice"}]}
    )
    session_id = response1.headers["X-Hermes-Session-Id"]
    
    # Follow-up with context
    response2 = await client.post(
        "/v1/chat/completions",
        headers={"X-Hermes-Session-Id": session_id},
        json={"messages": [{"role": "user", "content": "What's my name?"}]}
    )
    # Response should mention "Alice"
```

## Error Handling

Errors follow OpenAI format:

```json
{
  "error": {
    "message": "Error description",
    "type": "invalid_request_error",
    "code": "error_code"
  }
}
```

**Common Error Codes**:

| Status | Code | Description |
|--------|------|-------------|
| 400 | `invalid_request_error` | Missing fields, malformed JSON |
| 401 | `invalid_api_key` | Invalid or missing API key (when auth enabled) |
| 413 | `request_too_large` | Request body exceeds 1MB |
| 500 | `server_error` | Internal server error |

**Example Error**:

```json
{
  "error": {
    "message": "Missing required field: messages",
    "type": "invalid_request_error",
    "param": "messages",
    "code": null
  }
}
```

## Rate Limits

- **Local Use**: No explicit rate limiting
- **Concurrent Runs**: `/v1/runs` endpoint limited to 10 concurrent runs
- **Session Requests**: No per-session limits

## Configuration Options

Configure API server in `~/.hermes/config.yaml`:

```yaml
platforms:
  api_server:
    enabled: true
    host: 127.0.0.1  # Listen address
    port: 8642       # Listen port
    key: ""          # Optional API key (empty = no auth)
    cors_origins: "" # CORS origins (* or specific URLs)

# Configure available tools
platform_toolsets:
  api_server:
    - web           # Web search and extraction
    - terminal      # Terminal command execution
    - file          # File operations
    - memory        # Memory management
    - session_search # Session history search
    - skills        # Custom skills
```

## Toolsets

Available toolsets for API requests:

| Toolset | Description |
|---------|-------------|
| `web` | Web search, URL extraction |
| `terminal` | Execute shell commands |
| `file` | Read, write, search files |
| `memory` | Persistent memory across sessions |
| `session_search` | Search conversation history |
| `skills` | Custom skill execution |
| `browser` | Browser automation |
| `delegate_task` | Spawn sub-agents |

Enable/disable toolsets in `config.yaml` or use `hermes tools` command.

## Python Client Example

```python
from infrastructure.external.hermes.hermes_client import HermesClient, HermesConfig

# Initialize client
config = HermesConfig(
    base_url="http://localhost:8642/v1",
    timeout=300,
    api_key=None  # Optional
)
client = HermesClient(config)

# Check health
is_healthy = await client.check_health()
if not is_healthy:
    print("Hermes API not available")

# Send message
result = await client.chat(
    message="What is ETF arbitrage?",
    session_id="my-session-123",
    system_prompt="You are a trading assistant."
)

print(result["content"])
print(f"Session: {result['session_id']}")
print(f"Tokens: {result['usage']['total_tokens']}")

# Close client
await client.close()
```

## Integration Patterns

### Stateless Queries

For one-off queries without session management:

```python
result = await client.chat("Quick question?")
# Each call gets a new session
```

### Stateful Conversations

For multi-turn conversations with context:

```python
session_id = None

# First turn
result1 = await client.chat("What is 2+2?", session_id=session_id)
session_id = result1["session_id"]

# Second turn (maintains context)
result2 = await client.chat("What did I just ask?", session_id=session_id)
```

### Custom System Prompts

Tailor the AI's behavior:

```python
result = await client.chat(
    message="Analyze this trade...",
    system_prompt="You are a quantitative trading analyst specializing in ETF arbitrage."
)
```

## Performance Considerations

- **Timeout**: Default 300 seconds (5 minutes), adjust based on query complexity
- **Concurrent Requests**: No client-side limits, server handles queuing
- **Session Storage**: Sessions persist to disk, minimal memory overhead
- **Response Size**: No explicit limits, but large responses may slow down

## Best Practices

1. **Reuse Sessions**: Continue conversations with same session ID for context
2. **Set Appropriate Timeouts**: Complex queries may take longer
3. **Handle Errors Gracefully**: Check for connection errors, API errors
4. **Close Connections**: Call `client.close()` when done
5. **Health Checks**: Verify API availability before critical operations
6. **System Prompts**: Use specific prompts for better results

## Monitoring

Check API server status:

```bash
# Health endpoint
curl http://localhost:8642/health

# Or use the health check script
python scripts/check_hermes_api.py
```

View logs:

```bash
# Gateway logs show API requests
tail -f ~/.hermes/logs/gateway.log
```

## Security Notes

- **Local Only**: Default configuration binds to 127.0.0.1 (localhost only)
- **No Auth by Default**: API key authentication is optional
- **Production Use**: Enable API key and use reverse proxy with TLS for external access
- **CORS**: Configure `cors_origins` for browser-based clients

## Troubleshooting

### Connection Refused

**Problem**: Cannot connect to `http://localhost:8642`

**Solution**: Start the gateway:
```bash
python -m gateway.run
```

### Timeout Errors

**Problem**: Requests timing out

**Solutions**:
- Increase client timeout: `HermesConfig(timeout=600)`
- Check gateway logs for errors
- Verify API server is not overloaded

### Session Not Found

**Problem**: Session ID not recognized

**Solutions**:
- Verify session ID is correct
- Check if session was cleared (restart clears sessions)
- Sessions expire after long inactivity

## Additional Resources

- [Integration Guide](../../Schwab-API/docs/HERMES_INTEGRATION.md) - Schwab-API integration example
- [Gateway Documentation](../gateway/README.md) - Gateway platform details
- [Tool Documentation](../tools/README.md) - Available tools and capabilities
