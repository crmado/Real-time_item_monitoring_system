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
    # PyQt6
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtMultimedia',
    'PyQt6.sip',

    # NumPy 相關（修復 NumPy 2.x 打包問題）
    'numpy',
    'numpy._core',
    'numpy._core._exceptions',
    'numpy._core._multiarray_umath',
    'numpy._core._dtype_ctypes',
    'numpy._core._methods',  # NumPy 2.x 使用 _core 而非 core
    'numpy.lib.format',

    # OpenCV
    'cv2',

    # Basler pypylon
    'pypylon',

    # 其他依賴
    'psutil',
    'yaml',

    # 配置和更新系統
    'dataclasses',
    'json',
    'requests',
]

# 數據文件（配置文件、測試資料等）
datas = [
    # 配置檔案（必要）
    ('basler_pyqt6/config/detection_params.json', 'config'),

    # 資源文件（SVG 圖示、零件圖片目錄結構）
    ('basler_pyqt6/resources/icons', 'resources/icons'),
    ('basler_pyqt6/resources/parts', 'resources/parts'),

    # 測試資料目錄（用於無硬體測試）
    # ('basler_pyqt6/testData', 'testData'),

    # 可以添加圖標等資源
    # ('resources/icon.ico', 'resources'),
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
    console=True,  # True = 顯示控制台窗口（調試用，正式版改為 False）
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
