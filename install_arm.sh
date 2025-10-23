#!/bin/bash
# =============================================================================
# Basler Vision System - ARM 架構安裝腳本 (Rock 5B / Debian 12)
# =============================================================================
# 使用方法：
#   chmod +x install_arm.sh
#   ./install_arm.sh
# =============================================================================

set -e  # 遇到錯誤立即停止

echo "════════════════════════════════════════════════════════"
echo "  Basler Vision System - ARM 自動安裝"
echo "  目標系統: Rock 5B / Debian 12"
echo "════════════════════════════════════════════════════════"
echo ""

# -----------------------------------------------------------------------------
# 步驟 1: 檢查系統架構（必須是 ARM）
# -----------------------------------------------------------------------------
ARCH=$(uname -m)
echo "[1/5] 檢查系統架構: $ARCH"

if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" ]]; then
    echo "⚠️  警告: 不是 ARM 架構，但繼續安裝..."
fi
echo ""

# -----------------------------------------------------------------------------
# 步驟 2: 安裝系統依賴（Qt 圖形庫 + PyQt6）
#
# 重要：ARM 架構直接用系統的 PyQt6，避免編譯問題
# -----------------------------------------------------------------------------
echo "[2/5] 安裝系統依賴..."
sudo apt-get update -qq
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-pyqt6 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git

echo "✅ 系統依賴安裝完成"
echo ""

# -----------------------------------------------------------------------------
# 步驟 3: 創建 Python 虛擬環境（使用 --system-site-packages）
#
# 重要：必須加 --system-site-packages 才能使用系統的 PyQt6
# -----------------------------------------------------------------------------
echo "[3/5] 創建 Python 虛擬環境..."

if [ -d "venv" ]; then
    echo "刪除舊的虛擬環境..."
    rm -rf venv
fi

# 創建虛擬環境並允許訪問系統套件（PyQt6）
python3 -m venv --system-site-packages venv
echo "✅ 虛擬環境創建完成（已啟用系統套件訪問）"

# 啟用虛擬環境
source venv/bin/activate
echo "✅ 虛擬環境已啟用"
echo ""

# -----------------------------------------------------------------------------
# 步驟 4: 安裝 Python 依賴（跳過 PyQt6）
#
# 重要：PyQt6 已從系統安裝，這裡只安裝其他依賴
# -----------------------------------------------------------------------------
echo "[4/5] 安裝 Python 依賴（跳過 PyQt6，使用系統版本）..."

if [ ! -f "requirements.txt" ]; then
    echo "❌ 找不到 requirements.txt"
    echo "請確保在專案根目錄執行此腳本"
    exit 1
fi

# 升級 pip
pip install --upgrade pip

# 創建臨時 requirements（排除 PyQt6）
grep -v "^PyQt6" requirements.txt > requirements_arm.txt

# 安裝依賴（排除 PyQt6）
pip install -r requirements_arm.txt

# 清理臨時文件
rm requirements_arm.txt

echo "✅ Python 依賴安裝完成"
echo "   PyQt6: 使用系統版本"
echo ""

# -----------------------------------------------------------------------------
# 步驟 5: 創建啟動腳本（方便下次使用）
# -----------------------------------------------------------------------------
echo "[5/5] 創建啟動腳本..."

cat > run.sh <<'EOF'
#!/bin/bash
# Basler Vision System 啟動腳本
# 每次運行應用時執行此腳本

# 啟用虛擬環境
source venv/bin/activate

# 運行應用程式
python basler_pyqt6/main_v2.py
EOF

chmod +x run.sh
echo "✅ 啟動腳本已創建: ./run.sh"
echo ""

# -----------------------------------------------------------------------------
# 完成
# -----------------------------------------------------------------------------
echo "════════════════════════════════════════════════════════"
echo "✅ 安裝完成！"
echo "════════════════════════════════════════════════════════"
echo ""
echo "現在運行應用程式："
echo "  ./run.sh"
echo ""
echo "或手動運行："
echo "  source venv/bin/activate"
echo "  python basler_pyqt6/main_v2.py"
echo ""
