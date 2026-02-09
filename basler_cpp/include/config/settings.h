#ifndef SETTINGS_H
#define SETTINGS_H

#include <QObject>
#include <QString>
#include <QJsonObject>
#include <QJsonDocument>
#include <QFile>
#include <QDir>
#include <QStandardPaths>
#include <memory>
#include <vector>

namespace basler {

/**
 * @brief 檢測配置 - 基於 basler_mvc 驗證參數
 */
struct DetectionConfig {
    // 面積過濾參數（極小零件優化）
    int minArea = 2;
    int maxArea = 3000;

    // 物件形狀過濾參數
    double minAspectRatio = 0.001;
    double maxAspectRatio = 100.0;
    double minExtent = 0.001;
    double maxSolidity = 5.0;

    // 背景減除參數（basler_mvc 驗證的最佳參數）
    int bgHistory = 1000;
    int bgVarThreshold = 3;
    bool detectShadows = false;
    double bgLearningRate = 0.001;

    // 邊緣檢測參數
    int gaussianBlurKernelSize = 1;
    int cannyLowThreshold = 3;     // Python basler_mvc 驗證值
    int cannyHighThreshold = 10;   // Python basler_mvc 驗證值
    int binaryThreshold = 1;

    // 形態學處理參數
    int dilateKernelSize = 1;
    int dilateIterations = 0;
    int closeKernelSize = 1;
    bool enableWatershedSeparation = true;
    int openingKernelSize = 1;
    int openingIterations = 0;
    int connectivity = 4;

    // 通用形態學參數（UI 面板使用）
    int morphKernelSize = 3;
    int morphIterations = 1;

    // ROI 檢測區域參數
    bool roiEnabled = true;
    int roiX = 0;
    int roiY = 0;
    int roiWidth = 640;
    int roiHeight = 120;           // Python basler_mvc 驗證值 (原 150)
    double roiPositionRatio = 0.12; // Python basler_mvc 驗證值 (原 0.10)

    // 瑕疵檢測參數
    double defectSensitivity = 0.5;

    // 高速模式參數
    bool ultraHighSpeedMode = false;
    int targetFps = 280;
    int highSpeedBgHistory = 100;
    int highSpeedBgVarThreshold = 8;
    int highSpeedMinArea = 1;
    int highSpeedMaxArea = 2000;
    int highSpeedBinaryThreshold = 3;

    QJsonObject toJson() const;
    static DetectionConfig fromJson(const QJsonObject& json);
};

/**
 * @brief 虛擬光柵計數配置
 */
struct GateConfig {
    bool enableGateCounting = true;
    double gateLinePositionRatio = 0.5;
    int gateTriggerRadius = 20;
    int gateHistoryFrames = 8;

    // 直接位置參數（UI 面板使用）
    int yPosition = 240;      // 虛擬閘門 Y 位置
    int triggerRadius = 20;   // 觸發半徑

    QJsonObject toJson() const;
    static GateConfig fromJson(const QJsonObject& json);
};

/**
 * @brief 定量包裝控制配置
 */
struct PackagingConfig {
    int targetCount = 150;
    bool enableAutoPackaging = false;

    // 速度控制閾值（百分比）
    double speedFullThreshold = 0.85;
    double speedMediumThreshold = 0.93;
    double speedSlowThreshold = 0.97;

    // UI 速度閾值（簡化版）
    int speedThreshold = 85;

    // 震動機速度設定（百分比）
    int vibratorSpeedFull = 100;
    int vibratorSpeedMedium = 60;
    int vibratorSpeedSlow = 30;
    int vibratorSpeedCreep = 10;

    // 反應時間補償
    int stopDelayFrames = 10;
    int advanceStopCount = 2;

    // 提示音設定
    bool enableSoundAlert = true;
    bool alertOnTargetReached = true;
    bool alertOnSpeedChange = false;

    QJsonObject toJson() const;
    static PackagingConfig fromJson(const QJsonObject& json);
};

/**
 * @brief 性能優化配置
 */
struct PerformanceConfig {
    double imageScale = 0.5;
    int skipFrames = 0;

    bool showGray = false;
    bool showBinary = false;
    bool showEdges = false;
    bool showCoords = false;
    bool showTiming = true;

