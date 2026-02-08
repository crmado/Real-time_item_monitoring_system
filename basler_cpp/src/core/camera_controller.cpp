#include "core/camera_controller.h"
#include <QDebug>
#include <QDateTime>
#include <QtConcurrent>

#ifndef NO_PYLON_SDK

namespace basler
{

    // Pylon 全局初始化（RAII 模式）
    Pylon::PylonAutoInitTerm CameraController::s_pylonInit;

    // ============================================================================
    // GrabWorker 實現
    // ============================================================================

    GrabWorker::GrabWorker(Pylon::CInstantCamera *camera, QObject *parent)
        : QObject(parent), m_camera(camera)
    {
    }

    GrabWorker::~GrabWorker()
    {
        stopGrabbing();
    }

    void GrabWorker::startGrabbing()
    {
        if (m_running.load())
        {
            return;
        }

        m_running.store(true);
        qDebug() << "[GrabWorker] 開始抓取循環";

        try
        {
            // 增加接收緩衝區（防止 GigE 緩衝區不足）
            m_camera->MaxNumBuffer = 10;

            // 配置抓取策略：只保留最新幀，丟棄中間幀
            m_camera->StartGrabbing(Pylon::GrabStrategy_LatestImageOnly);

            Pylon::CGrabResultPtr grabResult;
            int frameCount = 0;
            int errorCount = 0;

            while (m_running.load() && m_camera->IsGrabbing())
            {
                // 500ms 超時（給 GigE 更多緩衝時間）
                if (m_camera->RetrieveResult(500, grabResult, Pylon::TimeoutHandling_Return))
                {
                    if (grabResult->GrabSucceeded())
                    {
                        errorCount = 0; // 重置錯誤計數

                        // 根據像素格式決定 Mat 類型
                        int cvType = CV_8UC1;
                        Pylon::EPixelType pixelType = grabResult->GetPixelType();
                        if (Pylon::IsBGR(pixelType) || Pylon::IsRGB(pixelType))
                        {
                            cvType = CV_8UC3;
                        }

                        cv::Mat frame(
                            grabResult->GetHeight(),
                            grabResult->GetWidth(),
                            cvType,
                            grabResult->GetBuffer());

                        // 深拷貝一份發送（因為 grabResult 會被復用）
                        qint64 timestamp = QDateTime::currentMSecsSinceEpoch();
                        cv::Mat frameCopy = frame.clone();
                        emit frameGrabbed(frameCopy, timestamp);

                        frameCount++;
                        if (frameCount == 1 || frameCount % 100 == 0)
                        {
                            qDebug() << "[GrabWorker] 已抓取" << frameCount << "幀, 尺寸:"
                                     << frameCopy.cols << "x" << frameCopy.rows;
                        }
                    }
                    else
                    {
                        errorCount++;
                        if (errorCount <= 5)
                        {
                            qWarning() << "[GrabWorker] 抓取失敗 (" << errorCount << "):"
                                       << grabResult->GetErrorDescription();
                        }
                        // 連續錯誤過多時，給系統一點緩衝時間
                        if (errorCount > 10)
                        {
                            QThread::msleep(50);
                        }
                    }
                }
                // 沒有 sleep - 全速運行
            }
        }
        catch (const Pylon::GenericException &e)
        {
            emit grabError(QString::fromStdString(e.GetDescription()));
        }

        m_running.store(false);

        // 確保停止相機抓取
        if (m_camera->IsGrabbing())
        {
            m_camera->StopGrabbing();
        }

        emit grabStopped();
        qDebug() << "[GrabWorker] 抓取循環結束";
    }

    void GrabWorker::stopGrabbing()
    {
        qDebug() << "[GrabWorker] 收到停止請求";
        m_running.store(false); // 原子操作，線程安全
    }

    // ============================================================================
    // CameraController 實現
    // ============================================================================

    CameraController::CameraController(QObject *parent)
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
        if (m_grabWorker)
        {
            m_grabWorker->disconnect();
        }
        if (m_grabThread)
        {
            m_grabThread->disconnect();
        }

