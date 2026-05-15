#!/usr/bin/env bash
# ============================================================
# CaptureIQ — macOS Build Script
# Run this from the sbir-pipeline/ directory:
#   cd sbir-pipeline
#   bash build_mac.sh
# ============================================================

set -euo pipefail

echo "=================================================="
echo "  CaptureIQ — macOS Build"
echo "=================================================="

# ── 1. Ensure PyInstaller is installed ─────────────────────
if ! python -m PyInstaller --version &>/dev/null; then
  echo "[BUILD] Installing PyInstaller..."
  pip install pyinstaller --break-system-packages 2>/dev/null || pip install pyinstaller
fi

# ── 2. Ensure all requirements are installed ───────────────
echo "[BUILD] Installing requirements..."
pip install -r requirements.txt --break-system-packages 2>/dev/null \
  || pip install -r requirements.txt

# ── 3. Clean previous build ────────────────────────────────
echo "[BUILD] Cleaning previous build artifacts..."
rm -rf build/ dist/

# ── 4. Run PyInstaller ─────────────────────────────────────
echo "[BUILD] Running PyInstaller..."
python -m PyInstaller CaptureIQ.spec --noconfirm

# ── 5. Report result ───────────────────────────────────────
if [ -d "dist/CaptureIQ.app" ]; then
  echo ""
  echo "=================================================="
  echo "  ✅  Build successful!"
  echo "  App: $(pwd)/dist/CaptureIQ.app"
  echo ""
  echo "  To distribute:"
  echo "  1. Zip the .app:  cd dist && zip -r CaptureIQ.zip CaptureIQ.app"
  echo "  2. Share CaptureIQ.zip with other users"
  echo "  3. Recipients unzip and move CaptureIQ.app to /Applications"
  echo "=================================================="
else
  echo ""
  echo "❌  Build failed — check output above for errors."
  exit 1
fi
