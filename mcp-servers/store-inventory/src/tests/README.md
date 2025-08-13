# Testing Guide for MCP Store Inventory Server

This directory contains a comprehensive testing suite organized into three tiers to ensure robust testing of the MCP server functionality.

## 🏗️ **Test Structure**

### **1. Unit Tests** (`tests/unit/`)
- **Purpose**: Test individual functions and components in isolation
- **Dependencies**: All external dependencies are mocked
- **Execution**: Fast, no network calls, no external services required
- **Coverage**: Business logic, error handling, input validation

### **2. Integration Tests** (`tests/integration/`)
- **Purpose**: Test MCP server integration with LLM-like behavior
- **Dependencies**: MCP server instance (no external API calls)
- **Execution**: Medium speed, tests MCP protocol and tool discovery
- **Coverage**: Tool schemas, MCP endpoints, server configuration

### **3. E2E Tests** (`tests/e2e/`)
- **Purpose**: Test complete end-to-end workflows simulating actual LLM usage
- **Dependencies**: Both MCP server AND store-inventory API must be running
- **Execution**: Slower, makes real API calls, tests complete tool functionality
- **Coverage**: Full tool execution, error handling, concurrent operations

## 🚀 **Quick Start**

### **Run All Tests**
```bash
make test
```

### **Run Specific Test Types**

#### **Unit Tests (Fast, No Dependencies)**
```bash
make test-unit
```

#### **Integration Tests (MCP Protocol, No External Dependencies)**
```bash
make test-integration
```

#### **E2E Tests (Requires External Services)**
```bash
make test-e2e
```

#### **E2E Tests with Auto-Service Management**
```bash
make test-e2e-local
```

## 📋 **Test Details**

### **Unit Tests** (`tests/unit/`)
- **File**: `test_server_unit.py`
- **Tests**:
  - API request handling with mocked responses
  - Error handling (timeouts, HTTP errors, API unavailability)
  - Tool function logic with mocked dependencies
  - Health check functionality
  - Input validation and edge cases

### **Integration Tests** (`tests/integration/`)
- **File**: `test_mcp_integration.py`
- **Tests**:
  - MCP tool discovery and metadata
  - Tool schemas and descriptions
  - MCP protocol endpoints (`/health`, `/tools`, `/sse`, `/messages`)
  - Server configuration and readiness
  - Error handling for invalid requests

### **E2E Tests** (`tests/e2e/`)
- **File**: `test_e2e_tools.py`
- **Tests**:
  - Complete product lifecycle (create, read, update, delete)
  - Order creation workflow
  - Search functionality with real data
  - Pagination and concurrent operations
  - Error handling and validation
  - Performance under load

## 🔧 **Prerequisites**

### **For Unit Tests**
- Python 3.8+
- pytest and pytest-asyncio
- Virtual environment activated

### **For Integration Tests**
- All unit test prerequisites
- FastMCP 2.x installed
- No external services required

### **For E2E Tests**
- All integration test prerequisites
- `store-inventory` API running on port 8002
- `mcp-store-inventory` server running on port 8003

## 🚨 **Troubleshooting**

### **Event Loop Issues**
If you encounter "Event loop is closed" errors:
- **Unit Tests**: Should never happen - all dependencies are mocked
- **Integration Tests**: Should never happen - no external HTTP calls
- **E2E Tests**: May happen if services are not properly started

### **Service Connection Issues**
- Ensure `store-inventory` API is running: `curl http://localhost:8002/health`
- Ensure MCP server is running: `curl http://localhost:8003/health`
- Check service logs for errors

### **Test Failures**
- **Unit Tests**: Check mock setup and function logic
- **Integration Tests**: Check MCP server configuration
- **E2E Tests**: Check external service availability and data state

## 📊 **Coverage Reports**

Generate coverage reports:
```bash
make test-coverage
```

This will:
- Run all tests with coverage tracking
- Generate HTML coverage report in `htmlcov/`
- Show terminal coverage summary

## 🎯 **Best Practices**

### **Writing Unit Tests**
- Mock all external dependencies
- Test error conditions and edge cases
- Use descriptive test names
- Keep tests focused and isolated

### **Writing Integration Tests**
- Test MCP protocol compliance
- Verify tool discovery and schemas
- Test server endpoints and configuration
- Avoid external service dependencies

### **Writing E2E Tests**
- Test complete user workflows
- Use realistic data and scenarios
- Clean up test data after tests
- Handle service availability gracefully

## 🔄 **Continuous Integration**

The test suite is designed to work in CI/CD environments:
- **Unit Tests**: Always run, no external dependencies
- **Integration Tests**: Run if FastMCP is available
- **E2E Tests**: Run only in environments with full service stack

## 📚 **Additional Resources**

- [FastMCP Testing Documentation](https://gofastmcp.com/patterns/testing)
- [Pytest Async Testing](https://pytest-asyncio.readthedocs.io/)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
