# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件
用於將 Basler PyQt6 應用打包成獨立可執行文件
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 添加專案路徑到 Python 路徑
sys.path.insert(0, os.path.abspath('.'))

# 從 version.py 導入版本信息
from basler_pyqt6.version import __version__, APP_NAME, APP_AUTHOR

VERSION = __version__
AUTHOR = APP_AUTHOR

# 路徑配置
block_cipher = None
basler_path = os.path.abspath('basler_pyqt6')

# 收集所有子模組
hidden_imports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'cv2',
    'numpy',
    'pypylon',
    'psutil',
    'yaml',
]

# 數據文件（如果有配置文件、圖標等）
datas = [
    # 可以添加圖標、配置文件等
    # ('resources/icon.ico', 'resources'),
    # ('config/*.yaml', 'config'),
]

# 分析階段
a = Analysis(
    ['basler_pyqt6/main_v2.py'],  # 主入口文件
    pathex=[basler_path],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',  # 排除不需要的大型庫
        'pandas',
        'scipy',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PYZ 歸檔
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# EXE 配置
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BaslerVisionSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 使用 UPX 壓縮
    console=False,  # False = 不顯示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加圖標路徑: 'resources/icon.ico'
)

# COLLECT 收集所有文件（目錄模式）
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BaslerVisionSystem',
)

# 如果要打包成單文件，使用以下配置替代 COLLECT：
# exe = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     [],
#     name='BaslerVisionSystem',
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     runtime_tmpdir=None,
#     console=False,
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlements_file=None,
#     icon=None,
# )
