# 🚀 Basler acA640-300gm MVC 精簡高性能系統

## 📖 項目概述

這是一個專為 Basler acA640-300gm 工業相機設計的精簡高性能影像處理系統。採用標準 MVC (Model-View-Controller) 架構，專注於核心功能，追求極致性能。

## 🏗️ 架構設計

### MVC 架構

```
basler_mvc/
├── models/                 # 數據模型層
│   ├── basler_camera_model.py    # 相機數據模型
│   ├── detection_model.py        # 檢測數據模型
│   └── __init__.py
├── views/                  # 視圖層
│   ├── main_view.py              # 主視圖
│   └── __init__.py
├── controllers/            # 控制器層
│   ├── main_controller.py        # 主控制器
│   └── __init__.py
├── config/                 # 配置管理
│   ├── settings.py               # 系統配置
│   └── __init__.py
├── logs/                   # 日誌目錄
├── main.py                 # 主程序入口
└── README.md              # 項目說明
```

### 核心特色

- **🎯 專注核心功能**: 只保留 Basler 相機和影像檢測
- **⚡ 極致性能**: 多線程架構，零延遲幀獲取
- **🏗️ 標準 MVC**: 清晰的架構分離，易於維護
- **🔧 高度可配置**: 集中的配置管理
- **📊 實時監控**: 詳細的性能統計

## 🚀 快速開始

### 1. 環境要求

```bash
Python 3.7+
```

### 2. 安裝依賴

```bash
pip install opencv-python numpy Pillow pypylon
```

### 3. 運行系統

```bash
cd basler_mvc
python main.py
```

### 4. 操作流程

1. **🔍 檢測相機** - 掃描可用的 Basler 相機
2. **🔗 連接相機** - 連接到 acA640-300gm
3. **🚀 啟動系統** - 開始高速捕獲和檢測
4. **📊 查看性能** - 實時監控系統性能

## 🎮 功能特色

### 相機功能

- ✅ Basler acA640-300gm 專用優化
- ✅ 640×480 Mono8 高速處理
- ✅ 280+ FPS 穩定捕獲
- ✅ 零延遲幀獲取
- ✅ 自動最佳化配置

### 檢測功能

- ✅ 圓形檢測 (霍夫變換)
- ✅ 輪廓檢測 (形態學)
- ✅ 實時參數調整
- ✅ 可視化檢測結果
- ✅ 性能統計

### 系統功能

- ✅ 多線程並行處理
- ✅ 觀察者模式事件通知
- ✅ 實時性能監控
- ✅ 異常處理和恢復
- ✅ 詳細日誌記錄

## ⚙️ 配置說明

### 相機配置 (config/settings.py)

```python
CAMERA_CONFIG = {
    'target_fps': 350.0,          # 目標FPS
    'default_exposure_time': 1000.0,  # 曝光時間(μs)
    'enable_jumbo_frames': True,   # 啟用巨型幀
    'packet_size': 9000           # 網路封包大小
}
```

### 檢測配置

```python
DETECTION_CONFIG = {
    'default_method': 'circle',    # 預設檢測方法
    'min_area': 100,              # 最小物件面積
    'max_area': 5000              # 最大物件面積
}
```

## 📊 性能指標

### 目標性能

- **相機 FPS**: 280+ FPS
- **處理 FPS**: 200+ FPS
- **檢測 FPS**: 150+ FPS
- **UI 更新**: 30 FPS
- **延遲**: < 5ms

### 性能監控

系統提供實時性能監控，包括：

- 相機幀率統計
- 處理效率分析
- 檢測性能評估
- 系統資源使用

## 🔧 開發指南

### 擴展檢測方法

1. 繼承 `DetectionMethod` 基類
2. 實現必要的抽象方法
3. 在 `DetectionModel` 中註冊新方法

```python
class NewDetection(DetectionMethod):
    def process_frame(self, frame):
        # 實現幀處理邏輯
        pass

    def detect_objects(self, processed_frame, min_area, max_area):
        # 實現物件檢測邏輯
        pass
```

### 自定義視圖

1. 繼承或修改 `MainView`
2. 實現觀察者模式接口
3. 處理控制器事件通知

### 配置管理

所有配置集中在 `config/settings.py`，支持運行時動態更新。

## 🐛 故障排除

### 常見問題

1. **pypylon 未安裝**

   ```bash
   pip install pypylon
   ```

2. **相機連接失敗**

   - 檢查相機電源和網路連接
   - 確認相機 IP 設置
   - 檢查防火牆設置

3. **性能不達標**
   - 確認網路設置 (MTU 9000)
   - 檢查系統資源使用
   - 調整檢測參數

### 日誌診斷

系統會在 `logs/basler_mvc.log` 中記錄詳細運行信息，可用於問題診斷。

## 📈 性能優化建議

1. **網路設置**: 啟用 Jumbo Frames (MTU 9000)
2. **系統設置**: 關閉不必要的後台程序
3. **參數調整**: 根據實際需求調整檢測參數
4. **硬體配置**: 使用高性能網卡和 CPU

## 🔄 版本歷史

- **v1.0**: 初始版本，完整 MVC 架構
- 基於原項目的精簡重構
- 專注 Basler acA640-300gm 優化

## 📄 授權

本項目採用精簡設計理念，專注於工業相機的高性能處理。

---

**🎯 設計理念**: 簡潔、高效、專業
**⚡ 性能目標**: 工業級穩定性和速度
**🔧 維護性**: 清晰的 MVC 架構，易於擴展
