#!/bin/bash

# Define the virtual environment directory
VENV_DIR="photolyse"

# Deactivate the current virtual environment if active
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo "Deactivating current virtual environment..."
    deactivate
fi

# Remove existing virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
    echo "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

# Create a new virtual environment
echo "Creating new virtual environment..."
python3 -m venv "$VENV_DIR"

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Install required packages
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
else
    echo "No requirements.txt found, skipping package installation."
fi

echo "Setup complete."

source "$VENV_DIR/bin/activate"