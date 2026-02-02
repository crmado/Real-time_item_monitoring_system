#include "core/detection_controller.h"
#include "config/settings.h"
#include <QDebug>
#include <opencv2/imgproc.hpp>
#include <cmath>

namespace basler {

DetectionController::DetectionController(QObject* parent)
    : QObject(parent)
{
    // 從配置載入參數
    const auto& config = getConfig();
    const auto& det = config.detection();
    const auto& gate = config.gate();
    const auto& pkg = config.packaging();

    // 檢測參數
    m_minArea = det.minArea;
    m_maxArea = det.maxArea;
    m_minAspectRatio = det.minAspectRatio;
    m_maxAspectRatio = det.maxAspectRatio;
    m_minExtent = det.minExtent;
    m_bgHistory = det.bgHistory;
    m_bgVarThreshold = det.bgVarThreshold;
    m_detectShadows = det.detectShadows;
    m_bgLearningRate = det.bgLearningRate;
    m_connectivity = det.connectivity;

    // ROI 參數
    m_roiEnabled = det.roiEnabled;
    m_roiHeight = det.roiHeight;
    m_roiPositionRatio = det.roiPositionRatio;

    // 高速模式參數
    m_ultraHighSpeedMode = det.ultraHighSpeedMode;
    m_targetFps = det.targetFps;
    m_highSpeedBgHistory = det.highSpeedBgHistory;
    m_highSpeedBgVarThreshold = det.highSpeedBgVarThreshold;
    m_highSpeedMinArea = det.highSpeedMinArea;
    m_highSpeedMaxArea = det.highSpeedMaxArea;

    // 虛擬光柵參數
    m_enableGateCounting = gate.enableGateCounting;
    m_gateLinePositionRatio = gate.gateLinePositionRatio;
    m_gateTriggerRadius = gate.gateTriggerRadius;
    m_gateHistoryFrames = gate.gateHistoryFrames;

    // 包裝控制參數
    m_targetCount = pkg.targetCount;
    m_advanceStopCount = pkg.advanceStopCount;
    m_speedFullThreshold = pkg.speedFullThreshold;
    m_speedMediumThreshold = pkg.speedMediumThreshold;
    m_speedSlowThreshold = pkg.speedSlowThreshold;

    // 初始化背景減除器
    resetBackgroundSubtractor();

    qDebug() << "[DetectionController] 初始化完成 - 虛擬光柵計數法";
    qDebug() << "[DetectionController] 配置: minArea=" << m_minArea
             << ", maxArea=" << m_maxArea
             << ", bgVarThreshold=" << m_bgVarThreshold;
}

DetectionController::~DetectionController()
{
    // 清理資源
}

void DetectionController::resetBackgroundSubtractor()
{
    int history = m_ultraHighSpeedMode ? m_highSpeedBgHistory : m_bgHistory;
    int varThreshold = m_ultraHighSpeedMode ? m_highSpeedBgVarThreshold : m_bgVarThreshold;

    m_bgSubtractor = cv::createBackgroundSubtractorMOG2(
        history, varThreshold, m_detectShadows
    );
    m_currentLearningRate = m_bgLearningRate;

    qDebug() << "[DetectionController] 背景減除器已重置: history=" << history
             << ", varThreshold=" << varThreshold;
}

cv::Mat DetectionController::processFrame(const cv::Mat& frame, std::vector<DetectedObject>& detectedObjects)
{
    detectedObjects.clear();

    if (frame.empty() || !m_enabled) {
        return frame;
    }

    QMutexLocker locker(&m_mutex);

    try {
        m_totalProcessedFrames++;
        m_frameHeight = frame.rows;
        m_frameWidth = frame.cols;

        // ROI 區域提取
        cv::Mat processRegion;
        if (m_roiEnabled) {
            m_currentRoiY = static_cast<int>(m_frameHeight * m_roiPositionRatio);
            m_currentRoiHeight = std::min(m_roiHeight, m_frameHeight - m_currentRoiY);
            processRegion = frame(cv::Rect(0, m_currentRoiY, m_frameWidth, m_currentRoiHeight));
        } else {
            processRegion = frame;
            m_currentRoiY = 0;
            m_currentRoiHeight = m_frameHeight;
        }

        // 執行檢測處理
        cv::Mat processed;
        if (m_ultraHighSpeedMode) {
            processed = ultraHighSpeedProcessing(processRegion);
        } else {
            processed = standardProcessing(processRegion);
        }

        // 檢測物件
        detectedObjects = detectObjects(processed);

        // 診斷報告（每 500 幀）
        if (m_totalProcessedFrames % 500 == 0) {
            qDebug() << "========================================";
            qDebug() << "[DetectionController] 診斷報告 - 幀" << m_totalProcessedFrames;
            qDebug() << "檢測物件數:" << detectedObjects.size()
                     << ", 光柵線Y=" << m_gateLineY
                     << ", 計數:" << m_crossingCounter;
            qDebug() << "========================================";
        }

        // 虛擬光柵計數
        if (m_enableGateCounting && !detectedObjects.empty()) {
            virtualGateCounting(detectedObjects);
        }

        // 繪製結果
        cv::Mat resultFrame = drawDetectionResults(frame.clone(), detectedObjects);

        return resultFrame;

    } catch (const std::exception& e) {
        qWarning() << "[DetectionController] 檢測失敗:" << e.what();
        return frame;
    }
}

cv::Mat DetectionController::standardProcessing(const cv::Mat& processRegion)
{
    // 1. 背景減除獲得前景遮罩
    cv::Mat fgMask;
    m_bgSubtractor->apply(processRegion, fgMask, m_currentLearningRate);

    // 2. 高斯模糊減少噪聲
    cv::Mat blurred;
    cv::GaussianBlur(processRegion, blurred, cv::Size(1, 1), 0);

    // 3. 增強前景遮罩濾波
    cv::Mat fgMedian;
    cv::medianBlur(fgMask, fgMedian, 5);

    // 形態學開運算去除獨立噪點
    cv::Mat enhancedKernel = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(5, 5));
    cv::Mat fgStep1;
    cv::morphologyEx(fgMedian, fgStep1, cv::MORPH_OPEN, enhancedKernel, cv::Point(-1, -1), 1);

