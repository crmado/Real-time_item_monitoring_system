#include "core/mqtt_vibrator_controller.h"
#include "config/settings.h"
#include <QDebug>

namespace basler {

// ============================================================================
// 建構 / 解構
// ============================================================================

MqttVibratorController::MqttVibratorController(
    const QString& name,
    const QString& deviceMac,
    QObject* parent)
    : VibratorControllerBase(name, parent)
    , m_deviceMac(deviceMac)
{
    m_client = new MinimalMqttClient(this);

    // MQTT 狀態回饋 → 轉發為本類信號
    connect(m_client, &MinimalMqttClient::connected,
            this, &MqttVibratorController::mqttConnected);
    connect(m_client, &MinimalMqttClient::disconnected,
            this, &MqttVibratorController::mqttDisconnected);
    connect(m_client, &MinimalMqttClient::errorOccurred,
            this, &MqttVibratorController::mqttError);

    qDebug() << "[MqttVibratorController]" << m_name << "初始化，設備 MAC:" << m_deviceMac;
}

MqttVibratorController::~MqttVibratorController()
{
    if (m_client->isConnected())
        m_client->disconnectFromHost();
}

// ============================================================================
// MQTT 連線管理
// ============================================================================

void MqttVibratorController::connectMqtt()
{
    const auto& cfg = AppConfig::instance().mqtt();
    m_client->connectToHost(
        cfg.broker,
        static_cast<quint16>(cfg.port),
        cfg.clientId + "-" + m_name,
        cfg.username,
        cfg.password,
        cfg.useSsl
    );
}

void MqttVibratorController::disconnectMqtt()
{
    m_client->disconnectFromHost();
}

bool MqttVibratorController::isMqttConnected() const
{
    return m_client->isConnected();
}

// ============================================================================
// 直接控制（實作 VibratorControllerBase 介面）
// ============================================================================

void MqttVibratorController::start()
{
    if (m_isRunning) return;
    m_isRunning = true;
    publish(QString("vibratory/%1/cmd/run").arg(m_deviceMac), "1");
    qDebug() << "[" << m_name << "] 啟動";
    emit runningStateChanged(true);
}

void MqttVibratorController::stop()
{
    if (!m_isRunning) return;
    m_isRunning    = false;
    m_isInSlowdown = false;
    publish(QString("vibratory/%1/cmd/run").arg(m_deviceMac), "0");
    qDebug() << "[" << m_name << "] 停止";
    emit runningStateChanged(false);
}

void MqttVibratorController::setSpeedPercent(int percent)
{
    percent = qBound(0, percent, 100);
    if (m_speedPercent == percent) return;
    m_speedPercent = percent;
    publish(QString("vibratory/%1/cmd/speed").arg(m_deviceMac),
            QByteArray::number(percent));
    qDebug() << "[" << m_name << "] 設速:" << percent << "%";
    emit speedChanged(percent);
}

// ============================================================================
// 計數自動控制
// ============================================================================

void MqttVibratorController::updateByCount(int currentCount, int targetCount)
{
    if (targetCount <= 0 || !m_isRunning) return;

    const double progress = static_cast<double>(currentCount) / targetCount;

    if (progress >= 1.0) {
        qDebug() << "[" << m_name << "] 計數達標，停機";
        stop();
    } else if (progress >= kSlowdownThreshold && !m_isInSlowdown) {
        m_isInSlowdown = true;
        qDebug() << "[" << m_name << "] 進度" << currentCount << "/" << targetCount
                 << "≥90%，降速至" << kCreepSpeed << "%";
        setSpeedPercent(kCreepSpeed);
    } else if (progress < kSlowdownThreshold && m_isInSlowdown) {
        m_isInSlowdown = false;
        qDebug() << "[" << m_name << "] 計數重置，恢復正常速度:" << m_normalSpeed << "%";
        setSpeedPercent(m_normalSpeed);
    }
}

void MqttVibratorController::setNormalSpeed(int percent)
{
    m_normalSpeed = qBound(0, percent, 100);
    if (m_isRunning && !m_isInSlowdown)
        setSpeedPercent(m_normalSpeed);
}

// ============================================================================
// 私有：publish
// ============================================================================

void MqttVibratorController::publish(const QString& topic, const QByteArray& payload)
{
    if (!m_client->publish(topic, payload)) {
        qWarning() << "[" << m_name << "] publish 失敗，MQTT 未連線，topic:" << topic;
    }
}

} // namespace basler
