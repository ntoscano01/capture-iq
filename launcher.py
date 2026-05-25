"""
CaptureIQ — Launcher
====================
Entry point for both development mode and the packaged PyInstaller executable.

When frozen (distributed as a .app or single-file binary):
  • BUNDLE_DIR  = sys._MEIPASS  (temp dir where PyInstaller extracts files)
  • DATA_DIR    = ~/CaptureIQ   (user-writable; holds the DB, uploads, credentials)

When running from source (python launcher.py or python app.py):
  • BUNDLE_DIR  = directory of this file
  • DATA_DIR    = same directory (classic dev behaviour)
"""

import os
import sys
import time
import threading
import webbrowser

# ── 1. Resolve paths ───────────────────────────────────────────────────────────

if getattr(sys, "frozen", False):
    # PyInstaller bundle — read-only extracted files live in _MEIPASS
    BUNDLE_DIR = sys._MEIPASS
    # User data goes in ~/CaptureIQ so it survives app updates
    DATA_DIR = os.path.join(os.path.expanduser("~"), "CaptureIQ")
else:
    # Source / development mode
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = BUNDLE_DIR

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "project_uploads"), exist_ok=True)

# Expose DATA_DIR to all submodules via environment variable
os.environ["CAPTUREIQ_DATA_DIR"] = DATA_DIR
# Required for Google OAuth2 over localhost HTTP
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

# Make sure bundle packages are importable
if BUNDLE_DIR not in sys.path:
    sys.path.insert(0, BUNDLE_DIR)

# Flask expects to find templates/ relative to cwd (or we pass template_folder).
# Changing cwd to BUNDLE_DIR is the simplest cross-platform fix.
os.chdir(BUNDLE_DIR)


# ── 2. Patch module-level paths BEFORE importing app ──────────────────────────

import database as db
db.DB_PATH = os.path.join(DATA_DIR, "captureiq.db")

# Patch google_drive paths so credentials & token live in DATA_DIR
try:
    import integrations.google_drive as gd
    gd.BASE_DIR    = DATA_DIR
    gd.TOKEN_PATH  = os.path.join(DATA_DIR, "gdrive_token.json")
    gd.CREDS_PATH  = os.path.join(DATA_DIR, "credentials.json")
except Exception:
    pass  # Drive integration optional


# ── 3. Import Flask app and patch upload folder ───────────────────────────────

import app as app_module
from app import app, start_scheduler

app_module.UPLOAD_FOLDER = os.path.join(DATA_DIR, "project_uploads")


# ── 4. Auto-open browser once Flask is ready ──────────────────────────────────

PORT = 5000
URL  = f"http://127.0.0.1:{PORT}"


def _wait_and_open():
    """Poll the server until it responds, then open the browser."""
    import urllib.request
    for _ in range(30):          # wait up to 15 s
        try:
            urllib.request.urlopen(URL, timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    webbrowser.open(URL)


threading.Thread(target=_wait_and_open, daemon=True).start()

# ── 4b. Start automated ingest job scheduler ─────────────────────────────────
db.init_db()
start_scheduler()


# ── 5. Run Flask (blocking) ───────────────────────────────────────────────────

print(f"[CaptureIQ] Data directory : {DATA_DIR}")
print(f"[CaptureIQ] Database       : {db.DB_PATH}")
print(f"[CaptureIQ] Starting server: {URL}")

app.run(host="127.0.0.1", port=PORT, debug=False, use_reloader=False)
