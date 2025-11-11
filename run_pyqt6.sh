#!/bin/bash
# Basler PyQt6 桌面應用一鍵啟動腳本

set -e  # 遇到錯誤立即退出

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🏭 啟動 Basler 工業視覺系統 (PyQt6 桌面版)..."
echo ""

# 進入專案目錄
cd "$(dirname "$0")" || exit 1

# 檢查 Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python 未安裝${NC}"
    exit 1
fi

# 優先使用 python3，否則使用 python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

# 檢查 Python 版本
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "🐍 Python 版本: $PYTHON_VERSION"

# 檢查虛擬環境
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo -e "${GREEN}✅ 虛擬環境: $(basename "$VIRTUAL_ENV")${NC}"
elif [[ -n "$CONDA_DEFAULT_ENV" ]]; then
    echo -e "${GREEN}✅ Conda 環境: $CONDA_DEFAULT_ENV${NC}"
else
    echo -e "${YELLOW}⚠️  未在虛擬環境中運行${NC}"
    echo "   建議使用: conda activate RPi_4_camera_py312"
fi

echo ""

# 快速檢查關鍵依賴
echo "📦 檢查依賴..."
missing_deps=()

if ! $PYTHON_CMD -c "import PyQt6" 2>/dev/null; then
    missing_deps+=("PyQt6")
fi

if ! $PYTHON_CMD -c "import cv2" 2>/dev/null; then
    missing_deps+=("opencv-python")
fi

if ! $PYTHON_CMD -c "import numpy" 2>/dev/null; then
    missing_deps+=("numpy")
fi

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  缺少依賴: ${missing_deps[*]}${NC}"
    echo "   正在安裝..."

    # 優先使用 conda（如果在 conda 環境中）
    if [[ -n "$CONDA_DEFAULT_ENV" ]]; then
        # 嘗試使用 conda 完整路徑來避免 __conda_exe 問題
        CONDA_PATH=$(which conda 2>/dev/null || echo "/Users/crmado/anaconda3/bin/conda")

        if [[ -x "$CONDA_PATH" ]]; then
            echo "   使用 conda 安裝依賴..."
            "$CONDA_PATH" install -y -c conda-forge \
                pyqt=6.6 \
                opencv \
                numpy \
                pillow \
                psutil \
                pyyaml \
                pyinstaller \
                requests \
                paramiko 2>/dev/null

            # 如果 conda 失敗，回退到 pip
            if [ $? -ne 0 ]; then
                echo -e "${YELLOW}   ⚠️  conda 安裝失敗，回退到 pip...${NC}"
                pip install -r requirements.txt
            else
                # pypylon 需要用 pip 安裝
                pip install "pypylon>=4.2.0"
            fi
        else
            echo "   conda 不可用，使用 pip 安裝依賴..."
            pip install -r requirements.txt
        fi
    else
        echo "   使用 pip 安裝依賴..."
        pip install -r requirements.txt
    fi
    echo ""
fi

# 顯示版本信息
if [ -f "basler_pyqt6/version.py" ]; then
    VERSION=$($PYTHON_CMD -c "import sys; sys.path.insert(0, 'basler_pyqt6'); from version import __version__; print(__version__)")
    echo -e "${GREEN}✅ 應用版本: $VERSION${NC}"
fi

echo ""

# 檢查是否啟用 DEBUG_MODE
if [[ "$DEBUG_MODE" == "true" || "$DEBUG_MODE" == "1" || "$DEBUG_MODE" == "yes" ]]; then
    echo -e "${YELLOW}🛠️  開發模式已啟用 (DEBUG_MODE=true)${NC}"
else
    echo "🚀 生產模式 (使用 DEBUG_MODE=true ./run_pyqt6.sh 啟用開發模式)"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 啟動應用
$PYTHON_CMD basler_pyqt6/main_v2.py

# 應用退出後
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👋 應用已關閉"
