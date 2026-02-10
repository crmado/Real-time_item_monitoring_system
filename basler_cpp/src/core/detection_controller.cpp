#include "core/detection_controller.h"
#include "config/settings.h"
#include <QDebug>
#include <opencv2/imgproc.hpp>
#include <cmath>
#include <set>
#include <algorithm>

namespace basler
{

    DetectionController::DetectionController(QObject *parent)
        : QObject(parent)
    {
        // 從配置載入參數
        const auto &config = getConfig();
        const auto &det = config.detection();
        const auto &gate = config.gate();
        const auto &pkg = config.packaging();

        // 檢測參數
        m_minArea = det.minArea;
        m_maxArea = det.maxArea;
        m_minAspectRatio = det.minAspectRatio;
        m_maxAspectRatio = det.maxAspectRatio;
        m_minExtent = det.minExtent;
        m_maxSolidity = det.maxSolidity;
        m_bgHistory = det.bgHistory;
        m_bgVarThreshold = det.bgVarThreshold;
        m_detectShadows = det.detectShadows;
        m_bgLearningRate = det.bgLearningRate;
        m_connectivity = det.connectivity;

        // 邊緣檢測參數
        m_gaussianBlurKernelSize = det.gaussianBlurKernelSize;
        m_cannyLowThreshold = det.cannyLowThreshold;
        m_cannyHighThreshold = det.cannyHighThreshold;
        m_binaryThreshold = det.binaryThreshold;

        // 形態學參數
        m_dilateKernelSize = det.dilateKernelSize;
        m_dilateIterations = det.dilateIterations;
        m_closeKernelSize = det.closeKernelSize;
        m_openingKernelSize = det.openingKernelSize;
        m_openingIterations = det.openingIterations;

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
            history, varThreshold, m_detectShadows);
        m_currentLearningRate = m_bgLearningRate;

