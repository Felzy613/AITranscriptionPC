# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for AI Transcription PC
# This compiles the Python application into a standalone Windows executable

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(Path(__file__).resolve().parent)],
    binaries=[
        ('venv/Lib/site-packages/_sounddevice_data/portaudio-binaries/libportaudio64bit.dll', '_sounddevice_data/portaudio-binaries'),
        ('venv/Lib/site-packages/_sounddevice_data/portaudio-binaries/libportaudio64bit-asio.dll', '_sounddevice_data/portaudio-binaries'),
        ('venv/Lib/site-packages/_soundfile_data/libsndfile_x64.dll', '_soundfile_data'),
    ],
    datas=[
        ('assets', 'assets'),
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'keyboard',
        'numpy',
        'sounddevice',
        'soundfile',
        'openai',
        'pynput',
        'pyperclip',
        'websockets',
        'dotenv',
        'cryptography',
        'cryptography.fernet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
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
    name='AI Transcription PC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
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
    name='AITranscriptionPC',
)
