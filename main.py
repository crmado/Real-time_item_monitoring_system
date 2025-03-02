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

        # 檢查環境依賴
        try:
            logging.info(f"NumPy 版本: {numpy.__version__}")
        except ImportError:
            logging.warning("未找到 NumPy 庫")

        # 初始化系統配置 (只在這裡初始化一次)
        config = Config()

        # ======================================================================
        # 第二部分：UI初始化
        # ======================================================================
        # 添加例外處理以捕獲Tkinter初始化錯誤
        try:
            # 建立主視窗
            root = tk.Tk()
            main_window = MainWindow(root, config)

            # 載入視窗狀態
            window_state = config.get('ui.window_state', {})
            if window_state.get('width') and window_state.get('height'):
                root.geometry(f"{window_state.get('width')}x{window_state.get('height')}")
                if window_state.get('position_x') and window_state.get('position_y'):
                    root.geometry(f"+{window_state.get('position_x')}+{window_state.get('position_y')}")
        except Exception as ui_error:
            logging.error(f"UI 初始化失敗: {str(ui_error)}")
            messagebox.showerror("UI 初始化錯誤", f"無法初始化使用者介面: {str(ui_error)}")
            sys.exit(1)

        # ======================================================================
        # 第三部分：模型和控制器初始化
        # ======================================================================
        try:
            # 初始化模型
            camera_manager = CameraManager()
            image_processor = ImageProcessor()

            # 從配置加載設定
            image_processor.set_parameters({
                'min_object_area': config.get('detection.min_object_area', 10),
                'max_object_area': config.get('detection.max_object_area', 150),
                'canny_threshold1': config.get('detection.canny_threshold1', 50),
                'canny_threshold2': config.get('detection.canny_threshold2', 110),
                'binary_threshold': config.get('detection.binary_threshold', 30),
                'bg_history': config.get('detection.bg_history', 20000),
                'bg_threshold': config.get('detection.bg_threshold', 16),
                'detect_shadows': config.get('detection.detect_shadows', True)
            })
        except Exception as model_error:
            logging.error(f"模型初始化失敗: {str(model_error)}")
            messagebox.showerror("模型初始化錯誤", f"無法初始化模型組件: {str(model_error)}")
            sys.exit(1)

        try:
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
            detection_controller.roi_height = config.get('detection.roi_height', 16)
            detection_controller.saved_roi_percentage = config.get('detection.roi_default_position', 0.2)

            # 初始化系統控制器 (將在這裡統一管理主題和語言)
            system_controller = SystemController(
                main_window,
                detection_controller,
                config
            )

            main_window.set_system_controller(system_controller)
        except Exception as controller_error:
            logging.error(f"控制器初始化失敗: {str(controller_error)}")
            messagebox.showerror("控制器初始化錯誤", f"無法初始化控制器組件: {str(controller_error)}")
            sys.exit(1)

        # 視窗關閉時保存狀態
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

            # 關閉視窗
            root.destroy()
            logging.info("=== 物件監測系統關閉 ===")

        root.protocol("WM_DELETE_WINDOW", on_closing)

        # 檢查是否自動檢查更新
        if config.get('system.check_updates', True):
            system_controller.check_for_updates()

        # 啟動主循環
        logging.info("主循環開始")
        root.mainloop()

    except Exception as e:
        logging.error(f"執行程式時發生錯誤：{str(e)}")
        logging.error(f"錯誤詳情: {traceback.format_exc()}")
        try:
            from tkinter import messagebox
            messagebox.showerror("系統錯誤", f"程式執行錯誤: {str(e)}\n請查看日誌檔案以獲取詳細資訊。")
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()