    // 閉運算填補物件內部空洞
    cv::Mat closeKernel = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(7, 7));
    cv::Mat fgStep2;
    cv::morphologyEx(fgStep1, fgStep2, cv::MORPH_CLOSE, closeKernel, cv::Point(-1, -1), 1);

    // 最終微調開運算
    cv::Mat finalKernel = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(3, 3));
    cv::Mat fgCleaned;
    cv::morphologyEx(fgStep2, fgCleaned, cv::MORPH_OPEN, finalKernel, cv::Point(-1, -1), 1);

    // 4. Canny 邊緣檢測
    cv::Mat sensitiveEdges;
    cv::Canny(blurred, sensitiveEdges, 1, 4);

    // 5. 自適應閾值檢測
    cv::Mat grayRoi;
    if (processRegion.channels() == 3) {
        cv::cvtColor(processRegion, grayRoi, cv::COLOR_BGR2GRAY);
    } else {
        grayRoi = processRegion;
    }
    cv::Mat adaptiveThresh;
    cv::adaptiveThreshold(grayRoi, adaptiveThresh, 255,
                          cv::ADAPTIVE_THRESH_GAUSSIAN_C, cv::THRESH_BINARY, 11, 2);

    // 6. 邊緣增強
    cv::Mat edgeEnhanced;
    cv::bitwise_and(sensitiveEdges, sensitiveEdges, edgeEnhanced, fgCleaned);
    cv::Mat edgeThresh;
    cv::threshold(edgeEnhanced, edgeThresh, 1, 255, cv::THRESH_BINARY);

    cv::Mat adaptiveEnhanced;
    cv::bitwise_and(adaptiveThresh, adaptiveThresh, adaptiveEnhanced, fgCleaned);
    cv::Mat adaptiveThreshClean;
    cv::threshold(adaptiveEnhanced, adaptiveThreshClean, 127, 255, cv::THRESH_BINARY);

    // 7. 三重聯合檢測
    cv::Mat tempCombined;
    cv::bitwise_or(fgCleaned, edgeThresh, tempCombined);
    cv::Mat combined;
    cv::bitwise_or(tempCombined, adaptiveThreshClean, combined);

    return combined;
}

