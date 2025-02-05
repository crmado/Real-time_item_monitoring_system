"""
物件監測系統主程式入口
"""

import tkinter as tk
import sys
import logging

from models.system_config import SystemConfig
from models.image_processor import ImageProcessor
from models.camera_manager import CameraManager
from views.main_window import MainWindow
from views.ui_manager import UIManager
from controllers.detection_controller import DetectionController
from controllers.system_controller import SystemController
from utils.logger import Logger
from utils.config import Config


def main():
    """主程式入口"""
    try:
        # 初始化系統配置
        SystemConfig.initialize_system()

        # 初始化日誌
        logger = Logger()

        # 載入配置
        config = Config()

        # 建立主視窗
        root = tk.Tk()
        ui_manager = UIManager()
        main_window = MainWindow(root)

        # 初始化模型
        camera_manager = CameraManager()
        image_processor = ImageProcessor()

        # 初始化控制器
        detection_controller = DetectionController(
            camera_manager,
            image_processor
        )
        system_controller = SystemController(
            main_window,
            detection_controller
        )

        # 檢查更新
        system_controller.check_for_updates()

        # 啟動主循環
        root.mainloop()

    except Exception as e:
        logging.error(f"程式執行時發生錯誤：{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()