#!/usr/bin/env python3
"""
設定同步測試腳本
用於驗證設定面板和設定對話框之間的數值同步
"""

import os
import sys
import logging
import json

# 設定日誌格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 檢查設定檔案
def check_settings_file():
    """檢查設定檔案是否存在"""
    settings_path = os.path.join('config', 'settings.json')
    if os.path.exists(settings_path):
        logging.info(f"設定檔案存在: {settings_path}")
        
        # 讀取設定檔案
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                logging.info(f"設定檔案內容: {settings}")
                
                # 檢查關鍵設定值
                target_count = settings.get('target_count')
                buffer_point = settings.get('buffer_point')
                
                logging.info(f"目標數量: {target_count}, 緩衝點: {buffer_point}")
                
                return settings
        except Exception as e:
            logging.error(f"讀取設定檔案時出錯: {str(e)}")
            return None
    else:
        logging.warning(f"設定檔案不存在: {settings_path}")
        return None

# 主函數
def main():
    """主函數"""
    logging.info("開始測試設定同步")
    
    # 檢查設定檔案
    settings = check_settings_file()
    if not settings:
        logging.error("無法繼續測試，設定檔案不存在或無法讀取")
        return
    
    # 檢查設定值是否合理
    target_count = settings.get('target_count')
    buffer_point = settings.get('buffer_point')
    
    if not target_count or not buffer_point:
        logging.error("設定值不完整，缺少目標數量或緩衝點")
        return
    
    if buffer_point >= target_count:
        logging.warning("設定值不合理，緩衝點應小於目標數量")
    
    logging.info("設定同步測試完成")

if __name__ == "__main__":
    main() 