        qDebug() << "[DetectionController] 背景減除器已重置: history=" << history
                 << ", varThreshold=" << varThreshold;
    }

    cv::Mat DetectionController::processFrame(const cv::Mat &frame, std::vector<DetectedObject> &detectedObjects)
    {
        detectedObjects.clear();

        if (frame.empty() || !m_enabled)
        {
            return frame;
        }

        // 只在讀取配置時短暫鎖定
        bool roiEnabled;
        int roiHeight;
        double roiPositionRatio;
        bool ultraHighSpeedMode;
        bool enableGateCounting;
        {
            QMutexLocker locker(&m_mutex);
            roiEnabled = m_roiEnabled;
            roiHeight = m_roiHeight;
            roiPositionRatio = m_roiPositionRatio;
            ultraHighSpeedMode = m_ultraHighSpeedMode;
            enableGateCounting = m_enableGateCounting;
            m_totalProcessedFrames++;
        }

        try
        {
            int frameHeight = frame.rows;
            int frameWidth = frame.cols;
            int currentRoiY = 0;
            int currentRoiHeight = frameHeight;

            // ROI 區域提取（不需要鎖，使用本地變量）
            cv::Mat processRegion;
            if (roiEnabled)
            {
                currentRoiY = static_cast<int>(frameHeight * roiPositionRatio);
                currentRoiHeight = std::min(roiHeight, frameHeight - currentRoiY);
                if (currentRoiHeight > 0 && currentRoiY < frameHeight)
                {
                    processRegion = frame(cv::Rect(0, currentRoiY, frameWidth, currentRoiHeight));
                }
                else
                {
                    processRegion = frame;
                    currentRoiY = 0;
                    currentRoiHeight = frameHeight;
                }
            }
            else
            {
                processRegion = frame;
            }

            // 更新共享變量
            {
                QMutexLocker locker(&m_mutex);
                m_frameHeight = frameHeight;
                m_frameWidth = frameWidth;
                m_currentRoiY = currentRoiY;
                m_currentRoiHeight = currentRoiHeight;
            }

            // 執行檢測處理（不需要鎖，背景減除器內部線程安全）
            cv::Mat processed;
            if (ultraHighSpeedMode)
            {
                processed = ultraHighSpeedProcessing(processRegion);
            }
            else
            {
                processed = standardProcessing(processRegion);
            }

            // 檢測物件（不需要鎖）
            detectedObjects = detectObjects(processed);

            // 始終計算光柵線位置（無論是否有物件）
            int gateLineY = 0;
            {
                QMutexLocker locker(&m_mutex);
                if (m_roiEnabled)
                {
                    gateLineY = m_currentRoiY + static_cast<int>(m_roiHeight * m_gateLinePositionRatio);
                }
                else
                {
                    gateLineY = static_cast<int>(m_frameHeight * 0.5);
                }
                m_gateLineY = gateLineY;
            }

            // 診斷報告（每 500 幀）
            int totalFrames;
            {
                QMutexLocker locker(&m_mutex);
                totalFrames = m_totalProcessedFrames;
            }
            if (totalFrames % 500 == 0)
            {
                QMutexLocker locker(&m_mutex);
                qDebug() << "========================================";
                qDebug() << "[DetectionController] 診斷報告 - 幀" << totalFrames;
                qDebug() << "檢測物件數:" << detectedObjects.size()
                         << ", 光柵線Y=" << m_gateLineY
                         << ", 計數:" << m_crossingCounter;
                qDebug() << "========================================";
            }

            // 虛擬光柵計數
            if (enableGateCounting && !detectedObjects.empty())
            {
                virtualGateCounting(detectedObjects);
            }

            // 繪製結果
            cv::Mat resultFrame = drawDetectionResults(frame.clone(), detectedObjects);

            return resultFrame;
        }
        catch (const std::exception &e)
        {
            qWarning() << "[DetectionController] 檢測失敗:" << e.what();
            return frame;
        }
    }

    cv::Mat DetectionController::standardProcessing(const cv::Mat &processRegion)
    {
        // 1. 背景減除獲得前景遮罩
        cv::Mat fgMask;
        m_bgSubtractor->apply(processRegion, fgMask, m_currentLearningRate);

        // 2. 高斯模糊減少噪聲（使用配置參數，預設 1x1 等同跳過，保留小零件細節）
        cv::Mat blurred;
        int blurSize = m_gaussianBlurKernelSize | 1; // 確保為奇數
        cv::GaussianBlur(processRegion, blurred, cv::Size(blurSize, blurSize), 0);

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

        // 4. Canny 邊緣檢測 - 使用敏感邊緣（Python: canny_low//2, canny_high//2）
        cv::Mat sensitiveEdges;
        cv::Canny(blurred, sensitiveEdges, m_cannyLowThreshold / 2, m_cannyHighThreshold / 2);

        // 5. 自適應閾值檢測
        cv::Mat grayRoi;
        if (processRegion.channels() == 3)
        {
            cv::cvtColor(processRegion, grayRoi, cv::COLOR_BGR2GRAY);
        }
        else
        {
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

        // 8. 後聯合形態學處理（參考 Python basler_mvc，預設跳過，可由 UI 調整啟用）
        cv::Mat postProcessed = combined;

        // 開運算（如果 kernel > 1 且 iterations > 0）
        if (m_openingKernelSize > 1 && m_openingIterations > 0)
        {
            cv::Mat openKernel = cv::getStructuringElement(
                cv::MORPH_ELLIPSE, cv::Size(m_openingKernelSize, m_openingKernelSize));
            cv::morphologyEx(postProcessed, postProcessed, cv::MORPH_OPEN,
                             openKernel, cv::Point(-1, -1), m_openingIterations);
        }

        // 膨脹（如果 kernel > 1 且 iterations > 0）
        if (m_dilateKernelSize > 1 && m_dilateIterations > 0)
        {
            cv::Mat dilateKernel = cv::Mat::ones(m_dilateKernelSize, m_dilateKernelSize, CV_8U);
            cv::dilate(postProcessed, postProcessed, dilateKernel,
                       cv::Point(-1, -1), m_dilateIterations);
        }

        // 閉合（如果 kernel > 1）
        if (m_closeKernelSize > 1)
        {
            cv::Mat closeK = cv::getStructuringElement(
                cv::MORPH_ELLIPSE, cv::Size(m_closeKernelSize, m_closeKernelSize));
            cv::morphologyEx(postProcessed, postProcessed, cv::MORPH_CLOSE, closeK);
        }

        return postProcessed;
    }

    cv::Mat DetectionController::ultraHighSpeedProcessing(const cv::Mat &processRegion)
    {
        cv::Mat fgMask;
        m_bgSubtractor->apply(processRegion, fgMask, m_currentLearningRate);

        cv::Mat kernel = cv::Mat::ones(3, 3, CV_8U);
        cv::Mat processed;
        cv::morphologyEx(fgMask, processed, cv::MORPH_OPEN, kernel, cv::Point(-1, -1), 1);
        cv::dilate(processed, processed, kernel, cv::Point(-1, -1), 1);

        return processed;
    }

    std::vector<DetectedObject> DetectionController::detectObjects(const cv::Mat &processed)
    {
        std::vector<DetectedObject> objects;

        if (processed.empty())
        {
            return objects;
        }

        // 小零件增強預處理：2x2 微膨脹使極小零件更容易被檢測（參考 Python basler_mvc）
        cv::Mat enhanced = processed;
        if (!m_ultraHighSpeedMode)
        {
            cv::Mat tinyKernel = cv::Mat::ones(2, 2, CV_8U);
            cv::dilate(processed, enhanced, tinyKernel, cv::Point(-1, -1), 1);
        }

        // 連通組件分析
        cv::Mat labels, stats, centroids;
        int numLabels = cv::connectedComponentsWithStats(
            enhanced, labels, stats, centroids, m_connectivity);

        int minArea = m_ultraHighSpeedMode ? m_highSpeedMinArea : m_minArea;
        int maxArea = m_ultraHighSpeedMode ? m_highSpeedMaxArea : m_maxArea;

        for (int i = 1; i < numLabels; ++i)
        { // 跳過背景 (label 0)
            int area = stats.at<int>(i, cv::CC_STAT_AREA);

            // 面積過濾
            if (area < minArea || area > maxArea)
            {
                continue;
            }

            int x = stats.at<int>(i, cv::CC_STAT_LEFT);
            int y = stats.at<int>(i, cv::CC_STAT_TOP) + m_currentRoiY;
            int w = stats.at<int>(i, cv::CC_STAT_WIDTH);
            int h = stats.at<int>(i, cv::CC_STAT_HEIGHT);

            int cx = static_cast<int>(centroids.at<double>(i, 0));
            int cy = static_cast<int>(centroids.at<double>(i, 1)) + m_currentRoiY;

            // 形狀驗證
            if (!validateShape(w, h, area))
            {
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
        if (width <= 0 || height <= 0)
        {
            return false;
        }

        // 長寬比
        double aspectRatio = (width > height)
                                 ? static_cast<double>(height) / width
                                 : static_cast<double>(width) / height;

        if (aspectRatio < m_minAspectRatio || aspectRatio > m_maxAspectRatio)
        {
            return false;
        }

        // 填充度
        double extent = static_cast<double>(area) / (width * height);
        if (extent < m_minExtent)
        {
            return false;
        }

        return true;
    }

    void DetectionController::virtualGateCounting(const std::vector<DetectedObject> &objects)
    {
        m_currentFrameCount++;

        // 更新物件追蹤
        updateObjectTracks(objects);

        // 檢查每個追蹤是否滿足計數條件
        for (auto &[trackId, track] : m_objectTracks)
        {
            // 如果已計數或幀數不足，跳過
            if (track.counted || track.inRoiFrames < m_minTrackFrames)
            {
                continue;
            }

            // 計算 Y 軸移動距離
            int yTravel = track.maxY - track.minY;

            // 檢查是否為重複計數
            if (checkDuplicateCount(track))
            {
                continue;
            }

            // 檢查是否滿足計數條件（寬鬆模式）
            bool validCrossing = (yTravel >= m_minYTravel &&
                                  track.inRoiFrames >= m_minTrackFrames);

            // 額外調試：記錄接近計數但未計數的情況（每 20 幀記錄一次）
            if (m_currentFrameCount % 20 == 0 && yTravel >= 1 && track.inRoiFrames >= 1 && !validCrossing)
            {
                qDebug() << "[Debug] 接近計數 Track" << trackId
                         << ": Y移動=" << yTravel << "px (需要>=" << m_minYTravel << ")"
                         << ", ROI幀數=" << track.inRoiFrames << "(需要>=" << m_minTrackFrames << ")";
            }

            if (validCrossing)
            {
                // 記錄到歷史中防止重複
                m_countedObjectsHistory.push_back({{track.x, track.y}, m_currentFrameCount});

                // 維護歷史長度
                if (m_countedObjectsHistory.size() > static_cast<size_t>(m_historyLength))
                {
                    m_countedObjectsHistory.erase(m_countedObjectsHistory.begin());
                }

                m_crossingCounter++;
                track.counted = true;

                qDebug() << "[DetectionController] ✅ 成功計數 #" << m_crossingCounter
                         << " - Track" << trackId
                         << " (Y移動: " << yTravel << "px)"
                         << ", 幀:" << m_currentFrameCount;

                emit countChanged(m_crossingCounter);
                emit objectsCrossedGate(m_crossingCounter);

                // 自動包裝模式：更新震動機速度
                if (m_packagingEnabled)
                {
                    updateVibratorSpeed();
                }
            }
        }

        // 清理過期的歷史記錄
        m_countedObjectsHistory.erase(
            std::remove_if(m_countedObjectsHistory.begin(), m_countedObjectsHistory.end(),
                           [this](const auto &entry)
                           {
                               return m_currentFrameCount - entry.second > m_historyLength;
                           }),
            m_countedObjectsHistory.end());

        // 診斷報告（每 50 幀）
        if (m_currentFrameCount % 50 == 0)
        {
            qDebug() << "[DetectionController] 追蹤狀態: 總追蹤=" << m_objectTracks.size()
                     << ", 失去追蹤=" << m_lostTracks.size()
                     << ", 計數=" << m_crossingCounter
                     << ", 幀=" << m_currentFrameCount;
        }
    }

    bool DetectionController::checkGateTriggerDuplicate(int cx, int cy)
    {
        for (const auto &[pos, frameNum] : m_triggeredPositions)
        {
            double distance = std::sqrt(
                std::pow(cx - pos.first, 2) + std::pow(cy - pos.second, 2));

            if (distance < m_gateTriggerRadius)
            {
                return true; // 重複觸發
            }
        }
        return false;
    }

    cv::Mat DetectionController::drawDetectionResults(cv::Mat frame, const std::vector<DetectedObject> &objects)
    {
        // 繪製 ROI 區域
        if (m_roiEnabled)
        {
            cv::rectangle(frame,
                          cv::Point(0, m_currentRoiY),
                          cv::Point(m_frameWidth, m_currentRoiY + m_currentRoiHeight),
                          cv::Scalar(255, 255, 0), 2);
        }

        // 繪製虛擬光柵線
        if (m_enableGateCounting && m_gateLineY > 0)
        {
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
        for (const auto &obj : objects)
        {
            cv::Scalar boxColor = (obj.cy >= m_gateLineY)
                                      ? cv::Scalar(0, 255, 255) // 黃色：已穿越
                                      : cv::Scalar(0, 255, 0);  // 綠色：未穿越

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
        if (!m_packagingEnabled)
        {
            return;
        }

        int currentCount = m_crossingCounter;
        int target = m_targetCount;

        // 檢查是否已完成
        if (currentCount >= target)
        {
            if (!m_packagingCompleted)
            {
                m_packagingCompleted = true;
                m_currentSpeed = VibratorSpeed::STOP;
                emit vibratorSpeedChanged(m_currentSpeed);
                emit packagingCompleted();
                qDebug() << "[DetectionController] 包裝完成！" << currentCount << "/" << target;
            }
            return;
        }

        // 計算完成度
        int effectiveTarget = target - m_advanceStopCount;
        double effectiveProgress = static_cast<double>(currentCount) / effectiveTarget;

        // 根據進度調整速度
        VibratorSpeed newSpeed = m_currentSpeed;

        if (effectiveProgress >= m_speedSlowThreshold)
        {
            newSpeed = VibratorSpeed::CREEP;
        }
        else if (effectiveProgress >= m_speedMediumThreshold)
        {
            newSpeed = VibratorSpeed::SLOW;
        }
        else if (effectiveProgress >= m_speedFullThreshold)
        {
            newSpeed = VibratorSpeed::MEDIUM;
        }
        else
        {
            newSpeed = VibratorSpeed::FULL;
        }

        if (newSpeed != m_currentSpeed)
        {
            m_currentSpeed = newSpeed;
            emit vibratorSpeedChanged(m_currentSpeed);
            qDebug() << "[DetectionController] 速度調整:" << static_cast<int>(m_currentSpeed)
                     << "% (" << currentCount << "/" << target << ")";
        }
    }

    // ===== 公開槽函數 =====

    void DetectionController::setEnabled(bool enabled)
    {
        if (m_enabled != enabled)
        {
            m_enabled = enabled;
            if (enabled)
            {
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
        if (enabled)
        {
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

    // ===== 增強型物件追蹤系統實作 - 多特徵匹配 =====

    void DetectionController::updateObjectTracks(const std::vector<DetectedObject> &objects)
    {
        std::map<int, ObjectTrack> newTracks;
        std::set<int> usedTrackIds;
        std::set<int> usedObjectIds;

        // 第一階段：為現有追蹤更新速度和預測
        for (auto &[trackId, track] : m_objectTracks)
        {
            updateTrackVelocity(track);
            track.missedFrames++;
        }

        // 第二階段：使用多特徵匹配尋找最佳配對
        std::vector<std::tuple<int, int, double>> matches; // (trackId, objIdx, score)

        for (size_t objIdx = 0; objIdx < objects.size(); ++objIdx)
        {
            const auto &obj = objects[objIdx];
            double bestScore = 0.0;
            int trackId = findMatchingTrack(obj, bestScore);

            if (trackId != -1 && bestScore >= m_matchThreshold)
            {
                matches.push_back({trackId, static_cast<int>(objIdx), bestScore});
            }
        }

        // 按評分排序，優先處理高分匹配
        std::sort(matches.begin(), matches.end(),
                  [](const auto &a, const auto &b)
                  { return std::get<2>(a) > std::get<2>(b); });

        // 第三階段：應用匹配並更新追蹤
        for (const auto &[trackId, objIdx, score] : matches)
        {
            if (usedTrackIds.find(trackId) != usedTrackIds.end() ||
                usedObjectIds.find(objIdx) != usedObjectIds.end())
            {
                continue; // 已被使用
            }

            const auto &obj = objects[objIdx];
            const auto &oldTrack = m_objectTracks[trackId];

            ObjectTrack updatedTrack = oldTrack;
            updatedTrack.x = obj.cx;
            updatedTrack.y = obj.cy;
            updatedTrack.w = obj.w;
            updatedTrack.h = obj.h;
            updatedTrack.area = obj.area;
            updatedTrack.lastFrame = m_currentFrameCount;
            updatedTrack.positions.push_back({obj.cx, obj.cy});
            updatedTrack.areaHistory.push_back(obj.area);
            updatedTrack.inRoiFrames++;
            updatedTrack.maxY = std::max(updatedTrack.maxY, obj.cy);
            updatedTrack.minY = std::min(updatedTrack.minY, obj.cy);
            updatedTrack.missedFrames = 0;

            // 限制歷史長度
            if (updatedTrack.positions.size() > 10)
            {
                updatedTrack.positions.erase(updatedTrack.positions.begin());
                updatedTrack.areaHistory.erase(updatedTrack.areaHistory.begin());
            }

            newTracks[trackId] = updatedTrack;
            usedTrackIds.insert(trackId);
            usedObjectIds.insert(objIdx);
        }

        // 第四階段：嘗試從失去的追蹤中恢復
        for (size_t objIdx = 0; objIdx < objects.size(); ++objIdx)
        {
            if (usedObjectIds.find(objIdx) != usedObjectIds.end())
            {
                continue;
            }

            const auto &obj = objects[objIdx];
            int recoveredTrackId = -1;
            double bestScore = 0.0;

            for (const auto &[lostId, lostTrack] : m_lostTracks)
            {
                double score = calculateMatchScore(obj, lostTrack);
                if (score > bestScore && score >= m_matchThreshold * 0.5) // 進一步放寬恢復閾值
                {
                    bestScore = score;
                    recoveredTrackId = lostId;
                }
            }

            if (recoveredTrackId != -1)
            {
                ObjectTrack recoveredTrack = m_lostTracks[recoveredTrackId];
                recoveredTrack.x = obj.cx;
                recoveredTrack.y = obj.cy;
                recoveredTrack.w = obj.w;
                recoveredTrack.h = obj.h;
                recoveredTrack.area = obj.area;
                recoveredTrack.lastFrame = m_currentFrameCount;
                recoveredTrack.positions.push_back({obj.cx, obj.cy});
                recoveredTrack.areaHistory.push_back(obj.area);
                recoveredTrack.inRoiFrames++;
                recoveredTrack.maxY = std::max(recoveredTrack.maxY, obj.cy);
                recoveredTrack.minY = std::min(recoveredTrack.minY, obj.cy);
                recoveredTrack.missedFrames = 0;

                newTracks[recoveredTrackId] = recoveredTrack;
                m_lostTracks.erase(recoveredTrackId);
                usedObjectIds.insert(objIdx);
            }
        }

        // 第五階段：為未匹配的物件創建新追蹤
        for (size_t objIdx = 0; objIdx < objects.size(); ++objIdx)
        {
            if (usedObjectIds.find(objIdx) != usedObjectIds.end())
            {
                continue;
            }

            const auto &obj = objects[objIdx];
            ObjectTrack newTrack;
            newTrack.trackId = m_nextTrackId++;
            newTrack.x = obj.cx;
            newTrack.y = obj.cy;
            newTrack.w = obj.w;
            newTrack.h = obj.h;
            newTrack.area = obj.area;
            newTrack.firstFrame = m_currentFrameCount;
            newTrack.lastFrame = m_currentFrameCount;
            newTrack.inRoiFrames = 1;
            newTrack.maxY = obj.cy;
            newTrack.minY = obj.cy;
            newTrack.counted = false;
            newTrack.positions.push_back({obj.cx, obj.cy});
            newTrack.areaHistory.push_back(obj.area);
            newTrack.velocityX = 0;
            newTrack.velocityY = 0;
            newTrack.predictedX = obj.cx;
            newTrack.predictedY = obj.cy;
            newTrack.missedFrames = 0;

            newTracks[newTrack.trackId] = newTrack;
        }

        // 第六階段：將未更新的追蹤移至 lostTracks
        for (const auto &[trackId, track] : m_objectTracks)
        {
            if (newTracks.find(trackId) == newTracks.end())
            {
                if (track.missedFrames < m_maxMissedFrames)
                {
                    m_lostTracks[trackId] = track;
                }
            }
        }

        // 清理過期的 lostTracks
        for (auto it = m_lostTracks.begin(); it != m_lostTracks.end();)
        {
            if (it->second.missedFrames >= m_maxMissedFrames)
            {
                it = m_lostTracks.erase(it);
            }
            else
            {
                ++it;
            }
        }

        // 更新追蹤狀態
        m_objectTracks = newTracks;
    }

    int DetectionController::findMatchingTrack(const DetectedObject &obj, double &outScore)
    {
        int bestTrackId = -1;
        double bestScore = 0.0;

        for (const auto &[trackId, track] : m_objectTracks)
        {
            double score = calculateMatchScore(obj, track);

            if (score > bestScore)
            {
                bestScore = score;
                bestTrackId = trackId;
            }
        }

        outScore = bestScore;
        return bestTrackId;
    }

    double DetectionController::calculateMatchScore(const DetectedObject &obj, const ObjectTrack &track)
    {
        // 純距離匹配模式（帶速度預測 + 當前位置雙重比較）
        double dx = obj.cx - track.predictedX;
        double dy = obj.cy - track.predictedY;
        double distance = std::sqrt(dx * dx + dy * dy);

        // 也計算與當前位置的距離，取較小值
        double dxCur = obj.cx - track.x;
        double dyCur = obj.cy - track.y;
        double distanceCur = std::sqrt(dxCur * dxCur + dyCur * dyCur);
        distance = std::min(distance, distanceCur);

        double maxDistance = std::sqrt(
            static_cast<double>(m_crossingToleranceX * m_crossingToleranceX) +
            static_cast<double>(m_crossingToleranceY * m_crossingToleranceY));
        double distanceScore = std::max(0.0, 1.0 - (distance / maxDistance));

        // 硬性限制：距離太遠直接排除（寬鬆2倍）
        if (std::abs(dxCur) > m_crossingToleranceX * 2.0 ||
            std::abs(dyCur) > m_crossingToleranceY * 2.0)
        {
            return 0.0;
        }

        return distanceScore;
    }

    double DetectionController::calculateIoU(int x1, int y1, int w1, int h1,
                                             int x2, int y2, int w2, int h2)
    {
        // 計算交集區域
        int xLeft = std::max(x1, x2);
        int yTop = std::max(y1, y2);
        int xRight = std::min(x1 + w1, x2 + w2);
        int yBottom = std::min(y1 + h1, y2 + h2);

        if (xRight < xLeft || yBottom < yTop)
        {
            return 0.0; // 無交集
        }

        int intersectionArea = (xRight - xLeft) * (yBottom - yTop);
        int unionArea = w1 * h1 + w2 * h2 - intersectionArea;

        return (unionArea > 0) ? static_cast<double>(intersectionArea) / unionArea : 0.0;
    }

    void DetectionController::updateTrackVelocity(ObjectTrack &track)
    {
        if (track.positions.size() >= 2)
        {
            // 使用最近兩個位置計算速度
            size_t size = track.positions.size();
            auto &recent = track.positions[size - 1];
            auto &previous = track.positions[size - 2];

            track.velocityX = recent.first - previous.first;
            track.velocityY = recent.second - previous.second;

            // 預測下一幀位置
            track.predictedX = recent.first + track.velocityX;
            track.predictedY = recent.second + track.velocityY;
        }
        else
        {
            // 沒有足夠歷史，使用當前位置
            track.predictedX = track.x;
            track.predictedY = track.y;
        }
    }

    bool DetectionController::checkDuplicateCount(const ObjectTrack &track)
    {
        for (const auto &entry : m_countedObjectsHistory)
        {
            const auto &[pos, frame] = entry;
            double distance = std::sqrt(std::pow(track.x - pos.first, 2) +
                                        std::pow(track.y - pos.second, 2));
            int temporalDistance = m_currentFrameCount - frame;

            if (distance < m_duplicateDistanceThreshold &&
                temporalDistance < m_temporalTolerance)
            {
                return true; // 重複計數
            }
        }
        return false;
    }

} // namespace basler
