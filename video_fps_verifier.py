#!/usr/bin/env python3
"""
視頻 FPS 驗證工具
用於驗證錄製的視頻是否使用了正確的幀率參數
"""

import cv2
import os
import sys
from pathlib import Path

class VideoFPSVerifier:
    """視頻 FPS 驗證器"""
    
    def __init__(self):
        self.recordings_dir = Path("basler_mvc/recordings")
    
    def verify_video_fps(self, video_path):
        """驗證指定視頻的 FPS"""
        try:
            video_path = Path(video_path)
            if not video_path.exists():
                print(f"❌ 視頻檔案不存在: {video_path}")
                return None
            
            # 使用 OpenCV 讀取視頻資訊
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                print(f"❌ 無法開啟視頻檔案: {video_path}")
                return None
            
            # 獲取視頻資訊
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            
            # 計算影片長度
            duration = frame_count / fps if fps > 0 else 0
            
            # 解碼 FourCC
            fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
            
            # 檔案大小
            file_size = video_path.stat().st_size / (1024 * 1024)  # MB
            
            cap.release()
            
            return {
                'file_path': str(video_path),
                'file_size_mb': file_size,
                'fps': fps,
                'frame_count': frame_count,
                'duration_sec': duration,
                'width': width,
                'height': height,
                'codec': fourcc_str
            }
            
        except Exception as e:
            print(f"❌ 驗證視頻時發生錯誤: {str(e)}")
            return None
    
    def list_recordings(self):
        """列出所有錄製檔案"""
        if not self.recordings_dir.exists():
            print(f"❌ 錄製目錄不存在: {self.recordings_dir}")
            return []
        
        video_files = []
        for ext in ['*.avi', '*.mp4', '*.mov']:
            video_files.extend(self.recordings_dir.glob(ext))
        
        # 按修改時間排序（最新的在前）
        video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return video_files
    
    def verify_all_recordings(self):
        """驗證所有錄製檔案"""
        video_files = self.list_recordings()
        
        if not video_files:
            print("❌ 錄製目錄中沒有找到視頻檔案")
            return
        
        print(f"🔍 找到 {len(video_files)} 個視頻檔案，開始驗證...")
        print("=" * 80)
        
        for i, video_file in enumerate(video_files, 1):
            print(f"\n📹 [{i}/{len(video_files)}] {video_file.name}")
            info = self.verify_video_fps(video_file)
            
            if info:
                self.print_video_info(info)
                self.analyze_fps(info)
            else:
                print("❌ 無法讀取視頻資訊")
            
            print("-" * 60)
    
    def print_video_info(self, info):
        """列印視頻資訊"""
        print(f"📊 視頻資訊:")
        print(f"   檔案大小: {info['file_size_mb']:.2f} MB")
        print(f"   解析度: {info['width']} x {info['height']}")
        print(f"   編碼: {info['codec']}")
        print(f"   幀數: {info['frame_count']} 幀")
        print(f"   時長: {info['duration_sec']:.2f} 秒")
        print(f"   FPS: {info['fps']:.2f}")
    
    def analyze_fps(self, info):
        """分析 FPS 是否符合預期"""
        actual_fps = info['fps']
        expected_fps = 280  # 預期的 FPS
        
        print(f"\n🎯 FPS 分析:")
        print(f"   預期 FPS: {expected_fps}")
        print(f"   實際 FPS: {actual_fps:.2f}")
        
        # 計算差異
        if actual_fps > 0:
            diff_percent = abs(actual_fps - expected_fps) / expected_fps * 100
            
            if diff_percent < 1:  # 1% 誤差內
                print(f"   ✅ FPS 正確 (誤差: {diff_percent:.2f}%)")
            elif diff_percent < 5:  # 5% 誤差內
                print(f"   ⚠️ FPS 接近預期 (誤差: {diff_percent:.2f}%)")
            else:
                print(f"   ❌ FPS 偏差過大 (誤差: {diff_percent:.2f}%)")
                
            # 實際幀率分析
            if actual_fps < 30:
                print(f"   📝 注意: 幀率較低 ({actual_fps:.1f} fps)，可能不適合高速監控")
            elif actual_fps > 200:
                print(f"   📝 注意: 高幀率錄製 ({actual_fps:.1f} fps)，檔案可能較大")
        else:
            print(f"   ❌ 無效的 FPS 值")
    
    def verify_latest(self):
        """驗證最新的錄製檔案"""
        video_files = self.list_recordings()
        
        if not video_files:
            print("❌ 沒有找到錄製檔案")
            return
        
        latest_file = video_files[0]
        print(f"🔍 驗證最新錄製檔案: {latest_file.name}")
        print("=" * 60)
        
        info = self.verify_video_fps(latest_file)
        if info:
            self.print_video_info(info)
            self.analyze_fps(info)
        else:
            print("❌ 無法讀取視頻資訊")

def main():
    """主函式"""
    verifier = VideoFPSVerifier()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "all":
            # 驗證所有檔案
            verifier.verify_all_recordings()
        elif sys.argv[1] == "latest":
            # 驗證最新檔案
            verifier.verify_latest()
        else:
            # 驗證指定檔案
            video_path = sys.argv[1]
            info = verifier.verify_video_fps(video_path)
            if info:
                verifier.print_video_info(info)
                verifier.analyze_fps(info)
    else:
        # 預設驗證最新檔案
        print("🎬 視頻 FPS 驗證工具")
        print("=" * 40)
        print("用法:")
        print("  python video_fps_verifier.py           # 驗證最新錄製檔案")
        print("  python video_fps_verifier.py latest    # 驗證最新錄製檔案")
        print("  python video_fps_verifier.py all       # 驗證所有錄製檔案")
        print("  python video_fps_verifier.py <檔案路徑> # 驗證指定檔案")
        print()
        
        # 預設執行驗證最新檔案
        verifier.verify_latest()

if __name__ == "__main__":
    main()
