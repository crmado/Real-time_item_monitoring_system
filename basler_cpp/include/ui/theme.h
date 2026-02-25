#ifndef THEME_H
#define THEME_H

#include <QString>

namespace basler {

/**
 * @brief 主題顏色常量 — 深色/淺色雙主題語義色彩
 *
 * 使用方式：
 *   ThemeColors tc(isDark);
 *   label->setStyleSheet("color: " + tc.success + ";");
 */
struct ThemeColors {
    // 語義顏色
    QString success;   // 成功/合格（計數、合格率）
    QString warning;   // 警告（接近目標）
    QString danger;    // 錯誤/不合格
    QString info;      // 一般資訊
    QString hint;      // 提示/次要文字
    QString neutral;   // 中性（停止狀態）

    // 背景色
    QString cardBg;    // 卡片/面板背景

    // 按鈕語義色
    QString btnStart;  // 開始/確認動作
    QString btnStop;   // 停止/取消動作
    QString btnInfo;   // 資訊/次要動作

    explicit ThemeColors(bool isDark)
    {
        if (isDark) {
            success  = "#00ff80";
            warning  = "#ffff00";
            danger   = "#ff4444";
            info     = "#5a8ab0";
            hint     = "#888888";
            neutral  = "#888888";
            cardBg   = "#1e2a3a";
            btnStart = "#4CAF50";
            btnStop  = "#FF9800";
            btnInfo  = "#2196F3";
        } else {
            success  = "#1b7a3a";  // 深綠，白底可讀
            warning  = "#b85c00";  // 深橙，白底可讀
            danger   = "#c62828";  // 深紅，白底可讀
            info     = "#1565c0";  // 深藍
            hint     = "#666666";
            neutral  = "#777777";
            cardBg   = "#f5f7fa";
            btnStart = "#388E3C";  // 深色按鈕，白底仍清晰
            btnStop  = "#E65100";
            btnInfo  = "#1565C0";
        }
    }

    // 快捷：生成 QPushButton StyleSheet
    QString btnStyle(const QString &bgColor) const {
        return QString("QPushButton { background-color: %1; color: white; padding: 10px; }")
               .arg(bgColor);
    }
};

} // namespace basler

#endif // THEME_H
