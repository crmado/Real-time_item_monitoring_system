#!/usr/bin/env python3
"""
單獨測試相機模型 - 不涉及控制器
"""

import sys
import time
import logging
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from basler_mvc.models.basler_camera_model import BaslerCameraModel

def test_camera_model_isolated():
    """獨立測試相機模型"""
    # 設置日誌
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🧪 獨立測試 BaslerCameraModel")
    print("=" * 50)
    
    try:
        # 1. 創建相機模型
        print("1. 創建相機模型...")
        camera_model = BaslerCameraModel()
        
        # 2. 檢測相機
        print("2. 檢測相機...")
        cameras = camera_model.detect_cameras()
        if not cameras:
            print("❌ 未檢測到相機")
            return False
        
        print(f"✅ 檢測到 {len(cameras)} 台相機")
        
        # 3. 連接相機
        print("3. 連接相機...")
        if not camera_model.connect(0):
            print("❌ 連接失敗")
            return False
        
        print("✅ 相機連接成功")
        
        # 4. 開始捕獲
        print("4. 開始捕獲...")
        if not camera_model.start_capture():
            print("❌ 啟動捕獲失敗")
            return False
        
        print("✅ 捕獲啟動成功")
        
        # 5. 等待並測試幀獲取
        print("5. 測試幀獲取...")
        time.sleep(2)  # 等待相機穩定
        
        frame_count = 0
        start_time = time.time()
        
        for i in range(50):  # 測試50次
            frame = camera_model.get_latest_frame()
            if frame is not None:
                frame_count += 1
                if frame_count == 1:
                    print(f"✅ 成功獲取第一幀！尺寸: {frame.shape}")
                elif frame_count % 10 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    print(f"   幀數: {frame_count}, FPS: {fps:.1f}")
            
            time.sleep(0.02)  # 50fps測試
        
        # 6. 檢查統計
        stats = camera_model.get_stats()
        print(f"\n📊 相機統計:")
        print(f"   總幀數: {stats['total_frames']}")
        print(f"   當前FPS: {stats['current_fps']:.1f}")
        print(f"   平均FPS: {stats['average_fps']:.1f}")
        print(f"   隊列大小: {stats['queue_size']}")
        
        # 7. 停止
        print("\n6. 停止捕獲...")
        camera_model.stop_capture()
        camera_model.disconnect()
        
        if frame_count > 0:
            print(f"✅ 測試成功！獲取了 {frame_count} 幀")
            return True
        else:
            print("❌ 未獲取到任何幀")
            return False
        
    except Exception as e:
        print(f"❌ 測試失敗: {str(e)}")
        logging.error(f"測試錯誤: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_camera_model_isolated()
    print("\n" + "=" * 50)
    if success:
        print("🎉 相機模型工作正常")
    else:
        print("❌ 相機模型有問題")
    
    sys.exit(0 if success else 1)