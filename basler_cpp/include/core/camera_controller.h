#ifndef CAMERA_CONTROLLER_H
#define CAMERA_CONTROLLER_H

#include <QObject>
#include <QThread>
#include <QMutex>
#include <QWaitCondition>
#include <QElapsedTimer>
#include <QImage>
#include <atomic>
#include <memory>
#include <deque>

#ifndef NO_PYLON_SDK
#include <pylon/PylonIncludes.h>
#endif
#include <opencv2/core.hpp>

namespace basler {

/**
 * @brief 相機資訊結構
 */
struct CameraInfo {
    int index;
    QString model;
    QString serial;
    QString friendlyName;
    bool isTargetModel;  // acA640-300gm
};

/**
 * @brief 相機狀態枚舉
 *
 * 使用狀態機避免非法狀態轉換，這是 C++ 版本的關鍵改進：
 * - 明確的狀態定義
 * - 原子操作保證線程安全
 * - 狀態轉換有嚴格檢查
 */
enum class CameraState {
    Disconnected,   // 未連接
    Connecting,     // 連接中（過渡狀態）
    Connected,      // 已連接但未抓取
    StartingGrab,   // 啟動抓取中（過渡狀態）
    Grabbing,       // 抓取中
    StoppingGrab,   // 停止抓取中（過渡狀態）
    Disconnecting,  // 斷開連接中（過渡狀態）
    Error           // 錯誤狀態
};

/**
 * @brief 圖像抓取工作線程
 *
 * 獨立於主線程運行，避免 UI 阻塞。
 * 使用 Qt 信號槽機制安全地將數據傳回主線程。
 */
#ifndef NO_PYLON_SDK
class GrabWorker : public QObject {
    Q_OBJECT

public:
    explicit GrabWorker(Pylon::CInstantCamera* camera, QObject* parent = nullptr);
    ~GrabWorker();

public slots:
    void startGrabbing();
    void stopGrabbing();

signals:
    void frameGrabbed(const cv::Mat& frame, qint64 timestamp);
    void grabError(const QString& error);
    void grabStopped();

private:
    Pylon::CInstantCamera* m_camera;
    std::atomic<bool> m_running{false};
    QMutex m_mutex;
};
#else
// Stub GrabWorker for builds without Pylon SDK
class GrabWorker : public QObject {
    Q_OBJECT

public:
    explicit GrabWorker(void* camera = nullptr, QObject* parent = nullptr) : QObject(parent) { Q_UNUSED(camera); }
    ~GrabWorker() = default;

public slots:
    void startGrabbing() {}
    void stopGrabbing() {}

signals:
    void frameGrabbed(const cv::Mat& frame, qint64 timestamp);
    void grabError(const QString& error);
    void grabStopped();

private:
    std::atomic<bool> m_running{false};
    QMutex m_mutex;
};
#endif

/**
 * @brief Basler 相機控制器
 *
 * 核心設計理念（相比 Python 版本的改進）：
 * 1. 狀態機管理 - 所有操作都檢查當前狀態，避免非法操作
 * 2. 異步操作 - 連接/斷開/啟動/停止都不阻塞 UI
 * 3. 信號驅動 - 操作完成通過信號通知，不需要輪詢
 * 4. RAII 資源管理 - 自動清理，無資源洩漏
 */
class CameraController : public QObject {
    Q_OBJECT
    Q_PROPERTY(CameraState state READ state NOTIFY stateChanged)
    Q_PROPERTY(double fps READ fps NOTIFY fpsUpdated)

public:
    explicit CameraController(QObject* parent = nullptr);
    ~CameraController();

    // 禁止複製
    CameraController(const CameraController&) = delete;
    CameraController& operator=(const CameraController&) = delete;

    // ===== 狀態查詢 =====
    CameraState state() const { return m_state.load(); }
    bool isConnected() const;
    bool isGrabbing() const;
    double fps() const { return m_currentFps; }
    qint64 totalFrames() const { return m_totalFrames; }

    // ===== 相機操作（全部異步，不阻塞 UI）=====
    QList<CameraInfo> detectCameras();

public slots:
    /**
     * @brief 異步連接相機
     * @param cameraIndex 相機索引
     *
     * 操作完成後發出 connected() 或 connectionError() 信號
     */
    void connectCamera(int cameraIndex = 0);

    /**
     * @brief 異步斷開相機
     *
     * 操作完成後發出 disconnected() 信號
     */
    void disconnectCamera();

    /**
     * @brief 異步開始抓取
     *
     * 操作完成後發出 grabbingStarted() 或 grabError() 信號
     */
    void startGrabbing();

    /**
     * @brief 異步停止抓取
     *
     * 操作完成後發出 grabbingStopped() 信號
     */
    void stopGrabbing();

    /**
     * @brief 設置曝光時間
     * @param exposureUs 曝光時間（微秒）
     */
    void setExposure(double exposureUs);

signals:
    // ===== 狀態信號 =====
    void stateChanged(CameraState newState);

    // ===== 操作完成信號 =====
    void connected(const CameraInfo& info);
    void disconnected();
    void grabbingStarted();
    void grabbingStopped();

    // ===== 數據信號 =====
    void frameReady(const cv::Mat& frame);      // 新幀可用
    void fpsUpdated(double fps);                 // FPS 更新

    // ===== 錯誤信號 =====
    void connectionError(const QString& error);
    void grabError(const QString& error);

private slots:
    void onFrameGrabbed(const cv::Mat& frame, qint64 timestamp);
    void onGrabError(const QString& error);
    void onGrabStopped();

private:
    // 狀態轉換輔助
    bool transitionTo(CameraState newState);
    void setState(CameraState newState);

    // 相機配置
    void configureCamera();

    // 資源
#ifndef NO_PYLON_SDK
    std::unique_ptr<Pylon::CInstantCamera> m_camera;
#else
    void* m_camera = nullptr;  // Stub for builds without Pylon
#endif
    std::unique_ptr<QThread> m_grabThread;
    std::unique_ptr<GrabWorker> m_grabWorker;

    // 狀態（原子操作保證線程安全）
    std::atomic<CameraState> m_state{CameraState::Disconnected};

    // 性能統計
    std::atomic<qint64> m_totalFrames{0};
    std::atomic<double> m_currentFps{0.0};
    std::deque<qint64> m_frameTimes;
    QMutex m_statsMutex;

    // 配置
    double m_targetFps = 350.0;
    double m_exposureTime = 1000.0;  // 微秒

#ifndef NO_PYLON_SDK
    // Pylon 初始化（全局單例）
    static Pylon::PylonAutoInitTerm s_pylonInit;
#endif
};

} // namespace basler

// 讓 Qt 能夠在信號中傳遞
Q_DECLARE_METATYPE(basler::CameraState)
Q_DECLARE_METATYPE(basler::CameraInfo)
Q_DECLARE_METATYPE(cv::Mat)

#endif // CAMERA_CONTROLLER_H
