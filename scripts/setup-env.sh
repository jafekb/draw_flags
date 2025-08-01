#!/bin/bash

# Setup script for different environments
# Usage: ./scripts/setup-env.sh [dev|test|deploy]

set -e

ENV=${1:-dev}

echo "Setting up $ENV environment..."

# Try to pull LFS files (many cloud platforms have git-lfs pre-installed)
echo "Pulling Git LFS files..."
git lfs pull || echo "Warning: Git LFS pull failed, continuing anyway..."

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