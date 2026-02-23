#ifndef CAMERA_CONTROL_H
#define CAMERA_CONTROL_H

#include <QWidget>
#include <QGroupBox>
#include <QPushButton>
#include <QComboBox>
#include <QLabel>
#include <QSlider>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QStringList>

namespace basler {

/**
 * @brief 相機控制組件
 *
 * 提供相機檢測、連接、斷開、抓取控制和曝光調整功能
 */
class CameraControlWidget : public QWidget {
    Q_OBJECT

public:
    explicit CameraControlWidget(QWidget* parent = nullptr);
    ~CameraControlWidget() = default;

public slots:
    /**
     * @brief 設置相機列表（字串版本）
     * @param cameras 相機名稱列表
     */
    void setCameraList(const QStringList& cameras);

    /**
     * @brief 設置連接狀態
     * @param connected 是否已連接
     */
    void setConnected(bool connected);

    /**
     * @brief 設置抓取狀態
     * @param grabbing 是否正在抓取
     */
    void setGrabbing(bool grabbing);

    /**
     * @brief 設置為視頻模式（禁用相機相關控制）
     * @param isVideo 是否為視頻模式
     */
    void setVideoMode(bool isVideo);

signals:
    // User operation signals
    void detectRequested();
    void detectWithRetryRequested();  // New: auto-retry detection
    void connectRequested();
    void disconnectRequested();
    void startGrabRequested();
    void stopGrabRequested();
    void exposureChanged(double exposureUs);

private slots:
    void onExposureChanged(int value);

private:
    void initUi();
    void updateButtonStates();

    // UI Components
    QGroupBox* m_groupBox;
    QPushButton* m_detectBtn;
    QPushButton* m_autoDetectBtn;  // New: auto-retry detect button
    QComboBox* m_cameraCombo;
    QPushButton* m_connectBtn;
    QPushButton* m_disconnectBtn;
    QPushButton* m_startBtn;
    QPushButton* m_stopBtn;
    QSlider* m_exposureSlider;
    QLabel* m_exposureLabel;

    // 狀態
    bool m_isConnected = false;
    bool m_isGrabbing = false;
    bool m_isVideoMode = false;
};

} // namespace basler

#endif // CAMERA_CONTROL_H
