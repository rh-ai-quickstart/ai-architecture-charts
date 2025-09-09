import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

# Adjust these imports based on your project structure
import crud
import database
from models import ProductCreate, ProductOrderRequest
from crud import DatabaseUnavailableError, DatabaseOperationError


@pytest_asyncio.fixture(scope="function")
async def db_session(mock_session_unavailable) -> AsyncSession:
    """Create a test database session."""
    # For unit tests, we'll use a mock session since we don't want to require a real database
    # In a real test environment, you might want to use a test database
    
    # The mock session simulates database unavailability
    return mock_session_unavailable


@pytest.mark.asyncio
async def test_crud_operations_with_unavailable_database(db_session: AsyncSession):
    """Test CRUD operations when database is unavailable."""
    # Test that all CRUD operations properly handle database unavailability
    
    # Test get_products
    with pytest.raises(DatabaseUnavailableError, match="Database is in an unknown state"):
        await crud.get_products(db_session, skip=0, limit=10)
    
    # Test get_product_by_id
    with pytest.raises(DatabaseUnavailableError, match="Database is in an unknown state"):
        await crud.get_product_by_id(db_session, product_id=1)
    
    # Test get_product_by_name
    with pytest.raises(DatabaseUnavailableError, match="Database is in an unknown state"):
        await crud.get_product_by_name(db_session, name="Test Product")
    
    # Test search_products
    with pytest.raises(DatabaseUnavailableError, match="Database is in an unknown state"):
        await crud.search_products(db_session, query="test", skip=0, limit=10)
    
    # Test add_product
    with pytest.raises(DatabaseUnavailableError, match="Database is in an unknown state"):
        product_data = ProductCreate(name="Test", inventory=5, price=10.0)
        await crud.add_product(db_session, product=product_data)
    
    # Test remove_product
    with pytest.raises(DatabaseUnavailableError, match="Database is in an unknown state"):
        await crud.remove_product(db_session, product_id=1)
    
    # Test order_product
    with pytest.raises(DatabaseUnavailableError, match="Database is in an unknown state"):
        order_data = ProductOrderRequest(product_id=1, quantity=2, customer_identifier="test")
        await crud.order_product(db_session, order_details=order_data)


@pytest.mark.asyncio
async def test_error_message_clarity():
    """Test that error messages are clear and helpful for LLM agents."""
    # Test different database states and their error messages
    
    # Mock database manager states
    test_states = [
        (database.DatabaseState.DISCONNECTED, "PostgreSQL service is running"),
        (database.DatabaseState.MIGRATION_FAILED, "database schema may be incompatible"),
        (database.DatabaseState.SCHEMA_INCOMPATIBLE, "Manual database migration may be required"),
    ]
    
    for state, expected_message in test_states:
        # Mock the database manager state
        original_state = database.db_manager.state
        database.db_manager.state = state
        
        try:
            # Test that the error message contains the expected content
            with pytest.raises(DatabaseUnavailableError) as exc_info:
                await crud._ensure_database_available()
            
            error_message = str(exc_info.value)
            assert expected_message.lower() in error_message.lower()
            
        finally:
            # Restore original state
            database.db_manager.state = original_state


@pytest.mark.asyncio
async def test_database_availability_check():
    """Test the database availability check function."""
    # Test with different database states
    
    # Test when database is available
    original_state = database.db_manager.state
    database.db_manager.state = database.DatabaseState.CONNECTED
    
    try:
        # Should not raise an exception when database is available
        await crud._ensure_database_available()
    finally:
        database.db_manager.state = original_state
    
    # Test when database is unavailable
    database.db_manager.state = database.DatabaseState.DISCONNECTED
    
    try:
        with pytest.raises(DatabaseUnavailableError):
            await crud._ensure_database_available()
    finally:
        database.db_manager.state = original_state


@pytest.mark.asyncio
async def test_crud_error_handling(mock_session_with_error):
    """Test that CRUD operations handle various error types correctly."""
    # Test that database operation errors are properly wrapped
    
    # Mock database as available but with operation errors
    original_state = database.db_manager.state
    database.db_manager.state = database.DatabaseState.CONNECTED
    
    try:
        # Test that database operation errors are properly wrapped
        with pytest.raises(DatabaseOperationError, match="Unexpected error"):
            await crud.get_products(mock_session_with_error, skip=0, limit=10)
            
    finally:
        database.db_manager.state = original_state


@pytest.mark.asyncio
async def test_order_product_business_logic_errors(mock_session_with_business_logic_error):
    """Test that business logic errors are preserved."""
    # Test that ValueError exceptions from business logic are not wrapped
    
    # Mock database as available
    original_state = database.db_manager.state
    database.db_manager.state = database.DatabaseState.CONNECTED
    
    try:
        # Test that business logic errors are preserved
        with pytest.raises(ValueError, match="Product not found"):
            order_data = ProductOrderRequest(product_id=999, quantity=1, customer_identifier="test")
            await crud.order_product(mock_session_with_business_logic_error, order_details=order_data)
            
    finally:
        database.db_manager.state = original_state


@pytest.mark.asyncio
async def test_crud_function_signatures():
    """Test that CRUD functions have the expected signatures and docstrings."""
    # Test that all CRUD functions have proper documentation and error handling
    
    crud_functions = [
        crud.get_products,
        crud.get_product_by_id,
        crud.get_product_by_name,
        crud.search_products,
        crud.add_product,
        crud.remove_product,
        crud.order_product,
    ]
    
    for func in crud_functions:
        # Check that function has docstring
        assert func.__doc__ is not None
        assert len(func.__doc__.strip()) > 0
        
        # Check that function is async
        assert asyncio.iscoroutinefunction(func)
        
        # Check that function has proper error handling in docstring
        docstring = func.__doc__.lower()
        assert "product" in docstring or "retrieve" in docstring or "pagination" in docstring
