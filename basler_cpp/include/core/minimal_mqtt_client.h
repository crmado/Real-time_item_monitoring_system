#ifndef MINIMAL_MQTT_CLIENT_H
#define MINIMAL_MQTT_CLIENT_H

/**
 * @brief 最小化 MQTT 3.1.1 客戶端（純 QSslSocket，不依賴 Qt MQTT 模組）
 *
 * 支援功能：
 *   - SSL / 純 TCP 連線
 *   - Username / Password 認證
 *   - PUBLISH（QoS 0）
 *   - 自動 PINGREQ keepalive（30 秒）
 *
 * 不支援：Subscribe、QoS 1/2、Will（本專案只需要 publish 控制指令）
 */

#include <QObject>
#include <QSslSocket>
#include <QTimer>
#include <QString>

namespace basler {

class MinimalMqttClient : public QObject {
    Q_OBJECT

public:
    enum State { Disconnected, Connecting, Connected };

    explicit MinimalMqttClient(QObject* parent = nullptr);
    ~MinimalMqttClient() override;

    State state() const { return m_state; }
    bool isConnected() const { return m_state == Connected; }

    /**
     * @brief 連線到 MQTT Broker
     * @param host     Broker 主機
     * @param port     端口（SSL 通常 8883，TCP 通常 1883）
     * @param clientId MQTT Client ID
     * @param username 帳號
     * @param password 密碼
     * @param useSsl   是否使用 SSL/TLS
     */
    void connectToHost(const QString& host, quint16 port,
                       const QString& clientId,
                       const QString& username,
                       const QString& password,
                       bool useSsl = true);

    void disconnectFromHost();

    /**
     * @brief 發布訊息（QoS 0，fire-and-forget）
     * @return false 若未連線
     */
    bool publish(const QString& topic, const QByteArray& payload);

    /**
     * @brief 訂閱主題（QoS 0）
     * @param topicFilter 支援 MQTT 萬用字元，如 "vibratory/#"
     * @return false 若未連線
     */
    bool subscribe(const QString& topicFilter);

signals:
    void connected();
    void disconnected();
    void errorOccurred(const QString& message);

    /** 收到訂閱主題的訊息時觸發（QoS 0 / Server 下行 PUBLISH） */
    void messageReceived(const QString& topic, const QByteArray& payload);

private slots:
    void onSocketReady();          // TCP connected 或 SSL encrypted
    void onSocketDisconnected();
    void onSocketError(QAbstractSocket::SocketError error);
    void onReadyRead();
    void onPingTimer();

private:
    // MQTT 封包組裝
    static QByteArray encodeString(const QString& s);
    static QByteArray encodeRemainingLength(int len);
    QByteArray buildConnectPacket() const;
    static QByteArray buildPingReq();

    void handleIncomingPacket(quint8 firstByte, const QByteArray& body);

    QSslSocket* m_socket    = nullptr;
    QTimer*     m_pingTimer = nullptr;
    State       m_state     = Disconnected;
    bool        m_useSsl    = false;  // 記錄連線模式，避免 connected/encrypted 雙重觸發
    quint16     m_packetId  = 0;      // 遞增封包 ID（SUBSCRIBE 用）

    QString    m_clientId;
    QString    m_username;
    QString    m_password;

    QByteArray m_readBuf;  // TCP 可能分片，需要緩衝
};

} // namespace basler

#endif // MINIMAL_MQTT_CLIENT_H
