# MCP Store-DB Test Suite

This directory contains the comprehensive test suite for the MCP Store-DB server with lazy database connection management.

## Test Structure

```
tests/
├── __init__.py                 # Makes tests a Python package
├── conftest.py                 # Pytest configuration and fixtures
├── test_crud.py                # CRUD operation tests
├── test_mcp_tools.py           # MCP tool functionality tests
├── test_lazy_connection.py     # Lazy database connection tests
├── run_tests.sh                # Test runner script
├── requirements-test.txt        # Test dependencies
└── README.md                   # This file
```

## Test Categories

### 1. **Unit Tests** (`-m unit`)
- Test individual functions and classes in isolation
- Use mocked dependencies (no real database required)
- Fast execution, high reliability
- Test error handling and edge cases

### 2. **Integration Tests** (`-m integration`)
- Test MCP protocol compliance
- Test tool discovery and metadata
- Test HTTP endpoints
- No external dependencies required

### 3. **End-to-End Tests** (`-m e2e`)
- Test complete workflows with real database
- Require PostgreSQL to be running
- Test actual database operations
- Slower execution, tests real scenarios

## Running Tests

### Using Make Commands
```bash
# Run all tests
make test

# Run specific test categories
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-e2e          # E2E tests only

# Run with coverage
make test-coverage

# Test lazy connection specifically
make test-lazy-connection
```

### Using Test Runner Script
```bash
# Make script executable (first time only)
chmod +x tests/run_tests.sh

# Run different test types
./tests/run_tests.sh unit           # Unit tests
./tests/run_tests.sh integration    # Integration tests
./tests/run_tests.sh e2e           # E2E tests
./tests/run_tests.sh all           # All tests
./tests/run_tests.sh coverage      # With coverage
./tests/run_tests.sh lazy-connection  # Lazy connection test
```

### Using Pytest Directly
```bash
# Install test dependencies first
pip install -r tests/requirements-test.txt

# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/ -m unit -v
pytest tests/ -m integration -v
pytest tests/ -m e2e -v

# Run specific test file
pytest tests/test_crud.py -v

# Run with coverage
pytest tests/ --cov=mcpservers.mcp-store-db --cov-report=html
```

## Test Dependencies

Install test dependencies with:
```bash
pip install -r tests/requirements-test.txt
```

Required packages:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `fastmcp` - MCP testing
- `httpx` - HTTP client for testing

## Test Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Coverage settings (80% minimum)
- Markers for test categorization
- Async mode configuration

### Test Fixtures (`conftest.py`)
- Common test fixtures
- Database state mocking
- Session management
- Sample data providers

## Test Coverage

The test suite aims for **80% minimum coverage** and includes:

- **Database Manager**: Connection states, health monitoring, error handling
- **CRUD Operations**: All database operations with error scenarios
- **MCP Tools**: Tool discovery, metadata, error handling
- **Health Checks**: Server and database status reporting
- **Error Handling**: Graceful degradation and clear error messages

## Test Scenarios

### Lazy Database Connection
- Server starts without database
- Health checks report database status
- MCP tools handle unavailability gracefully
- Clear error messages for LLM agents

### Database Operations
- CRUD operations with available database
- Error handling when database is unavailable
- Business logic error preservation
- Transaction safety

### MCP Protocol
- Tool discovery and metadata
- Input validation
- Response structure validation
- Error message clarity

## Local Development Testing

### With Compose (Recommended)
```bash
# Start services
podman compose up -d

# Run tests
make test-e2e-local

# Stop services
podman compose down
```

### Manual Database Setup
```bash
# Start PostgreSQL manually
podman compose -f ../../compose.yaml up -d postgresql

# Run tests
make test-e2e

# Stop PostgreSQL
podman compose -f ../../compose.yaml stop postgresql
```

## Continuous Integration

Tests are designed to run in CI environments:
- Unit and integration tests require no external services
- E2E tests can be skipped if database is unavailable
- Coverage reporting for quality gates
- Fast execution for quick feedback

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're running from the `mcp_store_db` directory
2. **Missing Dependencies**: Install test requirements with `pip install -r tests/requirements-test.txt`
3. **Database Connection**: E2E tests require PostgreSQL; use `make test-e2e-local` for auto-setup
4. **Permission Errors**: Make test runner executable with `chmod +x tests/run_tests.sh`

### Debug Mode
```bash
# Run tests with verbose output
pytest tests/ -v -s --tb=long

# Run specific test with debug
pytest tests/test_crud.py::test_crud_operations_with_unavailable_database -v -s
```

## Adding New Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test functions: `test_*`
- Test classes: `Test*`

### Test Markers
```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.e2e          # End-to-end test
@pytest.mark.slow         # Slow test
```

### Test Structure
```python
@pytest.mark.asyncio
async def test_functionality():
    """Test description."""
    # Arrange
    # Act
    # Assert
```

## Performance

- **Unit Tests**: < 1 second
- **Integration Tests**: < 5 seconds
- **E2E Tests**: < 30 seconds (with database)
- **Full Suite**: < 1 minute

## Contributing

When adding new tests:
1. Follow the existing test structure
2. Use appropriate test markers
3. Mock external dependencies for unit tests
4. Ensure tests are deterministic
5. Add to the appropriate test category
6. Update this documentation if needed