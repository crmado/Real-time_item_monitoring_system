"""
設定面板組件
包含計數顯示和參數設定
"""

import tkinter as tk
from tkinter import ttk
import logging


class SettingsPanel(ttk.Frame):
    """設定面板類別"""

    def __init__(self, parent, **kwargs):
        """
        初始化設定面板

        Args:
            parent: 父級視窗
            **kwargs: 其他參數
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.callbacks = {}
        self.create_widgets()

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
            text="Current count：",
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

        ttk.Label(target_frame, text="Estimated quantity：").grid(row=0, column=0)

        self.target_entry = ttk.Entry(target_frame, width=10)
        self.target_entry.grid(row=0, column=1, padx=5)
        self.target_entry.insert(0, "1000")  # 預設值

    def create_buffer_section(self):
        """創建緩衝點設定區段"""
        buffer_frame = ttk.Frame(self)
        buffer_frame.grid(row=2, column=0, pady=5, sticky=tk.EW)

        ttk.Label(buffer_frame, text="Buffer Point：").grid(row=0, column=0)

        self.buffer_entry = ttk.Entry(buffer_frame, width=10)
        self.buffer_entry.grid(row=0, column=1, padx=5)
        self.buffer_entry.insert(0, "950")  # 預設值

    def create_settings_button(self):
        """創建設定按鈕"""
        self.apply_settings_button = ttk.Button(
            self,
            text="Application Settings",
            style='Accent.TButton'
        )
        self.apply_settings_button.grid(row=3, column=0, pady=10)

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

            return {
                'target_count': target_count,
                'buffer_point': buffer_point
            }
        except ValueError:
            logging.error("The setting value must be an integer")
            return None

    def set_callback(self, callback):
        """
        設置設定按鈕回調函數

        Args:
            callback: 回調函數
        """
        self.apply_settings_button.configure(command=callback)