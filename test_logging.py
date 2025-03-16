"""
測試日誌系統
"""

import os
import logging
import sys
from datetime import datetime

# 確保 logs 資料夾存在
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# 根據當前日期生成日誌檔案名稱
log_filename = os.path.join(logs_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_filename, encoding='utf-8')
    ]
)

# 定義日誌類型前綴
LOG_INFO = "[資訊] "
LOG_WARNING = "[警告] "
LOG_ERROR = "[錯誤] "
LOG_DEBUG = "[除錯] "

def main():
    """測試日誌系統"""
    logging.info(f"{LOG_INFO}測試日誌系統開始")
    logging.debug(f"{LOG_DEBUG}這是一條除錯訊息")
    logging.info(f"{LOG_INFO}這是一條資訊訊息")
    logging.warning(f"{LOG_WARNING}這是一條警告訊息")
    logging.error(f"{LOG_ERROR}這是一條錯誤訊息")
    logging.critical(f"[嚴重] 這是一條嚴重錯誤訊息")
    
    # 檢查日誌檔案是否已創建
    if os.path.exists(log_filename):
        print(f"日誌檔案已創建: {log_filename}")
        print(f"檔案大小: {os.path.getsize(log_filename)} 位元組")
    else:
        print(f"日誌檔案未創建: {log_filename}")
    
    logging.info(f"{LOG_INFO}測試日誌系統結束")

if __name__ == "__main__":
    main() 