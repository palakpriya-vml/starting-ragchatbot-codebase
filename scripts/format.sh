#!/bin/bash

# Code formatting script
set -e

echo "Running code formatting tools..."

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Virtual environment activated."
else
    echo "Warning: No virtual environment found. Make sure dev tools are installed."
fi

# Format imports with isort
echo "Formatting imports with isort..."
isort . --check-only --diff || {
    echo "Fixing import formatting..."
    isort .
}

# Format code with black
echo "Formatting code with black..."
black . --check --diff || {
    echo "Fixing code formatting..."
    black .
}

echo "Code formatting complete!"