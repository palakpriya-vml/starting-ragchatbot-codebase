#!/bin/bash

# Test running script
set -e

echo "Running tests..."

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Virtual environment activated."
else
    echo "Warning: No virtual environment found. Make sure dependencies are installed."
fi

# Run pytest
echo "Running pytest..."
pytest -v --tb=short

echo "All tests passed!"