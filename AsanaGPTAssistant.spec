# AsanaGptAssistant.spec
# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

project_root = Path(__file__).parent.resolve()

tkcalendar_datas, tkcalendar_binaries, tkcalendar_hiddenimports = collect_all("tkcalendar")
docx_datas = collect_data_files("docx")

datas = tkcalendar_datas + docx_datas + [
    (str(project_root / "config.json"), "."),
]

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=tkcalendar_binaries,
    datas=datas,
    hiddenimports=tkcalendar_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="AsanaGptAssistant",
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
    icon=None,
)
