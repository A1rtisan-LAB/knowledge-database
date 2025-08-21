#!/bin/bash

# Integration Test Runner Script for Knowledge Database

echo "============================================"
echo "Knowledge Database Integration Test Suite"
echo "============================================"

# Set test environment variables
export APP_ENV=testing
export SECRET_KEY=test-secret-key-for-integration-tests
export DATABASE_URL=sqlite+aiosqlite:///:memory:
export REDIS_URL=redis://localhost:6379/1
export OPENSEARCH_URL=http://localhost:9200
export JWT_SECRET_KEY=test-jwt-secret-key
export JWT_ALGORITHM=HS256
export ACCESS_TOKEN_EXPIRE_MINUTES=30
export REFRESH_TOKEN_EXPIRE_DAYS=7

# Activate virtual environment
source venv/bin/activate

echo ""
echo "Running Integration Tests..."
echo "----------------------------"

# Run tests with coverage
python -m pytest tests/integration/ \
    -v \
    --tb=short \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:htmlcov_integration \
    --maxfail=10 \
    -m integration \
    "$@"

TEST_RESULT=$?

echo ""
echo "============================================"
echo "Integration Test Summary"
echo "============================================"

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ All integration tests passed!"
else
    echo "❌ Some integration tests failed. Check the output above."
fi

echo ""
echo "Coverage report generated at: htmlcov_integration/index.html"
echo ""

exit $TEST_RESULT