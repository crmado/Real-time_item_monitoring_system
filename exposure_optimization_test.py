#!/usr/bin/env python3
"""
曝光優化測試工具 - 測試不同曝光時間下的FPS性能
目標：1000us曝光時間達到280fps
"""

import sys
import time
import logging
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from basler_mvc.controllers.main_controller import MainController

def test_exposure_performance():
    """測試不同曝光時間下的性能"""
    # 設置日誌
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🚀 曝光優化測試 - 追求280fps")
    print("=" * 60)
    
    try:
        # 創建控制器
        print("1. 初始化系統...")
        controller = MainController()
        
        # 自動啟動
        print("2. 自動啟動相機系統...")
        if not controller.auto_start_camera_system():
            print("❌ 啟動失敗")
            return False
        
        print("✅ 系統啟動成功")
        time.sleep(2)  # 等待穩定
        
        # 測試不同曝光時間
        exposure_tests = [
            (5000.0, "5ms - 原始設置"),
            (3000.0, "3ms - 中等性能"),
            (2000.0, "2ms - 高性能"),
            (1500.0, "1.5ms - 超高性能"),
            (1000.0, "1ms - 極致性能 (目標280fps)"),
            (800.0, "0.8ms - 極限測試"),
            (600.0, "0.6ms - 挑戰極限"),
        ]
        
        results = []
        
        for exposure_us, description in exposure_tests:
            print(f"\n🔧 測試曝光時間: {exposure_us}μs ({description})")
            print("-" * 50)
            
            # 設置曝光時間
            success = controller.set_exposure_time(exposure_us)
            if not success:
                print(f"❌ 設置曝光時間失敗: {exposure_us}μs")
                continue
            
            print(f"✅ 曝光時間已設置為: {exposure_us}μs")
            
            # 等待相機適應新設置
            time.sleep(1)
            
            # 測試性能（5秒）
            print("📊 測試5秒性能...")
            test_start = time.time()
            fps_samples = []
            
            while time.time() - test_start < 5:
                status = controller.get_system_status()
                camera_fps = status['camera_fps']
                processing_fps = status['processing_fps']
                
                if camera_fps > 0:
                    fps_samples.append(camera_fps)
                
                time.sleep(0.2)  # 每200ms採樣一次
            
            # 計算結果
            if fps_samples:
                avg_fps = sum(fps_samples) / len(fps_samples)
                max_fps = max(fps_samples)
                min_fps = min(fps_samples)
                
                print(f"   平均FPS: {avg_fps:.1f}")
                print(f"   最高FPS: {max_fps:.1f}")
                print(f"   最低FPS: {min_fps:.1f}")
                
                # 性能評估
                if avg_fps >= 280:
                    grade = "🏆 達標！"
                elif avg_fps >= 250:
                    grade = "🎉 接近目標"
                elif avg_fps >= 200:
                    grade = "✅ 良好"
                else:
                    grade = "⚠️ 需要優化"
                
                print(f"   性能評級: {grade}")
                
                results.append({
                    'exposure': exposure_us,
                    'description': description,
                    'avg_fps': avg_fps,
                    'max_fps': max_fps,
                    'min_fps': min_fps,
                    'grade': grade
                })
            else:
                print("❌ 未能獲取有效的FPS數據")
        
        # 最終報告
        print("\n" + "=" * 60)
        print("📊 曝光優化測試完整報告")
        print("=" * 60)
        
        print(f"{'曝光時間':<12} {'描述':<20} {'平均FPS':<10} {'最高FPS':<10} {'評級':<15}")
        print("-" * 60)
        
        best_result = None
        target_achieved = False
        
        for result in results:
            print(f"{result['exposure']:<12.0f} {result['description']:<20} "
                  f"{result['avg_fps']:<10.1f} {result['max_fps']:<10.1f} {result['grade']:<15}")
            
            # 找到最佳結果
            if best_result is None or result['avg_fps'] > best_result['avg_fps']:
                best_result = result
            
            # 檢查是否達到280fps目標
            if result['avg_fps'] >= 280:
                target_achieved = True
        
        print("\n🎯 優化建議:")
        if target_achieved:
            print("✅ 已達到280fps目標！")
            best_280 = [r for r in results if r['avg_fps'] >= 280]
            if best_280:
                best_target = max(best_280, key=lambda x: x['exposure'])  # 選擇曝光時間最長的達標設置
                print(f"💡 推薦設置: {best_target['exposure']}μs - {best_target['description']}")
                print(f"   平均FPS: {best_target['avg_fps']:.1f}")
        else:
            print("⚠️ 未達到280fps目標")
            if best_result:
                print(f"💡 最佳性能: {best_result['exposure']}μs - 平均{best_result['avg_fps']:.1f}fps")
        
        # 清理
        controller.stop_system()
        controller.cleanup()
        
        return target_achieved
        
    except Exception as e:
        print(f"❌ 測試過程出錯: {str(e)}")
        logging.error(f"測試錯誤: {str(e)}", exc_info=True)
        return False

def main():
    """主函數"""
    print("🔥 Basler acA640-300gm 曝光優化測試")
    print("   目標: 尋找達到280fps的最佳曝光設置")
    print("   策略: 測試多種曝光時間，找到性能最佳點")
    print()
    
    success = test_exposure_performance()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 測試完成 - 已找到280fps達標設置！")
    else:
        print("⚠️ 測試完成 - 需要進一步優化")
    
    print("\n💡 下一步:")
    print("   1. 根據測試結果調整默認曝光時間")
    print("   2. 在UI中設置最佳曝光值")
    print("   3. 啟動完整系統驗證性能")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)