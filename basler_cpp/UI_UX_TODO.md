# UI/UX 改善 Todolist

> 最後更新：2026-02-24
> 分支：feature/cpp-rewrite → master
> 專案：Basler 工業視覺系統 v2.0 (Qt6 C++)

---

## 目前 UI 架構（快速參考）

```
MainWindow
├── 左側  VideoDisplayWidget（主視窗，60%）
└── 右側  QTabWidget（450-550px）
    ├── Tab 1  ⚙️ 設定
    │   ├── CameraControlWidget
    │   └── RecordingControlWidget
    ├── Tab 2  📊 監控（預設打開）
    │   ├── 原始畫面預覽（180px）
    │   ├── PackagingControlWidget
    │   │   ├── PartSelectorWidget
    │   │   ├── MethodSelectorWidget
    │   │   └── QStackedWidget
    │   │       ├── CountingMethodPanel
    │   │       └── DefectDetectionMethodPanel
    │   └── SystemMonitorWidget
    └── Tab 3  🛠️ 調試
        ├── 參數鎖定 checkbox
        ├── 7 個參數組（面積/背景/邊緣/形態/ROI/光柵/性能）
        ├── YOLO 控制
        ├── 調試視圖
        ├── 視頻控制
        └── 操作按鈕（重置/儲存/載入/重置計數）
```

---

## 🔴 優先修復（影響基本使用）

### P0 — Bug / 功能缺失

- [x] **瑕疵統計未連接**（2026-02-24）
  `onDefectStatsUpdated(double, int, int)` 已在 `main_window.h` 宣告，
  但 `connectDetectionSignals()` 從未連接，`DefectDetectionMethodPanel::updateStats()` 永遠不會被呼叫。
  → 已新增 `DetectionController::defectStatsUpdated` 信號（含 passCount/failCount 計數器）、
    `resetDefectStats()` slot，在傳統計數與 YOLO 計數兩條路徑均 emit 信號，
    並連接至 `MainWindow::onDefectStatsUpdated` → `PackagingControlWidget::updateDefectStats` →
    `DefectDetectionMethodPanel::updateStats()`。`onClearDefectStats()` 改用 `resetDefectStats()` 而非全量 reset。

- [x] **System Monitor 在 Windows 未實作**（2026-02-23）
  `system_monitor.cpp` 的 CPU/記憶體讀取只有 macOS/Linux 實作，Windows 會顯示 0%。
  → 已加入 `#define NOMINMAX` + `GetSystemTimes()` / `GlobalMemoryStatusEx()` 分支

- [x] **調試視圖（二值化預覽）永遠空白**（2026-02-23）
  `DebugPanelWidget::updateDebugImage()` 已實作，但 `MainWindow::updateDisplay()` 中有
  `// TODO: 偵錯圖像功能尚未實現`，從未呼叫。
  → 已在 `processFrame()` 後，若啟用調試視圖，將 `lastDebugFrame()` 傳給 `m_debugPanel->updateDebugImage()`

---

## 🟠 短期改善（1-2 次 session 可完成）

### P1 — 交互體驗

- [x] **Debug Panel 參數缺少數值顯示**（2026-02-23）
  目前所有 SpinBox 已能調整，但沒有「當前值已生效」的視覺反饋。
  → 已在 `connectDebugSignals()` 中，對 minArea/maxArea/bgVarThreshold/cannyLow/cannyHigh 調整後
    在 StatusBar 顯示 `"xxx = N 已套用"` 提示

- [x] **影片載入後 Debug Panel 應自動同步當前配置值**（2026-02-23）
  載入影片後 `m_isDetecting = true`，但 Debug Panel 的 SpinBox 值是 UI 初始值，
  不一定反映 `DetectionController` 實際使用的值（特別是從 JSON 載入後）。
  → 已在 `onLoadVideo()` 成功載入後呼叫 `m_debugPanel->syncFromConfig()`

- [x] **計數面板：包裝完成後缺少明顯視覺提示**（2026-02-23）
  目前只彈 `QMessageBox`，操作體驗不好。
  → 已在 `CountingMethodPanel` 加入 `m_completionOverlay` QLabel，顯示「✅ 包裝完成！」，4 秒後自動消失

