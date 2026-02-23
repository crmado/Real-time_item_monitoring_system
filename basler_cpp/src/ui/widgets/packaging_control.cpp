#include "ui/widgets/packaging_control.h"
#include "ui/widgets/part_selector.h"
#include "ui/widgets/method_selector.h"
#include "ui/widgets/method_panels/counting_method_panel.h"
#include "ui/widgets/method_panels/defect_detection_method_panel.h"
#include <QVBoxLayout>

namespace basler {

PackagingControlWidget::PackagingControlWidget(QWidget* parent)
    : QWidget(parent)
{
    initUi();
    connectSignals();
}

void PackagingControlWidget::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    // 零件選擇器
    m_partSelector = new PartSelectorWidget();
    mainLayout->addWidget(m_partSelector);

    // 方法選擇器
    m_methodSelector = new MethodSelectorWidget();
    mainLayout->addWidget(m_methodSelector);

    // 方法面板容器
    m_methodPanelStack = new QStackedWidget();

    // 計數方法面板
    m_countingPanel = new CountingMethodPanel();
    m_countingPanelIndex = m_methodPanelStack->addWidget(m_countingPanel);

    // 瑕疵檢測方法面板
    m_defectPanel = new DefectDetectionMethodPanel();
    m_defectPanelIndex = m_methodPanelStack->addWidget(m_defectPanel);

    mainLayout->addWidget(m_methodPanelStack, 1);

    // 初始化：載入當前零件的方法
    QString currentPartId = m_partSelector->currentPartId();
    if (!currentPartId.isEmpty()) {
        onPartTypeChanged(currentPartId);
    }
}

void PackagingControlWidget::connectSignals()
{
    // 零件選擇變更
    connect(m_partSelector, &PartSelectorWidget::partTypeChanged,
            this, &PackagingControlWidget::onPartTypeChanged);

    // 方法選擇變更
    connect(m_methodSelector, &MethodSelectorWidget::detectionMethodChanged,
            this, &PackagingControlWidget::onDetectionMethodChanged);

    // 計數方法面板信號
    connect(m_countingPanel, &CountingMethodPanel::startPackagingRequested,
            this, &PackagingControlWidget::startPackagingRequested);
    connect(m_countingPanel, &CountingMethodPanel::pausePackagingRequested,
            this, &PackagingControlWidget::pausePackagingRequested);
    connect(m_countingPanel, &CountingMethodPanel::resetCountRequested,
            this, &PackagingControlWidget::resetCountRequested);
    connect(m_countingPanel, &CountingMethodPanel::targetCountChanged,
            this, &PackagingControlWidget::targetCountChanged);
    connect(m_countingPanel, &CountingMethodPanel::thresholdChanged,
            this, &PackagingControlWidget::thresholdChanged);

    // 瑕疵檢測方法面板信號
    connect(m_defectPanel, &DefectDetectionMethodPanel::startDetectionRequested,
            this, &PackagingControlWidget::startDefectDetectionRequested);
    connect(m_defectPanel, &DefectDetectionMethodPanel::stopDetectionRequested,
            this, &PackagingControlWidget::stopDefectDetectionRequested);
    connect(m_defectPanel, &DefectDetectionMethodPanel::clearStatsRequested,
            this, &PackagingControlWidget::clearDefectStatsRequested);
    connect(m_defectPanel, &DefectDetectionMethodPanel::sensitivityChanged,
            this, &PackagingControlWidget::defectSensitivityChanged);
}

void PackagingControlWidget::onPartTypeChanged(const QString& partId)
{
    // 更新方法選擇器
    m_methodSelector->updateMethodsForPart(partId);

    emit partTypeChanged(partId);
}

void PackagingControlWidget::onDetectionMethodChanged(const QString& methodId)
{
    // 切換對應的方法面板
    if (methodId == "counting") {
        m_methodPanelStack->setCurrentIndex(m_countingPanelIndex);
    } else if (methodId == "defect_detection") {
        m_methodPanelStack->setCurrentIndex(m_defectPanelIndex);
    }

    emit detectionMethodChanged(methodId);
}

QString PackagingControlWidget::currentPartId() const
{
    return m_partSelector->currentPartId();
}

QString PackagingControlWidget::currentMethodId() const
{
    return m_methodSelector->currentMethodId();
}

void PackagingControlWidget::updateCount(int current, int target)
{
    m_countingPanel->updateCount(current, target);
}

void PackagingControlWidget::updateVibratorStatus(bool vibrator1Running, bool vibrator2Running, int speedPercent)
{
    m_countingPanel->updateVibratorStatus(vibrator1Running, vibrator2Running, speedPercent);
}

void PackagingControlWidget::updateDefectStats(double passRate, int passCount, int failCount)
{
    m_defectPanel->updateStats(passRate, passCount, failCount);
}

} // namespace basler
