#include "core/video_recorder.h"
#include <QDebug>
#include <QSize>

namespace basler {

VideoRecorder::VideoRecorder(const QString& outputDir, QObject* parent)
    : QObject(parent)
    , m_outputPath(outputDir)
{
    // 確保輸出目錄存在
    if (!m_outputPath.exists()) {
        m_outputPath.mkpath(".");
    }

    qDebug() << "[VideoRecorder] 初始化完成，輸出目錄:" << m_outputPath.absolutePath();
}

VideoRecorder::~VideoRecorder()
{
    cleanup();
}

double VideoRecorder::recordingDuration() const
{
    if (!m_isRecording.load() || !m_recordingStartTime.isValid()) {
        return 0.0;
    }
    return m_recordingStartTime.msecsTo(QDateTime::currentDateTime()) / 1000.0;
}

void VideoRecorder::setOutputDirectory(const QString& dir)
{
    m_outputPath = QDir(dir);
    if (!m_outputPath.exists()) {
        m_outputPath.mkpath(".");
    }
}

bool VideoRecorder::startRecording(const QSize& frameSize, double fps, const QString& filename)
{
    if (m_isRecording.load()) {
        qWarning() << "[VideoRecorder] 錄製已在進行中";
        return false;
    }

    // 生成文件名
    QString actualFilename = filename;
    if (actualFilename.isEmpty()) {
        QString timestamp = QDateTime::currentDateTime().toString("yyyyMMdd_HHmmss");
        actualFilename = QString("recording_%1").arg(timestamp);
    }
    m_currentFilename = actualFilename;
    m_fps = fps;

    // 嘗試不同的編碼器
    struct CodecInfo {
        QString name;
        int fourcc;
        QString extension;
    };

    std::vector<CodecInfo> codecs = {
        {"mp4v", cv::VideoWriter::fourcc('m', 'p', '4', 'v'), ".mp4"},
        {"MJPG", cv::VideoWriter::fourcc('M', 'J', 'P', 'G'), ".avi"},
        {"XVID", cv::VideoWriter::fourcc('X', 'V', 'I', 'D'), ".avi"}
    };

    for (const auto& codec : codecs) {
        if (tryCodec(codec.name, codec.fourcc, codec.extension, frameSize, fps)) {
            m_isRecording.store(true);
            m_framesRecorded.store(0);
            m_recordingStartTime = QDateTime::currentDateTime();

            emit recordingStarted(m_currentFilename);
            emit recordingStateChanged(true);

            qDebug() << "[VideoRecorder] 開始錄製:" << m_currentFilename;
            return true;
        }
    }

    emit recordingError("所有編碼器都失敗");
    return false;
}

bool VideoRecorder::tryCodec(const QString& codecName, int fourcc, const QString& extension,
                             const QSize& frameSize, double fps)
{
    try {
        QString filepath = m_outputPath.absoluteFilePath(m_currentFilename + extension);

        m_videoWriter = std::make_unique<cv::VideoWriter>(
            filepath.toStdString(),
            fourcc,
            fps,
            cv::Size(frameSize.width(), frameSize.height())
        );

        if (m_videoWriter->isOpened()) {
            m_codecName = codecName;
            m_currentFullPath = filepath;

            qDebug() << "[VideoRecorder] 使用" << codecName << "編碼器";
            qDebug() << "[VideoRecorder] 錄製參數:"
                     << frameSize.width() << "x" << frameSize.height()
                     << "@" << fps << "fps";
            qDebug() << "[VideoRecorder] 錄製文件:" << filepath;

            return true;
        }

        m_videoWriter.reset();
        return false;

    } catch (const std::exception& e) {
        qWarning() << "[VideoRecorder]" << codecName << "編碼器失敗:" << e.what();
        m_videoWriter.reset();
        return false;
    }
}

bool VideoRecorder::writeFrame(const cv::Mat& frame)
{
    if (!m_isRecording.load() || !m_videoWriter) {
        return false;
    }

    QMutexLocker locker(&m_writerMutex);

    try {
        m_videoWriter->write(frame);
        int frames = m_framesRecorded.fetch_add(1) + 1;
        emit frameWritten(frames);
        return true;

    } catch (const std::exception& e) {
        qWarning() << "[VideoRecorder] 寫入幀失敗:" << e.what();
        return false;
    }
}

RecordingInfo VideoRecorder::stopRecording()
{
    RecordingInfo info;

    if (!m_isRecording.load()) {
        return info;
    }

    m_isRecording.store(false);

    // 計算錄製時長
    double duration = 0.0;
    if (m_recordingStartTime.isValid()) {
        duration = m_recordingStartTime.msecsTo(QDateTime::currentDateTime()) / 1000.0;
    }

    // 釋放寫入器
    {
        QMutexLocker locker(&m_writerMutex);
        if (m_videoWriter) {
            m_videoWriter->release();
            m_videoWriter.reset();
        }
    }

    // 填充錄製信息
    int frames = m_framesRecorded.load();
    info.filename = m_currentFilename;
    info.fullPath = m_currentFullPath;
    info.framesRecorded = frames;
    info.duration = duration;
    info.averageFps = (duration > 0) ? (frames / duration) : 0.0;
    info.codec = m_codecName;

    emit recordingStopped(info);
    emit recordingStateChanged(false);

    qDebug() << "[VideoRecorder] 錄製完成:" << m_currentFilename;
    qDebug() << "[VideoRecorder] 錄製統計:" << frames << "幀," << duration << "秒";
    qDebug() << "[VideoRecorder] 平均幀率:" << info.averageFps << "fps";

    return info;
}

void VideoRecorder::cleanup()
{
    if (m_isRecording.load()) {
        stopRecording();
    }

    QMutexLocker locker(&m_writerMutex);
    if (m_videoWriter) {
        m_videoWriter->release();
        m_videoWriter.reset();
    }

    qDebug() << "[VideoRecorder] 資源已清理";
}

} // namespace basler
