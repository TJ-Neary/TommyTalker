# -*- mode: python ; coding: utf-8 -*-
"""
TommyTalker PyInstaller Spec File
Bundles the application into a standalone macOS .app
"""

import sys
from pathlib import Path

block_cipher = None

# Get the project root
project_root = Path(SPECPATH)

# Main script (now in src/tommy_talker/)
main_script = str(project_root / 'src' / 'tommy_talker' / 'main.py')

# Data files to include
datas = [
    # Include the entire package
    (str(project_root / 'src' / 'tommy_talker'), 'tommy_talker'),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    # TommyTalker package
    'tommy_talker',
    'tommy_talker.engine',
    'tommy_talker.engine.audio_capture',
    'tommy_talker.engine.transcriber',
    'tommy_talker.engine.llm_client',
    'tommy_talker.engine.diarizer',
    'tommy_talker.engine.rag_store',
    'tommy_talker.engine.modes',
    'tommy_talker.engine.session_db',
    'tommy_talker.gui',
    'tommy_talker.gui.menu_bar',
    'tommy_talker.gui.dashboard',
    'tommy_talker.gui.hud',
    'tommy_talker.gui.setup_guide',
    'tommy_talker.gui.onboarding',
    'tommy_talker.gui.hotkey_selector',
    'tommy_talker.utils',
    'tommy_talker.utils.config',
    'tommy_talker.utils.hardware_detect',
    'tommy_talker.utils.hotkeys',
    'tommy_talker.utils.permissions',
    'tommy_talker.utils.typing',
    'tommy_talker.utils.secure_credentials',
    'tommy_talker.utils.audio_feedback',
    'tommy_talker.utils.logger',
    'tommy_talker.app_controller',

    # PyQt6
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',

    # pyobjc frameworks
    'objc',
    'AppKit',
    'Foundation',
    'Cocoa',
    'Quartz',
    'AVFoundation',

    # Audio
    'sounddevice',
    'soundfile',
    'numpy',

    # AI/ML
    'mlx',
    'mlx_whisper',
    'ollama',
    'chromadb',
    'pyannote.audio',

    # Utils
    'psutil',
    'pyautogui',

    # SQLite
    'sqlite3',
]

# Exclude packages that are too large or not needed
excludes = [
    'tkinter',
    'matplotlib',
    'scipy',
    'pandas',
    'jupyter',
    'notebook',
    'IPython',
]

a = Analysis(
    [main_script],
    pathex=[str(project_root), str(project_root / 'src')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='TommyTalker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=True,  # For macOS drag-and-drop
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
    name='TommyTalker',
)

app = BUNDLE(
    coll,
    name='TommyTalker.app',
    icon=None,  # Add icon path here: 'resources/icon.icns'
    bundle_identifier='com.tommytalker.app',
    info_plist={
        'CFBundleName': 'TommyTalker',
        'CFBundleDisplayName': 'TommyTalker',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleExecutable': 'TommyTalker',
        'CFBundlePackageType': 'APPL',
        'LSMinimumSystemVersion': '12.0',
        'LSUIElement': True,  # Hide from dock (menu bar app)
        'NSHighResolutionCapable': True,
        'NSMicrophoneUsageDescription': 'TommyTalker needs microphone access for voice transcription.',
        'NSAppleEventsUsageDescription': 'TommyTalker needs accessibility access for typing at cursor and global hotkeys.',
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
    },
)
