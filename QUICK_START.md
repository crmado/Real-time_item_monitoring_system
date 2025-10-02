# 🚀 PyQt6 版本快速開始指南

## 📦 安裝

### 1. 克隆專案（如果還沒有）
```bash
git clone <repository-url>
cd Real-time_item_monitoring_system
```

### 2. 切換到 PyQt6 專用分支
```bash
git checkout new_version_1
```

### 3. 創建虛擬環境（推薦）
```bash
# 使用 conda
conda create -n basler_pyqt6 python=3.10
conda activate basler_pyqt6

# 或使用 venv
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

### 4. 安裝依賴
```bash
pip install -r requirements.txt
```

## 🎯 運行應用

### 方式 1: 直接運行（推薦）
```bash
python basler_pyqt6/main_v2.py
```

### 方式 2: 使用啟動腳本（Mac/Linux）
```bash
./run_pyqt6.sh
```

### 方式 3: 從專案根目錄運行
```bash
python -m basler_pyqt6.main_v2
```

## 🧪 測試功能（無需實體相機）

### 測試視頻播放
1. 啟動應用
2. **文件** > **加載視頻文件...**
3. 選擇測試視頻（MP4/AVI）
4. 點擊 **▶️ 播放**

### 測試檢測功能
1. 在視頻播放時
2. **檢測面板** > 選擇方法（推薦：**背景減除**）
3. 勾選 **✅ 啟用檢測**
4. 觀察檢測效果

### 測試錄製功能
1. 在視頻播放時
2. （可選）啟用檢測
3. **錄影控制** > **⏺️ 開始錄製**
4. 錄製一段時間後
5. **⏹️ 停止錄製**
6. 查看統計信息
7. 文件保存在 `basler_pyqt6/recordings/`

## 📷 連接實體相機

### Basler 工業相機
1. 確保已安裝 pypylon：`pip install pypylon`
2. 連接 Basler 相機（GigE/USB）
3. 啟動應用
4. **模式** > **📷 相機模式**
5. 點擊 **🔍 檢測相機**
6. 選擇相機並點擊 **連接**
7. 點擊 **▶️ 開始抓取**

### 調整曝光
- 連接相機後
- 使用 **曝光時間** 滑桿
- 範圍：100-10000 μs

## 🔧 常見問題

### Q: 提示缺少 PyQt6
```bash
pip install PyQt6
```

### Q: 無法導入 pypylon
```bash
pip install pypylon
```

### Q: 視頻無法播放
- 確認視頻格式為 MP4/AVI
- 嘗試使用其他視頻文件
- 檢查日誌：`basler_pyqt6/logs/basler_pyqt6.log`

### Q: 檢測效果不理想
- 嘗試不同的檢測方法
- 調整參數（編輯 `basler_pyqt6/core/detection.py`）
- 背景減除最適合小零件檢測

### Q: 錄製的視頻無法打開
- 使用 VLC 媒體播放器
- 檢查錄製是否正常完成
- 查看日誌中的編碼器信息

## 📁 文件位置

### 錄製視頻
```
basler_pyqt6/recordings/
├── recording_20250101_120000.mp4
└── recording_20250101_120500.avi
```

### 日誌文件
```
basler_pyqt6/logs/
└── basler_pyqt6.log
```

## 🎨 UI 功能說明

### 左側面板
- **相機控制**：檢測、連接、抓取相機
- **檢測控制**：選擇檢測方法、啟用檢測
- **錄影控制**：開始/停止錄製

### 中間區域
- **視頻顯示**：實時顯示相機/視頻畫面

### 右側面板
- **系統監控**：CPU、記憶體、FPS、檢測統計

### 狀態欄（底部）
- 源類型、FPS、檢測數量、狀態信息

### 菜單欄
- **文件**：加載視頻、退出
- **模式**：切換相機/視頻模式
- **幫助**：關於信息

## 📝 開發指南

### 修改檢測參數
編輯 `basler_pyqt6/core/detection.py`:
```python
self.params = {
    'min_area': 100,      # 最小面積
    'max_area': 5000,     # 最大面積
    # ... 其他參數
}
```

### 添加新功能
參考 `README_PYQT6.md` 開發指南

## 🐛 調試模式

啟用詳細日誌：
```python
# 編輯 basler_pyqt6/main_v2.py
logging.basicConfig(
    level=logging.DEBUG,  # 改為 DEBUG
    # ...
)
```

## 📚 更多文檔

- [完整功能說明](PYQT6_PROFESSIONAL.md)
- [開發指南](README_PYQT6.md)
- [遷移說明](MIGRATION.md)

## ✅ 驗證安裝

運行測試腳本：
```python
python3 -c "
from basler_pyqt6.core.source_manager import SourceManager
from basler_pyqt6.core.detection import DetectionController
from basler_pyqt6.core.video_recorder import VideoRecorder

print('✅ 所有核心模塊正常')
"
```

如果沒有錯誤，說明安裝成功！

---

**需要幫助？** 查看 [完整文檔](PYQT6_PROFESSIONAL.md) 或提交 Issue
