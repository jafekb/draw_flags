# Deployment Guide

This project uses uv to manage dependencies with separate environments for development and deployment.

## Environment Setup

### Development Environment (includes dev tools)
```bash
# Install with development dependencies (ruff, black, mypy, torch, sentence-transformers, etc.)
uv sync --extra dev
```

### Test Environment
```bash
# Install with test dependencies (pytest, etc.)
uv sync --extra test
```

### Production Deployment (minimal)
```bash
# Install only production dependencies
uv sync --no-dev
```

## Quick Setup Scripts

Use the provided scripts for easy environment setup:

```bash
# Development environment
./scripts/setup-env.sh dev

# Test environment  
./scripts/setup-env.sh test

# Production deployment
./scripts/setup-env.sh deploy
```

## Production Deployment

For production deployment, use the minimal environment:

```bash
# Set up production environment
uv sync --no-dev

# Run the server
uv run python main.py
```

## Dependencies

- **Production**: Core dependencies needed to run the application (67 packages)
- **Development**: Production + linting, formatting, and development tools (106 packages)
- **Test**: Production + testing framework and utilities

## Size Comparison

- **Production**: 67 packages (minimal deployment)
- **Development**: 106 packages (includes torch, sentence-transformers, dev tools)
- **Reduction**: 39 fewer packages in production (37% smaller!)

## Benefits

- **Much smaller deployment size**: Production environment excludes torch, sentence-transformers, and dev tools
- **Faster deployment**: 39 fewer packages to install
- **Better security**: Fewer packages in production reduces attack surface
- **Flexibility**: Easy to switch between environments
- **ONNX optimization**: Uses ONNX models instead of PyTorch for inference 