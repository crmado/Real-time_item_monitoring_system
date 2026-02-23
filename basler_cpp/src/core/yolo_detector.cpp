#include "core/yolo_detector.h"
#include "core/detection_controller.h" // for DetectedObject
#include <opencv2/imgproc.hpp>
#include <chrono>
#include <iostream>

namespace basler
{

    YoloDetector::YoloDetector()
    {
    }

    YoloDetector::~YoloDetector()
    {
    }

    bool YoloDetector::loadModel(const std::string &modelPath)
    {
        std::lock_guard<std::mutex> lock(m_mutex);

        try
        {
            m_net = cv::dnn::readNetFromONNX(modelPath);

            // 優先使用 CUDA，fallback 到 CPU
            try
            {
                m_net.setPreferableBackend(cv::dnn::DNN_BACKEND_CUDA);
                m_net.setPreferableTarget(cv::dnn::DNN_TARGET_CUDA);
                std::cout << "[YoloDetector] 使用 CUDA 加速" << std::endl;
            }
            catch (...)
            {
                m_net.setPreferableBackend(cv::dnn::DNN_BACKEND_OPENCV);
                m_net.setPreferableTarget(cv::dnn::DNN_TARGET_CPU);
                std::cout << "[YoloDetector] CUDA 不可用，使用 CPU" << std::endl;
            }

            m_modelLoaded = true;
            std::cout << "[YoloDetector] 模型載入成功: " << modelPath << std::endl;
            return true;
        }
        catch (const cv::Exception &e)
        {
            std::cerr << "[YoloDetector] 模型載入失敗: " << e.what() << std::endl;
            m_modelLoaded = false;
            return false;
        }
    }

