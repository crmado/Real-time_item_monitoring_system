#include "ui/main_window.h"
#include "ui/setup_wizard.h"
#include "ui/widgets/video_display.h"
#include "ui/widgets/camera_control.h"
#include "ui/widgets/recording_control.h"
#include "ui/widgets/packaging_control.h"
#include "ui/widgets/method_panels/counting_method_panel.h"
#include "ui/widgets/debug_panel.h"
#include "ui/widgets/system_monitor.h"
#include "config/settings.h"
#include "core/video_player.h"

#include <QMenuBar>
#include <QStatusBar>
#include <QShortcut>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollArea>
#include <QTabWidget>
#include <QFileDialog>
#include <QMessageBox>
#include <QCloseEvent>
#include <QCoreApplication>
#include <QDebug>
#include <QTimer>
#include <QtConcurrent>
#include <QStandardPaths>
#include <QDateTime>
#include <QDir>
#include <QFile>
#include <QTextStream>
#include <QResizeEvent>
#include <QSettings>
#include <QApplication>
#include <QActionGroup>
#include <opencv2/imgproc.hpp>
#include <opencv2/imgcodecs.hpp>

namespace basler
{

    MainWindow::MainWindow(QWidget *parent)
        : QMainWindow(parent)
    {
        setWindowTitle("Basler 工業視覺系統 v2.0 (C++)");
        setMinimumSize(1400, 800);

        // 載入使用者偏好（主題 / 字體），在 UI 建立前套用以避免閃爍
        m_baseFontPt = QApplication::font().pointSize();
        if (m_baseFontPt <= 0) m_baseFontPt = 10;
        {
            QSettings prefs("BaslerVision", "BaslerVisionSystem");
            m_isDarkTheme = prefs.value("isDarkTheme", true).toBool();
            m_fontScale   = prefs.value("fontScale", 1.0).toDouble();
        }
        applyTheme(m_isDarkTheme);
        applyFontScale(m_fontScale);

        // 初始化核心控制器
        m_sourceManager = std::make_unique<SourceManager>(this);
        m_detectionController = std::make_unique<DetectionController>(this);
        m_videoRecorder = std::make_unique<VideoRecorder>("recordings", this);
        m_vibratorManager = createDualVibratorManager("simulated", "震動機A", "震動機B");

        // 設置 UI
        setupUi();
        setupMenuBar();
        setupStatusBar();

        // 連接信號
        connectCameraSignals();
        connectRecordingSignals();
        connectPackagingSignals();
        connectDetectionSignals();
        connectDebugSignals();

        // UI 更新定時器（60 FPS）
        m_updateTimer = new QTimer(this);
        connect(m_updateTimer, &QTimer::timeout, this, &MainWindow::updateDisplay);
        m_updateTimer->start(16); // ~60 FPS

        // 啟動系統監控
        m_systemMonitor->startMonitoring();

        // 設置鍵盤快捷鍵
        setupKeyboardShortcuts();

        // 首次使用：延遲 500ms 後顯示設定向導（讓主視窗先完整渲染）
        if (SetupWizard::isFirstRun())
        {
            QTimer::singleShot(500, this, [this]()
            {
                SetupWizard wizard(this);
                wizard.exec();
                // 向導完成後刷新 Debug Panel 顯示值
                m_debugPanel->syncFromConfig();
            });
        }

        qDebug() << "[MainWindow] 初始化完成";
    }

    MainWindow::~MainWindow()
    {
        qDebug() << "[MainWindow] 開始析構...";

        // 1. 停止更新定時器
        if (m_updateTimer)
        {
            m_updateTimer->stop();
        }

        // 2. 停止系統監控
        m_systemMonitor->stopMonitoring();

        // 3. 斷開所有核心控制器的信號連接（防止析構期間信號觸發）
        if (m_sourceManager)
        {
            m_sourceManager->disconnect(this);
        }
        if (m_detectionController)
        {
            m_detectionController->disconnect(this);
        }
        if (m_videoRecorder)
        {
            m_videoRecorder->disconnect(this);
        }

        // 4. 停止進行中的操作（如果 closeEvent 沒被調用）
        if (m_isRecording && m_videoRecorder)
        {
            m_videoRecorder->stopRecording();
        }
        if (m_isDetecting && m_detectionController)
        {
            m_detectionController->disable();
        }
        if (m_sourceManager && m_sourceManager->isGrabbing())
        {
            m_sourceManager->stopGrabbing();
        }

        // 5. 其他資源由 unique_ptr RAII 自動清理
        qDebug() << "[MainWindow] 析構完成";
    }

    void MainWindow::closeEvent(QCloseEvent *event)
    {
        // 優雅關閉：停止所有進行中的操作
        if (m_isRecording)
        {
            m_videoRecorder->stopRecording();
        }
        if (m_isDetecting)
        {
            m_detectionController->disable();
        }
        if (m_sourceManager->isGrabbing())
        {
            m_sourceManager->stopGrabbing();
        }

        event->accept();
    }

    // ============================================================================
    // 響應式佈局：視窗寬度 < 1200px 時自動摺疊右側面板
    // ============================================================================
    void MainWindow::resizeEvent(QResizeEvent *event)
    {
        QMainWindow::resizeEvent(event);
        if (m_controlPanel && !m_isFullscreenMode)
        {
            bool narrow = event->size().width() < 1200;
            if (m_controlPanel->isVisible() == narrow)  // 狀態需要切換
                m_controlPanel->setVisible(!narrow);
        }
    }

    // ============================================================================
    // 深色/淺色主題切換
    // ============================================================================
    void MainWindow::applyTheme(bool isDark)
    {
        if (isDark)
        {
            // 深色：清除全局 QSS（各 widget 自帶深色 StyleSheet）
            qApp->setStyleSheet("");
        }
        else
        {
            // 淺色：覆蓋主框架元素（widget 層級的 StyleSheet 仍有優先權）
            qApp->setStyleSheet(
                "QMainWindow { background-color: #f0f2f5; }"
                "QMenuBar { background-color: #e8eaed; color: #2c3e50; }"
                "QMenuBar::item:selected { background-color: #bdc3c7; }"
                "QMenu { background-color: #ffffff; color: #2c3e50; border: 1px solid #bdc3c7; }"
                "QMenu::item:selected { background-color: #d5dbdb; }"
                "QTabWidget::pane { background-color: #ecf0f1; border: 1px solid #bdc3c7; }"
                "QTabBar::tab { background-color: #d0d3d4; color: #2c3e50; padding: 6px 12px; }"
                "QTabBar::tab:selected { background-color: #ecf0f1; font-weight: bold; }"
                "QStatusBar { background-color: #e8eaed; color: #2c3e50; }"
                "QDialog { background-color: #f0f2f5; color: #2c3e50; }"
                "QWizard { background-color: #f0f2f5; color: #2c3e50; }"
                "QScrollBar:vertical { background-color: #d0d3d4; width: 10px; }"
                "QScrollBar::handle:vertical { background-color: #909497; border-radius: 4px; }"
                "QScrollBar:horizontal { background-color: #d0d3d4; height: 10px; }"
                "QScrollBar::handle:horizontal { background-color: #909497; border-radius: 4px; }"
            );
        }
    }

    // ============================================================================
    // 字體縮放（100% / 125% / 150%）
    // ============================================================================
    void MainWindow::applyFontScale(double scale)
    {
        if (m_baseFontPt <= 0) return;
        QFont f = QApplication::font();
        f.setPointSizeF(m_baseFontPt * scale);
        QApplication::setFont(f);
    }

