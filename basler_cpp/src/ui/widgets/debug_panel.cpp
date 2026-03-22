#include "ui/widgets/debug_panel.h"
#include "config/settings.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QFormLayout>
#include <QPainter>
#include <QInputDialog>
#include <QMessageBox>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QStandardPaths>
#include <QCoreApplication>
#include <QRegularExpression>
#include <QTextEdit>
#include <QScrollBar>
#include <QTime>
#include <QDate>
#include <QTextStream>
#include <opencv2/imgproc.hpp>

namespace basler {

DebugPanelWidget::DebugPanelWidget(QWidget* parent)
    : QWidget(parent)
{
    initUi();
}

void DebugPanelWidget::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);
    mainLayout->setSpacing(4);
    mainLayout->setContentsMargins(4, 4, 4, 4);

    // 創建滾動區域
    m_scrollArea = new QScrollArea();
    m_scrollArea->setWidgetResizable(true);
    m_scrollArea->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);

    QWidget* scrollContent = new QWidget();
    QVBoxLayout* scrollLayout = new QVBoxLayout(scrollContent);
    scrollLayout->setSpacing(4);

    // Profile 預設模板群組（不受鎖定影響，始終可操作）
    scrollLayout->addWidget(createProfileGroup());

    // 參數鎖定 checkbox（預設鎖定，防止滑鼠滾輪誤改參數）
    m_lockParamsCheck = new QCheckBox(tr("🔒 鎖定參數"));
    m_lockParamsCheck->setChecked(true);
    m_lockParamsCheck->setStyleSheet("QCheckBox { font-weight: bold; padding: 4px; }");
    connect(m_lockParamsCheck, &QCheckBox::toggled,
            this, &DebugPanelWidget::onLockParamsChanged);
    scrollLayout->addWidget(m_lockParamsCheck);

    // 添加各個參數組（受鎖定控制的）
    QWidget* detectionGroup = createDetectionParamsGroup();
    QWidget* bgGroup = createBgSubtractorGroup();
    QWidget* edgeGroup = createEdgeDetectionGroup();
    QWidget* morphGroup = createMorphologyGroup();
    QWidget* roiGroup = createRoiGroup();
    QWidget* gateGroup = createGateGroup();
    QWidget* perfGroup = createPerformanceGroup();

    m_paramGroupWidgets = { detectionGroup, bgGroup, edgeGroup,
                            morphGroup, roiGroup, gateGroup, perfGroup };

    scrollLayout->addWidget(detectionGroup);
    scrollLayout->addWidget(bgGroup);
    scrollLayout->addWidget(edgeGroup);
    scrollLayout->addWidget(morphGroup);
    scrollLayout->addWidget(roiGroup);
    scrollLayout->addWidget(gateGroup);
    scrollLayout->addWidget(perfGroup);

    // 以下區域不受鎖定影響（始終可操作）
    scrollLayout->addWidget(createYoloGroup());
    scrollLayout->addWidget(createDebugViewGroup());
    scrollLayout->addWidget(createOperationLogGroup());
    scrollLayout->addWidget(createVideoControlGroup());
    scrollLayout->addWidget(createActionButtonsGroup());
    scrollLayout->addStretch();

    // 初始鎖定所有參數組
    for (auto* w : m_paramGroupWidgets) {
        w->setEnabled(false);
    }

    // 操作日誌：自動記錄關鍵參數變更
    connect(this, &DebugPanelWidget::minAreaChanged,
            [this](int v){ appendLog(QString("minArea → %1").arg(v), LogLevel::Param); });
    connect(this, &DebugPanelWidget::maxAreaChanged,
            [this](int v){ appendLog(QString("maxArea → %1").arg(v), LogLevel::Param); });
    connect(this, &DebugPanelWidget::bgVarThresholdChanged,
            [this](double v){ appendLog(QString("bgVarThreshold → %1").arg(v, 0, 'f', 1), LogLevel::Param); });
    connect(this, &DebugPanelWidget::cannyLowChanged,
            [this](int v){ appendLog(QString("cannyLow → %1").arg(v), LogLevel::Param); });
    connect(this, &DebugPanelWidget::cannyHighChanged,
            [this](int v){ appendLog(QString("cannyHigh → %1").arg(v), LogLevel::Param); });
    connect(this, &DebugPanelWidget::gateLinePositionChanged,
            [this](double v){ appendLog(QString("gateLineRatio → %1").arg(v, 0, 'f', 3), LogLevel::Param); });
    connect(this, &DebugPanelWidget::roiEnabledChanged,
            [this](bool v){ appendLog(v ? "ROI → 啟用" : "ROI → 停用", LogLevel::Param); });
    connect(this, &DebugPanelWidget::profileLoaded,
            [this](const QString& name){ appendLog(QString("載入模板：%1").arg(name), LogLevel::Info); });

    m_scrollArea->setWidget(scrollContent);
    mainLayout->addWidget(m_scrollArea);
}

// ============================================================================
// Profile 預設模板管理
// ============================================================================

QString DebugPanelWidget::profileDir() const
{
    QString dir = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation)
                  + "/profiles";
    QDir().mkpath(dir);
    return dir;
}

void DebugPanelWidget::refreshProfileList()
{
    m_profileCombo->blockSignals(true);
    QString current = m_profileCombo->currentText();
    m_profileCombo->clear();

    QDir dir(profileDir());
    const auto files = dir.entryList({"*.json"}, QDir::Files, QDir::Name);
    for (const QString& file : files) {
        m_profileCombo->addItem(QFileInfo(file).baseName());
    }

    // 恢復選中項
    int idx = m_profileCombo->findText(current);
    if (idx >= 0) m_profileCombo->setCurrentIndex(idx);

    m_profileCombo->blockSignals(false);

    // 有 profile 才能載入/刪除
    bool hasItems = m_profileCombo->count() > 0;
    m_deleteProfileBtn->setEnabled(hasItems);
}

