#!/usr/bin/env bash
set -euo pipefail

VENV_DIR=".venv"

echo ""
echo "=============================="
echo "  ACORN Course Checker Setup"
echo "=============================="
echo ""

# Locate a usable Python 3.8+
PYTHON=""
for candidate in python3 python3.12 python3.11 python3.10 python3.9 python3.8; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c 'import sys; print(sys.version_info >= (3, 8))')
        if [[ "$version" == "True" ]]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    echo "Error: Python 3.8 or newer is required but was not found."
    echo "Install it from https://www.python.org/downloads/ and re-run this script."
    exit 1
fi

echo "Using Python: $($PYTHON --version)"

# Create virtual environment
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment in $VENV_DIR/ ..."
    "$PYTHON" -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists — skipping creation."
fi

# Activate
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Install Playwright's Chromium browser
echo "Installing Playwright Chromium (this may take a minute)..."
python -m playwright install chromium

echo ""
echo "Setup complete!"
echo ""
echo "To start the checker, run:"
echo "  python3 run.py"
echo ""
echo "(run.py automatically uses the .venv interpreter, so no manual"
echo " source .venv/bin/activate is required.)"
echo ""
