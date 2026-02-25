#include "ui/widgets/part_selector.h"
#include "config/settings.h"
#include <QVBoxLayout>

namespace basler {

PartSelectorWidget::PartSelectorWidget(QWidget* parent)
    : QWidget(parent)
{
    initUi();
    loadPartTypes();
}

void PartSelectorWidget::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    // 創建分組框
    m_groupBox = new QGroupBox(tr("🔧 零件類型"));
    QVBoxLayout* groupLayout = new QVBoxLayout();

    // 下拉選單
    m_comboBox = new QComboBox();
    connect(m_comboBox, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &PartSelectorWidget::onComboBoxChanged);
    groupLayout->addWidget(m_comboBox);

    // 描述標籤
    m_descriptionLabel = new QLabel();
    m_descriptionLabel->setWordWrap(true);
    m_descriptionLabel->setStyleSheet("color: #888; font-size: 11px;");
    groupLayout->addWidget(m_descriptionLabel);

    m_groupBox->setLayout(groupLayout);
    mainLayout->addWidget(m_groupBox);
    mainLayout->addStretch();
}

void PartSelectorWidget::loadPartTypes()
{
    m_comboBox->clear();

    const auto& config = Settings::instance();
    const auto& profiles = config.partProfiles();

    for (const auto& profile : profiles) {
        m_comboBox->addItem(profile.partName, profile.partId);
    }

    // 設置當前選擇
    QString currentId = config.currentPartId();
    for (int i = 0; i < m_comboBox->count(); ++i) {
        if (m_comboBox->itemData(i).toString() == currentId) {
            m_comboBox->setCurrentIndex(i);
            break;
        }
    }

    // 更新描述
    onComboBoxChanged(m_comboBox->currentIndex());
}

void PartSelectorWidget::refreshPartList()
{
    loadPartTypes();
}

void PartSelectorWidget::setCurrentPart(const QString& partId)
{
    for (int i = 0; i < m_comboBox->count(); ++i) {
        if (m_comboBox->itemData(i).toString() == partId) {
            m_comboBox->setCurrentIndex(i);
            break;
        }
    }
}

QString PartSelectorWidget::currentPartId() const
{
    return m_comboBox->currentData().toString();
}

QString PartSelectorWidget::currentPartName() const
{
    return m_comboBox->currentText();
}

void PartSelectorWidget::onComboBoxChanged(int index)
{
    if (index < 0) {
        return;
    }

    QString partId = m_comboBox->itemData(index).toString();

    // 更新描述
    const auto& config = Settings::instance();
    const auto* profile = config.getPartProfile(partId);
    if (profile) {
        m_descriptionLabel->setText(profile->description);
    }

    emit partTypeChanged(partId);
}

} // namespace basler
