import asyncio
import datetime
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP, settings
from starlette.requests import Request
from starlette.responses import JSONResponse

import crud
import database
import models as PydanticModels
from crud import DatabaseUnavailableError, DatabaseOperationError

# Initialize FastMCP
mcp_server = FastMCP()

# Set port for FastMCP
settings.port = 8002

@mcp_server.tool()
async def get_products(skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetches a list of all products from the database.
    
    Args:
        skip: Number of products to skip (for pagination)
        limit: Maximum number of products to return (for pagination)
    
    Returns:
        List of product dictionaries containing id, name, description,
        inventory, and price
    
    Raises:
        RuntimeError: If the database is unavailable or operation fails
    """
    try:
        session = await database.db_manager.get_session()
        if not session:
            raise RuntimeError(
                "Database is currently unavailable. Please check your database connection "
                "and ensure the PostgreSQL service is running."
            )
        
        db_products = await crud.get_products(session, skip=skip, limit=limit)
        result = [
            PydanticModels.Product.model_validate(p).model_dump() for p in db_products
        ]
        await session.close()
        return result
        
    except DatabaseUnavailableError as e:
        raise RuntimeError(str(e))
    except DatabaseOperationError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp_server.tool()
async def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its ID from the database.
    
    Args:
        product_id: The unique identifier of the product to retrieve
    
    Returns:
        Product dictionary with id, name, description, inventory, and price,
        or None if not found
    
    Raises:
        RuntimeError: If the database is unavailable or operation fails
    """
    try:
        session = await database.db_manager.get_session()
        if not session:
            raise RuntimeError(
                "Database is currently unavailable. Please check your database connection "
                "and ensure the PostgreSQL service is running."
            )
        
        db_product = await crud.get_product_by_id(session, product_id=product_id)
        result = None
        if db_product:
            result = PydanticModels.Product.model_validate(db_product).model_dump()
        
        await session.close()
        return result
        
    except DatabaseUnavailableError as e:
        raise RuntimeError(str(e))
    except DatabaseOperationError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp_server.tool()
async def get_product_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Fetches a single product by its name from the database.
    
    Args:
        name: The exact name of the product to retrieve
    
    Returns:
        Product dictionary with id, name, description, inventory, and price,
        or None if not found
    
    Raises:
        RuntimeError: If the database is unavailable or operation fails
    """
    try:
        session = await database.db_manager.get_session()
        if not session:
            raise RuntimeError(
                "Database is currently unavailable. Please check your database connection "
                "and ensure the PostgreSQL service is running."
            )
        
        db_product = await crud.get_product_by_name(session, name=name)
        result = None
        if db_product:
            result = PydanticModels.Product.model_validate(db_product).model_dump()
        
        await session.close()
        return result
        
    except DatabaseUnavailableError as e:
        raise RuntimeError(str(e))
    except DatabaseOperationError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp_server.tool()
async def search_products(
    query: str, skip: int = 0, limit: int = 100
) -> List[Dict[str, Any]]:
    """Searches for products based on a query string (name or description).
    
    Args:
        query: Search term to match against product names and descriptions
        skip: Number of products to skip (for pagination)
        limit: Maximum products to return (for pagination)
    
    Returns:
        List of matching product dictionaries, empty list if no matches found
    
    Raises:
        RuntimeError: If the database is unavailable or operation fails
    """
    try:
        session = await database.db_manager.get_session()
        if not session:
            raise RuntimeError(
                "Database is currently unavailable. Please check your database connection "
                "and ensure the PostgreSQL service is running."
            )
        
        db_products = await crud.search_products(session, query=query, skip=skip, limit=limit)
        result = [
            PydanticModels.Product.model_validate(p).model_dump() for p in db_products
        ]
        await session.close()
        return result
        
    except DatabaseUnavailableError as e:
        raise RuntimeError(str(e))
    except DatabaseOperationError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp_server.tool()
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
        RuntimeError: If the database is unavailable or operation fails
    """
    try:
        session = await database.db_manager.get_session()
        if not session:
            raise RuntimeError(
                "Database is currently unavailable. Please check your database connection "
                "and ensure the PostgreSQL service is running."
            )
        
        product_create = PydanticModels.ProductCreate(
            name=name, description=description, inventory=inventory, price=price
        )
        db_product = await crud.add_product(session, product=product_create)
        result = PydanticModels.Product.model_validate(db_product).model_dump()
        
        await session.commit()
        await session.close()
        return result
        
    except DatabaseUnavailableError as e:
        raise RuntimeError(str(e))
    except DatabaseOperationError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp_server.tool()
async def remove_product(product_id: int) -> Optional[Dict[str, Any]]:
    """Removes a product from the database by its ID.
    
    Args:
        product_id: The unique identifier of the product to remove
    
    Returns:
        Removed product dictionary if found and deleted, None if product not found
    
    Raises:
        RuntimeError: If the database is unavailable or operation fails
    """
    try:
        session = await database.db_manager.get_session()
        if not session:
            raise RuntimeError(
                "Database is currently unavailable. Please check your database connection "
                "and ensure the PostgreSQL service is running."
            )
        
        db_product = await crud.remove_product(session, product_id=product_id)
        result = None
        if db_product:
            result = PydanticModels.Product.model_validate(db_product).model_dump()
        
        await session.commit()
        await session.close()
        return result
        
    except DatabaseUnavailableError as e:
        raise RuntimeError(str(e))
    except DatabaseOperationError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp_server.tool()
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
        ValueError: If product not found, insufficient inventory, or other business logic error
        RuntimeError: If the database is unavailable or operation fails
    """
    try:
        session = await database.db_manager.get_session()
        if not session:
            raise RuntimeError(
                "Database is currently unavailable. Please check your database connection "
                "and ensure the PostgreSQL service is running."
            )
        
        order_request = PydanticModels.ProductOrderRequest(
            product_id=product_id,
            quantity=quantity,
            customer_identifier=customer_identifier,
        )
        
        try:
            db_order = await crud.order_product(session, order_details=order_request)
            result = PydanticModels.Order.model_validate(db_order).model_dump()
            
            await session.commit()
            await session.close()
            return result
            
        except ValueError:
            await session.rollback()
            await session.close()
            raise
        except Exception:
            await session.rollback()
            await session.close()
            raise
            
    except ValueError:
        # Re-raise business logic errors
        raise
    except DatabaseUnavailableError as e:
        raise RuntimeError(str(e))
    except DatabaseOperationError as e:
        raise RuntimeError(str(e))
    except Exception as e:
        raise RuntimeError(f"Unexpected error: {str(e)}")


@mcp_server.tool()
async def health_check() -> Dict[str, Any]:
    """Check the health status of the MCP server and database connectivity.
    
    This tool provides health information that can be used by monitoring systems
    and for debugging connectivity issues.
    
    Returns:
        Dictionary containing server status and database connectivity information
    """
    db_state = database.db_manager.get_state()
    db_available = database.db_manager.is_available()
    
    return {
        "status": "healthy",  # MCP server is always healthy if running
        "service": "mcp-store-db",
        "database_status": db_state.value,
        "database_available": db_available,
        "database_url": database.DATABASE_URL,
        "timestamp": str(datetime.datetime.now()),
        "message": "MCP server is running and ready to process requests",
    }


@mcp_server.tool()
async def check_database_connectivity() -> Dict[str, Any]:
    """Check the current database connectivity status.
    
    This tool allows LLM agents to check if the database is available
    before attempting operations that require database access.
    
    Returns:
        Dictionary containing detailed database connectivity information
    """
    db_state = database.db_manager.get_state()
    db_available = database.db_manager.is_available()
    
    status_messages = {
        database.DatabaseState.CONNECTED: "Database is connected and ready for operations",
        database.DatabaseState.DISCONNECTED: "Database is currently unavailable",
        database.DatabaseState.CONNECTING: "Database connection is being established",
        database.DatabaseState.MIGRATION_FAILED: "Database migration failed - manual intervention may be required",
        database.DatabaseState.SCHEMA_INCOMPATIBLE: "Database schema is incompatible with current application version",
        database.DatabaseState.UNKNOWN: "Database status is unknown"
    }
    
    return {
        "database_status": db_state.value,
        "database_available": db_available,
        "status_message": status_messages.get(db_state, "Unknown status"),
        "can_perform_operations": db_available,
        "recommendation": "Use this tool to check database status before calling other tools" if not db_available else "Database is ready for operations",
        "timestamp": str(datetime.datetime.now())
    }


# Add custom HTTP endpoints using FastMCP
@mcp_server.custom_route("/health", methods=["GET"])
async def health_endpoint(request: Request) -> JSONResponse:
    """HTTP health check endpoint for container orchestration and monitoring."""
    db_state = database.db_manager.get_state()
    db_available = database.db_manager.is_available()
    
    return JSONResponse(
        {
            "status": "healthy",  # MCP server is always healthy if running
            "service": "mcp-store-db",
            "database_status": db_state.value,
            "database_available": db_available,
            "database_url": database.DATABASE_URL,
            "message": "MCP server is running and ready to process requests",
        }
    )


@mcp_server.custom_route("/tools", methods=["GET"])
async def tools_endpoint(request: Request) -> JSONResponse:
    """HTTP endpoint to list all available MCP tools."""
    try:
        tools = await mcp_server.get_tools()
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
                "service": "mcp-store-db",
                "total_tools": len(tool_list),
                "tools": tool_list,
            }
        )
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to retrieve tools: {str(e)}"}, status_code=500
        )


async def run_startup_tasks():
    """Initialize the MCP server and database manager."""
    print("INFO:     MCP_Store_DB Server startup tasks beginning...")
    
    try:
        await database.db_manager.initialize()
        print("INFO:     MCP_Store_DB database manager initialized successfully.")
    except Exception as e:
        print(f"WARNING:  Database initialization failed: {e}")
        print("INFO:     MCP server will start but database operations will be unavailable.")
    
    print("INFO:     MCP_Store_DB Server core initialization complete.")


async def run_shutdown_tasks():
    """Cleanup tasks for graceful shutdown."""
    print("INFO:     MCP_Store_DB Server shutdown tasks beginning...")
    await database.db_manager.shutdown()
    print("INFO:     MCP_Store_DB Server shutdown complete.")


if __name__ == "__main__":
    try:
        asyncio.run(run_startup_tasks())
        print("INFO:     Starting MCP_Store_DB FastMCP server on port 8002...")
        mcp_server.run(transport="sse")
    except KeyboardInterrupt:
        print("\nINFO:     Shutdown signal received...")
        asyncio.run(run_shutdown_tasks())
    except Exception as e:
        print(f"ERROR:    Server startup failed: {e}")
        asyncio.run(run_shutdown_tasks())
        raise
