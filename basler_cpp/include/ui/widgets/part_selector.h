#ifndef PART_SELECTOR_H
#define PART_SELECTOR_H

#include <QWidget>
#include <QGroupBox>
#include <QComboBox>
#include <QLabel>
#include <QString>

namespace basler {

/**
 * @brief 零件類型選擇器
 *
 * 允許用戶選擇要檢測的零件類型
 * 每種零件類型有預設的檢測參數
 */
class PartSelectorWidget : public QWidget {
    Q_OBJECT

public:
    explicit PartSelectorWidget(QWidget* parent = nullptr);
    ~PartSelectorWidget() = default;

    QString currentPartId() const;
    QString currentPartName() const;

public slots:
    /**
     * @brief 刷新零件列表
     */
    void refreshPartList();

    /**
     * @brief 設置當前零件
     * @param partId 零件 ID
     */
    void setCurrentPart(const QString& partId);

signals:
    void partTypeChanged(const QString& partId);

private slots:
    void onComboBoxChanged(int index);

private:
    void initUi();
    void loadPartTypes();

    QGroupBox* m_groupBox;
    QComboBox* m_comboBox;
    QLabel* m_descriptionLabel;
};

} // namespace basler

#endif // PART_SELECTOR_H
