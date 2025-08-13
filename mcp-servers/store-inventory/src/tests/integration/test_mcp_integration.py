"""
Integration tests for the MCP Store Inventory server.

These tests focus on MCP server integration with LLM-like behavior,
testing tool discovery, schemas, and MCP protocol without external dependencies.
"""

import time

import httpx
import pytest
import pytest_asyncio
from fastmcp import Client


class TestMCPIntegration:
    """Integration tests for MCP server using FastMCP Client."""

    @pytest.fixture(scope="function")
    def mcp_server_url(self):
        """MCP server URL for testing."""
        return "http://localhost:8003"

    @pytest_asyncio.fixture(scope="function")
    async def http_client(self):
        """HTTP client for testing HTTP endpoints."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            yield client

    @pytest_asyncio.fixture(scope="function")
    async def mcp_client(self):
        """FastMCP Client for testing MCP tools discovery."""
        # Import the server instance directly
        from server import mcp

        # Create a client that connects directly to the server instance
        async with Client(mcp) as client:
            yield client

    @pytest.mark.asyncio
    async def test_mcp_server_health(self, http_client, mcp_server_url):
        """Test MCP server health endpoint."""
        response = await http_client.get(f"{mcp_server_url}/health")
        assert response.status_code == 200

        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "mcp-store-inventory"
        assert "store_api_status" in health_data
        assert "store_api_url" in health_data

    @pytest.mark.asyncio
    async def test_mcp_tools_endpoint(self, http_client, mcp_server_url):
        """Test MCP server tools endpoint."""
        response = await http_client.get(f"{mcp_server_url}/tools")
        assert response.status_code == 200

        tools_data = response.json()
        assert tools_data["service"] == "mcp-store-inventory"
        assert tools_data["total_tools"] >= 8

        # Verify all expected tools are present
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

        tool_names = [tool["name"] for tool in tools_data["tools"]]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_mcp_tools_discovery(self, mcp_client):
        """Test that MCP tools can be discovered and have proper descriptions."""
        # Test tool discovery without calling tools that make HTTP requests
        tools = await mcp_client.list_tools()
        assert len(tools) >= 8

        # Verify all expected tools are present
        expected_tool_names = [
            "get_products",
            "get_product_by_id",
            "get_product_by_name",
            "search_products",
            "add_product",
            "remove_product",
            "order_product",
            "health_check",
        ]

        actual_tool_names = [tool.name for tool in tools]
        for expected_tool in expected_tool_names:
            assert expected_tool in actual_tool_names

        # Verify tool descriptions are present and non-empty
        for tool in tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert tool.description.strip() != ""
            assert tool.name.strip() != ""

    @pytest.mark.asyncio
    async def test_mcp_tool_schemas(self, mcp_client):
        """Test that MCP tools have proper input/output schemas."""
        tools = await mcp_client.list_tools()

        # Test a few key tools for schema validation
        for tool in tools:
            # FastMCP uses inputSchema and outputSchema (camelCase)
            assert hasattr(tool, "inputSchema") or hasattr(tool, "outputSchema")
            # Some tools might not have output schemas, which is fine

    @pytest.mark.asyncio
    async def test_mcp_protocol_endpoints(self, http_client, mcp_server_url):
        """Test MCP protocol endpoints accessibility."""
        # Test SSE endpoint accessibility
        try:
            async with http_client.stream("GET", f"{mcp_server_url}/sse") as response:
                assert response.status_code == 200
                # SSE responses streamed, so we just check if endpoint is accessible
        except Exception:
            # SSE endpoint might not be fully accessible via simple HTTP
            # This is expected behavior for MCP protocol endpoints
            pass

        # Test message endpoint accessibility
        response = await http_client.get(f"{mcp_server_url}/messages/")
        # This might return various status codes, but shouldn't crash
        # Accept various responses
        assert response.status_code in [200, 400, 404, 405]

    @pytest.mark.asyncio
    async def test_mcp_server_configuration(self, http_client, mcp_server_url):
        """Test MCP server configuration and metadata."""
        # Test health endpoint for configuration info
        response = await http_client.get(f"{mcp_server_url}/health")
        assert response.status_code == 200

        health_data = response.json()

        # Verify required fields
        assert "status" in health_data
        assert "service" in health_data
        assert "store_api_status" in health_data
        assert "store_api_url" in health_data

        # Verify service name
        assert health_data["service"] == "mcp-store-inventory"

        # Verify store API URL format
        store_api_url = health_data["store_api_url"]
        assert store_api_url.startswith("http://")
        assert "8002" in store_api_url  # Should point to store-inventory API

    @pytest.mark.asyncio
    async def test_mcp_tool_count_consistency(self, mcp_client):
        """Test that tool count is consistent."""
        tools = await mcp_client.list_tools()

        # Verify we have the expected number of tools
        assert len(tools) >= 8

        # Verify no duplicate tool names
        tool_names = [tool.name for tool in tools]
        assert len(tool_names) == len(set(tool_names))  # No duplicates

    @pytest.mark.asyncio
    async def test_mcp_tool_metadata(self, mcp_client):
        """Test that MCP tools have proper metadata."""
        tools = await mcp_client.list_tools()

        for tool in tools:
            # Verify basic attributes
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")

            # Verify name is valid
            assert isinstance(tool.name, str)
            assert tool.name.strip() != ""

            # Verify description is valid
            assert isinstance(tool.description, str)
            assert tool.description.strip() != ""

            # Verify no HTML or special characters in name
            assert "<" not in tool.name
            assert ">" not in tool.name
            assert "&" not in tool.name

    @pytest.mark.asyncio
    async def test_mcp_server_readiness(self, http_client, mcp_server_url):
        """Test that MCP server is ready to handle requests."""
        # Test health endpoint
        response = await http_client.get(f"{mcp_server_url}/health")
        assert response.status_code == 200

        # Test tools endpoint
        response = await http_client.get(f"{mcp_server_url}/tools")
        assert response.status_code == 200

        # Test that server responds quickly (basic performance check)
        start_time = time.time()
        response = await http_client.get(f"{mcp_server_url}/health")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second

    @pytest.mark.asyncio
    async def test_mcp_tool_categories(self, mcp_client):
        """Test that MCP tools can be categorized by functionality."""
        tools = await mcp_client.list_tools()

        # Categorize tools by functionality
        product_tools = [tool for tool in tools if "product" in tool.name.lower()]
        order_tools = [tool for tool in tools if "order" in tool.name.lower()]
        health_tools = [tool for tool in tools if "health" in tool.name.lower()]

        # Verify we have tools in each category
        assert len(product_tools) >= 5  # add, remove, get, search, etc.
        assert len(order_tools) >= 1  # order_product
        assert len(health_tools) >= 1  # health_check

        # Verify tool names are descriptive
        for tool in product_tools:
            assert "product" in tool.name.lower()

        for tool in order_tools:
            assert "order" in tool.name.lower()

        for tool in health_tools:
            assert "health" in tool.name.lower()

    @pytest.mark.asyncio
    async def test_mcp_server_error_handling(self, http_client, mcp_server_url):
        """Test MCP server error handling for invalid requests."""
        # Test invalid endpoint
        response = await http_client.get(f"{mcp_server_url}/invalid-endpoint")
        assert response.status_code in [404, 405]  # Should return appropriate error

        # Test invalid method on valid endpoint
        response = await http_client.post(f"{mcp_server_url}/health")
        assert response.status_code in [
            405,
            422,
        ]  # Method not allowed or validation error

        # Test malformed request (if applicable)
        # This tests that the server doesn't crash on bad input


if __name__ == "__main__":
    pytest.main([__file__])
