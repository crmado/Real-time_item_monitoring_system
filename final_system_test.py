#!/usr/bin/env python3
"""
最終系統測試 - 驗證MVC架構和UI顯示
"""

import sys
import time
import threading
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from basler_mvc.controllers.main_controller import MainController

def test_mvc_system():
    """測試完整的MVC系統"""
    print("🚀 測試 Basler MVC 系統")
    print("=" * 50)
    
    try:
        # 創建控制器
        print("1. 初始化控制器...")
        controller = MainController()
        
        # 測試自動啟動
        print("2. 測試自動啟動相機系統...")
        success = controller.auto_start_camera_system()
        
        if not success:
            print("❌ 自動啟動失敗")
            return False
        
        print("✅ 自動啟動成功")
        
        # 等待系統穩定
        print("3. 等待系統穩定...")
        time.sleep(3)
        
        # 檢查系統狀態
        print("4. 檢查系統狀態...")
        status = controller.get_system_status()
        
        print(f"   相機連接: {'✅' if status['is_connected'] else '❌'}")
        print(f"   正在捕獲: {'✅' if status['is_grabbing'] else '❌'}")
        print(f"   正在處理: {'✅' if status['is_processing'] else '❌'}")
        print(f"   相機FPS: {status['camera_fps']:.1f}")
        print(f"   處理FPS: {status['processing_fps']:.1f}")
        print(f"   檢測FPS: {status['detection_fps']:.1f}")
        
        # 運行性能測試
        print("5. 運行5秒性能測試...")
        start_time = time.time()
        
        while time.time() - start_time < 5:
            status = controller.get_system_status()
            print(f"   實時FPS - 相機: {status['camera_fps']:.1f}, 處理: {status['processing_fps']:.1f}")
            time.sleep(1)
        
        # 最終狀態
        final_status = controller.get_system_status()
        print("\n📊 最終測試結果:")
        print(f"   相機總幀數: {final_status['camera_total_frames']}")
        print(f"   處理總幀數: {final_status['processing_total_frames']}")
        print(f"   相機平均FPS: {final_status['camera_avg_fps']:.1f}")
        print(f"   處理平均FPS: {final_status['processing_avg_fps']:.1f}")
        
        # 性能評估
        camera_fps = final_status['camera_fps']
        processing_fps = final_status['processing_fps']
        
        print(f"\n🎯 性能評估:")
        if camera_fps >= 80:
            print(f"   相機性能: 🏆 優秀 ({camera_fps:.1f} fps)")
        elif camera_fps >= 50:
            print(f"   相機性能: ✅ 良好 ({camera_fps:.1f} fps)")
        else:
            print(f"   相機性能: ⚠️ 需要優化 ({camera_fps:.1f} fps)")
        
        if processing_fps >= 50:
            print(f"   處理性能: 🏆 優秀 ({processing_fps:.1f} fps)")
        elif processing_fps >= 30:
            print(f"   處理性能: ✅ 良好 ({processing_fps:.1f} fps)")
        else:
            print(f"   處理性能: ⚠️ 需要優化 ({processing_fps:.1f} fps)")
        
        # 停止系統
        print("\n6. 清理系統...")
        controller.stop_system()
        controller.cleanup()
        
        print("✅ 系統測試完成")
        return True
        
    except Exception as e:
        print(f"❌ 系統測試失敗: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔥 Basler acA640-300gm MVC 系統測試")
    print("   目標: 驗證相機捕獲和處理流程")
    print("   預期: 相機FPS > 80, 處理FPS > 50")
    print()
    
    success = test_mvc_system()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 系統測試通過 - 可以啟動UI界面")
        print("   請運行: python basler_mvc_launcher.py")
    else:
        print("❌ 系統測試失敗 - 需要進一步調試")
    
    sys.exit(0 if success else 1)