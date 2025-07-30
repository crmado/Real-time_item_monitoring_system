#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Debug 模式啟動程式
提供詳細的日誌輸出和錯誤追蹤功能
"""

import os
import sys
import logging
import traceback
import tkinter as tk
from datetime import datetime

# 設置環境變數
os.environ['DEBUG'] = '1'

# 添加專案根目錄到系統路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_debug_logging():
    """設置 Debug 模式的日誌配置"""
    # 確保 logs 資料夾存在
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # 根據當前日期和時間生成日誌檔案名稱
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = os.path.join(logs_dir, f"debug_{timestamp}.log")

    # 配置詳細的日誌
    logging.basicConfig(
        level=logging.DEBUG,  # 設置為 DEBUG 級別
        format='%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),  # 輸出到控制台
            logging.FileHandler(log_filename, encoding='utf-8')  # 輸出到日誌檔案
        ]
    )

    print(f"Debug 日誌檔案: {log_filename}")
    return log_filename

def check_dependencies():
    """檢查依賴套件"""
    required_packages = [
        'cv2',
        'numpy',
        'PIL',
        'tkinter'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'cv2':
                import cv2
                print(f"✓ OpenCV 版本: {cv2.__version__}")
            elif package == 'numpy':
                import numpy
                print(f"✓ NumPy 版本: {numpy.__version__}")
            elif package == 'PIL':
                from PIL import Image
                print("✓ Pillow 已安裝")
            elif package == 'tkinter':
                import tkinter
                print(f"✓ Tkinter 版本: {tkinter.TkVersion}")
        except ImportError as e:
            missing_packages.append(package)
            print(f"✗ {package}: {e}")
    
    if missing_packages:
        print(f"\n缺少以下套件: {missing_packages}")
        print("請執行: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """Debug 模式主程式"""
    print("=" * 60)
    print("即時物品監測系統 - Debug 模式")
    print("=" * 60)
    
    # 設置 Debug 日誌
    log_file = setup_debug_logging()
    
    try:
        # 檢查依賴
        print("\n檢查依賴套件...")
        if not check_dependencies():
            print("依賴檢查失敗，程式退出")
            return
        
        print("\n開始載入模組...")
        
        # 導入自定義模組
        logging.debug("導入 CameraManager...")
        from models.camera_manager import CameraManager
        
        logging.debug("導入 SystemController...")
        from controllers.system_controller import SystemController
        
        logging.debug("導入 MainWindow...")
        from views.main_window import MainWindow
        
        logging.debug("導入 UIStyleManager...")
        from utils.ui_style_manager import UIStyleManager
        
        logging.debug("導入語言模組...")
        from utils.language import set_language, get_text
        
        print("✓ 所有模組載入成功")
        
        # 創建Tkinter根窗口
        logging.info("創建Tkinter根窗口...")
        root = tk.Tk()
        root.title(get_text("app_title", "實時物品監測系統") + " (Debug 模式)")
        root.geometry("1200x800")
        root.minsize(1000, 700)
        
        # 設置語言
        logging.info("設置語言...")
        set_language("zh_TW")
        
        # 初始化UI樣式
        logging.info("初始化UI樣式...")
        ui_style_manager = UIStyleManager(root)
        ui_style_manager.apply_theme()
        
        # 創建主窗口
        logging.info("創建主窗口...")
        main_window = MainWindow(root)
        
        # 創建系統控制器
        logging.info("創建系統控制器...")
        system_controller = SystemController(main_window)
        
        # 設置主窗口的系統控制器
        logging.info("設置主窗口的系統控制器...")
        main_window.set_system_controller(system_controller)
        
        # 啟動UI更新
        logging.info("啟動UI更新...")
        system_controller.start_ui_update()
        
        print("✓ 程式初始化完成")
        print(f"✓ Debug 日誌檔案: {log_file}")
        print("✓ 程式開始運行...")
        
        # 運行主循環
        logging.info("運行主循環...")
        root.mainloop()
        
    except Exception as e:
        logging.error(f"程式啟動時發生錯誤: {str(e)}")
        logging.error(traceback.format_exc())
        print(f"\n❌ 錯誤: {str(e)}")
        print(f"詳細錯誤資訊已記錄到: {log_file}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 