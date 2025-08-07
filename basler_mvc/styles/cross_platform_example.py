"""
跨平台 UI 使用範例
展示如何使用跨平台 UI 管理系統創建一致的用戶介面
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from theme_manager import ThemeManager

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class CrossPlatformExample:
    """跨平台 UI 範例應用"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("跨平台 UI 範例")
        self.root.geometry("800x600")
        
        # 初始化主題管理器（自動啟用跨平台支援）
        self.theme_manager = ThemeManager(self.root)
        
        # 創建變數
        self.count_var = tk.StringVar(value="000")
        self.status_var = tk.StringVar(value="就緒")
        self.input_var = tk.StringVar()
        
        # 創建 UI
        self.create_ui()
        
        logging.info("✅ 跨平台範例應用初始化完成")
    
    def create_ui(self):
        """創建用戶介面"""
        
        # 主容器 - 使用跨平台框架
        main_frame = self.theme_manager.create_cross_platform_frame(
            self.root, 
            frame_type="transparent"
        )
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 標題區域
        self.create_header(main_frame)
        
        # 控制面板
        self.create_control_panel(main_frame)
        
        # 顯示區域
        self.create_display_area(main_frame)
        
        # 狀態列
        self.create_status_bar(main_frame)
    
    def create_header(self, parent):
        """創建標題區域"""
        
        header_frame = self.theme_manager.create_cross_platform_frame(
            parent,
            frame_type="card"
        )
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 主標題
        title_label = self.theme_manager.create_cross_platform_label(
            header_frame,
            "跨平台 UI 系統範例",
            label_type="title"
        )
        title_label.pack(pady=10)
        
        # 副標題
        subtitle_label = self.theme_manager.create_cross_platform_label(
            header_frame,
            "展示在不同平台上的一致外觀和體驗",
            label_type="subtitle"
        )
        subtitle_label.pack(pady=(0, 10))
        
        # 平台資訊
        platform_info = f"當前平台: {self.theme_manager.ui_manager.platform_name.title()}"
        platform_label = self.theme_manager.create_cross_platform_label(
            header_frame,
            self.theme_manager.get_safe_text(platform_info),
            label_type="caption"
        )
        platform_label.pack()
    
    def create_control_panel(self, parent):
        """創建控制面板"""
        
        control_frame = self.theme_manager.create_cross_platform_frame(
            parent,
            frame_type="card"
        )
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 面板標題
        control_title = self.theme_manager.create_cross_platform_label(
            control_frame,
            "控制面板",
            label_type="subtitle"
        )
        control_title.pack(pady=(10, 15))
        
        # 按鈕區域
        button_frame = self.theme_manager.create_cross_platform_frame(
            control_frame,
            frame_type="transparent"
        )
        button_frame.pack(pady=(0, 10))
        
        # 不同類型的按鈕
        buttons = [
            ("開始監測", "primary", self.start_monitoring),
            ("停止監測", "danger", self.stop_monitoring),
            ("重設計數", "warning", self.reset_count),
            ("儲存設定", "success", self.save_settings),
            ("關於", "secondary", self.show_about)
        ]
        
        for i, (text, btn_type, command) in enumerate(buttons):
            btn = self.theme_manager.create_cross_platform_button(
                button_frame,
                text,
                command=command,
                button_type=btn_type
            )
            btn.grid(row=0, column=i, padx=5, pady=5)
        
        # 輸入區域
        input_frame = self.theme_manager.create_cross_platform_frame(
            control_frame,
            frame_type="transparent"
        )
        input_frame.pack(pady=10)
        
        input_label = self.theme_manager.create_cross_platform_label(
            input_frame,
            "輸入測試文字："
        )
        input_label.pack(side=tk.LEFT, padx=(0, 10))
        
        input_entry = self.theme_manager.create_cross_platform_entry(
            input_frame,
            textvariable=self.input_var
        )
        input_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        test_btn = self.theme_manager.create_cross_platform_button(
            input_frame,
            "測試編碼",
            command=self.test_encoding,
            button_type="secondary"
        )
        test_btn.pack(side=tk.LEFT)
    
    def create_display_area(self, parent):
        """創建顯示區域"""
        
        display_frame = self.theme_manager.create_cross_platform_frame(
            parent,
            frame_type="card"
        )
        display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 顯示標題
        display_title = self.theme_manager.create_cross_platform_label(
            display_frame,
            "顯示區域",
            label_type="subtitle"
        )
        display_title.pack(pady=(10, 15))
        
        # 計數顯示
        count_frame = self.theme_manager.create_cross_platform_frame(
            display_frame,
            frame_type="transparent"
        )
        count_frame.pack(expand=True)
        
        count_label = self.theme_manager.create_cross_platform_label(
            count_frame,
            "當前計數："
        )
        count_label.pack()
        
        # 大數字顯示
        count_display = self.theme_manager.create_cross_platform_status_display(
            count_frame,
            status_type="info"
        )
        count_display.configure(textvariable=self.count_var)
        # 設置大字體
        font_tuple = self.theme_manager.get_platform_font('mono', 48, 'bold')
        count_display.configure(font=font_tuple)
        count_display.pack(pady=20)
        
        # 狀態顯示
        status_display = self.theme_manager.create_cross_platform_status_display(
            count_frame,
            status_type="success"
        )
        status_display.configure(textvariable=self.status_var)
        status_display.pack()
        
        # 測試不同字體類型
        font_test_frame = self.theme_manager.create_cross_platform_frame(
            display_frame,
            frame_type="transparent"
        )
        font_test_frame.pack(pady=20)
        
        font_tests = [
            ("標準字體測試：這是一段中文測試文字", "body"),
            ("等寬字體測試：Code Font Test 123", "mono"),
            ("標題字體測試：系統標題樣式", "title"),
            ("說明字體測試：小字體說明文字", "caption")
        ]
        
        for text, label_type in font_tests:
            test_label = self.theme_manager.create_cross_platform_label(
                font_test_frame,
                self.theme_manager.get_safe_text(text),
                label_type=label_type
            )
            test_label.pack(pady=2)
    
    def create_status_bar(self, parent):
        """創建狀態列"""
        
        status_frame = self.theme_manager.create_cross_platform_frame(
            parent,
            frame_type="panel"
        )
        status_frame.pack(fill=tk.X)
        
        # 狀態資訊
        platform_name = self.theme_manager.ui_manager.platform_name
        encoding = self.theme_manager.ui_manager.font_manager.encoding
        
        status_text = f"平台: {platform_name.title()} | 編碼: {encoding} | UI管理器: 已啟用"
        status_label = self.theme_manager.create_cross_platform_label(
            status_frame,
            self.theme_manager.get_safe_text(status_text),
            label_type="caption"
        )
        status_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 時間戳
        import datetime
        time_text = f"初始化時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        time_label = self.theme_manager.create_cross_platform_label(
            status_frame,
            time_text,
            label_type="caption"
        )
        time_label.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def start_monitoring(self):
        """開始監測"""
        self.status_var.set("監測中...")
        # 模擬計數增加
        current = int(self.count_var.get())
        self.count_var.set(f"{current + 1:03d}")
        logging.info("開始監測")
    
    def stop_monitoring(self):
        """停止監測"""
        self.status_var.set("已停止")
        logging.info("停止監測")
    
    def reset_count(self):
        """重設計數"""
        self.count_var.set("000")
        self.status_var.set("已重設")
        logging.info("重設計數")
    
    def save_settings(self):
        """儲存設定"""
        messagebox.showinfo("儲存設定", "設定已儲存！")
        self.status_var.set("設定已儲存")
        logging.info("儲存設定")
    
    def show_about(self):
        """顯示關於對話框"""
        about_text = f"""跨平台 UI 系統範例

平台: {self.theme_manager.ui_manager.platform_name.title()}
字體編碼: {self.theme_manager.ui_manager.font_manager.encoding}

功能特點:
• 自動字體檢測和回退
• 平台特定顏色優化  
• 編碼安全處理
• 一致的視覺體驗

這個範例展示了如何使用跨平台 UI 管理系統
創建在不同操作系統上都有一致外觀的應用程式。"""
        
        messagebox.showinfo("關於", self.theme_manager.get_safe_text(about_text))
    
    def test_encoding(self):
        """測試編碼處理"""
        test_text = self.input_var.get()
        if not test_text:
            test_text = "測試中文編碼：你好世界！Test encoding: Hello World!"
        
        safe_text = self.theme_manager.get_safe_text(test_text)
        messagebox.showinfo("編碼測試", f"原始文字: {test_text}\n安全文字: {safe_text}")
        logging.info(f"編碼測試 - 原始: {test_text}, 安全: {safe_text}")
    
    def run(self):
        """運行應用程式"""
        logging.info("啟動跨平台範例應用")
        self.root.mainloop()


def main():
    """主函數"""
    try:
        app = CrossPlatformExample()
        app.run()
    except Exception as e:
        logging.error(f"應用程式啟動失敗: {str(e)}")
        messagebox.showerror("錯誤", f"應用程式啟動失敗:\n{str(e)}")


if __name__ == "__main__":
    main()
