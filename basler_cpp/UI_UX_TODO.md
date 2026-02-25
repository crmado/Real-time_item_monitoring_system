# UI/UX 改善 Todolist

> 最後更新：2026-02-24（Session 10 — 代碼審計 + 警告清零）
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

- [x] **ROI 視覺化拖拽編輯器**（2026-02-24）
  目前只能在 Debug Panel 輸入 X/Y/W/H 數字，不直覺。
  → Debug Panel ROI 組加入「✎ 在畫面上框選 ROI」按鈕
  → 點擊後主畫面進入框選模式（游標變十字、藍色虛線邊框提示）
  → 拖拽完成後自動退出框選模式，更新 Settings / DetectionController / SpinBox
  → `roiSelected(x,y,w,h)` 信號在影像原始座標系發出，完整信號鏈閉合

- [x] **光柵線位置可視化點擊設定**（2026-02-24）
  目前光柵線只能輸入 ratio（0.0-1.0）數字，不直覺。
  → Debug Panel 光柵組加入「🎯 點擊畫面設定光柵線」按鈕
  → 點擊後主畫面進入點擊模式（黃色虛線邊框提示、游標變十字）
  → 滑鼠懸停時顯示水平預覽線（黃色虛線）並即時顯示 ratio 數值
  → 點擊完成後自動退出模式，更新 Settings / DetectionController / SpinBox
  → ESC 可取消（與 ROI 框選模式共用 ESC 快捷鍵）

- [x] **參數預設模板（Profile）**（2026-02-24）
  不同零件/場景需要完全不同的一組參數，切換很麻煩。
  → Debug Panel 頂部新增「📋 參數預設模板」群組（不受參數鎖定影響）
  → QComboBox 列出 AppDataLocation/profiles/ 目錄內的所有 JSON 模板
  → 「另存新模板」：QInputDialog 輸入名稱 → 序列化 detection+gate 為 JSON
  → 「載入」：反序列化 → 更新 Settings → syncFromConfig() → emit profileLoaded()
  → MainWindow 收到 profileLoaded() 立即將所有參數套用到 DetectionController
  → 「刪除」：確認對話框後移除 JSON 檔、刷新列表
  → 同步修正 syncFromConfig() 空 stub，完整實作 SpinBox 靜默更新（blockSignals）

- [x] **歷史計數趨勢迷你圖**（2026-02-24）
  在 `CountingMethodPanel` 計數旁加一個小折線圖，顯示最近 N 包的計數速率趨勢
  → `CountTrendWidget`（QPainter 自繪，70px 高）定義在 .cpp 內，不新增檔案
  → 每包完成時記錄速率（件/秒）= targetCount / elapsed_seconds，最多保留 20 點
  → 折線 + 填充面積 + 最新速率標籤 + Y 軸 max/min 標籤
  → `setPackagingState(true)` 記錄開始時間戳，`showPackagingCompleted()` 計算並推入資料點

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

- [x] **全螢幕影像模式**（2026-02-24）
  按 F11 或雙擊影像，讓 `VideoDisplayWidget` 撐滿全螢幕，
  疊加最少量的 HUD 資訊（計數、FPS、光柵線）
  → F11 / 雙擊 / ESC 三種觸發方式
  → 進入全螢幕：隱藏右側 QTabWidget + showFullScreen() + 啟用 HUD
  → HUD overlay：左上角半透明面板顯示計數 + FPS，黃色虛線光柵線
  → `m_controlPanel` 提升為成員變數，`toggleFullscreenMode()` 統一管理

- [x] **演算法中間結果視覺化**（2026-02-24）
  在調試模式下，左側主畫面可切換顯示：
  - 原始幀
  - 背景減除結果（前景遮罩）
  - Canny 邊緣
  - 形態學處理後結果
  - 最終合併結果
  → `DetectionController` 在 `standardProcessing()` 中保存 `m_lastFgMask`、`m_lastCannyEdges`、
    `m_lastCombined`、`m_lastDebugFrame`，線程安全 clone() 存取
  → `DebugPanelWidget` 調試視圖區塊加入 QComboBox（5 選項）
  → 勾選「顯示調試視圖」後 ComboBox 才啟用；取消勾選自動重設為原始幀（mode=0）
  → `MainWindow::updateDisplay()` 依 `m_debugViewMode` 取中間 Mat，灰階自動轉 BGR 後顯示

- [x] **多視窗分割顯示**（2026-02-24）
  並排顯示原始幀 + 處理結果（2格），方便調參時比對
  → `m_displaySplitter`（QSplitter 水平）包裝 `m_videoDisplay` + `m_videoDisplay2`
  → 左面板：選定視圖（由 debugViewMode ComboBox 控制）
  → 右面板：互補幀（debugViewMode=0 時顯示原始幀；否則顯示最終檢測結果）
  → F9 快捷鍵 + Debug Panel「⊞ 分割顯示」按鈕切換
  → 全螢幕模式時自動隱藏右面板，退出全螢幕後自動恢復

