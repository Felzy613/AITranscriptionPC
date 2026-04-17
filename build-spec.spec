# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for AI Transcription PC
# This compiles the Python application into a standalone Windows executable.
from pathlib import Path

block_cipher = None
project_root = Path.cwd().resolve()
site_packages = Path("venv/Lib/site-packages")


def _existing_binaries() -> list[tuple[str, str]]:
    binaries: list[tuple[str, str]] = []
    for path in site_packages.glob("_sounddevice_data/portaudio-binaries/libportaudio*bit*.dll"):
        binaries.append((str(path), "_sounddevice_data/portaudio-binaries"))
    for path in site_packages.glob("_soundfile_data/libsndfile_*.dll"):
        binaries.append((str(path), "_soundfile_data"))
    return binaries

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=_existing_binaries(),
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
        'PyQt6.QtSvg',
        'dotenv',
    ],
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
