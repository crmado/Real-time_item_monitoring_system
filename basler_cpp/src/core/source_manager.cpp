#include "core/source_manager.h"
#include "core/video_player.h"
#include <QDebug>

namespace basler
{

    SourceManager::SourceManager(QObject *parent)
        : QObject(parent)
    {
        qRegisterMetaType<SourceType>("SourceType");

        // 默認創建相機控制器
        m_cameraController = std::make_unique<CameraController>(this);
        setupCameraConnections();

        qDebug() << "[SourceManager] 初始化完成";
    }

    SourceManager::~SourceManager()
    {
        cleanup();
    }

    bool SourceManager::isActive() const
    {
        switch (m_sourceType)
        {
        case SourceType::Camera:
            return m_cameraController && m_cameraController->isGrabbing();
        case SourceType::Video:
            return m_videoPlayer && m_videoPlayer->isPlaying();
        default:
            return false;
        }
    }

    bool SourceManager::isGrabbing() const
    {
        return isActive();
    }

    double SourceManager::fps() const
    {
        switch (m_sourceType)
        {
        case SourceType::Camera:
            return m_cameraController ? m_cameraController->fps() : 0.0;
        case SourceType::Video:
            return m_videoPlayer ? m_videoPlayer->fps() : 0.0;
        default:
            return 0.0;
        }
    }

    void SourceManager::setupCameraConnections()
    {
        if (!m_cameraController)
            return;

        // 連接狀態信號（明確使用 Qt::QueuedConnection 確保線程安全）
        connect(m_cameraController.get(), &CameraController::connected,
                this, &SourceManager::onCameraConnected, Qt::QueuedConnection);
        connect(m_cameraController.get(), &CameraController::disconnected,
                this, &SourceManager::onCameraDisconnected, Qt::QueuedConnection);
        connect(m_cameraController.get(), &CameraController::grabbingStarted,
                this, &SourceManager::onCameraGrabbingStarted, Qt::QueuedConnection);
        connect(m_cameraController.get(), &CameraController::grabbingStopped,
                this, &SourceManager::onCameraGrabbingStopped, Qt::QueuedConnection);

        // 連接幀和 FPS 信號（跨線程，必須使用 Qt::QueuedConnection）
        connect(m_cameraController.get(), &CameraController::frameReady,
                this, &SourceManager::onCameraFrameReady, Qt::QueuedConnection);
        connect(m_cameraController.get(), &CameraController::fpsUpdated,
                this, &SourceManager::onCameraFpsUpdated, Qt::QueuedConnection);

        // 連接錯誤信號
        connect(m_cameraController.get(), &CameraController::connectionError,
                this, &SourceManager::onCameraError, Qt::QueuedConnection);
        connect(m_cameraController.get(), &CameraController::grabError,
                this, &SourceManager::onCameraError, Qt::QueuedConnection);
    }

    void SourceManager::setupVideoConnections()
    {
        if (!m_videoPlayer)
            return;

        connect(m_videoPlayer.get(), &VideoPlayer::frameReady,
                this, &SourceManager::onVideoFrameReady);
        connect(m_videoPlayer.get(), &VideoPlayer::playbackFinished,
                this, &SourceManager::onVideoPlaybackFinished);
    }

    CameraController *SourceManager::useCamera()
    {
        if (m_sourceType == SourceType::Camera && m_cameraController)
        {
            return m_cameraController.get();
        }

        // 清理視頻播放器
        if (m_videoPlayer)
        {
            m_videoPlayer->release();
            m_videoPlayer.reset();
        }

        // 如果相機控制器不存在，創建新的
        if (!m_cameraController)
        {
            m_cameraController = std::make_unique<CameraController>(this);
            setupCameraConnections();
        }

        m_sourceType = SourceType::Camera;
        emit sourceTypeChanged(m_sourceType);

        qDebug() << "[SourceManager] 切換到相機模式";
        return m_cameraController.get();
    }

