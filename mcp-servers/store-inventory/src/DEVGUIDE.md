# MCP Store Inventory Development Guide

Development setup for the lightweight Store API.

## Development Setup

### Prerequisites
- Python 3.12+
- Running Store Inventory API (see [store-inventory](../store-inventory/))

### Local Environment Setup

1. **Clone and Navigate**
   ```bash
   git clone <repository>
   cd mcpservers/mcp-store-inventory
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Store API** (in another terminal)
   ```bash
   cd ../store-inventory
   uvicorn main:app --port 8002 --reload
   ```

4. **Run MCP Server**
   ```bash
   STORE_API_URL="http://localhost:8002" python server.py
   ```

## Project Structure

```
mcp-store-inventory/
├── server.py             # Main MCP server
├── requirements.txt      # Python dependencies
├── Containerfile         # Container build
└── helm/                # Kubernetes deployment
```

## Development Workflow

### Running with Different APIs

```bash
# Local development API
STORE_API_URL="http://localhost:8002" python server.py

# Remote API
STORE_API_URL="https://api.example.com/store" python server.py

# With authentication (if needed)
STORE_API_URL="http://localhost:8002" \
API_KEY="your-key" \
python server.py
```

### Testing API Integration

```bash
# Test API connectivity
curl http://localhost:8002/health

# Test MCP server
python -c "
import asyncio
from server import get_products
print(asyncio.run(get_products()))
"
```

## Architecture Details

### HTTP Client Management
```python
# Efficient connection pooling
import httpx

async_client = httpx.AsyncClient(
    timeout=30.0,
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
)
```

### Error Handling Strategy
```python
async def make_api_request(method: str, endpoint: str, **kwargs):
    try:
        response = await async_client.request(method, f"{STORE_API_URL}{endpoint}", **kwargs)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        # Handle network errors
        raise RuntimeError(f"API request failed: {e}")
    except Exception as e:
        # Handle other errors
        raise RuntimeError(f"Unexpected error: {e}")
```

## Adding New Tools

### 1. Add Tool Function
```python
@mcp_server.tool()
async def new_inventory_tool(param1: str, param2: int) -> Dict[str, Any]:
    """Tool description for LLM reasoning.

    Args:
        param1: Description of parameter
        param2: Another parameter

    Returns:
        API response data
    """
    return await make_api_request(
        "GET",
        f"/new-endpoint/?param1={param1}&param2={param2}"
    )
```

### 2. Test the Tool
```python
# Test manually
async def test_new_tool():
    result = await new_inventory_tool("test", 123)
    print(result)

import asyncio
asyncio.run(test_new_tool())
```

## Container Development

### Building and Testing
```bash
# Build container
docker build -t mcp-store-inventory:dev .

# Test with local API
docker run --rm -p 8003:8003 \
  -e STORE_API_URL="http://host.docker.internal:8002" \
  mcp-store-inventory:dev

# Test with docker-compose
cat > docker-compose.dev.yml << EOF
services:
  store-api:
    build: ../store-inventory
    ports: ["8002:8002"]
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:password@db:5432/store_db
    depends_on: [db]

  mcp-inventory:
    build: .
    ports: ["8003:8003"]
    environment:
      STORE_API_URL: http://store-api:8002
    depends_on: [store-api]

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: store_db
EOF

docker-compose -f docker-compose.dev.yml up
```

## Testing Strategy

### Unit Tests
```python
import pytest
from unittest.mock import patch, AsyncMock
import httpx

@pytest.mark.asyncio
async def test_get_products():
    mock_response = AsyncMock()
    mock_response.json.return_value = [{"id": 1, "name": "Test Product"}]
    mock_response.raise_for_status.return_value = None

    with patch('server.async_client.request', return_value=mock_response):
        from server import get_products
        result = await get_products()
        assert len(result) == 1
        assert result[0]["name"] == "Test Product"

@pytest.mark.asyncio
async def test_api_error_handling():
    with patch('server.async_client.request') as mock_request:
        mock_request.side_effect = httpx.HTTPError("Connection failed")

        from server import get_products
        with pytest.raises(RuntimeError, match="API request failed"):
            await get_products()
```

### Integration Tests
```python
import pytest
import httpx

@pytest.mark.integration
async def test_with_real_api():
    """Test against running Store API"""
    # Assumes Store API is running on localhost:8002
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8002/health")
        assert response.status_code == 200

    # Now test MCP tools
    from server import get_products
    result = await get_products()
    assert isinstance(result, list)
```

## Debugging

### Common Issues

1. **API Connection Errors**
   ```bash
   # Check API availability
   curl $STORE_API_URL/health

   # Check network connectivity
   ping api-hostname

   # Test with verbose logging
   LOG_LEVEL=DEBUG STORE_API_URL="http://localhost:8002" python server.py
   ```

2. **Timeout Issues**
   ```python
   # Adjust timeout in server.py
   async_client = httpx.AsyncClient(timeout=60.0)  # Increase timeout
   ```

3. **Authentication Issues**
   ```python
   # Add authentication headers if needed
   async def make_api_request(method: str, endpoint: str, **kwargs):
       headers = kwargs.get('headers', {})
       if os.getenv('API_KEY'):
           headers['Authorization'] = f"Bearer {os.getenv('API_KEY')}"
       kwargs['headers'] = headers
       # ... rest of function
   ```

### Debug Mode
```python
# Add to server.py for debugging
import logging
logging.basicConfig(level=logging.DEBUG)

# Log all HTTP requests
async_client = httpx.AsyncClient(
    timeout=30.0,
    event_hooks={
        'request': [lambda request: print(f"Request: {request.method} {request.url}")],
        'response': [lambda response: print(f"Response: {response.status_code}")]
    }
)
```

## Performance Optimization

### Connection Pooling
```python
# Optimize for high throughput
async_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
        keepalive_expiry=30
    )
)
```

### Caching (if appropriate)
```python
from functools import lru_cache
import asyncio
import time

# Simple in-memory cache for relatively static data
_cache = {}
_cache_ttl = {}

async def cached_get_products(ttl_seconds=60):
    now = time.time()
    if 'products' in _cache and now - _cache_ttl.get('products', 0) < ttl_seconds:
        return _cache['products']

    result = await get_products()
    _cache['products'] = result
    _cache_ttl['products'] = now
    return result
```

## Helm Chart Development

### Local Testing
```bash
# Lint chart
helm lint ./helm

# Template with values
helm template test-release ./helm \
  --set env.STORE_API_URL="http://store-inventory:8002"

# Install for testing
helm install mcp-inventory-dev ./helm \
  --set image.tag=dev \
  --set env.STORE_API_URL="http://store-inventory:8002"
```

### Chart Values
```yaml
# values-dev.yaml
image:
  tag: dev
  pullPolicy: Never

env:
  STORE_API_URL: "http://localhost:8002"
  LOG_LEVEL: "DEBUG"

resources:
  requests:
    memory: "32Mi"
    cpu: "10m"
  limits:
    memory: "64Mi"
    cpu: "100m"
```

## Contributing

### Code Style
- Keep the server lightweight and focused
- Use async/await consistently
- Add comprehensive error handling
- Include detailed docstrings for MCP tools

### Adding Features
1. Ensure the Store API supports the new endpoint
2. Add the MCP tool function
3. Add tests for the new functionality
4. Update documentation

### Pull Request Checklist
- [ ] Tests pass with live Store API
- [ ] Container builds successfully
- [ ] Helm chart validates
- [ ] Documentation updated
- [ ] Error handling implemented

This development guide focuses on the unique aspects of building an API-client MCP server.
