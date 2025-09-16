#!/bin/bash

# Development environment setup script
set -e

echo "Setting up development environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install project with dev dependencies
echo "Installing project with development dependencies..."
pip install -e ".[dev]"

echo "Development environment setup complete!"
echo "To activate the environment in the future, run: source venv/bin/activate"