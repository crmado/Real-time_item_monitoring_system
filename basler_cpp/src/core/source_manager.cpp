#include "core/source_manager.h"
#include "core/camera_controller.h"
#include "core/video_player.h"
#include <QDebug>

namespace basler {

SourceManager::SourceManager(QObject* parent)
    : QObject(parent)
{
    qRegisterMetaType<SourceType>("SourceType");
    qDebug() << "[SourceManager] 初始化完成";
}

SourceManager::~SourceManager()
{
    cleanup();
}

bool SourceManager::isActive() const
{
    switch (m_sourceType) {
        case SourceType::Camera:
            return m_cameraController && m_cameraController->isGrabbing();
        case SourceType::Video:
            return m_videoPlayer && m_videoPlayer->isPlaying();
        default:
            return false;
    }
}

double SourceManager::fps() const
{
    switch (m_sourceType) {
        case SourceType::Camera:
            return m_cameraController ? m_cameraController->fps() : 0.0;
        case SourceType::Video:
            return m_videoPlayer ? m_videoPlayer->fps() : 0.0;
        default:
            return 0.0;
    }
}

CameraController* SourceManager::useCamera()
{
    cleanupCurrentSource();

    m_cameraController = std::make_unique<CameraController>(this);

    // 連接信號
    connect(m_cameraController.get(), &CameraController::frameReady,
            this, &SourceManager::onCameraFrameReady);
    connect(m_cameraController.get(), &CameraController::fpsUpdated,
            this, &SourceManager::onCameraFpsUpdated);

    m_sourceType = SourceType::Camera;
    emit sourceTypeChanged(m_sourceType);

    qDebug() << "[SourceManager] 切換到相機模式";
    return m_cameraController.get();
}

bool SourceManager::useVideo(const QString& videoPath)
{
    cleanupCurrentSource();

    m_videoPlayer = std::make_unique<VideoPlayer>(this);

    if (m_videoPlayer->loadVideo(videoPath)) {
        // 連接信號
        connect(m_videoPlayer.get(), &VideoPlayer::frameReady,
                this, &SourceManager::onVideoFrameReady);

        m_sourceType = SourceType::Video;
        emit sourceTypeChanged(m_sourceType);

        qDebug() << "[SourceManager] 切換到視頻模式:" << videoPath;
        return true;
    } else {
        m_videoPlayer.reset();
        m_sourceType = SourceType::None;
        emit sourceError("無法載入視頻文件");
        return false;
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
    if (m_cameraController) {
        m_cameraController->disconnect();
        m_cameraController.reset();
    }

    if (m_videoPlayer) {
        m_videoPlayer->release();
        m_videoPlayer.reset();
    }

    m_sourceType = SourceType::None;
}

void SourceManager::onCameraFrameReady(const cv::Mat& frame)
{
    {
        QMutexLocker locker(&m_frameMutex);
        m_latestFrame = frame.clone();
    }
    emit frameReady(frame);
}

void SourceManager::onVideoFrameReady(const cv::Mat& frame)
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

} // namespace basler
