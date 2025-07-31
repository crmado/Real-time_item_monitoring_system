#!/usr/bin/env python3
"""
深度性能分析工具 - 找出280fps的真正瓶頸
"""

import sys
import time
import logging
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from pypylon import pylon
except ImportError:
    print("❌ pypylon 未安裝")
    sys.exit(1)

def analyze_camera_limits():
    """分析相機的理論極限"""
    print("🔍 深度性能分析 - acA640-300gm")
    print("=" * 60)
    
    try:
        # 1. 連接相機並獲取規格
        print("1. 分析相機理論性能...")
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        if not devices:
            print("❌ 未檢測到相機")
            return False
        
        camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
        camera.Open()
        
        print(f"   相機型號: {camera.GetDeviceInfo().GetModelName()}")
        print(f"   序列號: {camera.GetDeviceInfo().GetSerialNumber()}")
        
        # 2. 檢查硬體限制
        print("\n2. 硬體規格分析...")
        
        # 幀率限制
        if hasattr(camera, 'AcquisitionFrameRateAbs'):
            max_fps = camera.AcquisitionFrameRateAbs.GetMax()
            min_fps = camera.AcquisitionFrameRateAbs.GetMin()
            print(f"   最大幀率: {max_fps:.1f} fps")
            print(f"   最小幀率: {min_fps:.1f} fps")
        elif hasattr(camera, 'AcquisitionFrameRate'):
            max_fps = camera.AcquisitionFrameRate.GetMax()
            min_fps = camera.AcquisitionFrameRate.GetMin()
            print(f"   最大幀率: {max_fps:.1f} fps")
            print(f"   最小幀率: {min_fps:.1f} fps")
        
        # 曝光時間限制
        if hasattr(camera, 'ExposureTimeAbs'):
            max_exp = camera.ExposureTimeAbs.GetMax()
            min_exp = camera.ExposureTimeAbs.GetMin()
            print(f"   曝光範圍: {min_exp:.0f} - {max_exp:.0f} μs")
        
        # 像素時鐘
        if hasattr(camera, 'PixelClock'):
            try:
                pixel_clock = camera.PixelClock.GetValue()
                print(f"   像素時鐘: {pixel_clock} Hz")
            except:
                pass
        
        # 3. 測試極限設置
        print("\n3. 測試極限性能設置...")
        
        # 基本設置
        camera.AcquisitionMode.SetValue('Continuous')
        camera.PixelFormat.SetValue('Mono8')
        camera.Width.SetValue(640)
        camera.Height.SetValue(480)
        
        # 關閉自動模式
        if hasattr(camera, 'ExposureAuto'):
            camera.ExposureAuto.SetValue('Off')
        if hasattr(camera, 'GainAuto'):
            camera.GainAuto.SetValue('Off')
        
        # 設置最小曝光時間
        if hasattr(camera, 'ExposureTimeAbs'):
            min_exposure = camera.ExposureTimeAbs.GetMin()
            camera.ExposureTimeAbs.SetValue(min_exposure)
            print(f"   設置最小曝光: {min_exposure:.0f} μs")
        
        # 設置最小增益
        if hasattr(camera, 'GainRaw'):
            try:
                min_gain = camera.GainRaw.GetMin()
                camera.GainRaw.SetValue(min_gain)
                print(f"   設置最小增益: {min_gain}")
            except:
                pass
        
        # 設置最大幀率
        if hasattr(camera, 'AcquisitionFrameRateEnable'):
            camera.AcquisitionFrameRateEnable.SetValue(True)
            
            if hasattr(camera, 'AcquisitionFrameRateAbs'):
                max_fps = camera.AcquisitionFrameRateAbs.GetMax()
                camera.AcquisitionFrameRateAbs.SetValue(max_fps)
                print(f"   設置最大幀率: {max_fps:.1f} fps")
            elif hasattr(camera, 'AcquisitionFrameRate'):
                max_fps = camera.AcquisitionFrameRate.GetMax()
                camera.AcquisitionFrameRate.SetValue(max_fps)
                print(f"   設置最大幀率: {max_fps:.1f} fps")
        
        # 網路優化
        try:
            if hasattr(camera, 'GevSCPSPacketSize'):
                camera.GevSCPSPacketSize.SetValue(9000)
                print("   設置Jumbo frames: 9000 bytes")
        except:
            pass
        
        # 4. 實際性能測試
        print("\n4. 極限性能測試...")
        
        # 開始抓取
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        
        frame_count = 0
        start_time = time.time()
        
        print("   測試10秒極限性能...")
        
        while time.time() - start_time < 10:
            try:
                grab_result = camera.RetrieveResult(100, pylon.TimeoutHandling_Return)
                
                if grab_result and grab_result.GrabSucceeded():
                    frame_count += 1
                    grab_result.Release()
                elif grab_result:
                    grab_result.Release()
                    
            except Exception as e:
                pass
        
        total_time = time.time() - start_time
        actual_fps = frame_count / total_time
        
        print(f"\n📊 極限性能結果:")
        print(f"   測試時間: {total_time:.1f} 秒")
        print(f"   總幀數: {frame_count}")
        print(f"   實際FPS: {actual_fps:.1f}")
        
        # 5. 瓶頸分析
        print(f"\n🔍 瓶頸分析:")
        
        if actual_fps >= 280:
            print("✅ 達到280fps目標！")
        elif actual_fps >= 250:
            print("🎉 接近280fps目標")
        else:
            print("⚠️ 未達到280fps，可能的瓶頸：")
            print("   - 相機硬體限制")
            print("   - 網路頻寬限制")
            print("   - USB/GigE介面限制")
            print("   - 系統處理能力限制")
        
        # 理論計算
        pixel_count = 640 * 480
        bits_per_pixel = 8  # Mono8
        bytes_per_frame = pixel_count * bits_per_pixel // 8
        bytes_per_second_280fps = bytes_per_frame * 280
        mbps_280fps = bytes_per_second_280fps * 8 / 1024 / 1024
        
        print(f"\n📐 理論計算:")
        print(f"   每幀像素: {pixel_count:,}")
        print(f"   每幀字節: {bytes_per_frame:,}")
        print(f"   280fps需要頻寬: {mbps_280fps:.1f} Mbps")
        print(f"   GigE理論極限: 1000 Mbps")
        
        if mbps_280fps <= 1000:
            print("✅ 理論上可達到280fps")
        else:
            print("❌ 超出GigE頻寬限制")
        
        # 清理
        camera.StopGrabbing()
        camera.Close()
        
        return actual_fps >= 250  # 250fps以上視為成功
        
    except Exception as e:
        print(f"❌ 分析過程出錯: {str(e)}")
        return False

def main():
    """主函數"""
    print("🔥 acA640-300gm 深度性能分析")
    print("   目標: 找出280fps的真正瓶頸")
    print("   方法: 硬體極限測試 + 理論計算")
    print()
    
    success = analyze_camera_limits()
    
    print("\n" + "=" * 60)
    print("📋 分析總結:")
    
    if success:
        print("🎉 相機具備高性能潛力")
    else:
        print("⚠️ 存在性能瓶頸")
    
    print("\n💡 優化建議:")
    print("   1. 檢查網路設置（MTU、Jumbo frames）")
    print("   2. 優化系統負載")
    print("   3. 調整抓取策略")
    print("   4. 考慮硬體升級")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)