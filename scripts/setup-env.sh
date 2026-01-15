#!/bin/bash

# Setup script for different environments
# Usage: ./scripts/setup-env.sh [dev|test|deploy]

set -e

ENV=${1:-dev}

echo "Setting up $ENV environment..."

# Try to pull only required LFS files (many cloud platforms have git-lfs pre-installed)
echo "Pulling required Git LFS files..."
git lfs pull --include "\
backend/models/clip-text-encoder.onnx,\
backend/data/comprehensive_flags_3/embeddings.hnsw.bin\
" || echo "Warning: Git LFS pull failed, continuing anyway..."

case $ENV in
    "dev")
        echo "Installing development dependencies..."
        uv sync --extra dev
        ;;
    "test")
        echo "Installing test dependencies..."
        uv sync --extra test
        ;;
    "deploy")
        echo "Installing deployment dependencies only..."
        uv sync --no-dev
        ;;
    *)
        echo "Usage: $0 [dev|test|deploy]"
        echo "  dev    - Install with development dependencies"
        echo "  test   - Install with test dependencies"
        echo "  deploy - Install production dependencies only"
        exit 1
        ;;
esac

echo "Environment setup complete!" 