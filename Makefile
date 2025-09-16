# Makefile for development tasks

.PHONY: help setup format lint test clean all

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

setup:  ## Set up development environment
	@./scripts/setup_dev.sh

format:  ## Format code with black and isort
	@./scripts/format.sh

lint:  ## Run linting and code quality checks
	@./scripts/lint.sh

test:  ## Run tests
	@./scripts/test.sh

clean:  ## Clean up generated files
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete!"

all: format lint test  ## Run format, lint, and test