#include "ui/main_window.h"
#include "ui/widgets/video_display.h"
#include "ui/widgets/camera_control.h"
#include "ui/widgets/recording_control.h"
#include "ui/widgets/packaging_control.h"
#include "ui/widgets/debug_panel.h"
#include "ui/widgets/system_monitor.h"
#include "config/settings.h"

#include <QMenuBar>
#include <QStatusBar>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QScrollArea>
#include <QTabWidget>
#include <QFileDialog>
#include <QMessageBox>
#include <QCloseEvent>
#include <QDebug>
#include <opencv2/imgproc.hpp>

namespace basler
{

    MainWindow::MainWindow(QWidget *parent)
        : QMainWindow(parent)
    {
        setWindowTitle("Basler 工業視覺系統 v2.0 (C++)");
        setMinimumSize(1400, 800);

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

    void MainWindow::setupUi()
    {
        QWidget *centralWidget = new QWidget(this);
        setCentralWidget(centralWidget);

        QHBoxLayout *mainLayout = new QHBoxLayout(centralWidget);
        mainLayout->setSpacing(10);
        mainLayout->setContentsMargins(10, 10, 10, 10);

        // 主分割器
        m_mainSplitter = new QSplitter(Qt::Horizontal);

        // ========== 左側：主視頻顯示區（大） ==========
        m_videoDisplay = new VideoDisplayWidget();
        m_videoDisplay->setMinimumSize(600, 500);
        m_mainSplitter->addWidget(m_videoDisplay);

        // ========== 右側：分頁控制面板 ==========
        QTabWidget* tabWidget = new QTabWidget();
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
        QWidget* cameraSettingsTab = new QWidget();
        QVBoxLayout* cameraSettingsLayout = new QVBoxLayout(cameraSettingsTab);
        cameraSettingsLayout->setSpacing(10);
        cameraSettingsLayout->setContentsMargins(8, 8, 8, 8);

        m_cameraControl = new CameraControlWidget();
        cameraSettingsLayout->addWidget(m_cameraControl);

        m_recordingControl = new RecordingControlWidget();
        cameraSettingsLayout->addWidget(m_recordingControl);

        cameraSettingsLayout->addStretch();

        // 為設定頁面添加滾動區域
        QScrollArea* settingsScroll = new QScrollArea();
        settingsScroll->setWidgetResizable(true);
        settingsScroll->setWidget(cameraSettingsTab);
        settingsScroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        settingsScroll->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);

        // ========== Tab 2: 檢測監控 ==========
        QWidget* monitoringTab = new QWidget();
        QVBoxLayout* monitoringLayout = new QVBoxLayout(monitoringTab);
        monitoringLayout->setSpacing(10);
        monitoringLayout->setContentsMargins(8, 8, 8, 8);

        // 原始畫面預覽區域
        QWidget* previewContainer = new QWidget();
        previewContainer->setStyleSheet(R"(
            QWidget {
                background-color: #0a0e27;
                border: 2px solid #1f3a5f;
                border-radius: 8px;
            }
        )");
        QVBoxLayout* previewLayout = new QVBoxLayout(previewContainer);
        previewLayout->setContentsMargins(8, 8, 8, 8);
        previewLayout->setSpacing(5);

        QLabel* previewLabel = new QLabel("📹 原始畫面");
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
        QScrollArea* monitoringScroll = new QScrollArea();
        monitoringScroll->setWidgetResizable(true);
        monitoringScroll->setWidget(monitoringTab);
        monitoringScroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        monitoringScroll->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);

        // ========== Tab 3: 調試工具 ==========
        m_debugPanel = new DebugPanelWidget();
        
        QScrollArea* debugScroll = new QScrollArea();
        debugScroll->setWidgetResizable(true);
        debugScroll->setWidget(m_debugPanel);
        debugScroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
        debugScroll->setVerticalScrollBarPolicy(Qt::ScrollBarAsNeeded);

