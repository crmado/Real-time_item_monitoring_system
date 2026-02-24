#include "ui/widgets/method_panels/counting_method_panel.h"
#include "config/settings.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QTimer>
#include <QPainter>
#include <QPainterPath>
#include <QDateTime>
#include <algorithm>

namespace basler {

// ============================================================================
// CountTrendWidget — QPainter 自繪折線圖，顯示最近 N 包計數速率（件/秒）
// ============================================================================
class CountTrendWidget : public QWidget {
public:
    explicit CountTrendWidget(QWidget* parent = nullptr) : QWidget(parent)
    {
        setMinimumHeight(70);
        setMaximumHeight(70);
        setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
        setToolTip(tr("最近 %1 包的計數速率趨勢（件/秒）").arg(MAX_POINTS));
    }

    void addDataPoint(double ratePerSec)
    {
        m_data.append(ratePerSec);
        if (m_data.size() > MAX_POINTS)
            m_data.removeFirst();
        update();
    }

    void clearData() { m_data.clear(); update(); }

protected:
    void paintEvent(QPaintEvent*) override
    {
        QPainter p(this);
        p.setRenderHint(QPainter::Antialiasing);

        // 背景
        p.fillRect(rect(), QColor(10, 14, 35));
        p.setPen(QPen(QColor(31, 58, 95), 1));
        p.drawRect(rect().adjusted(0, 0, -1, -1));

        // 標題
        p.setPen(QColor(0, 212, 255));
        p.setFont(QFont("Arial", 8));
        p.drawText(QRect(4, 2, width(), 14), Qt::AlignLeft | Qt::AlignTop,
                   tr("📈 計數速率趨勢（件/秒）"));

        if (m_data.size() < 2) {
            p.setPen(QColor(100, 100, 100));
            p.setFont(QFont("Arial", 9));
            p.drawText(rect().adjusted(0, 16, 0, 0), Qt::AlignCenter,
                       tr("等待更多包裝數據..."));
            return;
        }

        double minVal = *std::min_element(m_data.begin(), m_data.end());
        double maxVal = *std::max_element(m_data.begin(), m_data.end());
        if (maxVal - minVal < 0.01) { maxVal = minVal + 0.01; }

        const int padL = 30, padR = 6, padT = 18, padB = 6;
        int w = width() - padL - padR;
        int h = height() - padT - padB;

        auto toPoint = [&](int i, double v) -> QPointF {
            float x = padL + static_cast<float>(i) / (m_data.size() - 1) * w;
            float y = padT + h - static_cast<float>((v - minVal) / (maxVal - minVal)) * h;
            return QPointF(x, y);
        };

        // 填充面積
        QPolygonF poly;
        poly << QPointF(padL, padT + h);
        for (int i = 0; i < m_data.size(); ++i) poly << toPoint(i, m_data[i]);
        poly << QPointF(padL + w, padT + h);
        p.setBrush(QColor(0, 212, 255, 25));
        p.setPen(Qt::NoPen);
        p.drawPolygon(poly);

        // 折線
        QPainterPath path;
        path.moveTo(toPoint(0, m_data[0]));
        for (int i = 1; i < m_data.size(); ++i) path.lineTo(toPoint(i, m_data[i]));
        p.setPen(QPen(QColor(0, 212, 255), 1.5));
        p.setBrush(Qt::NoBrush);
        p.drawPath(path);

        // 最後一點
        QPointF last = toPoint(m_data.size() - 1, m_data.last());
        p.setBrush(QColor(0, 212, 255));
        p.setPen(Qt::NoPen);
        p.drawEllipse(last, 3, 3);

        // Y 軸 max/min 標籤
        p.setPen(QColor(120, 140, 160));
        p.setFont(QFont("Arial", 7));
        p.drawText(QRect(0, padT - 1, padL - 2, 12),
                   Qt::AlignRight | Qt::AlignTop,
                   QString("%1").arg(maxVal, 0, 'f', 1));
        p.drawText(QRect(0, padT + h - 11, padL - 2, 12),
                   Qt::AlignRight | Qt::AlignBottom,
                   QString("%1").arg(minVal, 0, 'f', 1));

        // 最新速率（右下角）
        p.setPen(QColor(0, 255, 128));
        p.setFont(QFont("Arial", 8, QFont::Bold));
        p.drawText(QRect(padL, padT + h - 14, w, 14),
                   Qt::AlignRight | Qt::AlignBottom,
                   QString("最新: %1").arg(m_data.last(), 0, 'f', 1));
    }

private:
    static constexpr int MAX_POINTS = 20;
    QVector<double> m_data;
};


CountingMethodPanel::CountingMethodPanel(QWidget* parent)
    : QWidget(parent)
{
    initUi();

    // 從配置載入預設值
    const auto& config = getConfig();
    m_targetCount = config.packaging().targetCount;
    m_targetCountSpin->setValue(m_targetCount);
}

void CountingMethodPanel::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    // ===== 目標設定 =====
    m_targetGroup = new QGroupBox(tr("🎯 目標設定"));
    QHBoxLayout* targetLayout = new QHBoxLayout();

