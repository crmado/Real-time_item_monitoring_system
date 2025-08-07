#!/usr/bin/env python3
"""
Basler MVC 版本選擇器
可以選擇使用原始 tkinter 版本或 CustomTkinter 高清版本
"""

import sys
import os
from pathlib import Path

def show_menu():
    """顯示選擇菜單"""
    print("🚀 Basler acA640-300gm 精簡高性能系統")
    print("=" * 50)
    print("請選擇界面版本：")
    print()
    print("1. 🎨 CustomTkinter 優化版本 (推薦)")
    print("   - 大幅改善字體大小，特別是即時統計")
    print("   - 簡潔活潑的配色方案") 
    print("   - 完整功能 + 優化視覺效果")
    print("   - 解決跨平台顯示模糊問題")
    print()
    print("2. 🔧 原始 tkinter 版本")
    print("   - 傳統界面")
    print("   - 可能有顯示問題")
    print()
    print("0. ❌ 退出")
    print("=" * 50)

def main():
    """主函數"""
    while True:
        show_menu()
        
        try:
            choice = input("請輸入選擇 (0-2): ").strip()
            
            if choice == "0":
                print("👋 再見！")
                sys.exit(0)
                
            elif choice == "1":
                print("🎨 啟動 CustomTkinter 高清版本...")
                
                # 檢查 customtkinter 依賴
                try:
                    import customtkinter
                    print("✅ CustomTkinter 已安裝")
                except ImportError:
                    print("❌ 缺少 CustomTkinter")
                    install = input("是否自動安裝？(y/N): ").lower()
                    if install == 'y':
                        os.system("pip install customtkinter")
                        print("✅ 安裝完成")
                    else:
                        continue
                
                # 啟動 CustomTkinter 優化版本
                try:
                    from basler_mvc.controllers.main_controller import MainController
                    from basler_mvc.views.main_view_ctk_optimized import MainView
                    
                    print("🏗️ 初始化系統...")
                    controller = MainController()
                    view = MainView(controller)
                    
                    print("🎮 啟動界面...")
                    view.run()
                    
                except ImportError as e:
                    print(f"❌ 導入錯誤: {str(e)}")
                    print("請確保所有必要文件都已創建")
                    
                except Exception as e:
                    print(f"❌ 執行錯誤: {str(e)}")
                
                break
                
            elif choice == "2":
                print("🔧 啟動原始 tkinter 版本...")
                
                # 啟動原始版本
                try:
                    from basler_mvc.controllers.main_controller import MainController
                    from basler_mvc.views.main_view import MainView
                    
                    print("🏗️ 初始化系統...")
                    controller = MainController()
                    view = MainView(controller)
                    
                    print("🎮 啟動界面...")
                    view.run()
                    
                except ImportError as e:
                    print(f"❌ 導入錯誤: {str(e)}")
                    print("請確保所有必要文件都已創建")
                    
                except Exception as e:
                    print(f"❌ 執行錯誤: {str(e)}")
                
                break
                
            else:
                print("❌ 無效選擇，請重新輸入")
                input("按 Enter 繼續...")
                os.system('clear' if os.name == 'posix' else 'cls')
                
        except KeyboardInterrupt:
            print("\n👋 用戶中斷，程式結束")
            sys.exit(0)
        except Exception as e:
            print(f"❌ 錯誤: {str(e)}")
            input("按 Enter 繼續...")

if __name__ == "__main__":
    # 添加項目根目錄到路徑
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    
    main()