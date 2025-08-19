#!/usr/bin/env python3
"""
透過主系統啟動合成調試功能
"""

import logging
import sys
import os

# 添加項目路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from basler_mvc.controllers.main_controller import MainController
from basler_mvc.views.main_view_ctk_bright import MainView

def setup_enhanced_debug_logging():
    """設置增強的調試日誌"""
    # 創建自定義格式器，包含更多調試信息
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    # 設置控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 設置文件處理器（調試日誌）
    file_handler = logging.FileHandler('basler_debug.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 配置根日誌器
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger().addHandler(console_handler)
    logging.getLogger().addHandler(file_handler)
    
    # 減少某些模組的日誌級別
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)

def enable_composite_debug_in_system(controller):
    """在主系統中啟用合成調試功能"""
    try:
        # 取得背景減除檢測方法
        detection_model = controller.detection_model
        
        if hasattr(detection_model, 'current_method'):
            method = detection_model.current_method
            
            # 檢查是否為背景減除檢測方法
            if hasattr(method, 'enable_composite_debug'):
                # 啟用合成調試
                method.enable_composite_debug(True)
                
                # 設置調試參數
                method.max_debug_frames = float('inf')  # 保存全部照片，不設限制
                
                # 獲取調試信息
                debug_info = method.get_composite_debug_info()
                
                print("🖼️ 合成調試功能已啟用!")
                print(f"   - 檢測方法: {method.name}")
                print(f"   - 最大幀數: {debug_info['max_frames']}")
                print(f"   - 保存目錄: {debug_info['save_directory']}")
                print(f"   - 布局: {debug_info['layout']}")
                
                return True
            else:
                print(f"⚠️ 當前檢測方法 ({method.name}) 不支援合成調試功能")
                return False
        else:
            print("❌ 無法取得檢測方法")
            return False
            
    except Exception as e:
        print(f"❌ 啟用合成調試功能失敗: {str(e)}")
        return False

def main():
    """主函數 - 啟動帶合成調試功能的主系統"""
    print("🚀 啟動 Real-time Item Monitoring System...")
    print("🖼️ 已整合合成調試功能 - 當切換到背景減除檢測時自動啟用")
    
    # 設置增強日誌
    setup_enhanced_debug_logging()
    
    try:
        # 創建主控制器
        print("🔧 初始化主控制器...")
        controller = MainController()
        
        # 檢查背景減除檢測是否可用
        detection_model = controller.detection_model
        if 'background' in detection_model.available_methods:
            print("✅ 背景減除檢測方法已載入")
            if detection_model.method_name == 'background':
                print("🎯 預設使用背景減除檢測（合成調試已整合）")
        else:
            print("⚠️ 背景減除檢測方法不可用")
        
        # 創建主視圖
        print("🖥️ 啟動主界面...")
        view = MainView(controller)
        
        print("✅ 系統啟動完成!")
        print("\n📋 使用說明:")
        print("1. 在右側控制面板選擇「背景減除檢測」")
        print("2. 連接相機或載入視頻")
        print("3. 開始檢測")
        print("4. 合成調試圖片會自動保存到: basler_mvc/recordings/composite_debug/")
        print("\n🎯 合成調試圖片特點:")
        print("   - 6-in-1 布局：原圖+ROI → 前景遮罩 → 檢測結果")
        print("   - 包含完整參數信息")
        print("   - 比分散圖片更容易分析")
        print("   - 顯著減少檔案數量")
        
        # 啟動UI主循環
        view.run()
        
    except KeyboardInterrupt:
        print("\n🛑 用戶中斷，正在關閉系統...")
    except Exception as e:
        print(f"❌ 系統啟動失敗: {str(e)}")
        logging.exception("系統啟動異常")
    finally:
        print("👋 系統已關閉")

if __name__ == "__main__":
    main()