cv::Mat DetectionController::ultraHighSpeedProcessing(const cv::Mat& processRegion)
{
    cv::Mat fgMask;
    m_bgSubtractor->apply(processRegion, fgMask, m_currentLearningRate);

    cv::Mat kernel = cv::Mat::ones(3, 3, CV_8U);
    cv::Mat processed;
    cv::morphologyEx(fgMask, processed, cv::MORPH_OPEN, kernel, cv::Point(-1, -1), 1);
    cv::dilate(processed, processed, kernel, cv::Point(-1, -1), 1);

    return processed;
}

std::vector<DetectedObject> DetectionController::detectObjects(const cv::Mat& processed)
{
    std::vector<DetectedObject> objects;

    if (processed.empty()) {
        return objects;
    }

    // 連通組件分析
    cv::Mat labels, stats, centroids;
    int numLabels = cv::connectedComponentsWithStats(
        processed, labels, stats, centroids, m_connectivity
    );

    int minArea = m_ultraHighSpeedMode ? m_highSpeedMinArea : m_minArea;
    int maxArea = m_ultraHighSpeedMode ? m_highSpeedMaxArea : m_maxArea;

    for (int i = 1; i < numLabels; ++i) {  // 跳過背景 (label 0)
        int area = stats.at<int>(i, cv::CC_STAT_AREA);

        // 面積過濾
        if (area < minArea || area > maxArea) {
            continue;
        }

        int x = stats.at<int>(i, cv::CC_STAT_LEFT);
        int y = stats.at<int>(i, cv::CC_STAT_TOP) + m_currentRoiY;
        int w = stats.at<int>(i, cv::CC_STAT_WIDTH);
        int h = stats.at<int>(i, cv::CC_STAT_HEIGHT);

        int cx = static_cast<int>(centroids.at<double>(i, 0));
        int cy = static_cast<int>(centroids.at<double>(i, 1)) + m_currentRoiY;

        // 形狀驗證
        if (!validateShape(w, h, area)) {
            continue;
        }

        DetectedObject obj;
        obj.x = x;
        obj.y = y;
        obj.w = w;
        obj.h = h;
        obj.cx = cx;
        obj.cy = cy;
        obj.area = area;

        objects.push_back(obj);
    }

    return objects;
}

bool DetectionController::validateShape(int width, int height, int area)
{
    if (width <= 0 || height <= 0) {
        return false;
    }

    // 長寬比
    double aspectRatio = (width > height)
        ? static_cast<double>(height) / width
        : static_cast<double>(width) / height;

    if (aspectRatio < m_minAspectRatio || aspectRatio > m_maxAspectRatio) {
        return false;
    }

    // 填充度
    double extent = static_cast<double>(area) / (width * height);
    if (extent < m_minExtent) {
        return false;
    }

    return true;
}

void DetectionController::virtualGateCounting(const std::vector<DetectedObject>& objects)
{
    m_currentFrameCount++;

    // 計算光柵線位置
    if (m_roiEnabled) {
        m_gateLineY = m_currentRoiY + static_cast<int>(m_roiHeight * m_gateLinePositionRatio);
    } else {
        m_gateLineY = static_cast<int>(m_frameHeight * 0.5);
    }

    // 清理過期的觸發記錄
    std::vector<std::pair<int, int>> expiredPositions;
    for (const auto& [pos, frameNum] : m_triggeredPositions) {
        if (m_currentFrameCount - frameNum > m_gateHistoryFrames) {
            expiredPositions.push_back(pos);
        }
    }
    for (const auto& pos : expiredPositions) {
        m_triggeredPositions.erase(pos);
    }

    // 遍歷當前幀的所有檢測物件
    for (const auto& obj : objects) {
        int cx = obj.cx;
        int cy = obj.cy;

        // 檢查物件中心是否穿越光柵線
        if (cy >= m_gateLineY) {
            // 檢查是否為重複觸發
            if (!checkGateTriggerDuplicate(cx, cy)) {
                // 新物件穿越光柵線
                m_crossingCounter++;
                m_triggeredPositions[{cx, cy}] = m_currentFrameCount;

                qDebug() << "[DetectionController] 光柵計數 #" << m_crossingCounter
                         << " - 位置:(" << cx << "," << cy << ")"
                         << ", 幀:" << m_currentFrameCount;

                emit countChanged(m_crossingCounter);
                emit objectsCrossedGate(m_crossingCounter);

                // 自動包裝模式：更新震動機速度
                if (m_packagingEnabled) {
                    updateVibratorSpeed();
                }
            }
        }
    }
}

