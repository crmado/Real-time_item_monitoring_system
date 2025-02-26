"""
控制面板組件
包含視訊來源選擇和控制按鈕
"""

import tkinter as tk
from tkinter import ttk
import logging

from utils.language import get_text


class ControlPanel(ttk.Frame):
    """控制面板類別"""

    def __init__(self, parent, **kwargs):
        """
        初始化控制面板

        Args:
            parent: 父級視窗
            **kwargs: 其他參數
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.callbacks = {}
        self.create_widgets()

    def create_widgets(self):
        """創建控制面板組件"""
        # 視訊來源選擇
        ttk.Label(self, text=get_text("select_source", "選擇視訊來源：")).grid(row=0, column=0, padx=5)

        self.camera_combo = ttk.Combobox(self, width=30)
        self.camera_combo.grid(row=0, column=1, padx=5)

        # 測試按鈕
        self.test_button = ttk.Button(
            self,
            text=get_text("test_button", "測試鏡頭"),
            style='Accent.TButton'
        )
        self.test_button.grid(row=0, column=2, padx=5)

        # 開始/停止按鈕
        self.start_button = ttk.Button(
            self,
            text=get_text("start_button", "開始監測"),
            style='Accent.TButton'
        )
        self.start_button.grid(row=0, column=3, padx=5)

    def set_camera_sources(self, sources):
        """
        設置可用的視訊來源

        Args:
            sources: 視訊來源列表
        """
        self.camera_combo['values'] = sources

    def get_selected_source(self):
        """
        獲取選擇的視訊來源

        Returns:
            str: 選擇的視訊來源名稱
        """
        return self.camera_combo.get()

    def set_callback(self, button_name, callback):
        """
        設置按鈕回調函數

        Args:
            button_name: 按鈕名稱
            callback: 回調函數
        """
        if button_name == 'test':
            self.test_button.configure(command=callback)
        elif button_name == 'start':
            self.start_button.configure(command=callback)
        self.callbacks[button_name] = callback

    def update_start_button_text(self, is_monitoring):
        """
        更新開始按鈕文字

        Args:
            is_monitoring: 是否正在監測
        """
        self.start_button.configure(
            text=get_text("stop_button", "停止監測") if is_monitoring else get_text("start_button", "開始監測")
        )

    def update_test_button_text(self, is_testing):
        """
        更新測試按鈕文字

        Args:
            is_testing: 是否正在測試
        """
        self.test_button.configure(
            text=get_text("stop_test", "停止測試") if is_testing else get_text("test_button", "測試鏡頭")
        )

    def update_language(self):
        """更新組件語言"""
        # 更新標籤文字
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Label):
                if "選擇視訊來源" in widget.cget('text') or "Select Video Source" in widget.cget('text'):
                    widget.configure(text=get_text("select_source", "選擇視訊來源："))

        # 更新按鈕文字
        if "Stop" in self.test_button.cget('text') or "停止" in self.test_button.cget('text'):
            self.test_button.configure(text=get_text("stop_test", "停止測試"))
        else:
            self.test_button.configure(text=get_text("test_button", "測試鏡頭"))

        if "Stop" in self.start_button.cget('text') or "停止" in self.start_button.cget('text'):
            self.start_button.configure(text=get_text("stop_button", "停止監測"))
        else:
            self.start_button.configure(text=get_text("start_button", "開始監測"))