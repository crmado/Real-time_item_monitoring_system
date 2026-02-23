#include "ui/widgets/video_display.h"
#include <QPainter>
#include <QResizeEvent>
#include <QMouseEvent>
#include <opencv2/imgproc.hpp>

namespace basler {

VideoDisplayWidget::VideoDisplayWidget(QWidget* parent)
    : QWidget(parent)
{
    setMinimumSize(320, 240);
    setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);
    setStyleSheet("background-color: #1a1a1a;");

    m_message = tr("等待視頻輸入...");
}

void VideoDisplayWidget::updateFrame(const cv::Mat& frame)
{
    if (frame.empty()) {
        return;
    }

    QMutexLocker locker(&m_mutex);
    m_currentImage = matToQImage(frame);
    m_imageSize = m_currentImage.size();
    m_message.clear();

    updateScaledImage();
    update();  // 觸發重繪
}

void VideoDisplayWidget::clear()
{
    QMutexLocker locker(&m_mutex);
    m_currentImage = QImage();
    m_scaledImage = QImage();
    m_message = tr("等待視頻輸入...");
    update();
}

void VideoDisplayWidget::showMessage(const QString& message)
{
    QMutexLocker locker(&m_mutex);
    m_message = message;
    m_currentImage = QImage();
    m_scaledImage = QImage();
    update();
}

QImage VideoDisplayWidget::matToQImage(const cv::Mat& mat)
{
    if (mat.empty()) {
        return QImage();
    }

    switch (mat.type()) {
        case CV_8UC1: {
            // 灰度圖
            return QImage(mat.data, mat.cols, mat.rows,
                          static_cast<int>(mat.step),
                          QImage::Format_Grayscale8).copy();
        }
        case CV_8UC3: {
            // BGR 轉 RGB
            cv::Mat rgb;
            cv::cvtColor(mat, rgb, cv::COLOR_BGR2RGB);
            return QImage(rgb.data, rgb.cols, rgb.rows,
                          static_cast<int>(rgb.step),
                          QImage::Format_RGB888).copy();
        }
        case CV_8UC4: {
            // BGRA 轉 RGBA
            cv::Mat rgba;
            cv::cvtColor(mat, rgba, cv::COLOR_BGRA2RGBA);
            return QImage(rgba.data, rgba.cols, rgba.rows,
                          static_cast<int>(rgba.step),
                          QImage::Format_RGBA8888).copy();
        }
        default:
            return QImage();
    }
}

void VideoDisplayWidget::updateScaledImage()
{
    if (m_currentImage.isNull()) {
        m_scaledImage = QImage();
        return;
    }

    Qt::AspectRatioMode aspectMode;
    switch (m_scaleMode) {
        case ScaleMode::KeepAspectRatio:
            aspectMode = Qt::KeepAspectRatio;
            break;
        case ScaleMode::IgnoreAspectRatio:
            aspectMode = Qt::IgnoreAspectRatio;
            break;
        case ScaleMode::KeepAspectRatioByExpanding:
            aspectMode = Qt::KeepAspectRatioByExpanding;
            break;
    }

    m_scaledImage = m_currentImage.scaled(
        size(), aspectMode, Qt::SmoothTransformation
    );
}

void VideoDisplayWidget::paintEvent(QPaintEvent* event)
{
    Q_UNUSED(event);
    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);

    // 填充背景
    painter.fillRect(rect(), QColor(26, 26, 26));

    QMutexLocker locker(&m_mutex);

    if (!m_scaledImage.isNull()) {
        // 計算居中位置
        int x = (width() - m_scaledImage.width()) / 2;
        int y = (height() - m_scaledImage.height()) / 2;
        painter.drawImage(x, y, m_scaledImage);
    } else if (!m_message.isEmpty()) {
        // 顯示消息
        painter.setPen(QColor(136, 136, 136));
        painter.setFont(QFont("Microsoft YaHei", 14));
        painter.drawText(rect(), Qt::AlignCenter, m_message);
    }
}

void VideoDisplayWidget::resizeEvent(QResizeEvent* event)
{
    QWidget::resizeEvent(event);

    QMutexLocker locker(&m_mutex);
    updateScaledImage();
}

void VideoDisplayWidget::mousePressEvent(QMouseEvent* event)
{
    if (m_scaledImage.isNull() || m_currentImage.isNull()) {
        return;
    }

    // 計算圖像在 widget 中的偏移
    int offsetX = (width() - m_scaledImage.width()) / 2;
    int offsetY = (height() - m_scaledImage.height()) / 2;

    // 轉換為圖像座標
    QPoint clickPos = event->pos();
    int imgX = clickPos.x() - offsetX;
    int imgY = clickPos.y() - offsetY;

    // 檢查是否在圖像範圍內
    if (imgX >= 0 && imgX < m_scaledImage.width() &&
        imgY >= 0 && imgY < m_scaledImage.height()) {

        // 縮放到原始圖像座標
        double scaleX = static_cast<double>(m_currentImage.width()) / m_scaledImage.width();
        double scaleY = static_cast<double>(m_currentImage.height()) / m_scaledImage.height();

        int origX = static_cast<int>(imgX * scaleX);
        int origY = static_cast<int>(imgY * scaleY);

        emit clicked(QPoint(origX, origY));
    }
}

} // namespace basler
