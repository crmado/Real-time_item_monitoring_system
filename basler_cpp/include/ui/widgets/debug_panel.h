#ifndef DEBUG_PANEL_H
#define DEBUG_PANEL_H

#include <QWidget>
#include <QGroupBox>
#include <QSlider>
#include <QSpinBox>
#include <QDoubleSpinBox>
#include <QCheckBox>
#include <QComboBox>
#include <QPushButton>
#include <QLabel>
#include <QScrollArea>
#include <opencv2/core.hpp>

namespace basler {

/**
 * @brief 調試面板
 *
 * 提供實時調整檢測參數的功能
 * 包含面積、背景減除、ROI、邊緣檢測、形態學、光柵等參數控制
 */
class DebugPanelWidget : public QWidget {
    Q_OBJECT

public:
    explicit DebugPanelWidget(QWidget* parent = nullptr);
    ~DebugPanelWidget() = default;

    /**
     * @brief 是否顯示調試視圖
     */
    bool isShowingDebugView() const { return m_showDebugView; }

public slots:
    // 狀態更新
    void updateFps(double fps);
    void updateFrameCount(int count);
    void updateDetectionCount(int count);

    /**
     * @brief 更新調試圖像顯示
     */
    void updateDebugImage(const cv::Mat& image);

    // 參數同步（從配置載入）
    void syncFromConfig();

    // YOLO 狀態更新
    void updateYoloModelStatus(bool loaded);
    void updateYoloInferenceTime(double ms);

signals:
    // ===== ROI 參數 =====
    void roiChanged(int x, int y, int width, int height);
    void roiEnabledChanged(bool enabled);

    // ===== 背景減除參數 =====
    void bgHistoryChanged(int history);
    void bgVarThresholdChanged(double threshold);
    void bgLearningRateChanged(double rate);

    // ===== 邊緣檢測參數 =====
    void cannyLowChanged(int threshold);
    void cannyHighChanged(int threshold);

    // ===== 形態學參數 =====
    void morphKernelSizeChanged(int size);
    void morphIterationsChanged(int iterations);

    // ===== 面積參數 =====
    void minAreaChanged(int area);
    void maxAreaChanged(int area);

    // ===== 虛擬閘門參數 =====
    void gateYPositionChanged(int y);
    void gateTriggerRadiusChanged(int radius);
    void gateHistoryFramesChanged(int frames);
    void gateLinePositionChanged(double ratio);

    // ===== 性能參數 =====
    void imageScaleChanged(double scale);
    void skipFramesChanged(int frames);

    // ===== 控制信號 =====
    void paramChanged(const QString& paramName, const QVariant& value);
    void resetParams();
    void saveConfig();
    void loadConfig();

    // 測試視頻控制
    void loadTestVideo();
    void playVideo();
    void pauseVideo();
    void prevFrame();
    void nextFrame();
    void jumpToFrame(int frame);
    void screenshot();

    // YOLO 偵測控制
    void yoloModeChanged(int modeIndex);          // 0=Classical, 1=YOLO, 2=Auto
    void yoloConfidenceChanged(double threshold);
    void yoloNmsThresholdChanged(double threshold);
    void yoloRoiUpscaleChanged(double factor);
    void loadYoloModelRequested();

