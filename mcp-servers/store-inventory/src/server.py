import asyncio
import datetime
import os
from typing import Any, Dict, List, Optional

# Set FastMCP settings before creating the instance
import fastmcp
import httpx
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

fastmcp.settings.port = 8003  # Different port to avoid conflicts

# Initialize FastMCP 2.x
mcp = FastMCP()

# Store API server URL - this will connect to the store-inventory API
STORE_API_URL = os.getenv("STORE_API_URL", "http://localhost:8002")

# Global flag to track store API availability
store_api_available = True


# Store API health check function
async def check_api_health() -> bool:
    """Check if the store API is available."""
    global store_api_available

    try:
        # Create a new client for each health check to avoid event loop issues
        async with httpx.AsyncClient(base_url=STORE_API_URL) as client:
            response = await client.get("/health", timeout=5.0)
            store_api_available = response.status_code == 200
            return store_api_available
    except Exception:
        store_api_available = False
        return False


# Helper function to make API requests to the Store API Server
async def make_api_request(
    method: str,
    endpoint: str,
    params: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Helper function to make API requests to the Store API Server."""
    global store_api_available

    # Check API availability first
    if not store_api_available:
        # Try to reconnect
        await check_api_health()
        if not store_api_available:
            raise RuntimeError(
                f"Store API is currently unavailable at {STORE_API_URL}. "
                "Please check if the store-inventory service is running."
            )

    try:
        # Create a new client for each request to avoid event loop issues
        async with httpx.AsyncClient(base_url=STORE_API_URL) as client:
            response = await client.request(
                method, endpoint, params=params, json=json_data, timeout=30.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        raise RuntimeError(
            f"Request to Store API timed out after 30 seconds. "
            f"Endpoint: {method} {endpoint}"
        )
    except httpx.HTTPStatusError as e:
        # Attempt to get more details from the response body if available
        try:
            if e.response.content and e.response.text:
                # Try to parse JSON response
                try:
                    error_json = e.response.json()
                    error_detail = error_json.get(
                        "detail", error_json.get("message", str(error_json))
                    )
                except (ValueError, TypeError):
                    # If JSON parsing fails, use raw text
                    error_detail = e.response.text
            else:
                error_detail = f"HTTP {e.response.status_code}"
        except Exception:
            error_detail = f"HTTP {e.response.status_code}"

        raise ValueError(
            f"API Error: {e.response.status_code} - {error_detail} when calling "
            f"{e.request.method} {e.request.url}"
        ) from e
    except httpx.RequestError as e:
        # Mark API as unavailable
        store_api_available = False
        raise RuntimeError(
            f"Request Error: Could not connect to Store API Server at "
            f"{e.request.url}. Details: {str(e)}. "
            "Please check if the store-inventory service is running."
        ) from e
    except Exception as e:
        # Mark API as unavailable for unexpected errors
        store_api_available = False
        raise RuntimeError(f"Unexpected error connecting to Store API: {str(e)}") from e


@mcp.tool()
async def get_products(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetches a list of all products from the database.

    Args:
        skip: Number of products to skip (for pagination)
        limit: Maximum number of products to return (for pagination)

    Returns:
        List of product dictionaries containing id, name, description,
        inventory, and price

    Raises:
        RuntimeError: If the store API is unavailable
    """
    return await make_api_request(
        "GET", "/products/", params={"skip": skip, "limit": limit}
    )


@mcp.tool()
async def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its ID from the database.

    Args:
        product_id: The unique identifier of the product to retrieve

    Returns:
        Product dictionary with id, name, description, inventory, and price,
        or None if not found

    Raises:
        RuntimeError: If the store API is unavailable
    """
    try:
        return await make_api_request("GET", f"/products/id/{product_id}")
    except ValueError as e:
        if "404" in str(e):  # crude check for 404
            return None  # Product not found
        raise


@mcp.tool()
async def get_product_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its name from the database.

    Args:
        name: The exact name of the product to retrieve

    Returns:
        Product dictionary with id, name, description, inventory, and price,
        or None if not found

    Raises:
        RuntimeError: If the store API is unavailable
    """
    try:
        return await make_api_request("GET", f"/products/name/{name}")
    except ValueError as e:
        if "404" in str(e):
            return None  # Product not found
        raise


@mcp.tool()
async def search_products(
    query: str, skip: int = 0, limit: int = 100
) -> List[Dict[str, Any]]:
    """Searches for products based on a query string (name or description).

    Args:
        query: Search term to match against product names and descriptions
        skip: Number of products to skip (for pagination)
        limit: Maximum number of products to return (for pagination)

    Returns:
        List of matching product dictionaries, empty list if no matches found

    Raises:
        RuntimeError: If the store API is unavailable
    """
    try:
        return await make_api_request(
            "GET",
            "/products/search/",
            params={"query": query, "skip": skip, "limit": limit},
        )
    except ValueError as e:
        if "404" in str(e):  # crude check for 404 when no products found
            return []
        raise


@mcp.tool()
async def add_product(
    name: str, description: Optional[str] = None, inventory: int = 0, price: float = 0.0
) -> Dict[str, Any]:
    """Adds a new product to the database.

    Args:
        name: The name of the product (required)
        description: Optional description of the product
        inventory: Initial inventory count (defaults to 0)
        price: Price of the product (defaults to 0.0)

    Returns:
        Created product dictionary with id, name, description, inventory, and price

    Raises:
        RuntimeError: If the store API is unavailable
    """
    payload = {
        "name": name,
        "description": description,
        "inventory": inventory,
        "price": price,
    }
    return await make_api_request("POST", "/products/", json_data=payload)


@mcp.tool()
async def remove_product(product_id: int) -> Optional[Dict[str, Any]]:
    """Removes a product from the database by its ID.

    Args:
        product_id: The unique identifier of the product to remove

    Returns:
        Removed product dictionary if found and deleted, None if product not found

    Raises:
        RuntimeError: If the store API is unavailable
    """
    try:
        return await make_api_request("DELETE", f"/products/{product_id}")
    except ValueError as e:
        if "404" in str(e):
            return None  # Product not found
        raise


@mcp.tool()
async def order_product(
    product_id: int, quantity: int, customer_identifier: str
) -> Dict[str, Any]:
    """Places an order for a product.
    This involves checking inventory, deducting the quantity from the product's
    inventory, and creating an order record in the database.

    Args:
        product_id: The unique identifier of the product to order
        quantity: The number of items to order
        customer_identifier: Identifier for the customer placing the order

    Returns:
        Created order dictionary with id, product_id, quantity, and customer_identifier

    Raises:
        ValueError: If product not found, insufficient inventory, or other API error
        RuntimeError: If the store API is unavailable
    """
    payload = {
        "product_id": product_id,
        "quantity": quantity,
        "customer_identifier": customer_identifier,
    }
    return await make_api_request("POST", "/orders/", json_data=payload)


@mcp.tool()
async def health_check() -> Dict[str, Any]:
    """Check the health status of the MCP server and store API connectivity.

    This tool provides health information that can be used by monitoring systems
    and for debugging connectivity issues.

    Returns:
        Dictionary containing server status and API connectivity information
    """
    # Check API connectivity
    api_status = "unknown"
    try:
        if await check_api_health():
            api_status = "connected"
        else:
            api_status = "disconnected"
    except Exception:
        api_status = "error"

    return {
        "status": "healthy",
        "service": "mcp-store-inventory",
        "store_api_status": api_status,
        "store_api_url": STORE_API_URL,
        "timestamp": str(datetime.datetime.now()),
        "message": "MCP server is running and ready to process requests",
    }


# Add custom HTTP endpoints using FastMCP 2.x
@mcp.custom_route("/health", methods=["GET"])
async def health_endpoint(request: Request) -> JSONResponse:
    """HTTP health check endpoint for container orchestration and monitoring."""
    # Check API connectivity
    api_status = "unknown"
    try:
        if await check_api_health():
            api_status = "connected"
        else:
            api_status = "disconnected"
    except Exception:
        api_status = "error"

    return JSONResponse(
        {
            "status": "healthy",
            "service": "mcp-store-inventory",
            "store_api_status": api_status,
            "store_api_url": STORE_API_URL,
            "message": "MCP server is running and ready to process requests",
        }
    )


@mcp.custom_route("/tools", methods=["GET"])
async def tools_endpoint(request: Request) -> JSONResponse:
    """HTTP endpoint to list all available MCP tools."""
    try:
        tools = await mcp.get_tools()
        tool_list = []
        for name, tool in tools.items():
            tool_info = {
                "name": name,
                "description": tool.description or "No description available",
                "input_schema": (
                    tool.input_schema if hasattr(tool, "input_schema") else None
                ),
                "output_schema": (
                    tool.output_schema if hasattr(tool, "output_schema") else None
                ),
                "tags": list(tool.tags) if hasattr(tool, "tags") and tool.tags else [],
                "enabled": tool.enabled if hasattr(tool, "enabled") else True,
            }
            tool_list.append(tool_info)

        return JSONResponse(
            {
                "service": "mcp-store-inventory",
                "total_tools": len(tool_list),
                "tools": tool_list,
            }
        )
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to retrieve tools: {str(e)}"}, status_code=500
        )


# Note: FastMCP 2.x supports custom HTTP endpoints via custom_route
# The async_client is initialized at module level and will be cleaned up
# when the process terminates

if __name__ == "__main__":
    print("INFO:     Starting MCP Store Inventory server...")
    print(f"INFO:     Connecting to Store API at: {STORE_API_URL}")

    # Initial API health check
    try:
        asyncio.run(check_api_health())
        if store_api_available:
            print("INFO:     Store API is available")
        else:
            print("WARNING:  Store API is not available - tools will fail gracefully")
    except Exception as e:
        print(f"WARNING:  Could not check Store API health: {e}")
        store_api_available = False

    print("INFO:     MCP server starting on port 8003...")
    mcp.run(transport="sse")
