# 更新指南

## 🔄 自動更新系統

系統會根據運行環境自動選擇更新方式：

### Rock 5B / 開發環境（Git 更新）

**自動更新**：
1. 應用內點擊：幫助 → 檢查更新
2. 如有更新會顯示提交日誌
3. 點擊「是」自動執行 `git pull`
4. 重啟應用生效

**手動更新**：
```bash
cd ~/Desktop/Real-time_item_monitoring_system
git pull
./run.sh
```

如果 requirements.txt 有變更：
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

### Windows/macOS/Linux 打包版本（OTA 更新）

**自動更新**：
1. 應用內點擊：幫助 → 檢查更新
2. 如有新版本會顯示更新說明
3. 點擊「下載並安裝」
4. 自動下載、安裝、重啟

**特點**：
- ✅ 自動下載新版本
- ✅ 驗證文件完整性（MD5）
- ✅ 自動備份舊版本
- ✅ 失敗時可回滾

---

## 🎯 更新模式檢測邏輯

```python
if getattr(sys, 'frozen', False):
    # 打包環境 → OTA 更新
    updater = OTAUpdater()
elif os.path.exists('.git'):
    # Git 倉庫 → Git 更新
    updater = GitUpdater()
else:
    # 無法自動更新 → 手動更新
    updater = None
```

---

## 📝 程式碼中使用更新器

```python
from basler_pyqt6.core.smart_updater import get_smart_updater

# 獲取更新器（單例模式）
updater = get_smart_updater()

# 檢查更新
update_info = updater.check_for_updates()

if update_info:
    mode = update_info['mode']  # 'git' 或 'ota'

    # 執行更新
    success = updater.perform_update(update_info, restart=True)
```

---

## 🔧 設定更新服務器

編輯 `basler_pyqt6/version.py`：

```python
# OTA 更新服務器 URL
UPDATE_SERVER_URL = "http://your-server.com:5000/api"

# 檢查更新間隔（秒）
UPDATE_CHECK_INTERVAL = 86400  # 24 小時
```

---

## 📊 更新流程對比

| 項目 | Git 更新 | OTA 更新 |
|------|---------|---------|
| **適用環境** | 開發/源碼環境 | 打包的二進制 |
| **更新速度** | 快（只下載差異） | 較慢（下載完整包） |
| **依賴更新** | 需手動 pip install | 已包含在包中 |
| **回滾** | `git reset --hard` | 自動備份 |
| **權限** | 需要 Git | 無特殊要求 |

---

## ⚠️ 注意事項

### Git 更新
- 確保沒有未提交的本地修改
- 有衝突時需手動解決
- Python 依賴變更需手動安裝

### OTA 更新
- 需要網絡連接
- 下載大小取決於應用大小
- Windows 可能需要管理員權限

---

更新日期：2025-10-23
