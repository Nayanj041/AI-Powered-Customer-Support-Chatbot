#!/bin/bash

# Run tests for AI-Powered Customer Support Chatbot

set -e

echo "🧪 Running AI-Powered Customer Support Chatbot tests..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check if pytest is installed
if ! python -c "import pytest" &> /dev/null; then
    echo "❌ pytest is not installed. Installing..."
    pip install pytest pytest-asyncio
fi

# Set test environment
export PYTHONPATH=$(pwd)
export TESTING=true

# Run tests with verbose output
echo "Running unit tests..."
python -m pytest tests/ -v --tb=short

# Run tests with coverage if coverage is available
if python -c "import coverage" &> /dev/null 2>&1; then
    echo ""
    echo "Running tests with coverage..."
    python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
    echo "📊 Coverage report generated in htmlcov/"
else
    echo "💡 Install coverage for test coverage reports: pip install coverage pytest-cov"
fi

echo ""
echo "✅ All tests completed!"
