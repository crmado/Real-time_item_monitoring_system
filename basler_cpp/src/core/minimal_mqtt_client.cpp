#include "core/minimal_mqtt_client.h"
#include <QSslConfiguration>
#include <QDebug>

namespace basler {

// ============================================================================
// 建構 / 解構
// ============================================================================

MinimalMqttClient::MinimalMqttClient(QObject* parent)
    : QObject(parent)
{
    m_socket = new QSslSocket(this);

    // TCP 層連線完成（非 SSL 路徑用）
    // 注意：SSL 時 connected 比 encrypted 早觸發，isEncrypted() 此時仍為 false
    // 因此必須用 m_useSsl 旗標而非 isEncrypted() 來區分，避免雙重 CONNECT
    connect(m_socket, &QAbstractSocket::connected,
            this, [this]() {
        if (!m_useSsl) onSocketReady();  // 純 TCP：直接進入 MQTT 握手
    });

    // SSL 握手完成（SSL 路徑用）
    connect(m_socket, &QSslSocket::encrypted,
            this, &MinimalMqttClient::onSocketReady);

    connect(m_socket, &QAbstractSocket::disconnected,
            this, &MinimalMqttClient::onSocketDisconnected);

    connect(m_socket, &QAbstractSocket::errorOccurred,
            this, &MinimalMqttClient::onSocketError);

    connect(m_socket, &QIODevice::readyRead,
            this, &MinimalMqttClient::onReadyRead);

    // SSL 錯誤：一律忽略（EMQX 自簽憑證、IP 與 hostname 不符等情況）
    connect(m_socket, &QSslSocket::sslErrors,
            this, [this](const QList<QSslError>& errors) {
        QStringList msgs;
        for (const auto& e : errors) msgs << e.errorString();
        qWarning() << "[MinimalMqttClient] SSL 警告（已忽略）:" << msgs.join("; ");
        m_socket->ignoreSslErrors(errors);  // 忽略本次連線的所有 SSL 錯誤
    });

    // Keepalive 定時器：30 秒發一次 PINGREQ
    m_pingTimer = new QTimer(this);
    m_pingTimer->setInterval(30000);
    connect(m_pingTimer, &QTimer::timeout,
            this, &MinimalMqttClient::onPingTimer);
}

MinimalMqttClient::~MinimalMqttClient()
{
    disconnectFromHost();
}

// ============================================================================
// 連線管理
// ============================================================================

void MinimalMqttClient::connectToHost(
    const QString& host, quint16 port,
    const QString& clientId,
    const QString& username, const QString& password,
    bool useSsl)
{
    if (m_state != Disconnected) {
        qWarning() << "[MinimalMqttClient] 已在連線中，請先斷開";
        return;
    }

    m_clientId = clientId;
    m_username = username;
    m_password = password;
    m_useSsl   = useSsl;
    m_state    = Connecting;
    m_readBuf.clear();

    qDebug() << "[MinimalMqttClient] 連接至" << host << ":" << port
             << (useSsl ? "(SSL)" : "(TCP)") << "clientId:" << clientId;

    if (useSsl) {
        QSslConfiguration sslCfg = QSslConfiguration::defaultConfiguration();
        sslCfg.setProtocol(QSsl::TlsV1_2OrLater);
        sslCfg.setPeerVerifyMode(QSslSocket::VerifyNone);  // 允許自簽憑證 / IP 不匹配
        m_socket->setSslConfiguration(sslCfg);
        m_socket->setPeerVerifyMode(QSslSocket::VerifyNone);  // 雙重設定：socket 層級也關閉驗證
        m_socket->ignoreSslErrors();  // 預先忽略所有 SSL 錯誤（包含 hostname mismatch）
        m_socket->connectToHostEncrypted(host, port);
    } else {
        m_socket->connectToHost(host, port);
    }
}

void MinimalMqttClient::disconnectFromHost()
{
    m_pingTimer->stop();

    if (m_socket->state() != QAbstractSocket::UnconnectedState) {
        // 發送 MQTT DISCONNECT（0xE0, 0x00）
        m_socket->write(QByteArray("\xE0\x00", 2));
        m_socket->flush();
        m_socket->disconnectFromHost();
    }

    m_state = Disconnected;
}

// ============================================================================
// Publish（QoS 0）
// ============================================================================

bool MinimalMqttClient::publish(const QString& topic, const QByteArray& payload)
{
    if (!isConnected()) {
        qWarning() << "[MinimalMqttClient] 未連線，無法 publish topic:" << topic;
        return false;
    }

    QByteArray varHeader = encodeString(topic);  // QoS 0：無 Packet Identifier
    QByteArray remaining = varHeader + payload;

    QByteArray packet;
    packet += static_cast<char>(0x30);  // PUBLISH, QoS 0, DUP=0, RETAIN=0
    packet += encodeRemainingLength(remaining.size());
    packet += remaining;

    const qint64 written = m_socket->write(packet);
    if (written < 0) {
        emit errorOccurred("PUBLISH 寫入失敗: " + topic);
        return false;
    }
    return true;
}

// ============================================================================
// Socket Slots
// ============================================================================

void MinimalMqttClient::onSocketReady()
{
    // TCP / SSL 連線就緒 → 送出 MQTT CONNECT
    qDebug() << "[MinimalMqttClient] Socket 就緒，發送 MQTT CONNECT";
    m_socket->write(buildConnectPacket());
}

void MinimalMqttClient::onSocketDisconnected()
{
    qDebug() << "[MinimalMqttClient] Socket 斷線";
    m_pingTimer->stop();
    m_state = Disconnected;
    emit disconnected();
}

void MinimalMqttClient::onSocketError(QAbstractSocket::SocketError err)
{
    const QString msg = QString("Socket 錯誤 (%1): %2")
                            .arg(static_cast<int>(err))
                            .arg(m_socket->errorString());
    qWarning() << "[MinimalMqttClient]" << msg;
    m_state = Disconnected;
    emit errorOccurred(msg);
}

void MinimalMqttClient::onReadyRead()
{
    m_readBuf += m_socket->readAll();

    // 解析封包（可能一次收到多個或分片）
    while (m_readBuf.size() >= 2) {
        const quint8 firstByte = static_cast<quint8>(m_readBuf[0]);

        // 解碼剩餘長度（可變長度編碼）
        int pos        = 1;
        int remaining  = 0;
        int multiplier = 1;
        bool hasMore   = true;

        while (pos < m_readBuf.size() && hasMore) {
            const quint8 b = static_cast<quint8>(m_readBuf[pos++]);
            remaining += (b & 0x7F) * multiplier;
            multiplier *= 128;
            hasMore = (b & 0x80) != 0;
        }

        if (hasMore) break;  // 剩餘長度字節不完整，等待更多數據

        const int totalLen = pos + remaining;
        if (m_readBuf.size() < totalLen) break;  // 封包資料不完整

        const QByteArray body = m_readBuf.mid(pos, remaining);
        m_readBuf = m_readBuf.mid(totalLen);

        handleIncomingPacket(firstByte, body);  // 傳 firstByte 供 PUBLISH QoS 判斷
    }
}

void MinimalMqttClient::onPingTimer()
{
    if (isConnected()) {
        m_socket->write(buildPingReq());
        qDebug() << "[MinimalMqttClient] PINGREQ sent";
    }
}

// ============================================================================
// Subscribe（QoS 0）
// ============================================================================

bool MinimalMqttClient::subscribe(const QString& topicFilter)
{
    if (!isConnected()) {
        qWarning() << "[MinimalMqttClient] 未連線，無法 subscribe:" << topicFilter;
        return false;
    }

    const quint16 pid = ++m_packetId;

    // Variable header: Packet Identifier
    QByteArray varHeader;
    varHeader += static_cast<char>((pid >> 8) & 0xFF);
    varHeader += static_cast<char>(pid & 0xFF);

    // Payload: topic filter + QoS byte
    QByteArray payload;
    payload += encodeString(topicFilter);
    payload += static_cast<char>(0x00);  // QoS 0

    const QByteArray remaining = varHeader + payload;

    QByteArray packet;
    packet += static_cast<char>(0x82);  // SUBSCRIBE（fixed header 必須帶 QoS bit）
    packet += encodeRemainingLength(remaining.size());
    packet += remaining;

    const qint64 written = m_socket->write(packet);
    if (written < 0) {
        emit errorOccurred("SUBSCRIBE 寫入失敗: " + topicFilter);
        return false;
    }
    qDebug() << "[MinimalMqttClient] SUBSCRIBE 已發送，主題:" << topicFilter;
    return true;
}

// ============================================================================
// 封包處理
// ============================================================================

void MinimalMqttClient::handleIncomingPacket(quint8 firstByte, const QByteArray& body)
{
    const quint8 packetType = (firstByte & 0xF0) >> 4;

    switch (packetType) {
    case 2: {  // CONNACK
        if (body.size() < 2) break;
        const quint8 returnCode = static_cast<quint8>(body[1]);
        if (returnCode == 0) {
            m_state = Connected;
            m_pingTimer->start();
            qDebug() << "[MinimalMqttClient] CONNACK 成功，MQTT 已連線";
            emit connected();
        } else {
            const QString err = QString("CONNACK 拒絕，錯誤碼: %1").arg(returnCode);
            qWarning() << "[MinimalMqttClient]" << err;
            m_state = Disconnected;
            emit errorOccurred(err);
        }
        break;
    }
    case 3: {  // PUBLISH（Server → Client，訂閱主題的下行訊息）
        if (body.size() < 2) break;
        const int topicLen = (static_cast<quint8>(body[0]) << 8) | static_cast<quint8>(body[1]);
        if (body.size() < 2 + topicLen) break;
        const QString topic = QString::fromUtf8(body.mid(2, topicLen));

        // QoS 從 firstByte 的 bit 2-1 取得
        const quint8 qos = (firstByte & 0x06) >> 1;
        int payloadStart = 2 + topicLen;
        if (qos > 0) payloadStart += 2;  // 跳過 Packet Identifier

        const QByteArray payload = body.mid(payloadStart);
        qDebug() << "[MinimalMqttClient] 收到訊息  主題:" << topic
                 << "  內容:" << payload;
        emit messageReceived(topic, payload);
        break;
    }
    case 9: {  // SUBACK
        if (body.size() < 3) break;
        const quint16 pid = (static_cast<quint8>(body[0]) << 8) | static_cast<quint8>(body[1]);
        const quint8 retCode = static_cast<quint8>(body[2]);
        if (retCode == 0x80) {
            qWarning() << "[MinimalMqttClient] SUBACK 失敗，PacketID:" << pid;
        } else {
            qDebug() << "[MinimalMqttClient] SUBACK 成功，PacketID:" << pid
                     << "  授予 QoS:" << retCode;
        }
        break;
    }
    case 13:  // PINGRESP
        qDebug() << "[MinimalMqttClient] PINGRESP 收到";
        break;
    default:
        qDebug() << "[MinimalMqttClient] 收到未處理封包類型:" << packetType;
        break;
    }
}

// ============================================================================
// 封包組裝工具
// ============================================================================

QByteArray MinimalMqttClient::encodeString(const QString& s)
{
    const QByteArray utf8 = s.toUtf8();
    QByteArray result;
    result += static_cast<char>((utf8.size() >> 8) & 0xFF);  // MSB
    result += static_cast<char>(utf8.size() & 0xFF);          // LSB
    result += utf8;
    return result;
}

QByteArray MinimalMqttClient::encodeRemainingLength(int len)
{
    QByteArray result;
    do {
        char byte = static_cast<char>(len & 0x7F);
        len >>= 7;
        if (len > 0) byte |= static_cast<char>(0x80);
        result += byte;
    } while (len > 0);
    return result;
}

QByteArray MinimalMqttClient::buildConnectPacket() const
{
    // Variable header
    QByteArray varHeader;
    varHeader += encodeString("MQTT");  // Protocol Name
    varHeader += static_cast<char>(0x04);  // Protocol Level (MQTT 3.1.1)

    // Connect Flags: CleanSession=1, Username=1, Password=1
    quint8 flags = 0x02;  // Clean session
    if (!m_username.isEmpty()) flags |= 0x80;
    if (!m_password.isEmpty()) flags |= 0x40;
    varHeader += static_cast<char>(flags);

    // Keep Alive: 60 秒 (0x003C)
    varHeader += static_cast<char>(0x00);
    varHeader += static_cast<char>(0x3C);

    // Payload
    QByteArray payload;
    payload += encodeString(m_clientId);
    if (!m_username.isEmpty()) payload += encodeString(m_username);
    if (!m_password.isEmpty()) payload += encodeString(m_password);

    const QByteArray remaining = varHeader + payload;

    QByteArray packet;
    packet += static_cast<char>(0x10);  // CONNECT packet type
    packet += encodeRemainingLength(remaining.size());
    packet += remaining;
    return packet;
}

QByteArray MinimalMqttClient::buildPingReq()
{
    return QByteArray("\xC0\x00", 2);
}

} // namespace basler
