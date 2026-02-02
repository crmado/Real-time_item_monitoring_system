#include "ui/widgets/debug_panel.h"
#include "config/settings.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QGroupBox>

namespace basler {

DebugPanelWidget::DebugPanelWidget(QWidget* parent)
    : QWidget(parent)
{
    initUi();
    syncFromConfig();
}

void DebugPanelWidget::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    // 創建滾動區域
    m_scrollArea = new QScrollArea();
    m_scrollArea->setWidgetResizable(true);
    m_scrollArea->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);

    QWidget* scrollContent = new QWidget();
    QVBoxLayout* contentLayout = new QVBoxLayout(scrollContent);

    // 狀態顯示
    QGroupBox* statusGroup = new QGroupBox(tr("📊 狀態"));
    QGridLayout* statusLayout = new QGridLayout();

    statusLayout->addWidget(new QLabel(tr("FPS:")), 0, 0);
    m_fpsLabel = new QLabel("0.0");
    m_fpsLabel->setStyleSheet("font-weight: bold;");
    statusLayout->addWidget(m_fpsLabel, 0, 1);

    statusLayout->addWidget(new QLabel(tr("幀數:")), 1, 0);
    m_frameCountLabel = new QLabel("0");
    statusLayout->addWidget(m_frameCountLabel, 1, 1);

    statusLayout->addWidget(new QLabel(tr("計數:")), 2, 0);
    m_detectionCountLabel = new QLabel("0");
    m_detectionCountLabel->setStyleSheet("font-weight: bold; color: #00ff00;");
    statusLayout->addWidget(m_detectionCountLabel, 2, 1);

    statusGroup->setLayout(statusLayout);
    contentLayout->addWidget(statusGroup);

    // 檢測參數組
    contentLayout->addWidget(createDetectionParamsGroup());

    // 背景減除參數組
    contentLayout->addWidget(createBgSubtractorGroup());

    // ROI 參數組
    contentLayout->addWidget(createRoiGroup());

    // 虛擬光柵參數組
    contentLayout->addWidget(createGateGroup());

    // 性能參數組
    contentLayout->addWidget(createPerformanceGroup());

    // 視頻控制組
    contentLayout->addWidget(createVideoControlGroup());

    // 操作按鈕組
    contentLayout->addWidget(createActionButtonsGroup());

    contentLayout->addStretch();

    m_scrollArea->setWidget(scrollContent);
    mainLayout->addWidget(m_scrollArea);
}

