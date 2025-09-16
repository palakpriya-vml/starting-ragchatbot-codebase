#!/bin/bash

# Code linting script
set -e

echo "Running code quality checks..."

# Check if virtual environment exists and activate it
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Virtual environment activated."
else
    echo "Warning: No virtual environment found. Make sure dev tools are installed."
fi

# Run flake8 linting
echo "Running flake8 linting..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics

# Check import sorting
echo "Checking import sorting..."
isort . --check-only --diff

# Check code formatting
echo "Checking code formatting..."
black . --check --diff

echo "All quality checks passed!"