QWidget* DebugPanelWidget::createProfileGroup()
{
    QGroupBox* group = new QGroupBox(tr("📋 參數預設模板"));
    QVBoxLayout* layout = new QVBoxLayout();

    // 下拉選單 + 載入按鈕（橫排）
    QHBoxLayout* row1 = new QHBoxLayout();
    m_profileCombo = new QComboBox();
    m_profileCombo->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Fixed);
    m_profileCombo->setToolTip(tr("選擇預設模板（儲存的偵測 + 光柵設定）"));

    QPushButton* loadBtn = new QPushButton(tr("載入"));
    loadBtn->setFixedWidth(52);
    loadBtn->setStyleSheet(
        "QPushButton { background-color: #1a3a5a; color: #00d4ff; border: 1px solid #00d4ff;"
        "              border-radius: 4px; padding: 3px; }"
        "QPushButton:hover { background-color: #1e4a7a; }"
        "QPushButton:disabled { color: #555; border-color: #333; }");
    row1->addWidget(m_profileCombo, 1);
    row1->addWidget(loadBtn);

    // 儲存 + 刪除按鈕（橫排）
    QHBoxLayout* row2 = new QHBoxLayout();
    m_saveProfileBtn = new QPushButton(tr("💾 另存新模板"));
    m_saveProfileBtn->setStyleSheet(
        "QPushButton { background-color: #1a3a2a; color: #00ff80; border: 1px solid #00ff80;"
        "              border-radius: 4px; padding: 4px; }"
        "QPushButton:hover { background-color: #1e4a3a; }");

    m_deleteProfileBtn = new QPushButton(tr("🗑 刪除"));
    m_deleteProfileBtn->setFixedWidth(60);
    m_deleteProfileBtn->setEnabled(false);
    m_deleteProfileBtn->setStyleSheet(
        "QPushButton { background-color: #3a1a1a; color: #ff4444; border: 1px solid #ff4444;"
        "              border-radius: 4px; padding: 4px; }"
        "QPushButton:hover { background-color: #4a1a1a; }"
        "QPushButton:disabled { color: #555; border-color: #333; }");
    row2->addWidget(m_saveProfileBtn, 1);
    row2->addWidget(m_deleteProfileBtn);

    layout->addLayout(row1);
    layout->addLayout(row2);
    group->setLayout(layout);

    // 初始化列表
    refreshProfileList();

    // ===== 連接按鈕 =====
    connect(loadBtn, &QPushButton::clicked, this, [this]()
    {
        if (m_profileCombo->count() == 0) return;
        QString name = m_profileCombo->currentText();
        QString path = profileDir() + "/" + name + ".json";

        QFile f(path);
        if (!f.open(QIODevice::ReadOnly)) {
            QMessageBox::warning(this, tr("載入失敗"), tr("無法讀取檔案：%1").arg(path));
            return;
        }
        QJsonDocument doc = QJsonDocument::fromJson(f.readAll());
        f.close();
        if (!doc.isObject()) return;

        QJsonObject root = doc.object();
        // 更新 Settings（只覆蓋 detection + gate）
        auto& s = Settings::instance();
        if (root.contains("detection"))
            s.detection() = DetectionConfig::fromJson(root["detection"].toObject());
        if (root.contains("gate"))
            s.gate() = GateConfig::fromJson(root["gate"].toObject());

        // 同步 SpinBox 顯示
        syncFromConfig();
        emit profileLoaded(name);
    });

    connect(m_saveProfileBtn, &QPushButton::clicked, this, [this]()
    {
        bool ok = false;
        QString name = QInputDialog::getText(this, tr("儲存模板"),
                                             tr("模板名稱（不含副檔名）："),
                                             QLineEdit::Normal, QString(), &ok);
        if (!ok || name.trimmed().isEmpty()) return;

        // 清理非法字元
        name = name.trimmed().replace(QRegularExpression("[/\\\\:*?\"<>|]"), "_");

        QJsonObject root;
        root["detection"] = Settings::instance().detection().toJson();
        root["gate"]      = Settings::instance().gate().toJson();

        QString path = profileDir() + "/" + name + ".json";
        QFile f(path);
        if (!f.open(QIODevice::WriteOnly)) {
            QMessageBox::warning(this, tr("儲存失敗"), tr("無法寫入檔案：%1").arg(path));
            return;
        }
        f.write(QJsonDocument(root).toJson(QJsonDocument::Indented));
        f.close();

        refreshProfileList();
        // 選中剛儲存的項目
        int idx = m_profileCombo->findText(name);
        if (idx >= 0) m_profileCombo->setCurrentIndex(idx);
    });

    connect(m_deleteProfileBtn, &QPushButton::clicked, this, [this]()
    {
        if (m_profileCombo->count() == 0) return;
        QString name = m_profileCombo->currentText();
        auto reply = QMessageBox::question(this, tr("確認刪除"),
                                           tr("確定要刪除模板「%1」？").arg(name));
        if (reply != QMessageBox::Yes) return;

        QFile::remove(profileDir() + "/" + name + ".json");
        refreshProfileList();
    });

    return group;
}

// ============================================================================
// syncFromConfig — 從 Settings 更新所有 SpinBox（靜默，不觸發信號迴圈）
// ============================================================================

