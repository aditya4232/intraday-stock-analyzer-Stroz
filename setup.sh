#!/usr/bin/env bash
# Setup script for HuggingFace Spaces deployment
# This script is automatically executed on Space startup.

set -e

echo "Installing Python dependencies..."
pip install --no-cache-dir -r intraday-scanner/requirements.txt

echo "Setup complete!"
