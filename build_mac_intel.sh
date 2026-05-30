#!/usr/bin/env bash
# ============================================================
# CaptureIQ — macOS Intel (x86_64) Local Build Script
# Run from the sbir-pipeline/ directory:
#   bash build_mac_intel.sh
#
# Output: dist/CaptureIQ.app
#         ~/Desktop/CaptureIQ-macOS-intel-<version>.zip
#
# NOTE: Must be run on an Intel Mac, OR on Apple Silicon with
# an x86_64 Python (via Rosetta):
#   arch -x86_64 /usr/local/bin/python3 -m PyInstaller ...
# ============================================================

set -euo pipefail

VERSION="${1:-1.0.0}"
OUTPUT_ZIP="${HOME}/Desktop/CaptureIQ-macOS-intel-${VERSION}.zip"

echo "=================================================="
echo "  CaptureIQ — macOS Intel Build v${VERSION}"
echo "=================================================="

# ── Verify architecture ────────────────────────────────────
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
  echo "⚠️  Detected Apple Silicon. Building x86_64 via Rosetta..."
  echo "   Ensure you have an Intel Python installed at /usr/local/bin/python3"
  PYTHON="arch -x86_64 /usr/local/bin/python3"
else
  PYTHON="python3"
fi

# ── Ensure PyInstaller ─────────────────────────────────────
if ! $PYTHON -m PyInstaller --version &>/dev/null; then
  echo "[BUILD] Installing PyInstaller..."
  $PYTHON -m pip install pyinstaller --break-system-packages 2>/dev/null \
    || $PYTHON -m pip install pyinstaller
fi

# ── Install requirements ───────────────────────────────────
echo "[BUILD] Installing requirements..."
$PYTHON -m pip install -r requirements.txt --break-system-packages 2>/dev/null \
  || $PYTHON -m pip install -r requirements.txt

# ── Clean previous build ───────────────────────────────────
echo "[BUILD] Cleaning previous build artifacts..."
rm -rf build/ dist/

# ── Run PyInstaller ────────────────────────────────────────
echo "[BUILD] Running PyInstaller (x86_64)..."
$PYTHON -m PyInstaller CaptureIQ_mac_intel.spec --noconfirm

# ── Package as zip to Desktop ─────────────────────────────
if [ -d "dist/CaptureIQ.app" ]; then
  echo "[BUILD] Creating zip on Desktop..."
  cd dist
  zip -r "${OUTPUT_ZIP}" CaptureIQ.app
  cd ..

  echo ""
  echo "=================================================="
  echo "  ✅  Build successful!"
  echo "  App : $(pwd)/dist/CaptureIQ.app"
  echo "  Zip : ${OUTPUT_ZIP}"
  echo ""
  echo "  To install locally:"
  echo "  1. Open ~/Desktop"
  echo "  2. Unzip CaptureIQ-macOS-intel-${VERSION}.zip"
  echo "  3. Move CaptureIQ.app to /Applications"
  echo "  4. First launch: right-click → Open (bypasses Gatekeeper)"
  echo "=================================================="
else
  echo "❌  Build failed — check output above."
  exit 1
fi
