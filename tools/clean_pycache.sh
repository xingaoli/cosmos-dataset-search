#!/bin/bash
# Clean Python cache files

# Load environment variables
if [ -f "$(dirname "$0")/../deploy/standalone/.env" ]; then
    export $(grep -v '^#' "$(dirname "$0")/../deploy/standalone/.env" | xargs)
fi

# Use PROJECT_ROOT from env or default to parent directory
PROJECT_ROOT=${PROJECT_ROOT:-$(dirname "$(dirname "$(realpath "$0")")")}

echo "Cleaning Python cache files in $PROJECT_ROOT/src..."
find "$PROJECT_ROOT/src" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find "$PROJECT_ROOT/src" -type f -name "*.pyc" -delete 2>/dev/null
echo "✓ Cache cleaned"
