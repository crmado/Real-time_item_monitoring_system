#pragma once
#include <QString>

namespace basler {

/**
 * @brief 統一按鈕與色彩風格常量
 *
 * 在所有 Widget 中 include 此標頭，統一取用按鈕 stylesheet 與色票。
 * 使用 inline function 讓每個 .cpp 可各自呼叫，避免 ODR 問題。
 */
namespace Style {

// ── 按鈕 StyleSheet ──────────────────────────────────────────────────────

/** 主色調動作按鈕（青色）— 用於「開始」、「連接」等主要操作 */
inline QString primaryBtn()
{
    return "QPushButton {"
           "  background-color: #00a0c8; color: #ffffff;"
           "  border: none; border-radius: 4px; padding: 7px 14px;"
           "  font-weight: bold;"
           "}"
           "QPushButton:hover  { background-color: #00b8e0; }"
           "QPushButton:pressed { background-color: #0080a0; }"
           "QPushButton:disabled { background-color: #1a2a3a; color: #3a5060; }";
}

/** 成功/確認按鈕（綠色）— 用於「儲存」、「確認」、「包裝開始」 */
inline QString successBtn()
{
    return "QPushButton {"
           "  background-color: #2e7d32; color: #ffffff;"
           "  border: none; border-radius: 4px; padding: 7px 14px;"
           "  font-weight: bold;"
           "}"
           "QPushButton:hover  { background-color: #388e3c; }"
           "QPushButton:pressed { background-color: #1b5e20; }"
           "QPushButton:disabled { background-color: #1a2a3a; color: #3a5060; }";
}

/** 危險操作按鈕（紅色）— 用於「刪除」、「強制停止」 */
inline QString dangerBtn()
{
    return "QPushButton {"
           "  background-color: #c62828; color: #ffffff;"
           "  border: none; border-radius: 4px; padding: 7px 14px;"
           "  font-weight: bold;"
           "}"
           "QPushButton:hover  { background-color: #d32f2f; }"
           "QPushButton:pressed { background-color: #b71c1c; }"
           "QPushButton:disabled { background-color: #1a2a3a; color: #3a5060; }";
}

/** 警告/暫停按鈕（橘色）— 用於「暫停」、「停止錄影」 */
inline QString warningBtn()
{
    return "QPushButton {"
           "  background-color: #e65100; color: #ffffff;"
           "  border: none; border-radius: 4px; padding: 7px 14px;"
           "  font-weight: bold;"
           "}"
           "QPushButton:hover  { background-color: #ef6c00; }"
           "QPushButton:pressed { background-color: #bf360c; }"
           "QPushButton:disabled { background-color: #1a2a3a; color: #3a5060; }";
}

/** 次要/輔助按鈕（透明邊框）— 用於「重置」、「取消」、「載入」等輔助操作 */
inline QString secondaryBtn()
{
    return "QPushButton {"
           "  background-color: transparent; color: #a0b4c8;"
           "  border: 1px solid #2a4060; border-radius: 4px; padding: 7px 14px;"
           "}"
           "QPushButton:hover  { border-color: #3a6080; color: #c0d0e0; background-color: #0f1e30; }"
           "QPushButton:pressed { background-color: #1a2a3a; }"
           "QPushButton:disabled { color: #3a5060; border-color: #1a2a30; }";
}

/** 小型工具按鈕（用於 Debug Panel 內的操作按鈕） */
inline QString toolBtn()
{
    return "QPushButton {"
           "  background-color: #1a2a4a; color: #90b0d0;"
           "  border: 1px solid #2a4060; border-radius: 3px; padding: 4px 8px;"
           "  font-size: 11px;"
           "}"
           "QPushButton:hover  { background-color: #243560; color: #c0d8f0; }"
           "QPushButton:pressed { background-color: #152038; }"
           "QPushButton:disabled { color: #3a5060; }";
}

// ── 色票常量 ─────────────────────────────────────────────────────────────

constexpr const char* BG_DARK     = "#0a0e27";   // 主背景深色
constexpr const char* BG_PANEL    = "#1a1f3d";   // 面板/GroupBox 背景
constexpr const char* BORDER      = "#1f3a5f";   // 邊框色
constexpr const char* ACCENT_CYAN = "#00d4ff";   // 主色調青色
constexpr const char* SUCCESS     = "#00ff80";   // 成功綠
constexpr const char* WARNING     = "#ffcc00";   // 警告黃
constexpr const char* ERROR_RED   = "#ff4444";   // 錯誤紅
constexpr const char* TEXT_MAIN   = "#e0e6f1";   // 主文字白
constexpr const char* TEXT_DIM    = "#6a7a8a";   // 次要文字灰

} // namespace Style
} // namespace basler
