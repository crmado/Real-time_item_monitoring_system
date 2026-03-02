#!/bin/bash
# ============================================================
# 本地打包腳本 - Basler Vision System C++
#
# 用法:
#   ./build-local.sh [平台]
#
# 平台選項:
#   macos        - macOS .dmg
#   linux        - Linux x86_64 AppImage
#   linux-arm64  - Linux aarch64 AppImage
#   linux-all    - Linux x86_64 + aarch64 (依序執行)
#   all          - 所有平台 (含 macOS)
#
# 環境變數:
#   APP_VERSION  - 版本號 (預設: 2.0.0)
#
# 範例:
#   ./build-local.sh linux
#   ./build-local.sh linux-arm64
#   APP_VERSION=2.1.0 ./build-local.sh linux-all
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASLER_SCRIPTS="$SCRIPT_DIR/basler_cpp/scripts"
VERSION="${APP_VERSION:-2.0.0}"

usage() {
  echo "用法: $0 [macos|linux|linux-arm64|linux-all|all]"
  echo ""
  echo "依賴:"
  echo "  macOS     - macdeployqt (brew install qt@6)"
  echo "  linux     - Docker (--platform linux/amd64)"
  echo "  linux-arm64 - Docker (--platform linux/arm64, Apple Silicon 原生)"
  exit 1
}

PLATFORM="${1:-linux}"

echo "版本: $VERSION"
echo ""

case "$PLATFORM" in
  macos)
    bash "$BASLER_SCRIPTS/package_macos.sh"
    ;;

  linux|linux-x86_64)
    APP_VERSION="$VERSION" bash "$BASLER_SCRIPTS/package_linux.sh" x86_64
    ;;

  linux-arm64|linux-aarch64)
    APP_VERSION="$VERSION" bash "$BASLER_SCRIPTS/package_linux.sh" aarch64
    ;;

  linux-all)
    echo "=== Linux x86_64 ==="
    APP_VERSION="$VERSION" bash "$BASLER_SCRIPTS/package_linux.sh" x86_64
    echo ""
    echo "=== Linux aarch64 ==="
    APP_VERSION="$VERSION" bash "$BASLER_SCRIPTS/package_linux.sh" aarch64
    ;;

  all)
    echo "=== macOS ==="
    bash "$BASLER_SCRIPTS/package_macos.sh"
    echo ""
    echo "=== Linux x86_64 ==="
    APP_VERSION="$VERSION" bash "$BASLER_SCRIPTS/package_linux.sh" x86_64
    echo ""
    echo "=== Linux aarch64 ==="
    APP_VERSION="$VERSION" bash "$BASLER_SCRIPTS/package_linux.sh" aarch64
    ;;

  -h|--help|help)
    usage
    ;;

  *)
    echo "❌ 未知平台: $PLATFORM"
    usage
    ;;
esac

echo ""
echo "releases/ 目錄內容："
ls -lh "$SCRIPT_DIR/releases/" 2>/dev/null || echo "  (空)"
