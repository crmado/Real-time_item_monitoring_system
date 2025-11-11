#!/bin/bash
# Basler PyQt6 桌面應用一鍵啟動腳本（開發模式）
# 自動啟用 DEBUG_MODE，顯示調試工具和性能監控

echo "🛠️  啟動 Basler 工業視覺系統 (開發模式)..."
echo ""

# 設置開發模式環境變數
export DEBUG_MODE=true

# 執行主啟動腳本
exec "$(dirname "$0")/run_pyqt6.sh"
