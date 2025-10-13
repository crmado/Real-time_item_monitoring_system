#!/bin/bash
# 快速安裝所有依賴的腳本

set -e

echo "🔧 安裝 Basler PyQt6 應用依賴..."
echo ""

# 進入專案目錄
cd "$(dirname "$0")"

# 檢查是否在 conda 環境中
if [[ -n "$CONDA_DEFAULT_ENV" ]]; then
    echo "✅ 檢測到 Conda 環境: $CONDA_DEFAULT_ENV"
    echo ""

    # 方案 1: 使用 conda 完整路徑
    CONDA_BIN="/Users/crmado/anaconda3/bin/conda"

    if [[ -x "$CONDA_BIN" ]]; then
        echo "📦 使用 conda 安裝主要依賴..."
        "$CONDA_BIN" install -y -c conda-forge \
            pyqt=6.6 \
            opencv \
            numpy \
            pillow \
            psutil \
            pyyaml \
            pyinstaller \
            requests \
            paramiko

        echo ""
        echo "📦 使用 pip 安裝 pypylon (Basler 相機驅動)..."
        pip install "pypylon>=4.2.0"
    else
        echo "⚠️  找不到 conda，使用 pip 安裝所有依賴..."
        pip install -r requirements.txt
    fi
else
    echo "⚠️  未在 conda 環境中"
    echo "📦 使用 pip 安裝依賴..."
    pip install -r requirements.txt
fi

echo ""
echo "✅ 依賴安裝完成！"
echo ""
echo "驗證安裝："
python -c "import PyQt6; print('✅ PyQt6:', PyQt6.__version__)" 2>/dev/null || echo "❌ PyQt6 安裝失敗"
python -c "import cv2; print('✅ OpenCV:', cv2.__version__)" 2>/dev/null || echo "❌ OpenCV 安裝失敗"
python -c "import numpy; print('✅ NumPy:', numpy.__version__)" 2>/dev/null || echo "❌ NumPy 安裝失敗"

echo ""
echo "🚀 現在可以運行: ./run_pyqt6.sh"
