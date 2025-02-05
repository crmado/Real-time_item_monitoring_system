"""
日誌工具
提供統一的日誌記錄功能
"""

import logging
import os
import datetime
from logging.handlers import RotatingFileHandler


class Logger:
    """日誌管理類別"""

    def __init__(self, name="ObjectDetectionSystem"):
        """
        初始化日誌管理器

        Args:
            name: 日誌名稱
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.setup_logger()

    def setup_logger(self):
        """設定日誌處理器"""
        # 建立日誌目錄
        log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'logs'
        )
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 建立日誌檔案名稱
        log_file = os.path.join(
            log_dir,
            f"detection_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # 檔案處理器
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # 控制台處理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 設定格式
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加處理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message):
        """
        記錄信息級別的日誌

        Args:
            message: 日誌訊息
        """
        self.logger.info(message)

    def error(self, message):
        """
        記錄錯誤級別的日誌

        Args:
            message: 日誌訊息
        """
        self.logger.error(message)

    def warning(self, message):
        """
        記錄警告級別的日誌

        Args:
            message: 日誌訊息
        """
        self.logger.warning(message)

    def debug(self, message):
        """
        記錄調試級別的日誌

        Args:
            message: 日誌訊息
        """
        self.logger.debug(message)