# 🔧 TTK 灰底修復代碼
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
# self.fix_ttk_gray_background()