        // 停止抓取
        if (isGrabbing() || m_grabThread)
        {
            if (m_grabWorker)
            {
                m_grabWorker->stopGrabbing();
            }
            if (m_grabThread && m_grabThread->isRunning())
            {
                m_grabThread->quit();
                if (!m_grabThread->wait(3000))
                {
                    qWarning() << "[CameraController] 析構：線程等待超時";
                }
            }
        }

        // 清理線程資源
        m_grabWorker.reset();
        m_grabThread.reset();

        // 關閉相機
        if (m_camera && m_camera->IsOpen())
        {
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
        if (oldState != newState)
        {
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
        switch (newState)
        {
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
                     current == CameraState::StoppingGrab ||
                     current == CameraState::Grabbing ||
                     current == CameraState::Error);
            break;
        case CameraState::Disconnected:
            valid = (current == CameraState::Disconnecting ||
                     current == CameraState::Error);
            break;
        case CameraState::Error:
            valid = true; // 任何狀態都可以進入錯誤狀態
            break;
        }

        if (valid)
        {
            setState(newState);
        }
        else
        {
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

        try
        {
            Pylon::CTlFactory &factory = Pylon::CTlFactory::GetInstance();
            Pylon::DeviceInfoList_t devices;
            factory.EnumerateDevices(devices);

            for (size_t i = 0; i < devices.size(); ++i)
            {
                CameraInfo info;
                info.index = static_cast<int>(i);
                info.model = QString::fromStdString(devices[i].GetModelName().c_str());
                info.serial = QString::fromStdString(devices[i].GetSerialNumber().c_str());
                info.friendlyName = QString::fromStdString(devices[i].GetFriendlyName().c_str());
                info.isTargetModel = info.model.contains("acA640-300gm");

                cameras.append(info);
                qDebug() << "[CameraController] Found camera:" << info.model;
            }
        }
        catch (const Pylon::GenericException &e)
        {
            qWarning() << "[CameraController] Camera detection failed:" << e.GetDescription();
        }

        return cameras;
    }

    QList<CameraInfo> CameraController::detectCamerasWithRetry(int maxRetries, int delayMs)
    {
        QList<CameraInfo> cameras;

        qDebug() << "[CameraController] Scanning for cameras with auto-retry (max" << maxRetries << "attempts)";

        for (int attempt = 1; attempt <= maxRetries; ++attempt)
        {
            qDebug() << "[CameraController] Attempt" << attempt << "/" << maxRetries << "- Scanning...";

            cameras = detectCameras();

            if (!cameras.empty())
            {
                qDebug() << "[CameraController] Successfully found" << cameras.size() << "camera(s) on attempt" << attempt;
                return cameras;
            }

            if (attempt < maxRetries)
            {
                qDebug() << "[CameraController] No cameras found, waiting" << delayMs << "ms before retry...";
                QThread::msleep(delayMs);
            }
        }

        qWarning() << "[CameraController] No cameras detected after" << maxRetries << "attempts";
        qWarning() << "[CameraController] Possible causes:";
        qWarning() << "  1. Camera power is off or booting (GigE cameras need 5-10 seconds)";
        qWarning() << "  2. Network cable not connected properly";
        qWarning() << "  3. Windows Firewall blocking GigE Vision protocol (UDP broadcast)";
        qWarning() << "  4. Network adapter driver issues";

        return cameras;
    }

    void CameraController::connectCamera(int cameraIndex)
    {
        // 使用 QtConcurrent 在背景線程執行，不阻塞 UI
        QtConcurrent::run([this, cameraIndex]()
                          {
        // 使用 QMetaObject::invokeMethod 確保狀態轉換在主線程執行
        bool transitionOk = false;
        QMetaObject::invokeMethod(this, [this, &transitionOk]() {
            transitionOk = transitionTo(CameraState::Connecting);
        }, Qt::BlockingQueuedConnection);
        
        if (!transitionOk) {
            QMetaObject::invokeMethod(this, [this]() {
                emit connectionError("無法從當前狀態連接相機");
            }, Qt::QueuedConnection);
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

            // 使用 QMetaObject::invokeMethod 確保狀態更新和信號發射在主線程
            QMetaObject::invokeMethod(this, [this, info]() {
                setState(CameraState::Connected);
                emit connected(info);
                qDebug() << "[CameraController] 相機連接成功:" << info.model;
            }, Qt::QueuedConnection);
        }
        catch (const Pylon::GenericException& e) {
            QString errorMsg = QString::fromStdString(e.GetDescription());
            QMetaObject::invokeMethod(this, [this, errorMsg]() {
                setState(CameraState::Error);
                emit connectionError(errorMsg);
            }, Qt::QueuedConnection);
        }
        catch (const std::exception& e) {
            QString errorMsg = QString::fromStdString(e.what());
            QMetaObject::invokeMethod(this, [this, errorMsg]() {
                setState(CameraState::Error);
                emit connectionError(errorMsg);
            }, Qt::QueuedConnection);
        } });
    }

    void CameraController::disconnectCamera()
    {
        QtConcurrent::run([this]()
                          {
        // 使用 QMetaObject::invokeMethod 確保狀態轉換在主線程執行
        bool transitionOk = false;
        QMetaObject::invokeMethod(this, [this, &transitionOk]() {
            transitionOk = transitionTo(CameraState::Disconnecting);
        }, Qt::BlockingQueuedConnection);
        
        if (!transitionOk) {
            return;
        }

        // 先停止抓取（如果正在抓取）
        if (m_grabWorker) {
            m_grabWorker->stopGrabbing();
            // 在主線程斷開信號連接
            QMetaObject::invokeMethod(this, [this]() {
                if (m_grabWorker) m_grabWorker->disconnect();
            }, Qt::BlockingQueuedConnection);
        }

        if (m_grabThread) {
            // 在主線程斷開信號連接
            QMetaObject::invokeMethod(this, [this]() {
                if (m_grabThread) m_grabThread->disconnect();
            }, Qt::BlockingQueuedConnection);
            
            if (m_grabThread->isRunning()) {
                m_grabThread->quit();
                if (!m_grabThread->wait(3000)) {
                    qWarning() << "[CameraController] 抓取線程等待超時";
                }
            }
        }

        // 先清理線程和 worker（在主線程執行）
        QMetaObject::invokeMethod(this, [this]() {
            m_grabWorker.reset();
            m_grabThread.reset();
        }, Qt::BlockingQueuedConnection);

        // 再關閉相機
        if (m_camera && m_camera->IsOpen()) {
            m_camera->Close();
        }
        m_camera.reset();

        // 使用 QMetaObject::invokeMethod 確保狀態更新和信號發射在主線程
        QMetaObject::invokeMethod(this, [this]() {
            setState(CameraState::Disconnected);
            emit disconnected();
            qDebug() << "[CameraController] 相機已斷開";
        }, Qt::QueuedConnection); });
    }

    void CameraController::startGrabbing()
    {
        if (!transitionTo(CameraState::StartingGrab))
        {
            emit grabError("無法從當前狀態開始抓取");
            return;
        }

        // 創建抓取線程
        m_grabThread = std::make_unique<QThread>();
        m_grabWorker = std::make_unique<GrabWorker>(m_camera.get());
        m_grabWorker->moveToThread(m_grabThread.get());

        // 連接信號（明確使用 Qt::QueuedConnection 確保跨線程安全）
        connect(m_grabThread.get(), &QThread::started,
                m_grabWorker.get(), &GrabWorker::startGrabbing,
                Qt::QueuedConnection);
        connect(m_grabWorker.get(), &GrabWorker::frameGrabbed,
                this, &CameraController::onFrameGrabbed,
                Qt::QueuedConnection);
        connect(m_grabWorker.get(), &GrabWorker::grabError,
                this, &CameraController::onGrabError,
                Qt::QueuedConnection);
        connect(m_grabWorker.get(), &GrabWorker::grabStopped,
                this, &CameraController::onGrabStopped,
                Qt::QueuedConnection);

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
        if (!transitionTo(CameraState::StoppingGrab))
        {
            return;
        }

        // 發送停止請求（非阻塞）
        if (m_grabWorker)
        {
            m_grabWorker->stopGrabbing();
        }

        // 線程會自己結束並發出 grabStopped 信號
        qDebug() << "[CameraController] 已發送停止抓取請求";
    }

    void CameraController::setExposure(double exposureUs)
    {
        if (!m_camera || !m_camera->IsOpen())
        {
            return;
        }

        try
        {
            m_exposureTime = exposureUs;

            // 確保手動曝光模式
            GenApi::INodeMap &nodemap = m_camera->GetNodeMap();

            GenApi::CEnumerationPtr exposureAuto(nodemap.GetNode("ExposureAuto"));
            if (exposureAuto.IsValid())
            {
                exposureAuto->FromString("Off");
            }

            GenApi::CFloatPtr exposureTime(nodemap.GetNode("ExposureTime"));
            if (exposureTime.IsValid())
            {
                exposureTime->SetValue(exposureUs);
            }

            qDebug() << "[CameraController] 曝光時間設置為:" << exposureUs << "us";
        }
        catch (const Pylon::GenericException &e)
        {
            qWarning() << "[CameraController] 設置曝光失敗:" << e.GetDescription();
        }
    }

    // ============================================================================
    // 私有槽函數
    // ============================================================================

    void CameraController::onFrameGrabbed(const cv::Mat &frame, qint64 timestamp)
    {
        static int grabCount = 0;
        grabCount++;
        if (grabCount == 1 || grabCount % 100 == 0)
        {
            qDebug() << "[CameraController::onFrameGrabbed] 收到 #" << grabCount;
        }

        // 更新統計
        m_totalFrames.fetch_add(1);

        {
            QMutexLocker locker(&m_statsMutex);
            m_frameTimes.push_back(timestamp);

            // 保留最近 60 幀的時間戳
            while (m_frameTimes.size() > 60)
            {
                m_frameTimes.pop_front();
            }

            // 計算 FPS
            if (m_frameTimes.size() >= 2)
            {
                qint64 timeDiff = m_frameTimes.back() - m_frameTimes.front();
                if (timeDiff > 0)
                {
                    double fps = (m_frameTimes.size() - 1) * 1000.0 / timeDiff;
                    m_currentFps.store(fps);
                    emit fpsUpdated(fps);
                }
            }
        }

        // 發送幀給 UI
        emit frameReady(frame);
    }

    void CameraController::onGrabError(const QString &error)
    {
        qWarning() << "[CameraController] 抓取錯誤:" << error;
        setState(CameraState::Error);
        emit grabError(error);
    }

    void CameraController::onGrabStopped()
    {
        // 清理線程
        if (m_grabThread && m_grabThread->isRunning())
        {
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
        if (!m_camera || !m_camera->IsOpen())
        {
            return;
        }

        try
        {
            GenApi::INodeMap &nodemap = m_camera->GetNodeMap();

            // ========== 圖像解析度設置（與 Python 版本一致）==========
            // 使用低解析度，減少 GigE 傳輸負擔
            GenApi::CIntegerPtr width(nodemap.GetNode("Width"));
            GenApi::CIntegerPtr height(nodemap.GetNode("Height"));
            if (width.IsValid() && height.IsValid())
            {
                width->SetValue(640);
                height->SetValue(480);
                qDebug() << "[CameraController] 解析度設置: 640x480";
            }

            // ========== GigE 傳輸優化 ==========
            // 先嘗試自動發現最佳封包大小（使用 Pylon 的 GigE 功能）
            GenApi::CIntegerPtr packetSize(nodemap.GetNode("GevSCPSPacketSize"));
            if (packetSize.IsValid())
            {
                // 嘗試使用 1500 標準 MTU (大多數網卡都支援)
                // 如果網卡支援 Jumbo frames，可以增加到 8000-9000
                int64_t targetPacketSize = 1500;

                // 檢查範圍
                int64_t minSize = packetSize->GetMin();
                int64_t maxSize = packetSize->GetMax();
                qDebug() << "[CameraController] Packet Size 範圍:" << minSize << "-" << maxSize;

                // 使用較小的安全值
                if (targetPacketSize < minSize)
                    targetPacketSize = minSize;
                if (targetPacketSize > maxSize)
                    targetPacketSize = maxSize;

                packetSize->SetValue(targetPacketSize);
                qDebug() << "[CameraController] GevSCPSPacketSize:" << packetSize->GetValue();
            }

            // Inter-Packet Delay (增大延遲確保穩定傳輸)
            GenApi::CIntegerPtr interPacketDelay(nodemap.GetNode("GevSCPD"));
            if (interPacketDelay.IsValid())
            {
                // 增加到 5000 ticks 以確保穩定傳輸
                interPacketDelay->SetValue(5000);
                qDebug() << "[CameraController] GevSCPD:" << interPacketDelay->GetValue();
            }

            // 設置像素格式為 Mono8
            GenApi::CEnumerationPtr pixelFormat(nodemap.GetNode("PixelFormat"));
            if (pixelFormat.IsValid())
            {
                pixelFormat->FromString("Mono8");
            }

            // ========== 曝光設置 ==========
            GenApi::CEnumerationPtr exposureAuto(nodemap.GetNode("ExposureAuto"));
            if (exposureAuto.IsValid())
            {
                exposureAuto->FromString("Off");
            }

            GenApi::CFloatPtr exposureTime(nodemap.GetNode("ExposureTime"));
            if (exposureTime.IsValid())
            {
                exposureTime->SetValue(m_exposureTime);
            }

            // ========== 幀率控制 ==========
            GenApi::CBooleanPtr fpsEnable(nodemap.GetNode("AcquisitionFrameRateEnable"));
            if (fpsEnable.IsValid())
            {
                fpsEnable->SetValue(true);
            }

            GenApi::CFloatPtr fps(nodemap.GetNode("AcquisitionFrameRate"));
            if (fps.IsValid())
            {
                fps->SetValue(m_targetFps);
            }

            qDebug() << "[CameraController] 相機配置完成";
        }
        catch (const Pylon::GenericException &e)
        {
            qWarning() << "[CameraController] 配置警告:" << e.GetDescription();
        }
    }

} // namespace basler

#else // NO_PYLON_SDK - Stub implementations for CI builds

namespace basler
{

    // ============================================================================
    // Stub CameraController (for builds without Pylon SDK)
    // ============================================================================

    CameraController::CameraController(QObject *parent)
        : QObject(parent)
    {
        qRegisterMetaType<CameraState>("CameraState");
        qRegisterMetaType<CameraInfo>("CameraInfo");
        qRegisterMetaType<cv::Mat>("cv::Mat");
        qDebug() << "[CameraController] 初始化完成 (NO_PYLON_SDK stub)";
    }

    CameraController::~CameraController()
    {
        qDebug() << "[CameraController] 資源已清理 (NO_PYLON_SDK stub)";
    }

    bool CameraController::isConnected() const { return false; }
    bool CameraController::isGrabbing() const { return false; }

    void CameraController::setState(CameraState newState)
    {
        CameraState oldState = m_state.exchange(newState);
        if (oldState != newState)
        {
            emit stateChanged(newState);
        }
    }

    bool CameraController::transitionTo(CameraState newState)
    {
        setState(newState);
        return true;
    }

    QList<CameraInfo> CameraController::detectCameras()
    {
        qWarning() << "[CameraController] Pylon SDK not available - no cameras detected";
        return QList<CameraInfo>();
    }

    void CameraController::connectCamera(int cameraIndex)
    {
        Q_UNUSED(cameraIndex);
        qWarning() << "[CameraController] Pylon SDK not available - cannot connect";
        emit connectionError("Pylon SDK not available (NO_PYLON_SDK build)");
    }

    void CameraController::disconnectCamera()
    {
        setState(CameraState::Disconnected);
        emit disconnected();
    }

    void CameraController::startGrabbing()
    {
        qWarning() << "[CameraController] Pylon SDK not available - cannot grab";
        emit grabError("Pylon SDK not available (NO_PYLON_SDK build)");
    }

    void CameraController::stopGrabbing()
    {
        emit grabbingStopped();
    }

    void CameraController::setExposure(double exposureUs)
    {
        Q_UNUSED(exposureUs);
        qWarning() << "[CameraController] Pylon SDK not available - cannot set exposure";
    }

    void CameraController::onFrameGrabbed(const cv::Mat &frame, qint64 timestamp)
    {
        Q_UNUSED(frame);
        Q_UNUSED(timestamp);
    }

    void CameraController::onGrabError(const QString &error)
    {
        emit grabError(error);
    }

    void CameraController::onGrabStopped()
    {
        emit grabbingStopped();
    }

    void CameraController::configureCamera()
    {
        qWarning() << "[CameraController] Pylon SDK not available - cannot configure";
    }

} // namespace basler

#endif // NO_PYLON_SDK