    targetLayout->addWidget(new QLabel(tr("目標數量:")));
    m_targetCountSpin = new QSpinBox();
    m_targetCountSpin->setRange(1, 9999);
    m_targetCountSpin->setValue(150);
    m_targetCountSpin->setSuffix(tr(" 顆"));
    connect(m_targetCountSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &CountingMethodPanel::onTargetCountChanged);
    targetLayout->addWidget(m_targetCountSpin);
    targetLayout->addStretch();

    m_targetGroup->setLayout(targetLayout);
    mainLayout->addWidget(m_targetGroup);

    // ===== 進度顯示 =====
    m_progressGroup = new QGroupBox(tr("📊 進度"));
    QVBoxLayout* progressLayout = new QVBoxLayout();

    // 大字體計數顯示
    m_countLabel = new QLabel("0");
    m_countLabel->setStyleSheet("font-size: 48px; font-weight: bold; color: #00ff00;");
    m_countLabel->setAlignment(Qt::AlignCenter);
    progressLayout->addWidget(m_countLabel);

    // 目標標籤
    m_targetLabel = new QLabel(tr("/ 150 顆"));
    m_targetLabel->setStyleSheet("font-size: 18px; color: #888;");
    m_targetLabel->setAlignment(Qt::AlignCenter);
    progressLayout->addWidget(m_targetLabel);

    // 進度條
    m_progressBar = new QProgressBar();
    m_progressBar->setRange(0, 100);
    m_progressBar->setValue(0);
    m_progressBar->setTextVisible(true);
    m_progressBar->setFormat("%v%");
    progressLayout->addWidget(m_progressBar);

    // 包裝完成覆蓋提示（預設隱藏）
    m_completionOverlay = new QLabel(tr("✅ 包裝完成！"));
    m_completionOverlay->setStyleSheet(
        "font-size: 28px; font-weight: bold; color: #00ff80;"
        "background-color: rgba(0,30,0,200); border-radius: 8px; padding: 10px;");
    m_completionOverlay->setAlignment(Qt::AlignCenter);
    m_completionOverlay->hide();
    progressLayout->insertWidget(0, m_completionOverlay);

    m_completionTimer = new QTimer(this);
    m_completionTimer->setSingleShot(true);
    connect(m_completionTimer, &QTimer::timeout,
            this, [this]() { m_completionOverlay->hide(); });

    // 歷史計數速率趨勢圖
    m_trendChart = new CountTrendWidget();
    progressLayout->addWidget(m_trendChart);

    m_progressGroup->setLayout(progressLayout);
    mainLayout->addWidget(m_progressGroup);

    // ===== 震動機狀態 =====
    m_vibratorGroup = new QGroupBox(tr("⚡ 震動機狀態"));
    QGridLayout* vibratorLayout = new QGridLayout();

