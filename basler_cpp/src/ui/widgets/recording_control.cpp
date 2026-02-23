#include "ui/widgets/recording_control.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFileDialog>
#include <QDir>

namespace basler {

RecordingControlWidget::RecordingControlWidget(QWidget* parent)
    : QWidget(parent)
{
    initUi();

    m_updateTimer = new QTimer(this);
    connect(m_updateTimer, &QTimer::timeout, this, &RecordingControlWidget::updateTimer);
}

void RecordingControlWidget::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    m_groupBox = new QGroupBox(tr("🎬 錄影控制"));
    QVBoxLayout* groupLayout = new QVBoxLayout();

    // 輸出路徑
    QHBoxLayout* pathLayout = new QHBoxLayout();
    pathLayout->addWidget(new QLabel(tr("路徑:")));

    m_pathEdit = new QLineEdit();
    m_pathEdit->setPlaceholderText(tr("選擇輸出目錄..."));
    m_pathEdit->setText(QDir::homePath() + "/Videos");
    pathLayout->addWidget(m_pathEdit);

    m_browseBtn = new QPushButton(tr("..."));
    m_browseBtn->setMaximumWidth(40);
    connect(m_browseBtn, &QPushButton::clicked, this, &RecordingControlWidget::onBrowseClicked);
    pathLayout->addWidget(m_browseBtn);
    groupLayout->addLayout(pathLayout);

    // 控制按鈕
    QHBoxLayout* btnLayout = new QHBoxLayout();
    m_startBtn = new QPushButton(tr("⏺ 開始錄影"));
    m_startBtn->setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }");
    connect(m_startBtn, &QPushButton::clicked, this, &RecordingControlWidget::onStartClicked);
    btnLayout->addWidget(m_startBtn);

    m_stopBtn = new QPushButton(tr("⏹ 停止"));
    m_stopBtn->setEnabled(false);
    connect(m_stopBtn, &QPushButton::clicked, this, &RecordingControlWidget::onStopClicked);
    btnLayout->addWidget(m_stopBtn);
    groupLayout->addLayout(btnLayout);

    // 狀態顯示
    m_statusLabel = new QLabel(tr("狀態: 就緒"));
    groupLayout->addWidget(m_statusLabel);

    QHBoxLayout* statsLayout = new QHBoxLayout();
    m_framesLabel = new QLabel(tr("幀數: 0"));
    statsLayout->addWidget(m_framesLabel);
    m_durationLabel = new QLabel(tr("時長: 00:00"));
    statsLayout->addWidget(m_durationLabel);
    groupLayout->addLayout(statsLayout);

    m_groupBox->setLayout(groupLayout);
    mainLayout->addWidget(m_groupBox);
    mainLayout->addStretch();
}

QString RecordingControlWidget::outputPath() const
{
    return m_pathEdit->text();
}

void RecordingControlWidget::setRecording(bool recording)
{
    m_isRecording = recording;

    m_startBtn->setEnabled(!recording);
    m_stopBtn->setEnabled(recording);
    m_pathEdit->setEnabled(!recording);
    m_browseBtn->setEnabled(!recording);

    if (recording) {
        m_statusLabel->setText(tr("狀態: 錄影中..."));
        m_statusLabel->setStyleSheet("color: #ff4444;");
        m_startBtn->setStyleSheet("");
        m_elapsedTimer.start();
        m_framesRecorded = 0;
        m_updateTimer->start(100);  // 每 100ms 更新
    } else {
        m_statusLabel->setText(tr("狀態: 就緒"));
        m_statusLabel->setStyleSheet("");
        m_startBtn->setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }");
        m_updateTimer->stop();
    }
}

void RecordingControlWidget::updateStats(int frames, double duration)
{
    m_framesRecorded = frames;
    m_framesLabel->setText(tr("幀數: %1").arg(frames));

    int minutes = static_cast<int>(duration) / 60;
    int seconds = static_cast<int>(duration) % 60;
    m_durationLabel->setText(tr("時長: %1:%2")
        .arg(minutes, 2, 10, QChar('0'))
        .arg(seconds, 2, 10, QChar('0')));
}

void RecordingControlWidget::setEnabled(bool enabled)
{
    m_groupBox->setEnabled(enabled);
}

void RecordingControlWidget::onStartClicked()
{
    emit startRecordingRequested();
}

void RecordingControlWidget::onStopClicked()
{
    emit stopRecordingRequested();
}

void RecordingControlWidget::onBrowseClicked()
{
    QString dir = QFileDialog::getExistingDirectory(
        this,
        tr("選擇輸出目錄"),
        m_pathEdit->text()
    );

    if (!dir.isEmpty()) {
        m_pathEdit->setText(dir);
        emit outputPathChanged(dir);
    }
}

void RecordingControlWidget::updateTimer()
{
    if (m_isRecording) {
        double elapsed = m_elapsedTimer.elapsed() / 1000.0;
        updateStats(m_framesRecorded, elapsed);
    }
}

} // namespace basler
