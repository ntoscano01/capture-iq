#!/usr/bin/env bash
# ============================================================
# CaptureIQ — macOS Apple Silicon (M1/M2/M3/M4) Build Script
# Run from the sbir-pipeline/ directory:
#   bash build_mac_arm64.sh
#
# Output: dist/CaptureIQ.app
#         dist/CaptureIQ-macOS-arm64.zip  (ready to attach to GitHub Release)
# ============================================================

set -euo pipefail

VERSION="${1:-1.0.0}"
OUTPUT_ZIP="CaptureIQ-macOS-arm64-${VERSION}.zip"

echo "=================================================="
echo "  CaptureIQ — macOS Apple Silicon Build v${VERSION}"
echo "=================================================="

# ── Verify we're on Apple Silicon ──────────────────────────
ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
  echo "❌  This script must run on Apple Silicon (arm64). Detected: $ARCH"
  exit 1
fi

# ── Ensure PyInstaller ─────────────────────────────────────
if ! python3 -m PyInstaller --version &>/dev/null; then
  echo "[BUILD] Installing PyInstaller..."
  pip3 install pyinstaller --break-system-packages 2>/dev/null || pip3 install pyinstaller
fi

# ── Install requirements ───────────────────────────────────
echo "[BUILD] Installing requirements..."
pip3 install -r requirements.txt --break-system-packages 2>/dev/null \
  || pip3 install -r requirements.txt

# ── Clean previous build ───────────────────────────────────
echo "[BUILD] Cleaning previous build artifacts..."
rm -rf build/ dist/

# ── Run PyInstaller ────────────────────────────────────────
echo "[BUILD] Running PyInstaller (arm64)..."
python3 -m PyInstaller CaptureIQ_mac_arm64.spec --noconfirm

# ── Package as zip ─────────────────────────────────────────
if [ -d "dist/CaptureIQ.app" ]; then
  echo "[BUILD] Creating zip archive..."
  cd dist
  zip -r "../${OUTPUT_ZIP}" CaptureIQ.app
  cd ..

  echo ""
  echo "=================================================="
  echo "  ✅  Build successful!"
  echo "  App : $(pwd)/dist/CaptureIQ.app"
  echo "  Zip : $(pwd)/${OUTPUT_ZIP}"
  echo ""
  echo "  To distribute:"
  echo "  1. Share ${OUTPUT_ZIP}"
  echo "  2. Recipients unzip → move CaptureIQ.app to /Applications"
  echo "  3. First launch: right-click → Open (bypasses Gatekeeper)"
  echo "=================================================="
else
  echo "❌  Build failed — check output above."
  exit 1
fi
