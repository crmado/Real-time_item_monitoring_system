"""
設定管理器
作為視圖層和邏輯層之間的中間層，用於管理所有設定
"""

import logging
import os
from typing import Dict, Any, List, Callable, Optional
from utils.config import Config


class SettingsManager:
    """
    設定管理器類別
    負責管理所有設定，並提供統一的介面給視圖層和邏輯層
    """

    def __init__(self, config_file: str = "settings.json"):
        """
        初始化設定管理器

        Args:
            config_file: 配置檔案名稱
        """
        self.config_manager = Config(config_file)
        self.observers: Dict[str, List[Callable]] = {}  # 觀察者模式，用於通知設定變更
        self.settings_cache: Dict[str, Any] = {}  # 設定快取，用於提高效能
        self._load_settings_to_cache()
        logging.info("設定管理器初始化完成")

    def _load_settings_to_cache(self):
        """載入所有設定到快取"""
        # 載入常用設定到快取
        self.settings_cache = {
            # 系統設定
            'language': self.config_manager.get('system.language', 'zh_TW'),
            'check_updates': self.config_manager.get('system.check_updates', True),
            'backup_config': self.config_manager.get('system.backup_config', True),
            
            # UI設定
            'theme': self.config_manager.get('ui.theme', 'light'),
            'font_size': self.config_manager.get('ui.font_size', 'medium'),
            'show_performance': self.config_manager.get('ui.show_performance', True),
            
            # 檢測設定
            'target_count': self.config_manager.get('detection.target_count', 1000),
            'buffer_point': self.config_manager.get('detection.buffer_point', 950),
            'roi_default_position': self.config_manager.get('detection.roi_default_position', 0.5),
            'min_object_area': self.config_manager.get('detection.min_object_area', 10),
            'max_object_area': self.config_manager.get('detection.max_object_area', 150),
        }
        logging.info("已載入設定到快取")

    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取設定值

        Args:
            key: 設定鍵名，例如 'target_count'
            default: 預設值

        Returns:
            設定值
        """
        # 優先從快取中獲取
        if key in self.settings_cache:
            return self.settings_cache[key]
        
        # 如果快取中沒有，嘗試從配置管理器獲取
        # 先嘗試使用帶前綴的鍵名
        if key in ['target_count', 'buffer_point', 'roi_default_position', 'min_object_area', 'max_object_area']:
            config_key = f'detection.{key}'
        elif key in ['language', 'check_updates', 'backup_config']:
            config_key = f'system.{key}'
        elif key in ['theme', 'font_size', 'show_performance']:
            config_key = f'ui.{key}'
        else:
            config_key = key
            
        value = self.config_manager.get(config_key, None)
        
        # 如果找不到帶前綴的鍵名，嘗試使用不帶前綴的鍵名
        if value is None:
            value = self.config_manager.get(key, default)
            
        # 更新快取
        if value is not None:
            self.settings_cache[key] = value
            
        return value

    def set(self, key: str, value: Any) -> bool:
        """
        設置設定值

        Args:
            key: 設定鍵名，例如 'target_count'
            value: 設定值

        Returns:
            bool: 是否成功設置
        """
        # 更新快取
        old_value = self.settings_cache.get(key)
        self.settings_cache[key] = value
        
        # 設置配置管理器中的值
        # 先轉換為帶前綴的鍵名
        if key in ['target_count', 'buffer_point', 'roi_default_position', 'min_object_area', 'max_object_area']:
            config_key = f'detection.{key}'
        elif key in ['language', 'check_updates', 'backup_config']:
            config_key = f'system.{key}'
        elif key in ['theme', 'font_size', 'show_performance']:
            config_key = f'ui.{key}'
        else:
            config_key = key
            
        result = self.config_manager.set(config_key, value)
        
        # 如果設置成功，通知觀察者
        if result and old_value != value:
            self._notify_observers(key, value)
            
        return result

    def update(self, settings: Dict[str, Any]) -> bool:
        """
        更新多個設定值

        Args:
            settings: 設定字典，格式為 {'key': value}

        Returns:
            bool: 是否全部成功更新
        """
        success = True
        updates = {}
        
        # 先更新快取並準備配置更新
        for key, value in settings.items():
            # 更新快取
            old_value = self.settings_cache.get(key)
            self.settings_cache[key] = value
            
            # 準備配置更新
            if key in ['target_count', 'buffer_point', 'roi_default_position', 'min_object_area', 'max_object_area']:
                config_key = f'detection.{key}'
            elif key in ['language', 'check_updates', 'backup_config']:
                config_key = f'system.{key}'
            elif key in ['theme', 'font_size', 'show_performance']:
                config_key = f'ui.{key}'
            else:
                config_key = key
                
            updates[config_key] = value
            
            # 如果值有變更，通知觀察者
            if old_value != value:
                self._notify_observers(key, value)
        
        # 批次更新配置
        if updates:
            success = self.config_manager.update(updates)
            
        return success

    def register_observer(self, key: str, callback: Callable[[str, Any], None]):
        """
        註冊設定變更觀察者

        Args:
            key: 設定鍵名，例如 'target_count'
            callback: 回調函數，接收鍵名和新值作為參數
        """
        if key not in self.observers:
            self.observers[key] = []
        self.observers[key].append(callback)
        logging.info(f"已註冊設定 '{key}' 的觀察者")

    def unregister_observer(self, key: str, callback: Callable[[str, Any], None]):
        """
        取消註冊設定變更觀察者

        Args:
            key: 設定鍵名，例如 'target_count'
            callback: 回調函數
        """
        if key in self.observers and callback in self.observers[key]:
            self.observers[key].remove(callback)
            logging.info(f"已取消註冊設定 '{key}' 的觀察者")

    def _notify_observers(self, key: str, value: Any):
        """
        通知設定變更觀察者

        Args:
            key: 設定鍵名
            value: 新的設定值
        """
        if key in self.observers:
            for callback in self.observers[key]:
                try:
                    callback(key, value)
                except Exception as e:
                    logging.error(f"通知設定 '{key}' 的觀察者時出錯：{str(e)}")

    def get_all_settings(self) -> Dict[str, Any]:
        """
        獲取所有設定

        Returns:
            Dict[str, Any]: 所有設定的字典
        """
        return self.settings_cache.copy()

    def reset_to_default(self) -> bool:
        """
        重設所有設定為預設值

        Returns:
            bool: 是否成功重設
        """
        result = self.config_manager.reset_to_default()
        if result:
            # 重新載入設定到快取
            self._load_settings_to_cache()
            
            # 通知所有觀察者
            for key, value in self.settings_cache.items():
                self._notify_observers(key, value)
                
        return result

    def save(self) -> bool:
        """
        保存設定

        Returns:
            bool: 是否成功保存
        """
        return self.config_manager.save_config()


# 全局設定管理器實例
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """
    獲取全局設定管理器實例

    Returns:
        SettingsManager: 設定管理器實例
    """
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager 