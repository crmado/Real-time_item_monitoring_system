#ifndef MQTT_VIBRATOR_CONTROLLER_H
#define MQTT_VIBRATOR_CONTROLLER_H

#include "core/vibrator_controller.h"
#include "core/minimal_mqtt_client.h"
#include <QString>

namespace basler {

/**
 * @brief MQTT 震動機控制器
 *
 * 透過 MQTT 協議控制實體震動機（EMQX broker，SSL，MQTT 3.1.1）
 * 使用內建 MinimalMqttClient，不依賴 Qt MQTT 模組。
 *
 * 主題格式（deviceMac = 震動機設備的 MAC，格式 "AABBCCDDEEFF"）：
 *   速度控制：vibratory/{deviceMac}/cmd/speed  payload: 0~100
 *   啟閉控制：vibratory/{deviceMac}/cmd/run    payload: 1=啟動, 0=停止
 *
 * 兩種控制模式：
 *   1. 直接控制：start() / stop() / setSpeedPercent()
 *   2. 計數自動控制：updateByCount(current, target)
 *      進度 < 90%  → 維持 normalSpeed
 *      進度 ≥ 90%  → 降速至 kCreepSpeed (< 10%)
 *      進度 ≥ 100% → 停機
 */
class MqttVibratorController : public VibratorControllerBase {
    Q_OBJECT

public:
    explicit MqttVibratorController(
        const QString& name,
        const QString& deviceMac,
        QObject* parent = nullptr
    );
    ~MqttVibratorController() override;

    // ===== 實作 VibratorControllerBase 介面 =====
    void start() override;
    void stop()  override;
    void setSpeedPercent(int percent) override;

    // ===== MQTT 連線管理 =====
    void connectMqtt();
    void disconnectMqtt();
    bool isMqttConnected() const;

    // ===== 計數自動控制 =====
    /**
     * @brief 根據當前計數自動調整速度（每次計數更新時呼叫）
     * @param currentCount 當前已計數量
     * @param targetCount  目標計數量
     */
    void updateByCount(int currentCount, int targetCount);

    // 設定計數控制下的正常運行速度（預設 100%）
    void setNormalSpeed(int percent);
    int  normalSpeed() const { return m_normalSpeed; }

    QString deviceMac() const { return m_deviceMac; }
    void setDeviceMac(const QString& mac) { m_deviceMac = mac; }

signals:
    void mqttConnected();
    void mqttDisconnected();
    void mqttError(const QString& errorMessage);

private:
    void publish(const QString& topic, const QByteArray& payload);

    MinimalMqttClient* m_client   = nullptr;
    QString            m_deviceMac;

    int  m_normalSpeed  = 100;
    bool m_isInSlowdown = false;

    static constexpr double kSlowdownThreshold = 0.90;
    static constexpr int    kCreepSpeed        = 8;
};

} // namespace basler

#endif // MQTT_VIBRATOR_CONTROLLER_H
