"""
測試 MVC 系統基本功能
檢查導入和基本初始化
"""

import sys
from pathlib import Path

def test_imports():
    """測試基本導入"""
    print("🧪 測試 MVC 系統導入...")
    
    try:
        # 測試基本 Python 模塊
        import tkinter
        print("✅ tkinter 導入成功")
        
        import cv2
        print("✅ opencv 導入成功")
        
        import numpy
        print("✅ numpy 導入成功")
        
        from PIL import Image
        print("✅ PIL 導入成功")
        
        # 測試 pypylon (可選)
        try:
            from pypylon import pylon
            print("✅ pypylon 導入成功")
        except ImportError:
            print("⚠️ pypylon 未安裝 (連接真實相機時需要)")
        
        return True
        
    except ImportError as e:
        print(f"❌ 導入失敗: {str(e)}")
        return False

def test_mvc_structure():
    """測試 MVC 結構"""
    print("\n🏗️ 測試 MVC 目錄結構...")
    
    basler_mvc = Path("basler_mvc")
    required_dirs = [
        basler_mvc,
        basler_mvc / "models",
        basler_mvc / "views", 
        basler_mvc / "controllers",
        basler_mvc / "config",
        basler_mvc / "logs"
    ]
    
    required_files = [
        basler_mvc / "__init__.py",
        basler_mvc / "main.py",
        basler_mvc / "models" / "__init__.py",
        basler_mvc / "models" / "basler_camera_model.py",
        basler_mvc / "models" / "detection_model.py",
        basler_mvc / "views" / "__init__.py",
        basler_mvc / "views" / "main_view_ctk_bright.py",
        basler_mvc / "controllers" / "__init__.py",
        basler_mvc / "controllers" / "main_controller.py",
        basler_mvc / "config" / "__init__.py",
        basler_mvc / "config" / "settings.py"
    ]
    
    # 檢查目錄
    for dir_path in required_dirs:
        if dir_path.exists():
            print(f"✅ 目錄存在: {dir_path}")
        else:
            print(f"❌ 目錄缺失: {dir_path}")
            return False
    
    # 檢查文件
    for file_path in required_files:
        if file_path.exists():
            print(f"✅ 文件存在: {file_path}")
        else:
            print(f"❌ 文件缺失: {file_path}")
            return False
    
    return True

def test_mvc_imports():
    """測試 MVC 模塊導入"""
    print("\n📦 測試 MVC 模塊導入...")
    
    # 添加路徑
    sys.path.insert(0, str(Path.cwd()))
    
    try:
        # 測試模型導入
        from basler_mvc.models.detection_model import DetectionModel, CircleDetection
        print("✅ DetectionModel 導入成功")
        
        # 測試檢測方法
        circle_detection = CircleDetection()
        print("✅ CircleDetection 實例化成功")
        
        # 測試配置導入
        from basler_mvc.config.settings import get_all_config, validate_config
        print("✅ 配置模塊導入成功")
        
        # 驗證配置
        if validate_config():
            print("✅ 配置驗證通過")
        else:
            print("❌ 配置驗證失敗")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ MVC 導入失敗: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ MVC 測試失敗: {str(e)}")
        return False

def test_detection_functionality():
    """測試檢測功能"""
    print("\n🔍 測試檢測功能...")
    
    try:
        import numpy as np
        from basler_mvc.models.detection_model import CircleDetection, ContourDetection
        
        # 創建測試圖像
        test_image = np.zeros((480, 640), dtype=np.uint8)
        # 繪制一個白色圓形
        import cv2
        cv2.circle(test_image, (320, 240), 50, 255, -1)
        
        # 測試圓形檢測
        circle_detector = CircleDetection()
        processed = circle_detector.process_frame(test_image)
        objects = circle_detector.detect_objects(processed)
        
        print(f"✅ 圓形檢測完成，檢測到 {len(objects)} 個物件")
        
        # 測試輪廓檢測
        contour_detector = ContourDetection()
        processed = contour_detector.process_frame(test_image)
        objects = contour_detector.detect_objects(processed)
        
        print(f"✅ 輪廓檢測完成，檢測到 {len(objects)} 個物件")
        
        return True
        
    except Exception as e:
        print(f"❌ 檢測功能測試失敗: {str(e)}")
        return False

def main():
    """主測試函數"""
    print("🚀 Basler MVC 系統測試")
    print("=" * 50)
    
    tests = [
        ("基本導入測試", test_imports),
        ("MVC 結構測試", test_mvc_structure), 
        ("MVC 模塊導入測試", test_mvc_imports),
        ("檢測功能測試", test_detection_functionality)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} 通過\n")
            else:
                print(f"❌ {test_name} 失敗\n")
        except Exception as e:
            print(f"❌ {test_name} 異常: {str(e)}\n")
    
    print("=" * 50)
    print(f"📊 測試結果: {passed}/{total} 通過")
    
    if passed == total:
        print("🎉 所有測試通過！MVC 系統準備就緒")
        print("\n📋 下一步:")
        print("1. 運行: python basler_mvc_launcher.py")
        print("2. 或在 VSCode 中選擇 'Basler MVC 精簡系統'")
        return True
    else:
        print("⚠️ 部分測試失敗，請檢查相關組件")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)