#!/bin/bash

# SQLite-based test runner for environments without Docker
# This script uses SQLite in-memory database and mock services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_section() {
    echo -e "\n${BLUE}==== $1 ====${NC}\n"
}

# Check Python installation
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_info "Python version: $PYTHON_VERSION"
}

# Setup virtual environment
setup_venv() {
    log_section "Setting up virtual environment"
    
    cd "$PROJECT_ROOT"
    
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    log_info "Virtual environment activated"
}

# Install dependencies
install_dependencies() {
    log_section "Installing dependencies"
    
    cd "$PROJECT_ROOT"
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install main requirements
    log_info "Installing main requirements..."
    pip install -r requirements.txt
    
    # Install test requirements
    log_info "Installing test requirements..."
    pip install -r requirements-test.txt
    
    # Install SQLite async support
    log_info "Installing SQLite async support..."
    pip install aiosqlite
    
    log_info "Dependencies installed successfully"
}

# Run tests with SQLite
run_tests() {
    log_section "Running tests with SQLite backend"
    
    cd "$PROJECT_ROOT"
    
    # Set environment variables for SQLite testing
    export TESTING=true
    export ENVIRONMENT=test
    export DATABASE_URL="sqlite+aiosqlite:///:memory:"
    export SECRET_KEY="test-secret-key-for-testing-only"
    export JWT_ALGORITHM="HS256"
    export JWT_EXPIRATION_DELTA=3600
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # Use SQLite conftest
    export PYTEST_CURRENT_TEST_CONFTEST="tests/conftest_sqlite.py"
    
    log_info "Running tests with SQLite in-memory database..."
    log_info "OpenSearch and Redis will be mocked"
    
    # Parse test arguments
    TEST_ARGS=""
    COVERAGE_ARGS=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --coverage)
                COVERAGE_ARGS="--cov=app --cov-report=html --cov-report=term --cov-report=xml"
                shift
                ;;
            --verbose|-v)
                TEST_ARGS="$TEST_ARGS -v"
                shift
                ;;
            --quiet|-q)
                TEST_ARGS="$TEST_ARGS -q"
                shift
                ;;
            --markers|-m)
                TEST_ARGS="$TEST_ARGS -m $2"
                shift 2
                ;;
            *)
                TEST_ARGS="$TEST_ARGS $1"
                shift
                ;;
        esac
    done
    
    # Default test path if not specified
    if [ -z "$TEST_ARGS" ]; then
        TEST_ARGS="tests/"
    fi
    
    # Run pytest with SQLite configuration
    pytest -c pytest.ini \
        --override-ini="addopts=-v --tb=short --color=yes" \
        --confcutdir="$PROJECT_ROOT" \
        -p no:warnings \
        $COVERAGE_ARGS \
        $TEST_ARGS
    
    TEST_EXIT_CODE=$?
    
    if [ $TEST_EXIT_CODE -eq 0 ]; then
        log_info "All tests passed!"
        
        if [ -n "$COVERAGE_ARGS" ]; then
            log_info "Coverage report generated:"
            echo "  - HTML: htmlcov/index.html"
            echo "  - XML: coverage.xml"
        fi
    else
        log_error "Some tests failed. Exit code: $TEST_EXIT_CODE"
    fi
    
    return $TEST_EXIT_CODE
}

# Run specific test file or directory
run_specific_test() {
    local test_path=$1
    shift
    
    log_section "Running specific test: $test_path"
    
    cd "$PROJECT_ROOT"
    source venv/bin/activate
    
    # Set environment variables
    export TESTING=true
    export ENVIRONMENT=test
    export DATABASE_URL="sqlite+aiosqlite:///:memory:"
    export SECRET_KEY="test-secret-key-for-testing-only"
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    pytest -c pytest.ini \
        --confcutdir="$PROJECT_ROOT" \
        -p no:warnings \
        "$test_path" \
        "$@"
}

# Clean up test artifacts
clean_up() {
    log_section "Cleaning up test artifacts"
    
    cd "$PROJECT_ROOT"
    
    # Remove Python cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Remove coverage files
    rm -f .coverage coverage.xml
    rm -rf htmlcov/
    
    # Remove test database files (if any)
    rm -f test.db test.db-journal
    
    log_info "Cleanup complete"
}

# Show help
show_help() {
    echo "SQLite Test Runner - Run tests without Docker using SQLite in-memory database"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  setup       - Set up virtual environment and install dependencies"
    echo "  test        - Run all tests with SQLite backend"
    echo "  run <path>  - Run specific test file or directory"
    echo "  clean       - Clean up test artifacts"
    echo "  help        - Show this help message"
    echo ""
    echo "Test Options:"
    echo "  --coverage  - Generate coverage report"
    echo "  --verbose   - Verbose output"
    echo "  --quiet     - Quiet output"
    echo "  -m <marker> - Run tests with specific marker"
    echo ""
    echo "Examples:"
    echo "  $0 setup                           # Set up environment"
    echo "  $0 test                            # Run all tests"
    echo "  $0 test --coverage                 # Run with coverage"
    echo "  $0 run tests/test_auth.py         # Run specific test file"
    echo "  $0 test -m \"not slow\"             # Run non-slow tests"
    echo ""
    echo "Note: This uses SQLite in-memory database and mocks for OpenSearch/Redis."
    echo "      For full integration testing, use Docker-based tests instead."
}

# Main script
main() {
    case "$1" in
        setup)
            check_python
            setup_venv
            install_dependencies
            ;;
        test)
            shift
            check_python
            setup_venv
            run_tests "$@"
            ;;
        run)
            shift
            check_python
            setup_venv
            run_specific_test "$@"
            ;;
        clean)
            clean_up
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            if [ -z "$1" ]; then
                # Default action: run tests
                check_python
                setup_venv
                run_tests
            else
                echo "Unknown command: $1"
                echo "Run '$0 help' for usage information"
                exit 1
            fi
            ;;
    esac
}

main "$@"