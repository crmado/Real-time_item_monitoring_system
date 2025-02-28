# main.py (修改)
"""
物件監測系統主程式入口
"""

import tkinter as tk
import sys
import logging

from utils.config import Config as SystemConfig
from models.image_processor import ImageProcessor
from models.camera_manager import CameraManager
from views.main_window import MainWindow
from views.ui_manager import UIManager
from controllers.detection_controller import DetectionController
from controllers.system_controller import SystemController
from utils.logger import Logger
from utils.config import Config


def main():
    """
    /// 主程式入口
    /// 功能結構：
    /// 第一部分：系統初始化
    /// 第二部分：模型和控制器初始化
    /// 第三部分：UI初始化
    /// 第四部分：系統啟動
    """
    try:
        #======================================================================
        # 第一部分：系統初始化
        #======================================================================
        # 初始化系統配置
        SystemConfig.initialize_system()

        # 初始化日誌
        logger = Logger()

        # 載入配置
        config = Config()

        #======================================================================
        # 第二部分：模型和控制器初始化
        #======================================================================
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

        #======================================================================
        # 第三部分：UI初始化
        #======================================================================
        # 建立主視窗
        root = tk.Tk()
        ui_manager = UIManager()
        main_window = MainWindow(root, config)

        # 載入視窗狀態
        window_state = config.get('ui.window_state', {})
        if window_state.get('width') and window_state.get('height'):
            root.geometry(f"{window_state.get('width')}x{window_state.get('height')}")
            if window_state.get('position_x') and window_state.get('position_y'):
                root.geometry(f"+{window_state.get('position_x')}+{window_state.get('position_y')}")

        # 應用主題
        theme = config.get('ui.theme', 'system')
        main_window.apply_theme(theme)

        #======================================================================
        # 第四部分：系統啟動
        #======================================================================
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

        system_controller = SystemController(
            main_window,
            detection_controller,
            config
        )

        # 檢查是否自動檢查更新
        if config.get('system.check_updates', True):
            system_controller.check_for_updates()

        # 視窗關閉時保存狀態
        def on_closing():
            # 保存視窗狀態
            width = root.winfo_width()
            height = root.winfo_height()
            x = root.winfo_x()
            y = root.winfo_y()
            config.save_window_state(width, height, x, y)

            # 關閉視窗
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_closing)

        # 啟動主循環
        root.mainloop()

    except Exception as e:
        logging.error(f"An error occurred while executing the program：{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()