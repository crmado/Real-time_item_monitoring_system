#include "ui/widgets/recording_control.h"
#include <QVBoxLayout>
#include <QHBoxLayout>

namespace basler {

RecordingControlWidget::RecordingControlWidget(QWidget* parent)
    : QWidget(parent)
{
    initUi();

    // 更新計時器
    m_updateTimer = new QTimer(this);
    connect(m_updateTimer, &QTimer::timeout, this, &RecordingControlWidget::updateTimer);
}

void RecordingControlWidget::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    // 創建分組框
    m_groupBox = new QGroupBox(tr("🎬 錄影控制"));
    QVBoxLayout* groupLayout = new QVBoxLayout();

    // 控制按鈕
    QHBoxLayout* btnLayout = new QHBoxLayout();
    m_startBtn = new QPushButton(tr("⏺ 開始錄影"));
    m_startBtn->setStyleSheet("QPushButton { color: #ff4444; }");
    connect(m_startBtn, &QPushButton::clicked, this, &RecordingControlWidget::onStartClicked);

    m_stopBtn = new QPushButton(tr("⏹ 停止錄影"));
    m_stopBtn->setEnabled(false);
    connect(m_stopBtn, &QPushButton::clicked, this, &RecordingControlWidget::onStopClicked);

    btnLayout->addWidget(m_startBtn);
    btnLayout->addWidget(m_stopBtn);
    groupLayout->addLayout(btnLayout);

    // 狀態顯示
    m_statusLabel = new QLabel(tr("狀態: 待機"));
    m_statusLabel->setStyleSheet("font-weight: bold;");
    groupLayout->addWidget(m_statusLabel);

    // 幀數顯示
    m_framesLabel = new QLabel(tr("已錄製: 0 幀"));
    groupLayout->addWidget(m_framesLabel);

    // 時長顯示
    m_durationLabel = new QLabel(tr("時長: 00:00"));
    groupLayout->addWidget(m_durationLabel);

    m_groupBox->setLayout(groupLayout);
    mainLayout->addWidget(m_groupBox);
    mainLayout->addStretch();
}

void RecordingControlWidget::onStartClicked()
{
    emit startRecording();
}

void RecordingControlWidget::onStopClicked()
{
    emit stopRecording();
}

void RecordingControlWidget::setRecordingState(bool recording)
{
    m_isRecording = recording;

    m_startBtn->setEnabled(!recording);
    m_stopBtn->setEnabled(recording);

    if (recording) {
        m_statusLabel->setText(tr("狀態: 錄影中..."));
        m_statusLabel->setStyleSheet("font-weight: bold; color: #ff4444;");
        m_elapsedTimer.start();
        m_updateTimer->start(100);  // 每 100ms 更新
    } else {
        m_statusLabel->setText(tr("狀態: 待機"));
        m_statusLabel->setStyleSheet("font-weight: bold; color: inherit;");
        m_updateTimer->stop();
    }
}

void RecordingControlWidget::updateStats(int frames, double duration)
{
    m_framesRecorded = frames;
    m_framesLabel->setText(tr("已錄製: %1 幀").arg(frames));

    int minutes = static_cast<int>(duration) / 60;
    int seconds = static_cast<int>(duration) % 60;
    m_durationLabel->setText(tr("時長: %1:%2")
        .arg(minutes, 2, 10, QChar('0'))
        .arg(seconds, 2, 10, QChar('0')));
}

void RecordingControlWidget::updateTimer()
{
    if (m_isRecording) {
        double elapsed = m_elapsedTimer.elapsed() / 1000.0;
        int minutes = static_cast<int>(elapsed) / 60;
        int seconds = static_cast<int>(elapsed) % 60;
        m_durationLabel->setText(tr("時長: %1:%2")
            .arg(minutes, 2, 10, QChar('0'))
            .arg(seconds, 2, 10, QChar('0')));
    }
}

void RecordingControlWidget::setEnabled(bool enabled)
{
    m_groupBox->setEnabled(enabled);
    if (!enabled) {
        setRecordingState(false);
    }
}

} // namespace basler
