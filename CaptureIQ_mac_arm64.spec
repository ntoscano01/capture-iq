# -*- mode: python ; coding: utf-8 -*-
#
# CaptureIQ — PyInstaller spec for macOS Apple Silicon (M1/M2/M3/M4)
# Build with:
#   pyinstaller CaptureIQ_mac_arm64.spec --noconfirm
#
# Must be run ON an Apple Silicon Mac.
# Output: dist/CaptureIQ.app
#

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

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
    + collect_submodules("flask_login")
    + collect_submodules("requests_oauthlib")
    + [
        "google.auth",
        "google.auth.transport.requests",
        "google.oauth2.credentials",
        "google_auth_oauthlib",
        "google_auth_oauthlib.flow",
        "googleapiclient",
        "googleapiclient.discovery",
        "googleapiclient.http",
        "sqlite3",
        "email.mime.multipart",
        "email.mime.text",
        "smtplib",
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

datas = [
    ("templates",       "templates"),
    ("static",          "static"),
]
datas += collect_data_files("lxml")
datas += collect_data_files("bs4")
datas += collect_data_files("certifi")
datas += collect_data_files("flask_login")

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
        "tkinter", "matplotlib", "numpy",
        "pandas", "scipy", "PIL", "cv2",
        "test", "_pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    target_arch="arm64",   # Apple Silicon
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    console=False,
    disable_windowed_traceback=False,
    target_arch="arm64",
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
    icon=None,
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
