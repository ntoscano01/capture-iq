# CaptureIQ — Build & Distribution Guide

## Overview

CaptureIQ is packaged using **PyInstaller**, which bundles the Flask app, Python
runtime, and all dependencies into a standalone executable that requires no
Python installation on the recipient's machine.

> **Key rule:** PyInstaller must be run on the same OS you are targeting.
> Build on a Mac → get a `.app`. Build on Windows → get a `.exe`.
> You cannot cross-compile.

---

## Building on macOS

### Prerequisites
- Python 3.10+ with pip (Anaconda works)
- All `requirements.txt` packages installed

```bash
cd sbir-pipeline
bash build_mac.sh
```

Output: `dist/CaptureIQ.app`

**To distribute:**
```bash
cd dist
zip -r CaptureIQ.zip CaptureIQ.app
```
Share the zip. Recipients:
1. Unzip and drag `CaptureIQ.app` to `/Applications`
2. First launch: **right-click → Open** (bypasses macOS Gatekeeper on unsigned apps)
3. A browser tab opens at `http://127.0.0.1:5000` automatically

---

## Building on Windows

### Prerequisites
- Python 3.10+ with pip installed and on PATH
- Run from the `sbir-pipeline\` folder in Command Prompt or PowerShell

```bat
build_windows.bat
```

Output: `dist\CaptureIQ\` folder containing `CaptureIQ.exe`

**To distribute:**
Zip the entire `dist\CaptureIQ\` folder (not just the .exe — it needs the files alongside it).
Recipients unzip and double-click `CaptureIQ.exe`. No install required.

> **Windows Defender / SmartScreen warning:** On first run, Windows may show a
> "Windows protected your PC" dialog. Click **"More info" → "Run anyway"**.
> This is expected for unsigned apps. It will not repeat after the first run.

---

## Where User Data Is Stored

All user data lives in **`~/CaptureIQ/`** on each machine:

| Platform | Full path |
|---|---|
| macOS | `/Users/yourname/CaptureIQ/` |
| Windows | `C:\Users\yourname\CaptureIQ\` |

| File/Folder | Contents |
|---|---|
| `captureiq.db` | SQLite database (all topics, projects, etc.) |
| `project_uploads/` | Uploaded proposal files |
| `credentials.json` | Google Drive OAuth credentials (optional, user-provided) |
| `gdrive_token.json` | Google Drive auth token (created automatically on connect) |

> **Backup tip:** Zip the `~/CaptureIQ/` folder to back up everything.
> **Upgrading:** Replace the app and user data is untouched.

---

## Google Drive Integration (Optional)

Each user who wants Drive integration needs a `credentials.json`:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable the Google Drive API
3. APIs & Services → Credentials → Create OAuth 2.0 Client ID (Web application)
4. Add `http://127.0.0.1:5000/settings/gdrive/callback` as an Authorised redirect URI
5. Download JSON → rename to `credentials.json`
6. Copy `credentials.json` into `~/CaptureIQ/`
7. Open CaptureIQ → Settings → Google Drive → Connect

You can share the same `credentials.json` across your team if you use a shared
Google Cloud project, as long as each user completes the OAuth flow themselves.

---

## Running from Source (No Build Required)

```bash
cd sbir-pipeline
python launcher.py
```

In development mode, data is stored in the script directory rather than `~/CaptureIQ/`.

---

## Troubleshooting

### macOS: "App is damaged and can't be opened"
Run in Terminal:
```bash
xattr -cr /Applications/CaptureIQ.app
```

### Windows: App closes immediately on launch
The app likely crashed before the browser opened. Run from Command Prompt to see errors:
```bat
cd "C:\path\to\CaptureIQ"
CaptureIQ.exe
```

### Port 5000 already in use (all platforms)
Edit `launcher.py`, change `PORT = 5000` to another port (e.g. `5100`), then rebuild.

### Build fails with missing module errors
Ensure packages are installed in the same Python environment that PyInstaller uses:
```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller CaptureIQ.spec --noconfirm   # (or CaptureIQ_windows.spec on Windows)
```
