# 🐛 Linux 執行錯誤診斷指南

## ❌ 錯誤：cannot execute binary file: exec format error

這個錯誤通常表示二進制文件與您的系統不兼容。以下是診斷和解決方案。

---

## 🔍 步驟 1：診斷問題

### 1.1 檢查文件類型

```bash
cd usr/bin
file BaslerVisionSystem
```

**期望輸出**：
```
BaslerVisionSystem: ELF 64-bit LSB executable, x86-64, ...
```

**如果輸出不是這樣**，說明文件可能損壞或不是正確的可執行文件。

### 1.2 檢查系統架構

```bash
uname -m
```

**可能的輸出**：
- `x86_64` - 64位 Intel/AMD 處理器（**兼容**）
- `aarch64` 或 `armv7l` - ARM 處理器（**不兼容**）
- `i686` - 32位處理器（**不兼容**）

**問題**：GitHub Actions 構建的是 **x86_64** 版本，如果您的系統是 ARM（如樹莓派），將無法運行。

### 1.3 檢查文件權限

```bash
ls -l BaslerVisionSystem
```

確保有執行權限（`-rwxr-xr-x`）。

### 1.4 檢查依賴庫

```bash
ldd BaslerVisionSystem | grep "not found"
```

如果有輸出，說明缺少必要的共享庫。

---

## ✅ 解決方案

### 方案 1：從 Python 源碼運行（推薦 - 最可靠）

**優點**：
- ✅ 支持所有架構（x86_64, ARM, etc.）
- ✅ 不依賴 PyInstaller 打包
- ✅ 易於調試和修改

**步驟**：

```bash
# 1. 克隆或下載源碼
git clone https://github.com/你的用戶名/Real-time_item_monitoring_system.git
cd Real-time_item_monitoring_system

# 2. 安裝 Python 依賴
# 使用 Conda（推薦）
conda env create -f environment.yml
conda activate RPi_4_camera_py312

# 或使用 pip
pip install -r requirements.txt

# 3. 直接運行 Python 源碼
python basler_pyqt6/main_v2.py
```

### 方案 2：使用 Docker 容器（跨架構）

如果您的系統支持 Docker：

```bash
# 創建 Dockerfile
cat > Dockerfile <<'EOF'
FROM python:3.12-slim

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libxkbcommon-x11-0 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    git \
    && rm -rf /var/lib/apt/lists/*

# 克隆專案
WORKDIR /app
RUN git clone https://github.com/你的用戶名/Real-time_item_monitoring_system.git .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 運行應用
CMD ["python", "basler_pyqt6/main_v2.py"]
EOF

# 構建並運行
docker build -t baslervision .
docker run -it --rm \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    baslervision
```

### 方案 3：針對您的架構重新打包

如果您需要二進制版本，在**目標系統**上本地打包：

```bash
# 1. 安裝依賴
pip install -r requirements.txt
pip install pyinstaller

# 2. 運行打包腳本
python scripts/build.py

# 3. 生成的可執行文件在
ls dist/BaslerVisionSystem/
```

### 方案 4：檢查是否下載錯誤

確保您下載的是正確的文件：

```bash
# 下載的文件應該是
BaslerVision_v2.0.6_Linux.tar.gz  # tar.gz 格式
# 或
BaslerVision_v2.0.6_Linux.AppImage  # AppImage 格式

# 不應該是
BaslerVisionSystem-linux-dist.zip  # 這是錯誤的備用包
```

---

## 🎯 推薦方案對比

| 方案 | 適用場景 | 優點 | 缺點 |
|------|---------|------|------|
| **Python 源碼** | 開發、測試、任何架構 | 最靈活、支持所有平台 | 需要 Python 環境 |
| **Docker** | 服務器、隔離環境 | 環境一致、易於部署 | 需要 Docker |
| **本地打包** | 單一系統長期使用 | 獨立可執行文件 | 需要在目標系統上打包 |
| **預構建二進制** | x86_64 Linux 系統 | 開箱即用 | 架構限制 |

---

## 📊 架構兼容性表

| 您的系統架構 | GitHub Actions 構建 | 是否兼容 | 推薦方案 |
|-------------|-------------------|---------|---------|
| x86_64 (Intel/AMD 64-bit) | ✅ 支持 | ✅ 是 | 預構建二進制 |
| aarch64 (ARM 64-bit) | ❌ 不支持 | ❌ 否 | Python 源碼 |
| armv7l (ARM 32-bit) | ❌ 不支持 | ❌ 否 | Python 源碼 |
| i686 (x86 32-bit) | ❌ 不支持 | ❌ 否 | Python 源碼 |

---

## 🔧 快速診斷腳本

保存並運行此腳本以自動診斷：

