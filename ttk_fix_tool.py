#!/usr/bin/env python3
"""
🔧 TTK 灰底修復工具
專門解決 TTK 組件灰色背景問題
"""

import tkinter as tk
from tkinter import ttk
import sys
from pathlib import Path

# 添加模組路徑
sys.path.insert(0, str(Path(__file__).parent))

class TTKFixTool:
    """TTK 修復工具"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🔧 TTK 灰底修復工具")
        self.root.geometry("800x600")
        
        # 設置根窗口背景為淺色
        self.root.configure(bg='#F8F9FA')
        
        # 創建 ttk.Style 對象
        self.style = ttk.Style()
        
        # 立即應用修復
        self.apply_ttk_fix()
        
        # 創建測試界面
        self.create_ui()
    
    def apply_ttk_fix(self):
        """應用 TTK 修復"""
        print("🔧 正在修復 TTK 樣式...")
        
        # 定義修復後的顏色
        bg_primary = '#F8F9FA'    # 主背景 - 淺灰
        bg_card = '#FFFFFF'       # 卡片背景 - 白色
        bg_secondary = '#F2F2F7'  # 次要背景
        text_primary = '#1D1D1F'  # 主要文字 - 深色
        text_secondary = '#6D6D70' # 次要文字 - 中灰
        primary_blue = '#0051D5'  # 優化後的藍色
        border_light = '#6D6D70'  # 邊框色
        
        # 🎨 修復 TTK Frame 樣式
        print("  ✅ 修復 TTK Frame...")
        self.style.configure('Fixed.TFrame',
                           background=bg_card,
                           relief='flat',
                           borderwidth=0)
        
        self.style.configure('FixedCard.TFrame',
                           background=bg_card,
                           relief='solid',
                           borderwidth=1,
                           lightcolor=border_light,
                           darkcolor=border_light)
                           
        # 🎨 修復 TTK Button 樣式
        print("  ✅ 修復 TTK Button...")
        self.style.configure('Fixed.TButton',
                           background=primary_blue,
                           foreground='white',
                           relief='flat',
                           borderwidth=0,
                           focuscolor='none',
                           padding=(10, 5))
        
        self.style.map('Fixed.TButton',
                      background=[('active', '#0040B8'),
                                ('pressed', '#003399')])
        
        # 🎨 修復 TTK Label 樣式
        print("  ✅ 修復 TTK Label...")
        self.style.configure('Fixed.TLabel',
                           background=bg_card,
                           foreground=text_primary)
        
        self.style.configure('FixedTitle.TLabel',
                           background=bg_card,
                           foreground=text_primary,
                           font=('Arial', 14, 'bold'))
        
        # 🎨 修復 TTK Entry 樣式
        print("  ✅ 修復 TTK Entry...")
        self.style.configure('Fixed.TEntry',
                           fieldbackground=bg_card,
                           bordercolor=border_light,
                           lightcolor=border_light,
                           darkcolor=border_light,
                           insertcolor=text_primary)
        
        # 🎨 修復 TTK LabelFrame 樣式
        print("  ✅ 修復 TTK LabelFrame...")
        self.style.configure('Fixed.TLabelframe',
                           background=bg_card,
                           bordercolor=border_light,
                           lightcolor=border_light,
                           darkcolor=border_light)
        
        self.style.configure('Fixed.TLabelframe.Label',
                           background=bg_card,
                           foreground=text_primary)
        
        # 🎨 強制覆蓋默認樣式
        print("  ✅ 覆蓋默認 TTK 樣式...")
        self.style.configure('TFrame', background=bg_card)
        self.style.configure('TLabel', background=bg_card, foreground=text_primary)
        self.style.configure('TButton', background=primary_blue, foreground='white')
        self.style.configure('TEntry', fieldbackground=bg_card)
        self.style.configure('TLabelframe', background=bg_card)
        self.style.configure('TLabelframe.Label', background=bg_card, foreground=text_primary)
        
        print("🎉 TTK 樣式修復完成！")
    
    def create_ui(self):
        """創建測試界面"""
        # 主容器 - 使用修復後的樣式
        main_frame = ttk.Frame(self.root, style='Fixed.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 標題
        title = ttk.Label(main_frame, text="🔧 TTK 修復效果測試", style='FixedTitle.TLabel')
        title.pack(pady=(0, 20))
        
        # 說明
        info = ttk.Label(main_frame, text="如果您看到白色背景而不是灰色，說明 TTK 修復成功！", style='Fixed.TLabel')
        info.pack(pady=(0, 15))
        
        # 按鈕測試區
        btn_frame = ttk.Frame(main_frame, style='Fixed.TFrame')
        btn_frame.pack(pady=10)
        
        ttk.Label(btn_frame, text="TTK 按鈕測試:", style='Fixed.TLabel').pack(anchor='w')
        
        button_container = ttk.Frame(btn_frame, style='Fixed.TFrame')
        button_container.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_container, text="修復後按鈕", style='Fixed.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_container, text="測試按鈕", style='Fixed.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_container, text="效果確認", style='Fixed.TButton').pack(side=tk.LEFT, padx=5)
        
        # 輸入框測試區
        entry_frame = ttk.LabelFrame(main_frame, text="TTK 輸入框測試", style='Fixed.TLabelframe')
        entry_frame.pack(fill=tk.X, pady=15)
        
        entry_container = ttk.Frame(entry_frame, style='Fixed.TFrame')
        entry_container.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(entry_container, text="名稱:", style='Fixed.TLabel').pack(side=tk.LEFT)
        entry1 = ttk.Entry(entry_container, style='Fixed.TEntry', width=30)
        entry1.pack(side=tk.LEFT, padx=5)
        entry1.insert(0, "修復後的輸入框")
        
        # 卡片效果測試
        card_frame = ttk.Frame(main_frame, style='FixedCard.TFrame')
        card_frame.pack(fill=tk.X, pady=15)
        
        ttk.Label(card_frame, text="📦 TTK 卡片效果測試", style='Fixed.TLabel').pack(padx=15, pady=15)
        ttk.Label(card_frame, text="這個區域應該有白色背景和可見的邊框", style='Fixed.TLabel').pack(padx=15, pady=(0, 15))
        
        # 修復代碼生成
        code_frame = ttk.LabelFrame(main_frame, text="🔧 修復代碼", style='Fixed.TLabelframe')
        code_frame.pack(fill=tk.BOTH, expand=True, pady=15)
        
        ttk.Button(code_frame, text="📋 生成修復代碼", command=self.generate_fix_code, style='Fixed.TButton').pack(pady=10)
        
        # 底部狀態
        status_frame = ttk.Frame(main_frame, style='Fixed.TFrame')
        status_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Label(status_frame, text="✅ TTK 修復工具 - 如果看到淺色背景，說明修復成功！", style='Fixed.TLabel').pack()
    
    def generate_fix_code(self):
        """生成修復代碼"""
        fix_code = '''# 🔧 TTK 灰底修復代碼
# 將此代碼添加到您的 ThemeManager 的 _apply_ttk_styles 方法中

def fix_ttk_gray_background(self):
    """修復 TTK 灰底問題"""
    # 定義淺色配色
    bg_card = '#FFFFFF'       # 白色背景
    bg_primary = '#F8F9FA'    # 淺灰背景
    text_primary = '#1D1D1F'  # 深色文字
    primary_blue = '#0051D5'  # 優化藍色
    border_light = '#6D6D70'  # 邊框色
    
    # 強制覆蓋所有 TTK 樣式
    self.style.configure('TFrame', background=bg_card, relief='flat')
    self.style.configure('TLabel', background=bg_card, foreground=text_primary)
    self.style.configure('TButton', background=primary_blue, foreground='white', relief='flat')
    self.style.configure('TEntry', fieldbackground=bg_card, bordercolor=border_light)
    self.style.configure('TLabelframe', background=bg_card, bordercolor=border_light)
    self.style.configure('TLabelframe.Label', background=bg_card, foreground=text_primary)
    
    # 設置默認樣式
    self.style.configure('.', background=bg_card)
    
    print("🎉 TTK 灰底問題已修復！")

# 使用方法：
# 在 ThemeManager.__init__ 中調用：
# self.fix_ttk_gray_background()'''
        
        # 創建代碼顯示窗口
        code_window = tk.Toplevel(self.root)
        code_window.title("TTK 修復代碼")
        code_window.geometry("700x500")
        code_window.configure(bg='#F8F9FA')
        
        text_widget = tk.Text(code_window, font=('Consolas', 10), bg='#FFFFFF')
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(1.0, fix_code)
        
        # 複製按鈕
        btn_frame = tk.Frame(code_window, bg='#F8F9FA')
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text="📋 複製修復代碼", 
                 command=lambda: self.copy_code(fix_code),
                 bg='#0051D5', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(btn_frame, text="💾 保存到文件", 
                 command=lambda: self.save_code(fix_code),
                 bg='#34C759', fg='white').pack(side=tk.LEFT, padx=5)
    
    def copy_code(self, code):
        """複製代碼到剪貼板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(code)
        print("📋 TTK 修復代碼已複製到剪貼板")
    
    def save_code(self, code):
        """保存代碼到文件"""
        with open('ttk_fix_code.py', 'w', encoding='utf-8') as f:
            f.write(code)
        print("💾 TTK 修復代碼已保存到 ttk_fix_code.py")
    
    def run(self):
        """運行工具"""
        self.root.mainloop()

def main():
    print("🔧 啟動 TTK 修復工具...")
    tool = TTKFixTool()
    tool.run()

if __name__ == "__main__":
    main()
