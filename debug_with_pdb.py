#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
使用 Python 內建 debugger (pdb) 的啟動程式
"""

import os
import sys
import pdb
import logging
from datetime import datetime

# 添加專案根目錄到系統路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_pdb_logging():
    """設置 pdb 模式的日誌配置"""
    # 確保 logs 資料夾存在
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # 根據當前日期和時間生成日誌檔案名稱
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_filename = os.path.join(logs_dir, f"pdb_{timestamp}.log")

    # 配置日誌
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )

    print(f"PDB 日誌檔案: {log_filename}")
    return log_filename

def main():
    """使用 PDB 的主程式"""
    print("=" * 60)
    print("即時物品監測系統 - PDB Debug 模式")
    print("=" * 60)
    print("PDB 命令說明:")
    print("  n (next) - 執行下一行")
    print("  s (step) - 步入函數")
    print("  c (continue) - 繼續執行")
    print("  l (list) - 顯示當前代碼")
    print("  p variable - 打印變數值")
    print("  q (quit) - 退出 debugger")
    print("=" * 60)
    
    # 設置日誌
    log_file = setup_pdb_logging()
    
    try:
        # 導入模組
        print("載入模組...")
        from models.camera_manager import CameraManager
        from controllers.system_controller import SystemController
        from views.main_window import MainWindow
        from utils.ui_style_manager import UIStyleManager
        from utils.language import set_language, get_text
        
        import tkinter as tk
        
        print("模組載入完成")
        
        # 設置斷點 - 在關鍵位置設置斷點
        print("設置斷點位置...")
        
        # 創建Tkinter根窗口
        print("創建Tkinter根窗口...")
        root = tk.Tk()
        root.title(get_text("app_title", "實時物品監測系統") + " (PDB Debug)")
        root.geometry("1200x800")
        root.minsize(1000, 700)
        
        # 設置語言
        print("設置語言...")
        set_language("zh_TW")
        
        # 初始化UI樣式
        print("初始化UI樣式...")
        ui_style_manager = UIStyleManager(root)
        ui_style_manager.apply_theme()
        
        # 創建主窗口
        print("創建主窗口...")
        main_window = MainWindow(root)
        
        # 創建系統控制器
        print("創建系統控制器...")
        system_controller = SystemController(main_window)
        
        # 設置主窗口的系統控制器
        print("設置主窗口的系統控制器...")
        main_window.set_system_controller(system_controller)
        
        # 啟動UI更新
        print("啟動UI更新...")
        system_controller.start_ui_update()
        
        print("✓ 程式初始化完成")
        print("✓ 準備進入 PDB debugger...")
        
        # 進入 PDB debugger
        pdb.set_trace()
        
        # 運行主循環
        print("運行主循環...")
        root.mainloop()
        
    except Exception as e:
        logging.error(f"程式啟動時發生錯誤: {str(e)}")
        print(f"\n❌ 錯誤: {str(e)}")
        print(f"詳細錯誤資訊已記錄到: {log_file}")
        import traceback
        traceback.print_exc()
        
        # 在錯誤處進入 PDB
        print("在錯誤處進入 PDB debugger...")
        pdb.post_mortem()

if __name__ == "__main__":
    main() 