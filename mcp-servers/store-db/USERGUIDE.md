# MCP DBStore User Guide

This guide provides practical examples and usage instructions for the MCP DBStore server.

## Getting Started

MCP DBStore provides AI agents with direct database access for inventory management. It's the simplest option when you need straightforward product and order operations.

### Quick Setup

1. **Start the Server**
   ```bash
   cd mcpservers/mcp-store-db
   python store.py
   ```

2. **Verify Connection**
   The server will start on port 8002 and automatically create database tables.

3. **Add to LlamaStack**
   Configure your AI agent to use the MCP DBStore tools.

## Available Tools

### Product Management

#### `get_products` - List Products
Retrieve all products with optional pagination.

**Parameters:**
- `skip` (int, optional): Number of products to skip (default: 0)
- `limit` (int, optional): Maximum products to return (default: 100)

**Example Usage:**
```python
# Get first 10 products
products = await get_products(skip=0, limit=10)

# Get all products (up to default limit)
all_products = await get_products()
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Laptop",
    "description": "High-performance laptop",
    "inventory": 50,
    "price": 999.99
  }
]
```

#### `get_product_by_id` - Get Specific Product
Retrieve a product by its unique ID.

**Parameters:**
- `product_id` (int): The product's unique identifier

**Example Usage:**
```python
# Get product with ID 1
product = await get_product_by_id(product_id=1)
```

**Response:**
```json
{
  "id": 1,
  "name": "Laptop",
  "description": "High-performance laptop",
  "inventory": 50,
  "price": 999.99
}
```

#### `get_product_by_name` - Get Product by Name
Find a product using its exact name.

**Parameters:**
- `name` (str): Exact product name to search for

**Example Usage:**
```python
# Find laptop product
product = await get_product_by_name(name="Laptop")
```

#### `search_products` - Search Products
Search products by name or description content.

**Parameters:**
- `query` (str): Search term to match against name/description
- `skip` (int, optional): Pagination offset (default: 0)
- `limit` (int, optional): Maximum results (default: 100)

**Example Usage:**
```python
# Search for electronics
electronics = await search_products(query="laptop")

# Search with pagination
page_2 = await search_products(query="phone", skip=10, limit=10)
```

#### `add_product` - Create Product
Add a new product to the inventory.

**Parameters:**
- `name` (str): Product name (required)
- `description` (str, optional): Product description
- `inventory` (int, optional): Initial stock quantity (default: 0)
- `price` (float, optional): Product price (default: 0.0)

**Example Usage:**
```python
# Add a new product
new_product = await add_product(
    name="Wireless Mouse",
    description="Ergonomic wireless mouse with long battery life",
    inventory=100,
    price=29.99
)
```

**Response:**
```json
{
  "id": 2,
  "name": "Wireless Mouse",
  "description": "Ergonomic wireless mouse with long battery life",
  "inventory": 100,
  "price": 29.99
}
```

#### `remove_product` - Delete Product
Remove a product from the inventory.

**Parameters:**
- `product_id` (int): ID of the product to remove

**Example Usage:**
```python
# Remove product with ID 2
removed = await remove_product(product_id=2)
```

### Order Management

#### `order_product` - Place Order
Create an order and reduce inventory automatically.

**Parameters:**
- `product_id` (int): ID of the product to order
- `quantity` (int): Number of items to order
- `customer_identifier` (str): Customer ID or identifier

**Example Usage:**
```python
# Place an order for 3 laptops
order = await order_product(
    product_id=1,
    quantity=3,
    customer_identifier="customer_123"
)
```

**Response:**
```json
{
  "id": 1,
  "product_id": 1,
  "quantity": 3,
  "customer_identifier": "customer_123"
}
```

**Note:** This operation automatically reduces the product's inventory by the ordered quantity.

## Usage Patterns

### Inventory Management Workflow

```mermaid
flowchart TD
    A[Check Current Inventory] --> B{Stock Available?}
    B -->|Yes| C[Place Order]
    B -->|No| D[Add New Stock]
    C --> E[Update Inventory]
    D --> F[Update Product]
    E --> G[Confirm Order]
    F --> A

    style A fill:#e3f2fd
    style C fill:#e8f5e9
    style D fill:#fff3e0
```

### Example: Complete Product Lifecycle

