#ifndef YOLO_DETECTOR_H
#define YOLO_DETECTOR_H

#include <opencv2/core.hpp>
#include <opencv2/dnn.hpp>
#include <string>
#include <vector>
#include <mutex>

namespace basler
{

    // 前向聲明（避免循環依賴）
    struct DetectedObject;

    /**
     * @brief YOLO ONNX 推理引擎
     *
     * 純 C++17 + OpenCV DNN，不依賴 Qt。
     * 支援 ROI 感知推理：ROI 放大 → letterbox → blob → 推理 → NMS → 座標反映射
     *
     * 線程安全：所有公開方法透過 std::mutex 保證線程安全
     */
    class YoloDetector
    {
    public:
        YoloDetector();
        ~YoloDetector();

        // 禁止複製
        YoloDetector(const YoloDetector &) = delete;
        YoloDetector &operator=(const YoloDetector &) = delete;

        /**
         * @brief 載入 ONNX 模型
         * @param modelPath ONNX 檔案路徑
         * @return 是否成功載入
         */
        bool loadModel(const std::string &modelPath);

        /**
         * @brief 是否已載入模型
         */
        bool isModelLoaded() const;

        /**
         * @brief 在 ROI 區域執行物件偵測
         * @param roiImage ROI 裁切後的影像
         * @param offsetX ROI 在原圖的 X 偏移
         * @param offsetY ROI 在原圖的 Y 偏移
         * @param results 輸出偵測結果（座標為原圖座標系）
         * @return 推理耗時（毫秒）
         */
        double detect(const cv::Mat &roiImage, int offsetX, int offsetY,
                       std::vector<DetectedObject> &results);

        // 參數設定
        void setConfidenceThreshold(double threshold);
        void setNmsThreshold(double threshold);
        void setRoiUpscaleFactor(double factor);
        void setInputSize(int size);

        double confidenceThreshold() const { return m_confidenceThreshold; }
        double nmsThreshold() const { return m_nmsThreshold; }
        double roiUpscaleFactor() const { return m_roiUpscaleFactor; }
        int inputSize() const { return m_inputSize; }
        double lastInferenceTimeMs() const { return m_lastInferenceTimeMs; }

    private:
        /**
         * @brief Letterbox 前處理：保持長寬比縮放到目標尺寸，灰色填充
         * @param src 輸入影像
         * @param dst 輸出影像（targetSize x targetSize）
         * @param scaleX 輸出：X 軸縮放比
         * @param scaleY 輸出：Y 軸縮放比
         * @param padX 輸出：X 軸填充像素
         * @param padY 輸出：Y 軸填充像素
         */
        void letterbox(const cv::Mat &src, cv::Mat &dst,
                        double &scaleX, double &scaleY,
                        int &padX, int &padY);

        /**
         * @brief 解析 YOLOv8 輸出 tensor，執行 NMS
         * @param output 模型輸出 tensor
         * @param scaleX letterbox 的 X 縮放比
         * @param scaleY letterbox 的 Y 縮放比
         * @param padX letterbox 的 X 填充
         * @param padY letterbox 的 Y 填充
         * @param upscaleRatio ROI 放大比例（用於反映射）
         * @param offsetX ROI 在原圖的 X 偏移
         * @param offsetY ROI 在原圖的 Y 偏移
         * @param results 輸出偵測結果
         */
        void postProcess(const cv::Mat &output,
                          double scaleX, double scaleY,
                          int padX, int padY,
                          double upscaleRatio,
                          int offsetX, int offsetY,
                          std::vector<DetectedObject> &results);

        cv::dnn::Net m_net;
        bool m_modelLoaded = false;

        // 推理參數
        double m_confidenceThreshold = 0.25;
        double m_nmsThreshold = 0.45;
        double m_roiUpscaleFactor = 2.0;
        int m_inputSize = 640;

        // 效能統計
        double m_lastInferenceTimeMs = 0.0;

        mutable std::mutex m_mutex;
    };

} // namespace basler

#endif // YOLO_DETECTOR_H
