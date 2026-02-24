#ifndef SETUP_WIZARD_H
#define SETUP_WIZARD_H

#include <QWizard>

namespace basler {

/**
 * @brief 首次使用設定向導
 *
 * 引導使用者完成基本初始設定（4 步驟）：
 *   1. 歡迎頁
 *   2. 影像來源說明
 *   3. 檢測參數設定（minArea / maxArea / bgVarThreshold）
 *   4. 包裝目標設定（targetCount）
 *
 * 完成後寫入 QSettings "wizardDone=true"，下次不再顯示。
 */
class SetupWizard : public QWizard {
    Q_OBJECT

public:
    explicit SetupWizard(QWidget* parent = nullptr);

    /**
     * @brief 判斷是否需要顯示向導（首次執行）
     * @return true = 尚未完成向導，應顯示
     */
    static bool isFirstRun();

protected:
    /** Finish 鍵按下時：寫入設定並標記 wizardDone */
    void accept() override;
};

} // namespace basler

#endif // SETUP_WIZARD_H
