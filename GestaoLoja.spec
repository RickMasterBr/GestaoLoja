# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
# Coleta arquivos de dados necessários para o runtime do Flet
try:
    datas += collect_data_files('flet')
except Exception:
    pass

hiddenimports = [
    'reportlab.lib.pagesizes',
    'reportlab.lib.colors',
    'reportlab.lib.units',
    'reportlab.lib.styles',
    'reportlab.lib.enums',
    'reportlab.platypus',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
    'openpyxl.cell._writer',
]
try:
    hiddenimports += collect_submodules('flet')
except Exception:
    pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='GestaoLoja',
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
