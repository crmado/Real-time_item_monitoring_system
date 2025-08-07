"""
主題管理器 - 統一應用和管理UI樣式
負責將主題配置應用到tkinter組件，實現樣式與邏輯的分離
整合跨平台支援，確保在不同操作系統上顯示一致
"""

import tkinter as tk
from tkinter import ttk
import logging
from .apple_theme import AppleTheme
from .cross_platform_ui_manager import get_ui_manager, initialize_ui_manager


class ThemeManager:
    """主題管理器 - 類似CSS的樣式應用系統"""
    
    def __init__(self, root_window, theme_class=AppleTheme):
        """
        初始化主題管理器
        
        Args:
            root_window: tkinter根視窗
            theme_class: 主題類別，默認使用AppleTheme
        """
        self.root = root_window
        self.theme = theme_class
        self.style = ttk.Style()
        self.current_theme_name = theme_class.__name__
        
        # 初始化跨平台 UI 管理器
        self.ui_manager = initialize_ui_manager(root_window)
        
        # 字體檢查和回退機制（保留向後相容性）
        self._setup_fonts()
        
        # 應用主題
        self.apply_theme()
        
        # 配置窗口跨平台設定
        self.ui_manager.configure_window()
        
        # 記錄平台資訊
        self.ui_manager.log_platform_info()
        
        logging.info(f"✅ 主題管理器初始化完成 - 當前主題: {self.current_theme_name} (跨平台支援已啟用)")
    
    def _setup_fonts(self):
        """設置字體，包含回退機制"""
        try:
            import tkinter.font as tkFont
            available_fonts = tkFont.families()
            
            # 檢查主要字體是否可用
            if self.theme.Typography.FONT_FAMILY_PRIMARY not in available_fonts:
                self.primary_font_family = self.theme.Typography.FONT_FAMILY_FALLBACK
                logging.info(f"使用回退字體: {self.primary_font_family}")
            else:
                self.primary_font_family = self.theme.Typography.FONT_FAMILY_PRIMARY
                
            # 檢查等寬字體
            if self.theme.Typography.FONT_FAMILY_MONO not in available_fonts:
                self.mono_font_family = self.theme.Typography.FONT_FAMILY_MONO_FALLBACK
            else:
                self.mono_font_family = self.theme.Typography.FONT_FAMILY_MONO
                
        except Exception as e:
            logging.warning(f"字體檢查失敗，使用默認字體: {str(e)}")
            self.primary_font_family = 'Arial'
            self.mono_font_family = 'Courier New'
    
    def get_font(self, size, weight='normal', family='primary'):
        """獲取字體配置"""
        if family == 'primary':
            font_family = self.primary_font_family
        elif family == 'mono':
            font_family = self.mono_font_family
        else:
            font_family = self.primary_font_family
            
        return (font_family, size, weight)
    
    def apply_theme(self):
        """應用完整主題"""
        try:
            # 設置根視窗背景
            self.root.configure(bg=self.theme.Colors.BACKGROUND_PRIMARY)
            
            # 應用ttk樣式
            self._apply_ttk_styles()
            
            logging.info("主題應用成功")
            
        except Exception as e:
            logging.error(f"應用主題失敗: {str(e)}")
    
    def _apply_ttk_styles(self):
        """應用ttk組件樣式 - 🎨 使用跨平台動態顏色"""
        
        # 🌈 獲取跨平台動態顏色（關鍵修復！）
        bg_primary = self.get_platform_color('background_primary')
        bg_card = self.get_platform_color('background_card')
        bg_secondary = self.get_platform_color('background_secondary')
        text_primary = self.get_platform_color('text_primary')
        text_secondary = self.get_platform_color('text_secondary')
        primary_blue = self.get_platform_color('primary_blue')
        border_light = self.get_platform_color('border_light')
        
        # ==================== Frame 樣式 ====================
        self.style.configure('Apple.TFrame',
                           background=bg_card,  # 使用動態顏色
                           relief='flat',
                           borderwidth=0)
        
        self.style.configure('AppleCard.TFrame',
                           background=bg_card,  # 使用動態顏色
                           relief='solid',
                           borderwidth=self.theme.Dimensions.BORDER_WIDTH_NORMAL,
                           lightcolor=border_light,  # 使用動態顏色
                           darkcolor=border_light)   # 使用動態顏色
        
        # ==================== LabelFrame 樣式 ====================
        self.style.configure('Apple.TLabelframe',
                           background=bg_card,    # 使用動態顏色
                           relief='solid',
                           borderwidth=self.theme.Dimensions.BORDER_WIDTH_THIN,
                           lightcolor=border_light,  # 使用動態顏色
                           darkcolor=border_light,   # 使用動態顏色
                           padding=(self.theme.Dimensions.SPACING_XL, 
                                   self.theme.Dimensions.SPACING_LG))
        
        self.style.configure('Apple.TLabelframe.Label',
                           background=bg_card,      # 使用動態顏色
                           foreground=text_primary, # 使用動態顏色
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                            self.theme.Typography.FONT_WEIGHT_BOLD))
        
        # ==================== Button 樣式 ====================
        # 主要按鈕 - 🎨 使用優化後的對比度顏色
        self.style.configure('Apple.TButton',
                           background=primary_blue,  # 使用優化後的藍色 #0051D5
                           foreground='#ffffff',
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                            self.theme.Typography.FONT_WEIGHT_BOLD),
                           relief='flat',
                           borderwidth=0,
                           focuscolor='none',
                           padding=(self.theme.Dimensions.SPACING_LG, 
                                   self.theme.Dimensions.SPACING_SM))
        
        # 動態獲取懸停和按下狀態的顏色
        hover_blue = '#0040B8'  # 比優化藍色更深
        pressed_blue = '#003399'  # 最深的藍色
        
        self.style.map('Apple.TButton',
                      background=[('active', hover_blue),
                                ('pressed', pressed_blue),
                                ('disabled', bg_secondary)],  # 使用動態顏色
                      foreground=[('disabled', text_secondary)])  # 使用動態顏色
        
        # 次要按鈕 - 🎨 使用動態顏色
        self.style.configure('AppleSecondary.TButton',
                           background=bg_secondary,   # 使用動態背景色
                           foreground=primary_blue,   # 使用優化後的藍色文字
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                            self.theme.Typography.FONT_WEIGHT_REGULAR),
                           relief='solid',
                           borderwidth=1,
                           focuscolor='none',
                           padding=(self.theme.Dimensions.SPACING_LG, 
                                   self.theme.Dimensions.SPACING_SM))
        
        self.style.map('AppleSecondary.TButton',
                      background=[('active', border_light),    # 使用動態顏色
                                ('pressed', border_light),     # 使用動態顏色  
                                ('disabled', bg_secondary)],   # 使用動態顏色
                      foreground=[('disabled', text_secondary)], # 使用動態顏色
                      bordercolor=[('active', primary_blue)])     # 使用優化藍色
        
        # 成功按鈕
        self.style.configure('AppleSuccess.TButton',
                           background=self.theme.Colors.SUCCESS_GREEN,
                           foreground=self.theme.Colors.BACKGROUND_CARD,
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                            self.theme.Typography.FONT_WEIGHT_REGULAR),
                           padding=(self.theme.Dimensions.SPACING_LG, 
                                   self.theme.Dimensions.SPACING_SM),
                           relief='flat',
                           borderwidth=0,
                           focuscolor='none')
        
        # 警告按鈕
        self.style.configure('AppleWarning.TButton',
                           background=self.theme.Colors.WARNING_ORANGE,
                           foreground=self.theme.Colors.BACKGROUND_CARD,
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                            self.theme.Typography.FONT_WEIGHT_REGULAR),
                           padding=(self.theme.Dimensions.SPACING_LG, 
                                   self.theme.Dimensions.SPACING_SM),
                           relief='flat',
                           borderwidth=0,
                           focuscolor='none')
        
        # ==================== Label 樣式 ====================
        # 🎨 使用動態顏色的標籤樣式
        self.style.configure('Apple.TLabel',
                           background=bg_card,      # 使用動態顏色
                           foreground=text_primary) # 使用動態顏色
        
        self.style.configure('AppleTitle.TLabel',
                           background=bg_card,      # 使用動態顏色
                           foreground=text_primary, # 使用動態顏色
                           font=self.get_font(self.theme.Typography.FONT_SIZE_HEADLINE,
                                            self.theme.Typography.FONT_WEIGHT_BOLD))
        
        self.style.configure('AppleCaption.TLabel',
                           background=bg_card,       # 使用動態顏色
                           foreground=text_secondary) # 使用動態顏色
        
        self.style.configure('AppleAccent.TLabel',
                           background=bg_card,   # 使用動態顏色
                           foreground=primary_blue, # 使用優化後的藍色
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                            self.theme.Typography.FONT_WEIGHT_MEDIUM))
        
        # ==================== Entry 樣式 ====================
        # 🎨 使用動態顏色的輸入框樣式  
        self.style.configure('Apple.TEntry',
                           fieldbackground=bg_card,    # 使用動態顏色
                           background=bg_card,         # 使用動態顏色
                           bordercolor=border_light,   # 使用動態顏色
                           lightcolor=border_light,    # 使用動態顏色
                           darkcolor=border_light,     # 使用動態顏色
                           relief='solid',
                           borderwidth=self.theme.Dimensions.BORDER_WIDTH_NORMAL,
                           insertcolor=text_primary,   # 使用動態顏色
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY),
                           padding=(self.theme.Dimensions.SPACING_MD, 
                                   self.theme.Dimensions.SPACING_SM))
        
        self.style.map('Apple.TEntry',
                      bordercolor=[('focus', self.theme.Colors.PRIMARY_BLUE),
                                 ('invalid', self.theme.Colors.ERROR_RED)])
        
        # ==================== Combobox 樣式 ====================
        self.style.configure('Apple.TCombobox',
                           fieldbackground=self.theme.Colors.BACKGROUND_INPUT,
                           background=self.theme.Colors.BACKGROUND_CARD,
                           bordercolor=self.theme.Colors.BORDER_LIGHT,
                           lightcolor=self.theme.Colors.BORDER_LIGHT,
                           darkcolor=self.theme.Colors.BORDER_LIGHT,
                           arrowcolor=self.theme.Colors.TEXT_SECONDARY,
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY),
                           padding=(self.theme.Dimensions.SPACING_MD, 
                                   self.theme.Dimensions.SPACING_SM))
        
        # ==================== Progressbar 樣式 ====================
        self.style.configure('Apple.Horizontal.TProgressbar',
                           background=self.theme.Colors.PRIMARY_BLUE,
                           troughcolor=self.theme.Colors.BACKGROUND_SECONDARY,
                           borderwidth=0,
                           lightcolor=self.theme.Colors.PRIMARY_BLUE,
                           darkcolor=self.theme.Colors.PRIMARY_BLUE,
                           barrelief='flat',
                           relief='flat')
        
        # ==================== Scale 滑塊樣式 ====================
        self.style.configure('Apple.Horizontal.TScale',
                           background=self.theme.Colors.BACKGROUND_CARD,
                           troughcolor=self.theme.Colors.BACKGROUND_SECONDARY,
                           borderwidth=0,
                           sliderrelief='raised',
                           sliderlength=24,
                           sliderwidth=16,
                           activebackground=self.theme.Colors.PRIMARY_BLUE,
                           relief='flat')
        
        # 針對滑塊滑動時的樣式
        self.style.map('Apple.Horizontal.TScale',
                      background=[('active', self.theme.Colors.PRIMARY_BLUE_HOVER)],
                      slidercolor=[('active', self.theme.Colors.PRIMARY_BLUE)])
        
        # ==================== Checkbutton 樣式 ====================
        self.style.configure('Apple.TCheckbutton',
                           background=self.theme.Colors.BACKGROUND_CARD,
                           foreground=self.theme.Colors.TEXT_PRIMARY,
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY),
                           focuscolor='none')
        
        # ==================== Spinbox 樣式 ====================
        self.style.configure('Apple.TSpinbox',
                           fieldbackground=self.theme.Colors.BACKGROUND_INPUT,
                           background=self.theme.Colors.BACKGROUND_CARD,
                           bordercolor=self.theme.Colors.BORDER_LIGHT,
                           arrowcolor=self.theme.Colors.TEXT_SECONDARY,
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY))
    
    def create_status_label(self, parent, text, status_type='info'):
        """創建狀態標籤，帶有對應的顏色"""
        status_colors = self.theme.States.status_colors()
        color = status_colors.get(status_type, self.theme.Colors.TEXT_PRIMARY)
        
        return tk.Label(parent, 
                       text=text,
                       font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                        self.theme.Typography.FONT_WEIGHT_REGULAR),
                       fg=color,
                       bg=self.theme.Colors.BACKGROUND_CARD)
    
    def create_card_frame(self, parent, **kwargs):
        """創建卡片式框架 - 增強視覺效果"""
        # 使用tk.Frame以支持更多視覺效果
        frame = tk.Frame(parent,
                        bg=self.theme.Colors.BACKGROUND_CARD,
                        relief='raised',  # 使用raised效果代替陰影
                        bd=1,
                        highlightbackground=self.theme.Colors.BORDER_LIGHT,
                        highlightcolor=self.theme.Colors.BORDER_LIGHT,
                        highlightthickness=1,
                        **kwargs)
        return frame
    
    def create_display_number(self, parent, textvariable, size='large'):
        """創建數字顯示標籤（用於計數器等）"""
        if size == 'large':
            font_size = self.theme.Typography.FONT_SIZE_DISPLAY
        elif size == 'medium':
            font_size = self.theme.Typography.FONT_SIZE_TITLE1
        else:
            font_size = self.theme.Typography.FONT_SIZE_TITLE2
            
        return tk.Label(parent,
                       textvariable=textvariable,
                       font=self.get_font(font_size, 
                                        self.theme.Typography.FONT_WEIGHT_BOLD,
                                        'mono'),
                       fg=self.theme.Colors.PRIMARY_BLUE,
                       bg=self.theme.Colors.BACKGROUND_SECONDARY)
    
    def update_theme(self, new_theme_class):
        """更新主題"""
        self.theme = new_theme_class
        self.current_theme_name = new_theme_class.__name__
        self.apply_theme()
        logging.info(f"主題已更新為: {self.current_theme_name}")
    
    def get_color(self, color_name):
        """獲取主題顏色"""
        return getattr(self.theme.Colors, color_name, self.theme.Colors.TEXT_PRIMARY)
    
    def get_dimension(self, dimension_name):
        """獲取主題尺寸"""
        return getattr(self.theme.Dimensions, dimension_name, 8)
    
    # ==================== 跨平台 UI 便利方法 ====================
    
    def create_cross_platform_button(self, parent, text, command=None, button_type='primary', **kwargs):
        """創建跨平台一致的按鈕 - 整合主題樣式"""
        return self.ui_manager.create_button(parent, text, command, button_type, **kwargs)
    
    def create_cross_platform_label(self, parent, text, label_type='body', **kwargs):
        """創建跨平台一致的標籤 - 整合主題樣式"""
        return self.ui_manager.create_label(parent, text, label_type, **kwargs)
    
    def create_cross_platform_entry(self, parent, textvariable=None, **kwargs):
        """創建跨平台一致的輸入框 - 整合主題樣式"""
        return self.ui_manager.create_entry(parent, textvariable, **kwargs)
    
    def create_cross_platform_frame(self, parent, frame_type='card', **kwargs):
        """創建跨平台一致的框架 - 整合主題樣式"""
        return self.ui_manager.create_frame(parent, frame_type, **kwargs)
    
    def create_cross_platform_status_display(self, parent, status_type='info'):
        """創建跨平台狀態顯示"""
        return self.ui_manager.create_status_display(parent, status_type)
    
    def get_safe_text(self, text):
        """獲取安全的文字顯示，防止編碼問題"""
        return self.ui_manager.font_manager.get_safe_text(text)
    
    def get_platform_color(self, color_name):
        """獲取平台特定顏色"""
        return self.ui_manager.color_manager.get_platform_color(color_name)
    
    def get_platform_font(self, font_type='primary', size=12, weight='normal'):
        """獲取平台特定字體"""
        return self.ui_manager.font_manager.get_best_font(font_type, size, weight)
    
    def apply_cross_platform_style(self, widget, widget_type):
        """將跨平台樣式應用到 widget"""
        self.ui_manager.apply_theme_to_widget(widget, widget_type)