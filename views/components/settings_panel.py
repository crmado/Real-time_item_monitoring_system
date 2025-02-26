"""
設定面板組件
包含計數顯示和參數設定
"""

import tkinter as tk
from tkinter import ttk
import logging

from utils.language import get_text, change_language, get_available_languages, get_language_name


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
        self.callbacks = {
            'settings_applied': None,
            'language_changed': None
        }
        self.create_widgets()

    def create_widgets(self):
        """創建設定面板組件"""
        # 當前計數顯示
        self.create_counter_section()

        # 預計數量設定
        self.create_target_section()

        # 緩衝點設定
        self.create_buffer_section()

        # 語言選擇區段
        self.create_language_section()

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
        self.target_entry.insert(0, "1000")  # 預設值

    def create_buffer_section(self):
        """創建緩衝點設定區段"""
        buffer_frame = ttk.Frame(self)
        buffer_frame.grid(row=2, column=0, pady=5, sticky=tk.EW)

        ttk.Label(buffer_frame, text=get_text("buffer_point", "緩衝點：")).grid(row=0, column=0)

        self.buffer_entry = ttk.Entry(buffer_frame, width=10)
        self.buffer_entry.grid(row=0, column=1, padx=5)
        self.buffer_entry.insert(0, "950")  # 預設值

    def create_language_section(self):
        """創建語言選擇區段"""
        language_frame = ttk.Frame(self)
        language_frame.grid(row=3, column=0, pady=5, sticky=tk.EW)

        ttk.Label(language_frame, text=get_text("language", "語言：")).grid(row=0, column=0)

        # 語言選擇下拉選單
        self.language_var = tk.StringVar()
        self.language_combo = ttk.Combobox(
            language_frame,
            width=15,
            textvariable=self.language_var,
            state="readonly"
        )

        # 獲取可用語言
        languages = get_available_languages()
        language_display = [f"{get_language_name(lang)}" for lang in languages]

        self.language_combo['values'] = language_display
        self.language_combo.grid(row=0, column=1, padx=5)

        # 找出預設語言(zh_TW)的索引並設定
        default_index = languages.index('zh_TW')
        self.language_combo.current(default_index)

        # 綁定選擇事件
        self.language_combo.bind("<<ComboboxSelected>>", self._on_language_change)

    def _on_language_change(self, event):
        """
        語言變更處理函數

        Args:
            event: 事件物件
        """
        selected_index = self.language_combo.current()
        if selected_index >= 0:
            languages = get_available_languages()
            selected_language = languages[selected_index]

            # 變更語言
            if change_language(selected_language):
                # 通知UI需要更新
                if self.callbacks['language_changed']:
                    self.callbacks['language_changed'](selected_language)

    def create_settings_button(self):
        """創建設定按鈕"""
        self.apply_settings_button = ttk.Button(
            self,
            text=get_text("apply_settings", "套用設定"),
            style='Accent.TButton'
        )
        self.apply_settings_button.grid(row=4, column=0, pady=10)

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
            logging.error(get_text("error_invalid_number", "設定值必須為整數"))
            return None

    def set_callback(self, event_name, callback):
        """
        設置回調函數

        Args:
            event_name: 事件名稱
            callback: 回調函數
        """
        if event_name == 'settings_applied':
            self.apply_settings_button.configure(command=callback)
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
                        elif child.cget('text') == "語言：" or child.cget('text') == "Language:":
                            child.configure(text=get_text("language", "語言："))

        # 更新按鈕文字
        self.apply_settings_button.configure(text=get_text("apply_settings", "套用設定"))