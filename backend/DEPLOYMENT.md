# Deployment Guide

This project uses uv to manage dependencies with separate environments for development and deployment.

## Environment Setup

### Development Environment (includes dev tools)
```bash
# Install with development dependencies (ruff, black, mypy, etc.)
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
./deploy.sh

# Run the server
uv run python main.py
```

## Dependencies

- **Production**: Core dependencies needed to run the application
- **Development**: Production + linting, formatting, and development tools
- **Test**: Production + testing framework and utilities

## Benefits

- **Smaller deployment size**: Production environment excludes dev tools
- **Faster deployment**: Fewer dependencies to install
- **Security**: Fewer packages in production reduces attack surface
- **Flexibility**: Easy to switch between environments 