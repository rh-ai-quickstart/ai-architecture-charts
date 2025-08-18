# Makefile for MCP DBStore Server
# Provides convenient commands for development, testing, and deployment

.PHONY: help install test test-unit test-integration test-e2e test-coverage clean lint format run stop logs

# Default target
help:
	@echo "MCP Store-DB Server - Available Commands:"
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
	@echo "  test-e2e         Run E2E tests only (requires database)"
	@echo "  test-e2e-local   Run E2E tests with local services (auto-start/stop)"
	@echo "  test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Database:"
	@echo "  db-init          Initialize database with Alembic"
	@echo "  db-migrate       Run database migrations"
	@echo "  db-upgrade       Upgrade database to latest version"
	@echo "  db-downgrade     Downgrade database to previous version"
	@echo "  db-reset         Reset database (drop and recreate)"
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
	@echo "Starting MCP Store-DB server..."
	@if [ -f server.log ]; then rm server.log; fi
	@nohup python3 store.py > server.log 2>&1 & echo "Server started with PID $$!"
	@echo "Server logs will be written to server.log"
	@echo "Use 'make logs' to view logs or 'make stop' to stop the server"

stop:
	@echo "Stopping MCP Store-DB server..."
	@-pkill -f "python3 store.py" || echo "No server running"
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
	pytest tests/ -m unit -v --tb=short

test-integration:
	@echo "Running integration tests..."
	pytest tests/ -m integration -v --tb=short

test-e2e:
	@echo "Running E2E tests..."
	@echo "Note: This requires a running PostgreSQL database"
	pytest tests/ -m e2e -v --tb=short

test-e2e-local:
	@echo "Running E2E tests with local services..."
	@echo "Starting required services..."
	@make start-deps
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "Running E2E tests..."
	pytest tests/ -m e2e -v --tb=short
	@echo "Stopping services..."
	@make stop-deps

test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=. --cov-report=html --cov-report=term-missing -v
	@echo "Coverage report generated in htmlcov/index.html"

test-lazy-connection:
	@echo "Testing lazy database connection management..."
	python3 tests/test_lazy_connection.py

# Database commands
db-init:
	@echo "Initializing database with Alembic..."
	alembic init alembic || echo "Alembic already initialized"
	@echo "Database initialized"

db-migrate:
	@echo "Creating new migration..."
	@read -p "Enter migration message: " message; \
	alembic revision --autogenerate -m "$$message"

db-upgrade:
	@echo "Upgrading database to latest version..."
	alembic upgrade head

db-downgrade:
	@echo "Downgrading database to previous version..."
	alembic downgrade -1

db-reset:
	@echo "Resetting database..."
	@read -p "Are you sure you want to drop all tables? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		echo "Dropping all tables..."; \
		alembic downgrade base; \
		echo "Recreating tables..."; \
		alembic upgrade head; \
	else \
		echo "Database reset cancelled"; \
	fi

# Code quality commands
lint:
	@echo "Running linting checks..."
	@echo "Note: Install flake8, black, and isort for full linting"
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 . --max-line-length=88 --ignore=E203,W503; \
	else \
		echo "flake8 not installed. Install with: pip install flake8"; \
	fi
	@if command -v black >/dev/null 2>&1; then \
		black --check .; \
	else \
		echo "black not installed. Install with: pip install black"; \
	fi

format:
	@echo "Formatting code..."
	@if command -v black >/dev/null 2>&1; then \
		black .; \
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
	@if curl -s http://localhost:8002/health > /dev/null 2>&1; then \
		echo "✅ MCP server is healthy"; \
		curl -s http://localhost:8002/health | python3 -m json.tool; \
	else \
		echo "❌ MCP server is not responding"; \
	fi

tools:
	@echo "Checking available MCP tools..."
	@if curl -s http://localhost:8002/tools > /dev/null 2>&1; then \
		echo "✅ Tools endpoint accessible"; \
		curl -s http://localhost:8002/tools | python3 -m json.tool; \
	else \
		echo "❌ Tools endpoint not accessible"; \
	fi

# Docker/Podman commands
build:
	@echo "Building container image..."
	podman build -t mcp-dbstore .

run-container:
	@echo "Running container..."
	podman run -d --name mcp-dbstore -p 8002:8002 \
		-e DATABASE_URL="postgresql+asyncpg://myuser:mypassword@host.docker.internal:5432/store_db" \
		mcp-dbstore

stop-container:
	@echo "Stopping container..."
	@-podman stop mcp-dbstore || echo "Container not running"
	@-podman rm mcp-dbstore || echo "Container not found"

# External dependency management
start-deps:
	@echo "Starting external dependencies for integration testing..."
	@echo "Starting PostgreSQL..."
	@cd ../.. && podman compose -f compose.yaml up -d postgresql
	@echo "PostgreSQL started on port 5432"

stop-deps:
	@echo "Stopping external dependencies..."
	@cd ../.. && podman compose -f compose.yaml stop postgresql
	@echo "PostgreSQL stopped"

check-deps:
	@echo "Checking external dependencies..."
	@echo "Checking PostgreSQL..."
	@if podman exec mcp-dbstore-postgresql pg_isready -U postgres > /dev/null 2>&1; then \
		echo "✅ PostgreSQL is running"; \
	else \
		echo "❌ PostgreSQL is not running"; \
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
	@echo "MCP Store-DB Server Status:"
	@echo "==========================="
	@if pgrep -f "python3 store.py" > /dev/null; then \
		echo "✅ Server is running"; \
		echo "PID: $$(pgrep -f 'python3 store.py')"; \
		echo "Port: 8002"; \
		echo "Health: $$(curl -s http://localhost:8002/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo 'unknown')"; \
		echo "Database: $$(curl -s http://localhost:8002/health | python3 -c "import sys, json; print(json.load(sys.stdin).get('database_status', 'unknown'))" 2>/dev/null || echo 'unknown')"; \
	else \
		echo "❌ Server is not running"; \
		echo "Use 'make run' to start the server"; \
	fi

