"""
配置工具
管理系統配置參數 - 改進版本
"""

import json
import os
import logging
import yaml
import shutil

from utils.exceptions import ConfigError, InvalidSettingError


class Config:
    """
    /// 配置管理類別
    /// 功能結構：
    /// 第一部分：基本屬性和初始化
    /// 第二部分：配置加載與保存
    /// 第三部分：配置讀取與設置
    /// 第四部分：配置驗證與修復
    /// 第五部分：工具方法
    """

    #==========================================================================
    # 第一部分：基本屬性和初始化
    #==========================================================================

    DEFAULT_CONFIG = {
        'system': {
            'language': 'zh_TW',            # 預設語言
            'check_updates': True,          # 是否自動檢查更新
            'log_level': 'INFO',            # 預設日誌等級
            'backup_config': True           # 是否在修改前備份配置
        },
        'camera': {
            'default_width': 640,           # 預設相機寬度
            'default_height': 480,          # 預設相機高度
            'default_fps': 30,              # 預設相機 FPS
            'auto_reconnect': True,         # 是否自動重連相機
            'reconnect_timeout': 5,         # 重連超時秒數
            'preferred_source': None,       # 預設選用的相機
            'last_source': None             # 最後使用的相機源
        },
        'detection': {
            'target_count': 1000,           # 預設預計數量
            'buffer_point': 950,            # 預設緩衝點
            'roi_height': 16,               # ROI 高度
            'roi_default_position': 0.2,    # ROI 線的預設位置（畫面高度的比例）
            'min_object_area': 10,          # 最小物件面積
            'max_object_area': 150,         # 最大物件面積
            'track_tolerance_x': 64,        # X 軸追蹤容許誤差
            'track_tolerance_y': 48,        # Y 軸追蹤容許誤差
            'canny_threshold1': 50,         # Canny 檢測器閾值 1
            'canny_threshold2': 110,        # Canny 檢測器閾值 2
            'binary_threshold': 30,         # 二值化閾值
            'bg_history': 20000,            # 背景模型歷史
            'bg_threshold': 16,             # 背景模型閾值
            'detect_shadows': True          # 是否檢測陰影
        },
        'ui': {
            'theme': 'system',              # UI 主題 (system, light, dark)
            'font_size': 'medium',          # 字體大小 (small, medium, large)
            'show_performance': True,       # 是否顯示效能資訊
            'video_quality': 'high',        # 視訊顯示品質 (low, medium, high)
            'roi_line_color': '#00FF00',    # ROI 線顏色
            'object_box_color': '#FF0000',  # 物件邊框顏色
            'window_state': {               # 視窗狀態
                'width': 800,               # 視窗寬度
                'height': 600,              # 視窗高度
                'position_x': None,         # 視窗 X 位置
                'position_y': None          # 視窗 Y 位置
            }
        },
        'photo_analysis': {
            'save_captured': True,  # 是否保存拍攝的照片
            'save_directory': 'captured_images',  # 保存目錄
            'min_circle_radius': 50,  # 最小圓形半徑
            'max_circle_radius': 300,  # 最大圓形半徑
            'quality_threshold': 9.0,  # 質量閾值
            'auto_analyze': True  # 拍照後自動分析
        }
    }

    def __init__(self, config_file="config.yaml"):
        """
        初始化配置管理器

        Args:
            config_file: 配置檔案名稱
        """
        self.config_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config"
        )

        # 確保配置目錄存在
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        self.config_file = os.path.join(self.config_dir, config_file)
        self.config = self.load_config()
        
        # 檢查配置有效性
        self._check_and_repair_config()

    #==========================================================================
    # 第二部分：配置加載與保存
    #==========================================================================
        
    def load_config(self):
        """
        載入配置 - 支援多種檔案格式

        Returns:
            dict: 配置字典
        """
        config = self.DEFAULT_CONFIG.copy()

        try:
            if os.path.exists(self.config_file):
                # 根據副檔名選擇載入方式
                ext = os.path.splitext(self.config_file)[1].lower()

                with open(self.config_file, 'r', encoding='utf-8') as f:
                    if ext == '.yaml' or ext == '.yml':
                        file_config = yaml.safe_load(f)
                    elif ext == '.json':
                        file_config = json.load(f)
                    else:
                        logging.warning(f"不支援的配置文件格式：{ext}，使用預設配置")
                        return config

                # 深度合併配置
                self._deep_update(config, file_config)
                logging.info(f"已從 {self.config_file} 載入配置")
            else:
                # 建立預設配置文件
                self.save_config(config)
                logging.info(f"已建立預設配置文件：{self.config_file}")

            return config

        except Exception as e:
            logging.error(f"載入配置文件時發生錯誤：{str(e)}")
            return config

    def save_config(self, config=None):
        """
        儲存配置

        Args:
            config: 要儲存的配置，預設為目前的配置
        """
        if config is None:
            config = self.config

        try:
            # 備份原有配置
            if os.path.exists(self.config_file) and self.get('system.backup_config', True):
                backup_file = f"{self.config_file}.bak"
                shutil.copy2(self.config_file, backup_file)
                logging.info(f"已備份配置到 {backup_file}")

            # 根據副檔名選擇儲存方式
            ext = os.path.splitext(self.config_file)[1].lower()

            with open(self.config_file, 'w', encoding='utf-8') as f:
                if ext == '.yaml' or ext == '.yml':
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                elif ext == '.json':
                    f.write(json.dumps(config, indent=4, ensure_ascii=False))
                else:
                    # 預設使用 YAML 格式
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            logging.info(f"已儲存配置到 {self.config_file}")
            return True

        except Exception as e:
            logging.error(f"儲存配置文件時發生錯誤：{str(e)}")
            return False
            
    #==========================================================================
    # 第三部分：配置讀取與設置
    #==========================================================================

    def get(self, key_path, default=None):
        """
        獲取配置值 - 支援層級路徑

        Args:
            key_path: 配置鍵路徑，例如 'detection.roi_height'
            default: 預設值

        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            if default is not None:
                return default
            raise ConfigError(f"找不到配置項：{key_path}", key_path)

    def set(self, key_path, value):
        """
        設置配置值 - 支援層級路徑

        Args:
            key_path: 配置鍵路徑，例如 'detection.roi_height'
            value: 配置值

        Returns:
            bool: 是否成功設置
        """
        keys = key_path.split('.')
        target = self.config

        # 驗證配置有效性
        if not self._validate_setting(key_path, value):
            return False

        try:
            # 遍歷路徑直到最後一個鍵
            for i, key in enumerate(keys[:-1]):
                if key not in target:
                    target[key] = {}
                target = target[key]

            # 設置最後一個鍵的值
            target[keys[-1]] = value

            # 儲存配置
            return self.save_config()

        except Exception as e:
            logging.error(f"設置配置 {key_path} 時發生錯誤：{str(e)}")
            return False

    def update(self, updates, save=True):
        """
        更新多個配置值

        Args:
            updates: 格式為 {'section.key': value} 或 {'section': {key: value}} 的更新字典
            save: 是否立即儲存更新

        Returns:
            bool: 是否全部成功更新
        """
        success = True

        for key_path, value in updates.items():
            # 對於點分隔的路徑，使用set方法，否則進行直接更新
            if '.' in key_path:
                if not self.set(key_path, value):
                    success = False
            else:
                # 處理字典形式的更新
                if isinstance(value, dict) and key_path in self.config and isinstance(self.config[key_path], dict):
                    self._deep_update(self.config[key_path], value)
                else:
                    self.config[key_path] = value

        # 如果需要儲存且尚未在set中儲存
        if save and success:
            return self.save_config()

        return success

    def get_section(self, section):
        """
        獲取完整配置區段

        Args:
            section: 區段名稱

        Returns:
            dict: 區段配置字典
        """
        if section in self.config:
            return self.config[section]
        return {}

    def reset_to_default(self, section=None):
        """
        重設配置為預設值

        Args:
            section: 要重設的區段，None 表示全部重設

        Returns:
            bool: 是否成功重設
        """
        try:
            if section is None:
                self.config = self.DEFAULT_CONFIG.copy()
                logging.info("已重設所有配置為預設值")
            elif section in self.DEFAULT_CONFIG:
                self.config[section] = self.DEFAULT_CONFIG[section].copy()
                logging.info(f"已重設區段 {section} 為預設值")
            else:
                logging.warning(f"找不到區段 {section}")
                return False

            return self.save_config()

        except Exception as e:
            logging.error(f"重設配置時發生錯誤：{str(e)}")
            return False
            
    #==========================================================================
    # 第四部分：配置驗證與修復
    #==========================================================================
            
    def _check_and_repair_config(self):
        """檢查配置完整性並自動修復"""
        repaired = False
        
        # 檢查並修復缺失的頂層節點
        for section in self.DEFAULT_CONFIG:
            if section not in self.config:
                self.config[section] = self.DEFAULT_CONFIG[section].copy()
                logging.warning(f"修復缺失的配置區段：{section}")
                repaired = True
                
        # 檢查並修復各區段中缺失的配置項
        for section, section_config in self.DEFAULT_CONFIG.items():
            if section in self.config:
                for key, value in section_config.items():
                    if key not in self.config[section]:
                        self.config[section][key] = value
                        logging.warning(f"修復缺失的配置項：{section}.{key}")
                        repaired = True
        
        # 如果有修復，保存配置
        if repaired:
            self.save_config()
            
    def _validate_setting(self, key_path, value):
        """
        驗證配置值的有效性

        Args:
            key_path: 配置鍵路徑
            value: 配置值

        Returns:
            bool: 是否有效
        """
        try:
            # 檢查常見配置項
            if key_path == 'detection.target_count':
                if not isinstance(value, int) or value <= 0:
                    raise InvalidSettingError("預計數量必須為正整數", key_path)

            elif key_path == 'detection.buffer_point':
                if not isinstance(value, int) or value < 0:
                    raise InvalidSettingError("緩衝點必須為非負整數", key_path)
                # 檢查緩衝點是否小於目標數量
                target_count = self.get('detection.target_count', 1000)
                if value >= target_count:
                    raise InvalidSettingError("緩衝點必須小於預計數量", key_path)

            elif key_path == 'detection.roi_height':
                if not isinstance(value, int) or value <= 0:
                    raise InvalidSettingError("ROI 高度必須為正整數", key_path)

            elif key_path == 'detection.roi_default_position':
                if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                    raise InvalidSettingError("ROI 預設位置必須為 0 到 1 之間的數值", key_path)

            elif key_path == 'camera.default_fps':
                if not isinstance(value, (int, float)) or value <= 0:
                    raise InvalidSettingError("FPS 必須為正數", key_path)

            elif key_path == 'system.language':
                # 語言代碼格式驗證
                if not isinstance(value, str) or not (len(value) == 5 and value[2] == '_'):
                    raise InvalidSettingError("語言代碼格式必須為 'xx_XX'", key_path)

            return True

        except InvalidSettingError as e:
            logging.error(str(e))
            return False
            
    #==========================================================================
    # 第五部分：工具方法
    #==========================================================================

    def _deep_update(self, target_dict, source_dict):
        """遞迴更新字典"""
        for key, value in source_dict.items():
            if isinstance(value, dict) and key in target_dict and isinstance(target_dict[key], dict):
                self._deep_update(target_dict[key], value)
            else:
                target_dict[key] = value
                
    def save_window_state(self, width, height, x=None, y=None):
        """
        保存視窗狀態

        Args:
            width: 視窗寬度
            height: 視窗高度
            x: 視窗X座標
            y: 視窗Y座標
        """
        self.config['ui']['window_state'] = {
            'width': width,
            'height': height,
            'position_x': x,
            'position_y': y
        }
        self.save_config()
        
    def save_last_camera_source(self, source):
        """
        保存最後使用的相機源

        Args:
            source: 相機源名稱
        """
        self.set('camera.last_source', source)

    @classmethod
    def initialize_system(cls):
        """
        初始化系統配置
        :return:
        """
        config_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config"
        )
        config_file = os.path.join(config_dir, "config.yaml")

        # 確保配置目錄存在
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # 創建預設配置文件

        if not os.path.exists(config_file):
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(cls.DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True)
            logging.info(f"已建立預設配置文件：{config_file}")
        else:

            logging.info(f"配置文件已存在：{config_file}")

        return config_file
