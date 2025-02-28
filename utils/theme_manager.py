"""
主題管理模組
管理應用程式主題切換
"""

import tkinter as tk
from tkinter import ttk


class ThemeManager:
    """主題管理類別"""

    def __init__(self, root):
        """
        初始化主題管理器

        Args:
            root: tkinter 根視窗
        """
        self.root = root
        self.current_theme = "light"
        self._define_themes()

    def _define_themes(self):
        """定義亮色和暗色主題樣式"""
        # 定義亮色主題
        self.light_theme = {
            'bg': '#f0f0f0',
            'fg': '#000000',
            'button_bg': '#e0e0e0',
            'button_fg': '#000000',
            'accent': '#0078d7',
            'accent_fg': '#ffffff',
            'entry_bg': '#ffffff',
            'entry_fg': '#000000',
            'panel_bg': '#f5f5f5'
        }

        # 定義暗色主題
        self.dark_theme = {
            'bg': '#1e1e1e',  # 更深的背景色
            'fg': '#ffffff',  # 更亮的文字顏色
            'button_bg': '#333333',  # 按鈕背景
            'button_fg': '#ffffff',  # 按鈕文字
            'accent': '#0096ff',  # 更亮的藍色調
            'accent_fg': '#ffffff',  # 強調按鈕文字
            'entry_bg': '#2a2a2a',  # 輸入框背景
            'entry_fg': '#000000',  # 輸入框文字
            'panel_bg': '#252525'  # 面板背景
        }

    def apply_theme(self, theme_name):
        """
        套用指定主題

        Args:
            theme_name: 主題名稱 ('light' 或 'dark')

        Returns:
            bool: 是否成功套用
        """
        if theme_name not in ["light", "dark"]:
            return False

        # 如果主題沒有變更，不重新應用
        if self.current_theme == theme_name:
            return True

        self.current_theme = theme_name
        theme = self.light_theme if theme_name == "light" else self.dark_theme

        # 設定 ttk 樣式
        style = ttk.Style(self.root)
        style.theme_use('clam')  # 使用較為彈性的基礎主題

        # 設定一般元件樣式
        style.configure('TFrame', background=theme['bg'])
        style.configure('TLabel', background=theme['bg'], foreground=theme['fg'])
        style.configure('TButton', background=theme['button_bg'], foreground=theme['button_fg'])
        style.configure('TEntry', background=theme['entry_bg'], foreground=theme['entry_fg'])
        style.configure('TCombobox', background=theme['entry_bg'], foreground=theme['entry_fg'])
        style.configure('TCheckbutton', background=theme['bg'], foreground=theme['fg'])
        style.configure('TRadiobutton', background=theme['bg'], foreground=theme['fg'])
        style.configure('TSpinbox', background=theme['entry_bg'], foreground=theme['entry_fg'])


        # 設定強調按鈕樣式
        style.configure('Accent.TButton', background=theme['accent'], foreground=theme['accent_fg'])

        # 設定 tk 元件樣式
        self.root.configure(background=theme['bg'])

        return True