        // 添加分頁
        tabWidget->addTab(settingsScroll, "⚙️ 設定");
        tabWidget->addTab(monitoringScroll, "📊 監控");
        tabWidget->addTab(debugScroll, "🛠️ 調試");

        // 預設顯示「檢測監控」頁面
        tabWidget->setCurrentIndex(1);

        m_mainSplitter->addWidget(tabWidget);

        // 設置分割比例：主畫面 : 右側控制面板
        m_mainSplitter->setStretchFactor(0, 1);  // 主畫面可伸縮
        m_mainSplitter->setStretchFactor(1, 0);  // 右側面板固定寬度

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

        QAction *exitAction = fileMenu->addAction("退出(&X)");
        exitAction->setShortcut(QKeySequence::Quit);
        connect(exitAction, &QAction::triggered, this, &QMainWindow::close);

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

        statusBar()->addWidget(m_statusLabel, 1);
        statusBar()->addPermanentWidget(m_detectionLabel);
        statusBar()->addPermanentWidget(m_recordingLabel);
        statusBar()->addPermanentWidget(m_fpsLabel);
    }

    // ============================================================================
    // 信號連接
    // ============================================================================

    void MainWindow::connectCameraSignals()
    {
        // 從 UI 到 SourceManager
        connect(m_cameraControl, &CameraControlWidget::detectRequested,
                this, &MainWindow::onDetectCameras);
        connect(m_cameraControl, &CameraControlWidget::connectRequested,
                this, &MainWindow::onConnectCamera);
        connect(m_cameraControl, &CameraControlWidget::disconnectRequested,
                this, &MainWindow::onDisconnectCamera);
        connect(m_cameraControl, &CameraControlWidget::startGrabRequested,
                this, &MainWindow::onStartGrabbing);
        connect(m_cameraControl, &CameraControlWidget::stopGrabRequested,
                this, &MainWindow::onStopGrabbing);

        // 從 SourceManager 到 MainWindow
        connect(m_sourceManager.get(), &SourceManager::connected,
                this, &MainWindow::onCameraConnected);
        connect(m_sourceManager.get(), &SourceManager::disconnected,
                this, &MainWindow::onCameraDisconnected);
        connect(m_sourceManager.get(), &SourceManager::grabbingStarted,
                this, &MainWindow::onGrabbingStarted);
        connect(m_sourceManager.get(), &SourceManager::grabbingStopped,
                this, &MainWindow::onGrabbingStopped);
        connect(m_sourceManager.get(), &SourceManager::frameReady,
                this, &MainWindow::onFrameReady);
        connect(m_sourceManager.get(), &SourceManager::fpsUpdated,
                this, &MainWindow::onFpsUpdated);
        connect(m_sourceManager.get(), &SourceManager::error,
                this, &MainWindow::onCameraError);
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
        // 注意: defectStatsUpdated 信號尚未實現

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

        // 背景減除參數
        connect(m_debugPanel, &DebugPanelWidget::bgHistoryChanged,
                [](int history)
                {
                    auto &config = Settings::instance().detection();
                    config.bgHistory = history;
                });
        connect(m_debugPanel, &DebugPanelWidget::bgVarThresholdChanged,
                [](double threshold)
                {
                    auto &config = Settings::instance().detection();
                    config.bgVarThreshold = threshold;
                });
        connect(m_debugPanel, &DebugPanelWidget::bgLearningRateChanged,
                [](double rate)
                {
                    auto &config = Settings::instance().detection();
                    config.bgLearningRate = rate;
                });

        // 邊緣檢測參數
        connect(m_debugPanel, &DebugPanelWidget::cannyLowChanged,
                [](int threshold)
                {
                    auto &config = Settings::instance().detection();
                    config.cannyLowThreshold = threshold;
                });
        connect(m_debugPanel, &DebugPanelWidget::cannyHighChanged,
                [](int threshold)
                {
                    auto &config = Settings::instance().detection();
                    config.cannyHighThreshold = threshold;
                });

        // 形態學參數
        connect(m_debugPanel, &DebugPanelWidget::morphKernelSizeChanged,
                [](int size)
                {
                    auto &config = Settings::instance().detection();
                    config.morphKernelSize = size;
                });
        connect(m_debugPanel, &DebugPanelWidget::morphIterationsChanged,
                [](int iterations)
                {
                    auto &config = Settings::instance().detection();
                    config.morphIterations = iterations;
                });

        // 面積參數
        connect(m_debugPanel, &DebugPanelWidget::minAreaChanged,
                [](int area)
                {
                    auto &config = Settings::instance().detection();
                    config.minArea = area;
                });
        connect(m_debugPanel, &DebugPanelWidget::maxAreaChanged,
                [](int area)
                {
                    auto &config = Settings::instance().detection();
                    config.maxArea = area;
                });

        // 虛擬閘門參數
        connect(m_debugPanel, &DebugPanelWidget::gateYPositionChanged,
                [](int y)
                {
                    auto &config = Settings::instance().gate();
                    config.yPosition = y;
                });
        connect(m_debugPanel, &DebugPanelWidget::gateTriggerRadiusChanged,
                [](int radius)
                {
                    auto &config = Settings::instance().gate();
                    config.triggerRadius = radius;
                });
    }

    // ============================================================================
    // 相機控制槽函數
    // ============================================================================

    void MainWindow::onDetectCameras()
    {
        m_statusLabel->setText("偵測相機中...");
        auto cameras = m_sourceManager->cameraController()->detectCameras();

        if (cameras.isEmpty())
        {
            m_statusLabel->setText("未發現相機");
            m_cameraControl->setCameraList({});
        }
        else
        {
            m_statusLabel->setText(QString("發現 %1 台相機").arg(cameras.size()));
            QStringList cameraNames;
            for (const auto &cam : cameras)
            {
                cameraNames.append(QString("%1 (%2)").arg(cam.model).arg(cam.serial));
            }
            m_cameraControl->setCameraList(cameraNames);
        }
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
        QMessageBox::warning(this, "相機錯誤", error);
    }

    void MainWindow::onCameraStateChanged(CameraState state)
    {
        updateButtonStates();
        Q_UNUSED(state);
    }

    // ============================================================================
    // 幀處理
    // ============================================================================

    void MainWindow::onFrameReady(const cv::Mat &frame)
    {
        QMutexLocker locker(&m_frameMutex);
        m_latestFrame = frame.clone();

        // 處理幀（檢測、錄製）
        if (m_isDetecting)
        {
            processFrame(frame);
        }

        // 錄製
        if (m_isRecording)
        {
            m_videoRecorder->writeFrame(frame);
        }
    }

    void MainWindow::processFrame(const cv::Mat &frame)
    {
        // 送入檢測控制器
        std::vector<DetectedObject> detectedObjects;
        cv::Mat processedFrame = m_detectionController->processFrame(frame, detectedObjects);

        // 儲存處理後的幀用於顯示
        {
            QMutexLocker locker(&m_frameMutex);
            m_processedFrame = processedFrame;
        }
    }

    void MainWindow::onFpsUpdated(double fps)
    {
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
            if (!m_processedFrame.empty())
            {
                processed = m_processedFrame.clone();
            }
        }

        // 顯示處理後的幀（如果有），否則顯示原始幀（主顯示區）
        if (m_isDetecting && !processed.empty())
        {
            m_videoDisplay->displayFrame(processed);
        }
        else
        {
            m_videoDisplay->displayFrame(frame);
        }

        // 更新小型預覽窗口（始終顯示原始畫面）
        if (m_cameraPreview && !frame.empty())
        {
            m_cameraPreview->displayFrame(frame);
        }

        // TODO: 偵錯圖像功能尚未實現
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
        QMessageBox::warning(this, "錄製錯誤", error);
    }

    // ============================================================================
    // 包裝/檢測控制
    // ============================================================================

    void MainWindow::onStartPackaging()
    {
        m_isDetecting = true;
        m_isPackaging = true;
        m_detectionController->enable();
        m_detectionController->enablePackagingMode(true);
        m_vibratorManager->start();
        m_detectionLabel->setText("計數中...");
    }

    void MainWindow::onPausePackaging()
    {
        m_isPackaging = false;
        m_vibratorManager->stop();
        m_detectionLabel->setText("已暫停");
    }

    void MainWindow::onResetCount()
    {
        m_detectionController->resetPackaging();
    }

    void MainWindow::onTargetCountChanged(int count)
    {
        m_detectionController->setTargetCount(count);
    }

    void MainWindow::onThresholdChanged(int threshold)
    {
        auto &config = Settings::instance().packaging();
        config.speedThreshold = threshold;
    }

    void MainWindow::onPartTypeChanged(const QString &partId)
    {
        qDebug() << "[MainWindow] 零件類型變更:" << partId;
        // 根據零件類型載入相應的參數設定
    }

    void MainWindow::onDetectionMethodChanged(const QString &methodId)
    {
        m_currentMethodId = methodId;
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
        // TODO: 瑕疵統計功能尚未實現
        m_detectionController->reset();
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
        // 停止震動機
        m_vibratorManager->stop();
        m_isPackaging = false;

        // 提示用戶
        QMessageBox::information(this, "包裝完成",
                                 QString("已達到目標數量！\n當前計數: %1")
                                     .arg(m_detectionController->count()));
    }

    void MainWindow::onDefectStatsUpdated(double passRate, int passCount, int failCount)
    {
        m_packagingControl->updateDefectStats(passRate, passCount, failCount);
    }

    // ============================================================================
    // Debug 參數
    // ============================================================================

    void MainWindow::onRoiChanged(int x, int y, int width, int height)
    {
        auto &config = Settings::instance().detection();
        config.roiX = x;
        config.roiY = y;
        config.roiWidth = width;
        config.roiHeight = height;
    }

    void MainWindow::onBgParamsChanged(int history, double varThreshold, double learningRate)
    {
        auto &config = Settings::instance().detection();
        config.bgHistory = history;
        config.bgVarThreshold = varThreshold;
        config.bgLearningRate = learningRate;
    }

    void MainWindow::onEdgeParamsChanged(int lowThreshold, int highThreshold)
    {
        auto &config = Settings::instance().detection();
        config.cannyLowThreshold = lowThreshold;
        config.cannyHighThreshold = highThreshold;
    }

    void MainWindow::onMorphParamsChanged(int kernelSize, int iterations)
    {
        auto &config = Settings::instance().detection();
        config.morphKernelSize = kernelSize;
        config.morphIterations = iterations;
    }

    void MainWindow::onAreaParamsChanged(int minArea, int maxArea)
    {
        auto &config = Settings::instance().detection();
        config.minArea = minArea;
        config.maxArea = maxArea;
    }

    void MainWindow::onGateParamsChanged(int yPosition, int triggerRadius)
    {
        auto &config = Settings::instance().gate();
        config.yPosition = yPosition;
        config.triggerRadius = triggerRadius;
    }

    // ============================================================================
    // 選單動作
    // ============================================================================

    void MainWindow::onLoadVideo()
    {
        QString filePath = QFileDialog::getOpenFileName(
            this,
            "選擇影片檔案",
            QDir::homePath(),
            "影片檔案 (*.mp4 *.avi *.mov *.mkv);;所有檔案 (*.*)");

        if (filePath.isEmpty())
            return;

        // 切換到影片源
        if (m_sourceManager->loadVideo(filePath))
        {
            m_statusLabel->setText(QString("已載入: %1").arg(QFileInfo(filePath).fileName()));
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

        // 更新 UI 以反映載入的設定
        // TODO: 刷新各個 widget 的顯示
    }

    void MainWindow::updateButtonStates()
    {
        // 根據當前狀態更新按鈕的啟用狀態
        // 這由各個 widget 內部處理
    }

} // namespace basler
