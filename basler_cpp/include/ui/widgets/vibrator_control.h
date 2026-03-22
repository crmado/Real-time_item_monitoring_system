#ifndef VIBRATOR_CONTROL_H
#define VIBRATOR_CONTROL_H

#include <QWidget>
#include <QGroupBox>
#include <QPushButton>
#include <QLineEdit>
#include <QLabel>
#include <QSlider>
#include <QSpinBox>
#include <QCheckBox>
#include <QVBoxLayout>
#include <QVector>
#include <QStringList>

namespace basler {

/**
 * @brief 震動機 MQTT 控制面板（動態多設備版本）
 *
 * 上半部：MQTT 連線設定（Broker / Port / SSL）
 * 下半部：動態設備列表，每台設備：
 *   - MAC 輸入
 *   - 主題顯示（vibratory/{MAC}/cmd/speed）
 *   - 速度滑桿 + SpinBox + 發送按鈕
 *   - 移除按鈕
 *
 * Widget 本身不持有 MinimalMqttClient，透過信號通知 MainWindow 操作。
 */
class VibratorControlWidget : public QWidget {
    Q_OBJECT

public:
    explicit VibratorControlWidget(QWidget* parent = nullptr);

    // ── MainWindow 呼叫：更新連線狀態 ──
    void setMqttConnected(bool connected);
    void showMqttError(const QString& msg);

    // 從外部設定某台設備的速度（status/online 訊息收到後呼叫）
    void setDeviceSpeed(const QString& mac, int speed);

    // ── 讀取 UI 值（供 MainWindow 存取）──
    QString     currentBroker() const;
    int         currentPort()   const;
    bool        currentSsl()    const;
    QStringList currentMacs()   const;  // 所有設備 MAC 列表

signals:
    // MQTT 連線
    void connectRequested(const QString& broker, int port, bool useSsl);
    void disconnectRequested();

    // 發布請求（topic = 完整 MQTT 主題，payload = 數值字串）
    void publishRequested(const QString& topic, const QByteArray& payload);

    // 設備列表變更（供 MainWindow 儲存設定）
    void deviceListChanged(const QStringList& macs);

    // 用戶調整速度並鬆開滑桿時，通知 MainWindow 儲存
    void deviceSpeedSaved(const QString& mac, int speed);

private slots:
    void onConnectBtnClicked();
    void addDevice(const QString& mac = QString());

private:
    void initConnectionGroup();
    void initDeviceGroup();
    void removeDeviceAt(int idx);
    void refreshDeviceBoxTitle(int idx);

    // ── 每台設備的 UI 元件 ──
    struct DeviceRow {
        QGroupBox*   box      = nullptr;
        QLineEdit*   macEdit  = nullptr;
        QLabel*      topicLbl = nullptr;  // 顯示 vibratory/{MAC}/cmd/speed
        QSlider*     slider   = nullptr;
        QSpinBox*    spin     = nullptr;
        QPushButton* sendBtn  = nullptr;
        QPushButton* delBtn   = nullptr;
        bool syncing = false;
    };

    // ── 連線群組 ──
    QLineEdit*   m_brokerEdit       = nullptr;
    QSpinBox*    m_portSpin         = nullptr;
    QCheckBox*   m_sslCheck         = nullptr;
    QPushButton* m_connectBtn       = nullptr;
    QLabel*      m_statusDot        = nullptr;
    QLabel*      m_statusText       = nullptr;
    bool         m_isMqttConnected  = false;
    bool         m_hasError         = false;

    // ── 設備列表 ──
    QGroupBox*   m_devGroup    = nullptr;
    QVBoxLayout* m_devLayout   = nullptr;  // 設備卡片容器
    QVector<DeviceRow> m_rows;
};

} // namespace basler

#endif // VIBRATOR_CONTROL_H
