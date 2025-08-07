# 跨平台 UI 一致性使用指南

## 概述

本指南介紹如何使用新的跨平台 UI 管理系統，確保應用程式在 Windows、macOS 和 Linux 上都有一致的外觀和使用體驗。

## 主要功能

### 1. 跨平台字體管理
- **自動字體檢測**：自動檢測可用字體並選擇最佳選項
- **字體回退機制**：當首選字體不可用時，自動使用備用字體
- **編碼處理**：防止中文字體亂碼問題
- **平台特定調整**：根據操作系統調整字體大小

### 2. 跨平台顏色管理
- **平台適配色彩**：針對不同平台優化顏色顯示
- **對比度增強**：確保在所有平台上都有良好的可讀性
- **動態顏色調整**：根據平台特性自動調整色彩飽和度和亮度

### 3. 統一 UI 組件
- **一致的外觀**：所有組件在不同平台上保持視覺一致性
- **平台原生感**：同時保留各平台的原生設計語言特點
- **智能佈局**：自動調整間距和尺寸以適應不同平台

## 快速開始

### 基本使用

```python
from basler_mvc.styles.theme_manager import ThemeManager

# 初始化主題管理器（自動啟用跨平台支援）
theme_manager = ThemeManager(root_window)

# 使用跨平台組件
button = theme_manager.create_cross_platform_button(
    parent=frame,
    text="開始監測",
    command=start_monitoring,
    button_type="primary"
)

label = theme_manager.create_cross_platform_label(
    parent=frame,
    text="當前計數",
    label_type="title"
)

entry = theme_manager.create_cross_platform_entry(
    parent=frame,
    textvariable=count_var
)
```

### 直接使用 UI 管理器

```python
from basler_mvc.styles.cross_platform_ui_manager import get_ui_manager

# 獲取 UI 管理器
ui_manager = get_ui_manager()

# 創建組件
button = ui_manager.create_button(parent, "按鈕文字", command_func)
label = ui_manager.create_label(parent, "標籤文字", "title")
frame = ui_manager.create_frame(parent, "card")
```

## 組件類型說明

### 按鈕類型 (button_type)
- `primary`: 主要操作按鈕（藍色）
- `success`: 成功操作按鈕（綠色）
- `warning`: 警告操作按鈕（橙色）
- `danger`: 危險操作按鈕（紅色）
- `secondary`: 次要操作按鈕（淺色）

### 標籤類型 (label_type)
- `title`: 標題文字（大字體，粗體）
- `subtitle`: 副標題文字（中字體）
- `body`: 正文文字（默認）
- `caption`: 說明文字（小字體，淺色）
- `mono`: 等寬字體文字

### 框架類型 (frame_type)
- `card`: 卡片樣式（白色背景，適合內容展示）
- `panel`: 面板樣式（有邊框，適合功能區域）
- `transparent`: 透明樣式（繼承父容器背景）

### 狀態顯示類型 (status_type)
- `info`: 信息狀態（藍色）
- `success`: 成功狀態（綠色）
- `warning`: 警告狀態（橙色）
- `error`: 錯誤狀態（紅色）

## 高級功能

### 安全文字處理

```python
# 防止編碼問題
safe_text = theme_manager.get_safe_text("可能包含特殊字符的文字")
label.configure(text=safe_text)
```

### 平台特定顏色

```python
# 獲取平台優化的顏色
primary_color = theme_manager.get_platform_color('primary_blue')
text_color = theme_manager.get_platform_color('text_primary')
```

### 平台特定字體

```python
# 獲取平台最佳字體
font_tuple = theme_manager.get_platform_font('primary', 14, 'bold')
widget.configure(font=font_tuple)
```

### 動態樣式應用

```python
# 將跨平台樣式應用到現有組件
theme_manager.apply_cross_platform_style(existing_button, 'button')
theme_manager.apply_cross_platform_style(existing_entry, 'entry')
```

## 平台差異說明

### Windows
- 使用微軟雅黑或 Segoe UI 字體
- 稍微增加顏色對比度
- 使用較小的圓角和間距
- 支援 Windows Accent Color

### macOS
- 使用 SF Pro Display 或 PingFang 字體
- 保持 Apple 原生設計風格
- 使用更大的圓角和間距
- 支援 macOS 原生窗口樣式

### Linux
- 使用 Noto Sans 或 Source Han Sans 字體
- 增強對比度以適應不同主題
- 支援 GTK 主題色彩
- 靈活的邊框和間距配置

## 故障排除

### 字體問題
1. **字體顯示異常**：檢查系統是否安裝了推薦字體
2. **中文亂碼**：確保系統編碼設置正確
3. **字體太小/太大**：系統會自動調整，如需手動調整可修改字體大小參數

### 顏色問題
1. **顏色對比度不足**：系統會自動調整，如仍有問題可檢查顯示器設置
2. **顏色顯示不一致**：確保使用的是平台特定顏色函數

### 佈局問題
1. **組件間距不當**：使用平台特定的框架和容器
2. **組件大小異常**：檢查是否正確使用了跨平台組件創建函數

## 最佳實踐

1. **優先使用跨平台組件**：使用 `create_cross_platform_*` 方法而不是直接創建 tkinter 組件
2. **文字安全處理**：所有顯示的文字都應該通過 `get_safe_text()` 處理
3. **顏色一致性**：使用 `get_platform_color()` 獲取平台特定顏色
4. **字體一致性**：使用 `get_platform_font()` 獲取平台最佳字體
5. **定期測試**：在不同平台上測試應用程式的外觀和功能

## 更新現有程式碼

### 從舊版本遷移

```python
# 舊版本
button = tk.Button(parent, text="按鈕", bg="#007AFF", fg="white")

# 新版本
button = theme_manager.create_cross_platform_button(
    parent, "按鈕", button_type="primary"
)
```

```python
# 舊版本
label = tk.Label(parent, text="標題", font=("Arial", 14, "bold"))

# 新版本
label = theme_manager.create_cross_platform_label(
    parent, "標題", label_type="title"
)
```

## 支援和回饋

如果在使用過程中遇到問題或有改進建議，請：

1. 檢查日誌輸出中的平台資訊
2. 確認是否正確初始化了主題管理器
3. 驗證組件創建時的參數是否正確
4. 在不同平台上進行測試

通過使用這個跨平台 UI 系統，您的應用程式將在所有支援的操作系統上提供一致且優質的用戶體驗。
