#!/usr/bin/env python3
"""
快速診斷相機幀問題
"""

import sys
import time
import logging
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from basler_mvc.models.basler_camera_model import BaslerCameraModel

def test_camera_frames():
    """測試相機是否能正常獲取幀"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🔍 快速診斷相機幀獲取...")
    
    camera_model = BaslerCameraModel()
    
    try:
        # 檢測並連接相機
        print("1. 檢測相機...")
        cameras = camera_model.detect_cameras()
        if not cameras:
            print("❌ 未檢測到相機")
            return False
        
        print(f"✅ 檢測到 {len(cameras)} 台相機")
        
        print("2. 連接相機...")
        if not camera_model.connect(0):
            print("❌ 連接失敗")
            return False
        
        print("✅ 相機連接成功")
        
        print("3. 開始捕獲...")
        if not camera_model.start_capture():
            print("❌ 啟動捕獲失敗")
            return False
        
        print("✅ 捕獲已啟動")
        
        print("4. 測試幀獲取 (10秒)...")
        frame_count = 0
        start_time = time.time()
        
        for i in range(100):  # 測試100次
            frame = camera_model.get_latest_frame()
            if frame is not None:
                frame_count += 1
                if frame_count == 1:
                    print(f"✅ 獲取第一幀！尺寸: {frame.shape}")
                elif frame_count % 20 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    print(f"幀數: {frame_count}, 時間: {elapsed:.1f}s, FPS: {fps:.1f}")
            
            time.sleep(0.01)  # 100fps測試
        
        elapsed = time.time() - start_time
        final_fps = frame_count / elapsed if elapsed > 0 else 0
        
        print(f"\n📊 測試結果:")
        print(f"   總幀數: {frame_count}")
        print(f"   測試時間: {elapsed:.1f}秒")
        print(f"   平均FPS: {final_fps:.1f}")
        
        if frame_count > 0:
            print("✅ 相機幀獲取正常")
            return True
        else:
            print("❌ 未能獲取任何幀")
            return False
            
    except Exception as e:
        print(f"❌ 測試過程出錯: {str(e)}")
        return False
        
    finally:
        try:
            camera_model.stop_capture()
            camera_model.disconnect()
        except:
            pass

if __name__ == "__main__":
    success = test_camera_frames()
    if success:
        print("\n✅ 相機幀獲取功能正常，問題可能在UI顯示部分")
    else:
        print("\n❌ 相機幀獲取有問題，需要檢查相機連接")