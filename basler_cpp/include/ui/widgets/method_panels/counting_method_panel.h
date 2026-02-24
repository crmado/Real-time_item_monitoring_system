#ifndef COUNTING_METHOD_PANEL_H
#define COUNTING_METHOD_PANEL_H

#include <QWidget>
#include <QGroupBox>
#include <QPushButton>
#include <QSpinBox>
#include <QDoubleSpinBox>
#include <QLabel>
#include <QProgressBar>
#include <QTimer>
#include <QVector>

namespace basler {

// 前向宣告（實作在 .cpp 內部，不需要公開 header）
class CountTrendWidget;

/**
 * @brief 計數方法控制面板
 *
 * 用於定量包裝的計數控制
 * 包含目標設定、進度顯示、震動機狀態、速度閾值調整
 */
class CountingMethodPanel : public QWidget {
    Q_OBJECT

public:
    explicit CountingMethodPanel(QWidget* parent = nullptr);
    ~CountingMethodPanel() = default;

    /** 回傳目前目標計數（供 MainWindow 導出報告使用）*/
    int targetCount() const { return m_targetCount; }

public slots:
    /**
     * @brief 更新計數顯示
     * @param current 當前計數
     * @param target 目標計數
     */
    void updateCount(int current, int target);

    /**
     * @brief 更新震動機狀態
     * @param vibrator1Running 震動機1運行狀態
     * @param vibrator2Running 震動機2運行狀態
     * @param speedPercent 當前速度百分比
     */
    void updateVibratorStatus(bool vibrator1Running, bool vibrator2Running, int speedPercent);

    /**
     * @brief 設置包裝狀態
     * @param running 是否正在包裝
     */
    void setPackagingState(bool running);

    /**
     * @brief 顯示包裝完成
     */
    void showPackagingCompleted();

signals:
    void startPackagingRequested();
    void pausePackagingRequested();
    void resetCountRequested();
    void targetCountChanged(int count);
    void thresholdChanged(double full, double medium, double slow);

private slots:
    void onTargetCountChanged(int value);
    void onFullThresholdChanged(double value);
    void onMediumThresholdChanged(double value);
    void onSlowThresholdChanged(double value);

private:
    void initUi();

    // 目標設定
    QGroupBox* m_targetGroup;
    QSpinBox* m_targetCountSpin;

    // 進度顯示
    QGroupBox* m_progressGroup;
    QLabel* m_countLabel;          // 大字體顯示當前計數
    QLabel* m_targetLabel;         // 目標計數
    QProgressBar* m_progressBar;

    // 震動機狀態
    QGroupBox* m_vibratorGroup;
    QLabel* m_vibrator1StatusLabel;
    QLabel* m_vibrator2StatusLabel;
    QLabel* m_speedLabel;

    // 速度閾值調整
    QGroupBox* m_thresholdGroup;
    QDoubleSpinBox* m_fullThresholdSpin;
    QDoubleSpinBox* m_mediumThresholdSpin;
    QDoubleSpinBox* m_slowThresholdSpin;

    // 控制按鈕
    QPushButton* m_startBtn;
    QPushButton* m_pauseBtn;
    QPushButton* m_resetBtn;

    // 狀態
    bool m_isRunning = false;
    int m_currentCount = 0;
    int m_targetCount = 150;

    // 包裝完成視覺提示
    QLabel* m_completionOverlay = nullptr;
    QTimer* m_completionTimer = nullptr;

    // 歷史計數趨勢迷你圖
    CountTrendWidget* m_trendChart = nullptr;
    qint64 m_packageStartTime = 0;  // 包裝開始時間戳（ms）
};

} // namespace basler

#endif // COUNTING_METHOD_PANEL_H
