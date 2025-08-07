#!/usr/bin/env python3
"""
跨平台 UI 系統演示
展示新的跨平台 UI 功能和改進效果
"""

import tkinter as tk
import logging
import sys
from pathlib import Path

# 添加模組路徑
sys.path.insert(0, str(Path(__file__).parent))

try:
    from basler_mvc.styles.theme_manager import ThemeManager
    from basler_mvc.styles.apple_theme import AppleTheme
except ImportError as e:
    print(f"❌ 導入錯誤: {e}")
    sys.exit(1)

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CrossPlatformDemo:
    """跨平台 UI 功能演示"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎨 跨平台 UI 配色系統演示")
        self.root.geometry("900x700")
        
        # 初始化跨平台主題管理器
        self.theme_manager = ThemeManager(self.root, AppleTheme)
        
        # 創建演示界面
        self.create_demo_ui()
        
        # 顯示平台資訊
        self.show_platform_info()
    
    def create_demo_ui(self):
        """創建演示界面"""
        
        # 主容器
        main_frame = self.theme_manager.create_cross_platform_frame(self.root, "transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 標題區域
        self.create_header(main_frame)
        
        # 平台資訊
        self.create_platform_info(main_frame)
        
        # 按鈕演示
        self.create_button_demo(main_frame)
        
        # 文字樣式演示
        self.create_text_demo(main_frame)
        
        # 狀態顯示演示
        self.create_status_demo(main_frame)
        
        # 輸入區域演示
        self.create_input_demo(main_frame)
    
    def create_header(self, parent):
        """創建標題區域"""
        header_frame = self.theme_manager.create_cross_platform_frame(parent, "card")
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title = self.theme_manager.create_cross_platform_label(
            header_frame,
            self.theme_manager.get_safe_text("🎨 跨平台 UI 配色系統"),
            label_type="title"
        )
        title.pack(pady=15)
        
        subtitle = self.theme_manager.create_cross_platform_label(
            header_frame,
            self.theme_manager.get_safe_text("解決字體顏色、小部件顏色和編碼一致性問題"),
            label_type="subtitle"
        )
        subtitle.pack(pady=(0, 15))
    
    def create_platform_info(self, parent):
        """創建平台資訊區域"""
        info_frame = self.theme_manager.create_cross_platform_frame(parent, "card")
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        info_title = self.theme_manager.create_cross_platform_label(
            info_frame,
            "系統資訊",
            label_type="subtitle"
        )
        info_title.pack(pady=(10, 15))
        
        # 平台資訊
        platform_info = [
            f"操作系統: {self.theme_manager.ui_manager.platform_name.title()}",
            f"字體編碼: {self.theme_manager.ui_manager.font_manager.encoding}",
            f"主要字體: {self.theme_manager.get_platform_font('primary')[0]}",
            f"等寬字體: {self.theme_manager.get_platform_font('mono')[0]}",
            f"主要顏色: {self.theme_manager.get_platform_color('primary_blue')}"
        ]
        
        for info in platform_info:
            label = self.theme_manager.create_cross_platform_label(
                info_frame,
                self.theme_manager.get_safe_text(info),
                label_type="body"
            )
            label.pack(anchor='w', padx=15, pady=2)
        
        # 添加底部間距
        tk.Frame(info_frame, height=10, bg=self.theme_manager.get_platform_color('background_card')).pack()
    
    def create_button_demo(self, parent):
        """創建按鈕演示區域"""
        button_frame = self.theme_manager.create_cross_platform_frame(parent, "card")
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        button_title = self.theme_manager.create_cross_platform_label(
            button_frame,
            "按鈕樣式演示",
            label_type="subtitle"
        )
        button_title.pack(pady=(10, 15))
        
        # 創建按鈕容器
        btn_container = self.theme_manager.create_cross_platform_frame(button_frame, "transparent")
        btn_container.pack(pady=(0, 15))
        
        buttons = [
            ("主要操作", "primary", "藍色主要按鈕"),
            ("成功操作", "success", "綠色成功按鈕"),
            ("警告操作", "warning", "橙色警告按鈕"),
            ("危險操作", "danger", "紅色危險按鈕"),
            ("次要操作", "secondary", "灰色次要按鈕")
        ]
        
        for i, (text, btn_type, description) in enumerate(buttons):
            btn = self.theme_manager.create_cross_platform_button(
                btn_container,
                self.theme_manager.get_safe_text(text),
                command=lambda desc=description: self.show_message(desc),
                button_type=btn_type
            )
            btn.grid(row=0, column=i, padx=8, pady=5)
    
    def create_text_demo(self, parent):
        """創建文字樣式演示"""
        text_frame = self.theme_manager.create_cross_platform_frame(parent, "card")
        text_frame.pack(fill=tk.X, pady=(0, 20))
        
        text_title = self.theme_manager.create_cross_platform_label(
            text_frame,
            "文字樣式演示",
            label_type="subtitle"
        )
        text_title.pack(pady=(10, 15))
        
        text_styles = [
            ("這是標題樣式文字", "title"),
            ("這是副標題樣式文字", "subtitle"),
            ("這是正文樣式文字，用於一般內容顯示", "body"),
            ("這是說明樣式文字，用於輔助資訊", "caption"),
            ("這是等寬字體：Code Font Test 123", "mono")
        ]
        
        for text, style in text_styles:
            label = self.theme_manager.create_cross_platform_label(
                text_frame,
                self.theme_manager.get_safe_text(text),
                label_type=style
            )
            label.pack(anchor='w', padx=15, pady=3)
        
        # 添加底部間距
        tk.Frame(text_frame, height=10, bg=self.theme_manager.get_platform_color('background_card')).pack()
    
    def create_status_demo(self, parent):
        """創建狀態顯示演示"""
        status_frame = self.theme_manager.create_cross_platform_frame(parent, "card")
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        status_title = self.theme_manager.create_cross_platform_label(
            status_frame,
            "狀態顯示演示",
            label_type="subtitle"
        )
        status_title.pack(pady=(10, 15))
        
        # 狀態顯示容器
        status_container = self.theme_manager.create_cross_platform_frame(status_frame, "transparent")
        status_container.pack(pady=(0, 15))
        
        statuses = [
            ("資訊狀態", "info"),
            ("成功狀態", "success"), 
            ("警告狀態", "warning"),
            ("錯誤狀態", "error")
        ]
        
        for i, (text, status_type) in enumerate(statuses):
            status_display = self.theme_manager.create_cross_platform_status_display(
                status_container, status_type=status_type
            )
            status_display.configure(text=self.theme_manager.get_safe_text(text))
            status_display.grid(row=0, column=i, padx=15, pady=5)
    
    def create_input_demo(self, parent):
        """創建輸入區域演示"""
        input_frame = self.theme_manager.create_cross_platform_frame(parent, "card")
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        input_title = self.theme_manager.create_cross_platform_label(
            input_frame,
            "輸入框演示",
            label_type="subtitle"
        )
        input_title.pack(pady=(10, 15))
        
        # 輸入容器
        input_container = self.theme_manager.create_cross_platform_frame(input_frame, "transparent")
        input_container.pack(pady=(0, 15))
        
        # 測試文字輸入
        label1 = self.theme_manager.create_cross_platform_label(
            input_container,
            "測試中文輸入：",
            label_type="body"
        )
        label1.pack(anchor='w', padx=15, pady=(0, 5))
        
        self.test_var = tk.StringVar(value="測試中文編碼安全處理")
        entry1 = self.theme_manager.create_cross_platform_entry(input_container, self.test_var)
        entry1.pack(anchor='w', padx=15, pady=(0, 10))
        
        # 測試按鈕
        test_btn = self.theme_manager.create_cross_platform_button(
            input_container,
            "測試編碼安全",
            command=self.test_encoding,
            button_type="primary"
        )
        test_btn.pack(anchor='w', padx=15)
    
    def show_message(self, message):
        """顯示消息"""
        import tkinter.messagebox as msgbox
        safe_msg = self.theme_manager.get_safe_text(f"您點擊了：{message}")
        msgbox.showinfo("按鈕點擊", safe_msg)
    
    def test_encoding(self):
        """測試編碼安全"""
        test_text = self.test_var.get()
        safe_text = self.theme_manager.get_safe_text(test_text)
        
        import tkinter.messagebox as msgbox
        result_msg = f"""編碼測試結果：

