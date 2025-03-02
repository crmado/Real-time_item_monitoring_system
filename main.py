"""
物件監測系統主程式入口
"""

import tkinter as tk
import sys
import logging
import traceback

import cv2
import numpy

from models.image_processor import ImageProcessor
from models.camera_manager import CameraManager
from views.main_window import MainWindow
from controllers.detection_controller import DetectionController
from controllers.system_controller import SystemController
from utils.logger import Logger
from utils.config import Config


def main(messagebox=None):
    """
    /// 主程式入口
    /// 功能結構：
    /// 第一部分：系統初始化
    /// 第二部分：UI初始化
    /// 第三部分：模型和控制器初始化
    """
    try:
        # ======================================================================
        # 第一部分：系統初始化
        # ======================================================================
        # 初始化日誌
        logger = Logger()

        # 添加進程開始的日誌記錄
        logging.info("=== 物件監測系統啟動 ===")
        logging.info(f"系統版本: 1.0.0")
        logging.info(f"Python 版本: {sys.version}")
        if hasattr(cv2, '__version__'):
            logging.info(f"OpenCV 版本: {cv2.__version__}")

        # 初始化系統配置 (只在這裡初始化一次)
        config = Config()

        # 確保語言管理器初始化
        import utils.language
        language_code = config.get('system.language', 'zh_TW')
        utils.language.change_language(language_code)

        # ======================================================================
        # 第二部分：UI初始化
        # ======================================================================
        # 建立主視窗
        root = tk.Tk()
        main_window = MainWindow(root, config)

        # ======================================================================
        # 第三部分：模型和控制器初始化
        # ======================================================================
        # 初始化模型
        camera_manager = CameraManager()
        image_processor = ImageProcessor()

        # 初始化控制器
        detection_controller = DetectionController(
            camera_manager,
            image_processor
        )

        # 從配置設定偵測參數
        detection_controller.update_settings(
            config.get('detection.target_count', 1000),
            config.get('detection.buffer_point', 950)
        )

        # 初始化系統控制器
        system_controller = SystemController(
            main_window,
            detection_controller,
            config
        )

        main_window.set_system_controller(system_controller)

        # 窗口關閉時保存配置
        def on_closing():
            # 保存視窗狀態
            width = root.winfo_width()
            height = root.winfo_height()
            x = root.winfo_x()
            y = root.winfo_y()
            config.save_window_state(width, height, x, y)

            # 停止一切進行中的活動
            if hasattr(detection_controller, 'stop_monitoring'):
                detection_controller.stop_monitoring()

            if hasattr(detection_controller, 'stop_camera_test'):
                detection_controller.stop_camera_test()

            if hasattr(detection_controller, 'cleanup_photo_resources'):
                detection_controller.cleanup_photo_resources()

            # 關閉視窗
            root.destroy()
            logging.info("=== 物件監測系統關閉 ===")

        root.protocol("WM_DELETE_WINDOW", on_closing)

        # 啟動主循環
        logging.info("主循環開始")
        root.mainloop()

    except Exception as e:
        logging.error(f"執行程式時發生錯誤：{str(e)}")
        logging.error(f"錯誤詳情: {traceback.format_exc()}")
        # 顯示錯誤訊息
        try:
            from tkinter import messagebox
            messagebox.showerror("系統錯誤", f"程式執行錯誤: {str(e)}\n請查看日誌檔案以獲取詳細資訊。")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()