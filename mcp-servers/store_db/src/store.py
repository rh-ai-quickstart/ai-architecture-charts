import asyncio
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import crud, database
from . import models as PydanticModels
import os

mcp_server = FastMCP()


@mcp_server.custom_route("/healthz", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for container health checks"""
    try:
        # Test database connectivity
        async with database.AsyncSessionLocal() as session:
            # Simple query to test database connection
            await session.execute("SELECT 1")
        
        return JSONResponse({
            "status": "healthy",
            "database": "connected",
            "service": "mcp-dbstore"
        }, status_code=200)
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy", 
            "database": "disconnected",
            "service": "mcp-dbstore",
            "error": str(e)
        }, status_code=503)


@mcp_server.tool()
async def get_products(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves a list of all products from the inventory database.

    This tool provides access to the complete product catalog, including product details
    such as names, descriptions, current inventory levels, and pricing information.
    Useful for browsing available products, checking stock levels, or getting an overview
    of the entire inventory.

    Parameters:
    - skip (int, optional): Number of products to skip for pagination. Default: 0
    - limit (int, optional): Maximum number of products to return. Default: 100, Max recommended: 1000

    Returns:
    List of product dictionaries, each containing:
    - id (int): Unique product identifier
    - name (str): Product name
    - description (str|null): Detailed product description
    - inventory (int): Current stock quantity available
    - price (float): Product price in USD

    Example use cases:
    - "Show me all available products"
    - "What products do we have in stock?"
    - "List the first 50 products"
    """
    async with database.AsyncSessionLocal() as session:
        db_products = await crud.get_products(session, skip=skip, limit=limit)
        return [
            PydanticModels.Product.model_validate(p).model_dump() for p in db_products
        ]


@mcp_server.tool()
async def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetches detailed information for a specific product using its unique ID.

    This tool retrieves complete product information including current inventory
    and pricing. Most useful when you have a specific product ID and need
    detailed information about that particular item.

    Parameters:
    - product_id (int, required): The unique integer identifier of the product

    Returns:
    - Product dictionary with complete details if found
    - null if no product exists with the given ID

    Product dictionary contains:
    - id (int): The product's unique identifier
    - name (str): Product name/title
    - description (str|null): Detailed product description
    - inventory (int): Current stock quantity
    - price (float): Product price in USD

    Example use cases:
    - "Get details for product ID 123"
    - "What's the current stock for product 456?"
    - "Show me information about product 789"
    """
    async with database.AsyncSessionLocal() as session:
        db_product = await crud.get_product_by_id(session, product_id=product_id)
        if db_product:
            return PydanticModels.Product.model_validate(db_product).model_dump()
        return None


@mcp_server.tool()
async def get_product_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Finds a specific product by its exact name match.

    This tool performs an exact name lookup to find products. The search is
    case-sensitive and requires an exact match of the product name. Use this
    when you know the precise product name and need its details.

    Parameters:
    - name (str, required): The exact product name to search for (case-sensitive)

    Returns:
    - Product dictionary with complete details if found
    - null if no product exists with the exact name

    Product dictionary contains:
    - id (int): The product's unique identifier
    - name (str): Product name (will match the search term exactly)
    - description (str|null): Detailed product description
    - inventory (int): Current stock quantity
    - price (float): Product price in USD

    Example use cases:
    - "Find the product named 'Super Widget'"
    - "Get details for 'Mega Gadget'"
    - "Look up 'Quantum Sprocket' by name"

    Note: For partial name searches, use the search_products tool instead.
    """
    async with database.AsyncSessionLocal() as session:
        db_product = await crud.get_product_by_name(session, name=name)
        if db_product:
            return PydanticModels.Product.model_validate(db_product).model_dump()
        return None


@mcp_server.tool()
async def search_products(
    query: str, skip: int = 0, limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Performs a flexible text search across product names and descriptions.

    This tool enables fuzzy searching through the product catalog by matching
    the query string against both product names and descriptions. It's ideal
    for finding products when you don't know the exact name or want to find
    all products related to a particular topic or keyword.

    Parameters:
    - query (str, required): Search term to match against product names and descriptions
                            (case-insensitive, supports partial matches)
    - skip (int, optional): Number of results to skip for pagination. Default: 0
    - limit (int, optional): Maximum number of results to return. Default: 100

    Returns:
    List of matching product dictionaries, each containing:
    - id (int): Unique product identifier
    - name (str): Product name
    - description (str|null): Product description
    - inventory (int): Current stock quantity
    - price (float): Product price in USD

    Search behavior:
    - Searches both product names and descriptions
    - Case-insensitive matching
    - Supports partial word matches
    - Returns results ordered by relevance

    Example use cases:
    - "Find all products containing 'widget'"
    - "Search for products related to 'quantum'"
    - "Look for items with 'ultra' in the name or description"
    - "Find products about 'gadgets' or 'tools'"
    """
    async with database.AsyncSessionLocal() as session:
        db_products = await crud.search_products(
            session, query=query, skip=skip, limit=limit
        )
        return [
            PydanticModels.Product.model_validate(p).model_dump() for p in db_products
        ]


@mcp_server.tool()
async def add_product(
    name: str, description: Optional[str] = None, inventory: int = 0, price: float = 0.0
) -> Dict[str, Any]:
    """
    Creates a new product in the inventory system with the specified details.

    This tool adds a brand new product to the database with the provided information.
    All products must have a unique name. This is typically used for inventory
    management, adding new items to the catalog, or setting up initial stock.

    Parameters:
    - name (str, required): Unique product name/title (must not already exist)
    - description (str, optional): Detailed product description. Default: null
    - inventory (int, optional): Initial stock quantity. Default: 0
    - price (float, optional): Product price in USD. Default: 0.0

    Returns:
    Complete product dictionary for the newly created product:
    - id (int): Auto-generated unique product identifier
    - name (str): The product name as provided
    - description (str|null): Product description
    - inventory (int): Initial inventory quantity
    - price (float): Product price in USD

    Validation rules:
    - Product name must be unique (will fail if name already exists)
    - Price must be non-negative
    - Inventory must be non-negative integer

    Example use cases:
    - "Add a new product called 'Smart Speaker' with 50 units at $99.99"
    - "Create a product 'Wireless Headphones' with description and initial stock"
    - "Add 'Premium Cable' to inventory with price $29.99"

    Error conditions:
    - Will raise an error if a product with the same name already exists
    - Invalid price or inventory values will be rejected
    """
    product_create = PydanticModels.ProductCreate(
        name=name, description=description, inventory=inventory, price=price
    )
    async with database.AsyncSessionLocal() as session:
        db_product = await crud.add_product(session, product=product_create)
        await session.commit()
        return PydanticModels.Product.model_validate(db_product).model_dump()


@mcp_server.tool()
async def remove_product(product_id: int) -> Optional[Dict[str, Any]]:
    """
    Permanently removes a product from the inventory system.

    This tool completely deletes a product from the database using its unique ID.
    This action is irreversible and will also remove any associated order history.
    Use with caution as this permanently removes all product data.

    Parameters:
    - product_id (int, required): The unique identifier of the product to remove

    Returns:
    - Product dictionary of the removed product if deletion was successful
    - null if no product was found with the given ID

    Returned product dictionary contains the final state before deletion:
    - id (int): The product's unique identifier
    - name (str): Product name
    - description (str|null): Product description
    - inventory (int): Final inventory quantity
    - price (float): Product price in USD

    Important considerations:
    - This action is permanent and cannot be undone
    - Any existing orders for this product may be affected
    - Consider reducing inventory to 0 instead of deletion for historical tracking

    Example use cases:
    - "Remove product with ID 123 from the system"
    - "Delete the discontinued product 456"
    - "Permanently remove product 789 from inventory"

    Alternative approach:
    - Consider setting inventory to 0 instead of deletion to maintain order history
    """
    async with database.AsyncSessionLocal() as session:
        db_product = await crud.remove_product(session, product_id=product_id)
        if db_product:
            await session.commit()
            return PydanticModels.Product.model_validate(db_product).model_dump()
        return None


@mcp_server.tool()
async def order_product(
    product_id: int, quantity: int, customer_identifier: str
) -> Dict[str, Any]:
    """
    Places an order for a specified quantity of a product, updating inventory automatically.

    This tool processes a product order by checking inventory availability, deducting
    the requested quantity from stock, and creating an order record. It handles the
    complete order workflow including inventory validation and automatic stock updates.

    Parameters:
    - product_id (int, required): The unique identifier of the product to order
    - quantity (int, required): Number of units to order (must be positive)
    - customer_identifier (str, required): Customer name, ID, or identifier for the order

    Returns:
    Complete order dictionary with details:
    - id (int): Auto-generated unique order identifier
    - product_id (int): ID of the ordered product
    - quantity (int): Number of units ordered
    - customer_identifier (str): Customer information

    Business logic:
    - Automatically checks if sufficient inventory is available
    - Deducts ordered quantity from product inventory
    - Creates a permanent order record
    - All operations are performed atomically (either all succeed or all fail)

    Validation and error handling:
    - Product must exist in the database
    - Requested quantity must not exceed available inventory
    - Quantity must be a positive integer
    - Customer identifier cannot be empty

    Example use cases:
    - "Order 5 units of product ID 123 for customer 'John Smith'"
    - "Place an order for 10 'Super Widgets' for customer ID 'CUST001'"
    - "Customer 'Alice Johnson' wants to order 3 units of product 456"

    Error conditions:
    - ValueError: Product not found or insufficient inventory
    - ValueError: Invalid quantity (negative or zero)
    - ValueError: Empty customer identifier

    Inventory impact:
    - Product inventory is immediately reduced by the order quantity
    - Inventory changes are permanent and reflected in subsequent product queries
    """
    order_request = PydanticModels.ProductOrderRequest(
        product_id=product_id,
        quantity=quantity,
        customer_identifier=customer_identifier,
    )
    async with database.AsyncSessionLocal() as session:
        try:
            db_order = await crud.order_product(session, order_details=order_request)
            await session.commit()
            return PydanticModels.Order.model_validate(db_order).model_dump()
        except ValueError:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise


async def run_startup_tasks():
    print("INFO:     MCP_DBStore Server startup tasks beginning...")
    await database.create_db_and_tables()
    print("INFO:     MCP_DBStore database tables checked/created.")
    print("INFO:     MCP_DBStore Server core initialization complete.")


if __name__ == "__main__":
    # Run startup tasks in their own event loop first
    print("INFO:     Running MCP_DBStore startup tasks...")
    asyncio.run(run_startup_tasks())
    
    # Get host and port from environment variables
    host = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_SERVER_PORT", "8002"))
    transport = os.getenv("MCP_SERVER_TRANSPORT", "sse")
    
    print(f"INFO:     Starting MCP_DBStore FastMCP server on {host}:{port} with transport {transport}...")
    mcp_server.settings.host = host
    mcp_server.settings.port = port
    
    try:
        # Start the server (this should block and keep running)
        mcp_server.run(transport=transport)
    except Exception as e:
        print(f"ERROR:    Failed to start MCP server: {e}")
        raise
