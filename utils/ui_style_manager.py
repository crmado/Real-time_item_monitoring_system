"""
UI樣式管理模組
負責將UI主題應用到應用程式的各個組件
"""

import tkinter as tk
from tkinter import ttk
from utils.ui_theme import UITheme


class UIStyleManager:
    """UI樣式管理類別，負責應用UI主題到應用程式的各個組件"""
    
    def __init__(self, root, theme_name=None):
        """
        初始化UI樣式管理器
        
        Args:
            root: tkinter根視窗
            theme_name: 主題名稱，'light'或'dark'，默認為'light'
        """
        self.root = root
        self.ui_theme = UITheme(theme_name or 'light')
        self.style = ttk.Style(root)
        
        # 初始化樣式
        self.apply_theme()
    
    def apply_theme(self):
        """應用當前主題到所有組件"""
        # 獲取當前主題顏色
        colors = self.ui_theme.get_all_colors()
        
        # 使用較為彈性的基礎主題
        self.style.theme_use('clam')
        
        # 設定根視窗背景色
        self.root.configure(background=colors['bg_main'])
        
        # 設定一般元件樣式
        self._setup_general_styles(colors)
        
        # 設定特定元件樣式
        self._setup_specific_styles(colors)
        
        # 設定自定義樣式
        self._setup_custom_styles(colors)
    
    def _setup_general_styles(self, colors):
        """設定一般元件樣式"""
        # 設定基本樣式
        self.style.configure('.',
            background=colors['bg_main'],
            foreground=colors['text_primary'],
            font=('PingFang TC', 10),
            relief='flat'
        )

        # 設定按鈕樣式
        self.style.configure('TButton',
            background=colors['button_bg'],
            foreground=colors['button_fg'],
            padding=(10, 5),
            font=('PingFang TC', 10),
            relief='raised',
            borderwidth=1
        )

        # 設定強調按鈕樣式
        self.style.configure('Accent.TButton',
            background=colors['button_accent_bg'],
            foreground=colors['button_accent_fg'],
            padding=(10, 5),
            font=('PingFang TC', 10, 'bold'),
            relief='raised',
            borderwidth=1
        )

        # 設定標籤樣式
        self.style.configure('TLabel',
            background=colors['bg_main'],
            foreground=colors['text_primary'],
            font=('PingFang TC', 10),
            padding=(5, 2)
        )

        # 設定輸入框樣式
        self.style.configure('TEntry',
            fieldbackground=colors['input_bg'],
            foreground=colors['text_primary'],
            padding=(5, 2),
            relief='solid',
            borderwidth=1
        )

        # 設定下拉選單樣式
        self.style.configure('TCombobox',
            fieldbackground=colors['input_bg'],
            foreground=colors['text_primary'],
            padding=(5, 2),
            relief='solid',
            borderwidth=1
        )

        # 設定下拉選單各狀態的樣式映射
        self.style.map('TCombobox',
                      fieldbackground=[('readonly', colors['input_bg'])],
                      foreground=[('readonly', colors['input_fg'])],
                      selectbackground=[('readonly', colors['primary'])],
                      selectforeground=[('readonly', colors['text_light'])])
        
        # 配置下拉清單顏色
        self.root.option_add('*TCombobox*Listbox.background', colors['input_bg'])
        self.root.option_add('*TCombobox*Listbox.foreground', colors['input_fg'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', colors['primary'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', colors['text_light'])
        
        # 複選框樣式
        self.style.configure('TCheckbutton', 
                            background=colors['bg_panel'], 
                            foreground=colors['text_primary'])
        
        # 單選按鈕樣式
        self.style.configure('TRadiobutton', 
                            background=colors['bg_panel'], 
                            foreground=colors['text_primary'])
        
        # 數字輸入框樣式
        self.style.configure('TSpinbox', 
                            background=colors['input_bg'], 
                            foreground=colors['input_fg'],
                            fieldbackground=colors['input_bg'])
    
    def _setup_specific_styles(self, colors):
        """設定特定元件樣式"""
        # 設定控制面板樣式
        self.style.configure('Control.TFrame',
            background=colors['bg_control'],
            relief='flat',
            borderwidth=0,
            padding=10
        )
        
        # 設定控制面板標籤框樣式
        self.style.configure('Control.TLabelFrame',
            background=colors['bg_control'],
            foreground=colors['text_primary'],
            relief='groove',
            borderwidth=1,
            padding=5
        )
        
        # 設定控制面板標籤框標籤樣式
        self.style.configure('Control.TLabelFrame.Label',
            background=colors['bg_control'],
            foreground=colors['text_primary'],
            font=('PingFang TC', 10, 'bold')
        )

        # 設定視訊面板樣式
        self.style.configure('Video.TFrame',
            background=colors['bg_video'],
            relief='flat',
            borderwidth=0,
            padding=0
        )
        
        # 設定視訊容器樣式
        self.style.configure('VideoContainer.TFrame',
            background=colors['bg_video'],
            relief='flat',
            borderwidth=0,
            padding=0
        )
        
        # 設定視訊標籤樣式
        self.style.configure('Video.TLabel',
            background=colors['bg_video'],
            foreground=colors['text_primary'],
            relief='flat',
            borderwidth=0,
            padding=0
        )

        # 設定設定面板樣式
        self.style.configure('Settings.TFrame',
            background=colors['bg_settings'],
            relief='flat',
            borderwidth=0,
            padding=10
        )

        # 設定標題樣式
        self.style.configure('Title.TLabel',
            font=('PingFang TC', 12, 'bold'),
            background=colors['bg_header'],
            foreground=colors['text_primary'],
            padding=(10, 5)
        )

        # 設定日誌區域樣式
        self.style.configure('Log.TFrame',
            background=colors['bg_panel'],
            relief='solid',
            borderwidth=1,
            padding=5
        )

        # 設定頂部區域樣式
        self.style.configure('Header.TFrame', 
                            background=colors['bg_header'],
                            borderwidth=1,
                            relief='solid')
        
        # 設定底部區域樣式
        self.style.configure('Footer.TFrame', 
                            background=colors['bg_footer'],
                            borderwidth=1,
                            relief='solid')
    
    def _setup_custom_styles(self, colors):
        """設定自定義樣式"""
        # 設定頁首樣式
        self.style.configure('Header.TFrame',
            background=colors['bg_header'],
            relief='flat',
            borderwidth=0,
            padding=5
        )

        # 設定頁尾樣式
        self.style.configure('Footer.TFrame',
            background=colors['bg_footer'],
            relief='flat',
            borderwidth=0,
            padding=5
        )

        # 設定圖標按鈕樣式
        self.style.configure('Icon.TButton',
            padding=2,
            relief='flat',
            borderwidth=0
        )

        # 設定警告文字樣式
        self.style.configure('Warning.TLabel',
            foreground=colors['warning'],
            font=('PingFang TC', 10, 'bold')
        )

        # 設定錯誤文字樣式
        self.style.configure('Error.TLabel',
            foreground=colors['danger'],
            font=('PingFang TC', 10, 'bold')
        )

        # 設定成功文字樣式
        self.style.configure('Success.TLabel',
            foreground=colors['success'],
            font=('PingFang TC', 10, 'bold')
        )

        # 計數器樣式
        self.style.configure('Counter.TLabel',
            font=('Arial', 12, 'bold'),
            background=colors['bg_settings'],
            foreground=colors['text_primary'])
        
        self.style.configure('CounterNum.TLabel',
            font=('Arial', 14, 'bold'),
            background=colors['bg_settings'],
            foreground=colors['secondary'])
        
        # 設定按鈕樣式
        self.style.configure('Settings.TButton',
            font=('Arial', 10),
            background=colors['button_bg'],
            foreground=colors['button_fg'])

        # 設定控制面板標題樣式
        self.style.configure('ControlTitle.TLabel',
            background=colors['bg_control'],
            foreground=colors['text_primary'],
            font=('PingFang TC', 11, 'bold'),
            padding=(5, 2)
        )

        # 設定控制面板標頭樣式
        self.style.configure('ControlHeader.TFrame',
            background=colors['bg_header'],
            relief='flat',
            borderwidth=0,
            padding=0
        )
    
    def set_theme(self, theme_name):
        """
        設置主題
        
        Args:
            theme_name: 主題名稱，'light'或'dark'
            
        Returns:
            bool: 是否成功設置
        """
        if self.ui_theme.set_theme(theme_name):
            self.apply_theme()
            return True
        return False
    
    def get_current_theme(self):
        """
        獲取當前主題名稱
        
        Returns:
            str: 主題名稱
        """
        return self.ui_theme.theme_name 