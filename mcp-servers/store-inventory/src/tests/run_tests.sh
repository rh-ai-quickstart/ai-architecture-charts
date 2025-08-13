#!/bin/bash

# Test runner script for MCP Store Inventory Server
# This script runs both unit and integration tests

set -e

echo "🧪 Running MCP Store Inventory Server Tests"
echo "============================================="

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ Virtual environment not activated. Please activate it first:"
    echo "   source ../../.venv/bin/activate"
    exit 1
fi

# Install test dependencies
echo "📦 Installing test dependencies..."
pip install -r requirements-test.txt

# Run unit tests
echo ""
echo "🔬 Running Unit Tests..."
echo "-----------------------"
pytest tests/unit/ -m "unit" --tb=short

# Check if store-inventory API is running
echo ""
echo "🔍 Checking if store-inventory API is running..."
if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    echo "✅ Store API is running on port 8002"

    # Check if MCP server is running
    if curl -s http://localhost:8003/health > /dev/null 2>&1; then
        echo "✅ MCP server is running on port 8003"

        echo ""
        echo "🔗 Running Integration Tests..."
        echo "------------------------------"
        pytest tests/integration/ -m "integration" --tb=short
    else
        echo "⚠️  MCP server is not running on port 8003"
        echo "   Skipping integration tests"
        echo "   Start the MCP server with: python3 server.py"
    fi
else
    echo "⚠️  Store API is not running on port 8002"
    echo "   Skipping integration tests"
    echo "   Start the store-inventory API first"
fi

echo ""
echo "✅ All tests completed!"
echo ""
echo "📊 Test Coverage Report:"
echo "   HTML report: htmlcov/index.html"
echo "   Terminal report: See above output"
