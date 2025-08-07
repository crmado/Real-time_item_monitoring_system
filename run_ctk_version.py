#!/usr/bin/env python3
"""
Basler MVC CustomTkinter 版本快速啟動腳本
解決跨平台顯示模糊問題
"""

import sys
import os
from pathlib import Path

def main():
    """主函數"""
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