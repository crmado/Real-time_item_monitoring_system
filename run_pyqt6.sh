#!/bin/bash

# Basler PyQt6 桌面應用啟動腳本

echo "🏭 啟動 Basler 工業視覺系統 (PyQt6 桌面版)..."

# 檢查 Python 環境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 未安裝"
    exit 1
fi

# 檢查是否在虛擬環境中
if [[ -z "$VIRTUAL_ENV" ]] && [[ -z "$CONDA_DEFAULT_ENV" ]]; then
    echo "⚠️  建議在虛擬環境中運行"
    echo "   conda activate RPi_4_camera"
    echo "   或"
    echo "   source venv/bin/activate"
    read -p "是否繼續? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 進入項目目錄
cd "$(dirname "$0")" || exit 1

# 檢查依賴
echo "📦 檢查依賴..."
if ! python3 -c "import PyQt6" 2>/dev/null; then
    echo "⚠️  缺少 PyQt6，正在安裝..."
    pip install -r basler_pyqt6/requirements.txt
fi

# 啟動應用
echo "✅ 啟動 PyQt6 桌面應用（專業版 V2）..."
echo ""

python3 basler_pyqt6/main_v2.py
