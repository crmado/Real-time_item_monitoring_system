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
     * @brief 顯示幀（別名）
     */
    void displayFrame(const cv::Mat& frame) { updateFrame(frame); }

    /**
     * @brief 清除顯示
     */
    void clear();

    /**
     * @brief 顯示消息（無圖像時）
     * @param message 消息文本
     */
    void showMessage(const QString& message);

    /**
     * @brief 顯示佔位符（別名）
     */
    void showPlaceholder(const QString& message) { showMessage(message); }

    /**
     * @brief 啟用/停用 ROI 拖拽框選模式
     * @param enabled true = 進入框選模式（游標變十字，可拖拽框選）
     */
    void setRoiEditMode(bool enabled);

    /**
     * @brief 啟用/停用 光柵線點擊設定模式
     * @param enabled true = 進入點擊模式（游標變十字，點擊影像設定光柵線位置）
     */
    void setGateLineEditMode(bool enabled);

    /**
     * @brief 啟用/停用 HUD overlay（計數、FPS、光柵線）
     * 全螢幕模式下使用，提供最少量操作資訊
     */
    void setHudEnabled(bool enabled);

    /**
     * @brief 更新 HUD 資料（每幀呼叫）
     */
    void updateHud(int count, double fps, double gateRatio);

signals:
    void clicked(const QPoint& pos);    // 點擊事件（圖像座標）
    void doubleClicked();               // 雙擊事件（觸發全螢幕切換）
    /**
     * @brief 用戶拖拽框選完成後發出（影像原始座標）
     */
    void roiSelected(int x, int y, int w, int h);
    /**
     * @brief 用戶點擊設定光柵線位置後發出
     * @param ratio Y 位置比例（0.0 = 頂部，1.0 = 底部，相對於原始影像高度）
     */
    void gateLinePositionSelected(double ratio);

protected:
    void paintEvent(QPaintEvent* event) override;
    void resizeEvent(QResizeEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;
    void mouseMoveEvent(QMouseEvent* event) override;
    void mouseReleaseEvent(QMouseEvent* event) override;
    void mouseDoubleClickEvent(QMouseEvent* event) override;

private:
    QImage matToQImage(const cv::Mat& mat);
    void updateScaledImage();

    QImage m_currentImage;
    QImage m_scaledImage;
    QString m_message;
    QSize m_imageSize;
    ScaleMode m_scaleMode = ScaleMode::KeepAspectRatio;
    QMutex m_mutex;

    // ROI 拖拽編輯狀態（均在主線程存取，無需 mutex）
    bool m_roiEditMode = false;
    bool m_isDragging = false;
    QPoint m_dragStart;  // 拖拽起點（widget 座標）
    QPoint m_dragEnd;    // 拖拽終點（widget 座標，即時更新）

    // 光柵線點擊設定狀態
    bool m_gateLineEditMode = false;
    int m_gateLineMouseY = -1;  // 滑鼠當前 Y 座標（widget 座標，-1 表示未在影像範圍內）

    // HUD（全螢幕模式疊加資訊）
    bool m_hudEnabled = false;
    int m_hudCount = 0;
    double m_hudFps = 0.0;
    double m_hudGateRatio = 0.5;
};

} // namespace basler

#endif // VIDEO_DISPLAY_H
