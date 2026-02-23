#ifndef RECORDING_CONTROL_H
#define RECORDING_CONTROL_H

#include <QWidget>
#include <QGroupBox>
#include <QPushButton>
#include <QLabel>
#include <QLineEdit>
#include <QTimer>
#include <QElapsedTimer>

namespace basler {

/**
 * @brief 錄影控制組件
 *
 * 提供開始/停止錄影功能、路徑選擇和錄影狀態顯示
 */
class RecordingControlWidget : public QWidget {
    Q_OBJECT

public:
    explicit RecordingControlWidget(QWidget* parent = nullptr);
    ~RecordingControlWidget() = default;

    /**
     * @brief 獲取輸出路徑
     */
    QString outputPath() const;

public slots:
    /**
     * @brief 設置錄影狀態
     * @param recording 是否正在錄影
     */
    void setRecording(bool recording);

    /**
     * @brief 更新錄影統計
     * @param frames 已錄製幀數
     * @param duration 錄製時長（秒）
     */
    void updateStats(int frames, double duration);

    /**
     * @brief 設置啟用狀態
     * @param enabled 是否啟用
     */
    void setEnabled(bool enabled);

signals:
    void startRecordingRequested();
    void stopRecordingRequested();
    void outputPathChanged(const QString& path);

private slots:
    void onStartClicked();
    void onStopClicked();
    void onBrowseClicked();
    void updateTimer();

private:
    void initUi();

    // UI 組件
    QGroupBox* m_groupBox;
    QLineEdit* m_pathEdit;
    QPushButton* m_browseBtn;
    QPushButton* m_startBtn;
    QPushButton* m_stopBtn;
    QLabel* m_statusLabel;
    QLabel* m_framesLabel;
    QLabel* m_durationLabel;

    // 計時器
    QTimer* m_updateTimer;
    QElapsedTimer m_elapsedTimer;

    // 狀態
    bool m_isRecording = false;
    int m_framesRecorded = 0;
};

} // namespace basler

#endif // RECORDING_CONTROL_H