1. **Add Product**
   ```python
   # Create new product
   product = await add_product(
       name="Gaming Keyboard",
       description="RGB mechanical keyboard",
       inventory=50,
       price=149.99
   )
   ```

2. **Check Inventory**
   ```python
   # Verify product was created
   current = await get_product_by_id(product_id=product["id"])
   print(f"Current inventory: {current['inventory']}")
   ```

3. **Process Orders**
   ```python
   # Customer places order
   order = await order_product(
       product_id=product["id"],
       quantity=2,
       customer_identifier="customer_456"
   )
   ```

4. **Monitor Stock**
   ```python
   # Check remaining inventory
   updated = await get_product_by_id(product_id=product["id"])
   print(f"Remaining inventory: {updated['inventory']}")  # Should be 48
   ```

### Example: Search and Filter

```python
# Find all gaming products
gaming_products = await search_products(query="gaming")

# Find products with "keyboard" in name or description
keyboards = await search_products(query="keyboard")

# Get expensive products (requires custom query)
all_products = await get_products(limit=1000)
expensive = [p for p in all_products if p["price"] > 100]
```

## Error Handling

### Common Errors and Solutions

#### Product Not Found
```python
try:
    product = await get_product_by_id(product_id=999)
    if product is None:
        print("Product not found")
except Exception as e:
    print(f"Error: {e}")
```

#### Insufficient Inventory
```python
try:
    order = await order_product(
        product_id=1,
        quantity=1000,  # More than available
        customer_identifier="customer_123"
    )
except ValueError as e:
    if "Not enough inventory" in str(e):
        print("Insufficient stock for this order")
    else:
        print(f"Order failed: {e}")
```

#### Duplicate Product Names
```python
try:
    await add_product(name="Existing Product")
except Exception as e:
    if "unique constraint" in str(e).lower():
        print("Product with this name already exists")
```

## Integration Examples

### With AI Agent Conversations

**Agent:** "What laptops do we have in stock?"
```python
# Agent would call:
laptops = await search_products(query="laptop")
response = f"We have {len(laptops)} laptop models available:\n"
for laptop in laptops:
    response += f"- {laptop['name']}: {laptop['inventory']} units at ${laptop['price']}\n"
```

**Agent:** "Order 5 wireless mice for customer John"
```python
# Agent would:
1. mice = await search_products(query="wireless mouse")
2. if mice:
       order = await order_product(
           product_id=mice[0]["id"],
           quantity=5,
           customer_identifier="john"
       )
       return f"Order placed: {order['quantity']} mice for customer {order['customer_identifier']}"
```

### Batch Operations

```python
# Add multiple products
products_to_add = [
    {"name": "Monitor", "price": 299.99, "inventory": 25},
    {"name": "Webcam", "price": 89.99, "inventory": 40},
    {"name": "Headphones", "price": 199.99, "inventory": 30}
]

created_products = []
for product_data in products_to_add:
    product = await add_product(**product_data)
    created_products.append(product)

print(f"Created {len(created_products)} products")
```

## Best Practices

### Performance Tips
- Use pagination for large product lists
- Cache frequently accessed product data
- Batch operations when possible
- Monitor database connection pool usage

### Data Management
- Keep product names unique and descriptive
- Use meaningful customer identifiers
- Regularly monitor inventory levels
- Implement proper error handling

### Security Considerations
- Validate all input parameters
- Use proper database connection strings
- Monitor for unusual order patterns
- Implement rate limiting if needed

## Troubleshooting

### Server Won't Start
1. Check database connection string
2. Verify PostgreSQL is running
3. Ensure database exists
4. Check port availability (8002)

### Database Errors
1. Verify database permissions
2. Check connection pool settings
3. Monitor database logs
4. Ensure proper schema exists

### Tool Not Working
1. Verify server is running
2. Check MCP tool registration
3. Review server logs for errors
4. Test with simple operations first

## Configuration Reference

### Environment Variables
```bash
# Required
DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"

# Optional
LOG_LEVEL="INFO"                    # DEBUG, INFO, WARNING, ERROR
MAX_CONNECTIONS=10                  # Database connection pool size
SERVER_PORT=8002                    # MCP server port
```

### Database Schema
The server creates these tables automatically:
- `products`: id, name, description, inventory, price
- `orders`: id, product_id, quantity, customer_identifier

For advanced usage and development, see the [Development Guide](dev-guide.md).
