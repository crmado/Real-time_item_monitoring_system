@echo off
echo ========================================
echo 即時物品監測系統 - 虛擬環境啟動腳本
echo ========================================

REM 激活 conda 環境
call conda activate item_monitoring

REM 檢查是否成功激活
if errorlevel 1 (
    echo 錯誤：無法激活虛擬環境
    echo 請確保已創建 item_monitoring 環境
    pause
    exit /b 1
)

echo ✓ 虛擬環境已激活
echo ✓ Python 路徑: %CONDA_PREFIX%
echo.

REM 檢查必要套件
echo 檢查必要套件...
python -c "import cv2; print('✓ OpenCV:', cv2.__version__)" 2>nul
if errorlevel 1 (
    echo ✗ OpenCV 未安裝，正在安裝...
    pip install opencv-python
)

python -c "import numpy; print('✓ NumPy:', numpy.__version__)" 2>nul
if errorlevel 1 (
    echo ✗ NumPy 未安裝，正在安裝...
    pip install numpy
)

python -c "from PIL import Image; print('✓ Pillow 已安裝')" 2>nul
if errorlevel 1 (
    echo ✗ Pillow 未安裝，正在安裝...
    pip install pillow
)

echo.
echo ========================================
echo 選擇運行模式：
echo 1. 正常運行 (main.py)
echo 2. 改進運行 (run.py)
echo 3. Debug 模式 (debug_main.py)
echo 4. PDB Debug 模式 (debug_with_pdb.py)
echo 5. 退出
echo ========================================

set /p choice="請選擇 (1-5): "

if "%choice%"=="1" (
    echo 啟動正常模式...
    python main.py
) else if "%choice%"=="2" (
    echo 啟動改進模式...
    python run.py
) else if "%choice%"=="3" (
    echo 啟動 Debug 模式...
    python debug_main.py
) else if "%choice%"=="4" (
    echo 啟動 PDB Debug 模式...
    python debug_with_pdb.py
) else if "%choice%"=="5" (
    echo 退出...
    exit /b 0
) else (
    echo 無效選擇，使用預設模式 (main.py)
    python main.py
)

echo.
echo 程式已結束
pause 