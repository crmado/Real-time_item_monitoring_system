#!/bin/bash
# Basler Vision System - Linux 快速啟動腳本
# 自動安裝依賴並運行應用程式

set -e  # 遇到錯誤立即退出

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Basler Vision System - Linux 快速啟動              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# 檢查系統架構
ARCH=$(uname -m)
echo -e "${BLUE}📊 檢測系統架構:${NC} $ARCH"

# 檢測發行版
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    echo -e "${BLUE}🐧 檢測Linux發行版:${NC} $PRETTY_NAME"
else
    echo -e "${RED}❌ 無法檢測 Linux 發行版${NC}"
    exit 1
fi

echo ""

# 檢查 Python
echo -e "${BLUE}🐍 檢查 Python 環境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未安裝 Python3${NC}"
    echo -e "${YELLOW}💡 請先安裝 Python 3.12+:${NC}"
    case $DISTRO in
        ubuntu|debian)
            echo "   sudo apt-get install -y python3 python3-pip python3-venv"
            ;;
        fedora|rhel|centos)
            echo "   sudo dnf install -y python3 python3-pip"
            ;;
        arch|manjaro)
            echo "   sudo pacman -S python python-pip"
            ;;
    esac
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python 版本: $PYTHON_VERSION${NC}"

# 檢查 pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  未安裝 pip，正在安裝...${NC}"
    case $DISTRO in
        ubuntu|debian)
            sudo apt-get update
            sudo apt-get install -y python3-pip
            ;;
        fedora|rhel|centos)
            sudo dnf install -y python3-pip
            ;;
        arch|manjaro)
            sudo pacman -S python-pip
            ;;
    esac
fi

echo ""

# 安裝系統依賴
echo -e "${BLUE}📦 安裝系統依賴...${NC}"
case $DISTRO in
    ubuntu|debian)
        echo -e "${YELLOW}正在更新套件列表...${NC}"
        sudo apt-get update -qq

        # 檢查並安裝缺失的依賴
        DEPS=(libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 libgl1-mesa-glx libglib2.0-0)
        MISSING_DEPS=()

        for dep in "${DEPS[@]}"; do
            if ! dpkg -l | grep -q "^ii  $dep"; then
                MISSING_DEPS+=($dep)
            fi
        done

        if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
            echo -e "${YELLOW}安裝缺失的依賴: ${MISSING_DEPS[@]}${NC}"
            sudo apt-get install -y "${MISSING_DEPS[@]}"
        else
            echo -e "${GREEN}✅ 所有系統依賴已安裝${NC}"
        fi
        ;;

    fedora|rhel|centos)
        echo -e "${YELLOW}安裝 Qt 依賴...${NC}"
        sudo dnf install -y xcb-util-wm xcb-util-image mesa-libGL glib2
        ;;

    arch|manjaro)
        echo -e "${YELLOW}安裝 Qt 依賴...${NC}"
        sudo pacman -S --noconfirm libxcb xcb-util-wm mesa glib2
        ;;

    *)
        echo -e "${YELLOW}⚠️  未識別的發行版，請手動安裝 Qt5/Qt6 依賴${NC}"
        ;;
esac

echo ""

# 安裝 Python 依賴
echo -e "${BLUE}🔧 安裝 Python 依賴...${NC}"
if [ -f "requirements.txt" ]; then
    echo -e "${YELLOW}這可能需要幾分鐘...${NC}"

    # 檢查是否有虛擬環境
    if [ -d "venv" ]; then
        echo -e "${YELLOW}檢測到虛擬環境，正在啟用...${NC}"
        source venv/bin/activate
    elif [ ! -z "$VIRTUAL_ENV" ]; then
        echo -e "${GREEN}✅ 已在虛擬環境中${NC}"
    else
        echo -e "${YELLOW}💡 建議創建虛擬環境（按 Ctrl+C 取消，或等待 5 秒繼續）${NC}"
        echo -e "${YELLOW}   創建虛擬環境請運行: python3 -m venv venv && source venv/bin/activate${NC}"
        sleep 5
    fi

    # 安裝依賴（靜默模式）
    pip3 install -q -r requirements.txt

    echo -e "${GREEN}✅ Python 依賴安裝完成${NC}"
else
    echo -e "${RED}❌ 找不到 requirements.txt${NC}"
    echo -e "${YELLOW}💡 請確保在專案根目錄運行此腳本${NC}"
    exit 1
fi

echo ""

# 啟動應用
echo -e "${BLUE}🚀 啟動應用程式...${NC}"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"

if [ -f "basler_pyqt6/main_v2.py" ]; then
    python3 basler_pyqt6/main_v2.py
else
    echo -e "${RED}❌ 找不到主程式: basler_pyqt6/main_v2.py${NC}"
    exit 1
fi
