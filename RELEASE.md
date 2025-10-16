# 📦 打包與發布流程

**3 個步驟發布新版本**（使用 SFTP 直接上傳）

---

## 🚀 發布新版本

### 1️⃣ 更新版本號

編輯 `basler_pyqt6/version.py`：

```python
__version__ = "2.0.3"  # ← 改這裡
BUILD_DATE = "2025-10-16"  # 更新日期
```

### 2️⃣ 打包應用

```bash
python scripts/build.py
```

**輸出位置：** `releases/BaslerVisionSystem_v{版本}_{時間戳}.zip`

### 3️⃣ 上傳到更新服務器（SFTP）

```bash
python scripts/release.py --notes "版本 2.0.2 - 修復 bug 和性能優化"
```

**腳本會自動：**
- ✅ 讀取 `.vscode/sftp.json` 配置
- ✅ 通過 SFTP 上傳 ZIP 文件
- ✅ 在遠端服務器解壓縮
- ✅ 更新 `update_manifest.json` 版本清單
- ✅ 顯示部署結果

✅ 完成！客戶端將自動檢測到新版本。

---

## 🌐 首次設置 SFTP 配置（只需一次）

### 1. 安裝 paramiko 模組

```bash
pip install paramiko
```

### 2. 配置 SFTP 連接

編輯 `.vscode/sftp.json`：

```json
{
    "name": "Basler Update Server",
    "host": "your-server.com",
    "port": 2224,
    "username": "fileuser",
    "password": "your_password",
    "remotePath": "/home/fileuser/releases"
}
```

### 3. 測試連接

```bash
# 顯示版本信息
python scripts/release.py --version

# 測試上傳（會自動連接並上傳最新的 release）
python scripts/release.py --notes "測試版本"
```

---

## 📝 打包腳本說明

### `scripts/build.py`

**功能：**
- 清理舊的構建文件
- 使用 PyInstaller 打包應用
- 創建發布包 ZIP
- 計算 MD5 校驗值
- 生成版本信息 JSON

**選項：**

```bash
# 完整打包（推薦）
python scripts/build.py

# 跳過清理（加快構建）
python scripts/build.py --skip-clean

# 只打包，不創建 ZIP
python scripts/build.py --no-package
```

### `scripts/release.py`

**功能：**
- 自動找到最新的發布包
- 上傳到更新服務器
- 更新版本信息

**選項：**

```bash
# 上傳最新的包
python scripts/release.py --notes "更新說明"

# 指定特定文件
python scripts/release.py --file releases/xxx.zip --notes "測試版本"

# 指定服務器地址
python scripts/release.py --server http://test-server.com:5000/api --notes "內部測試"
```

---

## ⚙️ PyInstaller 配置重點

### 資料檔案（Data Files）

PyInstaller 只會自動打包 Python 程式碼，**非 Python 檔案需要在 `basler_pyqt6.spec` 中明確指定**：

```python
datas = [
    # 配置檔案（必要）
    ('basler_pyqt6/config/detection_params.json', 'config'),

    # 測試資料目錄（可選，約 1.5GB）
    # ('basler_pyqt6/testData', 'testData'),  # 正式版可註解掉
]
```

**注意事項：**
- `detection_params.json` 是必要的，包含所有檢測參數配置
- `testData/` 約 1.5GB，內部測試版可保留，正式版建議註解掉以減小安裝包大小
- 如果添加了新的配置檔案或資源（圖示、樣式表等），記得加入 `datas` 列表

### 路徑處理（Path Handling）

打包後應用執行時，`__file__` 和相對路徑會失效。**必須使用 PyInstaller 的特殊路徑處理**：

```python
import sys
from pathlib import Path

def _get_project_root() -> Path:
    """獲取專案根目錄，支援開發和打包環境"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包環境
        # sys._MEIPASS 是資源被解壓的臨時目錄
        return Path(sys._MEIPASS)
    else:
        # 開發環境
        return Path(__file__).parent.parent

PROJECT_ROOT = _get_project_root()
config_file = PROJECT_ROOT / "config" / "detection_params.json"
```

**已實作位置：**
- `basler_pyqt6/config/settings.py` - 配置系統路徑處理
- `basler_pyqt6/updater.py` - 更新程式路徑處理

