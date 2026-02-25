#include "config/settings.h"
#include <QDebug>
#include <QJsonArray>
#include <QCoreApplication>

namespace basler {

// ============================================================================
// DetectionConfig
// ============================================================================

QJsonObject DetectionConfig::toJson() const
{
    return QJsonObject{
        {"minArea", minArea},
        {"maxArea", maxArea},
        {"minAspectRatio", minAspectRatio},
        {"maxAspectRatio", maxAspectRatio},
        {"minExtent", minExtent},
        {"maxSolidity", maxSolidity},
        {"bgHistory", bgHistory},
        {"bgVarThreshold", bgVarThreshold},
        {"detectShadows", detectShadows},
        {"bgLearningRate", bgLearningRate},
        {"gaussianBlurKernelSize", gaussianBlurKernelSize},
        {"cannyLowThreshold", cannyLowThreshold},
        {"cannyHighThreshold", cannyHighThreshold},
        {"binaryThreshold", binaryThreshold},
        {"dilateKernelSize", dilateKernelSize},
        {"dilateIterations", dilateIterations},
        {"closeKernelSize", closeKernelSize},
        {"enableWatershedSeparation", enableWatershedSeparation},
        {"openingKernelSize", openingKernelSize},
        {"openingIterations", openingIterations},
        {"connectivity", connectivity},
        {"roiEnabled", roiEnabled},
        {"roiX", roiX},
        {"roiWidth", roiWidth},
        {"roiHeight", roiHeight},
        {"roiPositionRatio", roiPositionRatio},
        {"ultraHighSpeedMode", ultraHighSpeedMode},
        {"targetFps", targetFps},
        {"highSpeedBgHistory", highSpeedBgHistory},
        {"highSpeedBgVarThreshold", highSpeedBgVarThreshold},
        {"highSpeedMinArea", highSpeedMinArea},
        {"highSpeedMaxArea", highSpeedMaxArea},
        {"highSpeedBinaryThreshold", highSpeedBinaryThreshold}
    };
}

DetectionConfig DetectionConfig::fromJson(const QJsonObject& json)
{
    DetectionConfig config;
    config.minArea = json.value("minArea").toInt(config.minArea);
    config.maxArea = json.value("maxArea").toInt(config.maxArea);
    config.minAspectRatio = json.value("minAspectRatio").toDouble(config.minAspectRatio);
    config.maxAspectRatio = json.value("maxAspectRatio").toDouble(config.maxAspectRatio);
    config.minExtent = json.value("minExtent").toDouble(config.minExtent);
    config.maxSolidity = json.value("maxSolidity").toDouble(config.maxSolidity);
    config.bgHistory = json.value("bgHistory").toInt(config.bgHistory);
    config.bgVarThreshold = json.value("bgVarThreshold").toInt(config.bgVarThreshold);
    config.detectShadows = json.value("detectShadows").toBool(config.detectShadows);
    config.bgLearningRate = json.value("bgLearningRate").toDouble(config.bgLearningRate);
    config.roiEnabled = json.value("roiEnabled").toBool(config.roiEnabled);
    config.roiX      = json.value("roiX").toInt(config.roiX);
    config.roiWidth  = json.value("roiWidth").toInt(config.roiWidth);
    config.roiHeight = json.value("roiHeight").toInt(config.roiHeight);
    config.roiPositionRatio = json.value("roiPositionRatio").toDouble(config.roiPositionRatio);
    config.ultraHighSpeedMode = json.value("ultraHighSpeedMode").toBool(config.ultraHighSpeedMode);
    config.targetFps = json.value("targetFps").toInt(config.targetFps);
    return config;
}

// ============================================================================
// CameraConfig
// ============================================================================

QJsonObject CameraConfig::toJson() const
{
    return QJsonObject{
        {"targetFps", targetFps},
        {"exposureTimeUs", exposureTimeUs}
    };
}

CameraConfig CameraConfig::fromJson(const QJsonObject& json)
{
    CameraConfig config;
    config.targetFps = json.value("targetFps").toDouble(config.targetFps);
    config.exposureTimeUs = json.value("exposureTimeUs").toDouble(config.exposureTimeUs);
    return config;
}

// ============================================================================
// GateConfig
// ============================================================================

QJsonObject GateConfig::toJson() const
{
    return QJsonObject{
        {"enableGateCounting", enableGateCounting},
        {"gateLinePositionRatio", gateLinePositionRatio},
        {"gateTriggerRadius", gateTriggerRadius},
        {"gateHistoryFrames", gateHistoryFrames}
    };
}

GateConfig GateConfig::fromJson(const QJsonObject& json)
{
    GateConfig config;
    config.enableGateCounting = json.value("enableGateCounting").toBool(config.enableGateCounting);
    config.gateLinePositionRatio = json.value("gateLinePositionRatio").toDouble(config.gateLinePositionRatio);
    config.gateTriggerRadius = json.value("gateTriggerRadius").toInt(config.gateTriggerRadius);
    config.gateHistoryFrames = json.value("gateHistoryFrames").toInt(config.gateHistoryFrames);
    return config;
}

// ============================================================================
// PackagingConfig
// ============================================================================

QJsonObject PackagingConfig::toJson() const
{
    return QJsonObject{
        {"targetCount", targetCount},
        {"enableAutoPackaging", enableAutoPackaging},
        {"speedFullThreshold", speedFullThreshold},
        {"speedMediumThreshold", speedMediumThreshold},
        {"speedSlowThreshold", speedSlowThreshold},
        {"vibratorSpeedFull", vibratorSpeedFull},
        {"vibratorSpeedMedium", vibratorSpeedMedium},
        {"vibratorSpeedSlow", vibratorSpeedSlow},
        {"vibratorSpeedCreep", vibratorSpeedCreep},
        {"stopDelayFrames", stopDelayFrames},
        {"advanceStopCount", advanceStopCount},
        {"enableSoundAlert", enableSoundAlert},
        {"alertOnTargetReached", alertOnTargetReached},
        {"alertOnSpeedChange", alertOnSpeedChange}
    };
}

PackagingConfig PackagingConfig::fromJson(const QJsonObject& json)
{
    PackagingConfig config;
    config.targetCount = json.value("targetCount").toInt(config.targetCount);
    config.enableAutoPackaging = json.value("enableAutoPackaging").toBool(config.enableAutoPackaging);
    config.speedFullThreshold = json.value("speedFullThreshold").toDouble(config.speedFullThreshold);
    config.speedMediumThreshold = json.value("speedMediumThreshold").toDouble(config.speedMediumThreshold);
    config.speedSlowThreshold = json.value("speedSlowThreshold").toDouble(config.speedSlowThreshold);
    config.advanceStopCount = json.value("advanceStopCount").toInt(config.advanceStopCount);
    return config;
}

// ============================================================================
// YoloConfig
// ============================================================================

QJsonObject YoloConfig::toJson() const
{
    return QJsonObject{
        {"modelPath", modelPath},
        {"confidenceThreshold", confidenceThreshold},
        {"nmsThreshold", nmsThreshold},
        {"roiUpscaleFactor", roiUpscaleFactor},
        {"inputSize", inputSize},
        {"enabled", enabled}
    };
}

YoloConfig YoloConfig::fromJson(const QJsonObject& json)
{
    YoloConfig config;
    config.modelPath = json.value("modelPath").toString(config.modelPath);
    config.confidenceThreshold = json.value("confidenceThreshold").toDouble(config.confidenceThreshold);
    config.nmsThreshold = json.value("nmsThreshold").toDouble(config.nmsThreshold);
    config.roiUpscaleFactor = json.value("roiUpscaleFactor").toDouble(config.roiUpscaleFactor);
    config.inputSize = json.value("inputSize").toInt(config.inputSize);
    config.enabled = json.value("enabled").toBool(config.enabled);
    return config;
}

// ============================================================================
// PerformanceConfig, DebugConfig, UIConfig
// ============================================================================

QJsonObject PerformanceConfig::toJson() const
{
    return QJsonObject{
        {"targetProcessingWidth", targetProcessingWidth},
        {"skipFrames", skipFrames},
        {"showGray", showGray},
        {"showBinary", showBinary},
        {"showEdges", showEdges},
        {"showCoords", showCoords},
        {"showTiming", showTiming}
    };
}

PerformanceConfig PerformanceConfig::fromJson(const QJsonObject& json)
{
    PerformanceConfig config;
    config.targetProcessingWidth = json.value("targetProcessingWidth").toInt(config.targetProcessingWidth);
    config.skipFrames = json.value("skipFrames").toInt(config.skipFrames);
    return config;
}

QJsonObject DebugConfig::toJson() const
{
    return QJsonObject{
        {"debugSaveEnabled", debugSaveEnabled},
        {"debugSaveDir", debugSaveDir},
        {"maxDebugFrames", maxDebugFrames}
    };
}

DebugConfig DebugConfig::fromJson(const QJsonObject& json)
{
    DebugConfig config;
    config.debugSaveEnabled = json.value("debugSaveEnabled").toBool(config.debugSaveEnabled);
    config.debugSaveDir = json.value("debugSaveDir").toString(config.debugSaveDir);
    config.maxDebugFrames = json.value("maxDebugFrames").toInt(config.maxDebugFrames);
    return config;
}

QJsonObject UIConfig::toJson() const
{
    return QJsonObject{
        {"minAreaRangeMin", minAreaRangeMin},
        {"minAreaRangeMax", minAreaRangeMax},
        {"minAreaDefault", minAreaDefault},
        {"maxAreaRangeMin", maxAreaRangeMin},
        {"maxAreaRangeMax", maxAreaRangeMax},
        {"maxAreaDefault", maxAreaDefault},
        {"bgVarThresholdDefault", bgVarThresholdDefault}
    };
}

UIConfig UIConfig::fromJson(const QJsonObject& /*json*/)
{
    return UIConfig{};
}

// ============================================================================
// DetectionMethodConfig & PartProfile
// ============================================================================

QJsonObject DetectionMethodConfig::toJson() const
{
    return QJsonObject{
        {"methodId", methodId},
        {"methodName", methodName},
        {"methodDescription", methodDescription},
        {"intent", intent},
        {"config", config}
    };
}

DetectionMethodConfig DetectionMethodConfig::fromJson(const QJsonObject& json)
{
    DetectionMethodConfig method;
    method.methodId = json.value("methodId").toString();
    method.methodName = json.value("methodName").toString();
    method.methodDescription = json.value("methodDescription").toString();
    method.intent = json.value("intent").toString();
    method.config = json.value("config").toObject();
    return method;
}

QJsonObject PartProfile::toJson() const
{
    QJsonArray methodsArray;
    for (const auto& method : availableMethods) {
        methodsArray.append(method.toJson());
    }

    return QJsonObject{
        {"partId", partId},
        {"partName", partName},
        {"partImage", partImage},
        {"description", description},
        {"isCircular", isCircular},
        {"isReflective", isReflective},
        {"requiresHighSpeed", requiresHighSpeed},
        {"availableMethods", methodsArray},
        {"currentMethodId", currentMethodId}
    };
}

PartProfile PartProfile::fromJson(const QJsonObject& json)
{
    PartProfile profile;
    profile.partId = json.value("partId").toString();
    profile.partName = json.value("partName").toString();
    profile.partImage = json.value("partImage").toString();
    profile.description = json.value("description").toString();
    profile.isCircular = json.value("isCircular").toBool();
    profile.isReflective = json.value("isReflective").toBool();
    profile.requiresHighSpeed = json.value("requiresHighSpeed").toBool();
    profile.currentMethodId = json.value("currentMethodId").toString("counting");

    QJsonArray methodsArray = json.value("availableMethods").toArray();
    for (const auto& methodVal : methodsArray) {
        profile.availableMethods.push_back(DetectionMethodConfig::fromJson(methodVal.toObject()));
    }

    return profile;
}

// ============================================================================
// AppConfig
// ============================================================================

AppConfig::AppConfig()
{
    // 設置預設配置文件路徑
    m_configFilePath = QCoreApplication::applicationDirPath() + "/config/detection_params.json";

    // 初始化預設零件配置
    initDefaultPartProfiles();
}

AppConfig& AppConfig::instance()
{
    static AppConfig instance;
    return instance;
}

void AppConfig::initDefaultPartProfiles()
{
    // 預設零件：極小零件
    PartProfile defaultPart;
    defaultPart.partId = "default_small_part";
    defaultPart.partName = "極小零件（已驗證）";
    defaultPart.description = "極小螺絲/零件（basler_mvc 驗證參數）";
    defaultPart.isReflective = true;

    // 計數方法
    DetectionMethodConfig countingMethod;
    countingMethod.methodId = "counting";
    countingMethod.methodName = "定量計數";
    countingMethod.methodDescription = "虛擬光柵計數法";
    countingMethod.intent = "counting";
    countingMethod.config = QJsonObject{
        {"minArea", 2},
        {"maxArea", 3000},
        {"bgVarThreshold", 3},
        {"targetCount", 150}
    };
    defaultPart.availableMethods.push_back(countingMethod);

    // 瑕疵檢測方法
    DetectionMethodConfig defectMethod;
    defectMethod.methodId = "defect_detection";
    defectMethod.methodName = "表面瑕疵檢測";
    defectMethod.methodDescription = "影像瑕疵分析（開發中）";
    defectMethod.intent = "defect_detection";
    defectMethod.config = QJsonObject{
        {"defectThreshold", 0.5},
        {"edgeDetectionEnabled", true}
    };
    defaultPart.availableMethods.push_back(defectMethod);

    defaultPart.currentMethodId = "counting";

    m_partProfiles.push_back(defaultPart);
}

PartProfile* AppConfig::getPartProfile(const QString& partId)
{
    for (auto& profile : m_partProfiles) {
        if (profile.partId == partId) {
            return &profile;
        }
    }
    return nullptr;
}

const PartProfile* AppConfig::getPartProfile(const QString& partId) const
{
    for (const auto& profile : m_partProfiles) {
        if (profile.partId == partId) {
            return &profile;
        }
    }
    return nullptr;
}

DetectionMethodConfig* AppConfig::getDetectionMethod(const QString& partId, const QString& methodId)
{
    PartProfile* profile = getPartProfile(partId);
    if (!profile) {
        return nullptr;
    }

    for (auto& method : profile->availableMethods) {
        if (method.methodId == methodId) {
            return &method;
        }
    }
    return nullptr;
}

void AppConfig::setCurrentPartId(const QString& partId)
{
    if (m_currentPartId != partId) {
        m_currentPartId = partId;
        emit partChanged(partId);
    }
}

bool AppConfig::load(const QString& filePath)
{
    QString path = filePath.isEmpty() ? m_configFilePath : filePath;

    QFile file(path);
    if (!file.exists()) {
        qWarning() << "[AppConfig] 配置文件不存在，使用預設配置:" << path;
        return false;
    }

    if (!file.open(QIODevice::ReadOnly)) {
        qWarning() << "[AppConfig] 無法開啟配置文件:" << path;
        return false;
    }

    QJsonDocument doc = QJsonDocument::fromJson(file.readAll());
    file.close();

    if (doc.isNull()) {
        qWarning() << "[AppConfig] 配置文件格式錯誤:" << path;
        return false;
    }

    QJsonObject root = doc.object();

    m_camera = CameraConfig::fromJson(root.value("camera").toObject());
    m_detection = DetectionConfig::fromJson(root.value("detection").toObject());
    m_gate = GateConfig::fromJson(root.value("gate").toObject());
    m_packaging = PackagingConfig::fromJson(root.value("packaging").toObject());
    m_performance = PerformanceConfig::fromJson(root.value("performance").toObject());
    m_debug = DebugConfig::fromJson(root.value("debug").toObject());
    m_ui = UIConfig::fromJson(root.value("ui").toObject());
    m_yolo = YoloConfig::fromJson(root.value("yolo").toObject());

    // 載入零件配置
    QJsonArray partsArray = root.value("partProfiles").toArray();
    if (!partsArray.isEmpty()) {
        m_partProfiles.clear();
        for (const auto& partVal : partsArray) {
            m_partProfiles.push_back(PartProfile::fromJson(partVal.toObject()));
        }
    }

    m_currentPartId = root.value("currentPartId").toString(m_currentPartId);
    m_configFilePath = path;

    qDebug() << "[AppConfig] 配置已從文件載入:" << path;
    emit configChanged();
    return true;
}

bool AppConfig::save(const QString& filePath) const
{
    QString path = filePath.isEmpty() ? m_configFilePath : filePath;

    // 確保目錄存在
    QFileInfo fileInfo(path);
    QDir dir = fileInfo.dir();
    if (!dir.exists()) {
        dir.mkpath(".");
    }

    QJsonArray partsArray;
    for (const auto& profile : m_partProfiles) {
        partsArray.append(profile.toJson());
    }

    QJsonObject root;
    root["camera"] = m_camera.toJson();
    root["detection"] = m_detection.toJson();
    root["gate"] = m_gate.toJson();
    root["packaging"] = m_packaging.toJson();
    root["performance"] = m_performance.toJson();
    root["debug"] = m_debug.toJson();
    root["ui"] = m_ui.toJson();
    root["yolo"] = m_yolo.toJson();
    root["partProfiles"] = partsArray;
    root["currentPartId"] = m_currentPartId;

    QJsonDocument doc(root);

    QFile file(path);
    if (!file.open(QIODevice::WriteOnly)) {
        qWarning() << "[AppConfig] 無法寫入配置文件:" << path;
        return false;
    }

    file.write(doc.toJson(QJsonDocument::Indented));
    file.close();

    qDebug() << "[AppConfig] 配置已保存到:" << path;
    return true;
}

void AppConfig::resetToDefault()
{
    m_camera = CameraConfig();
    m_detection = DetectionConfig();
    m_gate = GateConfig();
    m_packaging = PackagingConfig();
    m_performance = PerformanceConfig();
    m_debug = DebugConfig();
    m_ui = UIConfig();
    m_yolo = YoloConfig();

    m_partProfiles.clear();
    initDefaultPartProfiles();

    m_currentPartId = "default_small_part";

    emit configChanged();
    qDebug() << "[AppConfig] 配置已重置為預設值";
}

} // namespace basler
