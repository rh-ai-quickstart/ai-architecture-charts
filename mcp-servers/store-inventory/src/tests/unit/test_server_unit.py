"""
Unit tests for the MCP Store Inventory server.

These tests use dependency injection and FastMCP Client to test tool functionality
with mocked store API, following FastMCP testing best practices.
"""

import json
import os
import sys

import pytest
import pytest_asyncio
from fastmcp import Client, FastMCP

# Add parent directory to Python path to import server module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestServerUnit:
    """Unit tests for server functionality with mocked dependencies."""

    @pytest.fixture
    def mock_store_api(self):
        """Mock store API responses."""
        return {
            "products": [
                {
                    "id": 1,
                    "name": "Test Product 1",
                    "description": "Test desc 1",
                    "inventory": 100,
                    "price": 25.99,
                },
                {
                    "id": 2,
                    "name": "Test Product 2",
                    "description": "Test desc 2",
                    "inventory": 50,
                    "price": 19.99,
                },
            ],
            "orders": [
                {
                    "id": 1,
                    "product_id": 1,
                    "quantity": 5,
                    "customer_identifier": "test-customer",
                }
            ],
        }

    @pytest.fixture
    def test_mcp_server(self, mock_store_api):
        """Create a test MCP server with mocked store API."""
        # Create a new FastMCP instance for testing
        server = FastMCP("TestServer")

        # Mock the store API functions
        async def mock_make_api_request(method, endpoint, params=None, json_data=None):
            """Mock API request function."""
            if (
                method == "GET"
                and "/products/" in endpoint
                and not any(x in endpoint for x in ["/id/", "/name/"])
            ):
                # General products endpoint
                if params and params.get("skip", 0) > 0:
                    return mock_store_api["products"][1:]  # Skip first product
                return mock_store_api["products"]
            elif method == "GET" and "/products/id/" in endpoint:
                # Get product by ID
                product_id = int(endpoint.split("/")[-1])
                product = next(
                    (p for p in mock_store_api["products"] if p["id"] == product_id),
                    None,
                )
                if product:
                    return [product]  # Return as list for consistency
                return None
            elif method == "GET" and "/products/name/" in endpoint:
                # Get product by name
                product_name = endpoint.split("/")[-1]
                product = next(
                    (
                        p
                        for p in mock_store_api["products"]
                        if p["name"] == product_name
                    ),
                    None,
                )
                if product:
                    return [product]  # Return as list for consistency
                return None
            elif method == "POST" and "/products/" in endpoint:
                # Simulate creating a new product
                new_product = {"id": len(mock_store_api["products"]) + 1, **json_data}
                mock_store_api["products"].append(new_product)
                return [new_product]  # Return as list for consistency
            elif method == "DELETE" and "/products/" in endpoint:
                product_id = int(endpoint.split("/")[-1])
                product = next(
                    (p for p in mock_store_api["products"] if p["id"] == product_id),
                    None,
                )
                if product:
                    mock_store_api["products"] = [
                        p for p in mock_store_api["products"] if p["id"] != product_id
                    ]
                    return [
                        {"deleted": True, **product}
                    ]  # Return as list for consistency
                return None
            elif method == "POST" and "/orders/" in endpoint:
                # Simulate creating a new order
                new_order = {"id": len(mock_store_api["orders"]) + 1, **json_data}
                mock_store_api["orders"].append(new_order)
                return [new_order]  # Return as list for consistency
            else:
                return {"result": "success"}

        async def mock_check_api_health():
            """Mock API health check."""
            return True

        # Create tool functions that use the mocked API
        @server.tool()
        async def get_products(skip: int = 0, limit: int = 100):
            """Mock get_products tool."""
            return await mock_make_api_request(
                "GET", "/products/", params={"skip": skip, "limit": limit}
            )

        @server.tool()
        async def get_product_by_id(product_id: int):
            """Mock get_product_by_id tool."""
            return await mock_make_api_request("GET", f"/products/id/{product_id}")

        @server.tool()
        async def get_product_by_name(name: str):
            """Mock get_product_by_name tool."""
            return await mock_make_api_request("GET", f"/products/name/{name}")

        @server.tool()
        async def search_products(query: str, skip: int = 0, limit: int = 10):
            """Mock search_products tool."""
            products = await mock_make_api_request("GET", "/products/")
            # Simple search simulation
            filtered = [
                p
                for p in products
                if query.lower() in p["name"].lower()
                or query.lower() in p["description"].lower()
            ]
            return filtered[skip : skip + limit]

        @server.tool()
        async def add_product(
            name: str, description: str, inventory: int, price: float
        ):
            """Mock add_product tool."""
            return await mock_make_api_request(
                "POST",
                "/products/",
                json_data={
                    "name": name,
                    "description": description,
                    "inventory": inventory,
                    "price": price,
                },
            )

        @server.tool()
        async def remove_product(product_id: int):
            """Mock remove_product tool."""
            return await mock_make_api_request("DELETE", f"/products/{product_id}")

        @server.tool()
        async def order_product(
            product_id: int, quantity: int, customer_identifier: str
        ):
            """Mock order_product tool."""
            return await mock_make_api_request(
                "POST",
                "/orders/",
                json_data={
                    "product_id": product_id,
                    "quantity": quantity,
                    "customer_identifier": customer_identifier,
                },
            )

        @server.tool()
        async def health_check():
            """Mock health_check tool."""
            return {
                "status": "healthy",
                "service": "mcp-store-inventory",
                "store_api_status": "connected",
                "store_api_url": "http://localhost:8002",
                "timestamp": "2024-01-01T00:00:00",
                "message": "MCP server is running and ready to process requests",
            }

        return server, mock_store_api

    @pytest_asyncio.fixture
    async def mcp_client(self, test_mcp_server):
        """FastMCP Client for testing tools."""
        server, _ = test_mcp_server
        async with Client(server) as client:
            yield client

    @pytest.mark.asyncio
    async def test_get_products_tool(self, mcp_client, mock_store_api):
        """Test get_products tool functionality."""
        # Test basic product retrieval
        result = await mcp_client.call_tool("get_products", {"skip": 0, "limit": 10})
        assert result.content is not None
        assert (
            len(result.content) == 1
        )  # FastMCP returns content as a list of TextContent objects

        # Verify product data - FastMCP returns JSON as text
        products_text = result.content[0].text
        products = json.loads(products_text)
        assert len(products) == 2
        assert products[0]["name"] == "Test Product 1"
        assert products[1]["name"] == "Test Product 2"

        # Test pagination
        result = await mcp_client.call_tool("get_products", {"skip": 1, "limit": 1})
        assert len(result.content) == 1
        products_text = result.content[0].text
        products = json.loads(products_text)
        assert len(products) == 1
        assert products[0]["name"] == "Test Product 2"

    @pytest.mark.asyncio
    async def test_get_product_by_id_tool(self, mcp_client, mock_store_api):
        """Test get_product_by_id tool functionality."""
        # Test existing product
        result = await mcp_client.call_tool("get_product_by_id", {"product_id": 1})
        assert result.content is not None
        assert len(result.content) == 1

        import json

        product_text = result.content[0].text
        products = json.loads(product_text)
        assert len(products) == 1
        product = products[0]
        assert product["name"] == "Test Product 1"
        assert product["price"] == 25.99

        # Test non-existent product
        result = await mcp_client.call_tool("get_product_by_id", {"product_id": 999})
        assert result.content == []  # FastMCP returns empty list for not found

    @pytest.mark.asyncio
    async def test_get_product_by_name_tool(self, mcp_client, mock_store_api):
        """Test get_product_by_name tool functionality."""
        # Test existing product
        result = await mcp_client.call_tool(
            "get_product_by_name", {"name": "Test Product 2"}
        )
        assert result.content is not None
        assert len(result.content) == 1

        import json

        product_text = result.content[0].text
        products = json.loads(product_text)
        assert len(products) == 1
        product = products[0]
        assert product["id"] == 2
        assert product["inventory"] == 50

        # Test non-existent product
        result = await mcp_client.call_tool(
            "get_product_by_name", {"name": "Non-existent Product"}
        )
        assert result.content == []  # FastMCP returns empty list for not found

    @pytest.mark.asyncio
    async def test_search_products_tool(self, mcp_client, mock_store_api):
        """Test search_products tool functionality."""
        # Test search by name
        result = await mcp_client.call_tool(
            "search_products", {"query": "Product 1", "skip": 0, "limit": 10}
        )
        assert result.content is not None
        assert len(result.content) == 1

        import json

        products_text = result.content[0].text
        products = json.loads(products_text)
        assert len(products) == 1
        assert products[0]["name"] == "Test Product 1"

        # Test search by description
        result = await mcp_client.call_tool(
            "search_products", {"query": "desc 2", "skip": 0, "limit": 10}
        )
        assert len(result.content) == 1
        products_text = result.content[0].text
        products = json.loads(products_text)
        assert len(products) == 1
        assert products[0]["name"] == "Test Product 2"

        # Test pagination
        result = await mcp_client.call_tool(
            "search_products", {"query": "Test", "skip": 1, "limit": 1}
        )
        assert len(result.content) == 1

    @pytest.mark.asyncio
    async def test_add_product_tool(self, mcp_client, mock_store_api):
        """Test add_product tool functionality."""
        # Test adding a new product
        new_product_data = {
            "name": "New Test Product",
            "description": "A newly added test product",
            "inventory": 75,
            "price": 15.50,
        }

        result = await mcp_client.call_tool("add_product", new_product_data)
        assert result.content is not None
        assert len(result.content) == 1

        import json

        product_text = result.content[0].text
        products = json.loads(product_text)
        assert len(products) == 1
        product = products[0]
        assert product["name"] == new_product_data["name"]
        assert product["price"] == new_product_data["price"]
        assert "id" in product

        # Verify product was added to mock store
        verify_result = await mcp_client.call_tool(
            "get_product_by_name", {"name": "New Test Product"}
        )
        assert verify_result.content is not None
        assert len(verify_result.content) == 1
        verify_product_text = verify_result.content[0].text
        verify_products = json.loads(verify_product_text)
        assert len(verify_products) == 1
        verify_product = verify_products[0]
        assert verify_product["inventory"] == 75

    @pytest.mark.asyncio
    async def test_remove_product_tool(self, mcp_client, mock_store_api):
        """Test remove_product tool functionality."""
        # Test removing existing product
        result = await mcp_client.call_tool("remove_product", {"product_id": 1})
        assert result.content is not None
        assert len(result.content) == 1

        import json

        product_text = result.content[0].text
        products = json.loads(product_text)
        assert len(products) == 1
        product = products[0]
        assert product["deleted"] is True
        assert product["name"] == "Test Product 1"

        # Verify product was removed
        verify_result = await mcp_client.call_tool(
            "get_product_by_id", {"product_id": 1}
        )
        assert verify_result.content == []  # FastMCP returns empty list for not found

        # Test removing non-existent product
        result = await mcp_client.call_tool("remove_product", {"product_id": 999})
        assert result.content == []  # FastMCP returns empty list for not found

    @pytest.mark.asyncio
    async def test_order_product_tool(self, mcp_client, mock_store_api):
        """Test order_product tool functionality."""
        # Test creating an order
        order_data = {
            "product_id": 2,
            "quantity": 3,
            "customer_identifier": "test-customer-123",
        }

        result = await mcp_client.call_tool("order_product", order_data)
        assert result.content is not None
        assert len(result.content) == 1

        import json

        order_text = result.content[0].text
        orders = json.loads(order_text)
        assert len(orders) == 1
        order = orders[0]
        assert order["product_id"] == order_data["product_id"]
        assert order["quantity"] == order_data["quantity"]
        assert order["customer_identifier"] == order_data["customer_identifier"]
        assert "id" in order

    @pytest.mark.asyncio
    async def test_health_check_tool(self, mcp_client, mock_store_api):
        """Test health_check tool functionality."""
        result = await mcp_client.call_tool("health_check", {})
        assert result.content is not None
        assert len(result.content) == 1

        import json

        health_text = result.content[0].text
        health_data = json.loads(health_text)
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "mcp-store-inventory"
        assert health_data["store_api_status"] == "connected"
        assert "timestamp" in health_data
        assert "message" in health_data

    @pytest.mark.asyncio
    async def test_tool_discovery(self, mcp_client, mock_store_api):
        """Test that all expected tools are available."""
        tools = await mcp_client.list_tools()

        expected_tools = [
            "get_products",
            "get_product_by_id",
            "get_product_by_name",
            "search_products",
            "add_product",
            "remove_product",
            "order_product",
            "health_check",
        ]

        tool_names = [tool.name for tool in tools]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

        # Verify tool descriptions
        for tool in tools:
            assert hasattr(tool, "description")
            assert tool.description.strip() != ""

    @pytest.mark.asyncio
    async def test_tool_error_handling(self, mcp_client, test_mcp_server):
        """Test tool error handling."""
        server, _ = test_mcp_server

        # Create a tool that raises an exception
        @server.tool()
        async def error_tool():
            """Tool that raises an exception."""
            raise ValueError("Test error")

        # Test the error tool - FastMCP should handle the error gracefully
        with pytest.raises(
            Exception
        ):  # FastMCP will raise an exception for tool errors
            await mcp_client.call_tool("error_tool", {})


if __name__ == "__main__":
    pytest.main([__file__])
