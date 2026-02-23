#ifndef DEFECT_DETECTION_METHOD_PANEL_H
#define DEFECT_DETECTION_METHOD_PANEL_H

#include <QWidget>
#include <QGroupBox>
#include <QPushButton>
#include <QDoubleSpinBox>
#include <QLabel>
#include <QProgressBar>
#include <QTableWidget>

namespace basler {

/**
 * @brief 瑕疵檢測方法控制面板
 *
 * 用於表面瑕疵檢測
 * 包含合格率顯示、瑕疵類型分佈、敏感度調整
 */
class DefectDetectionMethodPanel : public QWidget {
    Q_OBJECT

public:
    explicit DefectDetectionMethodPanel(QWidget* parent = nullptr);
    ~DefectDetectionMethodPanel() = default;

public slots:
    /**
     * @brief 更新統計數據
     * @param passRate 合格率 (0-100)
     * @param passCount 合格數
     * @param failCount 不合格數
     */
    void updateStats(double passRate, int passCount, int failCount);

    /**
     * @brief 更新瑕疵類型分佈
     * @param scratchCount 刮痕數量
     * @param dentCount 凹痕數量
     * @param discolorationCount 變色數量
     */
    void updateDefectDistribution(int scratchCount, int dentCount, int discolorationCount);

    /**
     * @brief 設置檢測狀態
     * @param running 是否正在檢測
     */
    void setDetectionState(bool running);

signals:
    void startDetectionRequested();
    void stopDetectionRequested();
    void clearStatsRequested();
    void sensitivityChanged(double sensitivity);

private slots:
    void onSensitivityChanged(double value);

private:
    void initUi();

    // 合格率顯示
    QGroupBox* m_passRateGroup;
    QLabel* m_passRateLabel;         // 大字體顯示合格率
    QProgressBar* m_passRateBar;
    QLabel* m_passCountLabel;
    QLabel* m_failCountLabel;

    // 瑕疵類型分佈
    QGroupBox* m_defectDistGroup;
    QTableWidget* m_defectTable;
    QLabel* m_scratchLabel;
    QLabel* m_dentLabel;
    QLabel* m_discolorationLabel;

    // 敏感度調整
    QGroupBox* m_sensitivityGroup;
    QDoubleSpinBox* m_sensitivitySpin;
    QLabel* m_sensitivityHint;

    // 控制按鈕
    QPushButton* m_startBtn;
    QPushButton* m_stopBtn;
    QPushButton* m_clearBtn;

    // 狀態
    bool m_isRunning = false;
};

} // namespace basler

#endif // DEFECT_DETECTION_METHOD_PANEL_H