QWidget* DebugPanelWidget::createDetectionParamsGroup()
{
    QGroupBox* group = new QGroupBox(tr("🔍 檢測參數"));
    QGridLayout* layout = new QGridLayout();

    layout->addWidget(new QLabel(tr("最小面積:")), 0, 0);
    m_minAreaSpin = new QSpinBox();
    m_minAreaSpin->setRange(1, 100);
    connect(m_minAreaSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onMinAreaChanged);
    layout->addWidget(m_minAreaSpin, 0, 1);

    layout->addWidget(new QLabel(tr("最大面積:")), 1, 0);
    m_maxAreaSpin = new QSpinBox();
    m_maxAreaSpin->setRange(500, 10000);
    connect(m_maxAreaSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onMaxAreaChanged);
    layout->addWidget(m_maxAreaSpin, 1, 1);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createBgSubtractorGroup()
{
    QGroupBox* group = new QGroupBox(tr("🎨 背景減除"));
    QGridLayout* layout = new QGridLayout();

    layout->addWidget(new QLabel(tr("變異閾值:")), 0, 0);
    m_bgVarThresholdSpin = new QSpinBox();
    m_bgVarThresholdSpin->setRange(1, 20);
    connect(m_bgVarThresholdSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onBgVarThresholdChanged);
    layout->addWidget(m_bgVarThresholdSpin, 0, 1);

    layout->addWidget(new QLabel(tr("學習率:")), 1, 0);
    m_bgLearningRateSpin = new QDoubleSpinBox();
    m_bgLearningRateSpin->setRange(0.0001, 0.1);
    m_bgLearningRateSpin->setSingleStep(0.0001);
    m_bgLearningRateSpin->setDecimals(4);
    connect(m_bgLearningRateSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onBgLearningRateChanged);
    layout->addWidget(m_bgLearningRateSpin, 1, 1);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createRoiGroup()
{
    QGroupBox* group = new QGroupBox(tr("📐 ROI 區域"));
    QGridLayout* layout = new QGridLayout();

    m_roiEnabledCheck = new QCheckBox(tr("啟用 ROI"));
    connect(m_roiEnabledCheck, &QCheckBox::toggled,
            this, &DebugPanelWidget::onRoiEnabledChanged);
    layout->addWidget(m_roiEnabledCheck, 0, 0, 1, 2);

    layout->addWidget(new QLabel(tr("高度:")), 1, 0);
    m_roiHeightSpin = new QSpinBox();
    m_roiHeightSpin->setRange(50, 400);
    connect(m_roiHeightSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onRoiHeightChanged);
    layout->addWidget(m_roiHeightSpin, 1, 1);

    layout->addWidget(new QLabel(tr("位置比例:")), 2, 0);
    m_roiPositionSpin = new QDoubleSpinBox();
    m_roiPositionSpin->setRange(0.0, 1.0);
    m_roiPositionSpin->setSingleStep(0.05);
    m_roiPositionSpin->setDecimals(2);
    connect(m_roiPositionSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onRoiPositionChanged);
    layout->addWidget(m_roiPositionSpin, 2, 1);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createGateGroup()
{
    QGroupBox* group = new QGroupBox(tr("🚪 虛擬光柵"));
    QGridLayout* layout = new QGridLayout();

    layout->addWidget(new QLabel(tr("觸發半徑:")), 0, 0);
    m_gateTriggerRadiusSpin = new QSpinBox();
    m_gateTriggerRadiusSpin->setRange(5, 50);
    connect(m_gateTriggerRadiusSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateTriggerRadiusChanged);
    layout->addWidget(m_gateTriggerRadiusSpin, 0, 1);

    layout->addWidget(new QLabel(tr("歷史幀數:")), 1, 0);
    m_gateHistoryFramesSpin = new QSpinBox();
    m_gateHistoryFramesSpin->setRange(3, 20);
    connect(m_gateHistoryFramesSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateHistoryFramesChanged);
    layout->addWidget(m_gateHistoryFramesSpin, 1, 1);

    layout->addWidget(new QLabel(tr("線位置:")), 2, 0);
    m_gateLinePositionSpin = new QDoubleSpinBox();
    m_gateLinePositionSpin->setRange(0.0, 1.0);
    m_gateLinePositionSpin->setSingleStep(0.05);
    m_gateLinePositionSpin->setDecimals(2);
    connect(m_gateLinePositionSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateLinePositionChanged);
    layout->addWidget(m_gateLinePositionSpin, 2, 1);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createPerformanceGroup()
{
    QGroupBox* group = new QGroupBox(tr("⚡ 性能"));
    QGridLayout* layout = new QGridLayout();

    layout->addWidget(new QLabel(tr("圖像縮放:")), 0, 0);
    m_imageScaleCombo = new QComboBox();
    m_imageScaleCombo->addItems({"100% (原始)", "75%", "50%", "30%"});
    connect(m_imageScaleCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &DebugPanelWidget::onImageScaleChanged);
    layout->addWidget(m_imageScaleCombo, 0, 1);

    layout->addWidget(new QLabel(tr("跳幀數:")), 1, 0);
    m_skipFramesSpin = new QSpinBox();
    m_skipFramesSpin->setRange(0, 10);
    connect(m_skipFramesSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onSkipFramesChanged);
    layout->addWidget(m_skipFramesSpin, 1, 1);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createVideoControlGroup()
{
    QGroupBox* group = new QGroupBox(tr("🎬 視頻控制"));
    QVBoxLayout* layout = new QVBoxLayout();

    m_loadVideoBtn = new QPushButton(tr("📂 載入測試視頻"));
    connect(m_loadVideoBtn, &QPushButton::clicked, this, &DebugPanelWidget::loadTestVideo);
    layout->addWidget(m_loadVideoBtn);

    QHBoxLayout* playLayout = new QHBoxLayout();
    m_playBtn = new QPushButton(tr("▶"));
    m_playBtn->setMaximumWidth(40);
    connect(m_playBtn, &QPushButton::clicked, this, &DebugPanelWidget::playVideo);
    playLayout->addWidget(m_playBtn);

    m_pauseBtn = new QPushButton(tr("⏸"));
    m_pauseBtn->setMaximumWidth(40);
    connect(m_pauseBtn, &QPushButton::clicked, this, &DebugPanelWidget::pauseVideo);
    playLayout->addWidget(m_pauseBtn);

    m_prevFrameBtn = new QPushButton(tr("⏮"));
    m_prevFrameBtn->setMaximumWidth(40);
    connect(m_prevFrameBtn, &QPushButton::clicked, this, &DebugPanelWidget::prevFrame);
    playLayout->addWidget(m_prevFrameBtn);

    m_nextFrameBtn = new QPushButton(tr("⏭"));
    m_nextFrameBtn->setMaximumWidth(40);
    connect(m_nextFrameBtn, &QPushButton::clicked, this, &DebugPanelWidget::nextFrame);
    playLayout->addWidget(m_nextFrameBtn);

    layout->addLayout(playLayout);

    QHBoxLayout* jumpLayout = new QHBoxLayout();
    m_jumpFrameSpin = new QSpinBox();
    m_jumpFrameSpin->setRange(0, 99999);
    jumpLayout->addWidget(m_jumpFrameSpin);

    QPushButton* jumpBtn = new QPushButton(tr("跳轉"));
    connect(jumpBtn, &QPushButton::clicked, [this]() {
        emit jumpToFrame(m_jumpFrameSpin->value());
    });
    jumpLayout->addWidget(jumpBtn);
    layout->addLayout(jumpLayout);

    m_screenshotBtn = new QPushButton(tr("📷 截圖"));
    connect(m_screenshotBtn, &QPushButton::clicked, this, &DebugPanelWidget::screenshot);
    layout->addWidget(m_screenshotBtn);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createActionButtonsGroup()
{
    QGroupBox* group = new QGroupBox(tr("🛠 操作"));
    QVBoxLayout* layout = new QVBoxLayout();

    m_resetParamsBtn = new QPushButton(tr("🔄 重置參數"));
    connect(m_resetParamsBtn, &QPushButton::clicked, this, &DebugPanelWidget::resetParams);
    layout->addWidget(m_resetParamsBtn);

    QHBoxLayout* configLayout = new QHBoxLayout();
    m_saveConfigBtn = new QPushButton(tr("💾 保存"));
    connect(m_saveConfigBtn, &QPushButton::clicked, this, &DebugPanelWidget::saveConfig);
    configLayout->addWidget(m_saveConfigBtn);

    m_loadConfigBtn = new QPushButton(tr("📂 載入"));
    connect(m_loadConfigBtn, &QPushButton::clicked, this, &DebugPanelWidget::loadConfig);
    configLayout->addWidget(m_loadConfigBtn);
    layout->addLayout(configLayout);

    m_resetCountBtn = new QPushButton(tr("🔢 重置計數"));
    connect(m_resetCountBtn, &QPushButton::clicked, this, &DebugPanelWidget::resetTotalCount);
    layout->addWidget(m_resetCountBtn);

    group->setLayout(layout);
    return group;
}

void DebugPanelWidget::syncFromConfig()
{
    const auto& config = getConfig();
    const auto& det = config.detection();
    const auto& gate = config.gate();
    const auto& perf = config.performance();

    // 阻止信號發射
    m_minAreaSpin->blockSignals(true);
    m_maxAreaSpin->blockSignals(true);
    m_bgVarThresholdSpin->blockSignals(true);
    m_bgLearningRateSpin->blockSignals(true);
    m_roiEnabledCheck->blockSignals(true);
    m_roiHeightSpin->blockSignals(true);
    m_roiPositionSpin->blockSignals(true);
    m_gateTriggerRadiusSpin->blockSignals(true);
    m_gateHistoryFramesSpin->blockSignals(true);
    m_gateLinePositionSpin->blockSignals(true);
    m_skipFramesSpin->blockSignals(true);

    // 設置值
    m_minAreaSpin->setValue(det.minArea);
    m_maxAreaSpin->setValue(det.maxArea);
    m_bgVarThresholdSpin->setValue(det.bgVarThreshold);
    m_bgLearningRateSpin->setValue(det.bgLearningRate);
    m_roiEnabledCheck->setChecked(det.roiEnabled);
    m_roiHeightSpin->setValue(det.roiHeight);
    m_roiPositionSpin->setValue(det.roiPositionRatio);
    m_gateTriggerRadiusSpin->setValue(gate.gateTriggerRadius);
    m_gateHistoryFramesSpin->setValue(gate.gateHistoryFrames);
    m_gateLinePositionSpin->setValue(gate.gateLinePositionRatio);
    m_skipFramesSpin->setValue(perf.skipFrames);

    // 恢復信號
    m_minAreaSpin->blockSignals(false);
    m_maxAreaSpin->blockSignals(false);
    m_bgVarThresholdSpin->blockSignals(false);
    m_bgLearningRateSpin->blockSignals(false);
    m_roiEnabledCheck->blockSignals(false);
    m_roiHeightSpin->blockSignals(false);
    m_roiPositionSpin->blockSignals(false);
    m_gateTriggerRadiusSpin->blockSignals(false);
    m_gateHistoryFramesSpin->blockSignals(false);
    m_gateLinePositionSpin->blockSignals(false);
    m_skipFramesSpin->blockSignals(false);
}

void DebugPanelWidget::updateFps(double fps)
{
    m_fpsLabel->setText(QString::number(fps, 'f', 1));
}

void DebugPanelWidget::updateFrameCount(int count)
{
    m_frameCountLabel->setText(QString::number(count));
}

void DebugPanelWidget::updateDetectionCount(int count)
{
    m_detectionCountLabel->setText(QString::number(count));
}

// 槽函數實現
void DebugPanelWidget::onMinAreaChanged(int value) {
    emit paramChanged("minArea", value);
}

void DebugPanelWidget::onMaxAreaChanged(int value) {
    emit paramChanged("maxArea", value);
}

void DebugPanelWidget::onBgVarThresholdChanged(int value) {
    emit paramChanged("bgVarThreshold", value);
}

void DebugPanelWidget::onBgLearningRateChanged(double value) {
    emit paramChanged("bgLearningRate", value);
}

void DebugPanelWidget::onRoiEnabledChanged(bool enabled) {
    emit paramChanged("roiEnabled", enabled);
}

void DebugPanelWidget::onRoiHeightChanged(int value) {
    emit paramChanged("roiHeight", value);
}

void DebugPanelWidget::onRoiPositionChanged(double value) {
    emit paramChanged("roiPositionRatio", value);
}

void DebugPanelWidget::onGateTriggerRadiusChanged(int value) {
    emit paramChanged("gateTriggerRadius", value);
}

void DebugPanelWidget::onGateHistoryFramesChanged(int value) {
    emit paramChanged("gateHistoryFrames", value);
}

void DebugPanelWidget::onGateLinePositionChanged(double value) {
    emit paramChanged("gateLinePositionRatio", value);
}

void DebugPanelWidget::onImageScaleChanged(int index) {
    QStringList scales = {"1.0", "0.75", "0.5", "0.3"};
    if (index >= 0 && index < scales.size()) {
        emit paramChanged("imageScale", scales[index].toDouble());
    }
}

void DebugPanelWidget::onSkipFramesChanged(int value) {
    emit paramChanged("skipFrames", value);
}

} // namespace basler
