#!/bin/bash
# 更新服務器運行腳本（生產環境）

# 設置變數
HOST="0.0.0.0"
PORT=5000
WORKERS=4

echo "🚀 啟動 Basler Vision Update Server"
echo "   Host: $HOST"
echo "   Port: $PORT"
echo "   Workers: $WORKERS"
echo ""

# 使用 gunicorn 運行（生產環境）
gunicorn \
    --bind $HOST:$PORT \
    --workers $WORKERS \
    --timeout 300 \
    --access-logfile - \
    --error-logfile - \
    app:app
