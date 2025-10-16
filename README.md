# 🏭 Basler 工業視覺系統

高性能桌面應用，支持 Basler 工業相機實時檢測與視頻錄製。

## ✨ 核心特性

- **🎬 雙模式**：支持實體相機和視頻文件輸入
- **🔍 智能檢測**：內建多種檢測算法（圓形、輪廓、背景減除）
- **🔀 動態方法切換**：根據零件類型自動切換檢測方法（定量計數、瑕疵檢測）
- **📦 定量包裝**：雙震動機控制系統，智能速度調節
- **🎥 高速錄製**：支持 280+ FPS 高速視頻錄製
- **📊 實時監控**：CPU/記憶體使用率、FPS、檢測計數
- **🔄 自動更新**：內建版本檢查和自動更新功能

## 🚀 快速開始

### 方法 1: 使用 Conda（推薦）

```bash
# 創建環境
conda env create -f environment.yml
conda activate RPi_4_camera_py312

# 快速安裝
./install_deps.sh

# 運行應用
./run_pyqt6.sh
```

### 方法 2: 使用 pip

```bash
# 安裝依賴
pip install -r requirements.txt

# 運行應用
python basler_pyqt6/main_v2.py
```

### 測試模式（無需實體相機）

1. 啟動應用
2. 選擇 **文件 > 加載視頻文件**
3. 選擇測試視頻（`basler_pyqt6/testData/` 目錄下）
4. 點擊 **▶️ 播放**
5. 啟用檢測查看效果

## 📁 專案結構

```
basler_pyqt6/
├── main_v2.py              # 主程序入口
├── version.py              # 版本管理
├── updater.py              # 自動更新模組
├── config/                 # 統一配置系統
│   ├── settings.py         # 配置定義
│   └── detection_params.json # 配置持久化
├── ui/
│   ├── main_window_v2.py   # 主窗口
│   └── widgets/
│       ├── packaging_control.py      # 方法面板容器
│       ├── part_selector.py          # 零件選擇器
│       ├── method_selector.py        # 方法選擇器
│       └── method_panels/            # 動態方法面板
│           ├── counting_method_panel.py        # 定量計數面板
│           └── defect_detection_method_panel.py # 瑕疵檢測面板
├── core/
│   ├── camera.py           # 相機管理
│   ├── detection.py        # 檢測控制器
│   └── video_recorder.py   # 錄製引擎
└── testData/               # 測試視頻

scripts/
├── build.py                # 打包腳本
└── release.py              # 發布腳本

update_server/
└── app.py                  # 更新服務器
```

## 🎯 主要功能

### 1. 相機模式
- 支持 Basler acA640-300gm 工業相機
- 280+ FPS 高速抓取
- 實時曝光調整
- 硬體觸發支持

### 2. 視頻模式
- 支持多種視頻格式（MP4, AVI, MKV）
- 播放速度控制（0.5x - 2.0x）
- 逐幀播放
- 循環播放

### 3. 檢測功能

#### 定量計數方法
- **虛擬光柵計數**：工業級計數法（O(n)複雜度）
- **背景減除**：MOG2 演算法（極高靈敏度）
- **雙震動機控制**：智能速度調節（快速/中速/慢速/微動）
- **目標數量設定**：1-99999 個零件
- **進度追蹤**：實時顯示當前計數和進度

#### 瑕疵檢測方法
- **合格率統計**：動態顏色指示（綠/藍/橙/紅）
- **瑕疵分類**：刮痕、凹痕、變色三種類型
- **靈敏度調整**：0.0-1.0 可調
- **統計報表**：總數、合格數、不合格數、瑕疵分布

#### 通用功能
- 零件類型選擇（極小零件、中型零件、大型零件）
- 檢測方法自動切換（依據零件類型）
- 實時計數統計

### 4. 錄製功能
- H.264 編碼
- 可調節質量（CRF）
- 自動文件命名
- 錄製時長顯示

## 📦 打包與發布

詳細說明請參閱 [RELEASE.md](RELEASE.md)

### 快速發布

```bash
# 1. 更新版本號
vim basler_pyqt6/version.py

# 2. 打包
python scripts/build.py

# 3. 發布
python scripts/release.py --notes "更新說明"
```

## 🔄 自動更新

應用內建自動更新功能，用戶可通過菜單檢查更新：

**幫助 > 檢查更新**

系統會自動：
1. 檢查服務器上的最新版本
2. 顯示更新日誌
3. 下載並安裝更新
4. 重啟應用

## 🛠️ 系統需求

- **Python**: 3.12+ （需要 numpy 1.26+）
- **操作系統**: Windows 10/11, macOS 10.14+, Linux
- **RAM**: 最低 4GB（建議 8GB+）
- **相機**（可選）: Basler acA640-300gm 或其他 Basler GigE 相機

## 📚 依賴說明

所有依賴都在 `requirements.txt` 中：

### 桌面應用依賴
- **PyQt6** - GUI 框架
- **opencv-python-headless** - 視覺處理（無 GUI 版本）
- **pypylon** - Basler 相機驅動
- **numpy** - 數值運算
- **Pillow** - 圖像處理
- **psutil** - 系統監控
- **PyYAML** - 配置文件解析

### 網絡功能
- **requests** - HTTP 請求（自動更新功能）
- **paramiko** - SSH/SFTP（發布部署用）

### 開發工具
- **pyinstaller** - 打包成獨立應用

### 更新服務器（可選）
如需運行更新服務器，requirements.txt 已包含：
- **Flask** - Web 框架
- **Flask-CORS** - 跨域支持
- **Werkzeug** - WSGI 工具
- **gunicorn** - 生產級服務器

### 安裝注意事項

**Conda 用戶**：PyQt6 需要從 `conda-forge` 安裝
```bash
# 如果 conda 安裝失敗，使用完整路徑
/Users/crmado/anaconda3/bin/conda install -c conda-forge pyqt=6.6

# 或直接用 pip（最可靠）
pip install -r requirements.txt
```

**Python 版本**：需要 3.12+ 因為 numpy>=1.26 要求。如果使用 Python 3.9-3.11，請修改 requirements.txt 中 numpy 版本為 `numpy>=1.21.0,<1.26.0`

## 🐛 故障排除

### 相機無法連接

```bash
# 檢查相機是否被系統識別
pypylon-listdevices

# 確認網絡配置
# 相機 IP: 192.168.1.100
# 電腦 IP: 192.168.1.x (同網段)
```

### 檢測性能問題

- 降低解析度
- 調整檢測參數
- 關閉不需要的檢測算法

### 打包問題

詳見 [RELEASE.md](RELEASE.md) 的故障排除章節

## 📝 開發

### 當前版本

**Version**: 2.0.2
**Build Date**: 2025-10-16
**Build Type**: Release

### 版本歷史

- **v2.0.2** (2025-10-16)
  - 🎯 實作動態方法面板切換架構
  - 🔀 支援多種檢測方法（定量計數、瑕疵檢測）
  - 📦 新增零件類型選擇器
  - 🔧 修正 PyInstaller 打包路徑問題
  - 🎨 優化 UI 佈局和信號處理

- **v2.0.1** (2025-10-13)
  - 實現虛擬光柵計數法
  - 簡化追蹤系統
  - 性能優化

- **v2.0.0** (2024-10-05)
  - 全新 PyQt6 界面
  - 優化檢測算法
  - 添加自動更新功能

## 📄 授權

© 2025 Industrial Vision. All rights reserved.

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

---

**文檔更新**: 2025-10-16
**維護者**: Development Team
