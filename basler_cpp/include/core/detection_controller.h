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

// 前向聲明 YoloDetector
namespace basler { class YoloDetector; }

namespace basler
{

    // 前向聲明
    class AppConfig;

    /**
     * @brief 偵測模式列舉
     */
    enum class DetectionMode
    {
        Classical, // 傳統 MOG2 背景減除
        YOLO,      // YOLO 深度學習偵測
        Auto       // 自動：有模型用 YOLO，否則退回傳統
    };

    /**
     * @brief 檢測到的物件結構
     */
    struct DetectedObject
    {
        int x, y, w, h; // 邊界框
        int cx, cy;     // 中心點
        int area;       // 面積

        QRect boundingRect() const { return QRect(x, y, w, h); }
        QPoint center() const { return QPoint(cx, cy); }
    };

    /**
     * @brief 物件追蹤結構 - 增強型多特徵追蹤
     */
    struct ObjectTrack
    {
        int trackId;     // 追蹤 ID
        int x, y;        // 當前位置
        int w, h;        // 當前寬高
        int area;        // 當前面積
        int firstFrame;  // 首次出現幀
        int lastFrame;   // 最後出現幀
        int inRoiFrames; // 在 ROI 中的幀數
        int maxY, minY;  // Y 軸移動範圍
        int firstY;      // 首次出現的 Y 位置（用於方向驗證）
        bool counted;    // 是否已計數

        // 增強追蹤特徵
        std::vector<std::pair<int, int>> positions; // 位置歷史
        std::vector<int> areaHistory;               // 面積歷史
        double velocityX, velocityY;                // 速度（用於預測）
        double predictedX, predictedY;              // 預測位置
        int missedFrames;                           // 連續未匹配幀數
    };

    /**
     * @brief 震動機速度枚舉
     */
    enum class VibratorSpeed
    {
        STOP = 0,
        CREEP = 10,
        SLOW = 30,
        MEDIUM = 60,
        FULL = 100
    };

    /**
     * @brief 包裝狀態信息
     */
    struct PackagingStatus
    {
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
    class DetectionController : public QObject
    {
        Q_OBJECT
        Q_PROPERTY(bool enabled READ isEnabled WRITE setEnabled NOTIFY enabledChanged)
        Q_PROPERTY(int count READ count NOTIFY countChanged)

    public:
        explicit DetectionController(QObject *parent = nullptr);
        ~DetectionController();

        // 禁止複製
        DetectionController(const DetectionController &) = delete;
        DetectionController &operator=(const DetectionController &) = delete;

        // ===== 狀態查詢 =====
        bool isEnabled() const { return m_enabled; }
        int count() const { return m_crossingCounter; }
        int totalProcessedFrames() const { return m_totalProcessedFrames; }
        DetectionMode detectionMode() const { return m_detectionMode; }
        bool isYoloModelLoaded() const;

        // ===== 幀處理 =====
        /**
         * @brief 處理幀並執行小零件檢測
         * @param frame 輸入幀
         * @param[out] detectedObjects 檢測到的物件列表
         * @return 處理後的幀（帶繪製結果）
         */
        cv::Mat processFrame(const cv::Mat &frame, std::vector<DetectedObject> &detectedObjects);

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

        // YOLO 偵測控制
        bool loadYoloModel(const QString &modelPath);
        void setDetectionMode(DetectionMode mode);
        void setYoloConfidence(double threshold);
        void setYoloNmsThreshold(double threshold);
        void setYoloRoiUpscale(double factor);

        // 包裝控制
        void enablePackagingMode(bool enabled);
        void setTargetCount(int count);
        void setSpeedThresholds(double full, double medium, double slow);
        void resetPackaging();

    signals:
        void enabledChanged(bool enabled);
        void countChanged(int count);
        void objectsCrossedGate(int newCount); // 新物件穿越光柵
        void packagingCompleted();
        void vibratorSpeedChanged(VibratorSpeed speed);
        void detectionModeChanged(DetectionMode mode);
        void yoloModelLoaded(bool success);
        void yoloInferenceTimeUpdated(double ms);

    private:
        // 處理流程
        cv::Mat standardProcessing(const cv::Mat &processRegion);
        cv::Mat ultraHighSpeedProcessing(const cv::Mat &processRegion);
        std::vector<DetectedObject> detectObjects(const cv::Mat &processed);
        bool validateShape(int width, int height, int area);

        // YOLO 偵測流程
        std::vector<DetectedObject> yoloProcessing(const cv::Mat &roiImage, int roiY);
        void yoloBasedCounting(const std::vector<DetectedObject> &objects);

        // 判斷當前是否使用 YOLO 模式
        bool shouldUseYolo() const;

        // 虛擬光柵計數 - 基於物件追蹤
        void virtualGateCounting(const std::vector<DetectedObject> &objects);
        bool checkGateTriggerDuplicate(int cx, int cy);

