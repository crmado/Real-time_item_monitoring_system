#!/usr/bin/env python3
"""
深度相機診斷工具
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

def diagnose_camera():
    """詳細診斷相機問題"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🔍 深度相機診斷開始...")
    
    try:
        # 1. 檢測相機
        print("\n1. 檢測所有可用相機...")
        tl_factory = pylon.TlFactory.GetInstance()
        devices = tl_factory.EnumerateDevices()
        
        if not devices:
            print("❌ 未檢測到任何Basler相機")
            return False
        
        print(f"✅ 檢測到 {len(devices)} 台相機:")
        for i, device in enumerate(devices):
            model = device.GetModelName()
            serial = device.GetSerialNumber()
            print(f"   相機 {i}: {model} (序列號: {serial})")
        
        # 2. 連接第一台相機
        print(f"\n2. 連接第一台相機...")
        camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[0]))
        camera.Open()
        print("✅ 相機連接成功")
        
        # 3. 檢查相機狀態
        print("\n3. 檢查相機基本信息...")
        print(f"   相機已開啟: {camera.IsOpen()}")
        print(f"   最大寬度: {camera.Width.GetMax()}")
        print(f"   最大高度: {camera.Height.GetMax()}")
        print(f"   像素格式: {list(camera.PixelFormat.GetSymbolics())}")
        
        # 4. 安全配置相機參數
        print("\n4. 配置相機基本參數...")
        
        # 基本設置
        safe_configs = [
            ('AcquisitionMode', 'Continuous'),
            ('PixelFormat', 'Mono8'),
            ('Width', 640),
            ('Height', 480),
        ]
        
        for param, value in safe_configs:
            try:
                if hasattr(camera, param):
                    node = getattr(camera, param)
                    if hasattr(node, 'SetValue'):
                        node.SetValue(value)
                        print(f"   ✅ {param} = {value}")
                    else:
                        print(f"   ⚠️ {param} 節點無SetValue方法")
                else:
                    print(f"   ⚠️ {param} 節點不存在")
            except Exception as e:
                print(f"   ❌ 設置 {param} 失敗: {str(e)}")
        
        # 嘗試關閉自動模式
        auto_modes = ['ExposureAuto', 'GainAuto']
        for mode in auto_modes:
            try:
                if hasattr(camera, mode):
                    getattr(camera, mode).SetValue('Off')
                    print(f"   ✅ 關閉 {mode}")
                else:
                    print(f"   ⚠️ {mode} 不存在")
            except Exception as e:
                print(f"   ❌ 關閉 {mode} 失敗: {str(e)}")
        
        # 設置曝光時間 - 嘗試多種API
        exposure_set = False
        for exposure_attr in ['ExposureTime', 'ExposureTimeAbs', 'ExposureTimeRaw']:
            try:
                if hasattr(camera, exposure_attr):
                    exposure_node = getattr(camera, exposure_attr)
                    if hasattr(exposure_node, 'SetValue'):
                        # 根據不同API設置合適的值
                        if 'Raw' in exposure_attr:
                            exposure_node.SetValue(1000)  # Raw值
                        else:
                            exposure_node.SetValue(10000.0)  # 微秒
                        print(f"   ✅ 設置曝光時間 ({exposure_attr})")
                        exposure_set = True
                        break
            except Exception as e:
                print(f"   嘗試 {exposure_attr} 失敗: {str(e)}")
        
        if not exposure_set:
            print("   ⚠️ 無法設置曝光時間")
        
        # 設置增益 - 嘗試多種API
        gain_set = False
        for gain_attr in ['Gain', 'GainRaw']:
            try:
                if hasattr(camera, gain_attr):
                    gain_node = getattr(camera, gain_attr)
                    if hasattr(gain_node, 'SetValue'):
                        if 'Raw' in gain_attr:
                            gain_node.SetValue(0)  # Raw值
                        else:
                            gain_node.SetValue(0.0)  # dB值
                        print(f"   ✅ 設置增益 ({gain_attr})")
                        gain_set = True
                        break
            except Exception as e:
                print(f"   嘗試 {gain_attr} 失敗: {str(e)}")
        
        if not gain_set:
            print("   ⚠️ 無法設置增益")
        
        print("✅ 相機基本配置完成")
        
        # 5. 嘗試單次抓取
        print("\n5. 測試單次抓取...")
        camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
        
        # 等待並抓取一幀
        for attempt in range(5):
            try:
                grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                
                if grab_result.GrabSucceeded():
                    print(f"✅ 第 {attempt+1} 次抓取成功!")
                    frame = grab_result.Array
                    print(f"   幀尺寸: {frame.shape}")
                    print(f"   數據類型: {frame.dtype}")
                    print(f"   幀編號: {grab_result.GetFrameNumber()}")
                    grab_result.Release()
                    break
                else:
                    print(f"❌ 第 {attempt+1} 次抓取失敗: {grab_result.GetErrorCode()} - {grab_result.GetErrorDescription()}")
                    grab_result.Release()
                    
            except Exception as e:
                print(f"❌ 第 {attempt+1} 次抓取異常: {str(e)}")
        
        # 6. 連續抓取測試
        print("\n6. 測試連續抓取...")
        camera.StopGrabbing()
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        
        success_count = 0
        for i in range(10):
            try:
                grab_result = camera.RetrieveResult(1000, pylon.TimeoutHandling_Return)
                
                if grab_result and grab_result.GrabSucceeded():
                    success_count += 1
                    grab_result.Release()
                elif grab_result:
                    grab_result.Release()
                    
            except Exception as e:
                print(f"連續抓取異常: {str(e)}")
            
            time.sleep(0.1)
        
        print(f"連續抓取結果: {success_count}/10 幀成功")
        
        # 7. 清理
        print("\n7. 清理相機資源...")
        camera.StopGrabbing()
        camera.Close()
        print("✅ 相機已關閉")
        
        return success_count > 0
        
    except Exception as e:
        print(f"❌ 診斷過程出錯: {str(e)}")
        return False

if __name__ == "__main__":
    success = diagnose_camera()
    if success:
        print("\n✅ 相機診斷完成，相機可以正常工作")
    else:
        print("\n❌ 相機診斷完成，相機有問題需要修復")