#!/bin/bash

# Azure App Service startup script for FastAPI application
# This script ensures proper initialization of the application

echo "Starting AISight API..."

# Set environment variables
export PYTHONUNBUFFERED=1
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH
export PLAYWRIGHT_BROWSERS_PATH=/home/site/wwwroot/.playwright

# Navigate to the application directory
cd /home/site/wwwroot

# Verify Python version
echo "Python version:"
python --version

# Install/upgrade pip to avoid compatibility issues
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install Playwright browsers if Playwright is installed
echo "Checking for Playwright..."
if python -c "import playwright" 2>/dev/null; then
    echo "Playwright detected, installing browsers..."
    python -m playwright install --with-deps chromium || echo "Warning: Playwright browser installation failed (may need system dependencies)"
else
    echo "Playwright not installed, skipping browser setup"
fi

# Verify critical packages are installed
echo "Verifying critical packages..."
python -c "import fastapi; print(f'FastAPI version: {fastapi.__version__}')"
python -c "import pydantic; print(f'Pydantic version: {pydantic.__version__}')"
python -c "import uvicorn; print(f'Uvicorn version: {uvicorn.__version__}')"

# Start the application
echo "Starting uvicorn server..."
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
