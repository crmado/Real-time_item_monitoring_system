"""
Basler 工業視覺系統 - PyQt6 桌面版
主程序入口
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

# 添加項目路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from basler_pyqt6.ui.main_window import MainWindow


def setup_logging():
    """設置日誌系統"""
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

    # 減少 PIL 日誌噪音
    logging.getLogger('PIL').setLevel(logging.WARNING)


def check_dependencies():
    """檢查必要依賴"""
    missing_deps = []

    try:
        from PyQt6 import QtWidgets
    except ImportError:
        missing_deps.append("PyQt6")

    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")

    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")

    try:
        from pypylon import pylon
    except ImportError:
        missing_deps.append("pypylon")

    if missing_deps:
        print("❌ 缺少必要依賴:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n請安裝缺少的依賴:")
        print("pip install -r requirements.txt")
        return False

    return True


def main():
    """主函數"""
    print("=" * 60)
    print("🏭 Basler acA640-300gm 工業視覺系統 - PyQt6 桌面版")
    print("=" * 60)
    print("架構: PyQt6 桌面應用")
    print("目標: 單機部署，雙擊運行")
    print("支援: Basler acA640-300gm 工業相機 (280+ FPS)")
    print("=" * 60)
    print()

    # 檢查依賴
    print("🔍 檢查系統依賴...")
    if not check_dependencies():
        return 1
    print("✅ 所有依賴已安裝")

    # 設置日誌
    print("📝 初始化日誌系統...")
    setup_logging()
    logging.info("🚀 Basler PyQt6 系統啟動")

    try:
        # 創建 Qt 應用
        app = QApplication(sys.argv)
        app.setApplicationName("Basler 工業視覺系統")
        app.setOrganizationName("Industrial Vision")

        # 設置高 DPI 支持
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # 創建主窗口
        print("🏗️ 初始化主窗口...")
        window = MainWindow()
        window.show()

        logging.info("✅ 主窗口初始化完成")
        print("✅ 系統初始化完成")
        print()
        print("🎮 系統已啟動，開始使用...")

        # 運行應用
        exit_code = app.exec()

        logging.info("✅ 應用程序正常退出")
        return exit_code

    except Exception as e:
        error_msg = f"系統啟動失敗: {str(e)}"
        print(f"❌ {error_msg}")
        logging.error(error_msg, exc_info=True)

        import traceback
        print("🔍 詳細錯誤追蹤:")
        traceback.print_exc()

        return 1


if __name__ == "__main__":
    sys.exit(main())
