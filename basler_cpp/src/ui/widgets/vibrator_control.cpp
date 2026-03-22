#include "ui/widgets/vibrator_control.h"
#include "config/settings.h"
#include <QDebug>

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QFrame>
#include <QScrollArea>

namespace basler {

// ─────────────────────────────────────────────────────────────
// 樣式常數（沿用主視窗深色主題）
// ─────────────────────────────────────────────────────────────
static const char* kGroupStyle = R"(
    QGroupBox {
        color: #00d4ff;
        font-weight: bold;
        font-size: 10pt;
        border: 2px solid #1f3a5f;
        border-radius: 6px;
        margin-top: 8px;
        padding: 6px;
        background-color: #0a1628;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }
)";
static const char* kDevGroupStyle = R"(
    QGroupBox {
        color: #7090c0;
        font-size: 9pt;
        border: 1px solid #1a2f4a;
        border-radius: 5px;
        margin-top: 6px;
        padding: 6px 4px 4px 4px;
        background-color: #080e1e;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 3px;
    }
)";
static const char* kLabelStyle   = "color: #e0e6f1; font-size: 9pt; background: transparent;";
static const char* kTopicStyle   = "color: #44ccaa; font-size: 8pt; font-family: monospace; background: transparent;";
static const char* kEditStyle    = R"(
    QLineEdit {
        background-color: #0d1f3a;
        color: #e0e6f1;
        border: 1px solid #2a4a7a;
        border-radius: 4px;
        padding: 3px 8px;
        font-size: 10pt;
        font-family: monospace;
    }
    QLineEdit:focus { border-color: #00d4ff; }
)";
static const char* kSpinStyle    = R"(
    QSpinBox {
        background-color: #0d1f3a;
        color: #e0e6f1;
        border: 1px solid #2a4a7a;
        border-radius: 4px;
        padding: 2px 6px;
    }
    QSpinBox::up-button, QSpinBox::down-button {
        background-color: #1a3a6a;
        border: none;
        width: 16px;
    }
)";
static const char* kSliderStyle  = R"(
    QSlider::groove:horizontal {
        height: 6px;
        background: #1a3a6a;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #00d4ff;
        width: 14px;
        height: 14px;
        margin: -4px 0;
        border-radius: 7px;
    }
    QSlider::sub-page:horizontal { background: #0d7aaa; border-radius: 3px; }
)";

// ─────────────────────────────────────────────────────────────
// 建構
// ─────────────────────────────────────────────────────────────

VibratorControlWidget::VibratorControlWidget(QWidget* parent)
    : QWidget(parent)
{
    auto* root = new QVBoxLayout(this);
    root->setSpacing(8);
    root->setContentsMargins(6, 6, 6, 6);

    initConnectionGroup();
    initDeviceGroup();

    root->addWidget(
        [&]() -> QGroupBox* {
            // 找第一個 QGroupBox 子物件（連線群組）
            for (auto* c : children())
                if (auto* g = qobject_cast<QGroupBox*>(c)) return g;
            return nullptr;
        }()
    );
    root->addWidget(m_devGroup, 1);

    // 從設定載入初始設備列表
    const auto& cfg = AppConfig::instance().mqtt();
    m_brokerEdit->setText(cfg.broker);
    m_portSpin->setValue(cfg.port);
    m_sslCheck->setChecked(cfg.useSsl);

    for (const auto& mac : cfg.deviceMacs)
        addDevice(mac);
    if (m_rows.isEmpty())
        addDevice();  // 預設至少一台
}

// ─────────────────────────────────────────────────────────────
// 連線群組
// ─────────────────────────────────────────────────────────────

