#!/bin/bash

# Test runner script for MCP DBStore Server
# This script provides an easy way to run different types of tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python environment
check_python_env() {
    print_status "Checking Python environment..."
    
    if ! command_exists python3; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    if ! command_exists pip3; then
        print_error "pip3 is not installed"
        exit 1
    fi
    
    print_success "Python environment is ready"
}

# Function to install test dependencies
install_deps() {
    print_status "Installing test dependencies..."
    
    if [ ! -f "requirements-test.txt" ]; then
        print_error "Test requirements file not found"
        exit 1
    fi
    
    pip3 install -r requirements-test.txt
    print_success "Test dependencies installed"
}

# Function to run unit tests
run_unit_tests() {
    print_status "Running unit tests..."
    python3 -m pytest . -m unit -v --tb=short
    print_success "Unit tests completed"
}

# Function to run integration tests
run_integration_tests() {
    print_status "Running integration tests..."
    python3 -m pytest . -m integration -v --tb=short
    print_success "Integration tests completed"
}

# Function to run E2E tests
run_e2e_tests() {
    print_status "Running E2E tests..."
    python3 -m pytest . -m e2e -v --tb=short
    print_success "E2E tests completed"
}

# Function to run all tests
run_all_tests() {
    print_status "Running all tests..."
    python3 -m pytest . -v --tb=short
    print_success "All tests completed"
}

# Function to run tests with coverage
run_coverage_tests() {
    print_status "Running tests with coverage..."
    python3 -m pytest . --cov=. --cov-report=html --cov-report=term-missing -v
    print_success "Coverage tests completed"
    print_status "Coverage report generated in htmlcov/index.html"
}

# Function to run lazy connection test
run_lazy_connection_test() {
    print_status "Running lazy connection test..."
    python3 -m pytest test_lazy_connection.py -v --tb=short
    print_success "Lazy connection test completed"
}

# Function to show help
show_help() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  unit              Run unit tests only"
    echo "  integration       Run integration tests only"
    echo "  e2e               Run E2E tests only"
    echo "  all               Run all tests"
    echo "  coverage          Run tests with coverage"
    echo "  lazy-connection   Run lazy connection test"
    echo "  install           Install test dependencies"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 unit           # Run unit tests"
    echo "  $0 all            # Run all tests"
    echo "  $0 coverage       # Run tests with coverage"
}

# Main script logic
main() {
    case "${1:-help}" in
        "unit")
            check_python_env
            install_deps
            run_unit_tests
            ;;
        "integration")
            check_python_env
            install_deps
            run_integration_tests
            ;;
        "e2e")
            check_python_env
            install_deps
            run_e2e_tests
            ;;
        "all")
            check_python_env
            install_deps
            run_all_tests
            ;;
        "coverage")
            check_python_env
            install_deps
            run_coverage_tests
            ;;
        "lazy-connection")
            check_python_env
            install_deps
            run_lazy_connection_test
            ;;
        "install")
            check_python_env
            install_deps
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@"
