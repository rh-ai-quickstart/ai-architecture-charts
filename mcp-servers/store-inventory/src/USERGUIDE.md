# MCP Store Inventory User Guide

Usage guide for the lightweight MCP server that connects to Store Inventory APIs.

## Overview

MCP Store Inventory provides AI agents with inventory management tools by connecting to an external Store Inventory API. It acts as a bridge between the MCP protocol and REST APIs.

## Getting Started

### Prerequisites
1. **Running Store API**: You need a compatible Store Inventory API running (see [store-inventory](../store-inventory/))
2. **API Endpoint**: The URL of your Store API

### Quick Start
```bash
# Start Store API first (if using the provided one)
cd ../store-inventory
uvicorn main:app --port 8002

# Start MCP server in another terminal
cd ../mcp-store-inventory
STORE_API_URL="http://localhost:8002" python server.py
```

### Verify Connection
The MCP server will validate API connectivity on startup and provide health check capabilities.

## Available Tools

All tools proxy requests to the configured Store API:

### Product Management Tools

#### `get_products` - List Products
Retrieves products from the API with pagination support.

**Parameters:**
- `skip` (int, optional): Number of products to skip (default: 0)
- `limit` (int, optional): Maximum products to return (default: 100)

**Example:**
```python
# Get first 10 products
products = await get_products(skip=0, limit=10)

# Get all products (up to limit)
all_products = await get_products()
```

#### `get_product_by_id` - Get Product by ID
Fetches a specific product using its ID.

**Parameters:**
- `product_id` (int): The product's unique identifier

**Example:**
```python
product = await get_product_by_id(product_id=1)
```

#### `get_product_by_name` - Find Product by Name
Searches for a product by its exact name.

**Parameters:**
- `name` (str): Exact product name to search for

**Example:**
```python
laptop = await get_product_by_name(name="Gaming Laptop")
```

#### `search_products` - Search Products
Searches products using a query string against name and description.

**Parameters:**
- `query` (str): Search term
- `skip` (int, optional): Pagination offset (default: 0)
- `limit` (int, optional): Maximum results (default: 100)

**Example:**
```python
# Find gaming products
gaming_items = await search_products(query="gaming")

# Search with pagination
page_2 = await search_products(query="laptop", skip=10, limit=10)
```

#### `add_product` - Create Product
Adds a new product to the inventory via the API.

**Parameters:**
- `name` (str): Product name (required)
- `description` (str, optional): Product description
- `inventory` (int, optional): Initial stock (default: 0)
- `price` (float, optional): Product price (default: 0.0)

**Example:**
```python
new_product = await add_product(
    name="Wireless Headphones",
    description="Noise-cancelling Bluetooth headphones",
    inventory=25,
    price=199.99
)
```

#### `remove_product` - Delete Product
Removes a product from the inventory.

**Parameters:**
- `product_id` (int): ID of the product to remove

**Example:**
```python
removed = await remove_product(product_id=5)
```

### Order Management Tools

#### `order_product` - Place Order
Creates an order and reduces inventory automatically.

**Parameters:**
- `product_id` (int): ID of the product to order
- `quantity` (int): Number of items to order
- `customer_identifier` (str): Customer ID or identifier

**Example:**
```python
order = await order_product(
    product_id=1,
    quantity=2,
    customer_identifier="customer_789"
)
```

## Configuration

### Environment Variables

```bash
# Required: Store API endpoint
STORE_API_URL="http://store-api:8002"

# Optional: Server settings
MCP_PORT=8003                    # MCP server port
LOG_LEVEL=INFO                   # Logging level
TIMEOUT_SECONDS=30               # API request timeout
```

### API Compatibility

The MCP server expects the Store API to provide:

**Required Endpoints:**
- `GET /products/` - List products
- `POST /products/` - Create product
- `GET /products/id/{id}` - Get product by ID
- `GET /products/name/{name}` - Get product by name
- `GET /products/search/` - Search products
- `DELETE /products/{id}` - Delete product
- `POST /orders/` - Create order
- `GET /health` - Health check (recommended)

**Data Format:**
- JSON request/response bodies
- Standard HTTP status codes
- Compatible product and order models

## Usage Patterns

### AI Agent Integration

```mermaid
flowchart LR
    Agent[AI Agent] --> LlamaStack[LlamaStack]
    LlamaStack --> MCP[MCP Store Inventory]
    MCP -.->|HTTP| API[Store API]
    API --> DB[(Database)]

    style MCP fill:#e1f5fe
    style API fill:#e8f5e9
```

