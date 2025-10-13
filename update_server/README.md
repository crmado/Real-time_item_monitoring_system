# Basler Vision System - 更新服務器

自動更新服務器，提供版本檢查和應用更新下載服務。

## 功能

- ✅ 版本檢查 API
- ✅ 更新包上傳
- ✅ 更新包下載
- ✅ MD5 校驗
- ✅ 多版本管理

## 安裝

```bash
cd update_server
pip install -r requirements.txt
```

## 運行

### 開發模式

```bash
python app.py
```

### 生產模式

```bash
chmod +x run_server.sh
./run_server.sh
```

或使用 gunicorn 直接運行：

```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
```

## API 端點

### 1. 獲取最新版本

```
GET /api/updates/latest
```

**Query 參數：**
- `build_type` (可選): 構建類型（release, beta, alpha）

**響應範例：**
```json
{
  "version": "2.1.0",
  "download_url": "http://server/api/updates/download/file.zip",
  "file_size": 123456789,
  "md5": "abc123...",
  "release_notes": "更新說明",
  "publish_date": "2025-01-01T12:00:00"
}
```

### 2. 下載更新包

```
GET /api/updates/download/<filename>
```

### 3. 上傳新版本

```
POST /api/updates/upload
```

**Form 數據：**
- `file`: ZIP 文件（必需）
- `version`: 版本號（必需）
- `build_type`: 構建類型（可選）
- `md5`: MD5 值（可選）
- `release_notes`: 發布說明（可選）

### 4. 列出所有版本

```
GET /api/updates/list
```

### 5. 健康檢查

```
GET /api/health
```

## 部署到生產服務器

### 使用 systemd

創建服務文件 `/etc/systemd/system/basler-update-server.service`：

```ini
[Unit]
Description=Basler Vision Update Server
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/update_server
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

啟動服務：

```bash
sudo systemctl daemon-reload
sudo systemctl start basler-update-server
sudo systemctl enable basler-update-server
sudo systemctl status basler-update-server
```

### 使用 Nginx 反向代理

配置 Nginx：

```nginx
server {
    listen 80;
    server_name your-update-server.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 500M;
    }
}
```

## 目錄結構

```
update_server/
├── app.py                    # 主應用
├── requirements.txt          # Python 依賴
├── run_server.sh            # 運行腳本
├── releases/                # 發布包存儲目錄
└── releases_metadata.json   # 版本元數據
```

## 安全建議

1. **使用 HTTPS**: 在生產環境中使用 SSL/TLS 加密
2. **添加認證**: 為上傳 API 添加 API Key 或 Token 認證
3. **限制訪問**: 使用防火牆限制上傳端點的訪問
4. **定期備份**: 備份 releases 目錄和元數據文件

## 故障排除

### 上傳失敗

- 檢查文件大小是否超過限制（默認 500MB）
- 檢查磁盤空間是否充足
- 檢查文件權限

### 無法訪問

- 檢查防火牆設置
- 檢查服務是否運行：`systemctl status basler-update-server`
- 檢查日誌：`journalctl -u basler-update-server -f`