    vibratorLayout->addWidget(new QLabel(tr("震動機 A:")), 0, 0);
    m_vibrator1StatusLabel = new QLabel(tr("停止"));
    m_vibrator1StatusLabel->setStyleSheet("color: #888;");
    vibratorLayout->addWidget(m_vibrator1StatusLabel, 0, 1);

    vibratorLayout->addWidget(new QLabel(tr("震動機 B:")), 1, 0);
    m_vibrator2StatusLabel = new QLabel(tr("停止"));
    m_vibrator2StatusLabel->setStyleSheet("color: #888;");
    vibratorLayout->addWidget(m_vibrator2StatusLabel, 1, 1);

    vibratorLayout->addWidget(new QLabel(tr("當前速度:")), 2, 0);
    m_speedLabel = new QLabel(tr("0%"));
    m_speedLabel->setStyleSheet("font-weight: bold;");
    vibratorLayout->addWidget(m_speedLabel, 2, 1);

    m_vibratorGroup->setLayout(vibratorLayout);
    mainLayout->addWidget(m_vibratorGroup);

    // ===== 速度閾值調整 =====
    m_thresholdGroup = new QGroupBox(tr("⚙️ 速度閾值"));
    QGridLayout* thresholdLayout = new QGridLayout();

    thresholdLayout->addWidget(new QLabel(tr("全速閾值:")), 0, 0);
    m_fullThresholdSpin = new QDoubleSpinBox();
    m_fullThresholdSpin->setRange(0.0, 1.0);
    m_fullThresholdSpin->setSingleStep(0.01);
    m_fullThresholdSpin->setValue(0.85);
    m_fullThresholdSpin->setDecimals(2);
    connect(m_fullThresholdSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &CountingMethodPanel::onFullThresholdChanged);
    thresholdLayout->addWidget(m_fullThresholdSpin, 0, 1);

    thresholdLayout->addWidget(new QLabel(tr("中速閾值:")), 1, 0);
    m_mediumThresholdSpin = new QDoubleSpinBox();
    m_mediumThresholdSpin->setRange(0.0, 1.0);
    m_mediumThresholdSpin->setSingleStep(0.01);
    m_mediumThresholdSpin->setValue(0.93);
    m_mediumThresholdSpin->setDecimals(2);
    connect(m_mediumThresholdSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &CountingMethodPanel::onMediumThresholdChanged);
    thresholdLayout->addWidget(m_mediumThresholdSpin, 1, 1);

    thresholdLayout->addWidget(new QLabel(tr("慢速閾值:")), 2, 0);
    m_slowThresholdSpin = new QDoubleSpinBox();
    m_slowThresholdSpin->setRange(0.0, 1.0);
    m_slowThresholdSpin->setSingleStep(0.01);
    m_slowThresholdSpin->setValue(0.97);
    m_slowThresholdSpin->setDecimals(2);
    connect(m_slowThresholdSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &CountingMethodPanel::onSlowThresholdChanged);
    thresholdLayout->addWidget(m_slowThresholdSpin, 2, 1);

    m_thresholdGroup->setLayout(thresholdLayout);
    mainLayout->addWidget(m_thresholdGroup);

    // ===== 控制按鈕 =====
    QHBoxLayout* btnLayout = new QHBoxLayout();

    m_startBtn = new QPushButton(tr("▶ 開始包裝"));
    m_startBtn->setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; }");
    connect(m_startBtn, &QPushButton::clicked, this, &CountingMethodPanel::startPackagingRequested);
    btnLayout->addWidget(m_startBtn);

    m_pauseBtn = new QPushButton(tr("⏸ 暫停"));
    m_pauseBtn->setEnabled(false);
    connect(m_pauseBtn, &QPushButton::clicked, this, &CountingMethodPanel::pausePackagingRequested);
    btnLayout->addWidget(m_pauseBtn);

    m_resetBtn = new QPushButton(tr("🔄 重置"));
    connect(m_resetBtn, &QPushButton::clicked, this, &CountingMethodPanel::resetCountRequested);
    btnLayout->addWidget(m_resetBtn);

    mainLayout->addLayout(btnLayout);
    mainLayout->addStretch();
}

