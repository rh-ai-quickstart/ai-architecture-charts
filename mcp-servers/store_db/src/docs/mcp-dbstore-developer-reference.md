# MCP DBStore Developer Reference

## 🏗️ Architecture Overview

```
LLM Agent → MCP DBStore Server → PostgreSQL Database
           (FastMCP + SQLAlchemy)
```

**Key Components:**
- `store.py` - Main MCP server with 7 tools
- `database.py` - SQLAlchemy async setup
- `crud.py` - Database operations
- `models.py` - Pydantic schemas

## 🔧 Adding New Tools

### 1. Basic Tool Pattern
```python
@mcp_server.tool()
async def my_new_tool(param1: str, param2: int = 0) -> Dict[str, Any]:
    """
    Clear, specific description for LLM consumption.
    
    Parameters:
    - param1 (str, required): What this parameter does
    - param2 (int, optional): Default value explanation
    
    Returns:
    Dictionary with specific structure documented
    
    Example use cases:
    - "When user asks X"
    - "For Y operations"
    """
    async with database.AsyncSessionLocal() as session:
        try:
            result = await crud.my_crud_operation(session, param1, param2)
            await session.commit()
            return PydanticModels.MyModel.model_validate(result).model_dump()
        except Exception:
            await session.rollback()
            raise
```

### 2. Add CRUD Operation
```python
# In crud.py
async def my_crud_operation(db: AsyncSession, param1: str, param2: int):
    result = await db.execute(
        select(MyTable).filter(MyTable.field == param1)
    )
    return result.scalars().all()
```

### 3. Add Pydantic Model (if needed)
```python
# In models.py
class MyModel(BaseModel):
    id: int
    name: str
    
    class Config:
        from_attributes = True
```

## 📊 Database Patterns

### Async Session Management
```python
# Always use this pattern
async with database.AsyncSessionLocal() as session:
    try:
        # Your operations
        result = await crud.some_operation(session, params)
        await session.commit()
        return result
    except Exception:
        await session.rollback()
        raise
```

### Query Examples
```python
# Simple select
result = await session.execute(select(ProductDB).filter(ProductDB.id == product_id))
product = result.scalar_one_or_none()

# Join with aggregation  
result = await session.execute(
    select(ProductDB, func.count(OrderDB.id).label('order_count'))
    .outerjoin(OrderDB)
    .group_by(ProductDB.id)
)

# Update with validation
product = await get_product_by_id(session, product_id)
if not product:
    raise ValueError("Product not found")
product.price = new_price
```

## 🎯 Tool Design Best Practices

### 1. LLM-Friendly Descriptions
```python
# ✅ GOOD - Specific and actionable
"""
Updates the inventory quantity for a specific product.

Use this when inventory changes due to restocking, corrections, or
physical count updates. This does NOT create orders - use order_product
for sales transactions.

Parameters:
- product_id (int): The unique product identifier  
- new_quantity (int): New inventory count (must be >= 0)

Example use cases:
- "Update product 123 inventory to 50 units"
- "Set inventory for Super Widget to 0"
"""

# ❌ AVOID - Vague and technical
"""Updates product inventory in the database."""
```

### 2. Error Handling
```python
# Always validate inputs
if new_quantity < 0:
    raise ValueError("Inventory cannot be negative")

# Check business rules
if not product:
    raise ValueError(f"Product {product_id} not found")

# Handle database errors gracefully
try:
    await session.commit()
except IntegrityError:
    await session.rollback()
    raise ValueError("Product name already exists")
```

### 3. Transaction Safety
```python
# ✅ Atomic operations
async with database.AsyncSessionLocal() as session:
    try:
        # Multiple related operations
        product.inventory -= order_quantity
        order = OrderDB(...)
        session.add(order)
        await session.commit()  # All or nothing
    except Exception:
        await session.rollback()
        raise
```

## 📦 Building and Deployment

### Container Build
```bash
# Build image
docker build -t my-mcp-server ./mcpservers/mcp_dbstore

# Test locally
docker run -p 8002:8002 \
  -e DATABASE_URL="postgresql+asyncpg://..." \
  my-mcp-server
```

### Helm Customization
```yaml
# values-custom.yaml
mcpServer:
  image:
    repository: my-registry/my-mcp-server
    tag: "1.0.0"
  replicaCount: 2
  
postgresql:
  persistence:
    size: 10Gi
```

```bash
helm install my-server ./deploy/helm/mcp-dbstore -f values-custom.yaml
```

## 🔄 Creating New MCP Servers

### Server Template
```python
# my_domain_server/server.py
from mcp.server.fastmcp import FastMCP

mcp_server = FastMCP()

@mcp_server.tool()
async def domain_specific_tool() -> Dict[str, Any]:
    """Tool description for your domain"""
    # Implementation

if __name__ == "__main__":
    print("Starting My Domain MCP Server...")
    mcp_server.settings.port = 8003
    mcp_server.run(transport="sse")
```

### Domain Examples
- **Customer Management**: create_customer, get_customer_orders, update_preferences
- **File Operations**: list_files, read_file, create_backup
- **Analytics**: generate_report, get_metrics, export_data

## 🔍 Resources (Future)

MCP supports "resources" in addition to tools:

```python
@mcp_server.resource("product-catalog")
async def product_catalog_resource() -> str:
    """Complete product catalog as text resource for LLM context"""
    products = await get_all_products()
    return format_as_catalog_text(products)
```

## 🚨 Common Issues

### Port Conflicts
```bash
# Check what's using port 8002
lsof -i :8002
# Use different port
mcp_server.settings.port = 8003
```

### Database Connection
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"
# Check environment
echo $DATABASE_URL
```

### Import Errors
```python
# Ensure PYTHONPATH includes parent directory
import sys
sys.path.append('/app')
from mcpservers.mcp_dbstore import crud
```

## 📚 Key References

- **MCP Protocol**: https://modelcontextprotocol.io/docs/
- **FastMCP**: https://github.com/jlowin/fastmcp  
- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Pydantic**: https://docs.pydantic.dev/

---

**Quick Tip**: Start by copying an existing tool pattern, then modify for your specific use case. The `get_product_by_id` and `add_product` tools are good templates for read and write operations respectively. 