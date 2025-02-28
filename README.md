# 即時物件監測系統（Real-time Item Monitoring System）

這是一個使用 Python 開發的即時物件監測系統，專門用於工業生產線上的物件即時檢測和計數。系統提供圖形使用者介面，支援攝像頭即時監測和預先錄製的視頻分析。

## 系統環境

- Python 3.10
- 虛擬環境：RPi_4_camera

## 目錄結構

```plaintext
Real-time_item_monitoring_system/
│
├── main.py                 # 主程式入口
├── requirements.txt        # 專案依賴
│
├── models/                 # Model 層 - 處理資料和業務邏輯
│   ├── __init__.py
│   ├── system_config.py    # 系統配置
│   ├── image_processor.py  # 影像處理
│   └── camera_manager.py   # 攝影機管理
│
├── views/                  # View 層 - 使用者介面
│   ├── __init__.py
│   ├── ui_manager.py       # UI 樣式管理
│   ├── main_window.py      # 主視窗
│   └── components/         # UI 元件
│       ├── __init__.py
│       ├── control_panel.py
│       ├── video_panel.py
│       ├── settings_panel.py
│       └── setting/
│           └── settings_dialog.py  # 設定對話框
│
├── controllers/            # Controller 層 - 控制邏輯
│   ├── __init__.py
│   ├── detection_controller.py    # 物件偵測控制器
│   └── system_controller.py       # 系統控制器
│
├── utils/                  # 工具類
│   ├── __init__.py
│   ├── logger.py           # 日誌工具
│   ├── config.py           # 配置管理
│   ├── exceptions.py       # 異常處理
│   ├── language.py         # 多語言支援
│   └── theme_manager.py    # 主題管理
│
├── config/                 # 配置目錄
│   └── config.yaml         # 系統配置檔
│
├── languages/              # 語言資源目錄
│   ├── zh_TW.json          # 繁體中文
│   ├── en_US.json          # 英文
│   └── zh_CN.json          # 簡體中文
│
├── icons/                  # 圖標資源目錄
│   └── settings.png        # 設定圖標
│
├── logs/                   # 日誌目錄
│   └── detection_*.log     # 系統日誌文件
│
├── README.md               # 項目說明文件
└── requirements.txt        # 依賴套件清單

```

## 主要功能

- 即時物件檢測和計數
- 支援多種視訊輸入源（攝像頭和預錄視頻）
- 可設定預期數量和警告閾值
- 自動物件追蹤
- 圖形化使用者介面，支援主題切換
- 多語言支援（繁體中文、英文、簡體中文）
- 設定的持久化存儲
- 完整的日誌記錄

## 技術特點

系統採用以下技術實現核心功能：
- 架構：嚴格的 MVC 架構設計
- 影像處理：使用 OpenCV 進行影像分析和物件檢測
- GUI：使用 Tkinter 建立圖形使用者介面
- 背景消除：採用 MOG2 算法識別移動物體
- 物件追蹤：基於連通區域分析實現物件追蹤
- 多執行緒：使用線程池確保 UI 響應性和處理效能
- 設定管理：YAML格式配置持久化存儲
- 國際化：完整的多語言支援系統

## 安裝步驟

1. 建立並啟動虛擬環境：
```bash
    conda create -n RPi_4_camera python=3.10
    conda activate RPi_4_camera
```

2. 安裝依賴套件：
```bash
    pip install -r requirements.txt
```

## 使用說明

1. 啟動程式：
```bash
    python3 main.py
```

2. 打包執行檔：
```bash
    # 產生 spec 檔案
    pyinstaller --clean object_detection_system.spec
    # 執行打包後的程式，並將錯誤日誌導向到 logs 資料夾
    .\dist\object_detection_system.exe 2> logs\error.log
    
    # lixux 系統格式專用
    pyinstaller --onefile main.py
```

3. 操作流程：
   - 從下拉選單選擇視訊來源
   - 設定預期數量和緩衝點
   - 點擊「開始監測」按鈕開始處理
   - 點擊右上角設定圖標可進入系統設定
   - 系統會自動記住您的設定和偏好
   - 達到緩衝點時會發出警告
   - 達到預期數量時會自動停止並通知

## 系統設定

系統設定分為三個部分：

1. **一般設定**
   - 語言選擇（繁體中文、英文、簡體中文）
   - 啟動時自動檢查更新
   - 配置修改前自動備份

2. **顯示設定**
   - 主題選擇（亮色模式、暗色模式）
   - 字體大小（小、中、大）
   - 效能資訊顯示開關

3. **檢測設定**
   - 預計數量和緩衝點
   - ROI 預設位置（百分比）
   - 物件面積範圍（最小/最大）

所有設定都會自動保存到配置文件，下次啟動時自動套用。

## 系統參數

- ROI 檢測區域高度：16 像素（可配置）
- 物件面積範圍：10-150 像素²（可配置）
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

## 開發說明

- 開發環境：Python 3.10
- 專案管理：使用 Git 進行版本控制
- 代碼風格：遵循 PEP 8 規範
- 測試環境：Windows 系統，預計部署於樹莓派 4B
- 代碼組織：功能模組化，結構清晰

## 授權說明

本項目採用 MIT 授權條款。您可以自由使用、修改和分發本程式碼，但請保留原作者資訊。