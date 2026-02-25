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
        void resizeEvent(QResizeEvent *event) override;  // 響應式佈局：自動摺疊右側面板

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
        void toggleSplitView();       // 切換分割顯示模式（左右並排兩個視角）

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
        void exportPackagingReport(int target, int actual, double elapsedSec);
        void applyTheme(bool isDark);       // 套用 Dark/Light 主題（全局 QSS）
        void applyFontScale(double scale);  // 套用字體縮放比例

        // ========== 核心控制器 ==========
        std::unique_ptr<SourceManager> m_sourceManager;
        std::unique_ptr<DetectionController> m_detectionController;
        std::unique_ptr<VideoRecorder> m_videoRecorder;
        std::unique_ptr<DualVibratorManager> m_vibratorManager;

        // ========== UI 組件 ==========
        QSplitter *m_mainSplitter         = nullptr;

        // 控制面板組件
        CameraControlWidget    *m_cameraControl     = nullptr;
        RecordingControlWidget *m_recordingControl  = nullptr;
        PackagingControlWidget *m_packagingControl  = nullptr;
        SystemMonitorWidget    *m_systemMonitor     = nullptr;

        // 視頻顯示
        VideoDisplayWidget *m_videoDisplay   = nullptr;
        VideoDisplayWidget *m_videoDisplay2  = nullptr; // 分割視圖第二面板（預設隱藏）
        QSplitter          *m_displaySplitter = nullptr; // 左側顯示區分割器
        VideoDisplayWidget *m_cameraPreview  = nullptr; // 小型預覽窗口
        DebugPanelWidget   *m_debugPanel     = nullptr;
        QTabWidget         *m_controlPanel   = nullptr; // 右側分頁面板（全螢幕時隱藏）

        // 狀態欄
        QLabel *m_statusLabel      = nullptr;
        QLabel *m_fpsLabel         = nullptr;
        QLabel *m_detectionLabel   = nullptr;
        QLabel *m_recordingLabel   = nullptr;
        QLabel *m_objectCountLabel = nullptr;  // 即時偵測物件數
        QLabel *m_roiLabel         = nullptr;  // 當前 ROI 尺寸
        QLabel *m_bgStabilityLabel = nullptr;  // 背景減除器穩定狀態

        // ========== 更新定時器 ==========
        QTimer *m_updateTimer = nullptr;

        // ========== 幀緩衝 ==========
        cv::Mat m_latestFrame;
        cv::Mat m_processedFrame;
        QMutex m_frameMutex;

        // ========== 運行狀態 ==========
        bool m_isDetecting = false;
        bool m_isRecording = false;
        qint64 m_packagingStartTime = 0;  // 包裝開始時間戳（ms），用於計算耗時/速率

        // ========== 全螢幕 HUD 資料 ==========
        bool m_isFullscreenMode = false;  // 是否為純視頻全螢幕模式
        int m_hudCount = 0;
        double m_hudFps = 0.0;

        // ========== 調試視覺化模式 ==========
        int m_debugViewMode = 0;  // 0=原始, 1=前景遮罩, 2=Canny, 3=三重聯合, 4=最終形態學

        // ========== 分割顯示狀態 ==========
        bool m_isSplitView = false;  // 是否為分割顯示模式（左：選定視圖，右：互補幀）

        // ========== 主題 / 字體 ==========
        bool m_isDarkTheme = true;    // true=深色（預設），false=淺色
        double m_fontScale = 1.0;     // 字體縮放比例（1.0/1.25/1.5）
        int m_baseFontPt  = 0;        // 啟動時原始字體 point size
    };

} // namespace basler

#endif // MAIN_WINDOW_H
