# 🏭 Basler 工業視覺系統

高性能桌面應用，支持 Basler 工業相機實時檢測與視頻錄製。

## ✨ 核心特性

- **🎬 雙模式**：支持實體相機和視頻文件輸入
- **🔍 智能檢測**：內建多種檢測算法（圓形、輪廓、背景減除）
- **🎥 高速錄製**：支持 280+ FPS 高速視頻錄製
- **📊 實時監控**：CPU/記憶體使用率、FPS、檢測計數
- **🔄 自動更新**：內建版本檢查和自動更新功能

## 🚀 快速開始

### 安裝

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
├── ui/
│   └── main_window_v2.py   # 主窗口
├── core/
│   ├── camera_manager.py   # 相機管理
│   ├── detector.py         # 檢測引擎
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
- **圓形檢測**：霍夫圓檢測算法
- **輪廓檢測**：Canny 邊緣檢測 + 輪廓查找
- **背景減除**：KNN 背景減除算法
- 實時計數統計
- 虛擬光柵計數（進出統計）

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

- **Python**: 3.8+
- **操作系統**: Windows 10/11, macOS 10.14+, Linux
- **RAM**: 最低 4GB（建議 8GB+）
- **相機**（可選）: Basler acA640-300gm 或其他 Basler GigE 相機

## 📚 依賴項

- PyQt6 - GUI 框架
- OpenCV - 視覺處理
- pypylon - Basler 相機驅動
- numpy - 數值運算
- psutil - 系統監控
- requests - HTTP 請求（自動更新）

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

**Version**: 2.0.1
**Build Date**: 2025-10-13
**Build Type**: Release

### 版本歷史

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

**文檔更新**: 2025-10-13
**維護者**: Development Team