- [x] **錄影統計（幀數/時長）未即時更新**（2026-02-23）
  `RecordingControlWidget::updateStats()` 已實作，但 `MainWindow` 從未呼叫它。
  → 已在 `connectRecordingSignals()` 連接 `VideoRecorder::frameWritten` →
    `m_recordingControl->updateStats(frames, duration)`

- [x] **載入設定後 UI 不刷新**（2026-02-23）
  `onLoadConfig()` 只更新 `Settings`，但所有 SpinBox/Slider 仍顯示舊值。
  → 已在 `onLoadConfig()` 後呼叫 `m_debugPanel->syncFromConfig()`

---

## 🟡 中期改善（功能增強）

### P2 — 功能補強

- [ ] **ROI 視覺化拖拽編輯器**
  目前只能在 Debug Panel 輸入 X/Y/W/H 數字，不直覺。
  → 建議：在 `VideoDisplayWidget` 上覆蓋一個可拖拽的矩形，讓用戶直接在畫面上框選 ROI
  → 實作提示：`VideoDisplayWidget::clicked(QPoint)` 信號已存在，可延伸為 drag 事件

- [ ] **光柵線位置可視化拖拽**
  目前光柵線只能輸入 ratio（0.0-1.0）數字，不直覺。
  → 建議：在影像上顯示水平線時，讓用戶點擊拖拽線的位置來調整

- [ ] **參數預設模板（Profile）**
  不同零件/場景需要完全不同的一組參數，切換很麻煩。
  → 建議：在 Debug Panel 頂部加 Profile 下拉選單（如「小螺絲」「大齒輪」）
  → 每個 profile 是一組 JSON，`Settings::load()` 支援指定路徑可複用

- [ ] **歷史計數趨勢迷你圖**
  在 `CountingMethodPanel` 計數旁加一個小折線圖，顯示最近 N 包的計數速率趨勢
  → 可用 QPainter 自繪，不需外部庫

- [x] **鍵盤快捷鍵**（2026-02-24）
  常用操作應有快捷鍵：
  | 快捷鍵 | 功能 |
  |--------|------|
  | Space | 播放/暫停視頻 |
  | ← / → | 上一幀/下一幀 |
  | Ctrl+S | 儲存設定（已在 MenuBar） |
  | Ctrl+R | 開始/停止錄製 |
  | F5 | 重置計數 |
  | F11 | 全螢幕切換 |
  → 已用 `QShortcut`（`Qt::WindowShortcut`）實作，SpinBox/Button 聚焦時自然優先消費

- [x] **StatusBar 強化**（2026-02-24）
  目前 StatusBar 只有文字，建議加入：
  - 偵測到的物件數（即時）→ 已加，`processFrame()` 每幀更新
  - 當前 ROI 尺寸 → 已加，顯示 `ROI: W×H` 或 `ROI: 關閉`
  - 背景減除器狀態 → 已加，`背景: 學習 N%` / `背景: 穩定`（綠/黃色標示）

---

## 🔵 長期改善（架構/大功能）

### P3 — 大型功能

- [ ] **全螢幕影像模式**
  按 F11 或雙擊影像，讓 `VideoDisplayWidget` 撐滿全螢幕，
  疊加最少量的 HUD 資訊（計數、FPS、光柵線）

- [ ] **演算法中間結果視覺化**
  在調試模式下，左側主畫面可切換顯示：
  - 原始幀
  - 背景減除結果（前景遮罩）
  - Canny 邊緣
  - 形態學處理後結果
  - 最終合併結果
  → 建議用 QComboBox 或 QButtonGroup 切換

- [ ] **多視窗分割顯示**
  並排顯示原始幀 + 處理結果（4格或2格），方便調參時比對
  → 可用 `QSplitter` 實作，最多 2x2 格

- [ ] **操作日誌面板**
  在 Tab 3 增加一個摺疊式的操作日誌區域，顯示最近的：
  - 參數變更記錄（什麼時間改了什麼值）
  - 計數事件（第幾幀觸發計數）
  - 錯誤訊息

- [ ] **設定向導（第一次使用）**
  首次啟動時顯示 QWizard，引導用戶：
  1. 連接相機或選擇測試視頻
  2. 設定 ROI 區域
  3. 調整面積閾值（預覽效果）
  4. 設定目標計數

- [ ] **導出報告**
  每次包裝完成後可以 export 一份 CSV/PDF，包含：
  - 時間戳、目標數量、實際計數
  - 各參數設定值
  - 零件類型/方法

