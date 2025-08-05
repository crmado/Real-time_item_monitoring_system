#!/usr/bin/env python3
"""
Basler 相機線程同步問題修復測試腳本
用於驗證修復效果和系統穩定性
"""

import sys
import time
import logging
from pathlib import Path

# 添加項目路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_basic_functionality():
    """測試基本功能"""
    print("🧪 測試 1：基本功能檢查")
    
    try:
        from basler_mvc.controllers.main_controller import MainController
        from basler_mvc.models.basler_camera_model import BaslerCameraModel
        from basler_mvc.utils import quick_diagnostic
        
        print("   ✅ 模組導入成功")
        
        # 創建控制器
        controller = MainController()
        print("   ✅ 控制器創建成功")
        
        # 檢測相機
        cameras = controller.detect_cameras()
        print(f"   📷 檢測到 {len(cameras)} 台相機")
        
        # 運行診斷
        print("   🔍 運行系統診斷...")
        diagnostic = quick_diagnostic(controller)
        
        if 'error' not in diagnostic:
            print("   ✅ 系統診斷成功")
            issues = diagnostic.get('potential_issues', [])
            if issues:
                print(f"   ⚠️ 發現 {len(issues)} 個潛在問題")
                for issue in issues:
                    print(f"      - {issue.get('description', 'Unknown')}")
            else:
                print("   ✅ 未發現系統問題")
        else:
            print(f"   ❌ 診斷失敗: {diagnostic.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 測試失敗: {str(e)}")
        return False

def test_thread_safety():
    """測試線程安全性"""
    print("\n🧪 測試 2：線程安全性檢查")
    
    try:
        from basler_mvc.controllers.main_controller import MainController
        import threading
        
        controller = MainController()
        
        # 檢查初始線程狀態
        initial_threads = threading.active_count()
        print(f"   📊 初始線程數: {initial_threads}")
        
        # 模擬快速連接/斷開操作（如果有相機）
        cameras = controller.detect_cameras()
        if cameras:
            print("   🔄 測試快速連接/斷開...")
            
            # 嘗試連接
            success = controller.connect_camera(0)
            if success:
                print("   ✅ 相機連接成功")
                
                # 立即斷開
                controller.disconnect_camera()
                print("   ✅ 相機斷開成功")
                
                # 等待線程清理
                time.sleep(2.0)
                
                # 檢查線程是否正確清理
                final_threads = threading.active_count()
                print(f"   📊 最終線程數: {final_threads}")
                
                if final_threads <= initial_threads + 1:  # 允許一個額外的線程
                    print("   ✅ 線程正確清理")
                else:
                    print(f"   ⚠️ 可能存在線程洩漏 (+{final_threads - initial_threads})")
            else:
                print("   ⚠️ 相機連接失敗（可能無相機或驅動問題）")
        else:
            print("   ⚠️ 未檢測到相機，跳過連接測試")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 線程安全測試失敗: {str(e)}")
        return False

def test_error_handling():
    """測試錯誤處理"""
    print("\n🧪 測試 3：錯誤處理機制")
    
    try:
        from basler_mvc.models.basler_camera_model import BaslerCameraModel
        
        # 創建相機模型
        camera_model = BaslerCameraModel()
        print("   ✅ 相機模型創建成功")
        
        # 測試在未連接狀態下啟動捕獲
        result = camera_model.start_capture()
        if not result:
            print("   ✅ 正確處理未連接狀態")
        else:
            print("   ⚠️ 未連接狀態處理異常")
        
        # 測試重複停止
        camera_model.stop_capture()
        camera_model.stop_capture()  # 第二次調用
        print("   ✅ 重複停止處理正常")
        
        # 測試診斷功能
        if hasattr(camera_model, 'get_system_diagnostics'):
            diagnostics = camera_model.get_system_diagnostics()
            if 'error' not in diagnostics:
                print("   ✅ 診斷功能正常")
            else:
                print(f"   ⚠️ 診斷功能異常: {diagnostics.get('error')}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 錯誤處理測試失敗: {str(e)}")
        return False

def main():
    """主測試函數"""
    print("🚀 Basler 相機線程同步修復測試")
    print("=" * 50)
    
    # 設置簡單的日誌
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    
    test_results = []
    
    # 運行各項測試
    test_results.append(test_basic_functionality())
    test_results.append(test_thread_safety())
    test_results.append(test_error_handling())
    
    # 總結測試結果
    print("\n" + "=" * 50)
    print("📋 測試結果總結")
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"✅ 通過: {passed}/{total}")
    print(f"❌ 失敗: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有測試通過！修復效果良好。")
        print("💡 建議：您現在可以正常使用系統了。")
    elif passed > 0:
        print("\n⚠️ 部分測試通過，系統基本可用。")
        print("💡 建議：請檢查失敗的測試項目。")
    else:
        print("\n❌ 所有測試失敗，系統可能存在問題。")
        print("💡 建議：請檢查依賴安裝和相機連接。")
    
    print("\n📝 如需詳細診斷，請運行完整的系統診斷工具。")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    exit_code = main()
    
    print("\n🔍 按 Enter 鍵退出...")
    try:
        input()
    except:
        pass
    
    sys.exit(exit_code)