**檢查清單：**
- ✅ 所有讀取檔案的程式碼都使用 `PROJECT_ROOT` 或 `sys._MEIPASS`
- ✅ 不要使用硬編碼路徑（如 `"./config/xxx.json"`）
- ✅ 測試時使用 `--onedir` 模式（預設），比 `--onefile` 啟動更快

---

## 🔄 客戶端自動更新

客戶端會自動檢測更新（在 `basler_pyqt6/updater.py` 中實現）。

### 手動觸發更新檢查

在你的應用中添加：

```python
from basler_pyqt6.updater import check_for_updates

# 檢查更新
update_info = check_for_updates()
if update_info:
    print(f"發現新版本: {update_info['version']}")
    # 顯示更新對話框
```

### 更新服務器 API

更新服務器提供以下端點：

- `GET /api/updates/latest` - 獲取最新版本信息
- `GET /api/updates/download/<filename>` - 下載更新包
- `POST /api/updates/upload` - 上傳新版本（發布腳本使用）
- `GET /api/updates/list` - 列出所有版本
- `GET /api/health` - 健康檢查

---

## 🐛 故障排除

### 打包失敗

```bash
# 檢查依賴
pip install -r requirements.txt

# 清理後重新打包
rm -rf build dist
python scripts/build.py
```

### 打包後找不到配置檔案

**錯誤訊息**：`FileNotFoundError: config/detection_params.json`

**原因**：
1. 資料檔案未加入 `basler_pyqt6.spec` 的 `datas` 列表
2. 程式碼中使用了相對路徑而非 `sys._MEIPASS`

**解決方法**：
```python
# 1. 檢查 basler_pyqt6.spec
datas = [
    ('basler_pyqt6/config/detection_params.json', 'config'),  # ← 確認存在
]

# 2. 檢查程式碼使用正確的路徑處理
PROJECT_ROOT = _get_project_root()  # 使用動態路徑函數
config_file = PROJECT_ROOT / "config" / "detection_params.json"
```

### 打包後 UI 顯示異常

**可能原因**：
- 新增的 UI 模組未被自動追蹤
- 動態導入的模組需要添加到 `hiddenimports`

**解決方法**：
```python
# basler_pyqt6.spec
hidden_imports = [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    # 如果有動態導入，添加在這裡
]
```

### 無法連接更新服務器

```bash
# 測試服務器是否運行
curl http://your-server.com:5000/api/health

# 檢查防火牆（確保端口 5000 開放）
# Linux: sudo ufw allow 5000
# 或使用 Nginx 反向代理
```

### 上傳失敗

```bash
# 檢查服務器磁盤空間
df -h

# 檢查文件大小限制
# 編輯 update_server/app.py
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB
```

---

## 📚 完整流程範例

```bash
# 1. 開發完成，更新版本號
vim basler_pyqt6/version.py
# __version__ = "2.0.3"
# BUILD_DATE = "2025-10-16"

# 2. 測試應用
python basler_pyqt6/main_v2.py

# 3. 打包
python scripts/build.py
# ✅ 輸出: releases/BaslerVisionSystem_v2.0.3_*.zip

# 4. 發布
python scripts/release.py --notes "實作動態方法面板切換，支援多種檢測方法"
# ✅ 上傳完成！

# 5. 驗證
curl http://your-server.com:5000/api/updates/latest
# 應顯示版本 2.0.3

# 6. 客戶端自動檢測到更新 ✨
```

---

## 📁 目錄結構

```
專案根目錄/
├── basler_pyqt6/
│   ├── version.py          # 版本配置
│   └── updater.py          # 自動更新模組
├── scripts/
│   ├── build.py            # 打包腳本
│   └── release.py          # 發布腳本
├── update_server/
│   ├── app.py              # 更新服務器
│   ├── requirements.txt    # 服務器依賴
│   └── run_server.sh       # 啟動腳本
├── releases/               # 打包輸出目錄
├── basler_pyqt6.spec      # PyInstaller 配置
└── RELEASE.md             # 本文檔
```

---

## 🎯 快速命令參考

```bash
# 打包
python scripts/build.py

# 發布
python scripts/release.py --notes "更新說明"

# 啟動更新服務器
cd update_server && python app.py

# 檢查最新版本
curl http://your-server.com:5000/api/updates/latest

# 列出所有版本
curl http://your-server.com:5000/api/updates/list
```

---

**就這麼簡單！** 🎉

更多服務器部署細節請參閱 `update_server/README.md`
