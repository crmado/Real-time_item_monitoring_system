#include "core/video_player.h"
#include <QDebug>
#include <QFileInfo>
#include <QThread>

namespace basler {

// ============================================================================
// VideoPlayWorker 實現
// ============================================================================

VideoPlayWorker::VideoPlayWorker(cv::VideoCapture* capture, double fps, QObject* parent)
    : QObject(parent)
    , m_capture(capture)
    , m_fps(fps)
{
}

void VideoPlayWorker::startPlaying(bool loop)
{
    if (m_running.load()) {
        return;
    }

    m_running.store(true);
    m_paused.store(false);
    qDebug() << "[VideoPlayWorker] 開始播放";

    int frameIndex = 0;
    int delayMs = static_cast<int>(1000.0 / m_fps);

    while (m_running.load()) {
        // 檢查暫停
        if (m_paused.load()) {
            QThread::msleep(50);
            continue;
        }

        cv::Mat frame;
        bool ret = m_capture->read(frame);

        if (!ret) {
            if (loop) {
                // 循環播放
                m_capture->set(cv::CAP_PROP_POS_FRAMES, 0);
                frameIndex = 0;
                qDebug() << "[VideoPlayWorker] 視頻循環播放";
                continue;
            } else {
                // 播放完畢
                qDebug() << "[VideoPlayWorker] 視頻播放完畢";
                break;
            }
        }

        emit frameReady(frame, frameIndex);
        frameIndex++;

        // 控制播放速度
        QThread::msleep(delayMs);
    }

    m_running.store(false);
    emit playbackFinished();
}

void VideoPlayWorker::stopPlaying()
{
    qDebug() << "[VideoPlayWorker] 收到停止請求";
    m_running.store(false);
}

void VideoPlayWorker::pause()
{
    m_paused.store(true);
}

void VideoPlayWorker::resume()
{
    m_paused.store(false);
}

// ============================================================================
// VideoPlayer 實現
// ============================================================================

VideoPlayer::VideoPlayer(QObject* parent)
    : QObject(parent)
{
    qRegisterMetaType<cv::Mat>("cv::Mat");
    qDebug() << "[VideoPlayer] 初始化完成";
}

VideoPlayer::~VideoPlayer()
{
    release();
}

double VideoPlayer::progress() const
{
    if (m_totalFrames == 0) {
        return 0.0;
    }
    return static_cast<double>(m_currentFrameIndex.load()) / m_totalFrames;
}

bool VideoPlayer::loadVideo(const QString& videoPath)
{
    // 釋放之前的資源
    release();

    QFileInfo fileInfo(videoPath);
    if (!fileInfo.exists()) {
        emit loadError(QString("視頻文件不存在: %1").arg(videoPath));
        return false;
    }

    m_capture = std::make_unique<cv::VideoCapture>(videoPath.toStdString());

    if (!m_capture->isOpened()) {
        emit loadError("無法打開視頻文件");
        m_capture.reset();
        return false;
    }

    // 獲取視頻信息
    m_videoPath = videoPath;
    m_totalFrames = static_cast<int>(m_capture->get(cv::CAP_PROP_FRAME_COUNT));
    m_fps = m_capture->get(cv::CAP_PROP_FPS);
    m_frameWidth = static_cast<int>(m_capture->get(cv::CAP_PROP_FRAME_WIDTH));
    m_frameHeight = static_cast<int>(m_capture->get(cv::CAP_PROP_FRAME_HEIGHT));

    if (m_fps <= 0) {
        m_fps = 30.0;  // 預設值
    }

    qDebug() << "[VideoPlayer] 視頻載入成功:" << fileInfo.fileName();
    qDebug() << "[VideoPlayer] 總幀數:" << m_totalFrames << ", FPS:" << m_fps
             << ", 尺寸:" << m_frameWidth << "x" << m_frameHeight;

    emit videoLoaded(videoPath, m_totalFrames, m_fps);
    return true;
}

void VideoPlayer::startPlaying(bool loop)
{
    if (!m_capture || !m_capture->isOpened()) {
        emit playError("未載入視頻文件");
        return;
    }

    if (m_isPlaying.load()) {
        qDebug() << "[VideoPlayer] 已在播放中";
        return;
    }

    // 創建播放線程
    m_playThread = std::make_unique<QThread>();
    m_playWorker = std::make_unique<VideoPlayWorker>(m_capture.get(), m_fps);
    m_playWorker->moveToThread(m_playThread.get());

    // 連接信號
    connect(m_playThread.get(), &QThread::started, [this, loop]() {
        m_playWorker->startPlaying(loop);
    });
    connect(m_playWorker.get(), &VideoPlayWorker::frameReady,
            this, &VideoPlayer::onFrameReady);
    connect(m_playWorker.get(), &VideoPlayWorker::playbackFinished,
            this, &VideoPlayer::onPlaybackFinished);
    connect(m_playWorker.get(), &VideoPlayWorker::playError,
            this, &VideoPlayer::onPlayError);

    m_isPlaying.store(true);
    m_isPaused.store(false);
    m_currentFrameIndex.store(0);

    m_playThread->start();
    emit playingStateChanged(true);

    qDebug() << "[VideoPlayer] 開始播放";
}

void VideoPlayer::stopPlaying()
{
    if (!m_isPlaying.load()) {
        return;
    }

    if (m_playWorker) {
        m_playWorker->stopPlaying();
    }

    if (m_playThread && m_playThread->isRunning()) {
        m_playThread->quit();
        m_playThread->wait(2000);
    }

    m_isPlaying.store(false);
    m_isPaused.store(false);

    emit playingStateChanged(false);
    qDebug() << "[VideoPlayer] 停止播放";
}

void VideoPlayer::pause()
{
    if (m_playWorker && m_isPlaying.load()) {
        m_playWorker->pause();
        m_isPaused.store(true);
        qDebug() << "[VideoPlayer] 暫停播放";
    }
}

void VideoPlayer::resume()
{
    if (m_playWorker && m_isPaused.load()) {
        m_playWorker->resume();
        m_isPaused.store(false);
        qDebug() << "[VideoPlayer] 恢復播放";
    }
}

void VideoPlayer::seek(int frameIndex)
{
    if (!m_capture || !m_capture->isOpened()) {
        return;
    }

    if (frameIndex >= 0 && frameIndex < m_totalFrames) {
        m_capture->set(cv::CAP_PROP_POS_FRAMES, frameIndex);
        m_currentFrameIndex.store(frameIndex);
        emit frameChanged(frameIndex);
    }
}

void VideoPlayer::nextFrame()
{
    if (!m_capture || !m_capture->isOpened()) {
        return;
    }

    cv::Mat frame;
    if (m_capture->read(frame)) {
        int index = m_currentFrameIndex.fetch_add(1) + 1;
        {
            QMutexLocker locker(&m_frameMutex);
            m_latestFrame = frame.clone();
        }
        emit frameReady(frame);
        emit frameChanged(index);
    }
}

void VideoPlayer::previousFrame()
{
    int currentIndex = m_currentFrameIndex.load();
    if (currentIndex > 0) {
        seek(currentIndex - 1);
        nextFrame();
    }
}

void VideoPlayer::release()
{
    stopPlaying();

    if (m_capture) {
        m_capture->release();
        m_capture.reset();
    }

    m_playWorker.reset();
    m_playThread.reset();

    m_videoPath.clear();
    m_totalFrames = 0;
    m_currentFrameIndex.store(0);

    qDebug() << "[VideoPlayer] 資源已釋放";
}

void VideoPlayer::onFrameReady(const cv::Mat& frame, int frameIndex)
{
    {
        QMutexLocker locker(&m_frameMutex);
        m_latestFrame = frame.clone();
    }
    m_currentFrameIndex.store(frameIndex);

    emit frameReady(frame);
    emit frameChanged(frameIndex);
}

void VideoPlayer::onPlaybackFinished()
{
    m_isPlaying.store(false);
    emit playingStateChanged(false);
    emit playbackFinished();
}

void VideoPlayer::onPlayError(const QString& error)
{
    m_isPlaying.store(false);
    emit playingStateChanged(false);
    emit playError(error);
}

} // namespace basler
