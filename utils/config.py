"""
配置工具
管理系統配置參數
"""

import json
import os
import logging


class Config:
    """配置管理類別"""

    DEFAULT_CONFIG = {
        'target_count': 1000,
        'buffer_point': 950,
        'roi_height': 16,
        'roi_default_position': 0.2,  # ROI 線的預設位置（畫面高度的比例）
        'min_object_area': 10,
        'max_object_area': 150,
        'camera_width': 640,
        'camera_height': 480,
        'camera_fps': 30
    }

    def __init__(self, config_file="config.json"):
        """
        初始化配置管理器

        Args:
            config_file: 配置檔案名稱
        """
        self.config_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            config_file
        )
        self.config = self.load_config()

    def load_config(self):
        """
        載入配置

        Returns:
            dict: 配置字典
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return self.DEFAULT_CONFIG.copy()
        except Exception as e:
            logging.error(f"An error occurred while loading the configuration file：{str(e)}")
            return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        """儲存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"An error occurred while saving the configuration file：{str(e)}")

    def get(self, key, default=None):
        """
        獲取配置值

        Args:
            key: 配置鍵名
            default: 預設值

        Returns:
            配置值
        """
        return self.config.get(key, default)

    def set(self, key, value):
        """
        設置配置值

        Args:
            key: 配置鍵名
            value: 配置值
        """
        self.config[key] = value
        self.save_config()

    def update(self, new_config):
        """
        更新多個配置值

        Args:
            new_config: 新的配置字典
        """
        self.config.update(new_config)
        self.save_config()