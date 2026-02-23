#include "ui/widgets/method_panels/defect_detection_method_panel.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QHeaderView>

namespace basler {

DefectDetectionMethodPanel::DefectDetectionMethodPanel(QWidget* parent)
    : QWidget(parent)
{
    initUi();
}

void DefectDetectionMethodPanel::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    // ===== 合格率顯示 =====
    m_passRateGroup = new QGroupBox(tr("📊 合格率"));
    QVBoxLayout* passRateLayout = new QVBoxLayout();

    // 大字體合格率顯示
    m_passRateLabel = new QLabel("100%");
    m_passRateLabel->setStyleSheet("font-size: 48px; font-weight: bold; color: #00ff00;");
    m_passRateLabel->setAlignment(Qt::AlignCenter);
    passRateLayout->addWidget(m_passRateLabel);

    // 進度條
    m_passRateBar = new QProgressBar();
    m_passRateBar->setRange(0, 100);
    m_passRateBar->setValue(100);
    m_passRateBar->setTextVisible(false);
    m_passRateBar->setStyleSheet(
        "QProgressBar { border: 1px solid #333; background-color: #1a1a1a; }"
        "QProgressBar::chunk { background-color: #00ff00; }"
    );
    passRateLayout->addWidget(m_passRateBar);

    // 合格/不合格計數
    QHBoxLayout* countLayout = new QHBoxLayout();
    m_passCountLabel = new QLabel(tr("合格: 0"));
    m_passCountLabel->setStyleSheet("color: #00ff00;");
    countLayout->addWidget(m_passCountLabel);

    m_failCountLabel = new QLabel(tr("不合格: 0"));
    m_failCountLabel->setStyleSheet("color: #ff4444;");
    countLayout->addWidget(m_failCountLabel);
    passRateLayout->addLayout(countLayout);

    m_passRateGroup->setLayout(passRateLayout);
    mainLayout->addWidget(m_passRateGroup);

    // ===== 瑕疵類型分佈 =====
    m_defectDistGroup = new QGroupBox(tr("🔍 瑕疵類型分佈"));
    QVBoxLayout* defectLayout = new QVBoxLayout();

    // 使用表格顯示
    m_defectTable = new QTableWidget(3, 2);
    m_defectTable->setHorizontalHeaderLabels({tr("瑕疵類型"), tr("數量")});
    m_defectTable->verticalHeader()->setVisible(false);
    m_defectTable->horizontalHeader()->setStretchLastSection(true);
    m_defectTable->setEditTriggers(QAbstractItemView::NoEditTriggers);
    m_defectTable->setSelectionMode(QAbstractItemView::NoSelection);
    m_defectTable->setMaximumHeight(120);

    // 設置行
    m_defectTable->setItem(0, 0, new QTableWidgetItem(tr("刮痕")));
    m_defectTable->setItem(0, 1, new QTableWidgetItem("0"));
    m_defectTable->setItem(1, 0, new QTableWidgetItem(tr("凹痕")));
    m_defectTable->setItem(1, 1, new QTableWidgetItem("0"));
    m_defectTable->setItem(2, 0, new QTableWidgetItem(tr("變色")));
    m_defectTable->setItem(2, 1, new QTableWidgetItem("0"));

    defectLayout->addWidget(m_defectTable);

    m_defectDistGroup->setLayout(defectLayout);
    mainLayout->addWidget(m_defectDistGroup);

    // ===== 敏感度調整 =====
    m_sensitivityGroup = new QGroupBox(tr("⚙️ 檢測敏感度"));
    QVBoxLayout* sensitivityLayout = new QVBoxLayout();

    QHBoxLayout* spinLayout = new QHBoxLayout();
    spinLayout->addWidget(new QLabel(tr("敏感度:")));

    m_sensitivitySpin = new QDoubleSpinBox();
    m_sensitivitySpin->setRange(0.0, 1.0);
    m_sensitivitySpin->setSingleStep(0.05);
    m_sensitivitySpin->setValue(0.5);
    m_sensitivitySpin->setDecimals(2);
    connect(m_sensitivitySpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DefectDetectionMethodPanel::onSensitivityChanged);
    spinLayout->addWidget(m_sensitivitySpin);
    spinLayout->addStretch();
    sensitivityLayout->addLayout(spinLayout);

    m_sensitivityHint = new QLabel(tr("較高的敏感度會檢測出更多細微瑕疵"));
    m_sensitivityHint->setStyleSheet("color: #888; font-size: 11px;");
    sensitivityLayout->addWidget(m_sensitivityHint);

    m_sensitivityGroup->setLayout(sensitivityLayout);
    mainLayout->addWidget(m_sensitivityGroup);

    // ===== 控制按鈕 =====
    QHBoxLayout* btnLayout = new QHBoxLayout();

    m_startBtn = new QPushButton(tr("▶ 開始檢測"));
    m_startBtn->setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 10px; }");
    connect(m_startBtn, &QPushButton::clicked, this, &DefectDetectionMethodPanel::startDetectionRequested);
    btnLayout->addWidget(m_startBtn);

    m_stopBtn = new QPushButton(tr("⏹ 停止"));
    m_stopBtn->setEnabled(false);
    connect(m_stopBtn, &QPushButton::clicked, this, &DefectDetectionMethodPanel::stopDetectionRequested);
    btnLayout->addWidget(m_stopBtn);

    m_clearBtn = new QPushButton(tr("🗑 清除統計"));
    connect(m_clearBtn, &QPushButton::clicked, this, &DefectDetectionMethodPanel::clearStatsRequested);
    btnLayout->addWidget(m_clearBtn);

    mainLayout->addLayout(btnLayout);
    mainLayout->addStretch();
}

void DefectDetectionMethodPanel::updateStats(double passRate, int passCount, int failCount)
{
    // 更新合格率顯示
    m_passRateLabel->setText(QString("%1%").arg(passRate, 0, 'f', 1));
    m_passRateBar->setValue(static_cast<int>(passRate));

    // 根據合格率改變顏色
    QString color;
    if (passRate >= 95) {
        color = "#00ff00";  // 綠色
    } else if (passRate >= 80) {
        color = "#ffff00";  // 黃色
    } else {
        color = "#ff4444";  // 紅色
    }
    m_passRateLabel->setStyleSheet(QString("font-size: 48px; font-weight: bold; color: %1;").arg(color));
    m_passRateBar->setStyleSheet(QString(
        "QProgressBar { border: 1px solid #333; background-color: #1a1a1a; }"
        "QProgressBar::chunk { background-color: %1; }"
    ).arg(color));

    // 更新計數
    m_passCountLabel->setText(tr("合格: %1").arg(passCount));
    m_failCountLabel->setText(tr("不合格: %1").arg(failCount));
}

void DefectDetectionMethodPanel::updateDefectDistribution(int scratchCount, int dentCount, int discolorationCount)
{
    m_defectTable->item(0, 1)->setText(QString::number(scratchCount));
    m_defectTable->item(1, 1)->setText(QString::number(dentCount));
    m_defectTable->item(2, 1)->setText(QString::number(discolorationCount));
}

void DefectDetectionMethodPanel::setDetectionState(bool running)
{
    m_isRunning = running;
    m_startBtn->setEnabled(!running);
    m_stopBtn->setEnabled(running);
}

void DefectDetectionMethodPanel::onSensitivityChanged(double value)
{
    emit sensitivityChanged(value);
}

} // namespace basler
