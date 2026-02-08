#include "ui/widgets/camera_control.h"
#include <QVBoxLayout>
#include <QHBoxLayout>

namespace basler {

CameraControlWidget::CameraControlWidget(QWidget* parent)
    : QWidget(parent)
{
    initUi();
}

void CameraControlWidget::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    m_groupBox = new QGroupBox(tr("📷 相機控制"));
    QVBoxLayout* groupLayout = new QVBoxLayout();

    // Detection buttons layout
    QHBoxLayout* detectLayout = new QHBoxLayout();

    // Quick detect button (single scan)
    m_detectBtn = new QPushButton(tr("Quick Scan"));
    m_detectBtn->setToolTip(tr("Single scan - fast but may miss cameras that are booting"));
    connect(m_detectBtn, &QPushButton::clicked, this, &CameraControlWidget::detectRequested);
    detectLayout->addWidget(m_detectBtn);

    // Auto-retry detect button (recommended)
    m_autoDetectBtn = new QPushButton(tr("🔍 Auto-Detect (Recommended)"));
    m_autoDetectBtn->setToolTip(tr("Smart scan with 3 auto-retries - finds cameras that need time to boot"));
    m_autoDetectBtn->setStyleSheet("font-weight: bold;");
    connect(m_autoDetectBtn, &QPushButton::clicked, this, &CameraControlWidget::detectWithRetryRequested);
    detectLayout->addWidget(m_autoDetectBtn);

    groupLayout->addLayout(detectLayout);

    // 相機選擇（ComboBox）
    m_cameraCombo = new QComboBox();
    m_cameraCombo->setPlaceholderText(tr("選擇相機..."));
    groupLayout->addWidget(m_cameraCombo);

    // 連接/斷開按鈕
    QHBoxLayout* connectLayout = new QHBoxLayout();
    m_connectBtn = new QPushButton(tr("連接"));
    m_connectBtn->setEnabled(false);
    connect(m_connectBtn, &QPushButton::clicked, this, &CameraControlWidget::connectRequested);
    connectLayout->addWidget(m_connectBtn);

    m_disconnectBtn = new QPushButton(tr("斷開"));
    m_disconnectBtn->setEnabled(false);
    connect(m_disconnectBtn, &QPushButton::clicked, this, &CameraControlWidget::disconnectRequested);
    connectLayout->addWidget(m_disconnectBtn);
    groupLayout->addLayout(connectLayout);

    // 抓取控制按鈕
    QHBoxLayout* grabLayout = new QHBoxLayout();
    m_startBtn = new QPushButton(tr("▶ 開始"));
    m_startBtn->setEnabled(false);
    connect(m_startBtn, &QPushButton::clicked, this, &CameraControlWidget::startGrabRequested);
    grabLayout->addWidget(m_startBtn);

    m_stopBtn = new QPushButton(tr("⏹ 停止"));
    m_stopBtn->setEnabled(false);
    connect(m_stopBtn, &QPushButton::clicked, this, &CameraControlWidget::stopGrabRequested);
    grabLayout->addWidget(m_stopBtn);
    groupLayout->addLayout(grabLayout);

    // 曝光控制
    QHBoxLayout* exposureLayout = new QHBoxLayout();
    exposureLayout->addWidget(new QLabel(tr("曝光:")));

    m_exposureSlider = new QSlider(Qt::Horizontal);
    m_exposureSlider->setRange(100, 100000);  // 100us - 100ms
    m_exposureSlider->setValue(10000);        // 默認 10ms
    connect(m_exposureSlider, &QSlider::valueChanged,
            this, &CameraControlWidget::onExposureChanged);
    exposureLayout->addWidget(m_exposureSlider);

    m_exposureLabel = new QLabel("10000 μs");
    m_exposureLabel->setMinimumWidth(80);
    exposureLayout->addWidget(m_exposureLabel);
    groupLayout->addLayout(exposureLayout);

    m_groupBox->setLayout(groupLayout);
    mainLayout->addWidget(m_groupBox);
    mainLayout->addStretch();

    // 連接 combo box 選擇變更
    connect(m_cameraCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            [this](int index) {
                m_connectBtn->setEnabled(index >= 0 && !m_isConnected && !m_isVideoMode);
            });
}

void CameraControlWidget::setCameraList(const QStringList& cameras)
{
    m_cameraCombo->clear();
    m_cameraCombo->addItems(cameras);

    if (!cameras.isEmpty()) {
        m_cameraCombo->setCurrentIndex(0);
        m_connectBtn->setEnabled(!m_isConnected && !m_isVideoMode);
    } else {
        m_connectBtn->setEnabled(false);
    }
}

void CameraControlWidget::setConnected(bool connected)
{
    m_isConnected = connected;
    updateButtonStates();
}

void CameraControlWidget::setGrabbing(bool grabbing)
{
    m_isGrabbing = grabbing;
    updateButtonStates();
}

void CameraControlWidget::setVideoMode(bool isVideo)
{
    m_isVideoMode = isVideo;

    // 視頻模式下禁用相機相關控制
    m_detectBtn->setEnabled(!isVideo);
    m_cameraCombo->setEnabled(!isVideo);
    m_connectBtn->setEnabled(!isVideo && m_cameraCombo->count() > 0 && !m_isConnected);
    m_disconnectBtn->setEnabled(!isVideo && m_isConnected);
    m_exposureSlider->setEnabled(!isVideo);

    if (isVideo) {
        m_startBtn->setEnabled(true);
        m_stopBtn->setEnabled(false);
    }
}

void CameraControlWidget::updateButtonStates()
{
    if (m_isVideoMode) return;

    m_detectBtn->setEnabled(!m_isConnected);
    m_cameraCombo->setEnabled(!m_isConnected);
    m_connectBtn->setEnabled(!m_isConnected && m_cameraCombo->count() > 0);
    m_disconnectBtn->setEnabled(m_isConnected && !m_isGrabbing);
    m_startBtn->setEnabled(m_isConnected && !m_isGrabbing);
    m_stopBtn->setEnabled(m_isGrabbing);
    m_exposureSlider->setEnabled(m_isConnected && !m_isGrabbing);
}

void CameraControlWidget::onExposureChanged(int value)
{
    m_exposureLabel->setText(QString("%1 μs").arg(value));
    emit exposureChanged(static_cast<double>(value));
}

} // namespace basler