    void MainWindow::setupUi()
    {
        QWidget *centralWidget = new QWidget(this);
        setCentralWidget(centralWidget);

        QHBoxLayout *mainLayout = new QHBoxLayout(centralWidget);
        mainLayout->setSpacing(10);
        mainLayout->setContentsMargins(10, 10, 10, 10);

        // 主分割器
        m_mainSplitter = new QSplitter(Qt::Horizontal);

        // ========== 左側：顯示區（主視頻 + 可選的分割第二視頻） ==========
        m_displaySplitter = new QSplitter(Qt::Horizontal);
        m_displaySplitter->setCollapsible(0, false);
        m_displaySplitter->setCollapsible(1, false);
        m_displaySplitter->setHandleWidth(4);

        m_videoDisplay = new VideoDisplayWidget();
        m_videoDisplay->setMinimumSize(400, 500);
        m_displaySplitter->addWidget(m_videoDisplay);

        m_videoDisplay2 = new VideoDisplayWidget();
        m_videoDisplay2->setMinimumSize(400, 500);
        m_videoDisplay2->showPlaceholder("分割視圖  |  啟動分割顯示後顯示互補幀");
        m_videoDisplay2->hide();
        m_displaySplitter->addWidget(m_videoDisplay2);

        m_mainSplitter->addWidget(m_displaySplitter);

        // ========== 右側：分頁控制面板 ==========
        m_controlPanel = new QTabWidget();
        QTabWidget *tabWidget = m_controlPanel;
        tabWidget->setMinimumWidth(450);
        tabWidget->setMaximumWidth(550);
        tabWidget->setStyleSheet(R"(
            QTabWidget::pane {
                border: 2px solid #1f3a5f;
                border-radius: 6px;
                background-color: #0a0e27;
            }
            QTabBar::tab {
                background-color: #1a1f3d;
                color: #e0e6f1;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 10pt;
            }
            QTabBar::tab:selected {
                background-color: #0d4a7a;
                color: #00d4ff;
            }
            QTabBar::tab:hover {
                background-color: #1e5a8e;
            }
        )");

        // ========== Tab 1: 相機設定 ==========
        QWidget *cameraSettingsTab = new QWidget();
        QVBoxLayout *cameraSettingsLayout = new QVBoxLayout(cameraSettingsTab);
        cameraSettingsLayout->setSpacing(10);
        cameraSettingsLayout->setContentsMargins(8, 8, 8, 8);

        m_cameraControl = new CameraControlWidget();
        cameraSettingsLayout->addWidget(m_cameraControl);

        m_recordingControl = new RecordingControlWidget();
        cameraSettingsLayout->addWidget(m_recordingControl);

        cameraSettingsLayout->addStretch();

        // 為設定頁面添加滾動區域
        QScrollArea *settingsScroll = new QScrollArea();
        settingsScroll->setWidgetResizable(true);
        settingsScroll->setWidget(cameraSettingsTab);
        settingsScroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        settingsScroll->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);

        // ========== Tab 2: 檢測監控 ==========
        QWidget *monitoringTab = new QWidget();
        QVBoxLayout *monitoringLayout = new QVBoxLayout(monitoringTab);
        monitoringLayout->setSpacing(10);
        monitoringLayout->setContentsMargins(8, 8, 8, 8);

        // 原始畫面預覽區域
        QWidget *previewContainer = new QWidget();
        previewContainer->setStyleSheet(R"(
            QWidget {
                background-color: #0a0e27;
                border: 2px solid #1f3a5f;
                border-radius: 8px;
            }
        )");
        QVBoxLayout *previewLayout = new QVBoxLayout(previewContainer);
        previewLayout->setContentsMargins(8, 8, 8, 8);
        previewLayout->setSpacing(5);

        QLabel *previewLabel = new QLabel("📹 原始畫面");
        previewLabel->setStyleSheet(R"(
            font-weight: bold;
            color: #00d4ff;
            font-size: 11pt;
            background-color: transparent;
            border: none;
        )");
        previewLayout->addWidget(previewLabel);

        // 小型預覽窗口 - 減小尺寸
        m_cameraPreview = new VideoDisplayWidget();
        m_cameraPreview->setFixedHeight(180);
        m_cameraPreview->setStyleSheet(R"(
            QWidget {
                border: 1px solid #00d4ff;
                border-radius: 4px;
                background-color: #000000;
            }
        )");
        previewLayout->addWidget(m_cameraPreview);

        monitoringLayout->addWidget(previewContainer);

        // 包裝控制
        m_packagingControl = new PackagingControlWidget();
        monitoringLayout->addWidget(m_packagingControl);

        // 系統監控
        m_systemMonitor = new SystemMonitorWidget();
        monitoringLayout->addWidget(m_systemMonitor);

        monitoringLayout->addStretch();

