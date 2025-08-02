"""
Liquid Glass 主題管理器
實現Apple 2025年Liquid Glass設計理念的動態界面效果
"""

import tkinter as tk
from tkinter import ttk
import logging
from typing import Optional, Dict, Any
from .liquid_glass_theme import LiquidGlassTheme


class LiquidGlassManager:
    """Liquid Glass 主題管理器 - 實現動態玻璃質感界面"""
    
    def __init__(self, root_window, theme_class=LiquidGlassTheme):
        """
        初始化Liquid Glass主題管理器
        
        Args:
            root_window: tkinter根視窗
            theme_class: 主題類別，默認使用LiquidGlassTheme
        """
        self.root = root_window
        self.theme = theme_class
        self.style = ttk.Style()
        self.current_theme_name = "LiquidGlass"
        
        # 字體檢查和回退機制
        self._setup_glass_fonts()
        
        # 應用Liquid Glass主題
        self.apply_liquid_glass_theme()
        
        # 設置動態效果系統
        self._setup_dynamic_effects()
        
        logging.info(f"✨ Liquid Glass主題管理器初始化完成 - 當前主題: {self.current_theme_name}")
    
    def _setup_glass_fonts(self):
        """設置Liquid Glass字體系統，包含智能回退"""
        try:
            import tkinter.font as tkFont
            available_fonts = tkFont.families()
            
            # 檢查SF Pro Display系列
            if self.theme.Typography.FONT_FAMILY_DISPLAY in available_fonts:
                self.display_font_family = self.theme.Typography.FONT_FAMILY_DISPLAY
            elif self.theme.Typography.FONT_FALLBACK_DISPLAY in available_fonts:
                self.display_font_family = self.theme.Typography.FONT_FALLBACK_DISPLAY
            else:
                self.display_font_family = self.theme.Typography.FONT_FALLBACK_SYSTEM
            
            # 檢查SF Pro Text
            if self.theme.Typography.FONT_FAMILY_TEXT in available_fonts:
                self.text_font_family = self.theme.Typography.FONT_FAMILY_TEXT
            elif self.theme.Typography.FONT_FALLBACK_TEXT in available_fonts:
                self.text_font_family = self.theme.Typography.FONT_FALLBACK_TEXT
            else:
                self.text_font_family = self.theme.Typography.FONT_FALLBACK_SYSTEM
                
            # 檢查等寬字體
            if self.theme.Typography.FONT_FAMILY_MONO in available_fonts:
                self.mono_font_family = self.theme.Typography.FONT_FAMILY_MONO
            elif self.theme.Typography.FONT_FALLBACK_MONO in available_fonts:
                self.mono_font_family = self.theme.Typography.FONT_FALLBACK_MONO
            else:
                self.mono_font_family = 'Courier New'
                
            logging.info(f"🔤 字體系統: Display={self.display_font_family}, Text={self.text_font_family}")
                
        except Exception as e:
            logging.warning(f"字體檢查失敗，使用系統默認字體: {str(e)}")
            self.display_font_family = 'Segoe UI'
            self.text_font_family = 'Segoe UI'
            self.mono_font_family = 'Courier New'
    
    def get_glass_font(self, size, weight='normal', context='display'):
        """獲取Liquid Glass字體配置"""
        if context == 'display':
            font_family = self.display_font_family
        elif context == 'text':
            font_family = self.text_font_family
        elif context == 'mono':
            font_family = self.mono_font_family
        else:
            font_family = self.display_font_family
            
        return (font_family, size, weight)
    
    def apply_liquid_glass_theme(self):
        """應用完整的Liquid Glass主題"""
        try:
            # 設置根視窗的玻璃質背景
            self.root.configure(bg=self.theme.Colors.BACKGROUND_GLASS)
            
            # 應用ttk樣式
            self._apply_glass_ttk_styles()
            
            logging.info("✨ Liquid Glass主題應用成功")
            
        except Exception as e:
            logging.error(f"應用Liquid Glass主題失敗: {str(e)}")
    
    def _apply_glass_ttk_styles(self):
        """應用Liquid Glass ttk組件樣式"""
        
        # ==================== Glass Frame 樣式 ====================
        self.style.configure('Glass.TFrame',
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           relief='flat',
                           borderwidth=0)
        
        self.style.configure('GlassCard.TFrame',
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           relief='flat',
                           borderwidth=1,
                           lightcolor=self.theme.Colors.GLASS_SURFACE_MEDIUM,
                           darkcolor=self.theme.Colors.GLASS_SURFACE_MEDIUM)
        
        # ==================== Glass LabelFrame 樣式 ====================
        self.style.configure('Glass.TLabelframe',
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           relief='flat',
                           borderwidth=1,
                           lightcolor=self.theme.Colors.GLASS_SURFACE_LIGHT,
                           darkcolor=self.theme.Colors.GLASS_SURFACE_LIGHT,
                           padding=(self.theme.Dimensions.SPACING_FLUID_XL, 
                                   self.theme.Dimensions.SPACING_FLUID_LG))
        
        self.style.configure('Glass.TLabelframe.Label',
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           foreground=self.theme.Colors.TEXT_GLASS_PRIMARY,
                           font=self.get_glass_font(
                               self.theme.Typography.FONT_SIZE_BODY,
                               self.theme.Typography.FONT_WEIGHT_SEMIBOLD,
                               'display'
                           ))
        
        # ==================== Glass Button 樣式 ====================
        # 主要玻璃按鈕
        self.style.configure('Glass.TButton',
                           **self.theme.GlassPresets.glass_primary_button(),
                           padding=(self.theme.Dimensions.SPACING_FLUID_LG, 
                                   self.theme.Dimensions.SPACING_FLUID_MD))
        
        self.style.map('Glass.TButton',
                      background=[('active', self.theme.Colors.GLASS_PRIMARY_LIGHT),
                                ('pressed', self.theme.Colors.GLASS_PRIMARY_DARK)])
        
        # 次要玻璃按鈕
        self.style.configure('GlassSecondary.TButton',
                           **self.theme.GlassPresets.glass_secondary_button(),
                           padding=(self.theme.Dimensions.SPACING_FLUID_LG, 
                                   self.theme.Dimensions.SPACING_FLUID_MD))
        
        self.style.map('GlassSecondary.TButton',
                      background=[('active', self.theme.Colors.HOVER_GLASS),
                                ('pressed', self.theme.Colors.ACTIVE_GLASS)])
        
        # 成功玻璃按鈕
        self.style.configure('GlassSuccess.TButton',
                           background=self.theme.Colors.GLASS_PRIMARY,
                           foreground='#ffffff',
                           font=self.get_glass_font(
                               self.theme.Typography.FONT_SIZE_BODY,
                               self.theme.Typography.FONT_WEIGHT_SEMIBOLD
                           ),
                           relief='flat',
                           borderwidth=0,
                           padding=(self.theme.Dimensions.SPACING_FLUID_LG, 
                                   self.theme.Dimensions.SPACING_FLUID_MD))
        
        # ==================== Glass Label 樣式 ====================
        self.style.configure('Glass.TLabel',
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           foreground=self.theme.Colors.TEXT_GLASS_PRIMARY,
                           font=self.get_glass_font(
                               self.theme.Typography.FONT_SIZE_BODY,
                               context='text'
                           ))
        
        self.style.configure('GlassTitle.TLabel',
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           foreground=self.theme.Colors.TEXT_GLASS_PRIMARY,
                           font=self.get_glass_font(
                               self.theme.Typography.FONT_SIZE_TITLE2,
                               self.theme.Typography.FONT_WEIGHT_BOLD,
                               'display'
                           ))
        
        self.style.configure('GlassCaption.TLabel',
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           foreground=self.theme.Colors.TEXT_GLASS_SECONDARY,
                           font=self.get_glass_font(
                               self.theme.Typography.FONT_SIZE_CAPTION,
                               context='text'
                           ))
        
        self.style.configure('GlassAccent.TLabel',
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           foreground=self.theme.Colors.TEXT_GLASS_ACCENT,
                           font=self.get_glass_font(
                               self.theme.Typography.FONT_SIZE_BODY,
                               self.theme.Typography.FONT_WEIGHT_SEMIBOLD,
                               'text'
                           ))
        
        # ==================== Glass Entry 樣式 ====================
        self.style.configure('Glass.TEntry',
                           fieldbackground=self.theme.Colors.BACKGROUND_FROSTED,
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           bordercolor=self.theme.Colors.GLASS_SURFACE_MEDIUM,
                           lightcolor=self.theme.Colors.GLASS_SURFACE_LIGHT,
                           darkcolor=self.theme.Colors.GLASS_SURFACE_LIGHT,
                           relief='flat',
                           borderwidth=1,
                           insertcolor=self.theme.Colors.TEXT_GLASS_PRIMARY,
                           font=self.get_glass_font(self.theme.Typography.FONT_SIZE_BODY, context='text'),
                           padding=(self.theme.Dimensions.SPACING_FLUID_MD, 
                                   self.theme.Dimensions.SPACING_FLUID_SM))
        
        self.style.map('Glass.TEntry',
                      bordercolor=[('focus', self.theme.Colors.FOCUS_GLASS)])
        
        # ==================== Glass Progressbar 樣式 ====================
        self.style.configure('Glass.Horizontal.TProgressbar',
                           **self.theme.GlassPresets.glass_progress())
        
        # ==================== Glass Scale 樣式 ====================
        self.style.configure('Glass.Horizontal.TScale',
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           troughcolor=self.theme.Colors.BACKGROUND_FROSTED,
                           borderwidth=0,
                           sliderrelief='flat',
                           sliderlength=28,
                           sliderwidth=20,
                           activebackground=self.theme.Colors.GLASS_PRIMARY_LIGHT,
                           relief='flat')
        
        self.style.map('Glass.Horizontal.TScale',
                      slidercolor=[('active', self.theme.Colors.GLASS_PRIMARY)])
        
        # ==================== Glass Checkbutton 樣式 ====================
        self.style.configure('Glass.TCheckbutton',
                           background=self.theme.Colors.BACKGROUND_CRYSTAL,
                           foreground=self.theme.Colors.TEXT_GLASS_PRIMARY,
                           font=self.get_glass_font(self.theme.Typography.FONT_SIZE_BODY, context='text'),
                           focuscolor='none')
    
    def _setup_dynamic_effects(self):
        """設置動態效果系統"""
        self.hover_effects = {}
        self.animation_queue = []
        
        # 註冊動態效果處理器
        self.root.after(100, self._process_animations)
    
    def _process_animations(self):
        """處理動畫隊列"""
        # 在tkinter限制下的簡化動畫系統
        if self.animation_queue:
            # 處理動畫隊列中的效果
            pass
        
        # 繼續動畫循環
        self.root.after(50, self._process_animations)
    
    def create_glass_card(self, parent, **kwargs):
        """創建Liquid Glass卡片容器"""
        # 外層陰影容器
        shadow_container = tk.Frame(parent, 
                                   bg=self.theme.Colors.SHADOW_GLASS_SOFT,
                                   relief='flat',
                                   bd=0)
        
        # 內層玻璃卡片
        glass_card = tk.Frame(shadow_container,
                             **self.theme.GlassPresets.glass_card(),
                             **kwargs)
        
        # 設置卡片內的陰影效果
        glass_card.pack(fill=tk.BOTH, expand=True, 
                       padx=(0, 2), pady=(0, 2))
        
        return shadow_container, glass_card
    
    def create_glass_status_label(self, parent, text, status_type='info'):
        """創建玻璃質感狀態標籤"""
        status_colors = {
            'connected': self.theme.Colors.GLASS_PRIMARY,
            'disconnected': '#ff3b30',    # 紅色
            'warning': '#ff9500',         # 橙色
            'info': '#af52de',            # 紫色
            'processing': self.theme.Colors.GLASS_PRIMARY_LIGHT
        }
        
        color = status_colors.get(status_type, self.theme.Colors.TEXT_GLASS_PRIMARY)
        
        return tk.Label(parent, 
                       text=text,
                       font=self.get_glass_font(
                           self.theme.Typography.FONT_SIZE_BODY,
                           self.theme.Typography.FONT_WEIGHT_REGULAR,
                           'text'
                       ),
                       fg=color,
                       bg=self.theme.Colors.BACKGROUND_CRYSTAL)
    
    def create_glass_display_number(self, parent, textvariable, size='large'):
        """創建玻璃質感的大數字顯示"""
        if size == 'large':
            font_size = self.theme.Typography.FONT_SIZE_DISPLAY
        elif size == 'medium':
            font_size = self.theme.Typography.FONT_SIZE_TITLE1
        else:
            font_size = self.theme.Typography.FONT_SIZE_TITLE2
            
        # 數字背景容器
        number_bg = tk.Frame(parent,
                            bg=self.theme.Colors.BACKGROUND_FROSTED,
                            relief='flat',
                            bd=1,
                            highlightbackground=self.theme.Colors.GLASS_SURFACE_MEDIUM,
                            highlightthickness=1)
        
        # 數字標籤
        number_label = tk.Label(number_bg,
                               textvariable=textvariable,
                               font=self.get_glass_font(
                                   font_size, 
                                   self.theme.Typography.FONT_WEIGHT_BOLD,
                                   'mono'
                               ),
                               fg=self.theme.Colors.GLASS_PRIMARY,
                               bg=self.theme.Colors.BACKGROUND_FROSTED)
        
        number_label.pack(expand=True, fill=tk.BOTH,
                         padx=self.theme.Dimensions.SPACING_FLUID_LG,
                         pady=self.theme.Dimensions.SPACING_FLUID_MD)
        
        return number_bg
    
    def add_hover_effect(self, widget, effect_type='glass'):
        """為組件添加懸停效果"""
        def on_enter(event):
            if effect_type == 'glass':
                widget.configure(bg=self.theme.Colors.HOVER_GLASS)
        
        def on_leave(event):
            widget.configure(bg=self.theme.Colors.BACKGROUND_CRYSTAL)
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def get_glass_color(self, color_name):
        """獲取Liquid Glass主題顏色"""
        return getattr(self.theme.Colors, color_name, self.theme.Colors.TEXT_GLASS_PRIMARY)
    
    def get_glass_dimension(self, dimension_name):
        """獲取Liquid Glass主題尺寸"""
        return getattr(self.theme.Dimensions, dimension_name, 8)
    
    def apply_glass_blur_effect(self, widget):
        """應用玻璃模糊效果 (tkinter限制下的模擬)"""
        # 在tkinter限制下，使用半透明背景模擬模糊效果
        widget.configure(bg=self.theme.Colors.BACKGROUND_FROSTED)
    
    def create_floating_toolbar(self, parent):
        """創建懸浮式玻璃工具欄"""
        # 外層容器
        toolbar_container = tk.Frame(parent, bg=self.theme.Colors.BACKGROUND_GLASS)
        
        # 內層玻璃工具欄
        toolbar = tk.Frame(toolbar_container,
                          bg=self.theme.Colors.BACKGROUND_CRYSTAL,
                          relief='flat',
                          bd=1,
                          highlightbackground=self.theme.Colors.GLASS_SURFACE_HEAVY,
                          highlightthickness=1)
        
        # 設置懸浮效果
        toolbar.pack(fill=tk.X, padx=2, pady=2)
        
        return toolbar_container, toolbar
    
    def animate_glass_transition(self, widget, from_color, to_color, duration=300):
        """玻璃過渡動畫 (簡化版本)"""
        # 在tkinter限制下的簡化過渡效果
        def transition():
            widget.configure(bg=to_color)
        
        # 延遲執行過渡
        self.root.after(duration // 2, transition)
    
    def update_glass_theme(self, new_theme_class):
        """更新Liquid Glass主題"""
        self.theme = new_theme_class
        self.current_theme_name = new_theme_class.__name__
        self.apply_liquid_glass_theme()
        logging.info(f"✨ Liquid Glass主題已更新為: {self.current_theme_name}")