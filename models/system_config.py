"""
系統配置模型
處理系統層級的設定和初始化
"""

import os
import sys
import locale
import logging
import datetime


class SystemConfig:
    """系統配置類別"""

    @staticmethod
    def setup_opencv_paths():
        """設定 OpenCV 路徑"""
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cv2_bin_path = os.path.join(script_dir, 'bin')
        cv2_lib_path = os.path.join(script_dir, 'lib')

        if os.path.exists(cv2_bin_path):
            os.environ['PATH'] = cv2_bin_path + os.pathsep + os.environ['PATH']
        if os.path.exists(cv2_lib_path):
            os.environ['PATH'] = cv2_lib_path + os.pathsep + os.environ['PATH']

    @staticmethod
    def setup_system_encoding():
        """設定系統編碼"""
        if hasattr(sys, 'setdefaultencoding'):
            sys.setdefaultencoding('utf-8')
        locale.setlocale(locale.LC_ALL, 'zh_TW.UTF-8')

    @staticmethod
    def setup_logging():
        """設定日誌系統"""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = os.path.join(
            log_dir,
            f"detection_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    @classmethod
    def initialize_system(cls):
        """初始化系統設定"""
        cls.setup_opencv_paths()
        cls.setup_system_encoding()
        cls.setup_logging()