```bash
#!/bin/bash
# diagnose_linux.sh

echo "🔍 Basler Vision System - Linux 診斷工具"
echo "=========================================="
echo ""

# 檢查系統架構
ARCH=$(uname -m)
echo "📊 系統架構: $ARCH"

case $ARCH in
    x86_64)
        echo "   ✅ 兼容 GitHub Actions 構建的二進制文件"
        COMPATIBLE=true
        ;;
    aarch64|armv7l|armv6l)
        echo "   ❌ 不兼容（ARM 架構）"
        echo "   💡 建議：使用 Python 源碼運行"
        COMPATIBLE=false
        ;;
    i686|i386)
        echo "   ❌ 不兼容（32位架構）"
        echo "   💡 建議：使用 Python 源碼運行"
        COMPATIBLE=false
        ;;
    *)
        echo "   ⚠️  未知架構"
        COMPATIBLE=false
        ;;
esac

echo ""

# 檢查 Python
echo "🐍 檢查 Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "   ✅ $PYTHON_VERSION"

    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)"; then
        echo "   ✅ Python 版本符合要求 (>= 3.12)"
    else
        echo "   ⚠️  Python 版本過低，建議升級到 3.12+"
    fi
else
    echo "   ❌ 未安裝 Python3"
fi

echo ""

# 檢查 Qt 依賴
echo "📦 檢查 Qt 依賴..."
MISSING_DEPS=()

for lib in libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 libgl1-mesa-glx; do
    if dpkg -l | grep -q "^ii  $lib"; then
        echo "   ✅ $lib"
    else
        echo "   ❌ $lib (缺少)"
        MISSING_DEPS+=($lib)
    fi
done

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo ""
    echo "💡 安裝缺少的依賴："
    echo "   sudo apt-get install -y ${MISSING_DEPS[@]}"
fi

echo ""

# 檢查可執行文件（如果存在）
if [ -f "usr/bin/BaslerVisionSystem" ]; then
    echo "🔍 檢查可執行文件..."
    FILE_TYPE=$(file usr/bin/BaslerVisionSystem)
    echo "   文件類型: $FILE_TYPE"

    if echo "$FILE_TYPE" | grep -q "ELF 64-bit"; then
        echo "   ✅ 是有效的 64位 ELF 可執行文件"
    else
        echo "   ❌ 不是有效的可執行文件"
    fi

    if [ -x "usr/bin/BaslerVisionSystem" ]; then
        echo "   ✅ 有執行權限"
    else
        echo "   ❌ 缺少執行權限"
        echo "   💡 運行: chmod +x usr/bin/BaslerVisionSystem"
    fi
else
    echo "⚠️  未找到可執行文件（可能尚未解壓）"
fi

echo ""
echo "=========================================="
echo "🎯 推薦方案:"

if [ "$COMPATIBLE" = true ]; then
    echo ""
    echo "您的系統兼容預構建二進制文件。"
    echo ""
    echo "如果仍然無法運行，嘗試："
    echo "1. 從 Python 源碼運行（最可靠）："
    echo "   git clone https://github.com/你的用戶名/專案.git"
    echo "   cd Real-time_item_monitoring_system"
    echo "   pip install -r requirements.txt"
    echo "   python basler_pyqt6/main_v2.py"
    echo ""
    echo "2. 檢查錯誤日誌："
    echo "   ./usr/bin/BaslerVisionSystem 2>&1 | tee error.log"
else
    echo ""
    echo "您的系統架構不兼容預構建二進制文件。"
    echo ""
    echo "請使用 Python 源碼運行："
    echo "  git clone https://github.com/你的用戶名/專案.git"
    echo "  cd Real-time_item_monitoring_system"
    echo "  pip install -r requirements.txt"
    echo "  python basler_pyqt6/main_v2.py"
fi

echo "=========================================="
```

保存後運行：
```bash
chmod +x diagnose_linux.sh
./diagnose_linux.sh
```

---

## 💬 獲取幫助

如果以上方案都無法解決，請提供以下信息報告問題：

```bash
# 收集系統信息
cat > system_info.txt <<EOF
系統架構: $(uname -m)
操作系統: $(cat /etc/os-release | grep PRETTY_NAME)
Python 版本: $(python3 --version 2>&1)
文件類型: $(file usr/bin/BaslerVisionSystem 2>&1)
文件權限: $(ls -l usr/bin/BaslerVisionSystem 2>&1)
依賴檢查: $(ldd usr/bin/BaslerVisionSystem 2>&1 | grep "not found")
EOF

cat system_info.txt
```

將輸出複製並在 GitHub Issues 中報告。

---

**更新日期**: 2025-10-23
**適用版本**: v2.0.6+
