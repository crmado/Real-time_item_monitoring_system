#include "ui/widgets/debug_panel.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QFormLayout>
#include <QPainter>
#include <opencv2/imgproc.hpp>

namespace basler {

DebugPanelWidget::DebugPanelWidget(QWidget* parent)
    : QWidget(parent)
{
    initUi();
}

void DebugPanelWidget::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);
    mainLayout->setSpacing(4);
    mainLayout->setContentsMargins(4, 4, 4, 4);

    // 創建滾動區域
    m_scrollArea = new QScrollArea();
    m_scrollArea->setWidgetResizable(true);
    m_scrollArea->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);

    QWidget* scrollContent = new QWidget();
    QVBoxLayout* scrollLayout = new QVBoxLayout(scrollContent);
    scrollLayout->setSpacing(4);

    // 參數鎖定 checkbox（預設鎖定，防止滑鼠滾輪誤改參數）
    m_lockParamsCheck = new QCheckBox(tr("🔒 鎖定參數"));
    m_lockParamsCheck->setChecked(true);
    m_lockParamsCheck->setStyleSheet("QCheckBox { font-weight: bold; padding: 4px; }");
    connect(m_lockParamsCheck, &QCheckBox::toggled,
            this, &DebugPanelWidget::onLockParamsChanged);
    scrollLayout->addWidget(m_lockParamsCheck);

    // 添加各個參數組（受鎖定控制的）
    QWidget* detectionGroup = createDetectionParamsGroup();
    QWidget* bgGroup = createBgSubtractorGroup();
    QWidget* edgeGroup = createEdgeDetectionGroup();
    QWidget* morphGroup = createMorphologyGroup();
    QWidget* roiGroup = createRoiGroup();
    QWidget* gateGroup = createGateGroup();
    QWidget* perfGroup = createPerformanceGroup();

    m_paramGroupWidgets = { detectionGroup, bgGroup, edgeGroup,
                            morphGroup, roiGroup, gateGroup, perfGroup };

    scrollLayout->addWidget(detectionGroup);
    scrollLayout->addWidget(bgGroup);
    scrollLayout->addWidget(edgeGroup);
    scrollLayout->addWidget(morphGroup);
    scrollLayout->addWidget(roiGroup);
    scrollLayout->addWidget(gateGroup);
    scrollLayout->addWidget(perfGroup);

    // 以下區域不受鎖定影響（始終可操作）
    scrollLayout->addWidget(createYoloGroup());
    scrollLayout->addWidget(createDebugViewGroup());
    scrollLayout->addWidget(createVideoControlGroup());
    scrollLayout->addWidget(createActionButtonsGroup());
    scrollLayout->addStretch();

    // 初始鎖定所有參數組
    for (auto* w : m_paramGroupWidgets) {
        w->setEnabled(false);
    }

    m_scrollArea->setWidget(scrollContent);
    mainLayout->addWidget(m_scrollArea);
}