bool DetectionController::checkGateTriggerDuplicate(int cx, int cy)
{
    for (const auto& [pos, frameNum] : m_triggeredPositions) {
        double distance = std::sqrt(
            std::pow(cx - pos.first, 2) + std::pow(cy - pos.second, 2)
        );

        if (distance < m_gateTriggerRadius) {
            return true;  // 重複觸發
        }
    }
    return false;
}

cv::Mat DetectionController::drawDetectionResults(cv::Mat frame, const std::vector<DetectedObject>& objects)
{
    // 繪製 ROI 區域
    if (m_roiEnabled) {
        cv::rectangle(frame,
                      cv::Point(0, m_currentRoiY),
                      cv::Point(m_frameWidth, m_currentRoiY + m_currentRoiHeight),
                      cv::Scalar(255, 255, 0), 2);
    }

    // 繪製虛擬光柵線
    if (m_enableGateCounting && m_gateLineY > 0) {
        cv::line(frame,
                 cv::Point(0, m_gateLineY),
                 cv::Point(m_frameWidth, m_gateLineY),
                 cv::Scalar(0, 0, 255), 3);

        std::string gateText = "GATE LINE (Y=" + std::to_string(m_gateLineY) + ")";
        cv::putText(frame, gateText,
                    cv::Point(10, m_gateLineY - 10),
                    cv::FONT_HERSHEY_SIMPLEX, 0.6, cv::Scalar(0, 0, 255), 2);
    }

    // 繪製檢測到的物件
    for (const auto& obj : objects) {
        cv::Scalar boxColor = (obj.cy >= m_gateLineY)
            ? cv::Scalar(0, 255, 255)   // 黃色：已穿越
            : cv::Scalar(0, 255, 0);    // 綠色：未穿越

        cv::rectangle(frame,
                      cv::Point(obj.x, obj.y),
                      cv::Point(obj.x + obj.w, obj.y + obj.h),
                      boxColor, 2);

        cv::circle(frame, cv::Point(obj.cx, obj.cy), 3, cv::Scalar(255, 0, 0), -1);

        cv::putText(frame, std::to_string(obj.area),
                    cv::Point(obj.x, obj.y - 10),
                    cv::FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 255, 255), 1);
    }

    // 顯示統計信息
    std::string infoText = "Detections: " + std::to_string(objects.size()) +
                           " | Counted: " + std::to_string(m_crossingCounter) +
                           " | Gate: Y=" + std::to_string(m_gateLineY);
    cv::putText(frame, infoText,
                cv::Point(10, 30),
                cv::FONT_HERSHEY_SIMPLEX, 0.6, cv::Scalar(0, 255, 255), 2);

    return frame;
}

