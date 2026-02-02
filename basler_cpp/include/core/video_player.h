#ifndef VIDEO_PLAYER_H
#define VIDEO_PLAYER_H

#include <QObject>
#include <QThread>
#include <QMutex>
#include <QString>
#include <atomic>
#include <memory>
#include <opencv2/core.hpp>
#include <opencv2/videoio.hpp>

namespace basler {

/**
 * @brief 視頻播放工作線程
 */
class VideoPlayWorker : public QObject {
    Q_OBJECT

public:
    explicit VideoPlayWorker(cv::VideoCapture* capture, double fps, QObject* parent = nullptr);

public slots:
    void startPlaying(bool loop);
    void stopPlaying();
    void pause();
    void resume();

signals:
    void frameReady(const cv::Mat& frame, int frameIndex);
    void playbackFinished();
    void playError(const QString& error);

private:
    cv::VideoCapture* m_capture;
    double m_fps;
    std::atomic<bool> m_running{false};
    std::atomic<bool> m_paused{false};
};

/**
 * @brief 視頻文件播放器 - 模擬相機輸入
 *
 * 用於測試模式，無需實體相機即可測試檢測算法
 */
class VideoPlayer : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool isPlaying READ isPlaying NOTIFY playingStateChanged)
    Q_PROPERTY(double fps READ fps NOTIFY videoLoaded)
    Q_PROPERTY(int totalFrames READ totalFrames NOTIFY videoLoaded)
    Q_PROPERTY(int currentFrame READ currentFrame NOTIFY frameChanged)

public:
    explicit VideoPlayer(QObject* parent = nullptr);
    ~VideoPlayer();

    // 禁止複製
    VideoPlayer(const VideoPlayer&) = delete;
    VideoPlayer& operator=(const VideoPlayer&) = delete;

    // 狀態查詢
    bool isPlaying() const { return m_isPlaying.load(); }
    bool isPaused() const { return m_isPaused.load(); }
    bool isLoaded() const { return m_capture != nullptr && m_capture->isOpened(); }

    // 視頻信息
    double fps() const { return m_fps; }
    int totalFrames() const { return m_totalFrames; }
    int currentFrame() const { return m_currentFrameIndex.load(); }
    int frameWidth() const { return m_frameWidth; }
    int frameHeight() const { return m_frameHeight; }
    QString videoPath() const { return m_videoPath; }

    // 進度
    double progress() const;

public slots:
    /**
     * @brief 加載視頻文件
     * @param videoPath 視頻文件路徑
     * @return 是否成功
     */
    bool loadVideo(const QString& videoPath);

    /**
     * @brief 開始播放
     * @param loop 是否循環播放
     */
    void startPlaying(bool loop = false);

    /**
     * @brief 停止播放
     */
    void stopPlaying();

    /**
     * @brief 暫停播放
     */
    void pause();

    /**
     * @brief 恢復播放
     */
    void resume();

    /**
     * @brief 跳轉到指定幀
     * @param frameIndex 幀索引
     */
    void seek(int frameIndex);

    /**
     * @brief 下一幀
     */
    void nextFrame();

    /**
     * @brief 上一幀
     */
    void previousFrame();

    /**
     * @brief 釋放資源
     */
    void release();

signals:
    void videoLoaded(const QString& path, int totalFrames, double fps);
    void frameReady(const cv::Mat& frame);
    void frameChanged(int frameIndex);
    void playingStateChanged(bool isPlaying);
    void playbackFinished();
    void loadError(const QString& error);
    void playError(const QString& error);

private slots:
    void onFrameReady(const cv::Mat& frame, int frameIndex);
    void onPlaybackFinished();
    void onPlayError(const QString& error);

private:
    std::unique_ptr<cv::VideoCapture> m_capture;
    std::unique_ptr<QThread> m_playThread;
    std::unique_ptr<VideoPlayWorker> m_playWorker;

    QString m_videoPath;
    double m_fps = 30.0;
    int m_totalFrames = 0;
    int m_frameWidth = 0;
    int m_frameHeight = 0;

    std::atomic<int> m_currentFrameIndex{0};
    std::atomic<bool> m_isPlaying{false};
    std::atomic<bool> m_isPaused{false};

    cv::Mat m_latestFrame;
    QMutex m_frameMutex;
};

} // namespace basler

Q_DECLARE_METATYPE(cv::Mat)

#endif // VIDEO_PLAYER_H
