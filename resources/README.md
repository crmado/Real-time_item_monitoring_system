# 資源文件目錄

此目錄用於存放應用程式的資源文件。

## 文件說明

### icon.ico
**用途**: Windows 安裝程序和應用程式圖標
**規格**:
- 格式：ICO
- 尺寸：256x256、128x128、48x48、32x32、16x16（多尺寸圖標）
- 工具：可使用 [IcoFX](https://icofx.ro/) 或 [GIMP](https://www.gimp.org/) 創建

**如何添加**：
1. 創建 PNG 格式的圖標（256x256）
2. 使用工具轉換為 ICO 格式
3. 放置到此目錄
4. 更新 `installer/windows_installer.iss` 中的路徑
5. 更新 `basler_pyqt6.spec` 中的 icon 參數

### icon.icns（可選）
**用途**: macOS 應用程式圖標
**規格**:
- 格式：ICNS
- 工具：macOS 內建 iconutil

**創建方法**：
```bash
# 1. 準備不同尺寸的 PNG 圖標
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

# 2. 轉換為 ICNS
iconutil -c icns icon.iconset
```

### icon.png
**用途**: Linux AppImage 圖標和通用圖標
**規格**:
- 格式：PNG
- 尺寸：256x256 或 512x512
- 透明背景

## 目前狀態

⚠️ **目前圖標尚未添加**

如果未提供圖標，打包過程將使用系統預設圖標或跳過圖標設置。

## 快速開始

1. **準備您的圖標**（PNG 格式，256x256 或更高）
2. **轉換為各平台格式**（使用上述工具）
3. **放置到此目錄**
4. **更新配置文件**中的圖標路徑
5. **重新打包應用程式**

## 其他資源

您也可以在此目錄存放：
- 啟動畫面圖片
- 應用程式背景圖
- 安裝程序橫幅圖
- 許可證文件
- 用戶手冊 PDF

---

**注意**: 圖標文件不會自動包含在版本控制中（可能較大），請根據需要添加到 `.gitignore`。
