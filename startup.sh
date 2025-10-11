#!/bin/bash

# Azure App Service startup script for FastAPI application
# This script ensures proper initialization of the application

echo "Starting AISight API..."

# Set environment variables
export PYTHONUNBUFFERED=1
export PYTHONPATH=/home/site/wwwroot:$PYTHONPATH

# Navigate to the application directory
cd /home/site/wwwroot

# Verify Python version
echo "Python version:"
python --version

# Install/upgrade pip to avoid compatibility issues
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Verify critical packages are installed
echo "Verifying critical packages..."
python -c "import fastapi; print(f'FastAPI version: {fastapi.__version__}')"
python -c "import pydantic; print(f'Pydantic version: {pydantic.__version__}')"
python -c "import uvicorn; print(f'Uvicorn version: {uvicorn.__version__}')"

# Start the application
echo "Starting uvicorn server..."
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
