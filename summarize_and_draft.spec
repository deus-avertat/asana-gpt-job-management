# summarize_and_draft.spec

# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Include data from tkcalendar
tkcalendar_data = collect_data_files('tkcalendar')

a = Analysis(
    ['summarize_and_draft.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        ('config.json', '.'),  # Include config.json
    ] + tkcalendar_data,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='summarize_and_draft',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False  # Set to True if you want a terminal window for logs
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='summarize_and_draft'
)
