#ifndef METHOD_SELECTOR_H
#define METHOD_SELECTOR_H

#include <QWidget>
#include <QGroupBox>
#include <QComboBox>
#include <QLabel>
#include <QString>
#include <vector>

namespace basler {

/**
 * @brief 檢測方法信息
 */
struct MethodInfo {
    QString methodId;
    QString methodName;
    QString description;
};

/**
 * @brief 檢測方法選擇器
 *
 * 根據選擇的零件類型，顯示可用的檢測方法
 */
class MethodSelectorWidget : public QWidget {
    Q_OBJECT

public:
    explicit MethodSelectorWidget(QWidget* parent = nullptr);
    ~MethodSelectorWidget() = default;

    QString currentMethodId() const;
    QString currentMethodName() const;

public slots:
    /**
     * @brief 更新可用方法列表
     * @param partId 當前零件 ID
     */
    void updateMethodsForPart(const QString& partId);

    /**
     * @brief 設置當前方法
     * @param methodId 方法 ID
     */
    void setCurrentMethod(const QString& methodId);

signals:
    void detectionMethodChanged(const QString& methodId);

private slots:
    void onComboBoxChanged(int index);

private:
    void initUi();

    QGroupBox* m_groupBox;
    QComboBox* m_comboBox;
    QLabel* m_descriptionLabel;

    std::vector<MethodInfo> m_availableMethods;
};

} // namespace basler

#endif // METHOD_SELECTOR_H