        // 物件追蹤系統 - 增強型多特徵匹配
        void updateObjectTracks(const std::vector<DetectedObject> &objects);
        int findMatchingTrack(const DetectedObject &obj, double &outScore);
        double calculateMatchScore(const DetectedObject &obj, const ObjectTrack &track);
        double calculateIoU(int x1, int y1, int w1, int h1, int x2, int y2, int w2, int h2);
        void updateTrackVelocity(ObjectTrack &track);
        bool checkDuplicateCount(const ObjectTrack &track);

        // 繪製結果
        cv::Mat drawDetectionResults(cv::Mat frame, const std::vector<DetectedObject> &objects);

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
        double m_maxSolidity = 5.0;
        int m_bgHistory = 1000;
        int m_bgVarThreshold = 3;
        bool m_detectShadows = false;
        double m_bgLearningRate = 0.001;
        int m_connectivity = 4;

        // 邊緣檢測參數（basler_mvc 驗證值）
        int m_gaussianBlurKernelSize = 1;
        int m_cannyLowThreshold = 3;
        int m_cannyHighThreshold = 10;
        int m_binaryThreshold = 1;

        // 形態學參數（預設跳過，可由 UI 調整啟用）
        int m_dilateKernelSize = 1;
        int m_dilateIterations = 0;
        int m_closeKernelSize = 1;
        int m_openingKernelSize = 1;
        int m_openingIterations = 0;

        // ROI 參數（basler_mvc 驗證值）
        bool m_roiEnabled = true;
        int m_roiHeight = 120;
        double m_roiPositionRatio = 0.12;
        int m_currentRoiY = 0;
        int m_currentRoiHeight = 120;

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
        std::map<std::pair<int, int>, int> m_triggeredPositions; // {(x,y): frame_number}
        int m_crossingCounter = 0;
        int m_frameWidth = 640;
        int m_frameHeight = 480;
        int m_currentFrameCount = 0;
        int m_totalProcessedFrames = 0;
        int m_gateLineY = 0;

        // 物件追蹤系統（防重複計數）
        std::map<int, ObjectTrack> m_objectTracks;                                // {track_id: track_data}
        std::map<int, ObjectTrack> m_lostTracks;                                  // 暫時失去的追蹤
        std::vector<std::pair<std::pair<int, int>, int>> m_countedObjectsHistory; // {(x,y), frame}
        int m_nextTrackId = 1;
        // 追蹤參數
        int m_crossingToleranceX = 35;         // X 軸容錯距離
        int m_crossingToleranceY = 50;         // Y 軸容錯距離
        int m_minTrackFrames = 2;              // 最少追蹤幀數（保持 2 幀以適應快速掉落零件）
        int m_trackLifetime = 20;              // 追蹤生命週期
        int m_minYTravel = 2;                  // 最小 Y 移動距離
        int m_historyLength = 10;              // 歷史記錄長度
        int m_duplicateDistanceThreshold = 15; // 重複檢測距離
        int m_temporalTolerance = 6;           // 時間容錯
        int m_maxMissedFrames = 5;             // 最大可容忍的未匹配幀數

        // 匹配權重（距離 + 面積相似度，防止密集零件 Track Swap）
        double m_weightDistance = 0.8;  // 距離權重（80%）
        double m_weightArea = 0.2;      // 面積相似度權重（20%）
        double m_weightIoU = 0.0;       // IoU 權重（禁用，小零件不適用）
        double m_matchThreshold = 0.15; // 匹配閾值
        double m_directionConsistencyRatio = 0.7; // 方向一致性要求（70% 幀間 Y 遞增）

        // 包裝控制
        bool m_packagingEnabled = false;
        int m_targetCount = 150;
        int m_advanceStopCount = 2;
        double m_speedFullThreshold = 0.85;
        double m_speedMediumThreshold = 0.93;
        double m_speedSlowThreshold = 0.97;
        VibratorSpeed m_currentSpeed = VibratorSpeed::STOP;
        bool m_packagingCompleted = false;

        // YOLO 偵測
        std::unique_ptr<YoloDetector> m_yoloDetector;
        DetectionMode m_detectionMode = DetectionMode::Auto;

        // YOLO 簡化追蹤（用於計數）
        struct YoloTrack
        {
            int trackId;
            int cx, cy;       // 當前中心
            int firstY;       // 首次出現 Y
            int lastFrame;    // 最後出現幀
            bool counted;     // 是否已計數
        };
        std::map<int, YoloTrack> m_yoloTracks;
        int m_nextYoloTrackId = 1;

        // 互斥鎖
        mutable QMutex m_mutex;
    };

} // namespace basler

Q_DECLARE_METATYPE(basler::VibratorSpeed)
Q_DECLARE_METATYPE(basler::DetectedObject)
Q_DECLARE_METATYPE(basler::DetectionMode)

#endif // DETECTION_CONTROLLER_H
