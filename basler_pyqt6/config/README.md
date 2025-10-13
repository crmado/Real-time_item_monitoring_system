# basler_pyqt6 統一配置管理系統

## 📋 概述

這是 basler_pyqt6 項目的統一配置管理系統，參考 basler_mvc 的配置架構設計。所有檢測參數、UI 設定、性能優化參數都統一在這裡管理。

## 🎯 設計目標

- ✅ **統一管理**: 所有參數集中在一個配置檔案中
- ✅ **避免混亂**: 消除參數散落在各處的問題
- ✅ **易於維護**: 基於 dataclass 的類型安全配置
- ✅ **支援持久化**: JSON 格式儲存和載入
- ✅ **運行時可修改**: 支援動態更新參數

## 📁 檔案結構

```
basler_pyqt6/config/
├── __init__.py           # 模組初始化
├── settings.py           # 配置定義和管理
├── detection_params.json # JSON 配置檔案（自動生成）
└── README.md            # 本說明文件
```

## 🔧 配置結構

### 1. DetectionConfig（檢測配置）

基於 basler_mvc 驗證的檢測參數：

```python
detection:
  min_area: 2              # 極小零件最小面積
  max_area: 3000           # 最大面積
  bg_var_threshold: 3      # 背景減除閾值（極高敏感度）
  bg_history: 1000         # 背景歷史幀數
  bg_learning_rate: 0.001  # 極低學習率
  roi_enabled: true        # ROI 檢測區域
  roi_height: 150          # ROI 高度
  # ... 更多參數見 settings.py
```

### 2. GateConfig（虛擬光柵配置）

工業級虛擬光柵計數參數：

```python
gate:
  enable_gate_counting: true      # 啟用光柵計數
  gate_line_position_ratio: 0.5   # 光柵線位置（ROI 中的比例）
  gate_trigger_radius: 20          # 去重半徑（像素）
  gate_history_frames: 8           # 觸發歷史幀數
```

### 3. UIConfig（UI 配置）

調試面板的預設值和範圍：

```python
ui:
  min_area_range: [1, 100]        # 最小面積滑桿範圍
  min_area_default: 2             # 預設值
  max_area_range: [500, 10000]
  max_area_default: 3000
  # ... 更多 UI 參數
```

### 4. PerformanceConfig（性能配置）

性能優化參數：

```python
performance:
  image_scale: 0.5        # 圖像縮放比例
  skip_frames: 0          # 跳幀數
  show_gray: false        # 調試選項
  show_timing: true
```

### 5. DebugConfig（調試配置）

調試功能配置：

```python
debug:
  debug_save_enabled: false
  debug_save_dir: "basler_pyqt6/recordings/debug"
  max_debug_frames: 100
```

## 💻 使用方式

### 方式 1: 在代碼中使用配置

```python
from config.settings import get_config

# 獲取全局配置實例
config = get_config()

# 讀取參數
min_area = config.detection.min_area
gate_radius = config.gate.gate_trigger_radius

# 更新參數
config.update_detection_params(min_area=5, max_area=2500)

# 保存到 JSON 檔案
config.save()
```

### 方式 2: 在類初始化時使用

```python
from config.settings import get_config, AppConfig

class MyDetector:
    def __init__(self, config: Optional[AppConfig] = None):
        # 自動載入配置
        self.config = config if config else get_config()

        # 從配置讀取參數
        self.min_area = self.config.detection.min_area
        self.max_area = self.config.detection.max_area
```

### 方式 3: 直接編輯 JSON 檔案

編輯 `basler_pyqt6/config/detection_params.json`：

```json
{
  "detection": {
    "min_area": 5,
    "max_area": 2500
  }
}
```

重啟應用後自動載入新配置。

## 🔄 配置管理 API

### 初始化和載入

```python
from config.settings import init_config, get_config

# 初始化配置（指定配置檔案）
config = init_config(Path("my_config.json"))

# 獲取當前配置
config = get_config()

# 從檔案載入
config = AppConfig.load(Path("my_config.json"))
```

