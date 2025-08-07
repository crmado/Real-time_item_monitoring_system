#!/usr/bin/env python3
"""
🎨 離線顏色編碼工具
- 顏色選擇器
- 顏色格式轉換
- 對比度計算
- 配色方案生成
"""

import tkinter as tk
from tkinter import ttk, colorchooser
import colorsys
import math

class OfflineColorTool:
    """離線顏色編碼工具"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎨 離線顏色編碼工具")
        self.root.geometry("1000x700")
        self.root.configure(bg='#F8F9FA')
        
        # 當前選中的顏色
        self.current_color = "#007AFF"
        self.current_bg = "#FFFFFF"
        
        # 創建界面
        self.create_ui()
        
    def create_ui(self):
        """創建用戶界面"""
        # 主容器
        main_frame = tk.Frame(self.root, bg='#F8F9FA')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 標題
        title = tk.Label(main_frame, text="🎨 離線顏色編碼工具", 
                        font=('Arial', 20, 'bold'), bg='#F8F9FA', fg='#1D1D1F')
        title.pack(pady=(0, 20))
        
        # 創建三欄布局
        content_frame = tk.Frame(main_frame, bg='#F8F9FA')
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左側：顏色選擇
        self.create_color_picker(content_frame)
        
        # 中間：顏色預覽和信息
        self.create_color_preview(content_frame)
        
        # 右側：配色建議
        self.create_color_suggestions(content_frame)
        
        # 底部：工具欄
        self.create_toolbar(main_frame)
        
    def create_color_picker(self, parent):
        """創建顏色選擇區域"""
        picker_frame = tk.LabelFrame(parent, text="🎯 顏色選擇", 
                                   font=('Arial', 12, 'bold'),
                                   bg='#FFFFFF', fg='#1D1D1F',
                                   relief='solid', bd=1)
        picker_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 顏色選擇按鈕
        tk.Label(picker_frame, text="選擇主色:", bg='#FFFFFF', fg='#1D1D1F').pack(pady=5)
        self.color_btn = tk.Button(picker_frame, text="點擊選擇顏色", 
                                  command=self.choose_color,
                                  bg=self.current_color, fg='white',
                                  font=('Arial', 10, 'bold'))
        self.color_btn.pack(pady=5)
        
        # 背景色選擇
        tk.Label(picker_frame, text="選擇背景色:", bg='#FFFFFF', fg='#1D1D1F').pack(pady=(15, 5))
        self.bg_btn = tk.Button(picker_frame, text="點擊選擇背景", 
                               command=self.choose_bg_color,
                               bg=self.current_bg, fg='black',
                               font=('Arial', 10, 'bold'))
        self.bg_btn.pack(pady=5)
        
        # 快速顏色選項
        tk.Label(picker_frame, text="快速選擇:", bg='#FFFFFF', fg='#1D1D1F').pack(pady=(15, 5))
        
        quick_colors = [
            ('#0051D5', '優化藍'),
            ('#007AFF', 'Apple藍'),
            ('#34C759', 'Apple綠'),
            ('#FF3B30', 'Apple紅'),
            ('#FF9500', 'Apple橙'),
            ('#AF52DE', 'Apple紫'),
            ('#1D1D1F', '深灰'),
            ('#6D6D70', '中灰'),
        ]
        
        for i, (color, name) in enumerate(quick_colors):
            if i % 2 == 0:
                row_frame = tk.Frame(picker_frame, bg='#FFFFFF')
                row_frame.pack(pady=2)
            
            btn = tk.Button(row_frame, bg=color, width=3, height=1,
                          command=lambda c=color: self.set_color(c))
            btn.pack(side=tk.LEFT, padx=2)
            
            tk.Label(row_frame, text=name, bg='#FFFFFF', fg='#1D1D1F',
                    font=('Arial', 8)).pack(side=tk.LEFT, padx=(2, 10))
            
    def create_color_preview(self, parent):
        """創建顏色預覽區域"""
        preview_frame = tk.LabelFrame(parent, text="🔍 顏色預覽與資訊", 
                                    font=('Arial', 12, 'bold'),
                                    bg='#FFFFFF', fg='#1D1D1F',
                                    relief='solid', bd=1)
        preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # 顏色預覽區
        self.preview_canvas = tk.Canvas(preview_frame, width=300, height=150, 
                                       bg=self.current_bg, relief='solid', bd=1)
        self.preview_canvas.pack(pady=10)
        
        # 在預覽區顯示文字樣本
        self.update_preview()
        
        # 顏色信息區
        info_frame = tk.Frame(preview_frame, bg='#FFFFFF')
        info_frame.pack(fill=tk.X, padx=10)
        
        # 顏色值顯示
        self.color_info = tk.Text(info_frame, height=8, width=35, 
                                 font=('Consolas', 10), bg='#F8F9FA')
        self.color_info.pack(fill=tk.X, pady=5)
        
        # 對比度信息
        self.contrast_info = tk.Text(info_frame, height=4, width=35,
                                   font=('Arial', 10), bg='#F8F9FA')
        self.contrast_info.pack(fill=tk.X, pady=5)
        
        self.update_color_info()
        
    def create_color_suggestions(self, parent):
        """創建配色建議區域"""
        suggestions_frame = tk.LabelFrame(parent, text="💡 配色建議", 
                                        font=('Arial', 12, 'bold'),
                                        bg='#FFFFFF', fg='#1D1D1F',
                                        relief='solid', bd=1)
        suggestions_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # WCAG 標準建議
        wcag_frame = tk.LabelFrame(suggestions_frame, text="WCAG 標準", 
                                  bg='#FFFFFF', fg='#1D1D1F')
        wcag_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.wcag_suggestions = tk.Text(wcag_frame, height=6, width=30,
                                       font=('Arial', 9), bg='#F8F9FA')
        self.wcag_suggestions.pack(fill=tk.X, padx=5, pady=5)
        
        # 相似色建議
        similar_frame = tk.LabelFrame(suggestions_frame, text="相似色系", 
                                    bg='#FFFFFF', fg='#1D1D1F')
        similar_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.similar_colors_frame = tk.Frame(similar_frame, bg='#FFFFFF')
        self.similar_colors_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 互補色建議
        complement_frame = tk.LabelFrame(suggestions_frame, text="互補色系", 
                                       bg='#FFFFFF', fg='#1D1D1F')
        complement_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.complement_colors_frame = tk.Frame(complement_frame, bg='#FFFFFF')
        self.complement_colors_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.update_suggestions()
        
    def create_toolbar(self, parent):
        """創建工具欄"""
        toolbar_frame = tk.Frame(parent, bg='#F8F9FA')
        toolbar_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 複製顏色代碼
        tk.Button(toolbar_frame, text="📋 複製 HEX", 
                 command=self.copy_hex, bg='#0051D5', fg='white').pack(side=tk.LEFT, padx=5)
        
        tk.Button(toolbar_frame, text="📋 複製 RGB", 
                 command=self.copy_rgb, bg='#0051D5', fg='white').pack(side=tk.LEFT, padx=5)
        
        # 生成 TTK 樣式代碼
        tk.Button(toolbar_frame, text="🔧 生成 TTK 樣式", 
                 command=self.generate_ttk_style, bg='#34C759', fg='white').pack(side=tk.LEFT, padx=5)
        
        # 生成配色文件
        tk.Button(toolbar_frame, text="💾 導出配色", 
                 command=self.export_colors, bg='#FF9500', fg='white').pack(side=tk.LEFT, padx=5)
        
        # 右側信息
        tk.Label(toolbar_frame, text="離線顏色工具 v1.0", 
                bg='#F8F9FA', fg='#6D6D70').pack(side=tk.RIGHT)
        
    def choose_color(self):
        """選擇主色"""
        color = colorchooser.askcolor(color=self.current_color)
        if color[1]:
            self.set_color(color[1])
            
    def choose_bg_color(self):
        """選擇背景色"""
        color = colorchooser.askcolor(color=self.current_bg)
        if color[1]:
            self.current_bg = color[1]
            self.bg_btn.configure(bg=self.current_bg)
            self.update_all()
            
    def set_color(self, color):
        """設置顏色"""
        self.current_color = color.upper()
        self.color_btn.configure(bg=self.current_color)
        self.update_all()
        
    def update_all(self):
        """更新所有顯示"""
        self.update_preview()
        self.update_color_info()
        self.update_suggestions()
        
    def update_preview(self):
        """更新顏色預覽"""
        self.preview_canvas.configure(bg=self.current_bg)
        self.preview_canvas.delete("all")
        
        # 繪製文字樣本
        self.preview_canvas.create_text(150, 30, text="主要標題文字", 
                                       fill=self.current_color, font=('Arial', 16, 'bold'))
        self.preview_canvas.create_text(150, 60, text="這是一段正文內容測試", 
                                       fill=self.current_color, font=('Arial', 12))
        self.preview_canvas.create_text(150, 90, text="次要資訊顯示", 
                                       fill=self.current_color, font=('Arial', 10))
        
        # 繪製按鈕樣本
        self.preview_canvas.create_rectangle(50, 110, 150, 140, 
                                           fill=self.current_color, outline=self.current_color)
        self.preview_canvas.create_text(100, 125, text="按鈕", 
                                       fill='white', font=('Arial', 12, 'bold'))
        
    def hex_to_rgb(self, hex_color):
        """HEX轉RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
    def rgb_to_hex(self, rgb):
        """RGB轉HEX"""
        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
        
    def calculate_contrast(self, color1, color2):
        """計算對比度"""
        def luminance(rgb):
            def gamma_correct(channel):
                channel = channel / 255.0
                if channel <= 0.03928:
                    return channel / 12.92
                else:
                    return pow((channel + 0.055) / 1.055, 2.4)
            
            r, g, b = [gamma_correct(c) for c in rgb]
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        rgb1 = self.hex_to_rgb(color1)
        rgb2 = self.hex_to_rgb(color2)
        
        lum1 = luminance(rgb1)
        lum2 = luminance(rgb2)
        
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
        
    def update_color_info(self):
        """更新顏色信息"""
        rgb = self.hex_to_rgb(self.current_color)
        rgb_bg = self.hex_to_rgb(self.current_bg)
        
        # 轉換為HSV
        hsv = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
        
        # 計算對比度
        contrast = self.calculate_contrast(self.current_color, self.current_bg)
        
        info_text = f"""🎨 顏色資訊:
HEX: {self.current_color}
RGB: {rgb[0]}, {rgb[1]}, {rgb[2]}
HSV: {int(hsv[0]*360)}°, {int(hsv[1]*100)}%, {int(hsv[2]*100)}%

🎭 背景資訊:
HEX: {self.current_bg}
RGB: {rgb_bg[0]}, {rgb_bg[1]}, {rgb_bg[2]}

📏 對比度: {contrast:.2f}:1"""
        
        self.color_info.delete(1.0, tk.END)
        self.color_info.insert(1.0, info_text)
        
        # 對比度評估
        if contrast >= 7.0:
            grade = "🏆 AAA級 (優秀)"
        elif contrast >= 4.5:
            grade = "✅ AA級 (良好)"
        elif contrast >= 3.0:
            grade = "⚠️ AA大文字 (僅適用於大文字)"
        else:
            grade = "❌ 不合格 (需要改善)"
            
        contrast_text = f"""對比度評估: {grade}

WCAG 2.1 標準:
• AAA級: ≥7.0:1 (最高標準)
• AA級: ≥4.5:1 (建議標準)  
• AA大文字: ≥3.0:1 (大文字可接受)"""
        
        self.contrast_info.delete(1.0, tk.END)
        self.contrast_info.insert(1.0, contrast_text)
        
    def update_suggestions(self):
        """更新配色建議"""
        # WCAG建議
        contrast = self.calculate_contrast(self.current_color, self.current_bg)
        
        if contrast < 4.5:
            wcag_text = """⚠️ 對比度建議:
• 使前景色更深或背景色更淺
• 建議前景色: #1D1D1F (深灰)
• 建議背景色: #FFFFFF (白色)
• 或調整當前顏色的亮度"""
        else:
            wcag_text = """✅ 對比度合格:
• 當前配色符合WCAG AA標準
• 適用於正常文字顯示
• 可用於長時間閱讀
• 具有良好的可訪問性"""
            
        self.wcag_suggestions.delete(1.0, tk.END)
        self.wcag_suggestions.insert(1.0, wcag_text)
        
        # 清除舊的顏色建議
        for widget in self.similar_colors_frame.winfo_children():
            widget.destroy()
        for widget in self.complement_colors_frame.winfo_children():
            widget.destroy()
            
        # 生成相似色
        rgb = self.hex_to_rgb(self.current_color)
        hsv = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
        
        similar_colors = []
        for i in range(5):
            new_s = max(0, min(1, hsv[1] + (i-2) * 0.1))
            new_v = max(0, min(1, hsv[2] + (i-2) * 0.1))
            new_rgb = colorsys.hsv_to_rgb(hsv[0], new_s, new_v)
            new_hex = self.rgb_to_hex([c*255 for c in new_rgb])
            similar_colors.append(new_hex)
            
        for i, color in enumerate(similar_colors):
            btn = tk.Button(self.similar_colors_frame, bg=color, width=4, height=2,
                          command=lambda c=color: self.set_color(c))
            btn.grid(row=0, column=i, padx=1)
            
        # 生成互補色
        complement_colors = []
        for offset in [0, 60, 120, 180, 240]:
            new_h = (hsv[0] + offset/360) % 1
            new_rgb = colorsys.hsv_to_rgb(new_h, hsv[1], hsv[2])
            new_hex = self.rgb_to_hex([c*255 for c in new_rgb])
            complement_colors.append(new_hex)
            
        for i, color in enumerate(complement_colors):
            btn = tk.Button(self.complement_colors_frame, bg=color, width=4, height=2,
                          command=lambda c=color: self.set_color(c))
            btn.grid(row=0, column=i, padx=1)
            
    def copy_hex(self):
        """複製HEX代碼"""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.current_color)
        print(f"📋 已複製 HEX: {self.current_color}")
        
    def copy_rgb(self):
        """複製RGB代碼"""
        rgb = self.hex_to_rgb(self.current_color)
        rgb_text = f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"
        self.root.clipboard_clear()
        self.root.clipboard_append(rgb_text)
        print(f"📋 已複製 RGB: {rgb_text}")
        
    def generate_ttk_style(self):
        """生成TTK樣式代碼"""
        style_code = f"""# 🎨 TTK 樣式代碼 (基於您的配色)
self.style.configure('Custom.TButton',
                   background='{self.current_color}',
                   foreground='white',
                   relief='flat',
                   borderwidth=0)

self.style.configure('Custom.TFrame',
                   background='{self.current_bg}',
                   relief='flat')

self.style.configure('Custom.TLabel',
                   background='{self.current_bg}',
                   foreground='{self.current_color}')"""
        
        # 創建新窗口顯示代碼
        code_window = tk.Toplevel(self.root)
        code_window.title("TTK 樣式代碼")
        code_window.geometry("500x300")
        
        text_widget = tk.Text(code_window, font=('Consolas', 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(1.0, style_code)
        
        # 複製按鈕
        tk.Button(code_window, text="📋 複製代碼", 
                 command=lambda: self.copy_to_clipboard(style_code)).pack(pady=5)
        
    def copy_to_clipboard(self, text):
        """複製到剪貼板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        print("📋 TTK樣式代碼已複製到剪貼板")
        
    def export_colors(self):
        """導出配色方案"""
        rgb = self.hex_to_rgb(self.current_color)
        rgb_bg = self.hex_to_rgb(self.current_bg)
        contrast = self.calculate_contrast(self.current_color, self.current_bg)
        
        color_scheme = f"""# 🎨 配色方案導出
# 生成時間: {self.get_current_time()}

## 主要顏色
PRIMARY_COLOR = '{self.current_color}'
PRIMARY_RGB = ({rgb[0]}, {rgb[1]}, {rgb[2]})

## 背景顏色  
BACKGROUND_COLOR = '{self.current_bg}'
BACKGROUND_RGB = ({rgb_bg[0]}, {rgb_bg[1]}, {rgb_bg[2]})

## 對比度資訊
CONTRAST_RATIO = {contrast:.2f}
WCAG_GRADE = '{self.get_wcag_grade(contrast)}'

## 使用建議
# 適用於: {'文字、按鈕' if contrast >= 4.5 else '大文字、圖標'}
# 可訪問性: {'優秀' if contrast >= 7.0 else '良好' if contrast >= 4.5 else '需改善'}
"""
        
        # 保存到文件
        with open('color_scheme.py', 'w', encoding='utf-8') as f:
            f.write(color_scheme)
            
        print("💾 配色方案已導出到 color_scheme.py")
        
    def get_current_time(self):
        """獲取當前時間"""
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def get_wcag_grade(self, contrast):
        """獲取WCAG等級"""
        if contrast >= 7.0:
            return "AAA級"
        elif contrast >= 4.5:
            return "AA級"
        elif contrast >= 3.0:
            return "AA大文字"
        else:
            return "不合格"
            
    def run(self):
        """運行工具"""
        self.root.mainloop()

def main():
    print("🎨 啟動離線顏色編碼工具...")
    tool = OfflineColorTool()
    tool.run()

if __name__ == "__main__":
    main()
