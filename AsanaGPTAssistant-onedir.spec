# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for an onedir build of AsanaGPTAssistant.

This provides an alternative packaging approach for environments where the
single-file executable struggles to load Tk themed dialogs.  The onedir layout
keeps the application files unpacked beside the launcher so Tcl/Tk assets can be
resolved directly from disk.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

block_cipher = None

config_path = Path("config.json")
if not config_path.exists():
    raise FileNotFoundError(
        "config.json is required for building. Copy config.example.json and fill in your credentials before running PyInstaller."
    )

history_path = Path("history.db")
if not history_path.exists():
    history_path.touch()

collect_data = collect_all("tkcalendar")
datas = [
    (str(config_path), "."),
    (str(history_path), "."),
    *collect_data[0],
]
binaries = [*collect_data[1]]
hiddenimports = [*collect_data[2]]


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AsanaGPTAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
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
    name="AsanaGPTAssistant",
)