### 參數更新

```python
# 更新檢測參數
config.update_detection_params(
    min_area=5,
    max_area=2500,
    bg_var_threshold=5
)

# 更新光柵參數
config.update_gate_params(
    gate_trigger_radius=25,
    gate_history_frames=10
)

# 更新性能參數
config.update_performance_params(
    image_scale=0.75,
    skip_frames=1
)
```

### 保存和重置

```python
# 保存當前配置
config.save()

# 保存到指定檔案
config.save(Path("backup_config.json"))

# 重置為預設值
config.reset_to_default()
config.save()  # 保存重置後的配置
```

### 配置驗證

```python
from config.settings import validate_config

# 驗證配置有效性
if validate_config(config):
    print("配置有效")
else:
    print("配置無效")
```

## 📊 配置整合狀態

### ✅ 已整合的模組

1. **detection.py** - 檢測控制器
   - 從配置讀取所有檢測參數
   - 支援運行時參數更新
   - 配置路徑: `basler_pyqt6/core/detection.py:27`

2. **debug_panel.py** - 調試面板 UI
   - UI 控件範圍和預設值從配置讀取
   - 支援配置保存/載入功能
   - 配置路徑: `basler_pyqt6/ui/widgets/debug_panel.py:55`

### 📝 參數對應表

| 參數名稱 | settings.py | detection.py | debug_panel.py |
|---------|-------------|--------------|----------------|
| min_area | ✅ 統一 | ✅ 從配置讀取 | ✅ 從配置讀取 |
| max_area | ✅ 統一 | ✅ 從配置讀取 | ✅ 從配置讀取 |
| bg_var_threshold | ✅ 統一 | ✅ 從配置讀取 | ✅ 從配置讀取 |
| gate_trigger_radius | ✅ 統一 | ✅ 從配置讀取 | ✅ 從配置讀取 |
| gate_history_frames | ✅ 統一 | ✅ 從配置讀取 | ✅ 從配置讀取 |

## 🎓 與 basler_mvc 的差異

| 項目 | basler_mvc | basler_pyqt6 |
|-----|------------|--------------|
| 配置管理器 | ✅ ConfigManager（熱重載） | ⚠️ 簡化版（無熱重載） |
| 配置結構 | 字典形式 | dataclass 形式 |
| 類型安全 | ❌ 無 | ✅ 有（dataclass） |
| JSON 支援 | ✅ 有 | ✅ 有 |
| 參數驗證 | ✅ 有 | ✅ 有 |

## 🚀 未來改進

- [ ] 實現配置熱重載（參考 basler_mvc/utils/config_manager.py）
- [ ] 添加配置變更回調機制
- [ ] 支援配置歷史和回滾
- [ ] 添加 GUI 配置編輯器

## ⚠️ 注意事項

1. **配置載入時機**: 配置在第一次調用 `get_config()` 時自動載入
2. **參數同步**: 修改配置後需調用 `save()` 才會持久化到 JSON 檔案
3. **類型安全**: 使用 dataclass 確保類型正確，避免運行時錯誤
4. **預設值**: 如果 JSON 檔案不存在，會自動使用 settings.py 中定義的預設值

## 📞 問題回報

如果發現配置相關問題，請檢查：

1. JSON 檔案格式是否正確
2. 參數值是否在有效範圍內
3. 配置是否通過驗證 (`validate_config()`)
4. 查看日誌輸出的配置載入信息

## 📚 相關文件

- `basler_mvc/config/settings.py` - MVC 版本的配置參考
- `basler_mvc/utils/config_manager.py` - 配置管理器參考實現
- `basler_pyqt6/core/detection.py` - 檢測控制器實現
- `basler_pyqt6/ui/widgets/debug_panel.py` - 調試面板實現

---

**最後更新**: 2025-01-13
**版本**: 1.0.0
**維護者**: Real-time Item Monitoring System Team
