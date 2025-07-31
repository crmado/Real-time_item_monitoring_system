#!/usr/bin/env python3
"""
Basler acA640-300gm 高性能測試腳本
測試目標：驗證系統是否能達到280fps的性能目標
"""

import sys
import time
import statistics
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from basler_mvc.models.basler_camera_model import BaslerCameraModel
from basler_mvc.models.detection_model import DetectionModel

def test_camera_performance():
    """測試相機性能"""
    print("🚀 開始Basler acA640-300gm高性能測試")
    print("=" * 60)
    
    camera_model = BaslerCameraModel()
    detection_model = DetectionModel()
    
    try:
        # 檢測相機
        print("🔍 檢測Basler相機...")
        cameras = camera_model.detect_cameras()
        if not cameras:
            print("❌ 未檢測到Basler相機")
            return False
        
        print(f"✅ 檢測到 {len(cameras)} 台相機")
        for i, camera in enumerate(cameras):
            status = "🎯 目標型號" if camera.get('is_target', False) else "⚠️ 其他型號"
            print(f"   相機 {i+1}: {camera['model']} ({status})")
        
        # 連接相機
        print("\n🔗 連接相機...")
        if not camera_model.connect(0):
            print("❌ 相機連接失敗")
            return False
        
        camera_info = camera_model.get_camera_info()
        print(f"✅ 成功連接: {camera_info.get('model', 'Unknown')}")
        print(f"   解析度: {camera_info.get('width', 640)}x{camera_info.get('height', 480)}")
        print(f"   最大FPS: {camera_info.get('max_fps', 'Unknown')}")
        
        # 開始高速捕獲測試
        print("\n🚀 開始高速捕獲測試 (30秒)...")
        if not camera_model.start_capture():
            print("❌ 啟動捕獲失敗")
            return False
        
        # 測試參數
        test_duration = 30  # 測試30秒
        start_time = time.time()
        fps_samples = []
        frame_count = 0
        last_stats_time = start_time
        
        print("⏱️ 測試中...")
        print("時間  | 瞬時FPS | 平均FPS | 總幀數 | 檢測FPS")
        print("-" * 50)
        
        while time.time() - start_time < test_duration:
            # 獲取幀並進行檢測
            frame = camera_model.get_latest_frame()
            if frame is not None:
                frame_count += 1
                
                # 執行檢測測試
                objects, result_frame = detection_model.detect_frame(frame)
                
                # 每2秒輸出一次統計
                current_time = time.time()
                if current_time - last_stats_time >= 2.0:
                    stats = camera_model.get_stats()
                    detection_stats = detection_model.get_stats()
                    
                    current_fps = stats.get('current_fps', 0)
                    avg_fps = stats.get('average_fps', 0)
                    total_frames = stats.get('total_frames', 0)
                    detection_fps = detection_stats.get('detection_fps', 0)
                    
                    elapsed = current_time - start_time
                    
                    print(f"{elapsed:5.1f}s | {current_fps:7.1f} | {avg_fps:7.1f} | {total_frames:6d} | {detection_fps:7.1f}")
                    
                    if current_fps > 0:
                        fps_samples.append(current_fps)
                    
                    last_stats_time = current_time
            
            # 微小延遲以防過度佔用CPU
            time.sleep(0.0001)
        
        # 停止捕獲
        camera_model.stop_capture()
        
        # 計算最終統計
        final_stats = camera_model.get_stats()
        detection_stats = detection_model.get_stats()
        total_time = time.time() - start_time
        
        print("\n" + "=" * 60)
        print("📊 測試結果摘要")
        print("=" * 60)
        
        # 相機性能
        final_fps = final_stats.get('average_fps', 0)
        total_frames = final_stats.get('total_frames', 0)
        
        print(f"📹 相機性能:")
        print(f"   總測試時間: {total_time:.1f} 秒")
        print(f"   總幀數: {total_frames}")
        print(f"   平均FPS: {final_fps:.1f}")
        
        if fps_samples:
            max_fps = max(fps_samples)
            min_fps = min(fps_samples)
            std_fps = statistics.stdev(fps_samples) if len(fps_samples) > 1 else 0
            
            print(f"   最高FPS: {max_fps:.1f}")
            print(f"   最低FPS: {min_fps:.1f}")
            print(f"   標準差: {std_fps:.1f}")
        
        # 檢測性能
        detection_fps = detection_stats.get('detection_fps', 0)
        print(f"\n🔍 檢測性能:")
        print(f"   檢測FPS: {detection_fps:.1f}")
        print(f"   檢測方法: {detection_stats.get('current_method', 'unknown')}")
        
        # 性能評估
        print(f"\n🎯 性能評估:")
        target_fps = 280
        achievement_rate = (final_fps / target_fps) * 100
        
        print(f"   目標FPS: {target_fps}")
        print(f"   實際FPS: {final_fps:.1f}")
        print(f"   達成率: {achievement_rate:.1f}%")
        
        if final_fps >= target_fps:
            grade = "🏆 卓越 - 超越目標!"
        elif final_fps >= target_fps * 0.9:
            grade = "🎉 優秀 - 接近目標"
        elif final_fps >= target_fps * 0.7:
            grade = "✅ 良好 - 需要優化"
        else:
            grade = "⚠️ 需要改進"
        
        print(f"   性能等級: {grade}")
        
        # 建議
        print(f"\n💡 性能建議:")
        if final_fps < target_fps:
            print("   - 檢查相機連接（建議使用千兆乙太網）")
            print("   - 確保CPU性能充足")
            print("   - 檢查系統負載")
            print("   - 考慮調整曝光時間和幀率設置")
        else:
            print("   - 性能表現優異！")
            print("   - 系統已達到設計目標")
        
        return final_fps >= target_fps * 0.8  # 80%以上視為成功
        
    except Exception as e:
        print(f"❌ 測試過程中發生錯誤: {str(e)}")
        return False
    
    finally:
        # 清理資源
        try:
            camera_model.disconnect()
        except:
            pass

def main():
    """主測試函數"""
    print("🔥 Basler acA640-300gm 高性能測試工具")
    print("   目標: 驗證280fps性能")
    print("   持續: 30秒測試")
    print()
    
    success = test_camera_performance()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 測試完成 - 性能達標！")
        return 0
    else:
        print("❌ 測試完成 - 需要優化")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)