#!/usr/bin/env python3
"""
🚀 超高速檢測模式示例 - 專為206-376fps設計
展示如何啟用和使用超高速檢測模式以達到最高性能
"""

import sys
import os
import time
import logging

# 添加項目路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from controllers.main_controller import MainController

def main():
    """超高速檢測示例"""
    
    # 設置日誌級別
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🚀 超高速檢測模式示例")
    print("=" * 50)
    
    # 初始化控制器
    controller = MainController()
    
    try:
        # 1. 檢查當前檢測速度狀態
        print("\n📊 當前檢測速度狀態:")
        speed_info = controller.get_detection_speed_info()
        
        print(f"相機FPS: {speed_info.get('camera_fps', 0):.1f}")
        print(f"檢測FPS: {speed_info.get('detection_fps', 0):.1f}")
        print(f"速度比率: {speed_info.get('speed_ratio', 0):.2f}")
        print(f"性能等級: {speed_info.get('performance_grade', 'Unknown')}")
        print(f"高速模式: {'啟用' if speed_info.get('ultra_high_speed_enabled') else '禁用'}")
        
        # 2. 根據需求啟用超高速模式
        print("\n🚀 啟用超高速檢測模式...")
        
        # 選項A: 自動配置 (根據相機規格)
        controller.auto_configure_detection_speed()
        
        # 選項B: 手動指定目標FPS
        # controller.enable_ultra_high_speed_detection(True, target_fps=280)
        
        # 選項C: 特定規格
        # controller.enable_ultra_high_speed_detection(True, target_fps=376)  # 376fps模式
        # controller.enable_ultra_high_speed_detection(True, target_fps=280)  # 280fps模式  
        # controller.enable_ultra_high_speed_detection(True, target_fps=206)  # 206fps模式
        
        # 3. 驗證高速模式狀態
        print("\n✅ 高速模式配置後狀態:")
        speed_info = controller.get_detection_speed_info()
        
        print(f"高速模式: {'✅ 已啟用' if speed_info.get('ultra_high_speed_enabled') else '❌ 未啟用'}")
        
        if speed_info.get('ultra_high_speed_enabled'):
            ultra_status = speed_info.get('ultra_high_speed_status', {})
            print(f"目標FPS: {ultra_status.get('target_fps', 'Unknown')}")
            print(f"優化狀態: {ultra_status.get('optimizations', {})}")
        
        # 4. 顯示性能建議
        recommendations = speed_info.get('recommendations', [])
        if recommendations:
            print("\n💡 性能建議:")
            for rec in recommendations:
                print(f"  • {rec}")
        
        # 5. 模擬檢測工作
        print("\n🔄 開始模擬檢測工作...")
        
        # 這裡可以連接真實相機或使用測試影像
        # controller.connect_camera(0)
        # controller.start_capture()
        
        print("\n📈 高速模式性能特點:")
        print("  🚀 極簡化的圖像處理流程")
        print("  🚀 跳過複雜的形狀過濾") 
        print("  🚀 禁用所有調試功能")
        print("  🚀 簡化的物件追蹤邏輯")
        print("  🚀 減少logging開銷")
        print("  🚀 優化的系統資源配置")
        
        print("\n🎯 高速模式適用場景:")
        print("  • 206fps: 標準高速檢測")
        print("  • 280fps: 平衡性能和準確性") 
        print("  • 376fps: 極限速度檢測")
        
        # 6. 如需要，可以切換回標準模式
        print("\n🔧 如需切換回標準模式:")
        print("controller.enable_ultra_high_speed_detection(False)")
        
    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
        logging.error(f"示例執行錯誤: {str(e)}")
    
    finally:
        # 清理資源
        try:
            controller.cleanup()
        except:
            pass

def benchmark_speed_comparison():
    """基準測試：比較標準模式和高速模式的性能"""
    
    print("\n" + "=" * 60)
    print("🏁 速度基準測試")
    print("=" * 60)
    
    controller = MainController()
    
    try:
        # 測試標準模式
        print("\n🎯 測試標準模式性能...")
        controller.enable_ultra_high_speed_detection(False)
        
        start_time = time.time()
        # 這裡可以添加實際的檢測測試代碼
        standard_time = time.time() - start_time
        
        # 測試高速模式
        print("\n🚀 測試超高速模式性能...")
        controller.enable_ultra_high_speed_detection(True, 280)
        
        start_time = time.time()
        # 這裡可以添加實際的檢測測試代碼  
        high_speed_time = time.time() - start_time
        
        # 計算性能提升
        if standard_time > 0:
            speed_improvement = (standard_time - high_speed_time) / standard_time * 100
            print(f"\n📊 性能提升: {speed_improvement:.1f}%")
        
    except Exception as e:
        print(f"❌ 基準測試錯誤: {str(e)}")
    
    finally:
        controller.cleanup()

if __name__ == "__main__":
    main()
    
    # 可選：執行基準測試
    # benchmark_speed_comparison()
