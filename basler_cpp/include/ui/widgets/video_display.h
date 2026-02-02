#ifndef VIDEO_DISPLAY_H
#define VIDEO_DISPLAY_H

#include <QWidget>
#include <QLabel>
#include <QImage>
#include <QMutex>
#include <opencv2/core.hpp>

namespace basler {

/**
 * @brief 視頻顯示組件
 *
 * 負責將 OpenCV Mat 轉換為 QImage 並顯示
 * 支持縮放和保持長寬比
 */
class VideoDisplayWidget : public QWidget {
    Q_OBJECT

public:
    explicit VideoDisplayWidget(QWidget* parent = nullptr);
    ~VideoDisplayWidget() = default;

    // 顯示模式
    enum class ScaleMode {
        KeepAspectRatio,
        IgnoreAspectRatio,
        KeepAspectRatioByExpanding
    };

    void setScaleMode(ScaleMode mode) { m_scaleMode = mode; }
    ScaleMode scaleMode() const { return m_scaleMode; }

    // 當前顯示的圖像尺寸
    QSize imageSize() const { return m_imageSize; }

public slots:
    /**
     * @brief 更新顯示幀
     * @param frame OpenCV Mat 格式的幀
     */
    void updateFrame(const cv::Mat& frame);

    /**
     * @brief 清除顯示
     */
    void clear();

    /**
     * @brief 顯示消息（無圖像時）
     * @param message 消息文本
     */
    void showMessage(const QString& message);

signals:
    void clicked(const QPoint& pos);  // 點擊事件（圖像座標）

protected:
    void paintEvent(QPaintEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;

private:
    QImage matToQImage(const cv::Mat& mat);
    void updateScaledImage();

    QImage m_currentImage;
    QImage m_scaledImage;
    QString m_message;
    QSize m_imageSize;
    ScaleMode m_scaleMode = ScaleMode::KeepAspectRatio;
    QMutex m_mutex;
};

} // namespace basler

#endif // VIDEO_DISPLAY_H