- [x] **操作日誌面板**（2026-02-24）
  在 Tab 3 調試視圖下方加入摺疊式操作日誌面板：
  - 時間戳（HH:mm:ss）+ 色彩分級：參數變更=青色、計數=綠色、錯誤=紅色
  - 自動記錄 8 種關鍵參數變更（minArea/maxArea/bgVarThreshold/canny/gateLineRatio/ROI/profileLoaded）
  - 計數事件：MainWindow `onCountChanged()` → `logCountEvent(count, frame)`
  - 錯誤訊息：相機/錄影錯誤自動寫入日誌
  - `▼/▶` 按鈕摺疊/展開；清除按鈕清空；`setMaximumBlockCount(100)` 自動修剪

- [x] **設定向導（第一次使用）**（2026-02-24）
  首次啟動時顯示 QWizard，引導用戶：
  1. 連接相機或選擇測試視頻（說明頁）
  2. 設定面積閾值與背景敏感度（SpinBox 直接套用）
  3. 設定目標計數
  → `SetupWizard : QWizard` 4 頁面，`isFirstRun()` 讀取 QSettings，
    Finish 後自動 `save()` 並設 `wizardDone=true`，延遲 500ms 顯示避免視窗未渲染

- [x] **導出報告（CSV）**（2026-02-24）
  每次包裝完成後自動 export CSV，包含：
  - 時間戳、零件類型 ID、檢測方法 ID、目標數量、實際計數
  - 耗時（秒）、速率（件/秒）、minArea/maxArea/bgVarThreshold/canny 參數
  → `Documents/BaslerReports/report_YYYYMMDD.csv`（當天累積追加）
  → StatusBar 顯示儲存路徑；移除了原來干擾操作流程的 QMessageBox

---

## 🎨 UI 樣式優化

### 視覺一致性

- [x] **統一按鈕樣式**（2026-02-24）
  目前各 widget 的按鈕 stylesheet 略有不一致（顏色、圓角、padding）
  → 已建立 `include/ui/style.h`：`primaryBtn()` / `successBtn()` / `dangerBtn()` /
    `warningBtn()` / `secondaryBtn()` / `toolBtn()` + 色票常量（BG_DARK/SUCCESS/etc.）
  → 新 Widget 可直接 `#include "ui/style.h"` 並呼叫 `Style::primaryBtn()` 取得一致樣式

- [x] **響應式佈局**（2026-02-24）
  視窗縮小到 1400px 以下時，右側面板可自動摺疊成更緊湊的版本
  → 已覆寫 `MainWindow::resizeEvent()`：寬度 < 1200px 時自動隱藏 `m_controlPanel`，
    全螢幕模式下不觸發（`m_isFullscreenMode` 保護）

- [x] **Dark / Light 主題切換**（2026-02-24）
  目前硬編碼深藍色主題，工廠環境有時需要高對比度白色背景
  → 已在「檢視(&V)」選單加入「主題」子選單（深色/淺色，QActionGroup 互斥）
  → 淺色：`qApp->setStyleSheet()` 覆蓋主框架元素（QMainWindow/MenuBar/TabWidget/StatusBar 等）
  → 偏好儲存於 QSettings，啟動時自動套用；注意 widget 層級 StyleSheet 有優先權

- [x] **字體大小設定**（2026-02-24）
  工業環境有時要求大字體（操作員距離螢幕較遠）
  → 已在「檢視(&V)」選單加入「字體大小」子選單（100% / 125% / 150%，QActionGroup 互斥）
  → 透過 `QApplication::setFont()` 縮放全局字體；偏好儲存於 QSettings，啟動時自動套用

---

## 🔧 代碼品質（Code Audit 2026-02-24）

### 審計發現 — 已修復

- [x] **C4267 警告 × 3** — `detection_controller.cpp`（2026-02-24）
  `usedObjectIds` 從 `std::set<int>` 改為 `std::set<size_t>`，與 `objIdx(size_t)` 型別一致

- [x] **C4267 警告 × 2** — `debug_panel.cpp`（2026-02-24）
  `image.step` / `rgb.step` 加 `static_cast<int>`，消除 QImage 建構時的隱式轉換警告

- [x] **C4701 警告 × 1** — `video_display.cpp`（2026-02-24）
  `Qt::AspectRatioMode aspectMode` 加預設值 `= Qt::KeepAspectRatio`，消除未初始化警告

