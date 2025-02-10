"""
主視窗
整合所有UI組件
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
import datetime

from .components.control_panel import ControlPanel
from .components.video_panel import VideoPanel
from .components.settings_panel import SettingsPanel


class MainWindow:
    """主視窗類別"""

    def __init__(self, root):
        """
        初始化主視窗

        Args:
            root: Tkinter root 物件
        """
        self.root = root
        self.root.title("物件監測系統")
        self.setup_window()
        self.create_components()
        self.setup_layout()
        self.start_time_update()

    def setup_window(self):
        """設定視窗基本屬性"""
        self.root.minsize(800, 600)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

    def create_components(self):
        """創建所有UI組件"""
        # 主框架
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 控制面板
        self.control_panel = ControlPanel(self.main_frame)

        # 視訊面板
        self.video_panel = VideoPanel(self.main_frame)

        # 設定面板
        self.settings_panel = SettingsPanel(self.main_frame)

        # 日誌區域
        self.create_log_area()

        # 資訊區域
        self.create_info_area()

    def create_log_area(self):
        """創建日誌顯示區域"""
        log_frame = ttk.Frame(self.main_frame)
        log_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))

        ttk.Label(log_frame, text="System log：").grid(row=0, column=0, sticky=tk.W)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=70,
            height=8,
            wrap=tk.WORD
        )
        self.log_text.grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))

    def create_info_area(self):
        """創建資訊顯示區域"""
        info_frame = ttk.Frame(self.main_frame)
        info_frame.grid(row=2, column=1, padx=30, pady=10, sticky=(tk.E, tk.S))

        ttk.Label(info_frame, text="Current time：").grid(row=0, column=0, sticky=tk.W)
        self.time_label = ttk.Label(info_frame, text="")
        self.time_label.grid(row=1, column=0, sticky=tk.W)

    def setup_layout(self):
        """設置組件布局"""
        self.control_panel.grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.W)
        self.video_panel.grid(row=1, column=0, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.settings_panel.grid(row=1, column=1, padx=10, sticky=tk.N)

    def start_time_update(self):
        """開始更新時間顯示"""

        def update_time():
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.configure(text=current_time)
            self.root.after(1000, update_time)

        update_time()

    def log_message(self, message):
        """
        記錄訊息到日誌區域

        Args:
            message: 要記錄的訊息
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"

            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)

            logging.info(message)
        except Exception as e:
            print(f"記錄訊息時發生錯誤：{str(e)}")

    def get_components(self):
        """
        獲取所有UI組件

        Returns:
            dict: UI組件字典
        """
        return {
            'control_panel': self.control_panel,
            'video_panel': self.video_panel,
            'settings_panel': self.settings_panel
        }