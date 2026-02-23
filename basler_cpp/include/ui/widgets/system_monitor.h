#ifndef SYSTEM_MONITOR_H
#define SYSTEM_MONITOR_H

#include <QWidget>
#include <QGroupBox>
#include <QLabel>
#include <QProgressBar>
#include <QTimer>

namespace basler {

/**
 * @brief 系統監控組件
 *
 * 顯示 CPU 和記憶體使用率
 */
class SystemMonitorWidget : public QWidget {
    Q_OBJECT

public:
    explicit SystemMonitorWidget(QWidget* parent = nullptr);
    ~SystemMonitorWidget() = default;

    void setUpdateInterval(int ms);

public slots:
    void startMonitoring();
    void stopMonitoring();

private slots:
    void updateStats();

private:
    void initUi();
    double getCpuUsage();
    double getMemoryUsage();

    QGroupBox* m_groupBox;
    QLabel* m_cpuLabel;
    QProgressBar* m_cpuBar;
    QLabel* m_memLabel;
    QProgressBar* m_memBar;

    QTimer* m_updateTimer;
    int m_updateInterval = 1000;  // 1 秒

    // CPU 計算用
    qint64 m_lastCpuTime = 0;
    qint64 m_lastIdleTime = 0;
};

} // namespace basler

#endif // SYSTEM_MONITOR_H
