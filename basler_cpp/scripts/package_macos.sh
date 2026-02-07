#!/bin/bash
# macOS 打包腳本 - Basler Vision System C++

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
OUTPUT_DIR="$PROJECT_DIR/dist"

APP_NAME="BaslerVisionSystem"
VERSION="2.0.0"

echo "=========================================="
echo "Basler Vision System - macOS 打包"
echo "版本: $VERSION"
echo "=========================================="

# 確認 build 目錄存在
if [ ! -d "$BUILD_DIR" ]; then
    echo "錯誤: build 目錄不存在，請先編譯專案"
    exit 1
fi

# 創建輸出目錄
mkdir -p "$OUTPUT_DIR"

# 編譯 Release 版本
echo ""
echo ">>> 編譯 Release 版本..."
cd "$BUILD_DIR"
/opt/homebrew/Cellar/cmake/3.31.5/bin/cmake .. -DCMAKE_BUILD_TYPE=Release
/opt/homebrew/Cellar/cmake/3.31.5/bin/cmake --build . --config Release

# 檢查 macdeployqt 位置
MACDEPLOYQT=""
if [ -f "/opt/homebrew/opt/qt@6/bin/macdeployqt" ]; then
    MACDEPLOYQT="/opt/homebrew/opt/qt@6/bin/macdeployqt"
elif [ -f "/usr/local/opt/qt@6/bin/macdeployqt" ]; then
    MACDEPLOYQT="/usr/local/opt/qt@6/bin/macdeployqt"
else
    # 搜索系統
    MACDEPLOYQT=$(find /opt/homebrew -name "macdeployqt" 2>/dev/null | head -1)
fi

if [ -z "$MACDEPLOYQT" ]; then
    echo "警告: 找不到 macdeployqt，將跳過 Qt 依賴打包"
else
    echo ""
    echo ">>> 使用 macdeployqt 打包 Qt 依賴..."
    "$MACDEPLOYQT" "$BUILD_DIR/${APP_NAME}.app" -verbose=1
fi

# 複製應用到輸出目錄
echo ""
echo ">>> 複製應用到 dist 目錄..."
rm -rf "$OUTPUT_DIR/${APP_NAME}.app"
cp -R "$BUILD_DIR/${APP_NAME}.app" "$OUTPUT_DIR/"

# 創建 DMG（可選）
echo ""
read -p "是否創建 DMG 安裝包？(y/n): " CREATE_DMG

if [ "$CREATE_DMG" = "y" ] || [ "$CREATE_DMG" = "Y" ]; then
    DMG_NAME="${APP_NAME}_v${VERSION}_macOS"
    
    echo ">>> 創建 DMG..."
    
    # 創建臨時目錄
    DMG_TEMP="$OUTPUT_DIR/dmg_temp"
    rm -rf "$DMG_TEMP"
    mkdir -p "$DMG_TEMP"
    
    # 複製應用
    cp -R "$OUTPUT_DIR/${APP_NAME}.app" "$DMG_TEMP/"
    
    # 創建 Applications 符號連結
    ln -s /Applications "$DMG_TEMP/Applications"
    
    # 創建 DMG
    hdiutil create -volname "$APP_NAME" \
        -srcfolder "$DMG_TEMP" \
        -ov -format UDZO \
        "$OUTPUT_DIR/${DMG_NAME}.dmg"
    
    # 清理
    rm -rf "$DMG_TEMP"
    
    echo ">>> DMG 已創建: $OUTPUT_DIR/${DMG_NAME}.dmg"
fi

echo ""
echo "=========================================="
echo "打包完成！"
echo "輸出位置: $OUTPUT_DIR/${APP_NAME}.app"
echo "=========================================="

# 顯示應用大小
echo ""
echo "應用大小:"
du -sh "$OUTPUT_DIR/${APP_NAME}.app"

