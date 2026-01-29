#!/bin/bash
# Clean Python cache files

echo "Cleaning Python cache files..."
find /home/xingao/code/cosmos-dataset-search/src -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find /home/xingao/code/cosmos-dataset-search/src -type f -name "*.pyc" -delete 2>/dev/null
echo "✓ Cache cleaned"
