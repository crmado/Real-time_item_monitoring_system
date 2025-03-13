#!/usr/bin/env python3
"""
設定管理器測試腳本
用於測試新的設定管理器
"""

import os
import sys
import logging
import json
from utils.settings_manager import get_settings_manager

# 設定日誌格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_settings_manager():
    """測試設定管理器"""
    logging.info("開始測試設定管理器")
    
    # 獲取設定管理器
    settings_manager = get_settings_manager()
    
    # 獲取所有設定
    all_settings = settings_manager.get_all_settings()
    logging.info(f"所有設定: {all_settings}")
    
    # 測試獲取單個設定
    target_count = settings_manager.get('target_count', 1000)
    buffer_point = settings_manager.get('buffer_point', 950)
    logging.info(f"目標數量: {target_count}, 緩衝點: {buffer_point}")
    
    # 測試設置單個設定
    new_target_count = target_count + 10
    result = settings_manager.set('target_count', new_target_count)
    logging.info(f"設置目標數量為 {new_target_count}: {'成功' if result else '失敗'}")
    
    # 測試獲取更新後的設定
    updated_target_count = settings_manager.get('target_count')
    logging.info(f"更新後的目標數量: {updated_target_count}")
    
    # 測試觀察者模式
    def on_target_count_changed(key, value):
        logging.info(f"觀察者收到通知: {key} = {value}")
    
    # 註冊觀察者
    settings_manager.register_observer('target_count', on_target_count_changed)
    
    # 再次更新設定，觀察者應該會收到通知
    new_target_count = updated_target_count + 10
    settings_manager.set('target_count', new_target_count)
    
    # 測試批次更新設定
    settings = {
        'target_count': 1000,
        'buffer_point': 950
    }
    result = settings_manager.update(settings)
    logging.info(f"批次更新設定: {'成功' if result else '失敗'}")
    
    # 測試獲取更新後的設定
    updated_target_count = settings_manager.get('target_count')
    updated_buffer_point = settings_manager.get('buffer_point')
    logging.info(f"更新後的目標數量: {updated_target_count}, 緩衝點: {updated_buffer_point}")
    
    # 取消註冊觀察者
    settings_manager.unregister_observer('target_count', on_target_count_changed)
    
    logging.info("設定管理器測試完成")

if __name__ == "__main__":
    test_settings_manager() 