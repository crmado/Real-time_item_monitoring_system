"""
即時物品監測系統主程式入口
"""

import os
import sys
import logging
import traceback
import tkinter as tk
import cv2 # type: ignore
from datetime import datetime

# 添加專案根目錄到系統路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 導入自定義模組
from models.camera_manager import CameraManager
from controllers.system_controller import SystemController
from views.main_window import MainWindow
from utils.ui_style_manager import UIStyleManager
from utils.language import set_language, get_text

# 確保 logs 資料夾存在
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 根據當前日期生成日誌檔案名稱
log_filename = os.path.join(logs_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")

# 配置日誌
logging.basicConfig(
    level=logging.INFO,  # 將預設層級設為 INFO，減少不必要的 DEBUG 訊息
    format='%(asctime)s [%(levelname)s] %(message)s',  # 簡化格式，突出重要資訊
    datefmt='%Y-%m-%d %H:%M:%S',  # 自定義日期格式
    handlers=[
        logging.StreamHandler(),  # 輸出到控制台
        logging.FileHandler(log_filename, encoding='utf-8')  # 輸出到日誌檔案
    ]
)

# 定義日誌類型前綴，方便識別
LOG_INFO = "[資訊] "
LOG_WARNING = "[警告] "
LOG_ERROR = "[錯誤] "
LOG_DEBUG = "[除錯] "

# 創建一個自定義的日誌處理器，用於同時輸出到控制台和主視窗的日誌區域
class TkinterHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_queue = []
        self.main_window = None
    
    def set_main_window(self, main_window):
        self.main_window = main_window
        # 顯示之前緩存的日誌
        for record in self.log_queue:
            self.update_ui(record)
        self.log_queue.clear()
    
    def emit(self, record):
        log_entry = self.format(record)
        print(log_entry)  # 確保在控制台顯示
        
        if self.main_window is None:
            # 如果主視窗尚未設置，則將日誌緩存
            self.log_queue.append(record)
        else:
            self.update_ui(record)
    
    def update_ui(self, record):
        if hasattr(self.main_window, 'log_message'):
            # 在主視窗的日誌區域顯示
            self.main_window.log_message(record.getMessage())

# 創建並添加 Tkinter 處理器
tkinter_handler = TkinterHandler()
tkinter_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
logging.getLogger().addHandler(tkinter_handler)

def check_camera_permission():
    """檢查相機權限"""
    if sys.platform == 'darwin':  # macOS
        try:
            # 嘗試開啟相機以觸發權限請求
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    logging.info(f"{LOG_INFO}相機權限已獲得")
                    return True
            logging.warning(f"{LOG_WARNING}未能獲得相機權限")
            return False
        except Exception as e:
            logging.error(f"{LOG_ERROR}檢查相機權限時發生錯誤: {str(e)}")
            return False
    return True

def main():
    """主程序入口"""
    try:
        logging.info(f"{LOG_INFO}程序啟動...")
        
        # 檢查相機權限
        if not check_camera_permission():
            logging.error(f"{LOG_ERROR}無法獲得相機權限，程序將以受限模式運行")
        
        # 創建Tkinter根窗口
        logging.info(f"{LOG_INFO}創建Tkinter根窗口...")
        root = tk.Tk()
        root.title(get_text("app_title", "實時物品監測系統"))
        root.geometry("1200x800")
        root.minsize(1000, 700)
        
        # 設置語言
        logging.info(f"{LOG_INFO}設置語言...")
        set_language("zh_TW")
        
        # 初始化UI樣式
        logging.info(f"{LOG_INFO}初始化UI樣式...")
        ui_style_manager = UIStyleManager(root)
        ui_style_manager.apply_theme()
        
        # 創建主窗口
        logging.info(f"{LOG_INFO}創建主窗口...")
        main_window = MainWindow(root)
        
        # 設置 Tkinter 處理器的主視窗
        tkinter_handler.set_main_window(main_window)
        
        # 創建系統控制器
        logging.info(f"{LOG_INFO}創建系統控制器...")
        system_controller = SystemController(main_window)
        
        # 設置主窗口的系統控制器
        logging.info(f"{LOG_INFO}設置主窗口的系統控制器...")
        main_window.set_system_controller(system_controller)
        
        # 啟動UI更新
        logging.info(f"{LOG_INFO}啟動UI更新...")
        system_controller.start_ui_update()
        
        # 運行主循環
        logging.info(f"{LOG_INFO}運行主循環...")
        root.mainloop()
        
    except Exception as e:
        logging.error(f"{LOG_ERROR}程序啟動時發生錯誤: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()