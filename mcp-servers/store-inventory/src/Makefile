# Makefile for MCP Store Inventory Server
# Provides convenient commands for development, testing, and deployment

.PHONY: help install test test-unit test-integration test-coverage clean lint format run stop logs

# Default target
help:
	@echo "MCP Store Inventory Server - Available Commands:"
	@echo ""
	@echo "Development:"
	@echo "  install          Install dependencies"
	@echo "  run              Start the MCP server"
	@echo "  stop             Stop the MCP server"
	@echo "  logs             Show server logs"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only (mocked, no external deps)"
	@echo "  test-integration Run integration tests only (MCP protocol, no external deps)"
	@echo "  test-e2e         Run E2E tests only (requires external services)"
	@echo "  test-e2e-local   Run E2E tests with local services (auto-start/stop)"
	@echo "  test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linting checks"
	@echo "  format           Format code with black"
	@echo ""
	@echo "Dependencies:"
	@echo "  start-deps       Start external services for integration testing"
	@echo "  stop-deps        Stop external services"
	@echo "  check-deps       Check status of external services"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            Clean up generated files"
	@echo "  help             Show this help message"

# Development commands
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	pip install -r tests/requirements-test.txt

run:
	@echo "Starting MCP Store Inventory server..."
	@if [ -f server.log ]; then rm server.log; fi
	@nohup python3 server.py > server.log 2>&1 & echo "Server started with PID $$!"
	@echo "Server logs will be written to server.log"
	@echo "Use 'make logs' to view logs or 'make stop' to stop the server"

stop:
	@echo "Stopping MCP Store Inventory server..."
	@-pkill -f "python3 server.py" || echo "No server running"
	@echo "Server stopped"

logs:
	@if [ -f server.log ]; then \
		tail -f server.log; \
	else \
		echo "No server.log found. Start the server with 'make run'"; \
	fi

# Testing commands
test: test-unit test-integration test-e2e
	@echo "All tests completed!"

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -v --tb=short

test-integration:
	@echo "Running integration tests..."
	@echo "Note: This tests MCP server integration without external dependencies"
	pytest tests/integration/ -v --tb=short

test-e2e:
	@echo "Running E2E tests..."
	@echo "Note: This requires both MCP server and store-inventory API to be running"
	pytest tests/e2e/ -v --tb=short

test-e2e-local:
	@echo "Running E2E tests with local services..."
	@echo "Starting required services..."
	@make start-deps
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Running E2E tests..."
	pytest tests/e2e/ -v --tb=short
	@echo "Stopping services..."
	@make stop-deps

test-integration-local:
	@echo "Running integration tests with local services..."
	@echo "Starting required services..."
	@make start-deps
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Running integration tests..."
	pytest tests/integration/ -v --tb=short
	@echo "Stopping services..."
	@make stop-deps



test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=server --cov-report=html --cov-report=term-missing -v
	@echo "Coverage report generated in htmlcov/index.html"

# Code quality commands
lint:
	@echo "Running linting checks..."
	@echo "Note: Install flake8, black, and isort for full linting"
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 server.py tests/ --max-line-length=88 --ignore=E203,W503; \
	else \
		echo "flake8 not installed. Install with: pip install flake8"; \
	fi
	@if command -v black >/dev/null 2>&1; then \
		black --check server.py tests/; \
	else \
		echo "black not installed. Install with: pip install black"; \
	fi

format:
	@echo "Formatting code..."
	@if command -v black >/dev/null 2>&1; then \
		black server.py tests/; \
	else \
		echo "black not installed. Install with: pip install black"; \
	fi

# Maintenance commands
clean:
	@echo "Cleaning up generated files..."
	@-rm -rf __pycache__/
	@-rm -rf .pytest_cache/
	@-rm -rf htmlcov/
	@-rm -rf .coverage
	@-rm -f server.log
	@-rm -f nohup.out
	@echo "Cleanup complete"

# Health check commands
health:
	@echo "Checking server health..."
	@if curl -s http://localhost:8003/health > /dev/null 2>&1; then \
		echo "✅ MCP server is healthy"; \
		curl -s http://localhost:8003/health | python3 -m json.tool; \
	else \
		echo "❌ MCP server is not responding"; \
	fi

tools:
	@echo "Checking available MCP tools..."
	@if curl -s http://localhost:8003/tools > /dev/null 2>&1; then \
		echo "✅ Tools endpoint accessible"; \
		curl -s http://localhost:8003/tools | python3 -m json.tool; \
	else \
		echo "❌ Tools endpoint not accessible"; \
	fi

# Docker/Podman commands
build:
	@echo "Building container image..."
	podman build -t mcp-store-inventory .

run-container:
	@echo "Running container..."
	podman run -d --name mcp-store-inventory -p 8003:8003 mcp-store-inventory

stop-container:
	@echo "Stopping container..."
	@-podman stop mcp-store-inventory || echo "Container not running"
	@-podman rm mcp-store-inventory || echo "Container not found"

# External dependency management
start-deps:
	@echo "Starting external dependencies for integration testing..."
	@echo "Starting store-inventory API..."
	@cd ../store-inventory && make run 2>/dev/null || \
		(echo "store-inventory not found or make run not available"; \
		 echo "Please ensure store-inventory is running on port 8002")
	@echo "Starting MCP server..."
	@make run
	@echo "Waiting for services to be ready..."
	@echo "Store API: http://localhost:8002/health"
	@echo "MCP Server: http://localhost:8003/health"

stop-deps:
	@echo "Stopping external dependencies..."
	@make stop
	@echo "Note: store-inventory API may still be running in another terminal"
	@echo "Use 'cd ../store-inventory && make stop' to stop it"

check-deps:
	@echo "Checking external dependencies..."
	@echo "Checking store-inventory API..."
	@if curl -s http://localhost:8002/health > /dev/null 2>&1; then \
		echo "✅ Store API is running on port 8002"; \
	else \
		echo "❌ Store API is not running on port 8002"; \
	fi
	@echo "Checking MCP server..."
	@if curl -s http://localhost:8003/health > /dev/null 2>&1; then \
		echo "✅ MCP server is running on port 8003"; \
	else \
		echo "❌ MCP server is not running on port 8003"; \
	fi

# Development environment setup
setup-dev:
	@echo "Setting up development environment..."
	@if [ ! -d "../../.venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv ../../.venv; \
	fi
	@echo "Activate virtual environment with: source ../../.venv/bin/activate"
	@echo "Then run: make install"

# Quick development workflow
dev: install run
	@echo "Development environment ready!"
	@echo "Server is running. Use 'make logs' to view logs or 'make stop' to stop"

# Show server status
status:
	@echo "MCP Store Inventory Server Status:"
	@echo "=================================="
	@if pgrep -f "python3 server.py" > /dev/null; then \
		echo "✅ Server is running"; \
		echo "PID: $$(pgrep -f 'python3 server.py')"; \
		echo "Port: 8003"; \
		echo "Health: $$(curl -s http://localhost:8003/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('store_api_status', 'unknown'))" 2>/dev/null || echo 'unknown')"; \
	else \
		echo "❌ Server is not running"; \
		echo "Use 'make run' to start the server"; \
	fi
