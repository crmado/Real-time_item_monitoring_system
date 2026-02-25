#include "ui/setup_wizard.h"
#include "config/settings.h"

#include <QWizardPage>
#include <QLabel>
#include <QSpinBox>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QFormLayout>
#include <QSettings>
#include <QFont>

namespace basler {

// ============================================================================
// 頁面 0 — 歡迎
// ============================================================================
class WelcomePage : public QWizardPage {
public:
    explicit WelcomePage(QWidget* parent = nullptr) : QWizardPage(parent)
    {
        setTitle(tr("歡迎使用 Basler 工業視覺系統"));
        setSubTitle(tr("本向導將引導您完成初始設定（約 1 分鐘）。"));

        QVBoxLayout* layout = new QVBoxLayout(this);

        QLabel* iconLabel = new QLabel("🏭", this);
        iconLabel->setAlignment(Qt::AlignCenter);
        QFont iconFont = iconLabel->font();
        iconFont.setPointSize(36);
        iconLabel->setFont(iconFont);
        layout->addWidget(iconLabel);

        QLabel* descLabel = new QLabel(
            tr("完成以下步驟即可開始使用：\n\n"
               "  步驟 1：了解影像來源（相機 / 測試視頻）\n"
               "  步驟 2：設定檢測參數（面積範圍、背景敏感度）\n"
               "  步驟 3：設定包裝目標數量\n\n"
               "所有設定均可在調試面板中隨時調整。"),
            this);
        descLabel->setWordWrap(true);
        descLabel->setStyleSheet("font-size: 13px; line-height: 1.6;");
        layout->addWidget(descLabel);
        layout->addStretch();
    }
};

// ============================================================================
// 頁面 1 — 影像來源說明
// ============================================================================
class SourcePage : public QWizardPage {
public:
    explicit SourcePage(QWidget* parent = nullptr) : QWizardPage(parent)
    {
        setTitle(tr("步驟 1：影像來源"));
        setSubTitle(tr("本系統支援 Basler 工業相機及測試視頻兩種來源。"));

        QVBoxLayout* layout = new QVBoxLayout(this);

        QLabel* cameraInfo = new QLabel(
            tr("📷  <b>相機模式</b><br>"
               "在右側「設定」分頁中，點擊「偵測相機」連接 Basler 相機。<br><br>"
               "🎬  <b>測試視頻模式</b><br>"
               "在右側「調試」分頁中，點擊「載入視頻」選擇測試視頻檔案。<br>"
               "系統會自動開始播放並進行檢測。<br><br>"
               "⚠  <b>注意</b><br>"
               "如果未安裝 Pylon SDK，相機功能不可用，請使用測試視頻模式。"),
            this);
        cameraInfo->setWordWrap(true);
        cameraInfo->setTextFormat(Qt::RichText);
        cameraInfo->setStyleSheet("font-size: 13px; line-height: 1.6;");
        layout->addWidget(cameraInfo);
        layout->addStretch();
    }
};

// ============================================================================
// 頁面 2 — 檢測參數設定
// ============================================================================
class DetectionPage : public QWizardPage {
public:
    explicit DetectionPage(QWidget* parent = nullptr) : QWizardPage(parent)
    {
        setTitle(tr("步驟 2：檢測參數"));
        setSubTitle(tr("設定零件大小範圍和背景敏感度。（之後可在調試面板微調）"));

        QVBoxLayout* layout = new QVBoxLayout(this);

        QLabel* hint = new QLabel(
            tr("根據您的零件尺寸調整以下參數："),
            this);
        hint->setStyleSheet("font-size: 12px; color: #888;");
        layout->addWidget(hint);

        QFormLayout* form = new QFormLayout();

        // minArea
        m_minAreaSpin = new QSpinBox(this);
        m_minAreaSpin->setRange(1, 500);
        m_minAreaSpin->setValue(Settings::instance().detection().minArea);
        m_minAreaSpin->setSuffix(tr(" px²"));
        form->addRow(tr("最小面積（minArea）："), m_minAreaSpin);

        // maxArea
        m_maxAreaSpin = new QSpinBox(this);
        m_maxAreaSpin->setRange(100, 50000);
        m_maxAreaSpin->setValue(Settings::instance().detection().maxArea);
        m_maxAreaSpin->setSuffix(tr(" px²"));
        form->addRow(tr("最大面積（maxArea）："), m_maxAreaSpin);

        // bgVarThreshold
        m_bgVarSpin = new QSpinBox(this);
        m_bgVarSpin->setRange(1, 50);
        m_bgVarSpin->setValue(static_cast<int>(Settings::instance().detection().bgVarThreshold));
        m_bgVarSpin->setToolTip(tr("背景方差閾值：數字越小越靈敏，越容易偵測微小移動"));
        form->addRow(tr("背景敏感度（bgVarThreshold）："), m_bgVarSpin);

        layout->addLayout(form);

        QLabel* tipLabel = new QLabel(
            tr("💡 提示：小零件（如螺絲）建議 minArea=2～5，"
               "較大零件（如齒輪）建議 minArea=50～100"),
            this);
        tipLabel->setWordWrap(true);
        tipLabel->setStyleSheet("font-size: 11px; color: #5a8ab0; margin-top: 8px;");
        layout->addWidget(tipLabel);
        layout->addStretch();

        // 向 QWizard 註冊欄位（可讓 validatePage 使用）
        registerField("minArea",       m_minAreaSpin);
        registerField("maxArea",       m_maxAreaSpin);
        registerField("bgVarThreshold", m_bgVarSpin);
    }

private:
    QSpinBox* m_minAreaSpin  = nullptr;
    QSpinBox* m_maxAreaSpin  = nullptr;
    QSpinBox* m_bgVarSpin    = nullptr;
};

// ============================================================================
// 頁面 3 — 包裝目標設定
// ============================================================================
class PackagingPage : public QWizardPage {
public:
    explicit PackagingPage(QWidget* parent = nullptr) : QWizardPage(parent)
    {
        setTitle(tr("步驟 3：包裝目標設定"));
        setSubTitle(tr("設定每袋（包）的目標零件數量。"));

        QVBoxLayout* layout = new QVBoxLayout(this);

        QLabel* hint = new QLabel(
            tr("每次包裝完成（計數到達目標）時，系統會自動停止震動機並顯示完成提示。"),
            this);
        hint->setWordWrap(true);
        hint->setStyleSheet("font-size: 12px; color: #888;");
        layout->addWidget(hint);

        QFormLayout* form = new QFormLayout();

        m_targetCountSpin = new QSpinBox(this);
        m_targetCountSpin->setRange(1, 9999);
        m_targetCountSpin->setValue(Settings::instance().packaging().targetCount);
        m_targetCountSpin->setSuffix(tr(" 顆"));
        form->addRow(tr("每包目標數量："), m_targetCountSpin);

        layout->addLayout(form);

        QLabel* doneTip = new QLabel(
            tr("✅ 完成後系統即可正常使用。\n"
               "   調試面板（右側 Tab 3）可隨時調整所有參數。"),
            this);
        doneTip->setWordWrap(true);
        doneTip->setStyleSheet("font-size: 12px; color: #5aab70; margin-top: 16px;");
        layout->addWidget(doneTip);
        layout->addStretch();

        registerField("targetCount", m_targetCountSpin);
    }

private:
    QSpinBox* m_targetCountSpin = nullptr;
};

// ============================================================================
// SetupWizard 主體
// ============================================================================
SetupWizard::SetupWizard(QWidget* parent)
    : QWizard(parent)
{
    setWindowTitle(tr("初始設定向導"));
    setWizardStyle(QWizard::ModernStyle);
    setMinimumSize(560, 420);

    addPage(new WelcomePage(this));
    addPage(new SourcePage(this));
    addPage(new DetectionPage(this));
    addPage(new PackagingPage(this));

    setButtonText(QWizard::FinishButton, tr("完成並開始使用"));
    setButtonText(QWizard::NextButton,   tr("下一步 ▶"));
    setButtonText(QWizard::BackButton,   tr("◀ 上一步"));
    setButtonText(QWizard::CancelButton, tr("跳過（之後可手動設定）"));
}

bool SetupWizard::isFirstRun()
{
    QSettings settings("BaslerVision", "BaslerVisionSystem");
    return !settings.value("wizardDone", false).toBool();
}

void SetupWizard::accept()
{
    // 將向導中的設定值寫入 Settings
    auto& cfg = Settings::instance();

    cfg.detection().minArea        = field("minArea").toInt();
    cfg.detection().maxArea        = field("maxArea").toInt();
    cfg.detection().bgVarThreshold = field("bgVarThreshold").toDouble();
    cfg.packaging().targetCount    = field("targetCount").toInt();

    // 儲存到磁碟
    cfg.save();

    // 標記向導已完成，下次不再顯示
    QSettings settings("BaslerVision", "BaslerVisionSystem");
    settings.setValue("wizardDone", true);

    QWizard::accept();
}

} // namespace basler
