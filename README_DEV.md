# Development Setup

## Quick Start

1. **Set up development environment:**
   ```bash
   make setup
   ```
   Or manually:
   ```bash
   ./scripts/setup_dev.sh
   ```

2. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

## Development Commands

### Using Make (Recommended)
```bash
make help          # Show available commands
make setup         # Set up development environment
make format        # Format code with black and isort
make lint          # Run linting and code quality checks
make test          # Run tests
make clean         # Clean up generated files
make all           # Run format, lint, and test
```

### Using Scripts Directly
```bash
./scripts/setup_dev.sh  # Set up development environment
./scripts/format.sh     # Format code
./scripts/lint.sh       # Run linting
./scripts/test.sh       # Run tests
```

## Code Quality Tools

### Black (Code Formatter)
- **Config:** `[tool.black]` section in `pyproject.toml`
- **Line length:** 88 characters
- **Target:** Python 3.13+

### Flake8 (Linter)
- **Config:** `[tool.flake8]` section in `pyproject.toml`
- **Max line length:** 88 characters
- **Ignored:** E203, W503 (black compatibility)

### isort (Import Sorter)
- **Config:** `[tool.isort]` section in `pyproject.toml`
- **Profile:** black (for compatibility)

## Pre-commit Workflow

Before committing code:
```bash
make all
```

This will:
1. Format code with black and isort
2. Run linting checks
3. Run all tests

## Installation Notes

- The project uses `pyproject.toml` for configuration
- Development dependencies are in `[project.optional-dependencies.dev]`
- Virtual environment is recommended to avoid conflicts