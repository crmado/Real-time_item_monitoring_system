#include "core/camera_controller.h"
#include <QDebug>
#include <QDateTime>
#include <QtConcurrent>

namespace basler {

// Pylon 全局初始化（RAII 模式）
Pylon::PylonAutoInitTerm CameraController::s_pylonInit;

// ============================================================================
// GrabWorker 實現
// ============================================================================

GrabWorker::GrabWorker(Pylon::CInstantCamera* camera, QObject* parent)
    : QObject(parent)
    , m_camera(camera)
{
}

GrabWorker::~GrabWorker()
{
    stopGrabbing();
}

void GrabWorker::startGrabbing()
{
    if (m_running.load()) {
        return;
    }

    m_running.store(true);
    qDebug() << "[GrabWorker] 開始抓取循環";

    try {
        // 配置抓取策略：只保留最新幀，丟棄中間幀
        m_camera->StartGrabbing(Pylon::GrabStrategy_LatestImageOnly);

        Pylon::CGrabResultPtr grabResult;

        while (m_running.load() && m_camera->IsGrabbing()) {
            // 100ms 超時，允許快速響應停止請求
            if (m_camera->RetrieveResult(100, grabResult, Pylon::TimeoutHandling_Return)) {
                if (grabResult->GrabSucceeded()) {
                    // 直接使用 OpenCV Mat（零拷貝包裝）
                    cv::Mat frame(
                        grabResult->GetHeight(),
                        grabResult->GetWidth(),
                        CV_8UC1,
                        grabResult->GetBuffer()
                    );

                    // 深拷貝一份發送（因為 grabResult 會被復用）
                    qint64 timestamp = QDateTime::currentMSecsSinceEpoch();
                    emit frameGrabbed(frame.clone(), timestamp);
                }
            }
            // 沒有 sleep - 全速運行
        }
    }
    catch (const Pylon::GenericException& e) {
        emit grabError(QString::fromStdString(e.GetDescription()));
    }

    m_running.store(false);

    // 確保停止相機抓取
    if (m_camera->IsGrabbing()) {
        m_camera->StopGrabbing();
    }

    emit grabStopped();
    qDebug() << "[GrabWorker] 抓取循環結束";
}

void GrabWorker::stopGrabbing()
{
    qDebug() << "[GrabWorker] 收到停止請求";
    m_running.store(false);  // 原子操作，線程安全
}

// ============================================================================
// CameraController 實現
// ============================================================================

CameraController::CameraController(QObject* parent)
    : QObject(parent)
{
    // 註冊自定義類型（用於跨線程信號）
    qRegisterMetaType<CameraState>("CameraState");
    qRegisterMetaType<CameraInfo>("CameraInfo");
    qRegisterMetaType<cv::Mat>("cv::Mat");

    qDebug() << "[CameraController] 初始化完成";
}

CameraController::~CameraController()
{
    // RAII：確保資源正確釋放

    // 先斷開所有信號連接，防止析構期間信號觸發
    if (m_grabWorker) {
        m_grabWorker->disconnect();
    }
    if (m_grabThread) {
        m_grabThread->disconnect();
    }

    // 停止抓取
    if (isGrabbing() || m_grabThread) {
        if (m_grabWorker) {
            m_grabWorker->stopGrabbing();
        }
        if (m_grabThread && m_grabThread->isRunning()) {
            m_grabThread->quit();
            if (!m_grabThread->wait(3000)) {
                qWarning() << "[CameraController] 析構：線程等待超時";
            }
        }
    }

    // 清理線程資源
    m_grabWorker.reset();
    m_grabThread.reset();

    // 關閉相機
    if (m_camera && m_camera->IsOpen()) {
        m_camera->Close();
    }
    m_camera.reset();

    qDebug() << "[CameraController] 資源已清理";
}

// ============================================================================
// 狀態查詢
// ============================================================================

bool CameraController::isConnected() const
{
    CameraState s = m_state.load();
    return s == CameraState::Connected ||
           s == CameraState::Grabbing ||
           s == CameraState::StartingGrab ||
           s == CameraState::StoppingGrab;
}

bool CameraController::isGrabbing() const
{
    return m_state.load() == CameraState::Grabbing;
}

// ============================================================================
// 狀態機
// ============================================================================

void CameraController::setState(CameraState newState)
{
    CameraState oldState = m_state.exchange(newState);
    if (oldState != newState) {
        qDebug() << "[CameraController] 狀態轉換:"
                 << static_cast<int>(oldState) << "->"
                 << static_cast<int>(newState);
        emit stateChanged(newState);
    }
}

bool CameraController::transitionTo(CameraState newState)
{
    CameraState current = m_state.load();

    // 定義合法的狀態轉換
    bool valid = false;
    switch (newState) {
        case CameraState::Connecting:
            valid = (current == CameraState::Disconnected);
            break;
        case CameraState::Connected:
            valid = (current == CameraState::Connecting ||
                     current == CameraState::StoppingGrab);
            break;
        case CameraState::StartingGrab:
            valid = (current == CameraState::Connected);
            break;
        case CameraState::Grabbing:
            valid = (current == CameraState::StartingGrab);
            break;
        case CameraState::StoppingGrab:
            valid = (current == CameraState::Grabbing);
            break;
        case CameraState::Disconnecting:
            valid = (current == CameraState::Connected ||
                     current == CameraState::Error);
            break;
        case CameraState::Disconnected:
            valid = (current == CameraState::Disconnecting ||
                     current == CameraState::Error);
            break;
        case CameraState::Error:
            valid = true;  // 任何狀態都可以進入錯誤狀態
            break;
    }

    if (valid) {
        setState(newState);
    } else {
        qWarning() << "[CameraController] 非法狀態轉換:"
                   << static_cast<int>(current) << "->"
                   << static_cast<int>(newState);
    }

    return valid;
}

// ============================================================================
// 相機操作
// ============================================================================

QList<CameraInfo> CameraController::detectCameras()
{
    QList<CameraInfo> cameras;

    try {
        Pylon::CTlFactory& factory = Pylon::CTlFactory::GetInstance();
        Pylon::DeviceInfoList_t devices;
        factory.EnumerateDevices(devices);

        for (size_t i = 0; i < devices.size(); ++i) {
            CameraInfo info;
            info.index = static_cast<int>(i);
            info.model = QString::fromStdString(devices[i].GetModelName().c_str());
            info.serial = QString::fromStdString(devices[i].GetSerialNumber().c_str());
            info.friendlyName = QString::fromStdString(devices[i].GetFriendlyName().c_str());
            info.isTargetModel = info.model.contains("acA640-300gm");

            cameras.append(info);
            qDebug() << "[CameraController] 發現相機:" << info.model;
        }
    }
    catch (const Pylon::GenericException& e) {
        qWarning() << "[CameraController] 檢測相機失敗:" << e.GetDescription();
    }

    return cameras;
}

void CameraController::connectCamera(int cameraIndex)
{
    // 使用 QtConcurrent 在背景線程執行，不阻塞 UI
    QtConcurrent::run([this, cameraIndex]() {
        if (!transitionTo(CameraState::Connecting)) {
            emit connectionError("無法從當前狀態連接相機");
            return;
        }

        try {
            Pylon::CTlFactory& factory = Pylon::CTlFactory::GetInstance();
            Pylon::DeviceInfoList_t devices;
            factory.EnumerateDevices(devices);

            if (cameraIndex >= static_cast<int>(devices.size())) {
                throw std::runtime_error("相機索引超出範圍");
            }

            // 創建相機實例
            m_camera = std::make_unique<Pylon::CInstantCamera>(
                factory.CreateDevice(devices[cameraIndex])
            );

            // 打開相機
            m_camera->Open();

            // 配置相機參數
            configureCamera();

            // 準備相機資訊
            CameraInfo info;
            info.index = cameraIndex;
            info.model = QString::fromStdString(devices[cameraIndex].GetModelName().c_str());
            info.serial = QString::fromStdString(devices[cameraIndex].GetSerialNumber().c_str());

            setState(CameraState::Connected);
            emit connected(info);

            qDebug() << "[CameraController] 相機連接成功:" << info.model;
        }
        catch (const Pylon::GenericException& e) {
            setState(CameraState::Error);
            emit connectionError(QString::fromStdString(e.GetDescription()));
        }
        catch (const std::exception& e) {
            setState(CameraState::Error);
            emit connectionError(QString::fromStdString(e.what()));
        }
    });
}

void CameraController::disconnectCamera()
{
    QtConcurrent::run([this]() {
        if (!transitionTo(CameraState::Disconnecting)) {
            return;
        }

        // 先停止抓取（如果正在抓取）
        if (m_grabWorker) {
            m_grabWorker->stopGrabbing();
            m_grabWorker->disconnect();  // 防止懸空指針
        }

        if (m_grabThread) {
            m_grabThread->disconnect();  // 防止懸空指針
            if (m_grabThread->isRunning()) {
                m_grabThread->quit();
                if (!m_grabThread->wait(3000)) {
                    qWarning() << "[CameraController] 抓取線程等待超時";
                }
            }
        }

        // 先清理線程和 worker
        m_grabWorker.reset();
        m_grabThread.reset();

        // 再關閉相機
        if (m_camera && m_camera->IsOpen()) {
            m_camera->Close();
        }
        m_camera.reset();

        setState(CameraState::Disconnected);
        emit disconnected();

        qDebug() << "[CameraController] 相機已斷開";
    });
}

void CameraController::startGrabbing()
{
    if (!transitionTo(CameraState::StartingGrab)) {
        emit grabError("無法從當前狀態開始抓取");
        return;
    }

    // 創建抓取線程
    m_grabThread = std::make_unique<QThread>();
    m_grabWorker = std::make_unique<GrabWorker>(m_camera.get());
    m_grabWorker->moveToThread(m_grabThread.get());

    // 連接信號（跨線程，Qt 自動使用 QueuedConnection）
    connect(m_grabThread.get(), &QThread::started,
            m_grabWorker.get(), &GrabWorker::startGrabbing);
    connect(m_grabWorker.get(), &GrabWorker::frameGrabbed,
            this, &CameraController::onFrameGrabbed);
    connect(m_grabWorker.get(), &GrabWorker::grabError,
            this, &CameraController::onGrabError);
    connect(m_grabWorker.get(), &GrabWorker::grabStopped,
            this, &CameraController::onGrabStopped);

    // 重置統計
    m_totalFrames.store(0);
    m_currentFps.store(0.0);
    m_frameTimes.clear();

    // 啟動線程
    m_grabThread->start();

    setState(CameraState::Grabbing);
    emit grabbingStarted();

    qDebug() << "[CameraController] 開始抓取";
}

void CameraController::stopGrabbing()
{
    if (!transitionTo(CameraState::StoppingGrab)) {
        return;
    }

    // 發送停止請求（非阻塞）
    if (m_grabWorker) {
        m_grabWorker->stopGrabbing();
    }

    // 線程會自己結束並發出 grabStopped 信號
    qDebug() << "[CameraController] 已發送停止抓取請求";
}

void CameraController::setExposure(double exposureUs)
{
    if (!m_camera || !m_camera->IsOpen()) {
        return;
    }

    try {
        m_exposureTime = exposureUs;

        // 確保手動曝光模式
        GenApi::INodeMap& nodemap = m_camera->GetNodeMap();

        GenApi::CEnumerationPtr exposureAuto(nodemap.GetNode("ExposureAuto"));
        if (exposureAuto.IsValid()) {
            exposureAuto->FromString("Off");
        }

        GenApi::CFloatPtr exposureTime(nodemap.GetNode("ExposureTime"));
        if (exposureTime.IsValid()) {
            exposureTime->SetValue(exposureUs);
        }

        qDebug() << "[CameraController] 曝光時間設置為:" << exposureUs << "us";
    }
    catch (const Pylon::GenericException& e) {
        qWarning() << "[CameraController] 設置曝光失敗:" << e.GetDescription();
    }
}

// ============================================================================
// 私有槽函數
// ============================================================================

void CameraController::onFrameGrabbed(const cv::Mat& frame, qint64 timestamp)
{
    // 更新統計
    m_totalFrames.fetch_add(1);

    {
        QMutexLocker locker(&m_statsMutex);
        m_frameTimes.push_back(timestamp);

        // 保留最近 60 幀的時間戳
        while (m_frameTimes.size() > 60) {
            m_frameTimes.pop_front();
        }

        // 計算 FPS
        if (m_frameTimes.size() >= 2) {
            qint64 timeDiff = m_frameTimes.back() - m_frameTimes.front();
            if (timeDiff > 0) {
                double fps = (m_frameTimes.size() - 1) * 1000.0 / timeDiff;
                m_currentFps.store(fps);
                emit fpsUpdated(fps);
            }
        }
    }

    // 發送幀給 UI
    emit frameReady(frame);
}

void CameraController::onGrabError(const QString& error)
{
    qWarning() << "[CameraController] 抓取錯誤:" << error;
    setState(CameraState::Error);
    emit grabError(error);
}

void CameraController::onGrabStopped()
{
    // 清理線程
    if (m_grabThread && m_grabThread->isRunning()) {
        m_grabThread->quit();
        m_grabThread->wait(1000);
    }

    setState(CameraState::Connected);
    emit grabbingStopped();

    qDebug() << "[CameraController] 抓取已停止";
}

// ============================================================================
// 私有方法
// ============================================================================

void CameraController::configureCamera()
{
    if (!m_camera || !m_camera->IsOpen()) {
        return;
    }

    try {
        GenApi::INodeMap& nodemap = m_camera->GetNodeMap();

        // 設置圖像格式
        GenApi::CIntegerPtr width(nodemap.GetNode("Width"));
        GenApi::CIntegerPtr height(nodemap.GetNode("Height"));
        if (width.IsValid()) width->SetValue(640);
        if (height.IsValid()) height->SetValue(480);

        // 設置像素格式為 Mono8
        GenApi::CEnumerationPtr pixelFormat(nodemap.GetNode("PixelFormat"));
        if (pixelFormat.IsValid()) {
            pixelFormat->FromString("Mono8");
        }

        // 關閉自動曝光
        GenApi::CEnumerationPtr exposureAuto(nodemap.GetNode("ExposureAuto"));
        if (exposureAuto.IsValid()) {
            exposureAuto->FromString("Off");
        }

        // 設置曝光時間
        GenApi::CFloatPtr exposureTime(nodemap.GetNode("ExposureTime"));
        if (exposureTime.IsValid()) {
            exposureTime->SetValue(m_exposureTime);
        }

        // 啟用幀率控制
        GenApi::CBooleanPtr fpsEnable(nodemap.GetNode("AcquisitionFrameRateEnable"));
        if (fpsEnable.IsValid()) {
            fpsEnable->SetValue(true);
        }

        GenApi::CFloatPtr fps(nodemap.GetNode("AcquisitionFrameRate"));
        if (fps.IsValid()) {
            fps->SetValue(m_targetFps);
        }

        // GigE 優化：設置最大封包大小
        GenApi::CIntegerPtr packetSize(nodemap.GetNode("GevSCPSPacketSize"));
        if (packetSize.IsValid()) {
            packetSize->SetValue(9000);  // Jumbo frames
        }

        qDebug() << "[CameraController] 相機配置完成";
    }
    catch (const Pylon::GenericException& e) {
        qWarning() << "[CameraController] 配置警告:" << e.GetDescription();
    }
}

} // namespace basler