void VibratorControlWidget::initConnectionGroup()
{
    auto* grp = new QGroupBox("📡 MQTT 連線設定 (EMQX)");
    grp->setStyleSheet(kGroupStyle);
    auto* g = new QGridLayout(grp);
    g->setSpacing(6);

    // Row 0: Broker
    auto* lbl = new QLabel("Broker:");
    lbl->setStyleSheet(kLabelStyle);
    m_brokerEdit = new QLineEdit();
    m_brokerEdit->setPlaceholderText("www.example.com 或 IP");
    m_brokerEdit->setStyleSheet(kEditStyle);
    m_brokerEdit->setToolTip("建議填 domain name，SSL SNI 才能正確匹配憑證");
    g->addWidget(lbl,          0, 0);
    g->addWidget(m_brokerEdit, 0, 1, 1, 2);

    // Row 1: Port + SSL + 連接按鈕
    auto* portLbl = new QLabel("Port:");
    portLbl->setStyleSheet(kLabelStyle);
    m_portSpin = new QSpinBox();
    m_portSpin->setRange(1, 65535);
    m_portSpin->setValue(8883);
    m_portSpin->setFixedWidth(75);
    m_portSpin->setStyleSheet(kSpinStyle);
    m_portSpin->setToolTip("SSL: 8883  /  非 SSL: 1883");

    m_sslCheck = new QCheckBox("SSL");
    m_sslCheck->setChecked(true);
    m_sslCheck->setStyleSheet(
        "QCheckBox { color: #00d4ff; font-size: 9pt; background: transparent; }"
        "QCheckBox::indicator { width: 14px; height: 14px; }"
        "QCheckBox::indicator:checked   { background-color: #00d4ff; border: 1px solid #00d4ff; border-radius: 2px; }"
        "QCheckBox::indicator:unchecked { background-color: #0d1f3a; border: 1px solid #2a4a7a; border-radius: 2px; }");
    connect(m_sslCheck, &QCheckBox::toggled, this, [this](bool ssl) {
        m_portSpin->setValue(ssl ? 8883 : 1883);
    });

    m_connectBtn = new QPushButton("連接");
    m_connectBtn->setFixedHeight(28);
    m_connectBtn->setStyleSheet(R"(
        QPushButton {
            background-color: #0d4a7a;
            color: #e0e6f1;
            border: 1px solid #1f6aaa;
            border-radius: 4px;
            font-size: 9pt;
            font-weight: bold;
            padding: 0 12px;
        }
        QPushButton:hover   { background-color: #1e6aaa; }
        QPushButton:pressed { background-color: #0a3a5a; }
    )");
    connect(m_connectBtn, &QPushButton::clicked,
            this, &VibratorControlWidget::onConnectBtnClicked);

    auto* portRow = new QHBoxLayout();
    portRow->addWidget(portLbl);
    portRow->addWidget(m_portSpin);
    portRow->addWidget(m_sslCheck);
    portRow->addStretch();
    portRow->addWidget(m_connectBtn);
    g->addLayout(portRow, 1, 0, 1, 3);

    // Row 2: 連線狀態
    m_statusDot  = new QLabel("●");
    m_statusText = new QLabel("未連接");
    m_statusDot->setStyleSheet("color: #ff4444; font-size: 12pt; background: transparent;");
    m_statusText->setStyleSheet("color: #ff4444; font-size: 9pt; background: transparent;");
    auto* statusRow = new QHBoxLayout();
    statusRow->addWidget(m_statusDot);
    statusRow->addWidget(m_statusText);
    statusRow->addStretch();
    g->addLayout(statusRow, 2, 0, 1, 3);

    // 把這個 group 加到 this（稍後由 root layout 取用）
    grp->setParent(this);
}

// ─────────────────────────────────────────────────────────────
// 設備群組（含「新增設備」按鈕 + 動態列表）
// ─────────────────────────────────────────────────────────────

void VibratorControlWidget::initDeviceGroup()
{
    m_devGroup = new QGroupBox("🎛️ 震動機設備");
    m_devGroup->setStyleSheet(kGroupStyle);

    auto* outer = new QVBoxLayout(m_devGroup);
    outer->setSpacing(6);

    // 新增設備按鈕
    auto* addBtn = new QPushButton("＋  新增設備");
    addBtn->setFixedHeight(28);
    addBtn->setStyleSheet(R"(
        QPushButton {
            background-color: #0a2a10;
            color: #44cc44;
            border: 1px solid #226622;
            border-radius: 4px;
            font-size: 9pt;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #0f3a18; }
    )");
    connect(addBtn, &QPushButton::clicked, this, [this]() { addDevice(); });
    outer->addWidget(addBtn);

    // 捲動區：設備卡片放在這裡
    auto* scroll = new QScrollArea();
    scroll->setWidgetResizable(true);
    scroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    scroll->setStyleSheet(
        "QScrollArea { background: transparent; border: none; }"
        "QScrollBar:vertical { background: #0a1628; width: 8px; border-radius: 4px; }"
        "QScrollBar::handle:vertical { background: #2a4a7a; border-radius: 4px; }");

    auto* scrollContent = new QWidget();
    scrollContent->setStyleSheet("background: transparent;");
    m_devLayout = new QVBoxLayout(scrollContent);
    m_devLayout->setSpacing(8);
    m_devLayout->setContentsMargins(2, 2, 2, 2);
    m_devLayout->addStretch();  // stretch 在最後，新卡片插在它前面

    scroll->setWidget(scrollContent);
    outer->addWidget(scroll, 1);
}

// ─────────────────────────────────────────────────────────────
// 新增設備列
// ─────────────────────────────────────────────────────────────

void VibratorControlWidget::addDevice(const QString& mac)
{
    const int idx = m_rows.size();

    DeviceRow row;

    // 卡片 GroupBox
    row.box = new QGroupBox(QString("設備 %1").arg(idx + 1));
    row.box->setStyleSheet(kDevGroupStyle);
    auto* gl = new QGridLayout(row.box);
    gl->setSpacing(5);
    gl->setContentsMargins(8, 10, 8, 8);

    // MAC 輸入
    auto* macLbl = new QLabel("MAC:");
    macLbl->setStyleSheet(kLabelStyle);
    row.macEdit = new QLineEdit(mac);
    row.macEdit->setPlaceholderText("例：F22F77 或 AA:BB:CC:DD:EE:FF");
    row.macEdit->setStyleSheet(kEditStyle);
    row.macEdit->setToolTip("ESP8266 設備的 Wi-Fi MAC 地址（填入後主題自動更新）");

    // 刪除按鈕
    row.delBtn = new QPushButton("✕");
    row.delBtn->setFixedSize(26, 26);
    row.delBtn->setStyleSheet(R"(
        QPushButton {
            background-color: #3a0a0a;
            color: #ff6666;
            border: 1px solid #661111;
            border-radius: 4px;
            font-size: 10pt;
            font-weight: bold;
        }
        QPushButton:hover { background-color: #5a1212; }
    )");

    gl->addWidget(macLbl,      0, 0);
    gl->addWidget(row.macEdit, 0, 1);
    gl->addWidget(row.delBtn,  0, 2);

    // 主題顯示
    auto* topicLbl = new QLabel("主題:");
    topicLbl->setStyleSheet(kLabelStyle);
    QString cleanMac = mac;
    cleanMac.remove(':').remove('-');
    cleanMac = cleanMac.toUpper();
    row.topicLbl = new QLabel(
        cleanMac.isEmpty()
            ? "vibratory/(MAC)/cmd/speed"
            : QString("vibratory/%1/cmd/speed").arg(cleanMac));
    row.topicLbl->setStyleSheet(kTopicStyle);
    row.topicLbl->setTextInteractionFlags(Qt::TextSelectableByMouse);

    gl->addWidget(topicLbl,    1, 0);
    gl->addWidget(row.topicLbl, 1, 1, 1, 2);

    // 速度滑桿 + SpinBox + 發送
    auto* speedLbl = new QLabel("速度:");
    speedLbl->setStyleSheet(kLabelStyle);

    row.slider = new QSlider(Qt::Horizontal);
    row.slider->setRange(0, 100);
    row.slider->setValue(0);
    row.slider->setStyleSheet(kSliderStyle);

    row.spin = new QSpinBox();
    row.spin->setRange(0, 100);
    row.spin->setValue(0);
    row.spin->setSuffix(" %");
    row.spin->setFixedWidth(65);
    row.spin->setStyleSheet(kSpinStyle);

    row.sendBtn = new QPushButton("發送");
    row.sendBtn->setFixedSize(52, 26);
    row.sendBtn->setStyleSheet(R"(
        QPushButton {
            background-color: #0a3a5a;
            color: #00d4ff;
            border: 1px solid #1a6aaa;
            border-radius: 4px;
            font-size: 9pt;
            font-weight: bold;
        }
        QPushButton:hover   { background-color: #1a5a8a; }
        QPushButton:pressed { background-color: #082a44; }
        QPushButton:disabled { background-color: #0a1628; color: #336688; border-color: #1a2a3a; }
    )");
    row.sendBtn->setEnabled(m_isMqttConnected);

    auto* speedRow = new QHBoxLayout();
    speedRow->addWidget(row.slider, 1);
    speedRow->addWidget(row.spin);
    speedRow->addWidget(row.sendBtn);
    gl->addWidget(speedLbl, 2, 0);
    gl->addLayout(speedRow, 2, 1, 1, 2);

    // ── 信號連接 ──
    // MAC 變更 → 即時更新主題標籤（純 UI，不觸發訂閱）
    connect(row.macEdit, &QLineEdit::textChanged,
            this, [this, idx](const QString& text) {
        if (idx >= m_rows.size()) return;
        QString mac = text;
        mac.remove(':'); mac.remove('-');
        mac = mac.toUpper();
        m_rows[idx].topicLbl->setText(
            mac.isEmpty()
                ? "vibratory/(MAC)/cmd/speed"
                : QString("vibratory/%1/cmd/speed").arg(mac));
    });
    // MAC 確認完成（離開欄位或按 Enter）→ 才通知 MainWindow 更新訂閱
    connect(row.macEdit, &QLineEdit::editingFinished,
            this, [this]() {
        emit deviceListChanged(currentMacs());
    });

    // 載入已儲存的速度
    {
        const QString cleanMacKey = mac.isEmpty() ? "" :
            QString(mac).remove(':').remove('-').toUpper();
        const auto& speeds = AppConfig::instance().mqtt().deviceSpeeds;
        if (!cleanMacKey.isEmpty() && speeds.contains(cleanMacKey)) {
            const int savedSpeed = speeds.value(cleanMacKey, 0);
            qDebug() << "[VibratorControl] 載入速度" << cleanMacKey << "=" << savedSpeed;
            row.slider->setValue(savedSpeed);
            row.spin->setValue(savedSpeed);
        } else {
            qDebug() << "[VibratorControl] 無儲存速度" << cleanMacKey
                     << "，可用 keys:" << speeds.keys();
        }
    }

    // Slider ↔ SpinBox 雙向同步
    connect(row.slider, &QSlider::valueChanged,
            this, [this, idx](int v) {
        if (idx >= m_rows.size() || m_rows[idx].syncing) return;
        m_rows[idx].syncing = true;
        m_rows[idx].spin->setValue(v);
        m_rows[idx].syncing = false;
    });
    connect(row.spin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, [this, idx](int v) {
        if (idx >= m_rows.size() || m_rows[idx].syncing) return;
        m_rows[idx].syncing = true;
        m_rows[idx].slider->setValue(v);
        m_rows[idx].syncing = false;
    });
    // 滑桿鬆開 → 通知 MainWindow 儲存速度
    connect(row.slider, &QSlider::sliderReleased,
            this, [this, idx]() {
        if (idx >= m_rows.size()) return;
        QString mac = m_rows[idx].macEdit->text();
        mac.remove(':'); mac.remove('-'); mac = mac.toUpper();
        if (!mac.isEmpty())
            emit deviceSpeedSaved(mac, m_rows[idx].slider->value());
    });
    // SpinBox 確認（Enter 或失去焦點）→ 同樣儲存速度
    connect(row.spin, &QAbstractSpinBox::editingFinished,
            this, [this, idx]() {
        if (idx >= m_rows.size()) return;
        QString mac = m_rows[idx].macEdit->text();
        mac.remove(':'); mac.remove('-'); mac = mac.toUpper();
        if (!mac.isEmpty())
            emit deviceSpeedSaved(mac, m_rows[idx].spin->value());
    });

    // 發送按鈕 → publishRequested
    connect(row.sendBtn, &QPushButton::clicked,
            this, [this, idx]() {
        if (idx >= m_rows.size()) return;
        const QString mac = m_rows[idx].macEdit->text()
                                .remove(':').remove('-').toUpper();
        if (mac.isEmpty()) return;
        const QString topic = QString("vibratory/%1/cmd/speed").arg(mac);
        const int value = m_rows[idx].spin->value();
        emit publishRequested(topic, QByteArray::number(value));
    });

    // 刪除按鈕
    connect(row.delBtn, &QPushButton::clicked,
            this, [this, idx]() { removeDeviceAt(idx); });

    // 插入到 stretch 前
    m_devLayout->insertWidget(m_devLayout->count() - 1, row.box);
    m_rows.append(row);
}

// ─────────────────────────────────────────────────────────────
// 移除設備列
// ─────────────────────────────────────────────────────────────

void VibratorControlWidget::removeDeviceAt(int idx)
{
    if (idx < 0 || idx >= m_rows.size()) return;
    m_devLayout->removeWidget(m_rows[idx].box);
    m_rows[idx].box->deleteLater();
    m_rows.remove(idx);

    // 更新後續卡片的標題編號
    for (int i = idx; i < m_rows.size(); ++i)
        m_rows[i].box->setTitle(QString("設備 %1").arg(i + 1));

    emit deviceListChanged(currentMacs());
}

// ─────────────────────────────────────────────────────────────
// 連線按鈕點擊
// ─────────────────────────────────────────────────────────────

void VibratorControlWidget::onConnectBtnClicked()
{
    if (m_isMqttConnected) {
        emit disconnectRequested();
    } else {
        // 清除舊錯誤，顯示「連接中...」
        m_hasError = false;
        m_statusDot->setStyleSheet("color: #aaaaaa; font-size: 12pt; background: transparent;");
        m_statusText->setStyleSheet("color: #aaaaaa; font-size: 9pt; background: transparent;");
        m_statusText->setText("連接中...");
        emit connectRequested(currentBroker(), currentPort(), currentSsl());
    }
}

// ─────────────────────────────────────────────────────────────
// 狀態更新（MainWindow 呼叫）
// ─────────────────────────────────────────────────────────────

void VibratorControlWidget::setMqttConnected(bool connected)
{
    m_isMqttConnected = connected;

    if (connected) {
        m_statusDot->setStyleSheet("color: #44ff44; font-size: 12pt; background: transparent;");
        m_statusText->setStyleSheet("color: #44ff44; font-size: 9pt; background: transparent;");
        m_statusText->setText("已連接 EMQX");
        m_connectBtn->setText("斷開");
        m_hasError = false;
    } else {
        m_connectBtn->setText("連接");
        if (!m_hasError) {
            m_statusDot->setStyleSheet("color: #ff4444; font-size: 12pt; background: transparent;");
            m_statusText->setStyleSheet("color: #ff4444; font-size: 9pt; background: transparent;");
            m_statusText->setText("未連接");
        }
    }

    // 根據連線狀態啟用/停用所有設備的發送按鈕
    for (auto& row : m_rows)
        row.sendBtn->setEnabled(connected);
}

void VibratorControlWidget::showMqttError(const QString& msg)
{
    m_hasError = true;
    m_statusDot->setStyleSheet("color: #ffaa44; font-size: 12pt; background: transparent;");
    m_statusText->setStyleSheet("color: #ffaa44; font-size: 9pt; background: transparent;");
    m_statusText->setText(msg);
}

// ─────────────────────────────────────────────────────────────
// 讀取 UI 值
// ─────────────────────────────────────────────────────────────

QString VibratorControlWidget::currentBroker() const
{
    return m_brokerEdit->text().trimmed();
}

int VibratorControlWidget::currentPort() const
{
    return m_portSpin->value();
}

bool VibratorControlWidget::currentSsl() const
{
    return m_sslCheck->isChecked();
}

QStringList VibratorControlWidget::currentMacs() const
{
    QStringList macs;
    for (const auto& row : m_rows) {
        const QString mac = row.macEdit->text().remove(':').remove('-').toUpper();
        if (!mac.isEmpty()) macs << mac;
    }
    return macs;
}

// ─────────────────────────────────────────────────────────────
// 外部更新設備速度（status/online 訊息收到後由 MainWindow 呼叫）
// ─────────────────────────────────────────────────────────────

void VibratorControlWidget::setDeviceSpeed(const QString& mac, int speed)
{
    const QString cleanMac = QString(mac).remove(':').remove('-').toUpper();
    for (auto& row : m_rows) {
        const QString rowMac = row.macEdit->text().remove(':').remove('-').toUpper();
        if (rowMac == cleanMac) {
            row.syncing = true;
            row.slider->setValue(speed);
            row.spin->setValue(speed);
            row.syncing = false;
            break;
        }
    }
}

} // namespace basler
