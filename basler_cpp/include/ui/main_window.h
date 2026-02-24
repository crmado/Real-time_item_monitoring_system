#ifndef MAIN_WINDOW_H
#define MAIN_WINDOW_H

#include <QMainWindow>
#include <QTimer>
#include <QLabel>
#include <QSplitter>
#include <QTabWidget>
#include <QMutex>
#include <memory>

#include "core/camera_controller.h"
#include "core/source_manager.h"
#include "core/detection_controller.h"
#include "core/video_recorder.h"
#include "core/vibrator_controller.h"

// 前向聲明 Widget
namespace basler
{
    class VideoDisplayWidget;
    class CameraControlWidget;
    class RecordingControlWidget;
    class PackagingControlWidget;
    class DebugPanelWidget;
    class SystemMonitorWidget;
}

namespace basler
{

    /**
     * @brief 主視窗
     *
     * 與 Python 版本的主要差異：
     * 1. 所有相機操作都是異步的，通過信號通知完成
     * 2. UI 永遠不會被阻塞
     * 3. 狀態更新通過信號槽自動同步
     * 4. 使用 C++ RAII 確保資源正確釋放
     */
    class MainWindow : public QMainWindow
    {
        Q_OBJECT

    public:
        explicit MainWindow(QWidget *parent = nullptr);
        ~MainWindow();

    protected:
        void closeEvent(QCloseEvent *event) override;

    private slots:
        // ========== Camera Control ==========
        void onDetectCameras();
        void onDetectCamerasWithRetry();  // Smart scan with auto-retry
        void onConnectCamera();
        void onDisconnectCamera();
        void onStartGrabbing();
        void onStopGrabbing();

        // ========== 相機事件響應 ==========
        void onCameraConnected(const CameraInfo &info);
        void onCameraDisconnected();
        void onGrabbingStarted();
        void onGrabbingStopped();
        void onCameraError(const QString &error);

        // ========== 幀處理 ==========
        void onFrameReady(const cv::Mat &frame);
        void onFpsUpdated(double fps);
        void updateDisplay();

        // ========== 錄製控制 ==========
        void onStartRecording();
        void onStopRecording();
        void onRecordingStarted();
        void onRecordingStopped();
        void onRecordingError(const QString &error);

        // ========== 包裝/檢測控制 ==========
        void onStartPackaging();
        void onPausePackaging();
        void onResetCount();
        void onTargetCountChanged(int count);
        void onThresholdChanged(double full, double medium, double slow);
        void onPartTypeChanged(const QString &partId);
        void onDetectionMethodChanged(const QString &methodId);

        // ========== 瑕疵檢測 ==========
        void onStartDefectDetection();
        void onStopDefectDetection();
        void onClearDefectStats();
        void onDefectSensitivityChanged(double sensitivity);

        // ========== 檢測結果更新 ==========
        void onCountChanged(int count);
        void onVibratorSpeedChanged(VibratorSpeed speed);
        void onPackagingCompleted();
        void onDefectStatsUpdated(double passRate, int passCount, int failCount);

        // ========== Debug 參數 ==========
        void onRoiChanged(int x, int y, int width, int height);
        void onRoiSelectedFromDrag(int x, int y, int w, int h);
        void onGateLineFromClick(double ratio);
        void toggleFullscreenMode();  // 切換全螢幕影像模式（隱藏/顯示右側面板）

        // ========== 選單動作 ==========
        void onLoadVideo();
        void onLoadYoloModel();
        void onSaveConfig();
        void onLoadConfig();

    private:
        void setupUi();
        void setupMenuBar();
        void setupStatusBar();
        void setupKeyboardShortcuts();
        void connectCameraSignals();
        void connectRecordingSignals();
        void connectPackagingSignals();
        void connectDetectionSignals();
        void connectDebugSignals();

        void processFrame(const cv::Mat &frame);
        void updateButtonStates();

        // ========== 核心控制器 ==========
        std::unique_ptr<SourceManager> m_sourceManager;
        std::unique_ptr<DetectionController> m_detectionController;
        std::unique_ptr<VideoRecorder> m_videoRecorder;
        std::unique_ptr<DualVibratorManager> m_vibratorManager;

        // ========== UI 組件 ==========
        QSplitter *m_mainSplitter;

        // 控制面板組件
        CameraControlWidget *m_cameraControl;
        RecordingControlWidget *m_recordingControl;
        PackagingControlWidget *m_packagingControl;
        SystemMonitorWidget *m_systemMonitor;

        // 視頻顯示
        VideoDisplayWidget *m_videoDisplay;
        VideoDisplayWidget *m_cameraPreview; // 小型預覽窗口
        DebugPanelWidget *m_debugPanel;
        QTabWidget *m_controlPanel;          // 右側分頁面板（全螢幕時隱藏）

        // 狀態欄
        QLabel *m_statusLabel;
        QLabel *m_fpsLabel;
        QLabel *m_detectionLabel;
        QLabel *m_recordingLabel;
        QLabel *m_objectCountLabel;  // 即時偵測物件數
        QLabel *m_roiLabel;          // 當前 ROI 尺寸
        QLabel *m_bgStabilityLabel;  // 背景減除器穩定狀態

        // ========== 更新定時器 ==========
        QTimer *m_updateTimer;

        // ========== 幀緩衝 ==========
        cv::Mat m_latestFrame;
        cv::Mat m_processedFrame;
        QMutex m_frameMutex;

        // ========== 運行狀態 ==========
        bool m_isDetecting = false;
        bool m_isRecording = false;

        // ========== 全螢幕 HUD 資料 ==========
        bool m_isFullscreenMode = false;  // 是否為純視頻全螢幕模式
        int m_hudCount = 0;
        double m_hudFps = 0.0;
    };

} // namespace basler

#endif // MAIN_WINDOW_H