    bool YoloDetector::isModelLoaded() const
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_modelLoaded;
    }

    double YoloDetector::detect(const cv::Mat &roiImage, int offsetX, int offsetY,
                                 std::vector<DetectedObject> &results)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        results.clear();

        if (!m_modelLoaded || roiImage.empty())
        {
            return 0.0;
        }

        auto startTime = std::chrono::high_resolution_clock::now();

        // 1. ROI 放大（小零件增強）
        cv::Mat upscaled;
        if (m_roiUpscaleFactor > 1.0)
        {
            cv::resize(roiImage, upscaled, cv::Size(),
                        m_roiUpscaleFactor, m_roiUpscaleFactor,
                        cv::INTER_LINEAR);
        }
        else
        {
            upscaled = roiImage;
        }

        // 2. Letterbox 到模型輸入尺寸
        cv::Mat letterboxed;
        double scaleX, scaleY;
        int padX, padY;
        letterbox(upscaled, letterboxed, scaleX, scaleY, padX, padY);

        // 3. 建立 blob（BGR → RGB, 0~1 正規化）
        cv::Mat blob = cv::dnn::blobFromImage(
            letterboxed, 1.0 / 255.0,
            cv::Size(m_inputSize, m_inputSize),
            cv::Scalar(0, 0, 0), true, false);

        // 4. 推理
        m_net.setInput(blob);
        std::vector<cv::Mat> outputs;
        m_net.forward(outputs, m_net.getUnconnectedOutLayersNames());

        // 5. 後處理（NMS + 座標反映射）
        if (!outputs.empty())
        {
            postProcess(outputs[0], scaleX, scaleY, padX, padY,
                         m_roiUpscaleFactor, offsetX, offsetY, results);
        }

        auto endTime = std::chrono::high_resolution_clock::now();
        m_lastInferenceTimeMs = std::chrono::duration<double, std::milli>(endTime - startTime).count();

        return m_lastInferenceTimeMs;
    }

    void YoloDetector::letterbox(const cv::Mat &src, cv::Mat &dst,
                                  double &scaleX, double &scaleY,
                                  int &padX, int &padY)
    {
        int srcW = src.cols;
        int srcH = src.rows;
        int targetSize = m_inputSize;

        // 計算等比縮放比例
        double ratio = std::min(
            static_cast<double>(targetSize) / srcW,
            static_cast<double>(targetSize) / srcH);

        int newW = static_cast<int>(srcW * ratio);
        int newH = static_cast<int>(srcH * ratio);

        // 縮放
        cv::Mat resized;
        cv::resize(src, resized, cv::Size(newW, newH), 0, 0, cv::INTER_LINEAR);

        // 計算填充量
        padX = (targetSize - newW) / 2;
        padY = (targetSize - newH) / 2;

        // 灰色填充
        dst = cv::Mat(targetSize, targetSize, src.type(), cv::Scalar(114, 114, 114));
        resized.copyTo(dst(cv::Rect(padX, padY, newW, newH)));

        // 輸出縮放比（用於反映射）
        scaleX = ratio;
        scaleY = ratio;
    }

    void YoloDetector::postProcess(const cv::Mat &output,
                                    double scaleX, double scaleY,
                                    int padX, int padY,
                                    double upscaleRatio,
                                    int offsetX, int offsetY,
                                    std::vector<DetectedObject> &results)
    {
        // YOLOv8 輸出格式: [1, (4+numClasses), numDetections]
        // 對於單類別: [1, 5, N]，需要 transpose 為 [N, 5]
        // 每行: [cx, cy, w, h, confidence]

        // 取得輸出維度
        int rows = output.size[1]; // 5 (4+1 for single class)
        int cols = output.size[2]; // N detections

        // 如果 rows < cols，表示需要 transpose（YOLOv8 格式）
        cv::Mat detections;
        if (rows < cols)
        {
            // [1, 5, N] → reshape 為 [5, N] → transpose 為 [N, 5]
            cv::Mat reshaped = output.reshape(1, rows);
            cv::transpose(reshaped, detections);
        }
        else
        {
            detections = output.reshape(1, rows);
        }

        int numDetections = detections.rows;
        int numFields = detections.cols; // 4 + numClasses

        std::vector<cv::Rect> boxes;
        std::vector<float> confidences;
        std::vector<int> classIds;

        for (int i = 0; i < numDetections; i++)
        {
            const float *row = detections.ptr<float>(i);

            // 前 4 個值是 bbox: cx, cy, w, h
            float cx = row[0];
            float cy = row[1];
            float bw = row[2];
            float bh = row[3];

            // 從第 5 個值開始是各類別的信心分數
            // 找最高信心的類別
            float maxConf = 0.0f;
            int maxClassId = 0;
            for (int j = 4; j < numFields; j++)
            {
                if (row[j] > maxConf)
                {
                    maxConf = row[j];
                    maxClassId = j - 4;
                }
            }

            if (maxConf < m_confidenceThreshold)
            {
                continue;
            }

            // 座標反映射：letterbox → upscaled image
            float x1 = (cx - bw / 2.0f - padX) / static_cast<float>(scaleX);
            float y1 = (cy - bh / 2.0f - padY) / static_cast<float>(scaleY);
            float x2 = (cx + bw / 2.0f - padX) / static_cast<float>(scaleX);
            float y2 = (cy + bh / 2.0f - padY) / static_cast<float>(scaleY);

            // 反映射：upscaled → 原始 ROI
            x1 /= static_cast<float>(upscaleRatio);
            y1 /= static_cast<float>(upscaleRatio);
            x2 /= static_cast<float>(upscaleRatio);
            y2 /= static_cast<float>(upscaleRatio);

            int bx = static_cast<int>(x1);
            int by = static_cast<int>(y1);
            int boxW = static_cast<int>(x2 - x1);
            int boxH = static_cast<int>(y2 - y1);

            if (boxW > 0 && boxH > 0)
            {
                boxes.push_back(cv::Rect(bx, by, boxW, boxH));
                confidences.push_back(maxConf);
                classIds.push_back(maxClassId);
            }
        }

        // NMS 去除重疊框
        std::vector<int> nmsIndices;
        cv::dnn::NMSBoxes(boxes, confidences, static_cast<float>(m_confidenceThreshold),
                           static_cast<float>(m_nmsThreshold), nmsIndices);

        for (int idx : nmsIndices)
        {
            const auto &box = boxes[idx];

            DetectedObject obj;
            // 加上 ROI 偏移轉換到原圖座標
            obj.x = box.x + offsetX;
            obj.y = box.y + offsetY;
            obj.w = box.width;
            obj.h = box.height;
            obj.cx = obj.x + obj.w / 2;
            obj.cy = obj.y + obj.h / 2;
            obj.area = obj.w * obj.h;

            results.push_back(obj);
        }
    }

    // 參數設定
    void YoloDetector::setConfidenceThreshold(double threshold)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_confidenceThreshold = threshold;
    }

    void YoloDetector::setNmsThreshold(double threshold)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_nmsThreshold = threshold;
    }

    void YoloDetector::setRoiUpscaleFactor(double factor)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_roiUpscaleFactor = factor;
    }

    void YoloDetector::setInputSize(int size)
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_inputSize = size;
    }

} // namespace basler
