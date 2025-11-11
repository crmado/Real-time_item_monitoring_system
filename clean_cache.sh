#!/bin/bash
# 清理 Python 緩存文件腳本
# 用於清理專案中所有的 __pycache__ 目錄和 .pyc 文件

set -e

echo "🧹 開始清理 Python 緩存文件..."
echo ""

# 進入專案目錄
cd "$(dirname "$0")" || exit 1

# 統計刪除前的文件數
before_count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
pyc_count=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l)
pyo_count=$(find . -type f -name "*.pyo" 2>/dev/null | wc -l)

echo "📊 當前狀態:"
echo "   • __pycache__ 目錄: $before_count 個"
echo "   • .pyc 文件: $pyc_count 個"
echo "   • .pyo 文件: $pyo_count 個"
echo ""

# 刪除 __pycache__ 目錄
echo "🗑️  刪除 __pycache__ 目錄..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 刪除 .pyc 文件
echo "🗑️  刪除 .pyc 文件..."
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# 刪除 .pyo 文件
echo "🗑️  刪除 .pyo 文件..."
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# 刪除 .pyd 文件（Windows 編譯的 Python 文件）
echo "🗑️  刪除 .pyd 文件..."
find . -type f -name "*.pyd" -delete 2>/dev/null || true

echo ""
echo "✅ 清理完成！"
echo ""
echo "💡 建議:"
echo "   • 定期運行此腳本以保持專案清潔"
echo "   • 在 git commit 前運行以避免提交緩存文件"
echo "   • 打包前運行以減少包體積"
echo ""