原始輸入：{test_text}
安全處理：{safe_text}
字符長度：{len(safe_text)}

✅ 編碼安全處理正常！"""
        
        msgbox.showinfo("編碼測試", self.theme_manager.get_safe_text(result_msg))
    
    def show_platform_info(self):
        """顯示詳細平台資訊"""
        # 記錄詳細平台資訊
        self.theme_manager.ui_manager.log_platform_info()
        
        print("\n🎨 跨平台 UI 配色系統已啟動")
        print(f"📱 當前平台：{self.theme_manager.ui_manager.platform_name.title()}")
        print(f"🔤 系統編碼：{self.theme_manager.ui_manager.font_manager.encoding}")
        print(f"🖋️  主要字體：{self.theme_manager.get_platform_font('primary')[0]}")
        print(f"🎨 主要顏色：{self.theme_manager.get_platform_color('primary_blue')}")
        print("\n💡 功能特點：")
        print("   ✅ 跨平台字體一致性")
        print("   ✅ 智能顏色配色適配")
        print("   ✅ 編碼安全處理")
        print("   ✅ 平台原生風格保持")
        print("\n🚀 現在您可以在不同平台上獲得一致的視覺體驗！")
    
    def run(self):
        """運行演示"""
        self.root.mainloop()

def main():
    """主函數"""
    print("🎨 啟動跨平台 UI 配色系統演示...")
    
    try:
        demo = CrossPlatformDemo()
        demo.run()
        print("✅ 演示結束")
    except Exception as e:
        print(f"❌ 演示運行失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
