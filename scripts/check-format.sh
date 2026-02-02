#!/bin/bash
# Check if Python files are properly formatted (without modifying them)

set -e

echo "Checking Python file formatting with black..."
uv run black --check backend/ main.py

echo "All files are properly formatted!"
