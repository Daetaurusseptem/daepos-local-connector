# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec para DaePoint Local Connector v2.0"""

a = Analysis(
    ['main_gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('api', 'api'),
        ('hardware', 'hardware'),
        ('config', 'config'),
    ],
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'pydantic',
        'serial',
        'usb',
        'escpos',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DaePointConnector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed mode (GUI)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=None,  # Use version_info from a separate file if needed
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DaePointConnector',
)