void DebugPanelWidget::syncFromConfig()
{
    const auto& det  = Settings::instance().detection();
    const auto& gate = Settings::instance().gate();

    auto setInt = [](QSpinBox* sb, int v) {
        sb->blockSignals(true); sb->setValue(v); sb->blockSignals(false);
    };
    auto setDbl = [](QDoubleSpinBox* sb, double v) {
        sb->blockSignals(true); sb->setValue(v); sb->blockSignals(false);
    };

    setInt(m_minAreaSpin,          det.minArea);
    setInt(m_maxAreaSpin,          det.maxArea);
    setInt(m_bgHistorySpin,        det.bgHistory);
    setInt(m_bgVarThresholdSpin,   det.bgVarThreshold);
    setDbl(m_bgLearningRateSpin,   det.bgLearningRate);
    setInt(m_cannyLowSpin,         det.cannyLowThreshold);
    setInt(m_cannyHighSpin,        det.cannyHighThreshold);
    setInt(m_morphKernelSizeSpin,  det.morphKernelSize);
    setInt(m_morphIterationsSpin,  det.morphIterations);

    m_roiEnabledCheck->blockSignals(true);
    m_roiEnabledCheck->setChecked(det.roiEnabled);
    m_roiEnabledCheck->blockSignals(false);

    setInt(m_roiXSpin,     det.roiX);
    setInt(m_roiYSpin,     det.roiY);
    setInt(m_roiWidthSpin,  det.roiWidth);  // 0 = 自動全幀寬度
    setInt(m_roiHeightSpin, det.roiHeight);

    setInt(m_gateYPositionSpin,     gate.yPosition);
    setInt(m_gateTriggerRadiusSpin, gate.triggerRadius);
    setInt(m_gateHistoryFramesSpin, gate.gateHistoryFrames);
    setDbl(m_gateLinePositionSpin,  gate.gateLinePositionRatio);
}