    bool SourceManager::useVideo(const QString &videoPath)
    {
        // 停止相機抓取
        if (m_cameraController && m_cameraController->isGrabbing())
        {
            m_cameraController->stopGrabbing();
        }

        // 創建或重用視頻播放器
        if (!m_videoPlayer)
        {
            m_videoPlayer = std::make_unique<VideoPlayer>(this);
            setupVideoConnections();
        }

        if (m_videoPlayer->loadVideo(videoPath))
        {
            m_sourceType = SourceType::Video;
            emit sourceTypeChanged(m_sourceType);

            qDebug() << "[SourceManager] 切換到視頻模式:" << videoPath;
            return true;
        }
        else
        {
            emit error("無法載入視頻文件");
            return false;
        }
    }

    void SourceManager::connectCamera(int index)
    {
        useCamera();
        if (m_cameraController)
        {
            m_cameraController->connectCamera(index);
        }
    }

    void SourceManager::disconnectCamera()
    {
        if (m_cameraController)
        {
            m_cameraController->disconnectCamera();
        }
    }

    void SourceManager::startGrabbing()
    {
        switch (m_sourceType)
        {
        case SourceType::Camera:
            if (m_cameraController)
            {
                m_cameraController->startGrabbing();
            }
            break;
        case SourceType::Video:
            if (m_videoPlayer)
            {
                m_videoPlayer->startPlaying();
                emit grabbingStarted(); // 通知 UI 視頻播放已開始
            }
            break;
        default:
            qWarning() << "[SourceManager] 無有效的輸入源";
            break;
        }
    }

    void SourceManager::stopGrabbing()
    {
        switch (m_sourceType)
        {
        case SourceType::Camera:
            if (m_cameraController)
            {
                m_cameraController->stopGrabbing();
            }
            break;
        case SourceType::Video:
            if (m_videoPlayer)
            {
                m_videoPlayer->stopPlaying();
            }
            break;
        default:
            break;
        }
    }

    cv::Mat SourceManager::getFrame()
    {
        QMutexLocker locker(&m_frameMutex);
        return m_latestFrame.clone();
    }

    void SourceManager::cleanup()
    {
        cleanupCurrentSource();
        qDebug() << "[SourceManager] 資源已清理";
    }

    void SourceManager::cleanupCurrentSource()
    {
        if (m_cameraController)
        {
            if (m_cameraController->isGrabbing())
            {
                m_cameraController->stopGrabbing();
            }
            if (m_cameraController->isConnected())
            {
                m_cameraController->disconnectCamera();
            }
        }

        if (m_videoPlayer)
        {
            m_videoPlayer->release();
            m_videoPlayer.reset();
        }

        m_sourceType = SourceType::None;
    }

    // ============================================================================
    // 相機信號處理
    // ============================================================================

    void SourceManager::onCameraConnected(const CameraInfo &info)
    {
        m_sourceType = SourceType::Camera;
        emit connected(info);
        emit activeStateChanged(true);
    }

    void SourceManager::onCameraDisconnected()
    {
        emit disconnected();
        emit activeStateChanged(false);
    }

    void SourceManager::onCameraGrabbingStarted()
    {
        emit grabbingStarted();
    }

    void SourceManager::onCameraGrabbingStopped()
    {
        emit grabbingStopped();
    }

    void SourceManager::onCameraFrameReady(const cv::Mat &frame)
    {
        {
            QMutexLocker locker(&m_frameMutex);
            m_latestFrame = frame.clone();
        }
        emit frameReady(frame);
    }

    void SourceManager::onCameraFpsUpdated(double fps)
    {
        emit fpsUpdated(fps);
    }

    void SourceManager::onCameraError(const QString &errorMsg)
    {
        emit error(errorMsg);
    }

    // ============================================================================
    // 視頻信號處理
    // ============================================================================

    void SourceManager::onVideoFrameReady(const cv::Mat &frame)
    {
        {
            QMutexLocker locker(&m_frameMutex);
            m_latestFrame = frame.clone();
        }
        emit frameReady(frame);
    }

    void SourceManager::onVideoPlaybackFinished()
    {
        emit grabbingStopped();
        qDebug() << "[SourceManager] 視頻播放完成";
    }

} // namespace basler
