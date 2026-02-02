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

namespace basler {

/**
 * @brief 調試面板
 *
 * 提供實時調整檢測參數的功能
 * 包含面積、背景減除、ROI、光柵等參數控制
 */
class DebugPanelWidget : public QWidget {
    Q_OBJECT

public:
    explicit DebugPanelWidget(QWidget* parent = nullptr);
    ~DebugPanelWidget() = default;

public slots:
    // 狀態更新
    void updateFps(double fps);
    void updateFrameCount(int count);
    void updateDetectionCount(int count);

    // 參數同步（從配置載入）
    void syncFromConfig();

signals:
    // 參數變更信號
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

    // 其他
    void resetTotalCount();

private slots:
    void onMinAreaChanged(int value);
    void onMaxAreaChanged(int value);
    void onBgVarThresholdChanged(int value);
    void onBgLearningRateChanged(double value);
    void onRoiEnabledChanged(bool enabled);
    void onRoiHeightChanged(int value);
    void onRoiPositionChanged(double value);
    void onGateTriggerRadiusChanged(int value);
    void onGateHistoryFramesChanged(int value);
    void onGateLinePositionChanged(double value);
    void onImageScaleChanged(int index);
    void onSkipFramesChanged(int value);

private:
    void initUi();
    QWidget* createDetectionParamsGroup();
    QWidget* createBgSubtractorGroup();
    QWidget* createRoiGroup();
    QWidget* createGateGroup();
    QWidget* createPerformanceGroup();
    QWidget* createVideoControlGroup();
    QWidget* createActionButtonsGroup();

    // 檢測參數
    QSpinBox* m_minAreaSpin;
    QSpinBox* m_maxAreaSpin;

    // 背景減除參數
    QSpinBox* m_bgVarThresholdSpin;
    QDoubleSpinBox* m_bgLearningRateSpin;

    // ROI 參數
    QCheckBox* m_roiEnabledCheck;
    QSpinBox* m_roiHeightSpin;
    QDoubleSpinBox* m_roiPositionSpin;

    // 虛擬光柵參數
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

    // 滾動區域
    QScrollArea* m_scrollArea;
};

} // namespace basler

#endif // DEBUG_PANEL_H
