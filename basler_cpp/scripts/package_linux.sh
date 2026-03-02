#!/bin/bash
# ============================================================
# Linux AppImage 打包腳本 - Basler Vision System C++
#
# 用法:
#   ./package_linux.sh [x86_64|aarch64]
#   APP_VERSION=2.1.0 ./package_linux.sh aarch64
#
# 依賴: Docker (用於在 Ubuntu 22.04 環境中建構)
# 輸出: releases/BaslerVisionSystem_v{版本}_Linux-{架構}.AppImage
#
# 注意:
#   - x86_64: 在 Apple Silicon 上透過 Rosetta 模擬，較慢
#   - aarch64: 在 Apple Silicon 上原生執行，較快
#   - 首次執行需安裝套件 (~10-15 分鐘)
# ============================================================

set -euo pipefail

# ──────────────────────────────────────────────
# 參數與路徑設定
# ──────────────────────────────────────────────
ARCH="${1:-x86_64}"
VERSION="${APP_VERSION:-2.0.0}"
APP_NAME="BaslerVisionSystem"

case "$ARCH" in
  x86_64|amd64)   ARCH="x86_64";   DOCKER_PLATFORM="linux/amd64" ;;
  aarch64|arm64)  ARCH="aarch64";  DOCKER_PLATFORM="linux/arm64" ;;
  *)
    echo "❌ 不支援的架構: $ARCH"
    echo "   支援: x86_64 (amd64), aarch64 (arm64)"
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASLER_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$BASLER_DIR")"
RELEASES_DIR="$ROOT_DIR/releases"
APPIMAGE_NAME="${APP_NAME}_v${VERSION}_Linux-${ARCH}.AppImage"

mkdir -p "$RELEASES_DIR"

# ──────────────────────────────────────────────
# 輸出資訊
# ──────────────────────────────────────────────
echo "╔══════════════════════════════════════════════╗"
echo "║   Basler Vision System - Linux AppImage 打包 ║"
echo "╠══════════════════════════════════════════════╣"
printf "║  架構  : %-35s║\n" "$ARCH ($DOCKER_PLATFORM)"
printf "║  版本  : %-35s║\n" "$VERSION"
printf "║  輸出  : %-35s║\n" "releases/$APPIMAGE_NAME"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ──────────────────────────────────────────────
# 前置檢查
# ──────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  echo "❌ 未找到 Docker，請先安裝 Docker Desktop"
  exit 1
fi

if ! docker info &>/dev/null; then
  echo "❌ Docker 未啟動，請先開啟 Docker Desktop"
  exit 1
fi

# ──────────────────────────────────────────────
# 寫入 Docker 容器內部的建構腳本（暫存檔）
# 使用單引號 'INNER_EOF' 防止外層 shell 展開變數
# 容器內變數 ($ARCH 等) 由 docker run -e 環境變數提供
# ──────────────────────────────────────────────
INNER_SCRIPT="$(mktemp /tmp/basler_linux_build_XXXX.sh)"
trap 'rm -f "$INNER_SCRIPT"' EXIT

cat > "$INNER_SCRIPT" << 'INNER_EOF'
#!/bin/bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

ARCH="${ARCH:-x86_64}"
APP_NAME="${APP_NAME:-BaslerVisionSystem}"
VERSION="${APP_VERSION:-2.0.0}"
APPIMAGE_NAME="${APPIMAGE_NAME:-BaslerVisionSystem_v2.0.0_Linux-x86_64.AppImage}"

# ── [1/7] 安裝系統依賴 ──────────────────────────────────────
echo ""
echo "=== [1/7] 安裝系統依賴 ==="
apt-get update -qq 2>&1 | tail -1
apt-get install -y -qq \
  build-essential cmake git wget curl file python3 \
  qt6-base-dev qt6-multimedia-dev \
  libgl1-mesa-dev libglu1-mesa-dev \
  libopencv-dev \
  libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 \
  libfuse2 squashfs-tools 2>&1 | tail -3
echo "  ✓ 依賴安裝完成"

# 查找 qmake6 (linuxdeploy-plugin-qt 需要)
QMAKE=""
for Q in qmake6 qmake; do
  if command -v "$Q" &>/dev/null; then
    QMAKE="$(which "$Q")"
    break
  fi
done
if [ -z "$QMAKE" ]; then
  QMAKE="$(find /usr -name "qmake6" -type f 2>/dev/null | head -1 || echo "")"
fi
[ -n "$QMAKE" ] && echo "  qmake6: $QMAKE" || echo "  ⚠ 未找到 qmake6，AppImage 可能無法部署 Qt 插件"

# ── [2/7] 複製原始碼 ─────────────────────────────────────────
echo ""
echo "=== [2/7] 複製原始碼 ==="
mkdir -p /build
cp -r /workspace/basler_cpp /build/basler_cpp
# 清除 macOS 的 build/ 快取，避免 CMakeCache.txt 路徑衝突
rm -rf /build/basler_cpp/build/
echo "  ✓ 已複製到 /build/basler_cpp (舊 build/ 已清除)"

# ── [3/7] CMake 設定 ─────────────────────────────────────────
echo ""
echo "=== [3/7] CMake 設定 ==="
cd /build/basler_cpp
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DSKIP_PYLON=ON 2>&1 | grep -E "^(--|CMake (Error|Warning))" | head -15
echo "  ✓ CMake 設定完成"

# ── [4/7] 編譯 ──────────────────────────────────────────────
echo ""
echo "=== [4/7] 編譯 (使用 $(nproc) 核心) ==="
cmake --build build --parallel "$(nproc)" 2>&1
echo ""
echo "  ✓ 編譯完成"
if [ -f "build/$APP_NAME" ]; then
  ls -lh "build/$APP_NAME"
