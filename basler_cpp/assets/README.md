# Assets 資源目錄

此目錄包含 Basler Vision System (C++ 版本) 的所有靜態資源。

## 目錄結構

```
assets/
├── icons/                # 應用程式圖標
│   ├── app_icon.png      # 應用程式主圖標 (256x256)
│   ├── app_icon_48.png   # 工具欄圖標 (48x48)
│   └── app_icon_32.png   # 小圖標 (32x32)
├── images/               # 圖片資源
│   ├── logo.png          # 應用程式 Logo
│   └── splash.png        # 啟動畫面
├── styles/               # 樣式資源
│   └── dark_theme.qss    # 深色主題樣式表
├── icon.ico              # Windows 安裝程式圖標
├── icon.icns             # macOS 應用程式圖標
└── README.md             # 本文件
```

## 圖標要求

### Windows (icon.ico)

- 包含多種尺寸: 16x16, 32x32, 48x48, 256x256
- 格式: ICO
- 色彩深度: 32-bit RGBA

### macOS (icon.icns)

- 包含多種尺寸: 16x16, 32x32, 128x128, 256x256, 512x512, 1024x1024
- 格式: ICNS
- 支援 Retina 解析度 (@2x)

### Linux

- 主要使用 PNG 格式
- 尺寸: 256x256 (hicolor 主題)

## 生成圖標

### 從 PNG 生成 ICO (Windows)

```bash
# 使用 ImageMagick
convert icon.png -define icon:auto-resize=256,48,32,16 icon.ico
```

### 從 PNG 生成 ICNS (macOS)

```bash
# 創建 iconset 目錄
mkdir icon.iconset
sips -z 16 16     icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32     icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64     icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256   icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512   icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   icon.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png
iconutil -c icns icon.iconset
```

## 使用方式

資源文件會在編譯時自動複製到應用程式目錄，並在安裝時包含在安裝包中。

### CMake 配置

在 `CMakeLists.txt` 中已配置自動複製資源：

```cmake
# 複製 assets 目錄
add_custom_command(TARGET ${PROJECT_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
    "${CMAKE_SOURCE_DIR}/assets"
    "$<TARGET_FILE_DIR:${PROJECT_NAME}>/assets"
)
```

### 程式碼中存取

```cpp
#include <QCoreApplication>
#include <QDir>

QString getAssetPath(const QString& filename) {
    return QDir(QCoreApplication::applicationDirPath())
           .filePath("assets/" + filename);
}
```

## 注意事項

1. 確保所有圖標都有透明背景
2. 使用 PNG-24 格式以獲得最佳品質
3. 避免使用超過必要尺寸的圖片以減少應用程式大小
4. 遵循平台設計指南（Windows Fluent Design、macOS Human Interface Guidelines）