### Example Agent Conversation

**User:** "What gaming products do we have?"

**Agent Process:**
1. Calls `search_products(query="gaming")`
2. MCP server makes HTTP request to Store API
3. Returns formatted results to agent
4. Agent responds with product list

**User:** "Order 3 gaming mice for customer John"

**Agent Process:**
1. Calls `search_products(query="gaming mouse")` to find product
2. Calls `order_product(product_id=X, quantity=3, customer_identifier="john")`
3. Confirms order placement

## Error Handling

### Common Scenarios

#### API Unavailable
```python
# When Store API is down
try:
    products = await get_products()
except RuntimeError as e:
    if "API request failed" in str(e):
        print("Store API is currently unavailable")
```

#### Network Timeouts
```python
# Configure longer timeouts if needed
# Set TIMEOUT_SECONDS=60 environment variable
```

#### Invalid API Responses
The MCP server validates API responses and provides meaningful error messages when the API returns unexpected data.

## Integration Examples

### With Different Store APIs

#### Local Development
```bash
STORE_API_URL="http://localhost:8002" python server.py
```

#### Staging Environment
```bash
STORE_API_URL="https://staging-api.company.com/store" python server.py
```

#### Production with Authentication
```bash
STORE_API_URL="https://api.company.com/store" \
API_KEY="your-production-key" \
python server.py
```

### Docker Deployment
```bash
# With docker-compose
version: '3.8'
services:
  mcp-store-inventory:
    image: quay.io/ecosystem-appeng/mcp-store-inventory:latest
    ports: ["8003:8003"]
    environment:
      STORE_API_URL: "http://store-api:8002"
    depends_on: [store-api]

  store-api:
    image: quay.io/ecosystem-appeng/store-inventory:latest
    ports: ["8002:8002"]
    environment:
      DATABASE_URL: "postgresql+asyncpg://user:pass@db:5432/store_db"
```

### Kubernetes with Helm
```bash
# Deploy Store API first
helm install store-api ../store-inventory/helm

# Deploy MCP server
helm install mcp-inventory ./helm \
  --set env.STORE_API_URL="http://store-inventory:8002"
```

## Monitoring and Health

### Health Check
The MCP server provides a health endpoint:
```bash
curl http://localhost:8003/health
```

Response:
```json
{
  "status": "healthy",
  "service": "mcp-store-inventory",
  "store_api_status": "connected"
}
```

### Monitoring Points
- **API Connectivity**: Monitor connection to Store API
- **Response Times**: Track API call latency
- **Error Rates**: Monitor failed API requests
- **Tool Usage**: Track which MCP tools are called most

## Best Practices

### Performance
- **Connection Reuse**: The server maintains persistent HTTP connections
- **Timeout Configuration**: Set appropriate timeouts for your API
- **Error Handling**: Implement proper error handling in your agents

### Security
- **Network Security**: Use HTTPS for production API connections
- **Authentication**: Configure API keys or tokens if required
- **Access Control**: Limit network access between MCP server and API

### Reliability
- **Health Checks**: Monitor both MCP server and Store API health
- **Retry Logic**: The server includes basic retry logic for transient failures
- **Graceful Degradation**: Handle API unavailability gracefully

## Troubleshooting

### Server Won't Start
1. **Check API URL**: Verify `STORE_API_URL` is correct
2. **Test API**: `curl $STORE_API_URL/health`
3. **Check Logs**: Run with `LOG_LEVEL=DEBUG`

### Tools Not Working
1. **API Compatibility**: Ensure API provides expected endpoints
2. **Network Connectivity**: Test network path to API
3. **Authentication**: Verify API authentication if required

### Performance Issues
1. **API Performance**: Check Store API response times
2. **Network Latency**: Measure network latency to API
3. **Timeout Settings**: Adjust `TIMEOUT_SECONDS` if needed

## Advanced Configuration

### Custom API Headers
```python
# Modify server.py to add custom headers
async def make_api_request(method: str, endpoint: str, **kwargs):
    headers = kwargs.get('headers', {})
    headers.update({
        'User-Agent': 'MCP-Store-Inventory/1.0',
        'X-Client-ID': 'mcp-server'
    })
    kwargs['headers'] = headers
    # ... rest of function
```

### API Authentication
```python
# Add authentication to requests
if os.getenv('API_KEY'):
    headers['Authorization'] = f"Bearer {os.getenv('API_KEY')}"
```

For development and customization details, see the [Development Guide](dev-guide.md).