- [x] **趨勢圖重置後不清除** — `counting_method_panel`（2026-02-24）
  新增 `resetTrendChart()` 方法；`onResetCount()` 後呼叫，確保重置計數時圖表歸零

### 審計發現 — 設計缺口（暫緩）

- [x] **roiWidth 沒有對應 config 欄位**
  已加入 `DetectionConfig.roiWidth`（0=自動全幀寬度），JSON 序列化、
  `DetectionController::setRoiX/setRoiWidth`、ROI 繪製、邊界框 X 偏移全部修正。
  `syncFromConfig()` 現在會同步 `m_roiWidthSpin`（範圍 0-1920，0=自動）。

- [ ] **vibrator_controller.cpp TODO**
  `// TODO: 實現實際硬體控制器`（第 217 行）
  目前為模擬模式，若有實際 RS-232/Modbus 震動機控制器需要對接

### 潛在優化建議（Backlog）

- [x] **統一使用 `Settings::instance()`，移除 `getConfig()` 別名**
  7 個呼叫點（detection_controller.cpp × 3、setup_wizard.cpp × 5、part_selector.cpp × 2 等）
  全數替換為 `Settings::instance()`，並從 settings.h 移除 `getConfig()` inline 函數。

- [x] **CSV 報告補充欄位**
  標頭和資料列新增：gateLinePositionRatio、roiEnabled、skipFrames（共 15 欄）。

- [x] **操作日誌持久化**
  `appendLog()` 寫入 UI 的同時，同步 append 到
  `Documents/BaslerReports/operation_YYYYMMDD.log`（純文字，UTF-8）。

- [x] **SetupWizard「重新顯示向導」選單項**
  「幫助」選單新增「重新執行設定向導(&W)」，完成後呼叫 `m_debugPanel->syncFromConfig()` 刷新 UI。

- [x] **Light Theme 完整性**
  新增 `include/ui/theme.h`（ThemeColors 結構，深/淺雙主題語義色彩）。
  `CountingMethodPanel` + `DefectDetectionMethodPanel` 新增 `applyTheme(bool)` slot，
  動態 StyleSheet（計數顏色、震動機狀態、合格率顏色、按鈕）改用 ThemeColors。
  `MainWindow::applyTheme()` 擴充：全局 QSS 涵蓋 QGroupBox/QLabel/QSpinBox/QPushButton 等，
  並同步通知子 panel；`bgStabilityLabel` 和 `recordingLabel` 動態顏色也改用語義色。

---

## ✅ 已完成

### 2026-02-24（Session 10）

- [x] Code Audit: 清零全部 6 個預先存在的編譯警告（C4267×5 + C4701×1）
- [x] Code Audit: 修復趨勢圖重置邏輯（`resetTrendChart()` 新增）

### 2026-02-24（Session 9）

- [x] Style: 響應式佈局（`resizeEvent()` 覆寫，< 1200px 自動隱藏右側面板）
- [x] Style: Dark/Light 主題切換（「檢視」選單 → 主題子選單，`qApp->setStyleSheet()`，QSettings 持久化）
- [x] Style: 字體大小設定（「檢視」選單 → 字體大小子選單，100%/125%/150%，`QApplication::setFont()`，QSettings 持久化）

### 2026-02-24（Session 8）

- [x] P3: 設定向導 SetupWizard（4 頁面 QWizard，isFirstRun/QSettings，首次啟動自動顯示）
- [x] P3: CSV 導出報告（Documents/BaslerReports/report_YYYYMMDD.csv，包裝完成自動寫入）
- [x] Style: 統一按鈕樣式 style.h（6 個 inline 函數 + 色票常量，新 Widget 可直接引用）

### 2026-02-24（Session 7）

- [x] P3: 全螢幕影像模式（F11/雙擊/ESC 切換，隱藏右側面板，HUD overlay 計數+FPS+光柵線）

### 2026-02-24（Session 6）

- [x] P2: 歷史計數趨勢迷你圖（CountTrendWidget QPainter 折線圖，件/秒速率，最多 20 點，進度組內嵌）

### 2026-02-24（Session 5）

- [x] P2: 參數預設模板 Profile（Debug Panel 頂部 QComboBox + 儲存/載入/刪除，AppDataLocation/profiles/，detection+gate JSON，syncFromConfig 完整實作）

### 2026-02-24（Session 4）

- [x] P2: 光柵線位置可視化點擊設定（VideoDisplayWidget 新增點擊模式 + 黃色水平預覽線，Debug Panel 加點擊按鈕，ESC 取消，兩種編輯模式互斥）

### 2026-02-24（Session 3）

- [x] P2: ROI 視覺化拖拽編輯器（VideoDisplayWidget 新增拖拽模式 + rubberband overlay，Debug Panel 加框選按鈕）
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