QWidget* DebugPanelWidget::createDetectionParamsGroup()
{
    QGroupBox* group = new QGroupBox(tr("📏 面積參數"));
    QFormLayout* layout = new QFormLayout();

    m_minAreaSpin = new QSpinBox();
    m_minAreaSpin->setRange(1, 1000);
    m_minAreaSpin->setValue(2);
    connect(m_minAreaSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onMinAreaChanged);
    layout->addRow(tr("最小面積:"), m_minAreaSpin);

    m_maxAreaSpin = new QSpinBox();
    m_maxAreaSpin->setRange(100, 50000);
    m_maxAreaSpin->setValue(3000);
    connect(m_maxAreaSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onMaxAreaChanged);
    layout->addRow(tr("最大面積:"), m_maxAreaSpin);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createBgSubtractorGroup()
{
    QGroupBox* group = new QGroupBox(tr("🎨 背景減除"));
    QFormLayout* layout = new QFormLayout();

    m_bgHistorySpin = new QSpinBox();
    m_bgHistorySpin->setRange(10, 5000);
    m_bgHistorySpin->setValue(1000);
    connect(m_bgHistorySpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onBgHistoryChanged);
    layout->addRow(tr("歷史幀數:"), m_bgHistorySpin);

    m_bgVarThresholdSpin = new QSpinBox();
    m_bgVarThresholdSpin->setRange(1, 50);
    m_bgVarThresholdSpin->setValue(3);
    connect(m_bgVarThresholdSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onBgVarThresholdChanged);
    layout->addRow(tr("變異閾值:"), m_bgVarThresholdSpin);

    m_bgLearningRateSpin = new QDoubleSpinBox();
    m_bgLearningRateSpin->setRange(0.0001, 0.1);
    m_bgLearningRateSpin->setSingleStep(0.001);
    m_bgLearningRateSpin->setDecimals(4);
    m_bgLearningRateSpin->setValue(0.001);
    connect(m_bgLearningRateSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onBgLearningRateChanged);
    layout->addRow(tr("學習率:"), m_bgLearningRateSpin);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createEdgeDetectionGroup()
{
    QGroupBox* group = new QGroupBox(tr("🔲 邊緣檢測 (Canny)"));
    QFormLayout* layout = new QFormLayout();

    m_cannyLowSpin = new QSpinBox();
    m_cannyLowSpin->setRange(1, 255);
    m_cannyLowSpin->setValue(2);
    connect(m_cannyLowSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onCannyLowChanged);
    layout->addRow(tr("低閾值:"), m_cannyLowSpin);

    m_cannyHighSpin = new QSpinBox();
    m_cannyHighSpin->setRange(1, 255);
    m_cannyHighSpin->setValue(8);
    connect(m_cannyHighSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onCannyHighChanged);
    layout->addRow(tr("高閾值:"), m_cannyHighSpin);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createMorphologyGroup()
{
    QGroupBox* group = new QGroupBox(tr("⚙️ 形態學處理"));
    QFormLayout* layout = new QFormLayout();

    m_morphKernelSizeSpin = new QSpinBox();
    m_morphKernelSizeSpin->setRange(1, 15);
    m_morphKernelSizeSpin->setSingleStep(2);  // 奇數
    m_morphKernelSizeSpin->setValue(3);
    connect(m_morphKernelSizeSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onMorphKernelSizeChanged);
    layout->addRow(tr("核大小:"), m_morphKernelSizeSpin);

    m_morphIterationsSpin = new QSpinBox();
    m_morphIterationsSpin->setRange(0, 10);
    m_morphIterationsSpin->setValue(1);
    connect(m_morphIterationsSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onMorphIterationsChanged);
    layout->addRow(tr("迭代次數:"), m_morphIterationsSpin);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createRoiGroup()
{
    QGroupBox* group = new QGroupBox(tr("📐 ROI 區域"));
    QVBoxLayout* mainLayout = new QVBoxLayout();

    m_roiEnabledCheck = new QCheckBox(tr("啟用 ROI"));
    m_roiEnabledCheck->setChecked(true);
    connect(m_roiEnabledCheck, &QCheckBox::toggled,
            this, &DebugPanelWidget::onRoiEnabledChanged);
    mainLayout->addWidget(m_roiEnabledCheck);

    QGridLayout* gridLayout = new QGridLayout();

    gridLayout->addWidget(new QLabel("X:"), 0, 0);
    m_roiXSpin = new QSpinBox();
    m_roiXSpin->setRange(0, 1920);
    m_roiXSpin->setValue(0);
    connect(m_roiXSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onRoiXChanged);
    gridLayout->addWidget(m_roiXSpin, 0, 1);

    gridLayout->addWidget(new QLabel("Y:"), 0, 2);
    m_roiYSpin = new QSpinBox();
    m_roiYSpin->setRange(0, 1080);
    m_roiYSpin->setValue(0);
    connect(m_roiYSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onRoiYChanged);
    gridLayout->addWidget(m_roiYSpin, 0, 3);

    gridLayout->addWidget(new QLabel("寬:"), 1, 0);
    m_roiWidthSpin = new QSpinBox();
    m_roiWidthSpin->setRange(10, 1920);
    m_roiWidthSpin->setValue(640);
    connect(m_roiWidthSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onRoiWidthChanged);
    gridLayout->addWidget(m_roiWidthSpin, 1, 1);

    gridLayout->addWidget(new QLabel("高:"), 1, 2);
    m_roiHeightSpin = new QSpinBox();
    m_roiHeightSpin->setRange(10, 1080);
    m_roiHeightSpin->setValue(150);
    connect(m_roiHeightSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onRoiHeightChanged);
    gridLayout->addWidget(m_roiHeightSpin, 1, 3);

    mainLayout->addLayout(gridLayout);

    // 拖拽框選 ROI 按鈕
    m_roiEditBtn = new QPushButton(tr("✎ 在畫面上框選 ROI"));
    m_roiEditBtn->setStyleSheet(
        "QPushButton { background-color: #1a3a5a; color: #00d4ff; border: 1px solid #00d4ff;"
        "              border-radius: 4px; padding: 5px; }"
        "QPushButton:hover { background-color: #1e4a7a; }"
        "QPushButton:pressed { background-color: #0d4a7a; }"
    );
    connect(m_roiEditBtn, &QPushButton::clicked,
            this, &DebugPanelWidget::roiEditModeRequested);
    mainLayout->addWidget(m_roiEditBtn);

    group->setLayout(mainLayout);
    return group;
}

QWidget* DebugPanelWidget::createGateGroup()
{
    QGroupBox* group = new QGroupBox(tr("🚪 虛擬光柵"));
    QFormLayout* layout = new QFormLayout();

    m_gateYPositionSpin = new QSpinBox();
    m_gateYPositionSpin->setRange(0, 1080);
    m_gateYPositionSpin->setValue(240);
    connect(m_gateYPositionSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateYPositionChanged);
    layout->addRow(tr("Y 位置:"), m_gateYPositionSpin);

    m_gateTriggerRadiusSpin = new QSpinBox();
    m_gateTriggerRadiusSpin->setRange(5, 100);
    m_gateTriggerRadiusSpin->setValue(20);
    connect(m_gateTriggerRadiusSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateTriggerRadiusChanged);
    layout->addRow(tr("觸發半徑:"), m_gateTriggerRadiusSpin);

    m_gateHistoryFramesSpin = new QSpinBox();
    m_gateHistoryFramesSpin->setRange(1, 30);
    m_gateHistoryFramesSpin->setValue(8);
    connect(m_gateHistoryFramesSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateHistoryFramesChanged);
    layout->addRow(tr("歷史幀數:"), m_gateHistoryFramesSpin);

    m_gateLinePositionSpin = new QDoubleSpinBox();
    m_gateLinePositionSpin->setRange(0.0, 1.0);
    m_gateLinePositionSpin->setSingleStep(0.05);
    m_gateLinePositionSpin->setValue(0.5);
    connect(m_gateLinePositionSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateLinePositionChanged);
    layout->addRow(tr("線位置比:"), m_gateLinePositionSpin);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createPerformanceGroup()
{
    QGroupBox* group = new QGroupBox(tr("⚡ 性能"));
    QFormLayout* layout = new QFormLayout();

    // 處理解析度：固定寬度選項，自動適應任何相機解析度
    // 實際縮放比例 = min(1.0, 選定寬度 / 相機原生寬度)
    m_imageScaleCombo = new QComboBox();
    m_imageScaleCombo->addItems({"原生解析度", "1280px", "640px ★", "480px", "320px"});
    m_imageScaleCombo->setCurrentIndex(2);  // 默認 640px（與演算法調參基準一致）
    m_imageScaleCombo->setToolTip(tr("檢測演算法使用的處理寬度。原始影像仍以全解析度顯示。\n"
                                     "640px ★ = 演算法調參基準值，大多數場景建議使用。"));
    connect(m_imageScaleCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &DebugPanelWidget::onProcessingWidthChanged);
    layout->addRow(tr("處理解析度:"), m_imageScaleCombo);

    m_skipFramesSpin = new QSpinBox();
    m_skipFramesSpin->setRange(0, 10);
    m_skipFramesSpin->setValue(0);
    connect(m_skipFramesSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onSkipFramesChanged);
    layout->addRow(tr("跳幀:"), m_skipFramesSpin);

    // 狀態顯示
    m_fpsLabel = new QLabel("FPS: --");
    layout->addRow(m_fpsLabel);

    m_frameCountLabel = new QLabel(tr("幀數: 0"));
    layout->addRow(m_frameCountLabel);

    m_detectionCountLabel = new QLabel(tr("檢測數: 0"));
    layout->addRow(m_detectionCountLabel);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createDebugViewGroup()
{
    QGroupBox* group = new QGroupBox(tr("🔍 調試視圖"));
    QVBoxLayout* layout = new QVBoxLayout();

    m_showDebugViewCheck = new QCheckBox(tr("顯示二值化圖像"));
    m_showDebugViewCheck->setChecked(false);
    connect(m_showDebugViewCheck, &QCheckBox::toggled,
            this, &DebugPanelWidget::onShowDebugViewChanged);
    layout->addWidget(m_showDebugViewCheck);

    m_debugImageLabel = new QLabel();
    m_debugImageLabel->setFixedSize(200, 100);
    m_debugImageLabel->setStyleSheet("background-color: #1a1a1a; border: 1px solid #333;");
    m_debugImageLabel->setAlignment(Qt::AlignCenter);
    m_debugImageLabel->setText(tr("無圖像"));
    m_debugImageLabel->setVisible(false);
    layout->addWidget(m_debugImageLabel);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createVideoControlGroup()
{
    QGroupBox* group = new QGroupBox(tr("🎬 視頻控制"));
    QVBoxLayout* layout = new QVBoxLayout();

    QHBoxLayout* btnLayout1 = new QHBoxLayout();
    m_loadVideoBtn = new QPushButton(tr("載入"));
    connect(m_loadVideoBtn, &QPushButton::clicked, this, &DebugPanelWidget::loadTestVideo);
    btnLayout1->addWidget(m_loadVideoBtn);

    m_playBtn = new QPushButton(tr("▶"));
    connect(m_playBtn, &QPushButton::clicked, this, &DebugPanelWidget::playVideo);
    btnLayout1->addWidget(m_playBtn);

    m_pauseBtn = new QPushButton(tr("⏸"));
    connect(m_pauseBtn, &QPushButton::clicked, this, &DebugPanelWidget::pauseVideo);
    btnLayout1->addWidget(m_pauseBtn);
    layout->addLayout(btnLayout1);

    QHBoxLayout* btnLayout2 = new QHBoxLayout();
    m_prevFrameBtn = new QPushButton(tr("◀"));
    connect(m_prevFrameBtn, &QPushButton::clicked, this, &DebugPanelWidget::prevFrame);
    btnLayout2->addWidget(m_prevFrameBtn);

    m_jumpFrameSpin = new QSpinBox();
    m_jumpFrameSpin->setRange(0, 999999);
    btnLayout2->addWidget(m_jumpFrameSpin);

    m_jumpFrameBtn = new QPushButton(tr("跳轉"));
    connect(m_jumpFrameBtn, &QPushButton::clicked, this, [this]() {
        emit jumpToFrame(m_jumpFrameSpin->value());
    });
    btnLayout2->addWidget(m_jumpFrameBtn);

    m_nextFrameBtn = new QPushButton(tr("▶"));
    connect(m_nextFrameBtn, &QPushButton::clicked, this, &DebugPanelWidget::nextFrame);
    btnLayout2->addWidget(m_nextFrameBtn);
    layout->addLayout(btnLayout2);

    m_screenshotBtn = new QPushButton(tr("📷 截圖"));
    connect(m_screenshotBtn, &QPushButton::clicked, this, &DebugPanelWidget::screenshot);
    layout->addWidget(m_screenshotBtn);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createYoloGroup()
{
    QGroupBox* group = new QGroupBox(tr("YOLO 偵測設定"));
    group->setStyleSheet("QGroupBox { font-weight: bold; color: #00d4ff; }");
    QFormLayout* layout = new QFormLayout();

    // 偵測模式選擇
    m_yoloModeCombo = new QComboBox();
    m_yoloModeCombo->addItems({tr("傳統 (MOG2)"), tr("YOLO"), tr("自動")});
    m_yoloModeCombo->setCurrentIndex(2); // 預設自動
    connect(m_yoloModeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &DebugPanelWidget::onYoloModeChanged);
    layout->addRow(tr("偵測模式:"), m_yoloModeCombo);

    // 信心閾值
    m_yoloConfidenceSpin = new QDoubleSpinBox();
    m_yoloConfidenceSpin->setRange(0.05, 0.95);
    m_yoloConfidenceSpin->setSingleStep(0.05);
    m_yoloConfidenceSpin->setDecimals(2);
    m_yoloConfidenceSpin->setValue(0.25);
    connect(m_yoloConfidenceSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onYoloConfidenceChanged);
    layout->addRow(tr("信心閾值:"), m_yoloConfidenceSpin);

    // NMS 閾值
    m_yoloNmsSpin = new QDoubleSpinBox();
    m_yoloNmsSpin->setRange(0.1, 0.9);
    m_yoloNmsSpin->setSingleStep(0.05);
    m_yoloNmsSpin->setDecimals(2);
    m_yoloNmsSpin->setValue(0.45);
    connect(m_yoloNmsSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onYoloNmsChanged);
    layout->addRow(tr("NMS 閾值:"), m_yoloNmsSpin);

    // ROI 放大倍數
    m_yoloRoiUpscaleSpin = new QDoubleSpinBox();
    m_yoloRoiUpscaleSpin->setRange(1.0, 4.0);
    m_yoloRoiUpscaleSpin->setSingleStep(0.5);
    m_yoloRoiUpscaleSpin->setDecimals(1);
    m_yoloRoiUpscaleSpin->setValue(2.0);
    connect(m_yoloRoiUpscaleSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onYoloRoiUpscaleChanged);
    layout->addRow(tr("ROI 放大:"), m_yoloRoiUpscaleSpin);

    // 載入模型按鈕
    m_loadYoloModelBtn = new QPushButton(tr("載入 ONNX 模型..."));
    connect(m_loadYoloModelBtn, &QPushButton::clicked,
            this, &DebugPanelWidget::loadYoloModelRequested);
    layout->addRow(m_loadYoloModelBtn);

    // 模型狀態
    m_yoloStatusLabel = new QLabel(tr("模型: 未載入"));
    m_yoloStatusLabel->setStyleSheet("color: #888;");
    layout->addRow(m_yoloStatusLabel);

    // 推理時間
    m_yoloInferenceLabel = new QLabel(tr("推理: -- ms"));
    m_yoloInferenceLabel->setStyleSheet("color: #888;");
    layout->addRow(m_yoloInferenceLabel);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createActionButtonsGroup()
{
    QGroupBox* group = new QGroupBox(tr("⚙️ 操作"));
    QVBoxLayout* layout = new QVBoxLayout();

    QHBoxLayout* btnLayout = new QHBoxLayout();

    m_resetParamsBtn = new QPushButton(tr("重置參數"));
    connect(m_resetParamsBtn, &QPushButton::clicked, this, &DebugPanelWidget::resetParams);
    btnLayout->addWidget(m_resetParamsBtn);

    m_saveConfigBtn = new QPushButton(tr("儲存"));
    connect(m_saveConfigBtn, &QPushButton::clicked, this, &DebugPanelWidget::saveConfig);
    btnLayout->addWidget(m_saveConfigBtn);

    m_loadConfigBtn = new QPushButton(tr("載入"));
    connect(m_loadConfigBtn, &QPushButton::clicked, this, &DebugPanelWidget::loadConfig);
    btnLayout->addWidget(m_loadConfigBtn);

    layout->addLayout(btnLayout);

    m_resetCountBtn = new QPushButton(tr("🔄 重置總計數"));
    connect(m_resetCountBtn, &QPushButton::clicked, this, &DebugPanelWidget::resetTotalCount);
    layout->addWidget(m_resetCountBtn);

    group->setLayout(layout);
    return group;
}

// ============================================================================
// 槽函數實現
// ============================================================================

void DebugPanelWidget::updateFps(double fps)
{
    m_fpsLabel->setText(QString("FPS: %1").arg(fps, 0, 'f', 1));
}

void DebugPanelWidget::updateFrameCount(int count)
{
    m_frameCountLabel->setText(tr("幀數: %1").arg(count));
}

void DebugPanelWidget::updateDetectionCount(int count)
{
    m_detectionCountLabel->setText(tr("檢測數: %1").arg(count));
}

void DebugPanelWidget::updateDebugImage(const cv::Mat& image)
{
    if (image.empty() || !m_showDebugView) return;

    // 將 cv::Mat 轉換為 QImage
    QImage qImg;
    if (image.channels() == 1) {
        qImg = QImage(image.data, image.cols, image.rows,
                      image.step, QImage::Format_Grayscale8);
    } else if (image.channels() == 3) {
        cv::Mat rgb;
        cv::cvtColor(image, rgb, cv::COLOR_BGR2RGB);
        qImg = QImage(rgb.data, rgb.cols, rgb.rows,
                      rgb.step, QImage::Format_RGB888);
    }

    // 縮放並顯示
    QPixmap pixmap = QPixmap::fromImage(qImg).scaled(
        m_debugImageLabel->size(), Qt::KeepAspectRatio, Qt::FastTransformation);
    m_debugImageLabel->setPixmap(pixmap);
}

void DebugPanelWidget::syncFromConfig()
{
    // TODO: 從配置載入參數並更新 UI
}

void DebugPanelWidget::onMinAreaChanged(int value)
{
    emit minAreaChanged(value);
    emit paramChanged("minArea", value);
}

void DebugPanelWidget::onMaxAreaChanged(int value)
{
    emit maxAreaChanged(value);
    emit paramChanged("maxArea", value);
}

void DebugPanelWidget::onBgHistoryChanged(int value)
{
    emit bgHistoryChanged(value);
    emit paramChanged("bgHistory", value);
}

void DebugPanelWidget::onBgVarThresholdChanged(int value)
{
    emit bgVarThresholdChanged(static_cast<double>(value));
    emit paramChanged("bgVarThreshold", value);
}

void DebugPanelWidget::onBgLearningRateChanged(double value)
{
    emit bgLearningRateChanged(value);
    emit paramChanged("bgLearningRate", value);
}

void DebugPanelWidget::onCannyLowChanged(int value)
{
    emit cannyLowChanged(value);
    emit paramChanged("cannyLow", value);
}

void DebugPanelWidget::onCannyHighChanged(int value)
{
    emit cannyHighChanged(value);
    emit paramChanged("cannyHigh", value);
}

void DebugPanelWidget::onMorphKernelSizeChanged(int value)
{
    // 確保為奇數
    if (value % 2 == 0) value++;
    emit morphKernelSizeChanged(value);
    emit paramChanged("morphKernelSize", value);
}

void DebugPanelWidget::onMorphIterationsChanged(int value)
{
    emit morphIterationsChanged(value);
    emit paramChanged("morphIterations", value);
}

void DebugPanelWidget::onRoiEnabledChanged(bool enabled)
{
    emit roiEnabledChanged(enabled);
    emit paramChanged("roiEnabled", enabled);
}

void DebugPanelWidget::onRoiXChanged(int value)
{
    emit roiChanged(value, m_roiYSpin->value(),
                    m_roiWidthSpin->value(), m_roiHeightSpin->value());
}

void DebugPanelWidget::onRoiYChanged(int value)
{
    emit roiChanged(m_roiXSpin->value(), value,
                    m_roiWidthSpin->value(), m_roiHeightSpin->value());
}

void DebugPanelWidget::onRoiWidthChanged(int value)
{
    emit roiChanged(m_roiXSpin->value(), m_roiYSpin->value(),
                    value, m_roiHeightSpin->value());
}

void DebugPanelWidget::onRoiHeightChanged(int value)
{
    emit roiChanged(m_roiXSpin->value(), m_roiYSpin->value(),
                    m_roiWidthSpin->value(), value);
}

void DebugPanelWidget::onGateYPositionChanged(int value)
{
    emit gateYPositionChanged(value);
    emit paramChanged("gateYPosition", value);
}

void DebugPanelWidget::onGateTriggerRadiusChanged(int value)
{
    emit gateTriggerRadiusChanged(value);
    emit paramChanged("gateTriggerRadius", value);
}

void DebugPanelWidget::onGateHistoryFramesChanged(int value)
{
    emit gateHistoryFramesChanged(value);
    emit paramChanged("gateHistoryFrames", value);
}

void DebugPanelWidget::onGateLinePositionChanged(double value)
{
    emit gateLinePositionChanged(value);
    emit paramChanged("gateLinePosition", value);
}

void DebugPanelWidget::onProcessingWidthChanged(int index)
{
    // 0=原生(0表示不縮放), 1=1280, 2=640, 3=480, 4=320
    int widths[] = {0, 1280, 640, 480, 320};
    if (index >= 0 && index < 5) {
        emit processingWidthChanged(widths[index]);
        emit paramChanged("targetProcessingWidth", widths[index]);
    }
}

void DebugPanelWidget::onSkipFramesChanged(int value)
{
    emit skipFramesChanged(value);
    emit paramChanged("skipFrames", value);
}

void DebugPanelWidget::onShowDebugViewChanged(bool show)
{
    m_showDebugView = show;
    m_debugImageLabel->setVisible(show);
    emit debugViewToggled(show);
}

void DebugPanelWidget::onLockParamsChanged(bool locked)
{
    for (auto* w : m_paramGroupWidgets) {
        w->setEnabled(!locked);
    }
}

// ============================================================================
// YOLO 槽函數
// ============================================================================

void DebugPanelWidget::onYoloModeChanged(int index)
{
    emit yoloModeChanged(index);
}

void DebugPanelWidget::onYoloConfidenceChanged(double value)
{
    emit yoloConfidenceChanged(value);
}

void DebugPanelWidget::onYoloNmsChanged(double value)
{
    emit yoloNmsThresholdChanged(value);
}

void DebugPanelWidget::onYoloRoiUpscaleChanged(double value)
{
    emit yoloRoiUpscaleChanged(value);
}

void DebugPanelWidget::updateYoloModelStatus(bool loaded)
{
    if (loaded)
    {
        m_yoloStatusLabel->setText(tr("模型: 已載入"));
        m_yoloStatusLabel->setStyleSheet("color: #00ff88; font-weight: bold;");
    }
    else
    {
        m_yoloStatusLabel->setText(tr("模型: 未載入"));
        m_yoloStatusLabel->setStyleSheet("color: #888;");
    }
}

void DebugPanelWidget::updateYoloInferenceTime(double ms)
{
    m_yoloInferenceLabel->setText(QString(tr("推理: %1 ms")).arg(ms, 0, 'f', 1));

    // 依據推理時間變色：< 30ms 綠色, < 100ms 黃色, > 100ms 紅色
    if (ms < 30.0)
    {
        m_yoloInferenceLabel->setStyleSheet("color: #00ff88;");
    }
    else if (ms < 100.0)
    {
        m_yoloInferenceLabel->setStyleSheet("color: #ffcc00;");
    }
    else
    {
        m_yoloInferenceLabel->setStyleSheet("color: #ff4444;");
    }
}

void DebugPanelWidget::setRoiValues(int x, int y, int w, int h)
{
    // 靜默更新 4 個 SpinBox，避免觸發 roiChanged 4 次
    m_roiXSpin->blockSignals(true);
    m_roiYSpin->blockSignals(true);
    m_roiWidthSpin->blockSignals(true);
    m_roiHeightSpin->blockSignals(true);

    m_roiXSpin->setValue(x);
    m_roiYSpin->setValue(y);
    m_roiWidthSpin->setValue(w);
    m_roiHeightSpin->setValue(h);

    m_roiXSpin->blockSignals(false);
    m_roiYSpin->blockSignals(false);
    m_roiWidthSpin->blockSignals(false);
    m_roiHeightSpin->blockSignals(false);
}

} // namespace basler
