# 快速開始：多平台打包

> 🚀 **5 分鐘內完成自動化打包設置**

---

## 🎯 目標

使用 GitHub Actions 自動為 **Windows、macOS、Linux** 三個平台生成安裝程序。

---

## ✅ 前提檢查

確認以下文件已存在（應該都已經創建好了）：

```bash
✅ .github/workflows/build-release.yml    # GitHub Actions 配置
✅ installer/windows_installer.iss        # Windows 安裝程序配置
✅ scripts/build.py                       # 打包腳本（已更新）
✅ basler_pyqt6.spec                      # PyInstaller 配置
✅ requirements.txt                       # 依賴清單
✅ PACKAGING.md                           # 詳細打包指南
```

---

## 🚀 三步驟開始使用

### 步驟 1：提交代碼到 GitHub

```bash
# 添加新文件
git add .github/ installer/ PACKAGING.md QUICKSTART_PACKAGING.md scripts/build.py

# 提交
git commit -m "feat: 添加多平台自動打包支援

- 新增 GitHub Actions 工作流
- 新增 Windows Inno Setup 配置
- 更新 build.py 支援平台檢測
- 添加完整打包文檔"

# 推送
git push origin master
```

### 步驟 2：觸發自動構建

前往 GitHub 倉庫頁面：

1. 點擊 **Actions** 標籤
2. 選擇左側 **Build Multi-Platform Release**
3. 點擊右上角 **Run workflow** 按鈕
4. 填寫參數：
   - **版本號**: `2.0.3`（或您的版本號）
   - **是否創建 Release**: ✅ 勾選
5. 點擊綠色的 **Run workflow** 確認

### 步驟 3：等待並下載

⏱️ **等待時間**: 約 15-20 分鐘

完成後：
- 前往 **Releases** 標籤
- 找到最新的版本（例如 `v2.0.3`）
- 下載三個平台的安裝包：
  - `BaslerVision_Setup_v2.0.3.exe` (Windows)
  - `BaslerVision_v2.0.3_macOS.dmg` (macOS)
  - `BaslerVision_v2.0.3_Linux.AppImage` (Linux)

---

## 🎉 完成！

您現在已經有了三個平台的專業安裝包！

---

## 📋 下次發布新版本

1. **更新版本號**：
   ```bash
   vim basler_pyqt6/version.py
   # 修改 __version__ = "2.0.4"
   ```

2. **提交更改**：
   ```bash
   git add basler_pyqt6/version.py
   git commit -m "chore: 升級版本至 2.0.4"
   git push
   ```

3. **推送標籤觸發自動構建**：
   ```bash
   git tag -a v2.0.4 -m "Release version 2.0.4"
   git push origin v2.0.4
   ```

4. **自動構建**會在幾秒內開始，完成後自動創建 Release！

---

## 🛠️ 本地測試打包

如果需要在本地快速測試打包（不創建安裝程序）：

```bash
# macOS/Linux
python3 scripts/build.py --no-installer

# Windows
python scripts/build.py --no-installer

# 查看平台信息
python scripts/build.py --show-platform
```

**輸出位置**: `dist/BaslerVisionSystem/`

---

## ⚠️ 常見問題

### Q: GitHub Actions 構建失敗？

**A**: 查看錯誤日誌：
1. 前往 **Actions** 標籤
2. 點擊失敗的工作流運行
3. 查看紅色 ❌ 的步驟日誌

常見原因：
- 依賴安裝失敗 → 檢查 `requirements.txt`
- PyInstaller 錯誤 → 檢查 `basler_pyqt6.spec`
- 權限問題 → 確認倉庫 Actions 權限已啟用

### Q: 如何添加應用程式圖標？

**A**:
1. 準備 PNG 圖標（256x256）
2. 轉換為各平台格式：
   - Windows: `.ico`
   - macOS: `.icns`
   - Linux: `.png`
3. 放到 `resources/` 目錄
4. 更新配置文件中的圖標路徑
5. 重新打包

詳見 `resources/README.md`

### Q: Windows 安裝包需要簽名嗎？

**A**:
- **個人/內部使用**: 不需要
- **公開發布**: 建議簽名，避免 Windows Defender 警告
- **如何簽名**: 需要購買代碼簽名證書，參考 [Microsoft 文檔](https://docs.microsoft.com/windows/win32/seccrypto/cryptography-tools)

### Q: macOS 提示「應用程式已損壞」？

**A**: 用戶需要執行：
```bash
xattr -cr /Applications/BaslerVisionSystem.app
```

或者您需要：
1. 註冊 Apple Developer 帳號（$99/年）
2. 簽名應用程式
3. 進行公證（Notarization）

---

## 📚 更多信息

- **詳細打包指南**: 查看 `PACKAGING.md`
- **專案文檔**: 查看 `CLAUDE.md`
- **主要 README**: 查看 `README.md`

---

## 🎊 恭喜！

您已經完成了多平台打包的設置！

現在每次發布新版本，只需推送一個 Git 標籤，GitHub Actions 就會自動為您生成三個平台的專業安裝包。

**Happy Building! 🚀**