else
  echo "❌ 找不到執行檔: build/$APP_NAME"
  exit 1
fi

# ── [5/7] 建立 AppDir 結構 ───────────────────────────────────
echo ""
echo "=== [5/7] 建立 AppDir 結構 ==="
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

cp "build/$APP_NAME" AppDir/usr/bin/

# 複製資源（若存在）
[ -d "/workspace/basler_cpp/assets" ]  && cp -r /workspace/basler_cpp/assets  AppDir/usr/bin/ || true
[ -d "/workspace/basler_cpp/config" ]  && cp -r /workspace/basler_cpp/config  AppDir/usr/bin/ || true
[ -d "/workspace/basler_cpp/models" ]  && cp -r /workspace/basler_cpp/models  AppDir/usr/bin/ || true

# .desktop 文件
cat > "AppDir/usr/share/applications/${APP_NAME}.desktop" << DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=Basler Vision System
Comment=Industrial Vision Detection System
Exec=BaslerVisionSystem
Icon=BaslerVisionSystem
Categories=Utility;Development;
Terminal=false
DESKTOP_EOF
cp "AppDir/usr/share/applications/${APP_NAME}.desktop" AppDir/

# 圖標（優先使用現有圖標，否則生成佔位符）
ICON_DST="AppDir/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png"
if [ -f "/workspace/basler_cpp/assets/icon.png" ]; then
  cp /workspace/basler_cpp/assets/icon.png "$ICON_DST"
  echo "  使用現有圖標"
else
  # 生成藍色 256x256 佔位 PNG
  python3 -c "
import struct, zlib, sys
w, h = 256, 256; r, g, b = 30, 120, 200
raw = b''.join(b'\x00' + bytes([r, g, b]) * w for _ in range(h))
c = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t+d) & 0xffffffff)
sys.stdout.buffer.write(b'\x89PNG\r\n\x1a\n'
  + c(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
  + c(b'IDAT', zlib.compress(raw))
  + c(b'IEND', b''))
" > "$ICON_DST"
  echo "  已生成佔位圖標"
fi
cp "$ICON_DST" AppDir/ 2>/dev/null || true
echo "  ✓ AppDir 結構建立完成"

# ── [6/7] 下載 linuxdeploy ──────────────────────────────────
echo ""
echo "=== [6/7] 下載 linuxdeploy-${ARCH} ==="
export APPIMAGE_EXTRACT_AND_RUN=1

BASE_URL="https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous"
PLUGIN_URL="https://github.com/linuxdeploy/linuxdeploy-plugin-qt/releases/download/continuous"

wget -q --show-progress "${BASE_URL}/linuxdeploy-${ARCH}.AppImage"
wget -q --show-progress "${PLUGIN_URL}/linuxdeploy-plugin-qt-${ARCH}.AppImage"
chmod +x linuxdeploy-*.AppImage
echo "  ✓ linuxdeploy 下載完成"

# ── [7/7] 生成 AppImage ─────────────────────────────────────
echo ""
echo "=== [7/7] 生成 AppImage ==="
[ -n "$QMAKE" ] && export QMAKE="$QMAKE" || true

./linuxdeploy-${ARCH}.AppImage \
  --appdir AppDir \
  --plugin qt \
  --desktop-file "AppDir/usr/share/applications/${APP_NAME}.desktop" \
  --icon-file "AppDir/usr/share/icons/hicolor/256x256/apps/${APP_NAME}.png" \
  --output appimage

# 找到生成的 AppImage（排除 linuxdeploy 工具本身）
GENERATED="$(find . -maxdepth 1 -name "*.AppImage" ! -name "linuxdeploy*" -print -quit 2>/dev/null || echo "")"
if [ -z "$GENERATED" ]; then
  echo "❌ AppImage 生成失敗！"
  echo "目錄內容:"
  ls -la *.AppImage 2>/dev/null || echo "  (無 .AppImage 文件)"
  exit 1
fi

mv "$GENERATED" "/output/${APPIMAGE_NAME}"
SIZE="$(du -sh "/output/${APPIMAGE_NAME}" | cut -f1)"
echo ""
echo "  ✓ AppImage 生成成功！"
echo "  文件: $APPIMAGE_NAME"
echo "  大小: $SIZE"
INNER_EOF

# ──────────────────────────────────────────────
# 拉取映像並執行 Docker 建構
# ──────────────────────────────────────────────
echo ">>> 拉取 Ubuntu 22.04 ($DOCKER_PLATFORM)..."
docker pull --platform "$DOCKER_PLATFORM" ubuntu:22.04 -q

echo ">>> 啟動 Docker 容器建構..."
echo ""

docker run --rm \
  --platform "$DOCKER_PLATFORM" \
  -v "${ROOT_DIR}:/workspace:ro" \
  -v "${RELEASES_DIR}:/output" \
  -v "${INNER_SCRIPT}:/build_inner.sh:ro" \
  -e APP_VERSION="$VERSION" \
  -e ARCH="$ARCH" \
  -e APP_NAME="$APP_NAME" \
  -e APPIMAGE_NAME="$APPIMAGE_NAME" \
  ubuntu:22.04 \
  bash /build_inner.sh

# ──────────────────────────────────────────────
# 完成報告
# ──────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║  ✅ Linux $ARCH 打包完成！                   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "輸出位置: $RELEASES_DIR/$APPIMAGE_NAME"
if [ -f "$RELEASES_DIR/$APPIMAGE_NAME" ]; then
  ls -lh "$RELEASES_DIR/$APPIMAGE_NAME"
fi
