import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError

import database  # For direct DB manipulation/verification in tests
import store
from store import mcp_server  # Your FastMCP instance from store.py


@pytest_asyncio.fixture(scope="module")
async def initialized_test_mcp_server():
    """Fixture to provide an initialized FastMCP server instance."""
    # For testing without a real database, we'll use the server as-is
    # The server should handle database unavailability gracefully
    
    # The mcp_server instance is imported from your store.py
    # It should already have tools registered via decorators.
    yield mcp_server


@pytest.mark.asyncio
async def test_health_check_tool(initialized_test_mcp_server):
    """Test the health_check tool functionality."""
    async with Client(initialized_test_mcp_server) as client:
        response = await client.call_tool("health_check")
        assert hasattr(response, "content") and response.content is not None
        assert len(response.content) > 0

        # Parse the response content
        content = response.content[0]
        response_text = getattr(content, "text", str(content))
        
        # The response should contain health information
        assert "status" in response_text.lower() or "health" in response_text.lower()
        assert "mcp-store-db" in response_text.lower()


@pytest.mark.asyncio
async def test_check_database_connectivity_tool(initialized_test_mcp_server):
    """Test the check_database_connectivity tool functionality."""
    async with Client(initialized_test_mcp_server) as client:
        response = await client.call_tool("check_database_connectivity")
        assert hasattr(response, "content") and response.content is not None
        assert len(response.content) > 0

        # Parse the response content
        content = response.content[0]
        response_text = getattr(content, "text", str(content))
        
        # The response should contain database connectivity information
        assert "database" in response_text.lower()
        assert "status" in response_text.lower()


@pytest.mark.asyncio
async def test_tool_discovery(initialized_test_mcp_server):
    """Test that all expected tools are available."""
    async with Client(initialized_test_mcp_server) as client:
        tools = await client.list_tools()

        expected_tools = [
            "get_products",
            "get_product_by_id",
            "get_product_by_name",
            "search_products",
            "add_product",
            "remove_product",
            "order_product",
            "health_check",
            "check_database_connectivity",
        ]

        tool_names = [tool.name for tool in tools]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

        # Verify tool descriptions
        for tool in tools:
            assert hasattr(tool, "description")
            assert tool.description.strip() != ""


@pytest.mark.asyncio
async def test_tool_error_handling_with_unavailable_database(initialized_test_mcp_server):
    """Test that MCP tools handle database unavailability gracefully."""
    async with Client(initialized_test_mcp_server) as client:
        # Test a tool that requires database access
        # This should fail gracefully with a clear error message
        
        try:
            response = await client.call_tool("get_products", {"skip": 0, "limit": 5})
            
            # If we get here, the database might be available
            # This is acceptable in test environments with databases
            if response.ok:
                pytest.skip("Database is available, skipping unavailability test")
            else:
                # Check that the error message is clear
                assert response.content is not None
                
        except Exception as e:
            # The tool should handle errors gracefully
            # Check that the error message is helpful
            error_message = str(e).lower()
            assert any(keyword in error_message for keyword in [
                "database", "unavailable", "connection", "error"
            ])


@pytest.mark.asyncio
async def test_health_check_tool_consistency(initialized_test_mcp_server):
    """Test that health check and database connectivity check are consistent."""
    async with Client(initialized_test_mcp_server) as client:
        # Get both health checks
        health_response = await client.call_tool("health_check")
        connectivity_response = await client.call_tool("check_database_connectivity")
        
        # Parse responses
        health_content = health_response.content[0].text
        connectivity_content = connectivity_response.content[0].text
        
        # Both should contain database status information
        assert "database" in health_content.lower()
        assert "database" in connectivity_content.lower()


@pytest.mark.asyncio
async def test_tool_metadata(initialized_test_mcp_server):
    """Test that MCP tools have proper metadata."""
    async with Client(initialized_test_mcp_server) as client:
        tools = await client.list_tools()

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
async def test_tool_categories(initialized_test_mcp_server):
    """Test that MCP tools can be categorized by functionality."""
    async with Client(initialized_test_mcp_server) as client:
        tools = await client.list_tools()

        # Categorize tools by functionality
        product_tools = [tool for tool in tools if "product" in tool.name.lower()]
        order_tools = [tool for tool in tools if "order" in tool.name.lower()]
        health_tools = [tool for tool in tools if "health" in tool.name.lower() or "connectivity" in tool.name.lower()]

        # Verify we have tools in each category
        assert len(product_tools) >= 5  # add, remove, get, search, etc.
        assert len(order_tools) >= 1  # order_product
        assert len(health_tools) >= 2  # health_check, check_database_connectivity

        # Verify tool names are descriptive
        for tool in product_tools:
            assert "product" in tool.name.lower()

        for tool in order_tools:
            assert "order" in tool.name.lower()

        for tool in health_tools:
            assert "health" in tool.name.lower() or "connectivity" in tool.name.lower()


@pytest.mark.asyncio
async def test_tool_input_validation(initialized_test_mcp_server):
    """Test that MCP tools validate input parameters correctly."""
    async with Client(initialized_test_mcp_server) as client:
        # Test health check tool (no parameters required)
        response = await client.call_tool("health_check", {})
        assert hasattr(response, "content")
        
        # Test database connectivity check tool (no parameters required)
        response = await client.call_tool("check_database_connectivity", {})
        assert hasattr(response, "content")
        
        # Test get_products with valid parameters; DB may be unavailable
        try:
            response = await client.call_tool("get_products", {"skip": 0, "limit": 10})
            assert response.content is not None
        except ToolError:
            # Acceptable in environments without a running database
            pass


@pytest.mark.asyncio
async def test_tool_error_messages_for_llm_agents(initialized_test_mcp_server):
    """Test that error messages are helpful for LLM agents."""
    async with Client(initialized_test_mcp_server) as client:
        # Test that tools provide clear error messages when they fail
        
        # Try to call a tool that requires database access
        try:
            response = await client.call_tool("get_products", {"skip": 0, "limit": 5})
            
            if not response.ok:
                # Check that the error message is clear and helpful
                error_content = response.content[0].text if response.content else str(response)
                error_text = error_content.lower()
                
                # Error should contain helpful information
                helpful_keywords = ["database", "unavailable", "connection", "postgresql", "service"]
                assert any(keyword in error_text for keyword in helpful_keywords)
                
        except Exception as e:
            # Exception should also contain helpful information
            error_message = str(e).lower()
            helpful_keywords = ["database", "unavailable", "connection", "postgresql", "service"]
            assert any(keyword in error_message for keyword in helpful_keywords)


@pytest.mark.asyncio
async def test_health_check_tool_response_structure(initialized_test_mcp_server):
    """Test that health check tool returns properly structured response."""
    async with Client(initialized_test_mcp_server) as client:
        response = await client.call_tool("health_check")
        assert hasattr(response, "content")
        
        # Parse the response
        content = response.content[0].text
        
        # Response should contain JSON-like structure with key fields
        # Note: This is a basic check - in a real test you might want to parse JSON
        required_fields = ["status", "service", "database_status", "database_available"]
        for field in required_fields:
            assert field in content


@pytest.mark.asyncio
async def test_database_connectivity_tool_response_structure(initialized_test_mcp_server):
    """Test that database connectivity tool returns properly structured response."""
    async with Client(initialized_test_mcp_server) as client:
        response = await client.call_tool("check_database_connectivity")
        assert hasattr(response, "content")
        
        # Parse the response
        content = response.content[0].text
        
        # Response should contain JSON-like structure with key fields
        required_fields = ["database_status", "database_available", "status_message", "can_perform_operations"]
        for field in required_fields:
            assert field in content
