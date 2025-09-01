"""
Pytest configuration and fixtures for MCP DBStore tests.

This file provides common test fixtures and configuration that can be used
across all test modules.
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from database import db_manager, DatabaseState


@pytest.fixture(autouse=True)
def reset_database_manager():
    """Reset database manager state before each test."""
    # Store original state
    original_state = db_manager.state
    
    # Reset to initial state
    db_manager.state = DatabaseState.UNKNOWN
    
    yield
    
    # Restore original state
    db_manager.state = original_state


@pytest.fixture
def mock_database_session():
    """Create a mock database session for testing."""
    session = AsyncMock()
    
    # Mock common session methods
    session.execute = AsyncMock()
    session.add = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    
    return session


@pytest.fixture
def mock_database_available():
    """Mock database as available for testing."""
    original_state = db_manager.state
    db_manager.state = DatabaseState.CONNECTED
    
    yield
    
    db_manager.state = original_state


@pytest.fixture
def mock_database_unavailable():
    """Mock database as unavailable for testing."""
    original_state = db_manager.state
    db_manager.state = DatabaseState.DISCONNECTED
    
    yield
    
    db_manager.state = original_state


@pytest.fixture
def mock_database_migration_failed():
    """Mock database with migration failure for testing."""
    original_state = db_manager.state
    db_manager.state = DatabaseState.MIGRATION_FAILED
    
    yield
    
    db_manager.state = original_state


@pytest.fixture
def mock_database_schema_incompatible():
    """Mock database with schema incompatibility for testing."""
    original_state = db_manager.state
    db_manager.state = DatabaseState.SCHEMA_INCOMPATIBLE
    
    yield
    
    db_manager.state = original_state


@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        "name": "Test Product",
        "description": "A test product for testing purposes",
        "inventory": 10,
        "price": 29.99
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "product_id": 1,
        "quantity": 2,
        "customer_identifier": "test_customer_123"
    }


@pytest.fixture
def mock_product_db():
    """Mock product database object for testing."""
    product = MagicMock()
    product.id = 1
    product.name = "Test Product"
    product.description = "A test product"
    product.inventory = 10
    product.price = 29.99
    return product


@pytest.fixture
def mock_order_db():
    """Mock order database object for testing."""
    order = MagicMock()
    order.id = 1
    order.product_id = 1
    order.quantity = 2
    order.customer_identifier = "test_customer_123"
    return order


@pytest.fixture
def mock_session_unavailable():
    """Mock session that simulates database unavailability."""
    class MockAsyncSession:
        async def execute(self, query):
            from crud import DatabaseUnavailableError
            raise DatabaseUnavailableError("Database is unavailable for testing")
        
        async def add(self, obj):
            pass
        
        async def flush(self):
            pass
        
        async def refresh(self, obj):
            pass
        
        async def delete(self, obj):
            pass
        
        async def commit(self):
            pass
        
        async def rollback(self):
            pass
        
        async def close(self):
            pass
    
    return MockAsyncSession()


@pytest.fixture
def mock_session_with_error():
    """Mock session that simulates database operation errors."""
    class MockAsyncSession:
        async def execute(self, query):
            raise Exception("Simulated database error")
        
        async def add(self, obj):
            pass
        
        async def flush(self):
            pass
        
        async def refresh(self, obj):
            pass
        
        async def delete(self, obj):
            pass
        
        async def commit(self):
            pass
        
        async def rollback(self):
            pass
        
        async def close(self):
            pass
    
    return MockAsyncSession()


@pytest.fixture
def mock_session_with_business_logic_error():
    """Mock session that simulates business logic errors."""
    class MockAsyncSession:
        async def execute(self, query):
            raise ValueError("Product not found")
        
        async def add(self, obj):
            pass
        
        async def flush(self):
            pass
        
        async def refresh(self, obj):
            pass
        
        async def delete(self, obj):
            pass
        
        async def commit(self):
            pass
        
        async def rollback(self):
            pass
        
        async def close(self):
            pass
    
    return MockAsyncSession()


# Test markers
pytest_plugins = ["pytest_asyncio"]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers."""
    for item in items:
        # Add unit marker to tests that don't have any marker
        if not any(marker.name in ["slow", "integration", "unit", "e2e"] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)
