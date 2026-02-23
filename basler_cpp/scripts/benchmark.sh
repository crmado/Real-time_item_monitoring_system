#!/bin/bash
# 效能對比測試腳本 - C++ vs Python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

CPP_APP="$SCRIPT_DIR/../build/BaslerVisionSystem.app/Contents/MacOS/BaslerVisionSystem"
PY_SCRIPT="$PROJECT_ROOT/basler_pyqt6/main.py"

echo "=========================================="
echo "Basler Vision System - 效能對比測試"
echo "=========================================="

# ========================
# 1. 應用大小對比
# ========================
echo ""
echo ">>> 1. 應用大小對比"
echo "-------------------------------------------"

CPP_SIZE=$(du -sh "$SCRIPT_DIR/../build/BaslerVisionSystem.app" 2>/dev/null | cut -f1)
echo "C++ 版本 (App Bundle): ${CPP_SIZE:-N/A}"

# Python 專案大小
PY_SIZE=$(du -sh "$PROJECT_ROOT/basler_pyqt6" 2>/dev/null | cut -f1)
echo "Python 版本 (源碼): ${PY_SIZE:-N/A}"

# ========================
# 2. 啟動時間測試
# ========================
echo ""
echo ">>> 2. 啟動時間測試 (5次平均)"
echo "-------------------------------------------"

# C++ 版本啟動時間
if [ -f "$CPP_APP" ]; then
    echo "測試 C++ 版本..."
    CPP_TIMES=()
    
    for i in {1..5}; do
        START=$(python3 -c "import time; print(int(time.time() * 1000))")
        "$CPP_APP" --test-startup &
        PID=$!
        sleep 2  # 等待啟動
        kill $PID 2>/dev/null
        wait $PID 2>/dev/null
        END=$(python3 -c "import time; print(int(time.time() * 1000))")
        DIFF=$((END - START))
        CPP_TIMES+=($DIFF)
    done
    
    CPP_AVG=$(echo "${CPP_TIMES[@]}" | tr ' ' '\n' | awk '{sum+=$1} END {print int(sum/NR)}')
    echo "C++ 平均啟動時間: ${CPP_AVG}ms"
fi

# ========================
# 3. 記憶體使用
# ========================
echo ""
echo ">>> 3. 記憶體使用對比"
echo "-------------------------------------------"

# 檢查當前運行中的應用
CPP_MEM=$(ps aux | grep "BaslerVisionSystem" | grep -v grep | awk '{sum+=$6} END {print sum}')
PY_MEM=$(ps aux | grep "python.*main" | grep -v grep | awk '{sum+=$6} END {print sum}')

if [ -n "$CPP_MEM" ] && [ "$CPP_MEM" -gt 0 ]; then
    echo "C++ 版本記憶體使用: $((CPP_MEM / 1024)) MB"
else
    echo "C++ 版本: 未運行"
fi

if [ -n "$PY_MEM" ] && [ "$PY_MEM" -gt 0 ]; then
    echo "Python 版本記憶體使用: $((PY_MEM / 1024)) MB"
else
    echo "Python 版本: 未運行"
fi

# ========================
# 4. 編譯資訊
# ========================
echo ""
echo ">>> 4. C++ 編譯資訊"
echo "-------------------------------------------"

if [ -f "$CPP_APP" ]; then
    echo "執行檔大小: $(ls -lh "$CPP_APP" | awk '{print $5}')"
    echo "架構: $(file "$CPP_APP" | grep -o 'arm64\|x86_64')"
fi

echo ""
echo "=========================================="
echo "測試完成"
echo "=========================================="