---

## 🎨 UI 樣式優化

### 視覺一致性

- [ ] **統一按鈕樣式**
  目前各 widget 的按鈕 stylesheet 略有不一致（顏色、圓角、padding）
  → 建議：抽取共用 stylesheet 到 `include/ui/style.h` 常數

- [ ] **響應式佈局**
  視窗縮小到 1400px 以下時，右側面板可自動摺疊成更緊湊的版本

- [ ] **Dark / Light 主題切換**
  目前硬編碼深藍色主題，工廠環境有時需要高對比度白色背景
  → 建議：定義 2 套 QPalette，選單可切換

- [ ] **字體大小設定**
  工業環境有時要求大字體（操作員距離螢幕較遠）
  → 建議：在設定中加入 font scale 選項（100% / 125% / 150%）

---

## ✅ 已完成

### 2026-02-24（Session 3）

- [x] P2: 鍵盤快捷鍵（Space/←/→/Ctrl+R/F5/F11，`QShortcut` 實作）
- [x] P2: StatusBar 強化（物件數、ROI 尺寸、背景穩定度，每幀更新）
- [x] P0: 瑕疵統計信號鏈完整連接（`DetectionController::defectStatsUpdated` → `MainWindow` → `DefectDetectionMethodPanel::updateStats`）
  - 新增 `defectStatsUpdated(double, int, int)` 信號、`m_defectPassCount/m_defectFailCount` 計數器
  - 新增 `resetDefectStats()` slot（不影響計數/追蹤，只清瑕疵統計）
  - 傳統 MOG2 與 YOLO 兩條計數路徑均同步 emit
  - `onClearDefectStats()` 改為精確重置（不再 reset 整個 DetectionController）

### 2026-02-23（Session 2）

- [x] P0: System Monitor Windows CPU/RAM 實作（`GetSystemTimes` / `GlobalMemoryStatusEx`，`NOMINMAX` 修正）
- [x] P0: 調試視圖二值化預覽（`lastDebugFrame()` → `processFrame()` 中傳給 `m_debugPanel`）
- [x] P1: Debug Panel 關鍵參數調整後在 StatusBar 顯示「已套用」反饋
- [x] P1: 影片載入後 `syncFromConfig()` 自動同步 Debug Panel
- [x] P1: `onLoadConfig()` 後 `syncFromConfig()` 刷新 UI
- [x] P1: 錄影統計即時更新（連接 `frameWritten` → `updateStats`）
- [x] P1: 計數完成大字提示（`m_completionOverlay` QLabel，4 秒自動消失）

### 2026-02-23（Session 1）

- [x] Debug Panel 所有參數即時同步到 DetectionController
- [x] 補連 roiEnabledChanged / gateHistoryFramesChanged / gateLinePositionChanged
- [x] 補連 resetTotalCount / resetParams / saveConfig / loadConfig 按鈕
- [x] 移除 6 個 dead private slot
- [x] 新增 setBgHistory / setCannyThresholds / setMorphParams setter
- [x] 參數鎖定 checkbox（預設鎖定，防止滑鼠滾輪誤改）
- [x] 影片載入後自動啟用檢測（`m_isDetecting = true`）
- [x] 視頻控制 6 個信號連接（播放/暫停/上下幀/跳轉/截圖）

---

## 開發注意事項

### 新增 Widget 的標準流程

1. `include/ui/widgets/新widget.h` — 宣告，信號/槽清楚列出
2. `src/ui/widgets/新widget.cpp` — 實作，StyleSheet 跟現有一致
3. `main_window.h` — 加成員變數
4. `main_window.cpp::setupUi()` — 建立並加入佈局
5. `main_window.cpp::connect*Signals()` — 連接信號

### StyleSheet 色票

```
背景深色  #0a0e27
面板背景  #1a1f3d
邊框      #1f3a5f
主色青    #00d4ff
成功綠    #00ff80
警告黃    #ffcc00
錯誤紅    #ff4444
文字白    #e0e6f1
```

### 線程安全規則

- 所有 UI 更新必須在主線程（用 `Qt::QueuedConnection` 或 `QMetaObject::invokeMethod`）
- `VideoDisplayWidget::displayFrame()` 內部已有 mutex，可直接從任意線程呼叫