void DetectionController::updateVibratorSpeed()
{
    if (!m_packagingEnabled) {
        return;
    }

    int currentCount = m_crossingCounter;
    int target = m_targetCount;

    // 檢查是否已完成
    if (currentCount >= target) {
        if (!m_packagingCompleted) {
            m_packagingCompleted = true;
            m_currentSpeed = VibratorSpeed::STOP;
            emit vibratorSpeedChanged(m_currentSpeed);
            emit packagingCompleted();
            qDebug() << "[DetectionController] 包裝完成！" << currentCount << "/" << target;
        }
        return;
    }

    // 計算完成度
    double progress = static_cast<double>(currentCount) / target;
    int effectiveTarget = target - m_advanceStopCount;
    double effectiveProgress = static_cast<double>(currentCount) / effectiveTarget;

    // 根據進度調整速度
    VibratorSpeed newSpeed = m_currentSpeed;

    if (effectiveProgress >= m_speedSlowThreshold) {
        newSpeed = VibratorSpeed::CREEP;
    } else if (effectiveProgress >= m_speedMediumThreshold) {
        newSpeed = VibratorSpeed::SLOW;
    } else if (effectiveProgress >= m_speedFullThreshold) {
        newSpeed = VibratorSpeed::MEDIUM;
    } else {
        newSpeed = VibratorSpeed::FULL;
    }

    if (newSpeed != m_currentSpeed) {
        m_currentSpeed = newSpeed;
        emit vibratorSpeedChanged(m_currentSpeed);
        qDebug() << "[DetectionController] 速度調整:" << static_cast<int>(m_currentSpeed)
                 << "% (" << currentCount << "/" << target << ")";
    }
}

// ===== 公開槽函數 =====

void DetectionController::setEnabled(bool enabled)
{
    if (m_enabled != enabled) {
        m_enabled = enabled;
        if (enabled) {
            resetBackgroundSubtractor();
        }
        emit enabledChanged(enabled);
        qDebug() << "[DetectionController] 檢測" << (enabled ? "已啟用" : "已禁用");
    }
}

void DetectionController::reset()
{
    QMutexLocker locker(&m_mutex);

    m_crossingCounter = 0;
    m_triggeredPositions.clear();
    m_currentFrameCount = 0;
    m_totalProcessedFrames = 0;
    m_gateLineY = 0;
    resetBackgroundSubtractor();

    emit countChanged(0);
    qDebug() << "[DetectionController] 檢測狀態已重置";
}

void DetectionController::setMinArea(int area)
{
    m_minArea = area;
}

void DetectionController::setMaxArea(int area)
{
    m_maxArea = area;
}

void DetectionController::setBgVarThreshold(int threshold)
{
    m_bgVarThreshold = threshold;
    resetBackgroundSubtractor();
}

void DetectionController::setBgLearningRate(double rate)
{
    m_bgLearningRate = rate;
    m_currentLearningRate = rate;
}

void DetectionController::setRoiEnabled(bool enabled)
{
    m_roiEnabled = enabled;
}

void DetectionController::setRoiHeight(int height)
{
    m_roiHeight = height;
}

void DetectionController::setRoiPositionRatio(double ratio)
{
    m_roiPositionRatio = ratio;
}

void DetectionController::setGateTriggerRadius(int radius)
{
    m_gateTriggerRadius = radius;
}

void DetectionController::setGateHistoryFrames(int frames)
{
    m_gateHistoryFrames = frames;
}

void DetectionController::setGateLinePositionRatio(double ratio)
{
    m_gateLinePositionRatio = ratio;
}

void DetectionController::setUltraHighSpeedMode(bool enabled, int targetFps)
{
    m_ultraHighSpeedMode = enabled;
    m_targetFps = targetFps;
    resetBackgroundSubtractor();
}

void DetectionController::enablePackagingMode(bool enabled)
{
    m_packagingEnabled = enabled;
    if (enabled) {
        m_packagingCompleted = false;
    }
}

void DetectionController::setTargetCount(int count)
{
    m_targetCount = count;
    m_packagingCompleted = false;
}

void DetectionController::setSpeedThresholds(double full, double medium, double slow)
{
    m_speedFullThreshold = full;
    m_speedMediumThreshold = medium;
    m_speedSlowThreshold = slow;
}

void DetectionController::resetPackaging()
{
    reset();
    m_packagingCompleted = false;
    m_currentSpeed = VibratorSpeed::STOP;
}

PackagingStatus DetectionController::getPackagingStatus() const
{
    PackagingStatus status;
    status.enabled = m_packagingEnabled;
    status.currentCount = m_crossingCounter;
    status.targetCount = m_targetCount;
    status.progressPercent = (m_targetCount > 0)
        ? (static_cast<double>(m_crossingCounter) / m_targetCount * 100.0)
        : 0.0;
    status.vibratorSpeed = m_currentSpeed;
    status.completed = m_packagingCompleted;
    return status;
}

} // namespace basler
