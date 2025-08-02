"""
Basler MVC 主程序
精簡高性能版本 - 只保留核心功能
"""

import sys
import os
import logging
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 導入 MVC 組件
try:
    from basler_mvc.controllers.main_controller import MainController
    from basler_mvc.views.main_view import MainView
except ImportError as e:
    print(f"導入錯誤: {str(e)}")
    print("請確保所有必要文件都已創建")
    sys.exit(1)


def setup_logging():
    """設置日誌系統"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 創建日誌目錄
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 配置日誌 - 提高級別以減少I/O
    logging.basicConfig(
        level=logging.WARNING,  # 從INFO提高到WARNING減少日誌量
        format=log_format,
        handlers=[
            logging.FileHandler(log_dir / "basler_mvc.log", encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 減少 PIL 日誌噪音
    logging.getLogger('PIL').setLevel(logging.WARNING)


def check_dependencies():
    """檢查必要依賴"""
    missing_deps = []
    
    try:
        import tkinter
    except ImportError:
        missing_deps.append("tkinter")
    
    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        from PIL import Image
    except ImportError:
        missing_deps.append("Pillow")
    
    try:
        from pypylon import pylon
    except ImportError:
        missing_deps.append("pypylon")
    
    if missing_deps:
        print("❌ 缺少必要依賴:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n請安裝缺少的依賴:")
        print("pip install opencv-python numpy Pillow pypylon")
        return False
    
    return True


def show_startup_info():
    """顯示啟動信息"""
    print("🚀 Basler acA640-300gm MVC 精簡高性能系統")
    print("=" * 60)
    print("架構: Model-View-Controller")
    print("目標: 專注核心功能，追求極致性能")
    print("支援: Basler acA640-300gm 工業相機")
    print("檢測: 圓形檢測、輪廓檢測")
    print("=" * 60)
    print()


def main():
    """主函數"""
    try:
        # 顯示啟動信息
        show_startup_info()
        
        # 檢查依賴
        print("🔍 檢查系統依賴...")
        if not check_dependencies():
            return 1
        print("✅ 所有依賴已安裝")
        
        # 設置日誌
        print("📝 初始化日誌系統...")
        setup_logging()
        logging.info("Basler MVC 系統啟動")
        
        # 創建 MVC 組件
        print("🏗️ 初始化 MVC 架構...")
        controller = MainController()
        view = MainView(controller)
        
        logging.info("MVC 架構初始化完成")
        print("✅ 系統初始化完成")
        print()
        
        # 檢測可用相機設備（但不自動啟動）
        print("🔍 檢測可用相機設備...")
        detected_cameras = controller.detect_cameras()
        if detected_cameras:
            print(f"✅ 檢測到 {len(detected_cameras)} 台相機設備")
            for i, camera in enumerate(detected_cameras):
                status = "✅ 目標型號" if camera.get('is_target', False) else "⚠️ 其他型號"
                print(f"   相機 {i+1}: {camera['model']} ({status})")
            print("📌 請在界面中雙擊設備進行連接")
        else:
            print("⚠️ 未檢測到任何相機設備")
        
        print()
        print("🎮 啟動用戶界面...")
        
        # 運行應用程序
        view.run()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n❗ 用戶中斷程序")
        logging.info("用戶中斷程序")
        return 0
        
    except Exception as e:
        error_msg = f"系統啟動失敗: {str(e)}"
        print(f"❌ {error_msg}")
        logging.error(error_msg, exc_info=True)
        return 1
    
    finally:
        logging.info("Basler MVC 系統關閉")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)