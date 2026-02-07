# Assets 資源目錄

此目錄包含 Basler Vision System (C++ 版本) 的靜態資源。

## 目錄結構

```
assets/
├── setup_icon.ico      # Windows 安裝程式圖標
├── wizard_image.bmp    # 安裝精靈側邊圖片 (164x314)
├── wizard_small.bmp    # 安裝精靈標題圖片 (55x58)
└── README.md           # 本文件
```

## 檔案說明

| 檔案 | 用途 | 尺寸 |
|------|------|------|
| `setup_icon.ico` | Windows 安裝程式圖標 | 多尺寸 (16-256px) |
| `wizard_image.bmp` | Inno Setup 側邊橫幅 | 164 x 314 px |
| `wizard_small.bmp` | Inno Setup 標題圖片 | 55 x 58 px |

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
