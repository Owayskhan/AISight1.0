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
python -m pip install --upgrade pip --quiet

# Install dependencies from requirements.txt
echo "Installing requirements from requirements.txt..."
pip install -r requirements.txt --quiet

# Fix typing_extensions conflict (Azure has old version in /agents/python/)
echo "Fixing typing_extensions..."
pip install --force-reinstall --no-cache-dir typing-extensions>=4.8.0 pydantic-core>=2.14.0 --quiet

# Verify critical packages are installed
echo "Verifying critical packages..."
python -c "import fastapi; print(f'FastAPI version: {fastapi.__version__}')" || echo "ERROR: FastAPI not installed"
python -c "import pydantic; print(f'Pydantic version: {pydantic.__version__}')" || echo "ERROR: Pydantic not installed"
python -c "import uvicorn; print(f'Uvicorn version: {uvicorn.__version__}')" || echo "ERROR: Uvicorn not installed"
python -c "from typing_extensions import Sentinel; print('typing_extensions: OK')" || echo "ERROR: typing_extensions missing Sentinel"

# Start the application
echo "Starting uvicorn server on port 8000..."
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