void CountingMethodPanel::updateCount(int current, int target)
{
    m_currentCount = current;
    m_targetCount = target;

    m_countLabel->setText(QString::number(current));
    m_targetLabel->setText(tr("/ %1 顆").arg(target));

    int progress = (target > 0) ? (current * 100 / target) : 0;
    m_progressBar->setValue(progress);

    // 根據進度改變顏色
    if (progress >= 100) {
        m_countLabel->setStyleSheet("font-size: 48px; font-weight: bold; color: #00ff00;");
    } else if (progress >= 90) {
        m_countLabel->setStyleSheet("font-size: 48px; font-weight: bold; color: #ffff00;");
    } else {
        m_countLabel->setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff;");
    }
}

void CountingMethodPanel::updateVibratorStatus(bool vibrator1Running, bool vibrator2Running, int speedPercent)
{
    m_vibrator1StatusLabel->setText(vibrator1Running ? tr("運行中") : tr("停止"));
    m_vibrator1StatusLabel->setStyleSheet(vibrator1Running ? "color: #00ff00;" : "color: #888;");

    m_vibrator2StatusLabel->setText(vibrator2Running ? tr("運行中") : tr("停止"));
    m_vibrator2StatusLabel->setStyleSheet(vibrator2Running ? "color: #00ff00;" : "color: #888;");

    m_speedLabel->setText(tr("%1%").arg(speedPercent));
}

void CountingMethodPanel::setPackagingState(bool running)
{
    m_isRunning = running;

    if (running) {
        m_packageStartTime = QDateTime::currentMSecsSinceEpoch();  // 記錄開始時間
        m_startBtn->setText(tr("⏹ 包裝中..."));
        m_startBtn->setStyleSheet("QPushButton { background-color: #FF9800; color: white; padding: 10px; }");
        m_startBtn->setEnabled(false);
        m_pauseBtn->setEnabled(true);
        m_resetBtn->setEnabled(false);
    } else {
        m_startBtn->setText(tr("▶ 開始包裝"));
        m_startBtn->setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; }");
        m_startBtn->setEnabled(true);
        m_pauseBtn->setEnabled(false);
        m_resetBtn->setEnabled(true);
    }
}

void CountingMethodPanel::showPackagingCompleted()
{
    m_countLabel->setStyleSheet("font-size: 48px; font-weight: bold; color: #00ff80;");

    // 計算此包的速率並記錄到趨勢圖
    if (m_packageStartTime > 0) {
        qint64 elapsed = QDateTime::currentMSecsSinceEpoch() - m_packageStartTime;
        if (elapsed > 0) {
            double rate = static_cast<double>(m_targetCount) / (elapsed / 1000.0);
            m_trendChart->addDataPoint(rate);
        }
        m_packageStartTime = 0;
    }

    setPackagingState(false);

    // 顯示大字完成提示，4 秒後自動消失
    m_completionOverlay->show();
    m_completionTimer->start(4000);
}

void CountingMethodPanel::onTargetCountChanged(int value)
{
    m_targetCount = value;
    m_targetLabel->setText(tr("/ %1 顆").arg(value));
    emit targetCountChanged(value);
}

void CountingMethodPanel::onFullThresholdChanged(double value)
{
    emit thresholdChanged(value, m_mediumThresholdSpin->value(), m_slowThresholdSpin->value());
}

void CountingMethodPanel::onMediumThresholdChanged(double value)
{
    emit thresholdChanged(m_fullThresholdSpin->value(), value, m_slowThresholdSpin->value());
}

void CountingMethodPanel::onSlowThresholdChanged(double value)
{
    emit thresholdChanged(m_fullThresholdSpin->value(), m_mediumThresholdSpin->value(), value);
}

void CountingMethodPanel::resetTrendChart()
{
    if (m_trendChart)
        m_trendChart->clearData();
    m_packageStartTime = 0;
}

} // namespace basler