    // 其他
    void resetTotalCount();
    void debugViewToggled(bool show);

private slots:
    void onMinAreaChanged(int value);
    void onMaxAreaChanged(int value);
    void onBgHistoryChanged(int value);
    void onBgVarThresholdChanged(int value);
    void onBgLearningRateChanged(double value);
    void onCannyLowChanged(int value);
    void onCannyHighChanged(int value);
    void onMorphKernelSizeChanged(int value);
    void onMorphIterationsChanged(int value);
    void onRoiEnabledChanged(bool enabled);
    void onRoiXChanged(int value);
    void onRoiYChanged(int value);
    void onRoiWidthChanged(int value);
    void onRoiHeightChanged(int value);
    void onGateYPositionChanged(int value);
    void onGateTriggerRadiusChanged(int value);
    void onGateHistoryFramesChanged(int value);
    void onGateLinePositionChanged(double value);
    void onImageScaleChanged(int index);
    void onSkipFramesChanged(int value);
    void onShowDebugViewChanged(bool show);
    void onLockParamsChanged(bool locked);
    void onYoloModeChanged(int index);
    void onYoloConfidenceChanged(double value);
    void onYoloNmsChanged(double value);
    void onYoloRoiUpscaleChanged(double value);

private:
    void initUi();
    QWidget* createDetectionParamsGroup();
    QWidget* createBgSubtractorGroup();
    QWidget* createEdgeDetectionGroup();
    QWidget* createMorphologyGroup();
    QWidget* createRoiGroup();
    QWidget* createGateGroup();
    QWidget* createPerformanceGroup();
    QWidget* createVideoControlGroup();
    QWidget* createYoloGroup();
    QWidget* createDebugViewGroup();
    QWidget* createActionButtonsGroup();

    // 檢測參數
    QSpinBox* m_minAreaSpin;
    QSpinBox* m_maxAreaSpin;

    // 背景減除參數
    QSpinBox* m_bgHistorySpin;
    QSpinBox* m_bgVarThresholdSpin;
    QDoubleSpinBox* m_bgLearningRateSpin;

    // 邊緣檢測參數
    QSpinBox* m_cannyLowSpin;
    QSpinBox* m_cannyHighSpin;

    // 形態學參數
    QSpinBox* m_morphKernelSizeSpin;
    QSpinBox* m_morphIterationsSpin;

    // ROI 參數
    QCheckBox* m_roiEnabledCheck;
    QSpinBox* m_roiXSpin;
    QSpinBox* m_roiYSpin;
    QSpinBox* m_roiWidthSpin;
    QSpinBox* m_roiHeightSpin;

    // 虛擬光柵參數
    QSpinBox* m_gateYPositionSpin;
    QSpinBox* m_gateTriggerRadiusSpin;
    QSpinBox* m_gateHistoryFramesSpin;
    QDoubleSpinBox* m_gateLinePositionSpin;

    // 性能參數
    QComboBox* m_imageScaleCombo;
    QSpinBox* m_skipFramesSpin;

    // 狀態顯示
    QLabel* m_fpsLabel;
    QLabel* m_frameCountLabel;
    QLabel* m_detectionCountLabel;

    // 調試視圖
    QCheckBox* m_showDebugViewCheck;
    QLabel* m_debugImageLabel;
    bool m_showDebugView = false;

    // 視頻控制
    QPushButton* m_loadVideoBtn;
    QPushButton* m_playBtn;
    QPushButton* m_pauseBtn;
    QPushButton* m_prevFrameBtn;
    QPushButton* m_nextFrameBtn;
    QSpinBox* m_jumpFrameSpin;
    QPushButton* m_screenshotBtn;

    // 操作按鈕
    QPushButton* m_resetParamsBtn;
    QPushButton* m_saveConfigBtn;
    QPushButton* m_loadConfigBtn;
    QPushButton* m_resetCountBtn;

    // YOLO 控制
    QComboBox* m_yoloModeCombo;
    QDoubleSpinBox* m_yoloConfidenceSpin;
    QDoubleSpinBox* m_yoloNmsSpin;
    QDoubleSpinBox* m_yoloRoiUpscaleSpin;
    QPushButton* m_loadYoloModelBtn;
    QLabel* m_yoloStatusLabel;
    QLabel* m_yoloInferenceLabel;

    // 參數鎖定
    QCheckBox* m_lockParamsCheck;
    QList<QWidget*> m_paramGroupWidgets;  // 參數組容器（鎖定/解鎖用）

    // 跳轉按鈕
    QPushButton* m_jumpFrameBtn;

    // 滾動區域
    QScrollArea* m_scrollArea;
};

} // namespace basler

#endif // DEBUG_PANEL_H
