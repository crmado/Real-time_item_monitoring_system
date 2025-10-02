"""
Basler 工業視覺系統 - PyQt6 專業版
支持相機/視頻雙模式 + 完整檢測功能
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# 添加項目路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from basler_pyqt6.ui.main_window_v2 import MainWindowV2


def setup_logging():
    """設置日誌"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "basler_pyqt6.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.getLogger('PIL').setLevel(logging.WARNING)


def main():
    """主函數"""
    print("=" * 70)
    print("🏭 Basler 工業視覺系統 - PyQt6 專業版")
    print("=" * 70)
    print("✨ 功能特點:")
    print("  📷 支持 Basler 工業相機 (280+ FPS)")
    print("  🎬 支持視頻文件測試（無需實體相機）")
    print("  🔍 多種檢測算法（圓形/輪廓/背景減除）")
    print("  📊 實時性能監控")
    print("  🎨 專業化界面設計")
    print("=" * 70)
    print()

    # 設置日誌
    print("📝 初始化日誌系統...")
    setup_logging()

    try:
        # 創建 Qt 應用
        app = QApplication(sys.argv)
        app.setApplicationName("Basler 工業視覺系統")

        # 設置高 DPI 支持
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # 創建主窗口
        print("🏗️ 初始化主窗口...")
        window = MainWindowV2()
        window.show()

        print("✅ 系統初始化完成")
        print()
        print("💡 使用提示:")
        print("  • 文件 > 加載視頻文件 - 測試檢測算法")
        print("  • 模式 > 相機模式 - 連接實體相機")
        print("  • 檢測面板 - 切換檢測算法")
        print()

        # 運行應用
        return app.exec()

    except Exception as e:
        print(f"❌ 系統啟動失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
