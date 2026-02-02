#ifndef DETECTION_CONTROLLER_H
#define DETECTION_CONTROLLER_H

#include <QObject>
#include <QMutex>
#include <QPoint>
#include <QRect>
#include <opencv2/core.hpp>
#include <opencv2/video/background_segm.hpp>
#include <memory>
#include <vector>
#include <map>

namespace basler {

// 前向聲明
class AppConfig;

/**
 * @brief 檢測到的物件結構
 */
struct DetectedObject {
    int x, y, w, h;      // 邊界框
    int cx, cy;          // 中心點
    int area;            // 面積

    QRect boundingRect() const { return QRect(x, y, w, h); }
    QPoint center() const { return QPoint(cx, cy); }
};

/**
 * @brief 震動機速度枚舉
 */
enum class VibratorSpeed {
    STOP = 0,
    CREEP = 10,
    SLOW = 30,
    MEDIUM = 60,
    FULL = 100
};

/**
 * @brief 包裝狀態信息
 */
struct PackagingStatus {
    bool enabled = false;
    int currentCount = 0;
    int targetCount = 0;
    double progressPercent = 0.0;
    VibratorSpeed vibratorSpeed = VibratorSpeed::STOP;
    bool completed = false;
};

/**
 * @brief 小零件檢測控制器 - 背景減除 + 虛擬光柵計數
 *
 * 核心算法：
 * 1. 背景減除（MOG2）獲取前景遮罩
 * 2. 多重檢測策略（邊緣檢測 + 自適應閾值）
 * 3. 形態學處理優化
 * 4. 連通組件分析檢測物件
 * 5. 虛擬光柵計數（工業級方案）
 */
class DetectionController : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool enabled READ isEnabled WRITE setEnabled NOTIFY enabledChanged)
    Q_PROPERTY(int count READ count NOTIFY countChanged)

public:
    explicit DetectionController(QObject* parent = nullptr);
    ~DetectionController();

    // 禁止複製
    DetectionController(const DetectionController&) = delete;
    DetectionController& operator=(const DetectionController&) = delete;

    // ===== 狀態查詢 =====
    bool isEnabled() const { return m_enabled; }
    int count() const { return m_crossingCounter; }
    int totalProcessedFrames() const { return m_totalProcessedFrames; }

    // ===== 幀處理 =====
    /**
     * @brief 處理幀並執行小零件檢測
     * @param frame 輸入幀
     * @param[out] detectedObjects 檢測到的物件列表
     * @return 處理後的幀（帶繪製結果）
     */
    cv::Mat processFrame(const cv::Mat& frame, std::vector<DetectedObject>& detectedObjects);

    // ===== 包裝控制 =====
    PackagingStatus getPackagingStatus() const;

public slots:
    // 檢測控制
    void setEnabled(bool enabled);
    void enable() { setEnabled(true); }
    void disable() { setEnabled(false); }
    void reset();

    // 參數設置
    void setMinArea(int area);
    void setMaxArea(int area);
    void setBgVarThreshold(int threshold);
    void setBgLearningRate(double rate);
    void setRoiEnabled(bool enabled);
    void setRoiHeight(int height);
    void setRoiPositionRatio(double ratio);
    void setGateTriggerRadius(int radius);
    void setGateHistoryFrames(int frames);
    void setGateLinePositionRatio(double ratio);
    void setUltraHighSpeedMode(bool enabled, int targetFps = 280);

    // 包裝控制
    void enablePackagingMode(bool enabled);
    void setTargetCount(int count);
    void setSpeedThresholds(double full, double medium, double slow);
    void resetPackaging();

signals:
    void enabledChanged(bool enabled);
    void countChanged(int count);
    void objectsCrossedGate(int newCount);  // 新物件穿越光柵
    void packagingCompleted();
    void vibratorSpeedChanged(VibratorSpeed speed);

private:
    // 處理流程
    cv::Mat standardProcessing(const cv::Mat& processRegion);
    cv::Mat ultraHighSpeedProcessing(const cv::Mat& processRegion);
    std::vector<DetectedObject> detectObjects(const cv::Mat& processed);
    bool validateShape(int width, int height, int area);

    // 虛擬光柵計數
    void virtualGateCounting(const std::vector<DetectedObject>& objects);
    bool checkGateTriggerDuplicate(int cx, int cy);

    // 繪製結果
    cv::Mat drawDetectionResults(cv::Mat frame, const std::vector<DetectedObject>& objects);

    // 包裝控制
    void updateVibratorSpeed();

    // 背景減除器
    void resetBackgroundSubtractor();
    cv::Ptr<cv::BackgroundSubtractorMOG2> m_bgSubtractor;
    double m_currentLearningRate = 0.001;

    // 狀態
    bool m_enabled = false;

    // 檢測參數（從配置讀取）
    int m_minArea = 2;
    int m_maxArea = 3000;
    double m_minAspectRatio = 0.001;
    double m_maxAspectRatio = 100.0;
    double m_minExtent = 0.001;
    int m_bgHistory = 1000;
    int m_bgVarThreshold = 3;
    bool m_detectShadows = false;
    double m_bgLearningRate = 0.001;
    int m_connectivity = 4;

    // ROI 參數
    bool m_roiEnabled = true;
    int m_roiHeight = 150;
    double m_roiPositionRatio = 0.10;
    int m_currentRoiY = 0;
    int m_currentRoiHeight = 150;

    // 高速模式參數
    bool m_ultraHighSpeedMode = false;
    int m_targetFps = 280;
    int m_highSpeedBgHistory = 100;
    int m_highSpeedBgVarThreshold = 8;
    int m_highSpeedMinArea = 1;
    int m_highSpeedMaxArea = 2000;

    // 虛擬光柵參數
    bool m_enableGateCounting = true;
    double m_gateLinePositionRatio = 0.5;
    int m_gateTriggerRadius = 20;
    int m_gateHistoryFrames = 8;

    // 光柵狀態
    std::map<std::pair<int, int>, int> m_triggeredPositions;  // {(x,y): frame_number}
    int m_crossingCounter = 0;
    int m_frameWidth = 640;
    int m_frameHeight = 480;
    int m_currentFrameCount = 0;
    int m_totalProcessedFrames = 0;
    int m_gateLineY = 0;

    // 包裝控制
    bool m_packagingEnabled = false;
    int m_targetCount = 150;
    int m_advanceStopCount = 2;
    double m_speedFullThreshold = 0.85;
    double m_speedMediumThreshold = 0.93;
    double m_speedSlowThreshold = 0.97;
    VibratorSpeed m_currentSpeed = VibratorSpeed::STOP;
    bool m_packagingCompleted = false;

    // 互斥鎖
    mutable QMutex m_mutex;
};

} // namespace basler

Q_DECLARE_METATYPE(basler::VibratorSpeed)
Q_DECLARE_METATYPE(basler::DetectedObject)

#endif // DETECTION_CONTROLLER_H
