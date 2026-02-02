#include "ui/widgets/camera_control.h"
#include "core/camera_controller.h"
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

    // 創建分組框
    m_groupBox = new QGroupBox(tr("📷 相機控制"));
    QVBoxLayout* groupLayout = new QVBoxLayout();

    // 檢測按鈕
    m_detectBtn = new QPushButton(tr(" 檢測相機"));
    m_detectBtn->setStyleSheet("padding-left: 8px;");
    connect(m_detectBtn, &QPushButton::clicked, this, &CameraControlWidget::detectClicked);
    groupLayout->addWidget(m_detectBtn);

    // 相機列表
    groupLayout->addWidget(new QLabel(tr("可用相機:")));
    m_cameraList = new QListWidget();
    m_cameraList->setMaximumHeight(150);
    connect(m_cameraList, &QListWidget::itemClicked, this, &CameraControlWidget::onCameraSelected);
    groupLayout->addWidget(m_cameraList);

    // 連接/斷開按鈕
    QHBoxLayout* btnLayout = new QHBoxLayout();
    m_connectBtn = new QPushButton(tr("連接"));
    m_connectBtn->setEnabled(false);
    connect(m_connectBtn, &QPushButton::clicked, this, &CameraControlWidget::onConnectClicked);

    m_disconnectBtn = new QPushButton(tr("斷開"));
    m_disconnectBtn->setEnabled(false);
    connect(m_disconnectBtn, &QPushButton::clicked, this, &CameraControlWidget::disconnectClicked);

    btnLayout->addWidget(m_connectBtn);
    btnLayout->addWidget(m_disconnectBtn);
    groupLayout->addLayout(btnLayout);

    // 開始/停止抓取
    QHBoxLayout* grabLayout = new QHBoxLayout();
    m_startBtn = new QPushButton(tr(" 開始抓取"));
    m_startBtn->setStyleSheet("padding-left: 8px;");
    m_startBtn->setEnabled(false);
    connect(m_startBtn, &QPushButton::clicked, this, &CameraControlWidget::startClicked);

    m_stopBtn = new QPushButton(tr(" 停止抓取"));
    m_stopBtn->setStyleSheet("padding-left: 8px;");
    m_stopBtn->setEnabled(false);
    connect(m_stopBtn, &QPushButton::clicked, this, &CameraControlWidget::stopClicked);

    grabLayout->addWidget(m_startBtn);
    grabLayout->addWidget(m_stopBtn);
    groupLayout->addLayout(grabLayout);

    // 曝光控制
    groupLayout->addWidget(new QLabel(tr("曝光時間 (μs):")));
    QHBoxLayout* exposureLayout = new QHBoxLayout();

    m_exposureSlider = new QSlider(Qt::Horizontal);
    m_exposureSlider->setMinimum(100);
    m_exposureSlider->setMaximum(10000);
    m_exposureSlider->setValue(1000);
    m_exposureSlider->setEnabled(false);
    connect(m_exposureSlider, &QSlider::valueChanged, this, &CameraControlWidget::onExposureChanged);

    m_exposureLabel = new QLabel("1000");
    exposureLayout->addWidget(m_exposureSlider);
    exposureLayout->addWidget(m_exposureLabel);
    groupLayout->addLayout(exposureLayout);

    m_groupBox->setLayout(groupLayout);
    mainLayout->addWidget(m_groupBox);

    // 添加彈性空間
    mainLayout->addStretch();
}

void CameraControlWidget::updateCameraList(const std::vector<CameraInfo>& cameras)
{
    m_cameraList->clear();

    for (const auto& camera : cameras) {
        QString itemText = QString("%1 (%2)").arg(camera.model, camera.serial);
        if (camera.isTargetModel) {
            itemText += " ✓";
        }

        QListWidgetItem* item = new QListWidgetItem(itemText);
        item->setData(Qt::UserRole, camera.index);
        m_cameraList->addItem(item);
    }
}

void CameraControlWidget::onCameraSelected(QListWidgetItem* item)
{
    m_selectedCameraIndex = item->data(Qt::UserRole).toInt();
    m_connectBtn->setEnabled(true);
}

void CameraControlWidget::onConnectClicked()
{
    if (m_selectedCameraIndex >= 0) {
        emit connectClicked(m_selectedCameraIndex);
    }
}

void CameraControlWidget::onExposureChanged(int value)
{
    m_exposureLabel->setText(QString::number(value));
    emit exposureChanged(static_cast<double>(value));
}

void CameraControlWidget::setGrabbingState(bool grabbing)
{
    m_startBtn->setEnabled(!grabbing);
    m_stopBtn->setEnabled(grabbing);
}

void CameraControlWidget::setConnectedState(bool connected)
{
    m_disconnectBtn->setEnabled(connected);
    m_startBtn->setEnabled(connected);
    m_exposureSlider->setEnabled(connected);

    if (!connected) {
        m_stopBtn->setEnabled(false);
    }
}

void CameraControlWidget::setVideoMode(bool isVideo)
{
    if (isVideo) {
        // 視頻模式
        m_detectBtn->setEnabled(false);
        m_cameraList->setEnabled(false);
        m_connectBtn->setEnabled(false);
        m_disconnectBtn->setEnabled(false);
        m_exposureSlider->setEnabled(false);
        m_startBtn->setEnabled(true);
        m_startBtn->setText(tr(" 播放"));
        m_stopBtn->setText(tr(" 暫停"));
    } else {
        // 相機模式
        m_detectBtn->setEnabled(true);
        m_cameraList->setEnabled(true);
        m_startBtn->setText(tr(" 開始抓取"));
        m_stopBtn->setText(tr(" 停止抓取"));
    }
}

} // namespace basler
