"""
主題管理器 - 統一應用和管理UI樣式
負責將主題配置應用到tkinter組件，實現樣式與邏輯的分離
"""

import tkinter as tk
from tkinter import ttk
import logging
from .apple_theme import AppleTheme


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
        
        # 字體檢查和回退機制
        self._setup_fonts()
        
        # 應用主題
        self.apply_theme()
        
        logging.info(f"✅ 主題管理器初始化完成 - 當前主題: {self.current_theme_name}")
    
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
        """應用ttk組件樣式"""
        
        # ==================== Frame 樣式 ====================
        self.style.configure('Apple.TFrame',
                           background=self.theme.Colors.BACKGROUND_CARD,
                           relief='flat',
                           borderwidth=0)
        
        self.style.configure('AppleCard.TFrame',
                           background=self.theme.Colors.BACKGROUND_CARD,
                           relief='solid',
                           borderwidth=self.theme.Dimensions.BORDER_WIDTH_NORMAL,
                           lightcolor=self.theme.Colors.BORDER_LIGHT,
                           darkcolor=self.theme.Colors.BORDER_LIGHT)
        
        # ==================== LabelFrame 樣式 ====================
        self.style.configure('Apple.TLabelframe',
                           background=self.theme.Colors.BACKGROUND_CARD,
                           relief='solid',
                           borderwidth=self.theme.Dimensions.BORDER_WIDTH_THIN,
                           lightcolor=self.theme.Colors.BORDER_LIGHT,
                           darkcolor=self.theme.Colors.BORDER_LIGHT,
                           padding=(self.theme.Dimensions.SPACING_XL, 
                                   self.theme.Dimensions.SPACING_LG))
        
        self.style.configure('Apple.TLabelframe.Label',
                           background=self.theme.Colors.BACKGROUND_CARD,
                           foreground=self.theme.Colors.TEXT_PRIMARY,
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                            self.theme.Typography.FONT_WEIGHT_BOLD))
        
        # ==================== Button 樣式 ====================
        # 主要按鈕 - 增強對比度
        self.style.configure('Apple.TButton',
                           background='#007aff',
                           foreground='#ffffff',
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                            self.theme.Typography.FONT_WEIGHT_BOLD),
                           relief='flat',
                           borderwidth=0,
                           focuscolor='none',
                           padding=(self.theme.Dimensions.SPACING_LG, 
                                   self.theme.Dimensions.SPACING_SM))
        
        self.style.map('Apple.TButton',
                      background=[('active', '#0056cc'),
                                ('pressed', '#004499'),
                                ('disabled', '#d1d1d6')],
                      foreground=[('disabled', '#8e8e93')])
        
        # 次要按鈕 - 增強可見性
        self.style.configure('AppleSecondary.TButton',
                           background='#f2f2f7',
                           foreground='#007aff',
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                            self.theme.Typography.FONT_WEIGHT_REGULAR),
                           relief='solid',
                           borderwidth=1,
                           focuscolor='none',
                           padding=(self.theme.Dimensions.SPACING_LG, 
                                   self.theme.Dimensions.SPACING_SM))
        
        self.style.map('AppleSecondary.TButton',
                      background=[('active', '#e5e5ea'),
                                ('pressed', '#d1d1d6'),
                                ('disabled', '#f2f2f7')],
                      foreground=[('disabled', '#8e8e93')],
                      bordercolor=[('active', '#007aff')])
        
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
        self.style.configure('Apple.TLabel',
                           **self.theme.Presets.label_body())
        
        self.style.configure('AppleTitle.TLabel',
                           **self.theme.Presets.label_title())
        
        self.style.configure('AppleCaption.TLabel',
                           **self.theme.Presets.label_caption())
        
        self.style.configure('AppleAccent.TLabel',
                           background=self.theme.Colors.BACKGROUND_CARD,
                           foreground=self.theme.Colors.TEXT_ACCENT,
                           font=self.get_font(self.theme.Typography.FONT_SIZE_BODY,
                                            self.theme.Typography.FONT_WEIGHT_MEDIUM))
        
        # ==================== Entry 樣式 ====================
        self.style.configure('Apple.TEntry',
                           fieldbackground=self.theme.Colors.BACKGROUND_INPUT,
                           background=self.theme.Colors.BACKGROUND_CARD,
                           bordercolor=self.theme.Colors.BORDER_LIGHT,
                           lightcolor=self.theme.Colors.BORDER_LIGHT,
                           darkcolor=self.theme.Colors.BORDER_LIGHT,
                           relief='solid',
                           borderwidth=self.theme.Dimensions.BORDER_WIDTH_NORMAL,
                           insertcolor=self.theme.Colors.TEXT_PRIMARY,
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