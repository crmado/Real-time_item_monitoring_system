#ifndef VIDEO_RECORDER_H
#define VIDEO_RECORDER_H

#include <QObject>
#include <QString>
#include <QDateTime>
#include <QDir>
#include <QMutex>
#include <atomic>
#include <memory>
#include <opencv2/core.hpp>
#include <opencv2/videoio.hpp>

namespace basler {

/**
 * @brief 錄製信息結構
 */
struct RecordingInfo {
    QString filename;
    QString fullPath;
    int framesRecorded = 0;
    double duration = 0.0;
    double averageFps = 0.0;
    QString codec;
};

/**
 * @brief 視頻錄製器
 *
 * 支持多種編碼器自動選擇，線程安全的幀寫入
 */
class VideoRecorder : public QObject {
    Q_OBJECT
    Q_PROPERTY(bool isRecording READ isRecording NOTIFY recordingStateChanged)

public:
    explicit VideoRecorder(const QString& outputDir = "recordings", QObject* parent = nullptr);
    ~VideoRecorder();

    // 禁止複製
    VideoRecorder(const VideoRecorder&) = delete;
    VideoRecorder& operator=(const VideoRecorder&) = delete;

    // 狀態查詢
    bool isRecording() const { return m_isRecording.load(); }
    int framesRecorded() const { return m_framesRecorded.load(); }
    double recordingDuration() const;

    // 輸出目錄
    QString outputDirectory() const { return m_outputPath.path(); }
    void setOutputDirectory(const QString& dir);

public slots:
    /**
     * @brief 開始錄製
     * @param frameSize 幀尺寸 (width, height)
     * @param fps 錄製幀率
     * @param filename 自定義文件名（不含副檔名）
     * @return 是否成功開始錄製
     */
    bool startRecording(const QSize& frameSize, double fps = 30.0, const QString& filename = QString());

    /**
     * @brief 寫入一幀
     * @param frame 要寫入的幀
     * @return 是否成功寫入
     */
    bool writeFrame(const cv::Mat& frame);

    /**
     * @brief 停止錄製
     * @return 錄製信息
     */
    RecordingInfo stopRecording();

    /**
     * @brief 清理資源
     */
    void cleanup();

signals:
    void recordingStarted(const QString& filename);
    void recordingStopped(const RecordingInfo& info);
    void recordingStateChanged(bool isRecording);
    void recordingError(const QString& error);
    void frameWritten(int totalFrames);

private:
    bool tryCodec(const QString& codecName, int fourcc, const QString& extension,
                  const QSize& frameSize, double fps);

    std::unique_ptr<cv::VideoWriter> m_videoWriter;
    QDir m_outputPath;

    std::atomic<bool> m_isRecording{false};
    std::atomic<int> m_framesRecorded{0};

    QString m_currentFilename;
    QString m_currentFullPath;
    QString m_codecName;
    double m_fps = 30.0;
    QDateTime m_recordingStartTime;

    QMutex m_writerMutex;
};

} // namespace basler

#endif // VIDEO_RECORDER_H
