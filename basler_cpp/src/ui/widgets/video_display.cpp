#include "ui/widgets/video_display.h"
#include <QPainter>
#include <QResizeEvent>
#include <QMouseEvent>
#include <algorithm>
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

    int scaledW = 0, scaledH = 0, origW = 0, origH = 0;
    QPoint imageOffset;

    {
        QMutexLocker locker(&m_mutex);

        if (!m_scaledImage.isNull()) {
            // 計算居中位置
            imageOffset.setX((width() - m_scaledImage.width()) / 2);
            imageOffset.setY((height() - m_scaledImage.height()) / 2);
            scaledW = m_scaledImage.width();
            scaledH = m_scaledImage.height();
            origW = m_currentImage.width();
            origH = m_currentImage.height();
            painter.drawImage(imageOffset, m_scaledImage);
        } else if (!m_message.isEmpty()) {
            painter.setPen(QColor(136, 136, 136));
            painter.setFont(QFont("Microsoft YaHei", 14));
            painter.drawText(rect(), Qt::AlignCenter, m_message);
        }
    } // mutex 在此釋放，之後繪製 overlay 不持鎖

    // ===== ROI 編輯模式 overlay（主線程，無需 mutex）=====
    if (m_roiEditMode) {
        // 藍色虛線邊框提示目前處於框選模式
        painter.setPen(QPen(QColor(0, 212, 255), 2, Qt::DashLine));
        painter.setBrush(Qt::NoBrush);
        painter.drawRect(rect().adjusted(1, 1, -1, -1));

        // 頂部提示文字
        painter.setPen(QColor(0, 212, 255));
        painter.setFont(QFont("Arial", 11, QFont::Bold));
        painter.drawText(rect().adjusted(0, 6, 0, 0),
                         Qt::AlignTop | Qt::AlignHCenter,
                         tr("拖拽以框選 ROI  |  ESC 取消"));
    }

    // ===== 光柵線點擊設定模式 overlay =====
    if (m_gateLineEditMode) {
        // 黃色虛線邊框提示
        painter.setPen(QPen(QColor(255, 204, 0), 2, Qt::DashLine));
        painter.setBrush(Qt::NoBrush);
        painter.drawRect(rect().adjusted(1, 1, -1, -1));

        painter.setPen(QColor(255, 204, 0));
        painter.setFont(QFont("Arial", 11, QFont::Bold));
        painter.drawText(rect().adjusted(0, 6, 0, 0),
                         Qt::AlignTop | Qt::AlignHCenter,
                         tr("點擊影像設定光柵線位置  |  ESC 取消"));

        // 水平預覽線（跟隨滑鼠 Y 軸）
        if (m_gateLineMouseY >= 0 && scaledW > 0) {
            painter.setPen(QPen(QColor(255, 204, 0), 2, Qt::DashLine));
            int lineY = m_gateLineMouseY;
            painter.drawLine(imageOffset.x(), lineY,
                             imageOffset.x() + scaledW, lineY);

            // 顯示 ratio 數值
            if (scaledH > 0) {
                double ratio = static_cast<double>(lineY - imageOffset.y()) / scaledH;
                ratio = std::max(0.0, std::min(1.0, ratio));
                QString ratioText = QString("ratio = %1").arg(ratio, 0, 'f', 2);
                painter.setBrush(QColor(0, 0, 0, 140));
                painter.setPen(Qt::NoPen);
                QRect badge(imageOffset.x() + scaledW - 110, lineY - 22, 108, 20);
                painter.drawRect(badge);
                painter.setPen(QColor(255, 204, 0));
                painter.setFont(QFont("Arial", 9));
                painter.drawText(badge, Qt::AlignCenter, ratioText);
            }
        }
    }

    // 拖拽中：繪製 rubber-band 矩形
    if (m_isDragging && scaledW > 0 && origW > 0) {
        QRect dragRect = QRect(m_dragStart, m_dragEnd).normalized();

        painter.setPen(QPen(QColor(0, 212, 255), 2, Qt::DashLine));
        painter.setBrush(QColor(0, 212, 255, 40));
        painter.drawRect(dragRect);

        // 在矩形右下角顯示尺寸（影像原始座標）
        double scaleX = static_cast<double>(origW) / scaledW;
        double scaleY = static_cast<double>(origH) / scaledH;
        int vw = static_cast<int>(dragRect.width() * scaleX);
        int vh = static_cast<int>(dragRect.height() * scaleY);

        painter.setBrush(QColor(0, 0, 0, 140));
        QRect sizeHint(dragRect.right() - 70, dragRect.bottom() - 20, 70, 20);
        painter.setPen(Qt::NoPen);
        painter.drawRect(sizeHint);
        painter.setPen(Qt::white);
        painter.setFont(QFont("Arial", 9));
        painter.drawText(sizeHint, Qt::AlignCenter,
                         QString("%1×%2").arg(vw).arg(vh));
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

    if (m_roiEditMode && event->button() == Qt::LeftButton) {
        // ROI 框選模式：開始拖拽
        m_isDragging = true;
        m_dragStart = event->pos();
        m_dragEnd = event->pos();
        update();
        return;
    }

    if (m_gateLineEditMode && event->button() == Qt::LeftButton) {
        // 光柵線點擊模式：計算 Y ratio 並發出信號
        QMutexLocker locker(&m_mutex);
        if (!m_scaledImage.isNull() && m_scaledImage.height() > 0) {
            int offsetY = (height() - m_scaledImage.height()) / 2;
            int scaledH = m_scaledImage.height();
            locker.unlock();

            double ratio = static_cast<double>(event->pos().y() - offsetY) / scaledH;
            ratio = std::max(0.0, std::min(1.0, ratio));
            emit gateLinePositionSelected(ratio);
        }
        setGateLineEditMode(false);
        return;
    }

    // 一般模式：發出 clicked 信號（影像原始座標）
    int offsetX = (width() - m_scaledImage.width()) / 2;
    int offsetY = (height() - m_scaledImage.height()) / 2;
    QPoint clickPos = event->pos();
    int imgX = clickPos.x() - offsetX;
    int imgY = clickPos.y() - offsetY;

    if (imgX >= 0 && imgX < m_scaledImage.width() &&
        imgY >= 0 && imgY < m_scaledImage.height()) {
        double scaleX = static_cast<double>(m_currentImage.width()) / m_scaledImage.width();
        double scaleY = static_cast<double>(m_currentImage.height()) / m_scaledImage.height();
        emit clicked(QPoint(static_cast<int>(imgX * scaleX),
                            static_cast<int>(imgY * scaleY)));
    }
}