    QJsonObject toJson() const;
    static PerformanceConfig fromJson(const QJsonObject& json);
};

/**
 * @brief 調試配置
 */
struct DebugConfig {
    bool debugSaveEnabled = false;
    QString debugSaveDir = "recordings/debug";
    int maxDebugFrames = 100;

    QJsonObject toJson() const;
    static DebugConfig fromJson(const QJsonObject& json);
};

/**
 * @brief UI 配置
 */
struct UIConfig {
    // 面積範圍滑桿
    int minAreaRangeMin = 1;
    int minAreaRangeMax = 100;
    int minAreaDefault = 2;
    int maxAreaRangeMin = 500;
    int maxAreaRangeMax = 10000;
    int maxAreaDefault = 3000;

    // 背景減除滑桿
    int bgVarThresholdRangeMin = 1;
    int bgVarThresholdRangeMax = 20;
    int bgVarThresholdDefault = 3;

    // 圖像縮放
    QString imageScaleDefault = "50%";

    QJsonObject toJson() const;
    static UIConfig fromJson(const QJsonObject& json);
};

/**
 * @brief 檢測方法配置
 */
struct DetectionMethodConfig {
    QString methodId;
    QString methodName;
    QString methodDescription;
    QString intent;  // "counting", "defect_detection", etc.
    QJsonObject config;

    QJsonObject toJson() const;
    static DetectionMethodConfig fromJson(const QJsonObject& json);
};

/**
 * @brief 零件配置檔
 */
struct PartProfile {
    QString partId;
    QString partName;
    QString partImage;
    QString description;

    bool isCircular = false;
    bool isReflective = false;
    bool requiresHighSpeed = false;

    std::vector<DetectionMethodConfig> availableMethods;
    QString currentMethodId = "counting";

    QJsonObject toJson() const;
    static PartProfile fromJson(const QJsonObject& json);
};

/**
 * @brief 應用程序總配置
 *
 * 使用單例模式，確保全局唯一配置實例
 */
class AppConfig : public QObject {
    Q_OBJECT

public:
    static AppConfig& instance();

    // 禁止複製
    AppConfig(const AppConfig&) = delete;
    AppConfig& operator=(const AppConfig&) = delete;

    // 配置訪問
    DetectionConfig& detection() { return m_detection; }
    const DetectionConfig& detection() const { return m_detection; }

    GateConfig& gate() { return m_gate; }
    const GateConfig& gate() const { return m_gate; }

    PackagingConfig& packaging() { return m_packaging; }
    const PackagingConfig& packaging() const { return m_packaging; }

    PerformanceConfig& performance() { return m_performance; }
    const PerformanceConfig& performance() const { return m_performance; }

    DebugConfig& debug() { return m_debug; }
    const DebugConfig& debug() const { return m_debug; }

    UIConfig& ui() { return m_ui; }
    const UIConfig& ui() const { return m_ui; }

    // 零件庫
    const std::vector<PartProfile>& partProfiles() const { return m_partProfiles; }
    PartProfile* getPartProfile(const QString& partId);
    const PartProfile* getPartProfile(const QString& partId) const;
    DetectionMethodConfig* getDetectionMethod(const QString& partId, const QString& methodId);

    QString currentPartId() const { return m_currentPartId; }
    void setCurrentPartId(const QString& partId);

    // 文件操作
    bool load(const QString& filePath = QString());
    bool save(const QString& filePath = QString()) const;
    void resetToDefault();

    // 配置文件路徑
    QString configFilePath() const { return m_configFilePath; }
    void setConfigFilePath(const QString& path) { m_configFilePath = path; }

signals:
    void configChanged();
    void detectionConfigChanged();
    void gateConfigChanged();
    void packagingConfigChanged();
    void partChanged(const QString& partId);

private:
    AppConfig();
    ~AppConfig() = default;

    void initDefaultPartProfiles();

    DetectionConfig m_detection;
    GateConfig m_gate;
    PackagingConfig m_packaging;
    PerformanceConfig m_performance;
    DebugConfig m_debug;
    UIConfig m_ui;

    std::vector<PartProfile> m_partProfiles;
    QString m_currentPartId = "default_small_part";

    QString m_configFilePath;
};

// 便捷函數
inline AppConfig& getConfig() {
    return AppConfig::instance();
}

// 別名：Settings = AppConfig（相容性）
using Settings = AppConfig;

} // namespace basler

#endif // SETTINGS_H
