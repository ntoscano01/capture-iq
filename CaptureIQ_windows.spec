# -*- mode: python ; coding: utf-8 -*-
#
# CaptureIQ — PyInstaller spec file for WINDOWS
# Build with (on a Windows machine):
#   pyinstaller CaptureIQ_windows.spec
#
# Output: dist\CaptureIQ\CaptureIQ.exe  (folder distribution)
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
    ("templates",    "templates"),
]
datas += collect_data_files("lxml")
datas += collect_data_files("bs4")
datas += collect_data_files("certifi")

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
    console=False,          # no black terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="icon.ico",      # uncomment and add icon.ico for a custom icon
)

# Collect into a folder (easier to distribute than --onefile,
# which triggers antivirus false positives on Windows)
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
