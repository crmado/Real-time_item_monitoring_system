"""
設定面板組件
包含計數顯示和參數設定
"""

import tkinter as tk
from tkinter import ttk
import logging

from utils.language import get_text


class SettingsPanel(ttk.Frame):
    """
    /// 設定面板類別
    /// 功能結構：
    /// 第一部分：基本屬性和初始化
    /// 第二部分：UI元件創建
    /// 第三部分：事件處理
    /// 第四部分：數據管理
    /// 第五部分：工具方法
    """

    #==========================================================================
    # 第一部分：基本屬性和初始化
    #==========================================================================
    def __init__(self, parent, config_manager, **kwargs):
        """
        初始化設定面板

        Args:
            parent: 父級視窗
            config_manager: 配置管理器實例
            **kwargs: 其他參數
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.config_manager = config_manager
        self.callbacks = {
            'settings_applied': None
        }

        # 載入配置
        self.load_config()

        # 創建UI元件
        self.create_widgets()

    def load_config(self):
        """載入配置"""
        self.target_count = self.config_manager.get('detection.target_count', 1000)
        self.buffer_point = self.config_manager.get('detection.buffer_point', 950)

    #==========================================================================
    # 第二部分：UI元件創建
    #==========================================================================
    def create_widgets(self):
        """創建設定面板組件"""
        # 當前計數顯示
        self.create_counter_section()

        # 預計數量設定
        self.create_target_section()

        # 緩衝點設定
        self.create_buffer_section()

        # 設定按鈕
        self.create_settings_button()

    def create_counter_section(self):
        """創建計數器區段"""
        count_frame = ttk.Frame(self)
        count_frame.grid(row=0, column=0, pady=5, sticky=tk.EW)

        ttk.Label(
            count_frame,
            text=get_text("current_count", "目前數量："),
            style='Counter.TLabel'
        ).grid(row=0, column=0)

        self.count_label = ttk.Label(
            count_frame,
            text="0",
            style='CounterNum.TLabel'
        )
        self.count_label.grid(row=0, column=1)

    def create_target_section(self):
        """創建目標數量設定區段"""
        target_frame = ttk.Frame(self)
        target_frame.grid(row=1, column=0, pady=5, sticky=tk.EW)

        ttk.Label(target_frame, text=get_text("target_count", "預計數量：")).grid(row=0, column=0)

        self.target_entry = ttk.Entry(target_frame, width=10)
        self.target_entry.grid(row=0, column=1, padx=5)
        self.target_entry.insert(0, str(self.target_count))

    def create_buffer_section(self):
        """創建緩衝點設定區段"""
        buffer_frame = ttk.Frame(self)
        buffer_frame.grid(row=2, column=0, pady=5, sticky=tk.EW)

        ttk.Label(buffer_frame, text=get_text("buffer_point", "緩衝點：")).grid(row=0, column=0)

        self.buffer_entry = ttk.Entry(buffer_frame, width=10)
        self.buffer_entry.grid(row=0, column=1, padx=5)
        self.buffer_entry.insert(0, str(self.buffer_point))

    def create_settings_button(self):
        """創建設定按鈕"""
        self.apply_settings_button = ttk.Button(
            self,
            text=get_text("apply_settings", "套用設定"),
            style='Accent.TButton',
            command=self._on_apply_settings
        )
        self.apply_settings_button.grid(row=4, column=0, pady=10)

    #==========================================================================
    # 第三部分：事件處理
    #==========================================================================
    def _on_apply_settings(self):
        """當點擊套用設定按鈕時處理"""
        if self.callbacks['settings_applied']:
            self.callbacks['settings_applied']()

    #==========================================================================
    # 第四部分：數據管理
    #==========================================================================
    def update_count(self, count):
        """
        更新計數顯示

        Args:
            count: 當前計數
        """
        self.count_label.configure(text=str(count))

    def get_settings(self):
        """
        獲取設定值

        Returns:
            dict: 設定值字典
        """
        try:
            target_count = int(self.target_entry.get())
            buffer_point = int(self.buffer_entry.get())

            # 驗證設定
            if buffer_point >= target_count:
                logging.error(get_text("error_buffer_target", "緩衝點必須小於預計數量"))
                return None

            if buffer_point < 0 or target_count < 0:
                logging.error(get_text("error_negative", "設定值必須為正數"))
                return None

            # 原本返回的是帶前綴的鍵名，改為直接返回鍵名
            return {
                'target_count': target_count,
                'buffer_point': buffer_point
                # 使用一致的格式，不使用 'detection.target_count' 格式
            }
        except ValueError:
            logging.error(get_text("error_invalid_number", "設定值必須為整數"))
            return None

    #==========================================================================
    # 第五部分：工具方法
    #==========================================================================
    def set_callback(self, event_name, callback):
        """
        設置回調函數

        Args:
            event_name: 事件名稱
            callback: 回調函數
        """
        self.callbacks[event_name] = callback

    def update_language(self):
        """更新組件語言"""
        # 更新文字標籤
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label) and not child == self.count_label:
                        if child.cget('text') == "預計數量：" or child.cget('text') == "Estimated Quantity:":
                            child.configure(text=get_text("target_count", "預計數量："))
                        elif child.cget('text') == "緩衝點：" or child.cget('text') == "Buffer Point:":
                            child.configure(text=get_text("buffer_point", "緩衝點："))
                        elif child.cget('text') == "目前數量：" or child.cget('text') == "Current Count:":
                            child.configure(text=get_text("current_count", "目前數量："))

        # 更新按鈕文字
        self.apply_settings_button.configure(text=get_text("apply_settings", "套用設定"))