QWidget* DebugPanelWidget::createDetectionParamsGroup()
{
    QGroupBox* group = new QGroupBox(tr("📏 面積參數"));
    QFormLayout* layout = new QFormLayout();

    m_minAreaSpin = new QSpinBox();
    m_minAreaSpin->setRange(1, 1000);
    m_minAreaSpin->setValue(2);
    connect(m_minAreaSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onMinAreaChanged);
    layout->addRow(tr("最小面積:"), m_minAreaSpin);

    m_maxAreaSpin = new QSpinBox();
    m_maxAreaSpin->setRange(100, 50000);
    m_maxAreaSpin->setValue(3000);
    connect(m_maxAreaSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onMaxAreaChanged);
    layout->addRow(tr("最大面積:"), m_maxAreaSpin);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createBgSubtractorGroup()
{
    QGroupBox* group = new QGroupBox(tr("🎨 背景減除"));
    QFormLayout* layout = new QFormLayout();

    m_bgHistorySpin = new QSpinBox();
    m_bgHistorySpin->setRange(10, 5000);
    m_bgHistorySpin->setValue(1000);
    connect(m_bgHistorySpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onBgHistoryChanged);
    layout->addRow(tr("歷史幀數:"), m_bgHistorySpin);

    m_bgVarThresholdSpin = new QSpinBox();
    m_bgVarThresholdSpin->setRange(1, 50);
    m_bgVarThresholdSpin->setValue(3);
    connect(m_bgVarThresholdSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onBgVarThresholdChanged);
    layout->addRow(tr("變異閾值:"), m_bgVarThresholdSpin);

    m_bgLearningRateSpin = new QDoubleSpinBox();
    m_bgLearningRateSpin->setRange(0.0001, 0.1);
    m_bgLearningRateSpin->setSingleStep(0.001);
    m_bgLearningRateSpin->setDecimals(4);
    m_bgLearningRateSpin->setValue(0.001);
    connect(m_bgLearningRateSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onBgLearningRateChanged);
    layout->addRow(tr("學習率:"), m_bgLearningRateSpin);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createEdgeDetectionGroup()
{
    QGroupBox* group = new QGroupBox(tr("🔲 邊緣檢測 (Canny)"));
    QFormLayout* layout = new QFormLayout();

    m_cannyLowSpin = new QSpinBox();
    m_cannyLowSpin->setRange(1, 255);
    m_cannyLowSpin->setValue(2);
    connect(m_cannyLowSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onCannyLowChanged);
    layout->addRow(tr("低閾值:"), m_cannyLowSpin);

    m_cannyHighSpin = new QSpinBox();
    m_cannyHighSpin->setRange(1, 255);
    m_cannyHighSpin->setValue(8);
    connect(m_cannyHighSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onCannyHighChanged);
    layout->addRow(tr("高閾值:"), m_cannyHighSpin);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createMorphologyGroup()
{
    QGroupBox* group = new QGroupBox(tr("⚙️ 形態學處理"));
    QFormLayout* layout = new QFormLayout();

    m_morphKernelSizeSpin = new QSpinBox();
    m_morphKernelSizeSpin->setRange(1, 15);
    m_morphKernelSizeSpin->setSingleStep(2);  // 奇數
    m_morphKernelSizeSpin->setValue(3);
    connect(m_morphKernelSizeSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onMorphKernelSizeChanged);
    layout->addRow(tr("核大小:"), m_morphKernelSizeSpin);

    m_morphIterationsSpin = new QSpinBox();
    m_morphIterationsSpin->setRange(0, 10);
    m_morphIterationsSpin->setValue(1);
    connect(m_morphIterationsSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onMorphIterationsChanged);
    layout->addRow(tr("迭代次數:"), m_morphIterationsSpin);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createRoiGroup()
{
    QGroupBox* group = new QGroupBox(tr("📐 ROI 區域"));
    QVBoxLayout* mainLayout = new QVBoxLayout();

    m_roiEnabledCheck = new QCheckBox(tr("啟用 ROI"));
    m_roiEnabledCheck->setChecked(true);
    connect(m_roiEnabledCheck, &QCheckBox::toggled,
            this, &DebugPanelWidget::onRoiEnabledChanged);
    mainLayout->addWidget(m_roiEnabledCheck);

    QGridLayout* gridLayout = new QGridLayout();

    gridLayout->addWidget(new QLabel("X:"), 0, 0);
    m_roiXSpin = new QSpinBox();
    m_roiXSpin->setRange(0, 1920);
    m_roiXSpin->setValue(0);
    connect(m_roiXSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onRoiXChanged);
    gridLayout->addWidget(m_roiXSpin, 0, 1);

    gridLayout->addWidget(new QLabel("Y:"), 0, 2);
    m_roiYSpin = new QSpinBox();
    m_roiYSpin->setRange(0, 1080);
    m_roiYSpin->setValue(0);
    connect(m_roiYSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onRoiYChanged);
    gridLayout->addWidget(m_roiYSpin, 0, 3);

    gridLayout->addWidget(new QLabel("寬:"), 1, 0);
    m_roiWidthSpin = new QSpinBox();
    m_roiWidthSpin->setRange(0, 1920); // 0 = 自動全幀寬度
    m_roiWidthSpin->setValue(0);
    connect(m_roiWidthSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onRoiWidthChanged);
    gridLayout->addWidget(m_roiWidthSpin, 1, 1);

    gridLayout->addWidget(new QLabel("高:"), 1, 2);
    m_roiHeightSpin = new QSpinBox();
    m_roiHeightSpin->setRange(10, 1080);
    m_roiHeightSpin->setValue(150);
    connect(m_roiHeightSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onRoiHeightChanged);
    gridLayout->addWidget(m_roiHeightSpin, 1, 3);

    mainLayout->addLayout(gridLayout);

    // 拖拽框選 ROI 按鈕
    m_roiEditBtn = new QPushButton(tr("✎ 在畫面上框選 ROI"));
    m_roiEditBtn->setStyleSheet(
        "QPushButton { background-color: #1a3a5a; color: #00d4ff; border: 1px solid #00d4ff;"
        "              border-radius: 4px; padding: 5px; }"
        "QPushButton:hover { background-color: #1e4a7a; }"
        "QPushButton:pressed { background-color: #0d4a7a; }"
    );
    connect(m_roiEditBtn, &QPushButton::clicked,
            this, &DebugPanelWidget::roiEditModeRequested);
    mainLayout->addWidget(m_roiEditBtn);

    group->setLayout(mainLayout);
    return group;
}

QWidget* DebugPanelWidget::createGateGroup()
{
    QGroupBox* group = new QGroupBox(tr("🚪 虛擬光柵"));
    QFormLayout* layout = new QFormLayout();

    m_gateYPositionSpin = new QSpinBox();
    m_gateYPositionSpin->setRange(0, 1080);
    m_gateYPositionSpin->setValue(240);
    connect(m_gateYPositionSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateYPositionChanged);
    layout->addRow(tr("Y 位置:"), m_gateYPositionSpin);

    m_gateTriggerRadiusSpin = new QSpinBox();
    m_gateTriggerRadiusSpin->setRange(5, 100);
    m_gateTriggerRadiusSpin->setValue(20);
    connect(m_gateTriggerRadiusSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateTriggerRadiusChanged);
    layout->addRow(tr("觸發半徑:"), m_gateTriggerRadiusSpin);

    m_gateHistoryFramesSpin = new QSpinBox();
    m_gateHistoryFramesSpin->setRange(1, 30);
    m_gateHistoryFramesSpin->setValue(8);
    connect(m_gateHistoryFramesSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateHistoryFramesChanged);
    layout->addRow(tr("歷史幀數:"), m_gateHistoryFramesSpin);

    m_gateLinePositionSpin = new QDoubleSpinBox();
    m_gateLinePositionSpin->setRange(0.0, 1.0);
    m_gateLinePositionSpin->setSingleStep(0.05);
    m_gateLinePositionSpin->setValue(0.5);
    connect(m_gateLinePositionSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onGateLinePositionChanged);
    layout->addRow(tr("線位置比:"), m_gateLinePositionSpin);

    // 點擊畫面設定光柵線按鈕
    QVBoxLayout* outerLayout = new QVBoxLayout();
    outerLayout->addLayout(layout);

    m_gateLineEditBtn = new QPushButton(tr("🎯 點擊畫面設定光柵線"));
    m_gateLineEditBtn->setStyleSheet(
        "QPushButton { background-color: #2a2a1a; color: #ffcc00; border: 1px solid #ffcc00;"
        "              border-radius: 4px; padding: 5px; }"
        "QPushButton:hover { background-color: #3a3a1a; }"
        "QPushButton:pressed { background-color: #1a1a0a; }"
    );
    connect(m_gateLineEditBtn, &QPushButton::clicked,
            this, &DebugPanelWidget::gateLineEditModeRequested);
    outerLayout->addWidget(m_gateLineEditBtn);

    group->setLayout(outerLayout);
    return group;
}

QWidget* DebugPanelWidget::createPerformanceGroup()
{
    QGroupBox* group = new QGroupBox(tr("⚡ 性能"));
    QFormLayout* layout = new QFormLayout();

    // 處理解析度：固定寬度選項，自動適應任何相機解析度
    // 實際縮放比例 = min(1.0, 選定寬度 / 相機原生寬度)
    m_imageScaleCombo = new QComboBox();
    m_imageScaleCombo->addItems({"原生解析度", "1280px", "640px ★", "480px", "320px"});
    m_imageScaleCombo->setCurrentIndex(2);  // 默認 640px（與演算法調參基準一致）
    m_imageScaleCombo->setToolTip(tr("檢測演算法使用的處理寬度。原始影像仍以全解析度顯示。\n"
                                     "640px ★ = 演算法調參基準值，大多數場景建議使用。"));
    connect(m_imageScaleCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &DebugPanelWidget::onProcessingWidthChanged);
    layout->addRow(tr("處理解析度:"), m_imageScaleCombo);

    m_skipFramesSpin = new QSpinBox();
    m_skipFramesSpin->setRange(0, 10);
    m_skipFramesSpin->setValue(0);
    connect(m_skipFramesSpin, QOverload<int>::of(&QSpinBox::valueChanged),
            this, &DebugPanelWidget::onSkipFramesChanged);
    layout->addRow(tr("跳幀:"), m_skipFramesSpin);

    // 狀態顯示
    m_fpsLabel = new QLabel("FPS: --");
    layout->addRow(m_fpsLabel);

    m_frameCountLabel = new QLabel(tr("幀數: 0"));
    layout->addRow(m_frameCountLabel);

    m_detectionCountLabel = new QLabel(tr("檢測數: 0"));
    layout->addRow(m_detectionCountLabel);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createDebugViewGroup()
{
    QGroupBox* group = new QGroupBox(tr("🔍 調試視圖"));
    QVBoxLayout* layout = new QVBoxLayout();

    m_showDebugViewCheck = new QCheckBox(tr("顯示二值化圖像"));
    m_showDebugViewCheck->setChecked(false);
    connect(m_showDebugViewCheck, &QCheckBox::toggled,
            this, &DebugPanelWidget::onShowDebugViewChanged);
    layout->addWidget(m_showDebugViewCheck);

    // 主畫面視覺化模式（0=原始, 1=前景遮罩, 2=Canny, 3=三重聯合, 4=最終結果）
    m_debugViewModeCombo = new QComboBox();
    m_debugViewModeCombo->addItem(tr("原始幀"));
    m_debugViewModeCombo->addItem(tr("前景遮罩（背景減除）"));
    m_debugViewModeCombo->addItem(tr("Canny 邊緣"));
    m_debugViewModeCombo->addItem(tr("三重聯合結果"));
    m_debugViewModeCombo->addItem(tr("最終形態學結果"));
    m_debugViewModeCombo->setCurrentIndex(0);
    m_debugViewModeCombo->setToolTip(tr("選擇主畫面顯示的中間處理結果（需勾選顯示調試視圖）"));
    m_debugViewModeCombo->setEnabled(false);
    connect(m_debugViewModeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, [this](int index){ emit debugViewModeChanged(index); });
    layout->addWidget(m_debugViewModeCombo);

    // 分割顯示切換按鈕（並排顯示原始幀 + 選定結果，按 F9 或此按鈕切換）
    m_splitViewBtn = new QPushButton(tr("⊞ 分割顯示"));
    m_splitViewBtn->setToolTip(tr("並排顯示兩個視角（F9）\n左：選定視圖  右：互補幀"));
    m_splitViewBtn->setCheckable(true);
    m_splitViewBtn->setStyleSheet(R"(
        QPushButton { background-color: #1a1f3d; color: #e0e6f1; border: 1px solid #1f3a5f;
                      border-radius: 4px; padding: 4px; }
        QPushButton:checked { background-color: #0d4a7a; color: #00d4ff;
                              border-color: #00d4ff; }
        QPushButton:hover { background-color: #1e5a8e; }
    )");
    connect(m_splitViewBtn, &QPushButton::clicked,
            this, &DebugPanelWidget::splitViewToggleRequested);
    layout->addWidget(m_splitViewBtn);

    m_debugImageLabel = new QLabel();
    m_debugImageLabel->setFixedSize(200, 100);
    m_debugImageLabel->setStyleSheet("background-color: #1a1a1a; border: 1px solid #333;");
    m_debugImageLabel->setAlignment(Qt::AlignCenter);
    m_debugImageLabel->setText(tr("無圖像"));
    m_debugImageLabel->setVisible(false);
    layout->addWidget(m_debugImageLabel);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createVideoControlGroup()
{
    QGroupBox* group = new QGroupBox(tr("🎬 視頻控制"));
    QVBoxLayout* layout = new QVBoxLayout();

    QHBoxLayout* btnLayout1 = new QHBoxLayout();
    m_loadVideoBtn = new QPushButton(tr("載入"));
    connect(m_loadVideoBtn, &QPushButton::clicked, this, &DebugPanelWidget::loadTestVideo);
    btnLayout1->addWidget(m_loadVideoBtn);

    m_playBtn = new QPushButton(tr("▶"));
    connect(m_playBtn, &QPushButton::clicked, this, &DebugPanelWidget::playVideo);
    btnLayout1->addWidget(m_playBtn);

    m_pauseBtn = new QPushButton(tr("⏸"));
    connect(m_pauseBtn, &QPushButton::clicked, this, &DebugPanelWidget::pauseVideo);
    btnLayout1->addWidget(m_pauseBtn);
    layout->addLayout(btnLayout1);

    QHBoxLayout* btnLayout2 = new QHBoxLayout();
    m_prevFrameBtn = new QPushButton(tr("◀"));
    connect(m_prevFrameBtn, &QPushButton::clicked, this, &DebugPanelWidget::prevFrame);
    btnLayout2->addWidget(m_prevFrameBtn);

    m_jumpFrameSpin = new QSpinBox();
    m_jumpFrameSpin->setRange(0, 999999);
    btnLayout2->addWidget(m_jumpFrameSpin);

    m_jumpFrameBtn = new QPushButton(tr("跳轉"));
    connect(m_jumpFrameBtn, &QPushButton::clicked, this, [this]() {
        emit jumpToFrame(m_jumpFrameSpin->value());
    });
    btnLayout2->addWidget(m_jumpFrameBtn);

    m_nextFrameBtn = new QPushButton(tr("▶"));
    connect(m_nextFrameBtn, &QPushButton::clicked, this, &DebugPanelWidget::nextFrame);
    btnLayout2->addWidget(m_nextFrameBtn);
    layout->addLayout(btnLayout2);

    m_screenshotBtn = new QPushButton(tr("📷 截圖"));
    connect(m_screenshotBtn, &QPushButton::clicked, this, &DebugPanelWidget::screenshot);
    layout->addWidget(m_screenshotBtn);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createYoloGroup()
{
    QGroupBox* group = new QGroupBox(tr("YOLO 偵測設定"));
    group->setStyleSheet("QGroupBox { font-weight: bold; color: #00d4ff; }");
    QFormLayout* layout = new QFormLayout();

    // 偵測模式選擇
    m_yoloModeCombo = new QComboBox();
    m_yoloModeCombo->addItems({tr("傳統 (MOG2)"), tr("YOLO"), tr("自動")});
    m_yoloModeCombo->setCurrentIndex(2); // 預設自動
    connect(m_yoloModeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &DebugPanelWidget::onYoloModeChanged);
    layout->addRow(tr("偵測模式:"), m_yoloModeCombo);

    // 信心閾值
    m_yoloConfidenceSpin = new QDoubleSpinBox();
    m_yoloConfidenceSpin->setRange(0.05, 0.95);
    m_yoloConfidenceSpin->setSingleStep(0.05);
    m_yoloConfidenceSpin->setDecimals(2);
    m_yoloConfidenceSpin->setValue(0.25);
    connect(m_yoloConfidenceSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onYoloConfidenceChanged);
    layout->addRow(tr("信心閾值:"), m_yoloConfidenceSpin);

    // NMS 閾值
    m_yoloNmsSpin = new QDoubleSpinBox();
    m_yoloNmsSpin->setRange(0.1, 0.9);
    m_yoloNmsSpin->setSingleStep(0.05);
    m_yoloNmsSpin->setDecimals(2);
    m_yoloNmsSpin->setValue(0.45);
    connect(m_yoloNmsSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onYoloNmsChanged);
    layout->addRow(tr("NMS 閾值:"), m_yoloNmsSpin);

    // ROI 放大倍數
    m_yoloRoiUpscaleSpin = new QDoubleSpinBox();
    m_yoloRoiUpscaleSpin->setRange(1.0, 4.0);
    m_yoloRoiUpscaleSpin->setSingleStep(0.5);
    m_yoloRoiUpscaleSpin->setDecimals(1);
    m_yoloRoiUpscaleSpin->setValue(2.0);
    connect(m_yoloRoiUpscaleSpin, QOverload<double>::of(&QDoubleSpinBox::valueChanged),
            this, &DebugPanelWidget::onYoloRoiUpscaleChanged);
    layout->addRow(tr("ROI 放大:"), m_yoloRoiUpscaleSpin);

    // 載入模型按鈕
    m_loadYoloModelBtn = new QPushButton(tr("載入 ONNX 模型..."));
    connect(m_loadYoloModelBtn, &QPushButton::clicked,
            this, &DebugPanelWidget::loadYoloModelRequested);
    layout->addRow(m_loadYoloModelBtn);

    // 模型狀態
    m_yoloStatusLabel = new QLabel(tr("模型: 未載入"));
    m_yoloStatusLabel->setStyleSheet("color: #888;");
    layout->addRow(m_yoloStatusLabel);

    // 推理時間
    m_yoloInferenceLabel = new QLabel(tr("推理: -- ms"));
    m_yoloInferenceLabel->setStyleSheet("color: #888;");
    layout->addRow(m_yoloInferenceLabel);

    group->setLayout(layout);
    return group;
}

QWidget* DebugPanelWidget::createOperationLogGroup()
{
    QGroupBox* group = new QGroupBox();
    QVBoxLayout* outerLayout = new QVBoxLayout();
    outerLayout->setSpacing(4);
    outerLayout->setContentsMargins(6, 6, 6, 6);

    // 標題列（帶折疊按鈕 + 清除按鈕）
    QHBoxLayout* headerLayout = new QHBoxLayout();
    QLabel* titleLabel = new QLabel(tr("📋 操作日誌"));
    titleLabel->setStyleSheet("color: #00d4ff; font-weight: bold;");
    headerLayout->addWidget(titleLabel);
    headerLayout->addStretch();

    QPushButton* clearBtn = new QPushButton(tr("清除"));
    clearBtn->setMaximumWidth(48);
    clearBtn->setStyleSheet("QPushButton { background: #1a1f3d; color: #888; border: 1px solid #333;"
                            " border-radius: 3px; padding: 2px 4px; font-size: 8pt; }"
                            "QPushButton:hover { color: #e0e6f1; }");
    headerLayout->addWidget(clearBtn);

    QPushButton* collapseBtn = new QPushButton(tr("▼"));
    collapseBtn->setMaximumWidth(28);
    collapseBtn->setCheckable(true);
    collapseBtn->setStyleSheet("QPushButton { background: #1a1f3d; color: #888; border: 1px solid #333;"
                               " border-radius: 3px; padding: 2px; font-size: 9pt; }"
                               "QPushButton:checked { color: #00d4ff; }");
    headerLayout->addWidget(collapseBtn);
    outerLayout->addLayout(headerLayout);

    // 可折疊內容區
    QWidget* contentWidget = new QWidget();
    QVBoxLayout* contentLayout = new QVBoxLayout(contentWidget);
    contentLayout->setContentsMargins(0, 0, 0, 0);

    m_logTextEdit = new QTextEdit();
    m_logTextEdit->setReadOnly(true);
    m_logTextEdit->setMaximumHeight(150);
    m_logTextEdit->setMinimumHeight(60);
    m_logTextEdit->document()->setMaximumBlockCount(100); // 自動移除最舊記錄
    m_logTextEdit->setStyleSheet(R"(
        QTextEdit {
            background-color: #060810;
            color: #c0c8e0;
            border: 1px solid #1f3a5f;
            border-radius: 4px;
            font-family: "Menlo", "Consolas", monospace;
            font-size: 8pt;
        }
    )");
    contentLayout->addWidget(m_logTextEdit);
    outerLayout->addWidget(contentWidget);

    // 折疊 / 展開
    connect(collapseBtn, &QPushButton::toggled, [contentWidget, collapseBtn](bool collapsed) {
        contentWidget->setVisible(!collapsed);
        collapseBtn->setText(collapsed ? "▶" : "▼");
    });
    connect(clearBtn, &QPushButton::clicked, [this]() {
        if (m_logTextEdit) m_logTextEdit->clear();
    });

    group->setLayout(outerLayout);
    return group;
}

void DebugPanelWidget::appendLog(const QString& message, LogLevel level)
{
    if (!m_logTextEdit) return;

    const QString time = QTime::currentTime().toString("HH:mm:ss");
    QString colorStr;
    switch (level) {
        case LogLevel::Param: colorStr = "#00d4ff"; break;
        case LogLevel::Count: colorStr = "#00ff80"; break;
        case LogLevel::Error: colorStr = "#ff4444"; break;
        default:              colorStr = "#9099b0"; break;
    }

    const QString html = QString("<span style='color:#44475a'>[%1]</span>"
                                 "&nbsp;<span style='color:%2'>%3</span>")
                         .arg(time, colorStr, message.toHtmlEscaped());
    m_logTextEdit->append(html);
    // document()->setMaximumBlockCount() 已自動修剪，無需手動清除
    m_logTextEdit->verticalScrollBar()->setValue(m_logTextEdit->verticalScrollBar()->maximum());

    // 持久化：寫入專案 build/logs/operation_YYYYMMDD.log
    QString exeDir = QCoreApplication::applicationDirPath();
#ifdef Q_OS_MAC
    QDir logsDirObj(exeDir + "/../../../logs");
#else
    QDir logsDirObj(exeDir + "/logs");
#endif
    logsDirObj.mkpath(".");
    const QString logsDir = logsDirObj.absolutePath();
    const QString logFile = logsDir + "/operation_"
                            + QDate::currentDate().toString("yyyyMMdd") + ".log";
    QFile f(logFile);
    if (f.open(QIODevice::Append | QIODevice::Text)) {
        QTextStream out(&f);
        out.setEncoding(QStringConverter::Utf8);
        // 純文字格式：[HH:mm:ss] 原始訊息
        out << "[" << time << "] " << message << "\n";
    }
}

void DebugPanelWidget::logCountEvent(int count, int frame)
{
    appendLog(QString("計數 #%1（幀 %2）").arg(count).arg(frame), LogLevel::Count);
}

void DebugPanelWidget::logError(const QString& message)
{
    appendLog("⚠ " + message, LogLevel::Error);
}

QWidget* DebugPanelWidget::createActionButtonsGroup()
{
    QGroupBox* group = new QGroupBox(tr("⚙️ 操作"));
    QVBoxLayout* layout = new QVBoxLayout();

    QHBoxLayout* btnLayout = new QHBoxLayout();

    m_resetParamsBtn = new QPushButton(tr("重置參數"));
    connect(m_resetParamsBtn, &QPushButton::clicked, this, &DebugPanelWidget::resetParams);
    btnLayout->addWidget(m_resetParamsBtn);

    m_saveConfigBtn = new QPushButton(tr("儲存"));
    connect(m_saveConfigBtn, &QPushButton::clicked, this, &DebugPanelWidget::saveConfig);
    btnLayout->addWidget(m_saveConfigBtn);

    m_loadConfigBtn = new QPushButton(tr("載入"));
    connect(m_loadConfigBtn, &QPushButton::clicked, this, &DebugPanelWidget::loadConfig);
    btnLayout->addWidget(m_loadConfigBtn);

    layout->addLayout(btnLayout);

    m_resetCountBtn = new QPushButton(tr("🔄 重置總計數"));
    connect(m_resetCountBtn, &QPushButton::clicked, this, &DebugPanelWidget::resetTotalCount);
    layout->addWidget(m_resetCountBtn);

    group->setLayout(layout);
    return group;
}

// ============================================================================
// 槽函數實現
// ============================================================================

void DebugPanelWidget::updateFps(double fps)
{
    m_fpsLabel->setText(QString("FPS: %1").arg(fps, 0, 'f', 1));
}

void DebugPanelWidget::updateFrameCount(int count)
{
    m_frameCountLabel->setText(tr("幀數: %1").arg(count));
}

void DebugPanelWidget::updateDetectionCount(int count)
{
    m_detectionCountLabel->setText(tr("檢測數: %1").arg(count));
}

void DebugPanelWidget::updateDebugImage(const cv::Mat& image)
{
    if (image.empty() || !m_showDebugView) return;

    // 將 cv::Mat 轉換為 QImage
    QImage qImg;
    if (image.channels() == 1) {
        qImg = QImage(image.data, image.cols, image.rows,
                      static_cast<int>(image.step), QImage::Format_Grayscale8);
    } else if (image.channels() == 3) {
        cv::Mat rgb;
        cv::cvtColor(image, rgb, cv::COLOR_BGR2RGB);
        qImg = QImage(rgb.data, rgb.cols, rgb.rows,
                      static_cast<int>(rgb.step), QImage::Format_RGB888);
    }

    // 縮放並顯示
    QPixmap pixmap = QPixmap::fromImage(qImg).scaled(
        m_debugImageLabel->size(), Qt::KeepAspectRatio, Qt::FastTransformation);
    m_debugImageLabel->setPixmap(pixmap);
}

void DebugPanelWidget::onMinAreaChanged(int value)
{
    emit minAreaChanged(value);
    emit paramChanged("minArea", value);
}

void DebugPanelWidget::onMaxAreaChanged(int value)
{
    emit maxAreaChanged(value);
    emit paramChanged("maxArea", value);
}

void DebugPanelWidget::onBgHistoryChanged(int value)
{
    emit bgHistoryChanged(value);
    emit paramChanged("bgHistory", value);
}

void DebugPanelWidget::onBgVarThresholdChanged(int value)
{
    emit bgVarThresholdChanged(static_cast<double>(value));
    emit paramChanged("bgVarThreshold", value);
}

void DebugPanelWidget::onBgLearningRateChanged(double value)
{
    emit bgLearningRateChanged(value);
    emit paramChanged("bgLearningRate", value);
}

void DebugPanelWidget::onCannyLowChanged(int value)
{
    emit cannyLowChanged(value);
    emit paramChanged("cannyLow", value);
}

void DebugPanelWidget::onCannyHighChanged(int value)
{
    emit cannyHighChanged(value);
    emit paramChanged("cannyHigh", value);
}

void DebugPanelWidget::onMorphKernelSizeChanged(int value)
{
    // 確保為奇數
    if (value % 2 == 0) value++;
    emit morphKernelSizeChanged(value);
    emit paramChanged("morphKernelSize", value);
}

void DebugPanelWidget::onMorphIterationsChanged(int value)
{
    emit morphIterationsChanged(value);
    emit paramChanged("morphIterations", value);
}

void DebugPanelWidget::onRoiEnabledChanged(bool enabled)
{
    emit roiEnabledChanged(enabled);
    emit paramChanged("roiEnabled", enabled);
}

void DebugPanelWidget::onRoiXChanged(int value)
{
    emit roiChanged(value, m_roiYSpin->value(),
                    m_roiWidthSpin->value(), m_roiHeightSpin->value());
}

void DebugPanelWidget::onRoiYChanged(int value)
{
    emit roiChanged(m_roiXSpin->value(), value,
                    m_roiWidthSpin->value(), m_roiHeightSpin->value());
}

void DebugPanelWidget::onRoiWidthChanged(int value)
{
    emit roiChanged(m_roiXSpin->value(), m_roiYSpin->value(),
                    value, m_roiHeightSpin->value());
}

void DebugPanelWidget::onRoiHeightChanged(int value)
{
    emit roiChanged(m_roiXSpin->value(), m_roiYSpin->value(),
                    m_roiWidthSpin->value(), value);
}

void DebugPanelWidget::onGateYPositionChanged(int value)
{
    emit gateYPositionChanged(value);
    emit paramChanged("gateYPosition", value);
}

void DebugPanelWidget::onGateTriggerRadiusChanged(int value)
{
    emit gateTriggerRadiusChanged(value);
    emit paramChanged("gateTriggerRadius", value);
}

void DebugPanelWidget::onGateHistoryFramesChanged(int value)
{
    emit gateHistoryFramesChanged(value);
    emit paramChanged("gateHistoryFrames", value);
}

void DebugPanelWidget::onGateLinePositionChanged(double value)
{
    emit gateLinePositionChanged(value);
    emit paramChanged("gateLinePosition", value);
}

void DebugPanelWidget::onProcessingWidthChanged(int index)
{
    // 0=原生(0表示不縮放), 1=1280, 2=640, 3=480, 4=320
    int widths[] = {0, 1280, 640, 480, 320};
    if (index >= 0 && index < 5) {
        emit processingWidthChanged(widths[index]);
        emit paramChanged("targetProcessingWidth", widths[index]);
    }
}

void DebugPanelWidget::onSkipFramesChanged(int value)
{
    emit skipFramesChanged(value);
    emit paramChanged("skipFrames", value);
}

void DebugPanelWidget::onShowDebugViewChanged(bool show)
{
    m_showDebugView = show;
    m_debugImageLabel->setVisible(show);
    m_debugViewModeCombo->setEnabled(show);
    // 關閉調試視圖時重設為原始幀，避免主畫面停留在中間結果
    if (!show) {
        m_debugViewModeCombo->blockSignals(true);
        m_debugViewModeCombo->setCurrentIndex(0);
        m_debugViewModeCombo->blockSignals(false);
        emit debugViewModeChanged(0);
    }
    emit debugViewToggled(show);
}

void DebugPanelWidget::onLockParamsChanged(bool locked)
{
    for (auto* w : m_paramGroupWidgets) {
        w->setEnabled(!locked);
    }
}

// ============================================================================
// YOLO 槽函數
// ============================================================================

void DebugPanelWidget::onYoloModeChanged(int index)
{
    emit yoloModeChanged(index);
}

void DebugPanelWidget::onYoloConfidenceChanged(double value)
{
    emit yoloConfidenceChanged(value);
}

void DebugPanelWidget::onYoloNmsChanged(double value)
{
    emit yoloNmsThresholdChanged(value);
}

void DebugPanelWidget::onYoloRoiUpscaleChanged(double value)
{
    emit yoloRoiUpscaleChanged(value);
}

void DebugPanelWidget::updateYoloModelStatus(bool loaded)
{
    if (loaded)
    {
        m_yoloStatusLabel->setText(tr("模型: 已載入"));
        m_yoloStatusLabel->setStyleSheet("color: #00ff88; font-weight: bold;");
    }
    else
    {
        m_yoloStatusLabel->setText(tr("模型: 未載入"));
        m_yoloStatusLabel->setStyleSheet("color: #888;");
    }
}

void DebugPanelWidget::updateYoloInferenceTime(double ms)
{
    m_yoloInferenceLabel->setText(QString(tr("推理: %1 ms")).arg(ms, 0, 'f', 1));

    // 依據推理時間變色：< 30ms 綠色, < 100ms 黃色, > 100ms 紅色
    if (ms < 30.0)
    {
        m_yoloInferenceLabel->setStyleSheet("color: #00ff88;");
    }
    else if (ms < 100.0)
    {
        m_yoloInferenceLabel->setStyleSheet("color: #ffcc00;");
    }
    else
    {
        m_yoloInferenceLabel->setStyleSheet("color: #ff4444;");
    }
}

void DebugPanelWidget::setRoiValues(int x, int y, int w, int h)
{
    // 靜默更新 4 個 SpinBox，避免觸發 roiChanged 4 次
    m_roiXSpin->blockSignals(true);
    m_roiYSpin->blockSignals(true);
    m_roiWidthSpin->blockSignals(true);
    m_roiHeightSpin->blockSignals(true);

    m_roiXSpin->setValue(x);
    m_roiYSpin->setValue(y);
    m_roiWidthSpin->setValue(w);
    m_roiHeightSpin->setValue(h);

    m_roiXSpin->blockSignals(false);
    m_roiYSpin->blockSignals(false);
    m_roiWidthSpin->blockSignals(false);
    m_roiHeightSpin->blockSignals(false);
}

void DebugPanelWidget::setGateLineRatio(double ratio)
{
    // 靜默更新 SpinBox，再手動 emit 信號（保持與 DetectionController 同步）
    m_gateLinePositionSpin->blockSignals(true);
    m_gateLinePositionSpin->setValue(ratio);
    m_gateLinePositionSpin->blockSignals(false);
    // 明確 emit 讓 MainWindow 的連接生效（不觸發重複 blockSignals 迴圈）
    emit gateLinePositionChanged(ratio);
}

} // namespace basler
