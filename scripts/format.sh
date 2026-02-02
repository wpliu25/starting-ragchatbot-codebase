#!/bin/bash
# Format all Python files with black

set -e

echo "Formatting Python files with black..."
uv run black backend/ main.py

echo "Done! All Python files have been formatted."
