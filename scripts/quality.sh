#!/bin/bash
# Run all code quality checks

set -e

echo "=== Running Code Quality Checks ==="
echo

echo "1. Checking code formatting with black..."
uv run black --check backend/ main.py
echo "   Formatting check passed!"
echo

echo "2. Running tests with pytest..."
uv run pytest backend/tests/ -v
echo "   Tests passed!"
echo

echo "=== All quality checks passed! ==="
