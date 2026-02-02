#ifndef MAIN_WINDOW_H
#define MAIN_WINDOW_H

#include <QMainWindow>
#include <QTimer>
#include <QLabel>
#include <memory>

#include "core/camera_controller.h"

namespace basler {

/**
 * @brief 主視窗
 *
 * 與 Python 版本的主要差異：
 * 1. 所有相機操作都是異步的，通過信號通知完成
 * 2. UI 永遠不會被阻塞
 * 3. 狀態更新通過信號槽自動同步
 */
class MainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow();

protected:
    void closeEvent(QCloseEvent* event) override;

private slots:
    // 相機控制
    void onDetectCameras();
    void onConnectCamera();
    void onDisconnectCamera();
    void onStartGrabbing();
    void onStopGrabbing();

    // 相機事件響應
    void onCameraConnected(const CameraInfo& info);
    void onCameraDisconnected();
    void onGrabbingStarted();
    void onGrabbingStopped();
    void onCameraError(const QString& error);
    void onCameraStateChanged(CameraState state);

    // 顯示更新
    void onFrameReady(const cv::Mat& frame);
    void onFpsUpdated(double fps);
    void updateDisplay();

private:
    void setupUi();
    void setupMenuBar();
    void setupStatusBar();
    void connectSignals();

    // 核心控制器
    std::unique_ptr<CameraController> m_cameraController;

    // UI 組件（待實現）
    QLabel* m_videoDisplay;
    QLabel* m_statusLabel;
    QLabel* m_fpsLabel;

    // 更新定時器
    QTimer* m_updateTimer;

    // 最新幀
    cv::Mat m_latestFrame;
    QMutex m_frameMutex;
};

} // namespace basler

#endif // MAIN_WINDOW_H
