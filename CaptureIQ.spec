# -*- mode: python ; coding: utf-8 -*-
#
# CaptureIQ — PyInstaller spec file
# Build with:  pyinstaller CaptureIQ.spec
#
# Output: dist/CaptureIQ.app  (macOS)  or  dist/CaptureIQ  (Windows/Linux)
#

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# Collect all hidden imports for Flask, Jinja2, Werkzeug, and Google libs
hidden_imports = (
    collect_submodules("flask")
    + collect_submodules("jinja2")
    + collect_submodules("werkzeug")
    + collect_submodules("click")
    + collect_submodules("itsdangerous")
    + collect_submodules("markupsafe")
    + collect_submodules("bs4")
    + collect_submodules("lxml")
    + collect_submodules("requests")
    + collect_submodules("apscheduler")
    + collect_submodules("reportlab")
    + collect_submodules("docx")
    + [
        # Google auth (optional — Drive integration)
        "google.auth",
        "google.auth.transport.requests",
        "google.oauth2.credentials",
        "google_auth_oauthlib",
        "google_auth_oauthlib.flow",
        "googleapiclient",
        "googleapiclient.discovery",
        "googleapiclient.http",
        # stdlib extras sometimes missed
        "sqlite3",
        "email.mime.multipart",
        "email.mime.text",
        # App packages
        "database",
        "ingestors",
        "ingestors.sbir_gov",
        "ingestors.sbir_gov_topics",
        "ingestors.dod_sbirsttr",
        "ingestors.navy_sbir",
        "integrations",
        "integrations.google_drive",
    ]
)

# Data files: templates + any static assets
datas = [
    ("templates",    "templates"),    # Jinja2 templates
]

# Include lxml / bs4 data files if any
datas += collect_data_files("lxml")
datas += collect_data_files("bs4")
datas += collect_data_files("certifi")   # SSL certs for requests

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PIL",
        "cv2",
        "test",
        "_pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── macOS .app bundle ──────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CaptureIQ",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # no terminal window on macOS
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CaptureIQ",
)

app = BUNDLE(
    coll,
    name="CaptureIQ.app",
    icon=None,              # set to "icon.icns" if you add one later
    bundle_identifier="com.captureiq.app",
    info_plist={
        "NSHighResolutionCapable": True,
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "LSBackgroundOnly": False,
        "NSAppTransportSecurity": {
            "NSAllowsLocalNetworking": True,
        },
    },
)
