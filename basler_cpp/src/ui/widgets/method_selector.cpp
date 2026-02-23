#include "ui/widgets/method_selector.h"
#include "config/settings.h"
#include <QVBoxLayout>

namespace basler {

MethodSelectorWidget::MethodSelectorWidget(QWidget* parent)
    : QWidget(parent)
{
    initUi();
}

void MethodSelectorWidget::initUi()
{
    QVBoxLayout* mainLayout = new QVBoxLayout(this);

    // 創建分組框
    m_groupBox = new QGroupBox(tr("🎯 檢測方法"));
    QVBoxLayout* groupLayout = new QVBoxLayout();

    // 下拉選單
    m_comboBox = new QComboBox();
    connect(m_comboBox, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &MethodSelectorWidget::onComboBoxChanged);
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

void MethodSelectorWidget::updateMethodsForPart(const QString& partId)
{
    m_comboBox->clear();
    m_availableMethods.clear();

    const auto& config = getConfig();
    const auto* profile = config.getPartProfile(partId);

    if (!profile) {
        return;
    }

    for (const auto& method : profile->availableMethods) {
        MethodInfo info;
        info.methodId = method.methodId;
        info.methodName = method.methodName;
        info.description = method.methodDescription;
        m_availableMethods.push_back(info);

        m_comboBox->addItem(method.methodName, method.methodId);
    }

    // 設置當前選擇
    QString currentMethodId = profile->currentMethodId;
    for (int i = 0; i < m_comboBox->count(); ++i) {
        if (m_comboBox->itemData(i).toString() == currentMethodId) {
            m_comboBox->setCurrentIndex(i);
            break;
        }
    }

    onComboBoxChanged(m_comboBox->currentIndex());
}

void MethodSelectorWidget::setCurrentMethod(const QString& methodId)
{
    for (int i = 0; i < m_comboBox->count(); ++i) {
        if (m_comboBox->itemData(i).toString() == methodId) {
            m_comboBox->setCurrentIndex(i);
            break;
        }
    }
}

QString MethodSelectorWidget::currentMethodId() const
{
    return m_comboBox->currentData().toString();
}

QString MethodSelectorWidget::currentMethodName() const
{
    return m_comboBox->currentText();
}

void MethodSelectorWidget::onComboBoxChanged(int index)
{
    if (index < 0 || index >= static_cast<int>(m_availableMethods.size())) {
        return;
    }

    const auto& method = m_availableMethods[index];
    m_descriptionLabel->setText(method.description);

    emit detectionMethodChanged(method.methodId);
}

} // namespace basler
