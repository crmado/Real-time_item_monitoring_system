#!/usr/bin/env python3
"""
配置管理器 - 支援熱重載和動態配置
提供運行時配置變更和回滾功能
"""

import logging
import threading
import time
import json
from typing import Dict, Any, Optional, Callable, List
from pathlib import Path
from dataclasses import dataclass, asdict
from copy import deepcopy

@dataclass
class ConfigChange:
    """配置變更記錄"""
    timestamp: float
    section: str
    key: str
    old_value: Any
    new_value: Any
    source: str  # 'api', 'file', 'ui', etc.

class ConfigManager:
    """配置管理器 - 支援熱重載和歷史追蹤"""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置檔案路徑
        """
        self.config_file = config_file
        self.config_data = {}
        self.config_lock = threading.RLock()
        
        # 變更歷史
        self.change_history: List[ConfigChange] = []
        self.max_history_size = 100
        
        # 回調函數
        self.change_callbacks: Dict[str, List[Callable]] = {}
        self.validation_callbacks: Dict[str, Callable] = {}
        
        # 備份配置（用於回滾）
        self.config_backup = {}
        
        # 檔案監控（如果需要）
        self.file_monitor_enabled = False
        self.monitor_thread = None
        self.stop_monitoring = threading.Event()
        
        logging.info("配置管理器初始化完成")
    
    def load_config(self, config_dict: Dict[str, Any]):
        """載入配置"""
        with self.config_lock:
            self.config_backup = deepcopy(self.config_data)
            self.config_data = deepcopy(config_dict)
            logging.info("配置已載入")
    
    def get_config(self, section: str = None, key: str = None) -> Any:
        """
        獲取配置值
        
        Args:
            section: 配置節名
            key: 配置鍵名
            
        Returns:
            配置值
        """
        with self.config_lock:
            if section is None:
                return deepcopy(self.config_data)
            
            if section not in self.config_data:
                return None
            
            if key is None:
                return deepcopy(self.config_data[section])
            
            return deepcopy(self.config_data[section].get(key))
    
    def set_config(self, section: str, key: str, value: Any, source: str = 'api') -> bool:
        """
        設置配置值
        
        Args:
            section: 配置節名
            key: 配置鍵名
            value: 新值
            source: 變更來源
            
        Returns:
            是否成功
        """
        with self.config_lock:
            # 驗證配置
            if not self._validate_config_change(section, key, value):
                logging.error(f"配置驗證失敗: {section}.{key} = {value}")
                return False
            
            # 獲取舊值
            old_value = None
            if section in self.config_data and key in self.config_data[section]:
                old_value = self.config_data[section][key]
            
            # 確保節存在
            if section not in self.config_data:
                self.config_data[section] = {}
            
            # 設置新值
            self.config_data[section][key] = value
            
            # 記錄變更
            change = ConfigChange(
                timestamp=time.time(),
                section=section,
                key=key,
                old_value=old_value,
                new_value=value,
                source=source
            )
            
            self._add_change_history(change)
            
            # 觸發回調
            self._trigger_callbacks(section, key, old_value, value)
            
            logging.info(f"配置已更新: {section}.{key} = {value} (來源: {source})")
            return True
    
    def update_section(self, section: str, updates: Dict[str, Any], source: str = 'api') -> bool:
        """
        批量更新配置節
        
        Args:
            section: 配置節名
            updates: 更新字典
            source: 變更來源
            
        Returns:
            是否全部成功
        """
        success_count = 0
        for key, value in updates.items():
            if self.set_config(section, key, value, source):
                success_count += 1
        
        return success_count == len(updates)
    
    def rollback_config(self) -> bool:
        """回滾到上次備份的配置"""
        with self.config_lock:
            if not self.config_backup:
                logging.warning("沒有可回滾的配置備份")
                return False
            
            old_config = deepcopy(self.config_data)
            self.config_data = deepcopy(self.config_backup)
            
            logging.info("配置已回滾到上次備份")
            
            # 觸發全局變更回調
            self._trigger_global_callbacks(old_config, self.config_data)
            return True
    
    def save_to_file(self, file_path: Optional[Path] = None) -> bool:
        """
        保存配置到檔案
        
        Args:
            file_path: 檔案路徑，如果未提供則使用默認路徑
            
        Returns:
            是否成功
        """
        target_file = file_path or self.config_file
        if not target_file:
            logging.error("未指定配置檔案路徑")
            return False
        
        try:
            with self.config_lock:
                # 確保目錄存在
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 保存配置
                with open(target_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config_data, f, ensure_ascii=False, indent=2)
                
                logging.info(f"配置已保存到: {target_file}")
                return True
                
        except Exception as e:
            logging.error(f"保存配置失敗: {str(e)}")
            return False
    
    def load_from_file(self, file_path: Optional[Path] = None) -> bool:
        """
        從檔案載入配置
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            是否成功
        """
        source_file = file_path or self.config_file
        if not source_file or not source_file.exists():
            logging.error(f"配置檔案不存在: {source_file}")
            return False
        
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
            
            self.load_config(new_config)
            logging.info(f"配置已從檔案載入: {source_file}")
            return True
            
        except Exception as e:
            logging.error(f"載入配置失敗: {str(e)}")
            return False
    
    def register_change_callback(self, section: str, callback: Callable):
        """
        註冊配置變更回調
        
        Args:
            section: 要監聽的配置節
            callback: 回調函數 callback(section, key, old_value, new_value)
        """
        if section not in self.change_callbacks:
            self.change_callbacks[section] = []
        
        self.change_callbacks[section].append(callback)
        logging.info(f"已註冊配置變更回調: {section}")
    
    def register_validation_callback(self, section: str, callback: Callable):
        """
        註冊配置驗證回調
        
        Args:
            section: 要驗證的配置節
            callback: 驗證函數 callback(key, value) -> bool
        """
        self.validation_callbacks[section] = callback
        logging.info(f"已註冊配置驗證回調: {section}")
    
    def get_change_history(self, section: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取配置變更歷史
        
        Args:
            section: 過濾特定配置節
            limit: 限制數量
            
        Returns:
            變更歷史列表
        """
        with self.config_lock:
            history = self.change_history[-limit:] if limit else self.change_history
            
            if section:
                history = [change for change in history if change.section == section]
            
            return [asdict(change) for change in history]
    
    def _validate_config_change(self, section: str, key: str, value: Any) -> bool:
        """驗證配置變更"""
        if section in self.validation_callbacks:
            try:
                return self.validation_callbacks[section](key, value)
            except Exception as e:
                logging.error(f"配置驗證回調執行失敗: {str(e)}")
                return False
        
        return True
    
    def _add_change_history(self, change: ConfigChange):
        """添加變更歷史"""
        self.change_history.append(change)
        
        # 限制歷史大小
        if len(self.change_history) > self.max_history_size:
            self.change_history = self.change_history[-self.max_history_size:]
    
    def _trigger_callbacks(self, section: str, key: str, old_value: Any, new_value: Any):
        """觸發配置變更回調"""
        if section in self.change_callbacks:
            for callback in self.change_callbacks[section]:
                try:
                    callback(section, key, old_value, new_value)
                except Exception as e:
                    logging.error(f"配置變更回調執行失敗: {str(e)}")
    
    def _trigger_global_callbacks(self, old_config: Dict, new_config: Dict):
        """觸發全局配置變更回調"""
        # 比較配置差異並觸發相應回調
        for section in set(old_config.keys()) | set(new_config.keys()):
            old_section = old_config.get(section, {})
            new_section = new_config.get(section, {})
            
            for key in set(old_section.keys()) | set(new_section.keys()):
                old_value = old_section.get(key)
                new_value = new_section.get(key)
                
                if old_value != new_value:
                    self._trigger_callbacks(section, key, old_value, new_value)
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取配置管理器統計信息"""
        with self.config_lock:
            return {
                'config_sections': len(self.config_data),
                'total_keys': sum(len(section) for section in self.config_data.values()),
                'change_history_size': len(self.change_history),
                'registered_callbacks': {
                    section: len(callbacks) 
                    for section, callbacks in self.change_callbacks.items()
                },
                'validation_callbacks': len(self.validation_callbacks),
                'has_backup': bool(self.config_backup)
            }


# 全局配置管理器實例
_global_config_manager: Optional[ConfigManager] = None


def get_global_config_manager() -> ConfigManager:
    """獲取全局配置管理器實例"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


def init_config_manager(config_dict: Dict[str, Any], config_file: Optional[Path] = None):
    """初始化全局配置管理器"""
    global _global_config_manager
    _global_config_manager = ConfigManager(config_file)
    _global_config_manager.load_config(config_dict)


def hot_reload_config(section: str, updates: Dict[str, Any]) -> bool:
    """熱重載配置的便捷函數"""
    manager = get_global_config_manager()
    return manager.update_section(section, updates, source='hot_reload')