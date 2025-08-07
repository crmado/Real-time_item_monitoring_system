"""
跨平台 UI 管理器
統一管理字體、顏色、佈局，確保跨平台一致性
"""

import platform
import tkinter as tk
from tkinter import ttk
import logging
from typing import Dict, Any, Optional, Tuple
from .cross_platform_font_manager import get_font_manager
from .cross_platform_color_manager import get_color_manager


class CrossPlatformUIManager:
    """跨平台 UI 統一管理器"""
    
    def __init__(self, root_window: tk.Tk):
        self.root = root_window
        self.platform_name = platform.system().lower()
        
        # 初始化字體和顏色管理器
        self.font_manager = get_font_manager()
        self.color_manager = get_color_manager()
        
        # 初始化平台特定設定
        self._setup_platform_config()
        
        # 配置 ttk 樣式
        self._configure_ttk_styles()
        
        logging.info(f"✅ 跨平台 UI 管理器初始化完成 - 平台: {self.platform_name}")
    
    def _setup_platform_config(self):
        """設置平台特定配置"""
        
        if self.platform_name == 'windows':
            self.platform_config = {
                'window_padding': 8,
                'frame_padding': 6,
                'button_padding': (10, 4),
                'entry_padding': (8, 3),
                'label_padding': (4, 2),
                'default_relief': 'flat',
                'button_relief': 'raised',
                'entry_relief': 'sunken',
                'frame_relief': 'flat',
                'default_borderwidth': 1,
                'button_borderwidth': 1,
                'entry_borderwidth': 1,
                'frame_borderwidth': 0,
                'scrollbar_width': 16,
                'menu_tearoff': False,
                'use_native_dialogs': True
            }
            
        elif self.platform_name == 'darwin':  # macOS
            self.platform_config = {
                'window_padding': 12,
                'frame_padding': 10,
                'button_padding': (12, 6),
                'entry_padding': (10, 5),
                'label_padding': (6, 3),
                'default_relief': 'flat',
                'button_relief': 'flat',
                'entry_relief': 'solid',
                'frame_relief': 'flat',
                'default_borderwidth': 0,
                'button_borderwidth': 0,
                'entry_borderwidth': 1,
                'frame_borderwidth': 0,
                'scrollbar_width': 15,
                'menu_tearoff': False,
                'use_native_dialogs': True
            }
            
        else:  # Linux 及其他系統
            self.platform_config = {
                'window_padding': 10,
                'frame_padding': 8,
                'button_padding': (11, 5),
                'entry_padding': (9, 4),
                'label_padding': (5, 2),
                'default_relief': 'solid',
                'button_relief': 'raised',
                'entry_relief': 'sunken',
                'frame_relief': 'solid',
                'default_borderwidth': 1,
                'button_borderwidth': 1,
                'entry_borderwidth': 1,
                'frame_borderwidth': 1,
                'scrollbar_width': 14,
                'menu_tearoff': True,
                'use_native_dialogs': False
            }
    
    def _configure_ttk_styles(self):
        """配置 ttk 樣式"""
        self.style = ttk.Style()
        
        # 獲取顏色配置
        color_config = self.color_manager.get_ttk_style_config()
        
        # 應用樣式配置
        for style_name, config in color_config.items():
            if 'configure' in config:
                self.style.configure(f'CrossPlatform.{style_name}', **config['configure'])
            if 'map' in config:
                self.style.map(f'CrossPlatform.{style_name}', **config['map'])
    
    def create_button(self, parent: tk.Widget, text: str, command=None, 
                     button_type: str = 'primary', **kwargs) -> tk.Button:
        """創建跨平台一致的按鈕"""
        
        # 獲取安全文字
        safe_text = self.font_manager.get_safe_text(text)
        
        # 獲取字體
        font = self.font_manager.create_font_object('primary', 12, 'normal')
        
        # 根據按鈕類型設置顏色
        if button_type == 'primary':
            bg_color = self.color_manager.get_platform_color('primary_blue')
            fg_color = self.color_manager.get_contrast_color('primary_blue')
        elif button_type == 'success':
            bg_color = self.color_manager.get_platform_color('success_green')
            fg_color = self.color_manager.get_contrast_color('success_green')
        elif button_type == 'warning':
            bg_color = self.color_manager.get_platform_color('warning_orange')
            fg_color = self.color_manager.get_contrast_color('warning_orange')
        elif button_type == 'danger':
            bg_color = self.color_manager.get_platform_color('error_red')
            fg_color = self.color_manager.get_contrast_color('error_red')
        else:  # secondary
            bg_color = self.color_manager.get_platform_color('background_card')
            fg_color = self.color_manager.get_platform_color('text_primary')
        
        # 創建按鈕
        button = tk.Button(
            parent,
            text=safe_text,
            command=command,
            font=font,
            bg=bg_color,
            fg=fg_color,
            relief=self.platform_config['button_relief'],
            borderwidth=self.platform_config['button_borderwidth'],
            padx=self.platform_config['button_padding'][0],
            pady=self.platform_config['button_padding'][1],
            cursor='hand2',
            **kwargs
        )
        
        # 添加懸停效果
        self._add_hover_effect(button, bg_color)
        
        return button
    
    def create_entry(self, parent: tk.Widget, textvariable=None, **kwargs) -> tk.Entry:
        """創建跨平台一致的輸入框"""
        
        # 獲取字體
        font = self.font_manager.create_font_object('primary', 11, 'normal')
        
        # 創建輸入框
        entry = tk.Entry(
            parent,
            textvariable=textvariable,
            font=font,
            bg=self.color_manager.get_platform_color('background_card'),
            fg=self.color_manager.get_platform_color('text_primary'),
            insertbackground=self.color_manager.get_platform_color('text_primary'),
            selectbackground=self.color_manager.get_platform_color('primary_blue'),
            selectforeground=self.color_manager.get_contrast_color('primary_blue'),
            relief=self.platform_config['entry_relief'],
            borderwidth=self.platform_config['entry_borderwidth'],
            highlightcolor=self.color_manager.get_platform_color('primary_blue'),
            highlightthickness=1,
            **kwargs
        )
        
        return entry
    
    def create_label(self, parent: tk.Widget, text: str, label_type: str = 'body', **kwargs) -> tk.Label:
        """創建跨平台一致的標籤"""
        
        # 獲取安全文字
        safe_text = self.font_manager.get_safe_text(text)
        
        # 根據標籤類型設置字體
        if label_type == 'title':
            font = self.font_manager.create_font_object('primary', 16, 'bold')
            fg_color = self.color_manager.get_platform_color('text_primary')
        elif label_type == 'subtitle':
            font = self.font_manager.create_font_object('primary', 14, 'normal')
            fg_color = self.color_manager.get_platform_color('text_primary')
        elif label_type == 'caption':
            font = self.font_manager.create_font_object('primary', 10, 'normal')
            fg_color = self.color_manager.get_platform_color('text_secondary')
        elif label_type == 'mono':
            font = self.font_manager.create_font_object('mono', 11, 'normal')
            fg_color = self.color_manager.get_platform_color('text_primary')
        else:  # body
            font = self.font_manager.create_font_object('primary', 12, 'normal')
            fg_color = self.color_manager.get_platform_color('text_primary')
        
        # 創建標籤
        label = tk.Label(
            parent,
            text=safe_text,
            font=font,
            bg=self.color_manager.get_platform_color('background_card'),
            fg=fg_color,
            padx=self.platform_config['label_padding'][0],
            pady=self.platform_config['label_padding'][1],
            **kwargs
        )
        
        return label
    
    def create_frame(self, parent: tk.Widget, frame_type: str = 'card', **kwargs) -> tk.Frame:
        """創建跨平台一致的框架"""
        
        if frame_type == 'card':
            bg_color = self.color_manager.get_platform_color('background_card')
            relief = 'flat'
            borderwidth = 0
        elif frame_type == 'panel':
            bg_color = self.color_manager.get_platform_color('background_primary')
            relief = self.platform_config['frame_relief']
            borderwidth = self.platform_config['frame_borderwidth']
        else:  # transparent
            bg_color = self.color_manager.get_platform_color('background_primary')
            relief = 'flat'
            borderwidth = 0
        
        frame = tk.Frame(
            parent,
            bg=bg_color,
            relief=relief,
            borderwidth=borderwidth,
            padx=self.platform_config['frame_padding'],
            pady=self.platform_config['frame_padding'],
            **kwargs
        )
        
        return frame
    
    def create_listbox(self, parent: tk.Widget, **kwargs) -> tk.Listbox:
        """創建跨平台一致的列表框"""
        
        font = self.font_manager.create_font_object('primary', 11, 'normal')
        
        listbox = tk.Listbox(
            parent,
            font=font,
            bg=self.color_manager.get_platform_color('background_card'),
            fg=self.color_manager.get_platform_color('text_primary'),
            selectbackground=self.color_manager.get_platform_color('primary_blue'),
            selectforeground=self.color_manager.get_contrast_color('primary_blue'),
            relief=self.platform_config['entry_relief'],
            borderwidth=self.platform_config['entry_borderwidth'],
            highlightcolor=self.color_manager.get_platform_color('primary_blue'),
            **kwargs
        )
        
        return listbox
    
    def create_text(self, parent: tk.Widget, **kwargs) -> tk.Text:
        """創建跨平台一致的文字框"""
        
        font = self.font_manager.create_font_object('mono', 11, 'normal')
        
        text_widget = tk.Text(
            parent,
            font=font,
            bg=self.color_manager.get_platform_color('background_card'),
            fg=self.color_manager.get_platform_color('text_primary'),
            insertbackground=self.color_manager.get_platform_color('text_primary'),
            selectbackground=self.color_manager.get_platform_color('primary_blue'),
            selectforeground=self.color_manager.get_contrast_color('primary_blue'),
            relief=self.platform_config['entry_relief'],
            borderwidth=self.platform_config['entry_borderwidth'],
            wrap=tk.WORD,
            **kwargs
        )
        
        return text_widget
    
    def create_combobox(self, parent: tk.Widget, values=None, **kwargs) -> ttk.Combobox:
        """創建跨平台一致的下拉框"""
        
        combobox = ttk.Combobox(
            parent,
            style='CrossPlatform.TCombobox',
            values=values or [],
            state='readonly',
            **kwargs
        )
        
        return combobox
    
    def create_progressbar(self, parent: tk.Widget, **kwargs) -> ttk.Progressbar:
        """創建跨平台一致的進度條"""
        
        progressbar = ttk.Progressbar(
            parent,
            style='CrossPlatform.Horizontal.TProgressbar',
            **kwargs
        )
        
        return progressbar
    
    def _add_hover_effect(self, button: tk.Button, original_color: str):
        """為按鈕添加懸停效果"""
        
        hover_color = self.color_manager.adjust_color_for_platform(original_color, 'lighter')
        
        def on_enter(event):
            button.configure(bg=hover_color)
        
        def on_leave(event):
            button.configure(bg=original_color)
        
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)
    
    def configure_window(self, window: tk.Toplevel = None):
        """配置窗口的跨平台設定"""
        
        target_window = window or self.root
        
        # 設置窗口背景
        target_window.configure(bg=self.color_manager.get_platform_color('background_primary'))
        
        # 平台特定設定
        if self.platform_name == 'darwin':
            # macOS 特定設定
            try:
                target_window.tk.call('::tk::unsupported::MacWindowStyle', 'style', 
                                     target_window._w, 'document', 'closeBox collapseBox resizable')
            except:
                pass
        
        elif self.platform_name == 'windows':
            # Windows 特定設定
            try:
                target_window.wm_attributes('-alpha', 0.99)  # 微妙的透明度
            except:
                pass
    
    def apply_theme_to_widget(self, widget: tk.Widget, widget_type: str):
        """將主題應用到特定 widget"""
        self.color_manager.apply_platform_style_to_widget(widget, widget_type)
    
    def get_platform_config(self, config_name: str) -> Any:
        """獲取平台特定配置"""
        return self.platform_config.get(config_name)
    
    def create_status_display(self, parent: tk.Widget, status_type: str = 'info') -> tk.Label:
        """創建狀態顯示標籤"""
        
        color_map = {
            'info': 'primary_blue',
            'success': 'success_green',
            'warning': 'warning_orange',
            'error': 'error_red'
        }
        
        color = self.color_manager.get_platform_color(color_map.get(status_type, 'primary_blue'))
        font = self.font_manager.create_font_object('mono', 14, 'bold')
        
        label = tk.Label(
            parent,
            font=font,
            fg=color,
            bg=self.color_manager.get_platform_color('background_card')
        )
        
        return label
    
    def log_platform_info(self):
        """記錄平台資訊"""
        logging.info(f"=== 跨平台 UI 管理器資訊 ===")
        logging.info(f"平台: {self.platform_name}")
        
        # 記錄字體資訊
        self.font_manager.log_font_info()
        
        # 記錄顏色資訊
        self.color_manager.log_color_info()
        
        # 記錄平台配置
        logging.info("=== 平台配置 ===")
        for key, value in self.platform_config.items():
            logging.info(f"{key}: {value}")


# 全域 UI 管理器實例
_ui_manager = None

def get_ui_manager(root_window: tk.Tk = None) -> CrossPlatformUIManager:
    """獲取全域 UI 管理器實例"""
    global _ui_manager
    if _ui_manager is None and root_window is not None:
        _ui_manager = CrossPlatformUIManager(root_window)
    return _ui_manager

def initialize_ui_manager(root_window: tk.Tk) -> CrossPlatformUIManager:
    """初始化 UI 管理器"""
    global _ui_manager
    _ui_manager = CrossPlatformUIManager(root_window)
    return _ui_manager
