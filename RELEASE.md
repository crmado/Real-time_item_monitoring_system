# 📦 打包與發布流程

**3 個步驟發布新版本**

---

## 🚀 發布新版本

### 1️⃣ 更新版本號

編輯 `basler_pyqt6/version.py`：

```python
__version__ = "2.0.2"  # ← 改這裡
BUILD_DATE = "2025-10-13"  # 更新日期
```

### 2️⃣ 打包應用

```bash
python scripts/build.py
```

**輸出位置：** `releases/BaslerVisionSystem_v{版本}_{時間戳}.zip`

### 3️⃣ 上傳到更新服務器

```bash
python scripts/release.py --notes "版本 2.0.2 - 修復 bug 和性能優化"
```

✅ 完成！客戶端將自動檢測到新版本。

---

## 🌐 首次設置更新服務器（只需一次）

### 1. 在服務器上安裝

```bash
# 上傳 update_server 目錄到服務器
scp -r update_server user@your-server.com:~/

# SSH 登入服務器
ssh user@your-server.com

# 安裝依賴
cd ~/update_server
pip install -r requirements.txt

# 啟動服務器
python app.py
# 或使用 gunicorn（生產環境）
./run_server.sh
```

### 2. 配置客戶端

編輯 `basler_pyqt6/version.py`：

```python
UPDATE_SERVER_URL = "http://your-server-ip:5000/api"
# 或使用域名（建議）
UPDATE_SERVER_URL = "https://updates.yourdomain.com/api"
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
# __version__ = "2.1.0"

# 2. 測試應用
python basler_pyqt6/main_v2.py

# 3. 打包
python scripts/build.py
# ✅ 輸出: releases/BaslerVisionSystem_v2.1.0_*.zip

# 4. 發布
python scripts/release.py --notes "新增物體追蹤功能，修復相機重連問題"
# ✅ 上傳完成！

# 5. 驗證
curl http://your-server.com:5000/api/updates/latest
# 應顯示版本 2.1.0

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
