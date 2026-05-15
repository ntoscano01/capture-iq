#!/usr/bin/env bash
# SBIR Pipeline — Startup Script
# Run this from the sbir-pipeline/ directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║      SBIR Pipeline — Local App       ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install Python 3.10+ from https://python.org"
  exit 1
fi

PYTHON=$(command -v python3)
echo "Python: $($PYTHON --version)"

# Install dependencies if needed
if ! $PYTHON -c "import flask" 2>/dev/null; then
  echo "Installing dependencies…"
  $PYTHON -m pip install -r requirements.txt --quiet
fi

echo "Starting server on http://127.0.0.1:5000"
echo "Press Ctrl+C to stop."
echo ""

$PYTHON app.py