void VideoDisplayWidget::mouseMoveEvent(QMouseEvent* event)
{
    if (m_isDragging) {
        m_dragEnd = event->pos();
        update();  // 觸發 paintEvent 重繪 rubber-band
    }

    if (m_gateLineEditMode) {
        m_gateLineMouseY = event->pos().y();
        update();  // 觸發 paintEvent 重繪水平預覽線
    }
}

void VideoDisplayWidget::mouseReleaseEvent(QMouseEvent* event)
{
    if (!m_isDragging || event->button() != Qt::LeftButton) {
        return;
    }

    m_isDragging = false;
    m_dragEnd = event->pos();

    // 轉換拖拽矩形到影像原始座標
    QMutexLocker locker(&m_mutex);
    if (!m_scaledImage.isNull() && !m_currentImage.isNull()) {
        int offsetX = (width() - m_scaledImage.width()) / 2;
        int offsetY = (height() - m_scaledImage.height()) / 2;
        double scaleX = static_cast<double>(m_currentImage.width()) / m_scaledImage.width();
        double scaleY = static_cast<double>(m_currentImage.height()) / m_scaledImage.height();

        // 轉換兩端點並正規化矩形
        int x1 = static_cast<int>((m_dragStart.x() - offsetX) * scaleX);
        int y1 = static_cast<int>((m_dragStart.y() - offsetY) * scaleY);
        int x2 = static_cast<int>((m_dragEnd.x() - offsetX) * scaleX);
        int y2 = static_cast<int>((m_dragEnd.y() - offsetY) * scaleY);
        locker.unlock();

        QRect roi = QRect(QPoint(x1, y1), QPoint(x2, y2)).normalized();

        // 限制在影像範圍內
        roi = roi.intersected(QRect(0, 0, m_currentImage.width(), m_currentImage.height()));

        if (roi.width() > 4 && roi.height() > 4) {
            emit roiSelected(roi.x(), roi.y(), roi.width(), roi.height());
        }
    }

    // 拖拽完成後自動退出框選模式
    setRoiEditMode(false);
}

void VideoDisplayWidget::setRoiEditMode(bool enabled)
{
    m_roiEditMode = enabled;
    m_isDragging = false;
    if (enabled) {
        m_gateLineEditMode = false;  // 兩種模式互斥
        setCursor(Qt::CrossCursor);
        setMouseTracking(true);
    } else {
        if (!m_gateLineEditMode) {
            unsetCursor();
            setMouseTracking(false);
        }
    }
    update();
}

void VideoDisplayWidget::setGateLineEditMode(bool enabled)
{
    m_gateLineEditMode = enabled;
    m_gateLineMouseY = -1;
    if (enabled) {
        m_roiEditMode = false;  // 兩種模式互斥
        m_isDragging = false;
        setCursor(Qt::CrossCursor);
        setMouseTracking(true);  // 需要 mouseMoveEvent 才能更新預覽線
    } else {
        if (!m_roiEditMode) {
            unsetCursor();
            setMouseTracking(false);
        }
    }
    update();
}

} // namespace basler
