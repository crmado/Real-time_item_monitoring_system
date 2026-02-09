#ifndef PACKAGING_CONTROL_H
#define PACKAGING_CONTROL_H

#include <QWidget>
#include <QStackedWidget>
#include <QVBoxLayout>
#include <memory>

namespace basler {

// 前向聲明
class PartSelectorWidget;
class MethodSelectorWidget;
class CountingMethodPanel;
class DefectDetectionMethodPanel;

/**
 * @brief 定量包裝控制組件
 *
 * 整合零件選擇、檢測方法選擇和方法特定面板
 * 使用 QStackedWidget 動態切換不同檢測方法的控制面板
 */
class PackagingControlWidget : public QWidget {
    Q_OBJECT

public:
    explicit PackagingControlWidget(QWidget* parent = nullptr);
    ~PackagingControlWidget() = default;

    // 獲取當前選擇
    QString currentPartId() const;
    QString currentMethodId() const;

    // 獲取子組件
    PartSelectorWidget* partSelector() const { return m_partSelector; }
    MethodSelectorWidget* methodSelector() const { return m_methodSelector; }
    CountingMethodPanel* countingPanel() const { return m_countingPanel; }
    DefectDetectionMethodPanel* defectPanel() const { return m_defectPanel; }

public slots:
    /**
     * @brief 更新計數顯示
     * @param current 當前計數
     * @param target 目標計數
     */
    void updateCount(int current, int target);

    /**
     * @brief 更新震動機狀態
     * @param vibrator1Running 震動機1是否運行
     * @param vibrator2Running 震動機2是否運行
     * @param speedPercent 速度百分比
     */
    void updateVibratorStatus(bool vibrator1Running, bool vibrator2Running, int speedPercent);

    /**
     * @brief 更新瑕疵檢測統計
     * @param passRate 合格率
     * @param passCount 合格數
     * @param failCount 不合格數
     */
    void updateDefectStats(double passRate, int passCount, int failCount);

signals:
    // 零件和方法選擇
    void partTypeChanged(const QString& partId);
    void detectionMethodChanged(const QString& methodId);

    // 計數方法信號
    void startPackagingRequested();
    void pausePackagingRequested();
    void resetCountRequested();
    void targetCountChanged(int count);
    void thresholdChanged(double full, double medium, double slow);

    // 瑕疵檢測方法信號
    void startDefectDetectionRequested();
    void stopDefectDetectionRequested();
    void clearDefectStatsRequested();
    void defectSensitivityChanged(double sensitivity);

private slots:
    void onPartTypeChanged(const QString& partId);
    void onDetectionMethodChanged(const QString& methodId);

private:
    void initUi();
    void connectSignals();

    // 選擇器
    PartSelectorWidget* m_partSelector;
    MethodSelectorWidget* m_methodSelector;

    // 方法面板容器
    QStackedWidget* m_methodPanelStack;

    // 方法特定面板
    CountingMethodPanel* m_countingPanel;
    DefectDetectionMethodPanel* m_defectPanel;

    // 面板索引映射
    int m_countingPanelIndex = 0;
    int m_defectPanelIndex = 1;
};

} // namespace basler

#endif // PACKAGING_CONTROL_H