        // 為檢測監控添加滾動區域
        QScrollArea *monitoringScroll = new QScrollArea();
        monitoringScroll->setWidgetResizable(true);
        monitoringScroll->setWidget(monitoringTab);
        monitoringScroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        monitoringScroll->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);

        // ========== Tab 3: 調試工具 ==========
        // Debug Panel 內部已自帶 QScrollArea，不需要再包一層
        m_debugPanel = new DebugPanelWidget();

        // 添加分頁
        tabWidget->addTab(settingsScroll, "⚙️ 設定");
        tabWidget->addTab(monitoringScroll, "📊 監控");
        tabWidget->addTab(m_debugPanel, "🛠️ 調試");

        // 預設顯示「檢測監控」頁面
        tabWidget->setCurrentIndex(1);

        m_mainSplitter->addWidget(tabWidget);

        // 設置分割比例：主畫面 : 右側控制面板
        m_mainSplitter->setStretchFactor(0, 1); // 主畫面可伸縮
        m_mainSplitter->setStretchFactor(1, 0); // 右側面板固定寬度

        // 設置分割器不可摺疊
        m_mainSplitter->setCollapsible(0, false);
        m_mainSplitter->setCollapsible(1, false);

        mainLayout->addWidget(m_mainSplitter);
    }

    void MainWindow::setupMenuBar()
    {
        // ========== 檔案選單 ==========
        QMenu *fileMenu = menuBar()->addMenu("檔案(&F)");

        QAction *loadVideoAction = fileMenu->addAction("載入影片(&O)...");
        loadVideoAction->setShortcut(QKeySequence::Open);
        connect(loadVideoAction, &QAction::triggered, this, &MainWindow::onLoadVideo);

        fileMenu->addSeparator();

        QAction *saveConfigAction = fileMenu->addAction("儲存設定(&S)");
        saveConfigAction->setShortcut(QKeySequence::Save);
        connect(saveConfigAction, &QAction::triggered, this, &MainWindow::onSaveConfig);

        QAction *loadConfigAction = fileMenu->addAction("載入設定(&L)...");
        connect(loadConfigAction, &QAction::triggered, this, &MainWindow::onLoadConfig);

        fileMenu->addSeparator();

        QAction *loadYoloAction = fileMenu->addAction("載入 YOLO 模型(&Y)...");
        connect(loadYoloAction, &QAction::triggered, this, &MainWindow::onLoadYoloModel);

        fileMenu->addSeparator();

        QAction *exitAction = fileMenu->addAction("退出(&X)");
        exitAction->setShortcut(QKeySequence::Quit);
        connect(exitAction, &QAction::triggered, this, &QMainWindow::close);

        // ========== 檢視選單（主題 / 字體） ==========
        QMenu *viewMenu = menuBar()->addMenu("檢視(&V)");

        // 主題切換（互斥 QActionGroup）
        QMenu *themeMenu = viewMenu->addMenu("主題(&T)");
        QActionGroup *themeGroup = new QActionGroup(this);
        themeGroup->setExclusive(true);

        QAction *darkAction  = themeGroup->addAction(themeMenu->addAction("深色主題(&D)"));
        QAction *lightAction = themeGroup->addAction(themeMenu->addAction("淺色主題(&L)"));
        darkAction->setCheckable(true);
        lightAction->setCheckable(true);
        darkAction->setChecked(m_isDarkTheme);
        lightAction->setChecked(!m_isDarkTheme);

        connect(darkAction,  &QAction::triggered, [this]()
        {
            m_isDarkTheme = true;
            applyTheme(true);
            QSettings("BaslerVision", "BaslerVisionSystem").setValue("isDarkTheme", true);
        });
        connect(lightAction, &QAction::triggered, [this]()
        {
            m_isDarkTheme = false;
            applyTheme(false);
            QSettings("BaslerVision", "BaslerVisionSystem").setValue("isDarkTheme", false);
        });

        // 字體大小（互斥 QActionGroup）
        viewMenu->addSeparator();
        QMenu *fontMenu = viewMenu->addMenu("字體大小(&F)");
        QActionGroup *fontGroup = new QActionGroup(this);
        fontGroup->setExclusive(true);

        struct FontOption { const char* label; double scale; };
        const FontOption fontOptions[] = {
            { "100%（標準）", 1.00 },
            { "125%（中等）", 1.25 },
            { "150%（大字）", 1.50 },
        };
        for (const auto& opt : fontOptions)
        {
            QAction *act = fontGroup->addAction(fontMenu->addAction(opt.label));
            act->setCheckable(true);
            act->setChecked(qAbs(m_fontScale - opt.scale) < 0.01);
            double scaleCapture = opt.scale;
            connect(act, &QAction::triggered, [this, scaleCapture]()
            {
                m_fontScale = scaleCapture;
                applyFontScale(scaleCapture);
                QSettings("BaslerVision", "BaslerVisionSystem").setValue("fontScale", scaleCapture);
            });
        }

        // ========== 幫助選單 ==========
        QMenu *helpMenu = menuBar()->addMenu("幫助(&H)");

        QAction *aboutAction = helpMenu->addAction("關於(&A)");
        connect(aboutAction, &QAction::triggered, [this]()
                { QMessageBox::about(this, "關於",
                                     "Basler 工業視覺系統\n"
                                     "版本: 2.0.0 (C++)\n\n"
                                     "高性能工業相機控制與物件檢測系統\n\n"
                                     "特性:\n"
                                     "- 非阻塞異步相機操作\n"
                                     "- 狀態機驅動的相機控制\n"
                                     "- 虛擬光柵計數算法\n"
                                     "- 瑕疵檢測與合格率統計"); });
    }

    void MainWindow::setupStatusBar()
    {
        m_statusLabel = new QLabel("就緒");
        m_fpsLabel = new QLabel("FPS: --");
        m_detectionLabel = new QLabel("檢測: 停止");
        m_recordingLabel = new QLabel("");
        m_objectCountLabel = new QLabel("物件: --");
        m_roiLabel = new QLabel("ROI: --");
        m_bgStabilityLabel = new QLabel("背景: --");

        // 灰色樣式作為初始狀態（檢測啟動後會變色）
        QString dimStyle = "color: #888888;";
        m_objectCountLabel->setStyleSheet(dimStyle);
        m_roiLabel->setStyleSheet(dimStyle);
        m_bgStabilityLabel->setStyleSheet(dimStyle);

        statusBar()->addWidget(m_statusLabel, 1);
        statusBar()->addPermanentWidget(m_objectCountLabel);
        statusBar()->addPermanentWidget(m_roiLabel);
        statusBar()->addPermanentWidget(m_bgStabilityLabel);
        statusBar()->addPermanentWidget(m_detectionLabel);
        statusBar()->addPermanentWidget(m_recordingLabel);
        statusBar()->addPermanentWidget(m_fpsLabel);
    }

    // ============================================================================
    // 信號連接
    // ============================================================================

    void MainWindow::connectCameraSignals()
    {
        // From UI to SourceManager
        connect(m_cameraControl, &CameraControlWidget::detectRequested,
                this, &MainWindow::onDetectCameras);
        connect(m_cameraControl, &CameraControlWidget::detectWithRetryRequested,
                this, &MainWindow::onDetectCamerasWithRetry);
        connect(m_cameraControl, &CameraControlWidget::connectRequested,
                this, &MainWindow::onConnectCamera);
        connect(m_cameraControl, &CameraControlWidget::disconnectRequested,
                this, &MainWindow::onDisconnectCamera);
        connect(m_cameraControl, &CameraControlWidget::startGrabRequested,
                this, &MainWindow::onStartGrabbing);
        connect(m_cameraControl, &CameraControlWidget::stopGrabRequested,
                this, &MainWindow::onStopGrabbing);

        // 從 SourceManager 到 MainWindow（使用 Qt::QueuedConnection 確保線程安全）
        connect(m_sourceManager.get(), &SourceManager::connected,
                this, &MainWindow::onCameraConnected, Qt::QueuedConnection);
        connect(m_sourceManager.get(), &SourceManager::disconnected,
                this, &MainWindow::onCameraDisconnected, Qt::QueuedConnection);
        connect(m_sourceManager.get(), &SourceManager::grabbingStarted,
                this, &MainWindow::onGrabbingStarted, Qt::QueuedConnection);
        connect(m_sourceManager.get(), &SourceManager::grabbingStopped,
                this, &MainWindow::onGrabbingStopped, Qt::QueuedConnection);
        connect(m_sourceManager.get(), &SourceManager::frameReady,
                this, &MainWindow::onFrameReady, Qt::QueuedConnection);
        connect(m_sourceManager.get(), &SourceManager::fpsUpdated,
                this, &MainWindow::onFpsUpdated, Qt::QueuedConnection);
        connect(m_sourceManager.get(), &SourceManager::error,
                this, &MainWindow::onCameraError, Qt::QueuedConnection);
    }

    void MainWindow::connectRecordingSignals()
    {
        // 從 UI 到 VideoRecorder
        connect(m_recordingControl, &RecordingControlWidget::startRecordingRequested,
                this, &MainWindow::onStartRecording);
        connect(m_recordingControl, &RecordingControlWidget::stopRecordingRequested,
                this, &MainWindow::onStopRecording);

        // 從 VideoRecorder 到 MainWindow
        connect(m_videoRecorder.get(), &VideoRecorder::recordingStarted,
                this, &MainWindow::onRecordingStarted);
        connect(m_videoRecorder.get(), &VideoRecorder::recordingStopped,
                this, &MainWindow::onRecordingStopped);
        connect(m_videoRecorder.get(), &VideoRecorder::recordingError,
                this, &MainWindow::onRecordingError);

        // 錄影幀數/時長即時更新
        connect(m_videoRecorder.get(), &VideoRecorder::frameWritten,
                [this](int totalFrames)
                {
                    double duration = m_videoRecorder->recordingDuration();
                    m_recordingControl->updateStats(totalFrames, duration);
                });
    }

    void MainWindow::connectPackagingSignals()
    {
        // 計數方法信號
        connect(m_packagingControl, &PackagingControlWidget::startPackagingRequested,
                this, &MainWindow::onStartPackaging);
        connect(m_packagingControl, &PackagingControlWidget::pausePackagingRequested,
                this, &MainWindow::onPausePackaging);
        connect(m_packagingControl, &PackagingControlWidget::resetCountRequested,
                this, &MainWindow::onResetCount);
        connect(m_packagingControl, &PackagingControlWidget::targetCountChanged,
                this, &MainWindow::onTargetCountChanged);
        connect(m_packagingControl, &PackagingControlWidget::thresholdChanged,
                this, &MainWindow::onThresholdChanged);

        // 零件/方法選擇
        connect(m_packagingControl, &PackagingControlWidget::partTypeChanged,
                this, &MainWindow::onPartTypeChanged);
        connect(m_packagingControl, &PackagingControlWidget::detectionMethodChanged,
                this, &MainWindow::onDetectionMethodChanged);

        // 瑕疵檢測信號
        connect(m_packagingControl, &PackagingControlWidget::startDefectDetectionRequested,
                this, &MainWindow::onStartDefectDetection);
        connect(m_packagingControl, &PackagingControlWidget::stopDefectDetectionRequested,
                this, &MainWindow::onStopDefectDetection);
        connect(m_packagingControl, &PackagingControlWidget::clearDefectStatsRequested,
                this, &MainWindow::onClearDefectStats);
        connect(m_packagingControl, &PackagingControlWidget::defectSensitivityChanged,
                this, &MainWindow::onDefectSensitivityChanged);
    }

    void MainWindow::connectDetectionSignals()
    {
        // 從 DetectionController 到 MainWindow
        connect(m_detectionController.get(), &DetectionController::countChanged,
                this, &MainWindow::onCountChanged);
        connect(m_detectionController.get(), &DetectionController::vibratorSpeedChanged,
                this, &MainWindow::onVibratorSpeedChanged);
        connect(m_detectionController.get(), &DetectionController::packagingCompleted,
                this, &MainWindow::onPackagingCompleted);
        connect(m_detectionController.get(), &DetectionController::defectStatsUpdated,
                this, &MainWindow::onDefectStatsUpdated);

        // 震動機控制
        connect(m_detectionController.get(), &DetectionController::vibratorSpeedChanged,
                [this](VibratorSpeed speed)
                {
                    m_vibratorManager->setSpeed(speed);
                });
    }

    void MainWindow::connectDebugSignals()
    {
        // ROI 參數
        connect(m_debugPanel, &DebugPanelWidget::roiChanged,
                this, &MainWindow::onRoiChanged);
        // ROI 拖拽框選：按鈕 → 啟動框選模式，VideoDisplay 框選完成 → 更新設定
        connect(m_debugPanel, &DebugPanelWidget::roiEditModeRequested,
                [this]()
                {
                    m_videoDisplay->setRoiEditMode(true);
                    m_statusLabel->setText("ROI 框選模式：在主畫面拖拽框選區域，ESC 取消");
                });
        connect(m_videoDisplay, &VideoDisplayWidget::roiSelected,
                this, &MainWindow::onRoiSelectedFromDrag);
        connect(m_debugPanel, &DebugPanelWidget::roiEnabledChanged,
                [this](bool enabled)
                {
                    Settings::instance().detection().roiEnabled = enabled;
                    m_detectionController->setRoiEnabled(enabled);
                });

        // 背景減除參數
        connect(m_debugPanel, &DebugPanelWidget::bgHistoryChanged,
                [this](int history)
                {
                    Settings::instance().detection().bgHistory = history;
                    m_detectionController->setBgHistory(history);
                });
        connect(m_debugPanel, &DebugPanelWidget::bgVarThresholdChanged,
                [this](double threshold)
                {
                    Settings::instance().detection().bgVarThreshold = threshold;
                    m_detectionController->setBgVarThreshold(threshold);
                    m_statusLabel->setText(QString("bgVarThreshold = %1 已套用").arg(threshold));
                });
        connect(m_debugPanel, &DebugPanelWidget::bgLearningRateChanged,
                [this](double rate)
                {
                    Settings::instance().detection().bgLearningRate = rate;
                    m_detectionController->setBgLearningRate(rate);
                });

        // 邊緣檢測參數
        connect(m_debugPanel, &DebugPanelWidget::cannyLowChanged,
                [this](int threshold)
                {
                    auto &det = Settings::instance().detection();
                    det.cannyLowThreshold = threshold;
                    m_detectionController->setCannyThresholds(threshold, det.cannyHighThreshold);
                    m_statusLabel->setText(QString("Canny = %1/%2 已套用").arg(threshold).arg(det.cannyHighThreshold));
                });
        connect(m_debugPanel, &DebugPanelWidget::cannyHighChanged,
                [this](int threshold)
                {
                    auto &det = Settings::instance().detection();
                    det.cannyHighThreshold = threshold;
                    m_detectionController->setCannyThresholds(det.cannyLowThreshold, threshold);
                    m_statusLabel->setText(QString("Canny = %1/%2 已套用").arg(det.cannyLowThreshold).arg(threshold));
                });

        // 形態學參數
        connect(m_debugPanel, &DebugPanelWidget::morphKernelSizeChanged,
                [this](int size)
                {
                    auto &det = Settings::instance().detection();
                    det.morphKernelSize = size;
                    m_detectionController->setMorphParams(size, det.morphIterations);
                });
        connect(m_debugPanel, &DebugPanelWidget::morphIterationsChanged,
                [this](int iterations)
                {
                    auto &det = Settings::instance().detection();
                    det.morphIterations = iterations;
                    m_detectionController->setMorphParams(det.morphKernelSize, iterations);
                });

        // 面積參數
        connect(m_debugPanel, &DebugPanelWidget::minAreaChanged,
                [this](int area)
                {
                    Settings::instance().detection().minArea = area;
                    m_detectionController->setMinArea(area);
                    m_statusLabel->setText(QString("minArea = %1 已套用").arg(area));
                });
        connect(m_debugPanel, &DebugPanelWidget::maxAreaChanged,
                [this](int area)
                {
                    Settings::instance().detection().maxArea = area;
                    m_detectionController->setMaxArea(area);
                    m_statusLabel->setText(QString("maxArea = %1 已套用").arg(area));
                });

        // 虛擬閘門參數
        connect(m_debugPanel, &DebugPanelWidget::gateYPositionChanged,
                [](int y)
                {
                    Settings::instance().gate().yPosition = y;
                });
        connect(m_debugPanel, &DebugPanelWidget::gateTriggerRadiusChanged,
                [this](int radius)
                {
                    Settings::instance().gate().triggerRadius = radius;
                    m_detectionController->setGateTriggerRadius(radius);
                });
        connect(m_debugPanel, &DebugPanelWidget::gateHistoryFramesChanged,
                [this](int frames)
                {
                    Settings::instance().gate().gateHistoryFrames = frames;
                    m_detectionController->setGateHistoryFrames(frames);
                });
        connect(m_debugPanel, &DebugPanelWidget::gateLinePositionChanged,
                [this](double ratio)
                {
                    Settings::instance().gate().gateLinePositionRatio = ratio;
                    m_detectionController->setGateLinePositionRatio(ratio);
                });

        // 測試影片載入
        connect(m_debugPanel, &DebugPanelWidget::loadTestVideo,
                this, &MainWindow::onLoadVideo);

        // 影片控制信號
        connect(m_debugPanel, &DebugPanelWidget::playVideo, this, [this]()
                {
            auto* vp = m_sourceManager->videoPlayer();
            if (vp) vp->resume(); });
        connect(m_debugPanel, &DebugPanelWidget::pauseVideo, this, [this]()
                {
            auto* vp = m_sourceManager->videoPlayer();
            if (vp) vp->pause(); });
        connect(m_debugPanel, &DebugPanelWidget::prevFrame, this, [this]()
                {
            auto* vp = m_sourceManager->videoPlayer();
            if (vp) vp->previousFrame(); });
        connect(m_debugPanel, &DebugPanelWidget::nextFrame, this, [this]()
                {
            auto* vp = m_sourceManager->videoPlayer();
            if (vp) vp->nextFrame(); });
        connect(m_debugPanel, &DebugPanelWidget::jumpToFrame, this, [this](int frame)
                {
            auto* vp = m_sourceManager->videoPlayer();
            if (vp) vp->seek(frame); });
        connect(m_debugPanel, &DebugPanelWidget::screenshot, this, [this]()
                {
            QMutexLocker locker(&m_frameMutex);
            if (m_latestFrame.empty()) return;

            QString picturesDir = QStandardPaths::writableLocation(QStandardPaths::PicturesLocation);
            QDir().mkpath(picturesDir);
            QString filename = QString("%1/screenshot_%2.png")
                .arg(picturesDir)
                .arg(QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss"));

            cv::imwrite(filename.toStdString(), m_latestFrame);
            m_statusLabel->setText(QString("截圖已儲存: %1").arg(filename));
            qDebug() << "[MainWindow] 截圖已儲存:" << filename; });

        // ===== YOLO 偵測信號 =====
        connect(m_debugPanel, &DebugPanelWidget::yoloModeChanged,
                [this](int modeIndex)
                {
                    DetectionMode mode = static_cast<DetectionMode>(modeIndex);
                    m_detectionController->setDetectionMode(mode);
                    m_statusLabel->setText(QString("偵測模式: %1")
                                               .arg(modeIndex == 0 ? "傳統" : modeIndex == 1 ? "YOLO"
                                                                                             : "自動"));
                });
        connect(m_debugPanel, &DebugPanelWidget::yoloConfidenceChanged,
                [this](double threshold)
                {
                    m_detectionController->setYoloConfidence(threshold);
                });
        connect(m_debugPanel, &DebugPanelWidget::yoloNmsThresholdChanged,
                [this](double threshold)
                {
                    m_detectionController->setYoloNmsThreshold(threshold);
                });
        connect(m_debugPanel, &DebugPanelWidget::yoloRoiUpscaleChanged,
                [this](double factor)
                {
                    m_detectionController->setYoloRoiUpscale(factor);
                });
        connect(m_debugPanel, &DebugPanelWidget::loadYoloModelRequested,
                this, &MainWindow::onLoadYoloModel);

        // YOLO 狀態反饋到 UI
        connect(m_detectionController.get(), &DetectionController::yoloModelLoaded,
                m_debugPanel, &DebugPanelWidget::updateYoloModelStatus);
        connect(m_detectionController.get(), &DetectionController::yoloInferenceTimeUpdated,
                m_debugPanel, &DebugPanelWidget::updateYoloInferenceTime);

        // 處理解析度（targetProcessingWidth）
        connect(m_debugPanel, &DebugPanelWidget::processingWidthChanged,
                [](int width)
                {
                    auto &cfg = Settings::instance().performance();
                    // 0 = 原生解析度模式：設為一個不可能超過的大值，讓縮放邏輯跳過縮放
                    cfg.targetProcessingWidth = (width > 0) ? width : 99999;
                });

        // Profile 載入後將新設定套用到 DetectionController
        connect(m_debugPanel, &DebugPanelWidget::profileLoaded,
                [this](const QString& profileName)
                {
                    const auto& det  = Settings::instance().detection();
                    const auto& gate = Settings::instance().gate();
                    m_detectionController->setMinArea(det.minArea);
                    m_detectionController->setMaxArea(det.maxArea);
                    m_detectionController->setBgHistory(det.bgHistory);
                    m_detectionController->setBgVarThreshold(det.bgVarThreshold);
                    m_detectionController->setBgLearningRate(det.bgLearningRate);
                    m_detectionController->setCannyThresholds(det.cannyLowThreshold, det.cannyHighThreshold);
                    m_detectionController->setMorphParams(det.morphKernelSize, det.morphIterations);
                    m_detectionController->setRoiEnabled(det.roiEnabled);
                    m_detectionController->setRoiHeight(det.roiHeight);
                    m_detectionController->setGateTriggerRadius(gate.triggerRadius);
                    m_detectionController->setGateHistoryFrames(gate.gateHistoryFrames);
                    m_detectionController->setGateLinePositionRatio(gate.gateLinePositionRatio);
                    m_statusLabel->setText(QString("已載入模板：%1").arg(profileName));
                });

        // 光柵線點擊設定：按鈕 → 啟動點擊模式，VideoDisplay 點擊完成 → 更新設定
        connect(m_debugPanel, &DebugPanelWidget::gateLineEditModeRequested,
                [this]()
                {
                    m_videoDisplay->setGateLineEditMode(true);
                    m_statusLabel->setText("光柵線設定模式：點擊畫面指定光柵線位置，ESC 取消");
                });
        connect(m_videoDisplay, &VideoDisplayWidget::gateLinePositionSelected,
                this, &MainWindow::onGateLineFromClick);

        // 雙擊主畫面 → 全螢幕模式切換
        connect(m_videoDisplay, &VideoDisplayWidget::doubleClicked,
                this, &MainWindow::toggleFullscreenMode);

        // ===== 操作按鈕信號（原先未連接） =====
        connect(m_debugPanel, &DebugPanelWidget::resetTotalCount,
                m_detectionController.get(), &DetectionController::reset);
        connect(m_debugPanel, &DebugPanelWidget::resetParams,
                [](){ Settings::instance().resetToDefault(); });
        connect(m_debugPanel, &DebugPanelWidget::saveConfig,
                [](){ Settings::instance().save(); });
        connect(m_debugPanel, &DebugPanelWidget::loadConfig,
                [](){ Settings::instance().load(); });

        // 主畫面視覺化模式：0=原始, 1=前景遮罩, 2=Canny, 3=三重聯合, 4=最終形態學
        connect(m_debugPanel, &DebugPanelWidget::debugViewModeChanged,
                [this](int mode){ m_debugViewMode = mode; });

        // 分割顯示模式（Debug Panel 按鈕觸發）
        connect(m_debugPanel, &DebugPanelWidget::splitViewToggleRequested,
                this, &MainWindow::toggleSplitView);
    }

    void MainWindow::toggleFullscreenMode()
    {
        m_isFullscreenMode = !m_isFullscreenMode;

        if (m_isFullscreenMode) {
            // 隱藏右側控制面板 + 分割視圖第二面板，讓 m_videoDisplay 撐滿
            m_controlPanel->hide();
            if (m_isSplitView) m_videoDisplay2->hide();
            m_videoDisplay->setHudEnabled(true);
            showFullScreen();
            m_statusLabel->setText("全螢幕模式  |  按 F11 或 ESC 或雙擊畫面退出");
        } else {
            // 恢復右側面板
            m_controlPanel->show();
            if (m_isSplitView) m_videoDisplay2->show();  // 恢復分割視圖
            m_videoDisplay->setHudEnabled(false);
            showNormal();
            m_statusLabel->setText("已退出全螢幕模式");
        }
    }

    void MainWindow::toggleSplitView()
    {
        m_isSplitView = !m_isSplitView;

        if (m_isSplitView) {
            m_videoDisplay2->show();
            // 等比分配左側顯示區給兩個面板
            m_displaySplitter->setSizes({m_displaySplitter->width() / 2,
                                         m_displaySplitter->width() / 2});
            m_statusLabel->setText("分割顯示  |  左：選定視圖  右：互補幀  |  F9 關閉");
        } else {
            m_videoDisplay2->hide();
            m_statusLabel->setText("已關閉分割顯示");
        }
    }

    void MainWindow::setupKeyboardShortcuts()
    {
        // Space：播放 / 暫停視頻（僅影片模式有效）
        new QShortcut(Qt::Key_Space, this, [this]()
        {
            auto *vp = m_sourceManager->videoPlayer();
            if (!vp) return;
            if (vp->isPaused()) vp->resume();
            else if (vp->isPlaying()) vp->pause();
        });

        // ←：上一幀
        new QShortcut(Qt::Key_Left, this, [this]()
        {
            auto *vp = m_sourceManager->videoPlayer();
            if (vp) vp->previousFrame();
        });

        // →：下一幀
        new QShortcut(Qt::Key_Right, this, [this]()
        {
            auto *vp = m_sourceManager->videoPlayer();
            if (vp) vp->nextFrame();
        });

        // Ctrl+R：開始 / 停止錄製（Ctrl+S 已在 MenuBar 處理）
        new QShortcut(QKeySequence("Ctrl+R"), this, [this]()
        {
            if (m_isRecording) onStopRecording();
            else onStartRecording();
        });

        // F5：重置計數
        new QShortcut(Qt::Key_F5, this, [this]()
        {
            onResetCount();
        });

        // F9：分割顯示模式（左右並排兩個視角）
        new QShortcut(Qt::Key_F9, this, [this]()
        {
            toggleSplitView();
        });

        // F11：純視頻全螢幕模式（隱藏右側面板 + OS 全螢幕）
        new QShortcut(Qt::Key_F11, this, [this]()
        {
            toggleFullscreenMode();
        });

        // ESC：取消編輯模式或退出全螢幕
        new QShortcut(Qt::Key_Escape, this, [this]()
        {
            if (m_isFullscreenMode) {
                toggleFullscreenMode();
                return;
            }
            m_videoDisplay->setRoiEditMode(false);
            m_videoDisplay->setGateLineEditMode(false);
            m_statusLabel->setText("已取消編輯模式");
        });

        qDebug() << "[MainWindow] 鍵盤快捷鍵已設定 (Space/←/→/Ctrl+R/F5/F9/F11/ESC)";
    }

    // ============================================================================
    // 相機控制槽函數
    // ============================================================================

    void MainWindow::onDetectCameras()
    {
        m_statusLabel->setText("Detecting cameras (quick scan)...");
        auto cameras = m_sourceManager->cameraController()->detectCameras();

        if (cameras.isEmpty())
        {
            m_statusLabel->setText("No cameras found");
            m_cameraControl->setCameraList({});
        }
        else
        {
            m_statusLabel->setText(QString("Found %1 camera(s)").arg(cameras.size()));
            QStringList cameraNames;
            for (const auto &cam : cameras)
            {
                cameraNames.append(QString("%1 (%2)").arg(cam.model).arg(cam.serial));
            }
            m_cameraControl->setCameraList(cameraNames);
        }
    }

    void MainWindow::onDetectCamerasWithRetry()
    {
        m_statusLabel->setText("Auto-detecting cameras (smart scan with retry)...");

        // Run in background to avoid UI blocking
        QThreadPool::globalInstance()->start([this]()
                                             {
            auto cameras = m_sourceManager->cameraController()->detectCamerasWithRetry(3, 2000);

            // Update UI in main thread
            QMetaObject::invokeMethod(this, [this, cameras]() {
                if (cameras.isEmpty())
                {
                    m_statusLabel->setText("No cameras found after 3 attempts. Check connections and power.");
                    m_cameraControl->setCameraList({});
                }
                else
                {
                    m_statusLabel->setText(QString("Successfully found %1 camera(s)").arg(cameras.size()));
                    QStringList cameraNames;
                    for (const auto &cam : cameras)
                    {
                        cameraNames.append(QString("%1 (%2)").arg(cam.model).arg(cam.serial));
                    }
                    m_cameraControl->setCameraList(cameraNames);
                }
            }, Qt::QueuedConnection); });
    }

    void MainWindow::onConnectCamera()
    {
        m_statusLabel->setText("連接中...");
        m_sourceManager->connectCamera(0);
    }

    void MainWindow::onDisconnectCamera()
    {
        m_statusLabel->setText("斷開中...");
        m_sourceManager->disconnectCamera();
    }

    void MainWindow::onStartGrabbing()
    {
        m_sourceManager->startGrabbing();
    }

    void MainWindow::onStopGrabbing()
    {
        m_sourceManager->stopGrabbing();
    }

    void MainWindow::onCameraConnected(const CameraInfo &info)
    {
        m_statusLabel->setText(QString("已連接: %1").arg(info.model));
        m_cameraControl->setConnected(true);
        qDebug() << "[MainWindow] 相機已連接:" << info.model;

        // 連接成功後自動開始抓取
        QTimer::singleShot(100, this, [this]()
                           { m_sourceManager->startGrabbing(); });
    }

    void MainWindow::onCameraDisconnected()
    {
        m_statusLabel->setText("相機已斷開");
        m_cameraControl->setConnected(false);
        m_videoDisplay->showPlaceholder("等待相機連接...");
    }

    void MainWindow::onGrabbingStarted()
    {
        m_statusLabel->setText("抓取中");
        m_cameraControl->setGrabbing(true);
    }

    void MainWindow::onGrabbingStopped()
    {
        m_statusLabel->setText("抓取已停止");
        m_cameraControl->setGrabbing(false);
    }

    void MainWindow::onCameraError(const QString &error)
    {
        m_statusLabel->setText(QString("錯誤: %1").arg(error));
        m_debugPanel->logError("相機：" + error);
        QMessageBox::warning(this, "相機錯誤", error);
    }

    // ============================================================================
    // 幀處理
    // ============================================================================

    void MainWindow::onFrameReady(const cv::Mat &frame)
    {
        static int frameCount = 0;
        frameCount++;
        if (frameCount == 1 || frameCount % 100 == 0)
        {
            qDebug() << "[MainWindow::onFrameReady] 收到幀 #" << frameCount
                     << ", 尺寸:" << frame.cols << "x" << frame.rows;
        }

        // 只更新幀數據，不在這裡做耗時處理
        {
            QMutexLocker locker(&m_frameMutex);
            m_latestFrame = frame.clone();
        }

        // 錄製（快速操作）
        if (m_isRecording)
        {
            m_videoRecorder->writeFrame(frame);
        }

        // 注意：檢測處理已移到 updateDisplay() 中，與 UI 更新同步
    }

    void MainWindow::processFrame(const cv::Mat &frame)
    {
        // 送入檢測控制器
        std::vector<DetectedObject> detectedObjects;
        cv::Mat processedFrame = m_detectionController->processFrame(frame, detectedObjects);

        // ===== StatusBar 即時更新 =====
        // 1. 即時偵測物件數
        m_objectCountLabel->setText(QString("物件: %1").arg(static_cast<int>(detectedObjects.size())));

        // 2. ROI 尺寸
        const auto &det = Settings::instance().detection();
        if (det.roiEnabled)
            m_roiLabel->setText(QString("ROI: %1×%2").arg(frame.cols).arg(det.roiHeight));
        else
            m_roiLabel->setText("ROI: 關閉");

        // 3. 背景減除器穩定性（已處理幀數 vs bgHistory）
        int processed = m_detectionController->totalProcessedFrames();
        int bgHistory = det.bgHistory;
        if (processed >= bgHistory)
        {
            m_bgStabilityLabel->setText("背景: 穩定");
            m_bgStabilityLabel->setStyleSheet("color: #00ff80;");
        }
        else
        {
            int pct = (bgHistory > 0) ? (processed * 100 / bgHistory) : 0;
            m_bgStabilityLabel->setText(QString("背景: 學習 %1%").arg(pct));
            m_bgStabilityLabel->setStyleSheet("color: #ffcc00;");
        }

        // 調試視圖：將二值化遮罩傳給 Debug Panel 顯示
        if (m_debugPanel && m_debugPanel->isShowingDebugView())
        {
            cv::Mat debugFrame = m_detectionController->lastDebugFrame();
            if (!debugFrame.empty())
                m_debugPanel->updateDebugImage(debugFrame);
        }

        // HUD 更新（全螢幕模式下疊加計數/FPS/光柵線）
        if (m_isFullscreenMode)
        {
            double gateRatio = Settings::instance().gate().gateLinePositionRatio;
            m_videoDisplay->updateHud(m_hudCount, m_hudFps, gateRatio);
        }

        // 儲存處理後的幀用於顯示
        {
            QMutexLocker locker(&m_frameMutex);
            m_processedFrame = processedFrame;
        }
    }

    void MainWindow::onFpsUpdated(double fps)
    {
        m_hudFps = fps;
        m_fpsLabel->setText(QString("FPS: %1").arg(fps, 0, 'f', 1));
    }

    void MainWindow::updateDisplay()
    {
        cv::Mat frame;
        cv::Mat processed;
        {
            QMutexLocker locker(&m_frameMutex);
            if (m_latestFrame.empty())
                return;
            frame = m_latestFrame.clone();
        }

        // 如果正在檢測，在 UI 線程處理（60fps 頻率）
        if (m_isDetecting && !frame.empty())
        {
            processFrame(frame);
            QMutexLocker locker(&m_frameMutex);
            if (!m_processedFrame.empty())
            {
                processed = m_processedFrame.clone();
            }
        }

        // 根據調試模式選擇主畫面顯示幀
        cv::Mat displayMat;
        if (m_isDetecting && !processed.empty())
        {
            if (m_debugViewMode == 0)
            {
                displayMat = processed;
            }
            else
            {
                // 取得對應中間結果（灰階 Mat，需轉 BGR 才能疊加 UI 繪製）
                cv::Mat debugGray;
                switch (m_debugViewMode)
                {
                    case 1: debugGray = m_detectionController->lastFgMask();    break;
                    case 2: debugGray = m_detectionController->lastCannyEdges(); break;
                    case 3: debugGray = m_detectionController->lastCombined();   break;
                    case 4: debugGray = m_detectionController->lastDebugFrame(); break;
                    default: break;
                }
                if (!debugGray.empty())
                {
                    if (debugGray.channels() == 1)
                        cv::cvtColor(debugGray, displayMat, cv::COLOR_GRAY2BGR);
                    else
                        displayMat = debugGray;
                }
                else
                {
                    displayMat = processed; // 中間幀尚未就緒，回退原始結果
                }
            }
        }
        else
        {
            displayMat = frame;
        }
        m_videoDisplay->displayFrame(displayMat);

        // 分割視圖第二面板（非全螢幕時才更新）
        if (m_isSplitView && m_videoDisplay2 && m_videoDisplay2->isVisible())
        {
            // 左面板顯示選定中間結果時，右面板顯示最終檢測結果（互補）
            // 左面板顯示最終結果（mode=0）時，右面板顯示原始幀（互補）
            cv::Mat splitMat;
            if (m_debugViewMode == 0)
                splitMat = frame;                           // 互補：原始幀
            else if (m_isDetecting && !processed.empty())
                splitMat = processed;                       // 互補：最終檢測結果
            else
                splitMat = frame;
            m_videoDisplay2->displayFrame(splitMat);
        }

        // 更新小型預覽窗口（始終顯示原始畫面）
        if (m_cameraPreview && !frame.empty())
        {
            m_cameraPreview->displayFrame(frame);
        }
    }

    // ============================================================================
    // 錄製控制
    // ============================================================================

    void MainWindow::onStartRecording()
    {
        QString outputPath = m_recordingControl->outputPath();
        if (outputPath.isEmpty())
        {
            outputPath = QDir::homePath() + "/Videos";
        }

        // 設置輸出目錄
        m_videoRecorder->setOutputDirectory(outputPath);

        // 生成檔名（不含副檔名，由 VideoRecorder 自動添加）
        QString filename = QString("recording_%1")
                               .arg(QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss"));

        // 獲取幀尺寸（使用默認值或從最新幀獲取）
        QSize frameSize(640, 480);
        {
            QMutexLocker locker(&m_frameMutex);
            if (!m_latestFrame.empty())
            {
                frameSize = QSize(m_latestFrame.cols, m_latestFrame.rows);
            }
        }

        m_videoRecorder->startRecording(frameSize, 30.0, filename);
    }

    void MainWindow::onStopRecording()
    {
        m_videoRecorder->stopRecording();
    }

    void MainWindow::onRecordingStarted()
    {
        m_isRecording = true;
        m_recordingLabel->setText("🔴 錄製中");
        m_recordingLabel->setStyleSheet("color: #ff4444;");
        m_recordingControl->setRecording(true);
    }

    void MainWindow::onRecordingStopped()
    {
        m_isRecording = false;
        m_recordingLabel->setText("");
        m_recordingControl->setRecording(false);
    }

    void MainWindow::onRecordingError(const QString &error)
    {
        m_debugPanel->logError("錄影：" + error);
        QMessageBox::warning(this, "錄製錯誤", error);
    }

    // ============================================================================
    // 包裝/檢測控制
    // ============================================================================

    void MainWindow::onStartPackaging()
    {
        m_packagingStartTime = QDateTime::currentMSecsSinceEpoch();  // 記錄包裝開始時間
        m_isDetecting = true;
        m_detectionController->enable();
        m_detectionController->enablePackagingMode(true);
        m_vibratorManager->start();
        m_detectionLabel->setText("計數中...");

        // 更新 UI 按鈕狀態
        m_packagingControl->countingPanel()->setPackagingState(true);

        qDebug() << "[MainWindow] 包裝已啟動";
    }

    void MainWindow::onPausePackaging()
    {
        m_isDetecting = false;
        m_detectionController->disable();
        m_detectionController->enablePackagingMode(false);
        m_vibratorManager->stop();
        m_detectionLabel->setText("已暫停");

        // 更新 UI 按鈕狀態
        m_packagingControl->countingPanel()->setPackagingState(false);

        qDebug() << "[MainWindow] 包裝已暫停";
    }

    void MainWindow::onResetCount()
    {
        // 停止所有操作
        m_isDetecting = false;
        m_detectionController->disable();
        m_detectionController->resetPackaging();
        m_vibratorManager->stop();
        m_detectionLabel->setText("檢測: 停止");

        // 重置 UI 狀態
        m_packagingControl->countingPanel()->setPackagingState(false);
        auto &pkg = getConfig().packaging();
        m_packagingControl->updateCount(0, pkg.targetCount);
        m_packagingControl->updateVibratorStatus(false, false, 0);

        qDebug() << "[MainWindow] 包裝已重置";
    }

    void MainWindow::onTargetCountChanged(int count)
    {
        m_detectionController->setTargetCount(count);
    }

    void MainWindow::onThresholdChanged(double full, double medium, double slow)
    {
        auto &config = Settings::instance().packaging();
        config.speedFullThreshold = full;
        config.speedMediumThreshold = medium;
        config.speedSlowThreshold = slow;

        // 同步更新 DetectionController
        m_detectionController->setSpeedThresholds(full, medium, slow);

        qDebug() << "[MainWindow] 速度閾值變更: full=" << full
                 << ", medium=" << medium << ", slow=" << slow;
    }

    void MainWindow::onPartTypeChanged(const QString &partId)
    {
        qDebug() << "[MainWindow] 零件類型變更:" << partId;
        // 根據零件類型載入相應的參數設定
    }

    void MainWindow::onDetectionMethodChanged(const QString &methodId)
    {
        qDebug() << "[MainWindow] 檢測方法變更:" << methodId;

        // 更新狀態顯示
        if (methodId == "counting")
        {
            m_detectionLabel->setText("計數模式");
        }
        else if (methodId == "defect_detection")
        {
            m_detectionLabel->setText("瑕疵檢測模式");
        }
    }

    void MainWindow::onStartDefectDetection()
    {
        m_isDetecting = true;
        m_detectionController->enable();
        m_detectionLabel->setText("瑕疵檢測中...");
    }

    void MainWindow::onStopDefectDetection()
    {
        m_isDetecting = false;
        m_detectionController->disable();
        m_detectionLabel->setText("檢測: 停止");
    }

    void MainWindow::onClearDefectStats()
    {
        m_detectionController->resetDefectStats();
    }

    void MainWindow::onDefectSensitivityChanged(double sensitivity)
    {
        auto &config = Settings::instance().detection();
        config.defectSensitivity = sensitivity;
    }

    // ============================================================================
    // 檢測結果更新
    // ============================================================================

    void MainWindow::onCountChanged(int count)
    {
        m_hudCount = count;  // 供 HUD 使用
        m_debugPanel->logCountEvent(count, m_detectionController->totalProcessedFrames());

        // 從 DetectionController 獲取包裝狀態
        auto packagingStatus = m_detectionController->getPackagingStatus();
        m_packagingControl->updateCount(count, packagingStatus.targetCount);

        // 更新震動機狀態顯示
        auto vibratorStatus = m_vibratorManager->getStatus();
        m_packagingControl->updateVibratorStatus(
            vibratorStatus.vibrator1.isRunning,
            vibratorStatus.vibrator2.isRunning,
            vibratorStatus.vibrator1.speedPercent);
    }

    void MainWindow::onVibratorSpeedChanged(VibratorSpeed speed)
    {
        m_vibratorManager->setSpeed(speed);
    }

    void MainWindow::onPackagingCompleted()
    {
        // 計算耗時
        double elapsedSec = 0.0;
        if (m_packagingStartTime > 0)
        {
            elapsedSec = (QDateTime::currentMSecsSinceEpoch() - m_packagingStartTime) / 1000.0;
            m_packagingStartTime = 0;
        }

        // 停止所有操作
        m_vibratorManager->stop();
        m_isDetecting = false;
        m_detectionController->disable();
        m_detectionLabel->setText("包裝完成");

        // 更新 UI 狀態（CountingMethodPanel 的 overlay 已顯示「✅ 包裝完成！」，不再彈 QMessageBox）
        m_packagingControl->countingPanel()->showPackagingCompleted();
        m_packagingControl->updateVibratorStatus(false, false, 0);

        // 自動導出 CSV 報告
        int target  = m_packagingControl->countingPanel()->targetCount();
        int actual  = m_detectionController->count();
        exportPackagingReport(target, actual, elapsedSec);

        qDebug() << "[MainWindow] 包裝完成！計數:" << actual << "耗時:" << elapsedSec << "s";
    }

    void MainWindow::exportPackagingReport(int target, int actual, double elapsedSec)
    {
        // 建立報告目錄 Documents/BaslerReports/
        QString reportsDir = QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation)
                             + "/BaslerReports";
        QDir().mkpath(reportsDir);

        // 當天的累積 CSV（每天一個檔案，多包追加）
        QString dateStr   = QDate::currentDate().toString("yyyyMMdd");
        QString filePath  = QString("%1/report_%2.csv").arg(reportsDir, dateStr);

        QFile file(filePath);
        bool isNew = !file.exists();
        if (!file.open(QIODevice::Append | QIODevice::Text))
        {
            m_statusLabel->setText("⚠ 無法寫入報告檔案: " + filePath);
            return;
        }

        QTextStream out(&file);
        out.setCodec("UTF-8");

        // 標頭（僅新檔案寫一次）
        if (isNew)
        {
            out << "時間戳,零件類型,檢測方法,目標數量,實際數量,"
                   "耗時(秒),速率(件/秒),minArea,maxArea,"
                   "bgVarThreshold,cannyLow,cannyHigh\n";
        }

        const auto& det  = Settings::instance().detection();
        double rate      = (elapsedSec > 0) ? actual / elapsedSec : 0.0;
        QString partId   = m_packagingControl->currentPartId();
        QString methodId = m_packagingControl->currentMethodId();

        out << QDateTime::currentDateTime().toString("yyyy-MM-dd HH:mm:ss") << ","
            << partId   << ","
            << methodId << ","
            << target   << ","
            << actual   << ","
            << QString::number(elapsedSec, 'f', 1) << ","
            << QString::number(rate, 'f', 2) << ","
            << det.minArea << ","
            << det.maxArea << ","
            << det.bgVarThreshold << ","
            << det.cannyLowThreshold << ","
            << det.cannyHighThreshold << "\n";

        m_statusLabel->setText(QString("📄 報告已儲存: %1").arg(filePath));
        qDebug() << "[MainWindow] 導出報告:" << filePath;
    }

    void MainWindow::onDefectStatsUpdated(double passRate, int passCount, int failCount)
    {
        m_packagingControl->updateDefectStats(passRate, passCount, failCount);
    }

    // ============================================================================
    // Debug 參數
    // ============================================================================

    void MainWindow::onRoiChanged(int x, int y, int /*width*/, int height)
    {
        auto &config = Settings::instance().detection();
        config.roiX = x;
        config.roiY = y;
        config.roiHeight = height;
        m_detectionController->setRoiHeight(height);
    }

    void MainWindow::onRoiSelectedFromDrag(int x, int y, int w, int h)
    {
        // 更新 Settings
        auto &config = Settings::instance().detection();
        config.roiX = x;
        config.roiY = y;
        config.roiHeight = h;

        // 更新偵測控制器
        m_detectionController->setRoiHeight(h);

        // 同步 Debug Panel SpinBox（靜默，不重複觸發信號）
        m_debugPanel->setRoiValues(x, y, w, h);

        m_statusLabel->setText(
            QString("ROI 已更新：(%1, %2)  %3 × %4 px").arg(x).arg(y).arg(w).arg(h));
    }

    void MainWindow::onGateLineFromClick(double ratio)
    {
        // 更新 Settings 與 DetectionController
        Settings::instance().gate().gateLinePositionRatio = ratio;
        m_detectionController->setGateLinePositionRatio(ratio);

        // 同步 Debug Panel SpinBox（setGateLineRatio 會 blockSignals 後 emit，不造成迴圈）
        m_debugPanel->setGateLineRatio(ratio);

        m_statusLabel->setText(
            QString("光柵線已更新：ratio = %1").arg(ratio, 0, 'f', 2));
    }

    // ============================================================================
    // 選單動作
    // ============================================================================

    void MainWindow::onLoadVideo()
    {
        // 預設開啟測試影片目錄（從 build/Release/ 往上 3 層到專案根目錄）
        QDir appDir(QCoreApplication::applicationDirPath());
        QString testVideoDir = appDir.absoluteFilePath("../../../basler_mvc/recordings/新工業相機收集資料");
        QString defaultDir = QDir(testVideoDir).exists() ? testVideoDir : QDir::homePath();

        // macOS 原生對話框可能與 Qt6 事件循環衝突導致無法選取檔案，改用 Qt 對話框
        QString filePath = QFileDialog::getOpenFileName(
            this,
            "選擇影片檔案",
            defaultDir,
            "影片檔案 (*.mp4 *.avi *.mov *.mkv);;所有檔案 (*.*)",
            nullptr,
            QFileDialog::DontUseNativeDialog);

        if (filePath.isEmpty())
            return;

        // 如果正在播放/抓取，先停止
        if (m_sourceManager->isGrabbing())
        {
            m_sourceManager->stopGrabbing();
        }

        // 切換到影片源
        if (m_sourceManager->useVideo(filePath))
        {
            // 更新 UI 狀態
            m_cameraControl->setVideoMode(true);
            m_statusLabel->setText(QString("已載入影片: %1").arg(QFileInfo(filePath).fileName()));

            // 自動開始播放
            m_sourceManager->startGrabbing();

            // 影片模式自動啟用檢測（否則 processFrame 永遠不會被呼叫）
            m_isDetecting = true;
            m_detectionController->enable();
            m_detectionLabel->setText("檢測中（影片模式）");
            // 同步 Debug Panel 的 SpinBox 顯示值與當前設定
            m_debugPanel->syncFromConfig();
        }
        else
        {
            QMessageBox::warning(this, "載入失敗", "無法載入影片檔案");
        }
    }

    void MainWindow::onSaveConfig()
    {
        Settings::instance().save();
        m_statusLabel->setText("設定已儲存");
    }

    void MainWindow::onLoadConfig()
    {
        Settings::instance().load();
        m_statusLabel->setText("設定已載入");

        // 刷新 Debug Panel 的 SpinBox 顯示值
        m_debugPanel->syncFromConfig();
    }

    void MainWindow::updateButtonStates()
    {
        // 根據當前狀態更新按鈕的啟用狀態
        // 這由各個 widget 內部處理
    }

    void MainWindow::onLoadYoloModel()
    {
        // 預設開啟 models 目錄
        QDir appDir(QCoreApplication::applicationDirPath());
        QString modelsDir = appDir.absoluteFilePath("models");
        if (!QDir(modelsDir).exists())
        {
            modelsDir = appDir.absoluteFilePath("../../../basler_cpp/models");
        }
        QString defaultDir = QDir(modelsDir).exists() ? modelsDir : QDir::homePath();

        QString filePath = QFileDialog::getOpenFileName(
            this,
            "選擇 YOLO ONNX 模型",
            defaultDir,
            "ONNX 模型 (*.onnx);;所有檔案 (*.*)",
            nullptr,
            QFileDialog::DontUseNativeDialog);

        if (filePath.isEmpty())
            return;

        bool success = m_detectionController->loadYoloModel(filePath);
        if (success)
        {
            m_statusLabel->setText(QString("YOLO 模型已載入: %1").arg(QFileInfo(filePath).fileName()));
        }
        else
        {
            QMessageBox::warning(this, "載入失敗", "無法載入 YOLO ONNX 模型");
        }
    }

} // namespace basler
