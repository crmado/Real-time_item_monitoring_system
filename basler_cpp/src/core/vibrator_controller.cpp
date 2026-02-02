#include "core/vibrator_controller.h"
#include "core/detection_controller.h"  // for VibratorSpeed enum
#include <QDebug>

namespace basler {

// ============================================================================
// VibratorControllerBase 實現
// ============================================================================

VibratorControllerBase::VibratorControllerBase(const QString& name, QObject* parent)
    : QObject(parent)
    , m_name(name)
{
}

void VibratorControllerBase::setSpeed(VibratorSpeed speed)
{
    // 將枚舉轉換為百分比
    int percent = static_cast<int>(speed);
    setSpeedPercent(percent);
}

// ============================================================================
// SimulatedVibratorController 實現
// ============================================================================

SimulatedVibratorController::SimulatedVibratorController(const QString& name, QObject* parent)
    : VibratorControllerBase(name, parent)
{
    qDebug() << "[SimulatedVibratorController] 創建模擬震動機:" << name;
}

void SimulatedVibratorController::start()
{
    if (m_isRunning) {
        qDebug() << "[" << m_name << "] 已經在運行中";
        return;
    }

    m_isRunning = true;
    qDebug() << "[" << m_name << "] 啟動 (模擬), 速度:" << m_speedPercent << "%";
    emit runningStateChanged(true);
}

void SimulatedVibratorController::stop()
{
    if (!m_isRunning) {
        qDebug() << "[" << m_name << "] 已經停止";
        return;
    }

    m_isRunning = false;
    qDebug() << "[" << m_name << "] 停止 (模擬)";
    emit runningStateChanged(false);
}

void SimulatedVibratorController::setSpeedPercent(int percent)
{
    // 限制範圍 0-100
    percent = qBound(0, percent, 100);

    if (m_speedPercent == percent) {
        return;
    }

    m_speedPercent = percent;
    qDebug() << "[" << m_name << "] 設置速度:" << percent << "% (模擬)";
    emit speedChanged(percent);
}

// ============================================================================
// DualVibratorManager 實現
// ============================================================================

DualVibratorManager::DualVibratorManager(
    std::unique_ptr<VibratorControllerBase> vibrator1,
    std::unique_ptr<VibratorControllerBase> vibrator2,
    QObject* parent)
    : QObject(parent)
    , m_vibrator1(std::move(vibrator1))
    , m_vibrator2(std::move(vibrator2))
{
    // 連接子震動機的信號
    if (m_vibrator1) {
        connect(m_vibrator1.get(), &VibratorControllerBase::runningStateChanged,
                this, [this](bool running) {
            // 只有當兩個震動機都停止時才發送停止信號
            bool newState = running || (m_vibrator2 && m_vibrator2->isRunning());
            if (m_isRunning != newState) {
                m_isRunning = newState;
                emit runningStateChanged(m_isRunning);
            }
        });

        connect(m_vibrator1.get(), &VibratorControllerBase::error,
                this, [this](const QString& msg) {
            qWarning() << "[DualVibratorManager] 震動機1錯誤:" << msg;
        });
    }

    if (m_vibrator2) {
        connect(m_vibrator2.get(), &VibratorControllerBase::runningStateChanged,
                this, [this](bool running) {
            bool newState = running || (m_vibrator1 && m_vibrator1->isRunning());
            if (m_isRunning != newState) {
                m_isRunning = newState;
                emit runningStateChanged(m_isRunning);
            }
        });

        connect(m_vibrator2.get(), &VibratorControllerBase::error,
                this, [this](const QString& msg) {
            qWarning() << "[DualVibratorManager] 震動機2錯誤:" << msg;
        });
    }

    qDebug() << "[DualVibratorManager] 創建雙震動機管理器";
}

DualVibratorManager::DualStatus DualVibratorManager::getStatus() const
{
    DualStatus status{};

    if (m_vibrator1) {
        status.vibrator1.isRunning = m_vibrator1->isRunning();
        status.vibrator1.speedPercent = m_vibrator1->speedPercent();
    }

    if (m_vibrator2) {
        status.vibrator2.isRunning = m_vibrator2->isRunning();
        status.vibrator2.speedPercent = m_vibrator2->speedPercent();
    }

    return status;
}

void DualVibratorManager::start()
{
    qDebug() << "[DualVibratorManager] 啟動兩個震動機";

    if (m_vibrator1) {
        m_vibrator1->start();
    }
    if (m_vibrator2) {
        m_vibrator2->start();
    }

    m_isRunning = true;
}

void DualVibratorManager::stop()
{
    qDebug() << "[DualVibratorManager] 停止兩個震動機";

    if (m_vibrator1) {
        m_vibrator1->stop();
    }
    if (m_vibrator2) {
        m_vibrator2->stop();
    }

    m_isRunning = false;
}

void DualVibratorManager::setSpeed(VibratorSpeed speed)
{
    qDebug() << "[DualVibratorManager] 設置速度:" << static_cast<int>(speed) << "%";

    if (m_vibrator1) {
        m_vibrator1->setSpeed(speed);
    }
    if (m_vibrator2) {
        m_vibrator2->setSpeed(speed);
    }

    emit speedChanged(speed);
}

void DualVibratorManager::setSpeedPercent(int percent)
{
    qDebug() << "[DualVibratorManager] 設置速度:" << percent << "%";

    if (m_vibrator1) {
        m_vibrator1->setSpeedPercent(percent);
    }
    if (m_vibrator2) {
        m_vibrator2->setSpeedPercent(percent);
    }
}

// ============================================================================
// 工廠函數實現
// ============================================================================

std::unique_ptr<VibratorControllerBase> createVibratorController(
    const QString& type,
    const QString& name)
{
    if (type == "simulated" || type.isEmpty()) {
        return std::make_unique<SimulatedVibratorController>(name);
    }
    else if (type == "hardware") {
        // TODO: 實現實際硬體控制器
        // 目前返回模擬控制器並發出警告
        qWarning() << "[createVibratorController] 硬體控制器尚未實現，使用模擬控制器";
        return std::make_unique<SimulatedVibratorController>(name + " (simulated)");
    }
    else {
        qWarning() << "[createVibratorController] 未知類型:" << type << "，使用模擬控制器";
        return std::make_unique<SimulatedVibratorController>(name);
    }
}

std::unique_ptr<DualVibratorManager> createDualVibratorManager(
    const QString& controllerType,
    const QString& name1,
    const QString& name2)
{
    auto vibrator1 = createVibratorController(controllerType, name1);
    auto vibrator2 = createVibratorController(controllerType, name2);

    return std::make_unique<DualVibratorManager>(
        std::move(vibrator1),
        std::move(vibrator2)
    );
}

} // namespace basler
