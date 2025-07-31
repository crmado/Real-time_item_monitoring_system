"""
Basler MVC 系統啟動器
快速啟動精簡高性能系統
"""

import sys
import os
from pathlib import Path

def main():
    """主啟動函數"""
    print("🚀 啟動 Basler MVC 精簡高性能系統")
    print("=" * 50)
    
    # 檢查 basler_mvc 目錄
    mvc_dir = Path(__file__).parent / "basler_mvc"
    if not mvc_dir.exists():
        print("❌ 錯誤: basler_mvc 目錄不存在")
        print("請確保已正確創建 MVC 系統文件")
        return 1
    
    # 添加到 Python 路徑
    sys.path.insert(0, str(mvc_dir.parent))
    
    try:
        # 切換到 MVC 目錄
        os.chdir(mvc_dir)
        
        # 導入並運行主程序
        from basler_mvc.main import main as mvc_main
        return mvc_main()
        
    except ImportError as e:
        print(f"❌ 導入錯誤: {str(e)}")
        print("請檢查 MVC 系統文件是否完整")
        return 1
        
    except Exception as e:
        print(f"❌ 啟動失敗: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)