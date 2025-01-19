```markdown
# 即時物件監測系統（Real-time Item Monitoring System）

這是一個使用 Python 開發的即時物件監測系統，專門用於工業生產線上的物件即時檢測和計數。系統提供圖形使用者介面，支援攝像頭即時監測和預先錄製的視頻分析。

## 系統環境

- Python 3.8.19
- 虛擬環境：RPi_4_camera

## 目錄結構

```plaintext
Real-time_item_monitoring_system/
├── .idea/                      # IDE 配置文件
├── logs/                       # 系統運行日誌
├── testDate/                   # 測試用影片
├── .gitignore                  # Git 忽略文件配置
├── object_detection_system.py  # 主程式文件
├── README.md                   # 項目說明文件
└── requirements.txt            # 依賴套件清單
```

## 主要功能

- 即時物件檢測和計數
- 支援多種視訊輸入源（攝像頭和預錄視頻）
- 可設定預期數量和警告閾值
- 自動物件追蹤
- 圖形化使用者介面
- 完整的日誌記錄

## 技術特點

系統採用以下技術實現核心功能：
- OpenCV：影像處理和物件檢測
- Tkinter：圖形使用者介面
- 背景消除：使用 MOG2 算法
- 物件追蹤：使用連通區域分析
- 多執行緒：確保 UI 響應性

## 安裝步驟

1. 建立並啟動虛擬環境：
```bash
python -m venv RPi_4_camera
.\RPi_4_camera\Scripts\activate  # Windows
source RPi_4_camera/bin/activate # Linux/macOS
```

2. 安裝依賴套件：
```bash
pip install -r requirements.txt
```

## 使用說明

1. 啟動程式：
```bash
python object_detection_system.py
```

2. 操作流程：
   - 從下拉選單選擇視訊來源
   - 設定預期數量和緩衝點（可選）
   - 點擊「開始監測」按鈕開始處理
   - 系統會自動檢測和計數物件
   - 達到緩衝點時會發出警告
   - 達到預期數量時會自動停止並通知

## 系統參數

- ROI 檢測區域高度：16 像素
- 物件面積範圍：10-150 像素²
- 背景消除器參數：
  - 歷史幀數：20000
  - 閾值：16
  - 陰影檢測：開啟
- 追蹤容許誤差：
  - X 軸：64 像素
  - Y 軸：48 像素
- 視訊處理速率：最高支援 206 FPS

## 日誌系統

- 自動在 logs 目錄創建日誌文件
- 日誌命名格式：detection_YYYYMMDD_HHMMSS.log
- 記錄內容包含：
  - 系統啟動/停止
  - 物件檢測結果
  - 錯誤訊息
  - 設定變更

## 錯誤處理

系統具備完整的錯誤處理機制：
- 視訊源無法開啟時的錯誤處理
- 影像處理異常捕捉
- 設定值驗證
- UI 操作異常處理

## 開發說明

- 開發環境：Python 3.8.19
- 專案管理：使用 Git 進行版本控制
- 代碼風格：遵循 PEP 8 規範
- 測試環境：Windows 系統，預計部署於樹莓派 4B

## 授權說明

本項目採用 MIT 授權條款。您可以自由使用、修改和分發本程式碼，但請保留原作者資訊。
```

這個 README.md 更準確地反映了您的專案結構和環境配置，包含了：
- 正確的 Python 版本（3.8.19）
- 實際的目錄結構
- 準確的虛擬環境名稱（RPi_4_camera）
- 具體的檔案配置
- 實際使用的系統參數

需要我針對某個部分進行更詳細的說明嗎？