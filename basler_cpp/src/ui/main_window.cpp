#include "ui/main_window.h"
#include <QMenuBar>
#include <QStatusBar>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QPushButton>
#include <QMessageBox>
#include <QCloseEvent>
#include <QDebug>
#include <opencv2/imgproc.hpp>

namespace basler {

MainWindow::MainWindow(QWidget* parent)
    : QMainWindow(parent)
{
    setWindowTitle("Basler 工業視覺系統 v2.0 (C++)");
    setMinimumSize(1280, 720);

    // 創建相機控制器
    m_cameraController = std::make_unique<CameraController>(this);

    setupUi();
    setupMenuBar();
    setupStatusBar();
    connectSignals();

    // UI 更新定時器（60 FPS）
    m_updateTimer = new QTimer(this);
    connect(m_updateTimer, &QTimer::timeout, this, &MainWindow::updateDisplay);
    m_updateTimer->start(16);  // ~60 FPS

    qDebug() << "[MainWindow] 初始化完成";
}

MainWindow::~MainWindow()
{
    // CameraController 會自動清理（RAII）
}

void MainWindow::closeEvent(QCloseEvent* event)
{
    // 優雅關閉
    if (m_cameraController->isGrabbing()) {
        m_cameraController->stopGrabbing();
    }
    event->accept();
}

void MainWindow::setupUi()
{
    QWidget* centralWidget = new QWidget(this);
    setCentralWidget(centralWidget);

    QVBoxLayout* mainLayout = new QVBoxLayout(centralWidget);

    // 視頻顯示區
    m_videoDisplay = new QLabel("等待相機連接...");
    m_videoDisplay->setAlignment(Qt::AlignCenter);
    m_videoDisplay->setMinimumSize(640, 480);
    m_videoDisplay->setStyleSheet("QLabel { background-color: #1a1a1a; color: #888; font-size: 18px; }");
    mainLayout->addWidget(m_videoDisplay, 1);

    // 控制按鈕區
    QHBoxLayout* controlLayout = new QHBoxLayout();

    QPushButton* detectBtn = new QPushButton("偵測相機");
    QPushButton* connectBtn = new QPushButton("連接");
    QPushButton* disconnectBtn = new QPushButton("斷開");
    QPushButton* startBtn = new QPushButton("開始抓取");
    QPushButton* stopBtn = new QPushButton("停止抓取");

    connect(detectBtn, &QPushButton::clicked, this, &MainWindow::onDetectCameras);
    connect(connectBtn, &QPushButton::clicked, this, &MainWindow::onConnectCamera);
    connect(disconnectBtn, &QPushButton::clicked, this, &MainWindow::onDisconnectCamera);
    connect(startBtn, &QPushButton::clicked, this, &MainWindow::onStartGrabbing);
    connect(stopBtn, &QPushButton::clicked, this, &MainWindow::onStopGrabbing);

    controlLayout->addWidget(detectBtn);
    controlLayout->addWidget(connectBtn);
    controlLayout->addWidget(disconnectBtn);
    controlLayout->addStretch();
    controlLayout->addWidget(startBtn);
    controlLayout->addWidget(stopBtn);

    mainLayout->addLayout(controlLayout);
}

void MainWindow::setupMenuBar()
{
    QMenu* fileMenu = menuBar()->addMenu("檔案(&F)");

    QAction* exitAction = fileMenu->addAction("退出(&X)");
    exitAction->setShortcut(QKeySequence::Quit);
    connect(exitAction, &QAction::triggered, this, &QMainWindow::close);

    QMenu* helpMenu = menuBar()->addMenu("幫助(&H)");

    QAction* aboutAction = helpMenu->addAction("關於(&A)");
    connect(aboutAction, &QAction::triggered, [this]() {
        QMessageBox::about(this, "關於",
            "Basler 工業視覺系統\n"
            "版本: 2.0.0 (C++)\n\n"
            "高性能工業相機控制與物件檢測系統");
    });
}

void MainWindow::setupStatusBar()
{
    m_statusLabel = new QLabel("就緒");
    m_fpsLabel = new QLabel("FPS: --");

    statusBar()->addWidget(m_statusLabel, 1);
    statusBar()->addPermanentWidget(m_fpsLabel);
}

void MainWindow::connectSignals()
{
    // 連接相機控制器信號（關鍵：這些信號跨線程安全傳遞）
    connect(m_cameraController.get(), &CameraController::connected,
            this, &MainWindow::onCameraConnected);
    connect(m_cameraController.get(), &CameraController::disconnected,
            this, &MainWindow::onCameraDisconnected);
    connect(m_cameraController.get(), &CameraController::grabbingStarted,
            this, &MainWindow::onGrabbingStarted);
    connect(m_cameraController.get(), &CameraController::grabbingStopped,
            this, &MainWindow::onGrabbingStopped);
    connect(m_cameraController.get(), &CameraController::connectionError,
            this, &MainWindow::onCameraError);
    connect(m_cameraController.get(), &CameraController::grabError,
            this, &MainWindow::onCameraError);
    connect(m_cameraController.get(), &CameraController::stateChanged,
            this, &MainWindow::onCameraStateChanged);
    connect(m_cameraController.get(), &CameraController::frameReady,
            this, &MainWindow::onFrameReady);
    connect(m_cameraController.get(), &CameraController::fpsUpdated,
            this, &MainWindow::onFpsUpdated);
}

// ============================================================================
// 槽函數 - 用戶操作
// ============================================================================

void MainWindow::onDetectCameras()
{
    m_statusLabel->setText("偵測相機中...");

    QList<CameraInfo> cameras = m_cameraController->detectCameras();

    if (cameras.isEmpty()) {
        m_statusLabel->setText("未發現相機");
    } else {
        m_statusLabel->setText(QString("發現 %1 台相機").arg(cameras.size()));
    }
}

void MainWindow::onConnectCamera()
{
    m_statusLabel->setText("連接中...");
    // 異步操作！UI 不會阻塞
    m_cameraController->connectCamera(0);
}

void MainWindow::onDisconnectCamera()
{
    m_statusLabel->setText("斷開中...");
    // 異步操作！
    m_cameraController->disconnectCamera();
}

void MainWindow::onStartGrabbing()
{
    m_cameraController->startGrabbing();
}

void MainWindow::onStopGrabbing()
{
    m_cameraController->stopGrabbing();
}

// ============================================================================
// 槽函數 - 相機事件
// ============================================================================

void MainWindow::onCameraConnected(const CameraInfo& info)
{
    m_statusLabel->setText(QString("已連接: %1").arg(info.model));
    qDebug() << "[MainWindow] 相機已連接:" << info.model;
}

void MainWindow::onCameraDisconnected()
{
    m_statusLabel->setText("相機已斷開");
    m_videoDisplay->setText("等待相機連接...");
}

void MainWindow::onGrabbingStarted()
{
    m_statusLabel->setText("抓取中");
}

void MainWindow::onGrabbingStopped()
{
    m_statusLabel->setText("抓取已停止");
}

void MainWindow::onCameraError(const QString& error)
{
    m_statusLabel->setText(QString("錯誤: %1").arg(error));
    QMessageBox::warning(this, "相機錯誤", error);
}

void MainWindow::onCameraStateChanged(CameraState state)
{
    // 可以根據狀態更新 UI 元素的啟用/禁用狀態
    Q_UNUSED(state);
}

void MainWindow::onFrameReady(const cv::Mat& frame)
{
    // 保存最新幀（線程安全）
    QMutexLocker locker(&m_frameMutex);
    m_latestFrame = frame.clone();
}

void MainWindow::onFpsUpdated(double fps)
{
    m_fpsLabel->setText(QString("FPS: %1").arg(fps, 0, 'f', 1));
}

void MainWindow::updateDisplay()
{
    cv::Mat frame;
    {
        QMutexLocker locker(&m_frameMutex);
        if (m_latestFrame.empty()) return;
        frame = m_latestFrame.clone();
    }

    // 轉換為 QImage 並顯示
    QImage image(frame.data, frame.cols, frame.rows,
                 frame.step, QImage::Format_Grayscale8);

    m_videoDisplay->setPixmap(QPixmap::fromImage(image).scaled(
        m_videoDisplay->size(), Qt::KeepAspectRatio, Qt::SmoothTransformation));
}

} // namespace basler
