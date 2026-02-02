#ifndef SOURCE_MANAGER_H
#define SOURCE_MANAGER_H

#include <QObject>
#include <memory>
#include <opencv2/core.hpp>

namespace basler {

// 前向聲明
class CameraController;
class VideoPlayer;

/**
 * @brief 源類型枚舉
 */
enum class SourceType {
    None,
    Camera,
    Video
};

/**
 * @brief 統一的源管理器
 *
 * 抽象化相機和視頻輸入，提供統一的接口
 * 使得主視窗不需要關心具體的輸入源類型
 */
class SourceManager : public QObject {
    Q_OBJECT
    Q_PROPERTY(SourceType sourceType READ sourceType NOTIFY sourceTypeChanged)
    Q_PROPERTY(bool isActive READ isActive NOTIFY activeStateChanged)

public:
    explicit SourceManager(QObject* parent = nullptr);
    ~SourceManager();

    // 禁止複製
    SourceManager(const SourceManager&) = delete;
    SourceManager& operator=(const SourceManager&) = delete;

    // ===== 狀態查詢 =====
    SourceType sourceType() const { return m_sourceType; }
    bool isActive() const;
    double fps() const;

    // ===== 源訪問 =====
    CameraController* cameraController() const { return m_cameraController.get(); }
    VideoPlayer* videoPlayer() const { return m_videoPlayer.get(); }

public slots:
    /**
     * @brief 切換到相機模式
     * @return 相機控制器指針
     */
    CameraController* useCamera();

    /**
     * @brief 切換到視頻模式
     * @param videoPath 視頻文件路徑
     * @return 是否成功
     */
    bool useVideo(const QString& videoPath);

    /**
     * @brief 獲取當前幀
     * @return 當前幀（可能為空）
     */
    cv::Mat getFrame();

    /**
     * @brief 清理所有資源
     */
    void cleanup();

signals:
    void sourceTypeChanged(SourceType type);
    void activeStateChanged(bool active);
    void frameReady(const cv::Mat& frame);
    void fpsUpdated(double fps);
    void sourceError(const QString& error);

private slots:
    void onCameraFrameReady(const cv::Mat& frame);
    void onVideoFrameReady(const cv::Mat& frame);
    void onCameraFpsUpdated(double fps);

private:
    void cleanupCurrentSource();

    std::unique_ptr<CameraController> m_cameraController;
    std::unique_ptr<VideoPlayer> m_videoPlayer;
    SourceType m_sourceType = SourceType::None;

    cv::Mat m_latestFrame;
    QMutex m_frameMutex;
};

} // namespace basler

Q_DECLARE_METATYPE(basler::SourceType)

#endif // SOURCE_MANAGER_H
