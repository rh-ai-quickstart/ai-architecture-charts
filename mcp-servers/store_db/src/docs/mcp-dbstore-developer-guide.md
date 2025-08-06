# MCP DBStore Developer Guide

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Component Deep Dive](#component-deep-dive)
- [Development Setup](#development-setup)
- [Extending the Server](#extending-the-server)
- [Creating New MCP Servers](#creating-new-mcp-servers)
- [Best Practices](#best-practices)
- [Testing](#testing)
- [Deployment Patterns](#deployment-patterns)

## Architecture Overview

The MCP DBStore server implements the Model Context Protocol using the FastMCP framework, providing a database-backed inventory management system for AI agents.

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   LLM Agent     │    │   MCP DBStore    │    │   PostgreSQL    │
│                 │    │     Server       │    │    Database     │
│ - Tool Calls    │◄──►│ - FastMCP        │◄──►│ - Products      │
│ - Context       │    │ - SQLAlchemy     │    │ - Orders        │
│ - Responses     │    │ - Async Tools    │    │ - ACID          │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                        ▲                       ▲
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Llama Stack    │    │   Kubernetes     │    │  Persistent     │
│                 │    │                  │    │   Storage       │
│ - Tool Registry │    │ - Services       │    │ - Volume        │
│ - Agent Config  │    │ - Deployments    │    │ - Backup        │
│ - Auto-Discovery│    │ - Secrets        │    │ - Recovery      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Protocol** | Model Context Protocol | Standardized agent-tool communication |
| **Framework** | FastMCP | High-performance async MCP server |
| **Runtime** | Python 3.10+ | Application runtime environment |
| **Database** | PostgreSQL 15 | Persistent data storage |
| **ORM** | SQLAlchemy | Database abstraction and operations |
| **Container** | Docker/Podman | Application containerization |
| **Orchestration** | Kubernetes | Container orchestration and scaling |
| **Package Manager** | Helm | Kubernetes application deployment |

### Data Flow

1. **Tool Registration**: MCP server registers tools with Llama Stack
2. **Agent Request**: LLM agent sends tool call via MCP protocol
3. **Validation**: FastMCP validates parameters and schemas  
4. **Database Operation**: SQLAlchemy executes async database queries
5. **Response**: Structured data returned via MCP protocol
6. **Agent Processing**: LLM agent processes results for user

## Development Setup

### Local Development Environment

```bash
# Clone repository
git clone https://github.com/yourusername/ai-virtual-assistant.git
cd ai-virtual-assistant/mcpservers/mcp_dbstore

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up local PostgreSQL
docker run --name dev-postgres \
  -e POSTGRES_USER=mcpuser \
  -e POSTGRES_PASSWORD=mcppassword \
  -e POSTGRES_DB=store_db \
  -p 5432:5432 \
  -d postgres:15-alpine

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://mcpuser:mcppassword@localhost:5432/store_db"

# Initialize database with sample data
psql $DATABASE_URL -f populate_db.sql

# Run the MCP server
python -m mcpservers.mcp_dbstore.store
```

### Development Tools

#### MCP Inspector

```bash
# Install MCP inspector for testing
pip install mcp-inspector

# Test your server
mcp-inspector http://localhost:8002

# Interactive tool testing
# - Browse tools
# - Test parameters  
# - View responses
# - Debug issues
```

#### Database Tools

```bash
# Connect to development database
psql $DATABASE_URL

# Useful queries for development
\dt                          # List tables
\d products                  # Describe products table
SELECT * FROM products;      # View all products
SELECT * FROM orders;        # View all orders
```

### IDE Configuration

#### VS Code Settings

```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

#### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << EOF
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
EOF

# Install hooks
pre-commit install
```

## Extending the Server

### Adding New Tools

#### 1. Define Tool Function

```python
@mcp_server.tool()
async def update_product_price(product_id: int, new_price: float) -> Dict[str, Any]:
    """
    Updates the price of a specific product.
    
    This tool modifies the price of an existing product in the inventory system.
    Useful for price adjustments, promotions, or market changes.
    
    Parameters:
    - product_id (int, required): The unique identifier of the product
    - new_price (float, required): The new price in USD (must be positive)
    
    Returns:
    Updated product dictionary with new price information
    
    Error conditions:
    - ValueError: Product not found or invalid price
    """
    if new_price < 0:
        raise ValueError("Price must be non-negative")
    
    async with database.AsyncSessionLocal() as session:
        try:
            db_product = await crud.get_product_by_id(session, product_id=product_id)
            if not db_product:
                raise ValueError("Product not found")
            
            db_product.price = new_price
            await session.commit()
            await session.refresh(db_product)
            
            return PydanticModels.Product.model_validate(db_product).model_dump()
        except Exception:
            await session.rollback()
            raise
```

#### 2. Add CRUD Operation

```python
# In crud.py
async def update_product_price(db: AsyncSession, product_id: int, new_price: float):
    """Update product price with validation"""
    result = await db.execute(select(ProductDB).filter(ProductDB.id == product_id))
    product = result.scalar_one_or_none()
    
    if not product:
        raise ValueError("Product not found")
    
    product.price = new_price
    return product
```

#### 3. Update Pydantic Models (if needed)

```python
# In models.py
class ProductPriceUpdate(BaseModel):
    """Schema for price update operations"""
    product_id: int
    new_price: float
    
    @validator('new_price')
    def price_must_be_positive(cls, v):
        if v < 0:
            raise ValueError('Price must be non-negative')
        return v
```

### Advanced Tool Patterns

#### Batch Operations

```python
@mcp_server.tool()
async def bulk_update_inventory(updates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Updates inventory for multiple products in a single transaction.
    
    Parameters:
    - updates: List of {"product_id": int, "new_inventory": int} objects
    
    Returns:
    Summary of successful and failed updates
    """
    results = {"successful": [], "failed": []}
    
    async with database.AsyncSessionLocal() as session:
        try:
            for update in updates:
                try:
                    product = await crud.get_product_by_id(session, update["product_id"])
                    if product:
                        product.inventory = update["new_inventory"]
                        results["successful"].append(update["product_id"])
                    else:
                        results["failed"].append({
                            "product_id": update["product_id"],
                            "error": "Product not found"
                        })
                except Exception as e:
                    results["failed"].append({
                        "product_id": update["product_id"],
                        "error": str(e)
                    })
            
            await session.commit()
            return results
        except Exception:
            await session.rollback()
            raise
```

#### Analytics Tools

```python
@mcp_server.tool()
async def get_inventory_analytics() -> Dict[str, Any]:
    """
    Provides comprehensive inventory analytics and insights.
    
    Returns detailed analytics including:
    - Total products and inventory value
    - Low stock alerts
    - Top selling products (by order volume)
    - Price distribution analysis
    """
    async with database.AsyncSessionLocal() as session:
        # Total inventory value
        result = await session.execute(
            select(func.sum(ProductDB.price * ProductDB.inventory))
        )
        total_value = result.scalar() or 0
        
        # Low stock products
        low_stock = await session.execute(
            select(ProductDB).filter(ProductDB.inventory < 25)
        )
        low_stock_products = low_stock.scalars().all()
        
        # Order analytics
        order_stats = await session.execute(
            select(
                ProductDB.name,
                func.sum(OrderDB.quantity).label('total_ordered')
            )
            .join(OrderDB)
            .group_by(ProductDB.id, ProductDB.name)
            .order_by(func.sum(OrderDB.quantity).desc())
            .limit(5)
        )
        
        return {
            "total_value": float(total_value),
            "low_stock_count": len(low_stock_products),
            "low_stock_products": [p.name for p in low_stock_products],
            "top_selling": [
                {"product": row.name, "total_ordered": row.total_ordered}
                for row in order_stats
            ]
        }
```

## Creating New MCP Servers

### MCP Server Template

Use this template to create new domain-specific MCP servers:

```python
# my_new_server/server.py
from mcp.server.fastmcp import FastMCP
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from . import crud, models, database
import asyncio

mcp_server = FastMCP()

@mcp_server.tool()
async def my_first_tool(param1: str, param2: int = 0) -> Dict[str, Any]:
    """
    Comprehensive tool description for LLM consumption.
    
    Detailed explanation of what this tool does, when to use it,
    and what results to expect.
    
    Parameters:
    - param1 (str, required): Description of parameter
    - param2 (int, optional): Description with default value
    
    Returns:
    Dictionary containing specific result structure
    
    Example use cases:
    - "Use case 1"
    - "Use case 2"
    
    Error conditions:
    - Specific error scenarios
    """
    async with database.AsyncSessionLocal() as session:
        try:
            # Your business logic here
            result = await crud.my_crud_operation(session, param1, param2)
            return models.MyModel.model_validate(result).model_dump()
        except Exception:
            await session.rollback()
            raise

# Startup tasks
async def run_startup_tasks():
    print("INFO:     My MCP Server startup tasks beginning...")
    await database.create_db_and_tables()
    print("INFO:     Database tables checked/created.")
    print("INFO:     My MCP Server initialization complete.")

if __name__ == "__main__":
    asyncio.run(run_startup_tasks())
    print("INFO:     Starting My MCP Server on port 8003...")
    mcp_server.settings.port = 8003
    mcp_server.run(transport="sse")
```

### Domain-Specific Examples

#### Customer Management MCP Server

```python
# Tools for customer management
@mcp_server.tool()
async def create_customer(name: str, email: str, phone: str = None) -> Dict[str, Any]:
    """Create a new customer record with contact information."""
    # Implementation here

@mcp_server.tool()
async def get_customer_orders(customer_id: int) -> List[Dict[str, Any]]:
    """Retrieve all orders for a specific customer."""
    # Implementation here

@mcp_server.tool()
async def update_customer_preferences(customer_id: int, preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Update customer preferences and settings."""
    # Implementation here
```

#### File Management MCP Server

```python
# Tools for file operations
@mcp_server.tool()
async def list_files(directory: str, pattern: str = "*") -> List[Dict[str, Any]]:
    """List files in a directory with optional pattern matching."""
    # Implementation here

@mcp_server.tool()
async def read_file_content(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """Read and return file content with metadata."""
    # Implementation here

@mcp_server.tool()
async def create_backup(source_path: str, backup_name: str) -> Dict[str, Any]:
    """Create a backup of specified files or directories."""
    # Implementation here
```

### Resources Concept

MCP servers can also expose "resources" in addition to tools. Resources represent data or content that can be read by agents:

```python
from mcp.server.fastmcp import FastMCP

mcp_server = FastMCP()

@mcp_server.resource("product-catalog")
async def product_catalog_resource() -> str:
    """
    Provides the complete product catalog as a searchable resource.
    
    This resource contains all products in a structured format that
    agents can read and reference for context.
    """
    async with database.AsyncSessionLocal() as session:
        products = await crud.get_products(session, skip=0, limit=1000)
        
        catalog_text = "PRODUCT CATALOG\n\n"
        for product in products:
            catalog_text += f"ID: {product.id}\n"
            catalog_text += f"Name: {product.name}\n"
            catalog_text += f"Description: {product.description}\n"
            catalog_text += f"Price: ${product.price}\n"
            catalog_text += f"Inventory: {product.inventory}\n\n"
        
        return catalog_text

@mcp_server.resource("inventory-report")
async def inventory_report_resource() -> str:
    """
    Generates a real-time inventory status report.
    """
    # Generate comprehensive inventory report
    pass
```

## Best Practices

### Tool Design

#### 1. Comprehensive Descriptions

```python
@mcp_server.tool()
async def example_tool(param: str) -> Dict[str, Any]:
    """
    [GOOD] Comprehensive description with:
    
    Clear purpose statement explaining what the tool does and why an LLM
    would want to use it in different scenarios.
    
    Parameters:
    - param (str, required): Detailed parameter explanation with constraints
    
    Returns:
    Structured description of return value format and meaning
    
    Example use cases:
    - "When user asks about X"
    - "For analyzing Y data"
    
    Error conditions:
    - Specific error scenarios and handling
    """
```

#### 2. Error Handling

```python
async def robust_tool(id: int) -> Dict[str, Any]:
    """Tool with proper error handling patterns"""
    async with database.AsyncSessionLocal() as session:
        try:
            # Validate input
            if id <= 0:
                raise ValueError("ID must be positive integer")
            
            # Perform operation
            result = await crud.get_item(session, id)
            if not result:
                raise ValueError(f"Item with ID {id} not found")
            
            # Commit and return
            await session.commit()
            return result.to_dict()
            
        except ValueError:
            # Re-raise validation errors
            await session.rollback()
            raise
        except Exception as e:
            # Handle unexpected errors
            await session.rollback()
            raise RuntimeError(f"Unexpected error: {str(e)}")
```

#### 3. Transaction Management

```python
async def transactional_tool(operations: List[Dict]) -> Dict[str, Any]:
    """Tool demonstrating proper transaction handling"""
    async with database.AsyncSessionLocal() as session:
        try:
            results = []
            
            # Perform all operations in single transaction
            for op in operations:
                result = await crud.perform_operation(session, op)
                results.append(result)
            
            # Commit all changes atomically
            await session.commit()
            
            # Refresh all objects after commit
            for result in results:
                await session.refresh(result)
            
            return {"success": True, "results": results}
            
        except Exception:
            # Rollback on any error
            await session.rollback()
            raise
```

### Performance Optimization

#### 1. Database Queries

```python
# GOOD: Efficient query with proper joins
async def get_products_with_orders(db: AsyncSession):
    result = await db.execute(
        select(ProductDB, func.count(OrderDB.id).label('order_count'))
        .outerjoin(OrderDB)
        .group_by(ProductDB.id)
        .options(selectinload(ProductDB.orders))  # Eager loading
    )
    return result.all()

# BAD: N+1 query problem
async def get_products_with_orders_bad(db: AsyncSession):
    products = await db.execute(select(ProductDB))
    for product in products.scalars():
        # This executes a query for each product!
        orders = await db.execute(
            select(OrderDB).filter(OrderDB.product_id == product.id)
        )
```

#### 2. Connection Pooling

```python
# Configure connection pool for production
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,          # Base number of connections
    max_overflow=30,       # Additional connections under load
    pool_pre_ping=True,    # Validate connections
    pool_recycle=3600,     # Recycle connections hourly
)
```

#### 3. Caching

```python
from functools import lru_cache
import aioredis

# Simple in-memory cache
@lru_cache(maxsize=100)
def get_cached_config(key: str) -> str:
    """Cache configuration values"""
    return os.getenv(key, "")

# Redis-based async cache
async def get_cached_product(product_id: int) -> Optional[Dict]:
    """Get product from cache or database"""
    redis = await aioredis.from_url("redis://localhost")
    
    # Try cache first
    cached = await redis.get(f"product:{product_id}")
    if cached:
        return json.loads(cached)
    
    # Fall back to database
    async with database.AsyncSessionLocal() as session:
        product = await crud.get_product_by_id(session, product_id)
        if product:
            product_dict = product.to_dict()
            # Cache for 1 hour
            await redis.setex(f"product:{product_id}", 3600, json.dumps(product_dict))
            return product_dict
    
    return None
```

### Security Considerations

#### 1. Input Validation

```python
from pydantic import validator, Field

class SecureProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0, le=999999.99)
    inventory: int = Field(..., ge=0, le=1000000)
    
    @validator('name')
    def name_must_be_alphanumeric(cls, v):
        if not re.match(r'^[a-zA-Z0-9\s\-_]+$', v):
            raise ValueError('Name contains invalid characters')
        return v
```

#### 2. SQL Injection Prevention

```python
# GOOD: Using SQLAlchemy ORM (prevents SQL injection)
async def safe_search(db: AsyncSession, query: str):
    result = await db.execute(
        select(ProductDB).filter(ProductDB.name.ilike(f"%{query}%"))
    )
    return result.scalars().all()

# BAD: Raw SQL (vulnerable to injection)
async def unsafe_search(db: AsyncSession, query: str):
    # NEVER DO THIS!
    result = await db.execute(f"SELECT * FROM products WHERE name LIKE '%{query}%'")
    return result.fetchall()
```

#### 3. Rate Limiting

```python
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    async def is_allowed(self, client_id: str) -> bool:
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        # Record this request
        self.requests[client_id].append(now)
        return True

# Usage in tool
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)

@mcp_server.tool()
async def rate_limited_tool(client_id: str, data: str) -> Dict[str, Any]:
    if not await rate_limiter.is_allowed(client_id):
        raise ValueError("Rate limit exceeded. Please try again later.")
    
    # Tool implementation
    pass
```

## Testing

### Unit Testing

```python
# tests/test_tools.py
import pytest
from unittest.mock import AsyncMock, patch
from mcpservers.mcp_dbstore import store, crud, database

@pytest.fixture
async def db_session():
    """Mock database session for testing"""
    session = AsyncMock()
    yield session

@pytest.mark.asyncio
async def test_get_products(db_session):
    """Test get_products tool"""
    # Mock database response
    mock_products = [
        MockProduct(id=1, name="Test Product", price=10.0, inventory=100)
    ]
    
    with patch('mcpservers.mcp_dbstore.crud.get_products', return_value=mock_products):
        with patch('mcpservers.mcp_dbstore.database.AsyncSessionLocal', return_value=db_session):
            result = await store.get_products(skip=0, limit=10)
            
            assert len(result) == 1
            assert result[0]['name'] == "Test Product"
            assert result[0]['price'] == 10.0

@pytest.mark.asyncio
async def test_order_product_insufficient_inventory(db_session):
    """Test order processing with insufficient inventory"""
    with patch('mcpservers.mcp_dbstore.crud.order_product', side_effect=ValueError("Insufficient inventory")):
        with patch('mcpservers.mcp_dbstore.database.AsyncSessionLocal', return_value=db_session):
            with pytest.raises(ValueError, match="Insufficient inventory"):
                await store.order_product(product_id=1, quantity=999, customer_identifier="test")
```

### Integration Testing

```python
# tests/test_integration.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from mcpservers.mcp_dbstore import database, crud

@pytest.fixture(scope="session")
async def test_db():
    """Create test database"""
    engine = create_async_engine("postgresql+asyncpg://test:test@localhost:5433/test_db")
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_full_product_lifecycle(test_db):
    """Test complete product lifecycle"""
    async with AsyncSession(test_db) as session:
        # Create product
        product_data = {
            "name": "Test Widget",
            "description": "A test widget",
            "price": 25.99,
            "inventory": 50
        }
        product = await crud.add_product(session, product_data)
        await session.commit()
        
        # Retrieve product
        retrieved = await crud.get_product_by_id(session, product.id)
        assert retrieved.name == "Test Widget"
        
        # Place order
        order = await crud.order_product(session, {
            "product_id": product.id,
            "quantity": 5,
            "customer_identifier": "test-customer"
        })
        await session.commit()
        
        # Verify inventory updated
        updated_product = await crud.get_product_by_id(session, product.id)
        assert updated_product.inventory == 45
```

### Load Testing

```python
# tests/test_load.py
import asyncio
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

async def make_request(session, url, data):
    """Make single API request"""
    async with session.post(url, json=data) as response:
        return await response.json()

async def load_test_get_products(base_url: str, concurrent_requests: int = 50):
    """Load test the get_products endpoint"""
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(concurrent_requests):
            task = make_request(
                session,
                f"{base_url}/tools/get_products",
                {"skip": i * 10, "limit": 10}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
    end_time = time.time()
    
    # Analyze results
    successful = len([r for r in responses if not isinstance(r, Exception)])
    failed = len([r for r in responses if isinstance(r, Exception)])
    
    print(f"Load Test Results:")
    print(f"  Total requests: {concurrent_requests}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Duration: {end_time - start_time:.2f}s")
    print(f"  Requests/second: {concurrent_requests / (end_time - start_time):.2f}")

if __name__ == "__main__":
    asyncio.run(load_test_get_products("http://localhost:8002"))
```

## Deployment Patterns

### Development Deployment

```bash
# Quick development setup
docker-compose up -d postgres
export DATABASE_URL="postgresql+asyncpg://mcpuser:mcppassword@localhost:5432/store_db"
python -m mcpservers.mcp_dbstore.store
```

### Staging Deployment

```yaml
# values-staging.yaml
mcpServer:
  replicaCount: 2
  resources:
    limits:
      memory: 512Mi
      cpu: 500m
postgresql:
  persistence:
    size: 5Gi
  resources:
    limits:
      memory: 1Gi
      cpu: 500m
monitoring:
  enabled: true
```

### Production Deployment

```yaml
# values-production.yaml
mcpServer:
  replicaCount: 5
  resources:
    limits:
      memory: 2Gi
      cpu: 1000m
    requests:
      memory: 1Gi
      cpu: 500m
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
            - key: app.kubernetes.io/name
              operator: In
              values:
              - mcp-dbstore
          topologyKey: kubernetes.io/hostname

postgresql:
  persistence:
    enabled: true
    size: 100Gi
    storageClass: fast-ssd
  resources:
    limits:
      memory: 4Gi
      cpu: 2000m
  auth:
    password: "$(kubectl get secret prod-db-secret -o jsonpath='{.data.password}' | base64 -d)"

monitoring:
  enabled: true
  serviceMonitor:
    enabled: true

podDisruptionBudget:
  enabled: true
  minAvailable: 2
```

### Multi-Environment Pipeline

```bash
#!/bin/bash
# deploy.sh - Multi-environment deployment script

ENVIRONMENT=${1:-dev}
NAMESPACE="mcp-${ENVIRONMENT}"

echo "Deploying to ${ENVIRONMENT} environment..."

# Create namespace if it doesn't exist
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Deploy with environment-specific values
helm upgrade --install mcp-dbstore-${ENVIRONMENT} ./deploy/helm/mcp-dbstore \
  --namespace ${NAMESPACE} \
  --values ./deploy/helm/mcp-dbstore/values-${ENVIRONMENT}.yaml \
  --wait --timeout=600s

# Verify deployment
kubectl get pods -n ${NAMESPACE} -l app.kubernetes.io/name=mcp-dbstore

echo "Deployment to ${ENVIRONMENT} complete!"
```

---

## Resources and References

### Documentation
- [Model Context Protocol Specification](https://modelcontextprotocol.io/docs/)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Pydantic Models](https://docs.pydantic.dev/)

### Tools
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [Llama Stack](https://github.com/meta-llama/llama-stack)
- [PostgreSQL](https://www.postgresql.org/docs/)
- [Kubernetes](https://kubernetes.io/docs/)

### Best Practices
- [12-Factor App](https://12factor.net/)
- [Python Async Programming](https://docs.python.org/3/library/asyncio.html)
- [Database Design Patterns](https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)

This developer guide provides the foundation for building robust, scalable MCP servers that integrate seamlessly with the Llama Stack ecosystem. Use these patterns and practices to create powerful tools for AI agents in your specific domain. 