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

    # ==========================================================================
    # 第一部分：基本屬性和初始化
    # ==========================================================================
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

    # ==========================================================================
    # 第二部分：UI元件創建
    # ==========================================================================
    def create_widgets(self):
        """創建控制面板組件"""
        # 視訊來源選擇
        ttk.Label(self, text=get_text("select_source", "選擇視訊來源：")).grid(row=0, column=0, padx=5)

        self.camera_combo = ttk.Combobox(self, width=30)
        self.camera_combo.grid(row=0, column=1, padx=5)

        # 綁定選擇事件，當選擇變更時自動測試相機
        self.camera_combo.bind("<<ComboboxSelected>>", self._on_camera_selected)

        # # 測試按鈕
        # self.test_button = ttk.Button(
        #     self,
        #     text=get_text("test_button", "測試鏡頭"),
        #     style='Accent.TButton'
        # )
        # self.test_button.grid(row=0, column=2, padx=5)

        # 開始/停止按鈕
        self.start_button = ttk.Button(
            self,
            text=get_text("start_button", "開始監測"),
            style='Accent.TButton'
        )
        self.start_button.grid(row=0, column=2, padx=5)

        # 添加模式切換按鈕
        self.mode_button = ttk.Button(
            self,
            text=get_text("mode_switch", "切換到拍照模式"),
            command=self._on_mode_switch
        )
        self.mode_button.grid(row=0, column=3, padx=5)

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
        if button_name == 'start':
            self.start_button.configure(command=callback)
        # if button_name == 'test':
        #     self.test_button.configure(command=callback)
        # elif button_name == 'start':
        #     self.start_button.configure(command=callback)
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
        # 測試按鈕已移除，此方法保留為空
        pass

    def update_language(self):
        """更新組件語言"""
        # 更新標籤文字
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Label):
                if "選擇視訊來源" in widget.cget('text') or "Select Video Source" in widget.cget('text'):
                    widget.configure(text=get_text("select_source", "選擇視訊來源："))

        # 更新按鈕文字
        # if "Stop" in self.test_button.cget('text') or "停止" in self.test_button.cget('text'):
        #     self.test_button.configure(text=get_text("stop_test", "停止測試"))
        # else:
        #     self.test_button.configure(text=get_text("test_button", "測試鏡頭"))

        if "Stop" in self.start_button.cget('text') or "停止" in self.start_button.cget('text'):
            self.start_button.configure(text=get_text("stop_button", "停止監測"))
        else:
            self.start_button.configure(text=get_text("start_button", "開始監測"))

    def _on_camera_selected(self, event):
        """當選擇攝影機時自動執行測試"""
        selected_source = self.get_selected_source()
        if selected_source and 'test' in self.callbacks:
            self.callbacks['test']()  # 呼叫測試相機回調

    def select_source(self, source):
        """
        選擇指定的視訊來源

        Args:
            source: 視訊來源名稱
        """
        if source in self.camera_combo['values']:
            self.camera_combo.set(source)
            # 如果已經設定了選擇變更回調，呼叫它
            if 'source_changed' in self.callbacks and self.callbacks['source_changed']:
                self.callbacks['source_changed'](source)

    # ==========================================================================
    # 第三部分：事件處理
    # ==========================================================================

    def _on_mode_switch(self):
        """當點擊模式切換按鈕時處理"""
        if 'mode_switch' in self.callbacks and self.callbacks['mode_switch']:
            self.callbacks['mode_switch']()

    def update_mode_button_text(self, is_photo_mode):
        """
        更新模式按鈕文字

        Args:
            is_photo_mode: 是否為拍照模式
        """
        self.mode_button.configure(
            text=get_text("switch_to_monitor", "切換到監測模式") if is_photo_mode
            else get_text("switch_to_photo", "切換到拍照模式")
        )