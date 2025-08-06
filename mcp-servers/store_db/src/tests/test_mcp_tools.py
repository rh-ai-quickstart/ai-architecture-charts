import pytest
import pytest_asyncio
from fastmcp import Client

from .. import database  # For direct DB manipulation/verification in tests

# Adjust these imports based on your project structure
from ..store import mcp_server  # Your FastMCP instance from store.py


@pytest_asyncio.fixture(
    scope="module"
)  # Module scope: server & DB setup once per test file
async def initialized_test_mcp_server():
    """Fixture to provide an initialized FastMCP server instance with a clean
    database."""
    # Setup: Create database tables
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.drop_all)  # Clean slate
        await conn.run_sync(database.Base.metadata.create_all)  # Create tables

    # The mcp_server instance is imported from your store.py
    # It should already have tools registered via decorators.
    yield mcp_server

    # Teardown: Drop database tables after all tests in the module are done
    async with database.engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_tool_get_products_empty(initialized_test_mcp_server):
    """Test the get_products tool when no products exist."""
    async with Client(initialized_test_mcp_server) as client:
        response = await client.call_tool("get_products")
        assert response.ok
        assert response.content == []


@pytest.mark.asyncio
async def test_tool_add_product_and_get_products(initialized_test_mcp_server):
    """Test adding a product via tool and then retrieving it."""
    async with Client(initialized_test_mcp_server) as client:
        # Add a product using the tool
        add_payload = {
            "name": "Tool Test Widget",
            "description": "A widget added via tool",
            "inventory": 20,
            "price": 9.99,
        }
        add_response = await client.call_tool("add_product", add_payload)
        assert add_response.ok
        added_product_data = add_response.content
        assert added_product_data["name"] == add_payload["name"]
        assert added_product_data["inventory"] == add_payload["inventory"]
        assert added_product_data["price"] == add_payload["price"]

        # Get all products and verify the new one is there
        get_response = await client.call_tool("get_products")
        assert get_response.ok
        products = get_response.content
        assert isinstance(products, list)
        assert len(products) >= 1
        assert any(
            p["name"] == "Tool Test Widget" and p["id"] == added_product_data["id"]
            for p in products
        )

        # Test get_product_by_id tool
        get_by_id_response = await client.call_tool(
            "get_product_by_id", {"product_id": added_product_data["id"]}
        )
        assert get_by_id_response.ok
        assert get_by_id_response.content["name"] == "Tool Test Widget"

        # Test get_product_by_name tool
        get_by_name_response = await client.call_tool(
            "get_product_by_name", {"name": "Tool Test Widget"}
        )
        assert get_by_name_response.ok
        assert get_by_name_response.content["id"] == added_product_data["id"]


@pytest.mark.asyncio
async def test_tool_order_product_insufficient_inventory(initialized_test_mcp_server):
    """Test order_product tool fails correctly with insufficient inventory."""
    async with Client(initialized_test_mcp_server) as client:
        # 1. Add a product with limited inventory using the add_product tool
        product_name = "Eval Limited Item"
        add_payload = {
            "name": product_name,
            "description": "Limited for eval",
            "inventory": 1,
            "price": 50.0,
        }
        add_response = await client.call_tool("add_product", add_payload)
        assert add_response.ok
        product_id_to_order = add_response.content["id"]

        # 2. Attempt to order more than available
        order_payload = {
            "product_id": product_id_to_order,
            "quantity": 2,
            "customer_identifier": "eval_user_001",
        }
        order_response = await client.call_tool("order_product", order_payload)

        # FastMCP typically returns ok=False if the tool function raises an
        # unhandled exception. The exception message might be in response.error
        # or response.content (if FastMCP formats it).
        assert not order_response.ok
        # You might need to inspect order_response.error or response.content
        # for the specific error message. Example:
        # assert "Insufficient inventory" in str(order_response.error)
        # This depends on how FastMCP surfaces exceptions from tools.
        # For now, we just check that the operation was not successful.

        # 3. Verify inventory has not changed using get_product_by_id tool
        verify_response = await client.call_tool(
            "get_product_by_id", {"product_id": product_id_to_order}
        )
        assert verify_response.ok
        assert verify_response.content["inventory"] == 1  # Inventory should remain 1


@pytest.mark.asyncio
async def test_tool_search_products(initialized_test_mcp_server):
    """Test the search_products tool."""
    async with Client(initialized_test_mcp_server) as client:
        # Ensure a clean state or add specific products for this test
        # For simplicity, we rely on products potentially added in other tests or
        # ensure this test is robust to it.
        # Better: explicitly add products needed ONLY for this search test here.
        await client.call_tool(
            "add_product", {"name": "Search Alpha One", "inventory": 5, "price": 1.0}
        )
        await client.call_tool(
            "add_product", {"name": "Search Beta Two", "inventory": 5, "price": 2.0}
        )
        await client.call_tool(
            "add_product", {"name": "Another Alpha Item", "inventory": 5, "price": 3.0}
        )

        search_alpha_response = await client.call_tool(
            "search_products", {"query": "Alpha"}
        )
        assert search_alpha_response.ok
        alpha_results = search_alpha_response.content
        assert len(alpha_results) >= 2  # Could be more if other tests left Alpha items
        assert any(p["name"] == "Search Alpha One" for p in alpha_results)
        assert any(p["name"] == "Another Alpha Item" for p in alpha_results)

        search_beta_response = await client.call_tool(
            "search_products", {"query": "Beta"}
        )
        assert search_beta_response.ok
        assert any(p["name"] == "Search Beta Two" for p in search_beta_response.content)
