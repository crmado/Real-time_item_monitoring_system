#!/usr/bin/env python3
"""
Basler MVC 統一啟動腳本
支援正常模式和調試模式
解決跨平台顯示模糊問題
"""

import sys
import os
import argparse
import logging
from pathlib import Path

def setup_debug_logging():
    """設置調試模式的日誌"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug.log')
        ]
    )
    print("🔍 調試模式已啟用 - 日誌將保存到 debug.log")

def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='Basler MVC 系統啟動器')
    parser.add_argument('--debug', action='store_true', help='啟用調試模式')
    args = parser.parse_args()
    
    if args.debug:
        print("🔍 啟動 Basler MVC 調試模式")
        setup_debug_logging()
    else:
        print("🚀 啟動 Basler MVC CustomTkinter 高清版本")
    
    print("=" * 50)
    
    # 檢查必要依賴
    try:
        import customtkinter
        print("✅ CustomTkinter 已安裝")
    except ImportError:
        print("❌ 缺少 CustomTkinter，正在安裝...")
        os.system("pip install customtkinter")
        print("✅ CustomTkinter 安裝完成")
    
    try:
        import cv2
        print("✅ OpenCV 已安裝")
    except ImportError:
        print("❌ 缺少 OpenCV")
        return
    
    try:
        from pypylon import pylon
        print("✅ Basler pypylon 已安裝")
    except ImportError:
        print("⚠️ 缺少 pypylon，如需使用 Basler 相機請安裝: pip install pypylon")
    
    print("=" * 50)
    
    # 切換到 basler_mvc 目錄
    basler_mvc_path = Path(__file__).parent / "basler_mvc"
    if basler_mvc_path.exists():
        os.chdir(basler_mvc_path)
        print(f"📂 切換到目錄: {basler_mvc_path}")
    else:
        print(f"❌ 找不到 basler_mvc 目錄: {basler_mvc_path}")
        return
    
    # 執行主程式
    try:
        print("🎮 啟動 CustomTkinter 高清界面...")
        os.system("python main.py")
    except KeyboardInterrupt:
        print("\n👋 用戶中斷，程式結束")
    except Exception as e:
        print(f"❌ 執行錯誤: {str(e)}")

if __name__ == "__main__":
    main()