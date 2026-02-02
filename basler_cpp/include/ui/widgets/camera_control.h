#ifndef CAMERA_CONTROL_H
#define CAMERA_CONTROL_H

#include <QWidget>
#include <QGroupBox>
#include <QPushButton>
#include <QListWidget>
#include <QLabel>
#include <QSlider>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <vector>

namespace basler {

// 前向聲明
struct CameraInfo;

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
     * @brief 更新相機列表
     * @param cameras 相機信息列表
     */
    void updateCameraList(const std::vector<CameraInfo>& cameras);

    /**
     * @brief 設置抓取狀態
     * @param grabbing 是否正在抓取
     */
    void setGrabbingState(bool grabbing);

    /**
     * @brief 設置為視頻模式
     * @param isVideo 是否為視頻模式
     */
    void setVideoMode(bool isVideo);

    /**
     * @brief 設置連接狀態
     * @param connected 是否已連接
     */
    void setConnectedState(bool connected);

signals:
    void detectClicked();
    void connectClicked(int cameraIndex);
    void disconnectClicked();
    void startClicked();
    void stopClicked();
    void exposureChanged(double exposureUs);

private slots:
    void onCameraSelected(QListWidgetItem* item);
    void onConnectClicked();
    void onExposureChanged(int value);

private:
    void initUi();

    // UI 組件
    QGroupBox* m_groupBox;
    QPushButton* m_detectBtn;
    QListWidget* m_cameraList;
    QPushButton* m_connectBtn;
    QPushButton* m_disconnectBtn;
    QPushButton* m_startBtn;
    QPushButton* m_stopBtn;
    QSlider* m_exposureSlider;
    QLabel* m_exposureLabel;

    // 狀態
    int m_selectedCameraIndex = -1;
};

} // namespace basler

#endif // CAMERA_CONTROL_H
