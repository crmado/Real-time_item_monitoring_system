#ifndef SOURCE_MANAGER_H
#define SOURCE_MANAGER_H

#include <QObject>
#include <QMutex>
#include <memory>
#include <opencv2/core.hpp>

#include "camera_controller.h"

namespace basler {

// 前向聲明
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
    bool isGrabbing() const;
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
     * @brief 載入視頻檔案 (別名)
     */
    bool loadVideo(const QString& videoPath) { return useVideo(videoPath); }

    /**
     * @brief 連接相機
     * @param index 相機索引
     */
    void connectCamera(int index = 0);

    /**
     * @brief 斷開相機
     */
    void disconnectCamera();

    /**
     * @brief 開始抓取（相機或視頻播放）
     */
    void startGrabbing();

    /**
     * @brief 停止抓取
     */
    void stopGrabbing();

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
    // 源類型變更
    void sourceTypeChanged(SourceType type);
    void activeStateChanged(bool active);

    // 統一的連接/抓取信號（轉發自相機或視頻）
    void connected(const CameraInfo& info);
    void disconnected();
    void grabbingStarted();
    void grabbingStopped();

    // 幀和 FPS
    void frameReady(const cv::Mat& frame);
    void fpsUpdated(double fps);

    // 錯誤
    void error(const QString& error);

private slots:
    // 相機信號處理
    void onCameraConnected(const CameraInfo& info);
    void onCameraDisconnected();
    void onCameraGrabbingStarted();
    void onCameraGrabbingStopped();
    void onCameraFrameReady(const cv::Mat& frame);
    void onCameraFpsUpdated(double fps);
    void onCameraError(const QString& error);

    // 視頻信號處理
    void onVideoFrameReady(const cv::Mat& frame);
    void onVideoPlaybackFinished();

private:
    void cleanupCurrentSource();
    void setupCameraConnections();
    void setupVideoConnections();

    std::unique_ptr<CameraController> m_cameraController;
    std::unique_ptr<VideoPlayer> m_videoPlayer;
    SourceType m_sourceType = SourceType::None;

    cv::Mat m_latestFrame;
    QMutex m_frameMutex;
};

} // namespace basler

Q_DECLARE_METATYPE(basler::SourceType)

#endif // SOURCE_MANAGER_H
