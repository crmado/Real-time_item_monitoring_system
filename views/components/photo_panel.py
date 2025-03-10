"""
拍照面板組件
負責拍照和顯示預覽
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from PIL.Image import Resampling 
import cv2
import logging

from utils.language import get_text


class PhotoPanel(ttk.Frame):
    """拍照面板類別"""

    #==========================================================================
    # 第一部分：基本屬性和初始化
    #==========================================================================
    def __init__(self, parent, **kwargs):
        """
        初始化拍照面板

        Args:
            parent: 父級視窗
            **kwargs: 其他參數
        """
        super().__init__(parent, **kwargs)
        self.preview_img = None
        self.parent = parent
        self.callbacks = {}

        # 設定預設顯示大小
        self.display_width = 640
        self.display_height = 480

        # UI元件
        self.create_widgets()

    # ==========================================================================
    # 第二部分：UI元件創建
    # ==========================================================================
    def create_widgets(self):
        """創建拍照面板組件"""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 使用網格布局代替包裝布局
        main_frame.columnconfigure(0, weight=1)  # 設定列的權重
        main_frame.rowconfigure(0, weight=3)  # 相機預覽區域佔比較大
        main_frame.rowconfigure(1, weight=0)  # 按鈕區域不需要擴展
        main_frame.rowconfigure(2, weight=2)  # 已拍攝照片區域佔比適中
        main_frame.rowconfigure(3, weight=0)  # 進度條區域不需要擴展
        main_frame.rowconfigure(4, weight=0)  # 狀態文字區域不需要擴展

        # 相機預覽區域
        self.camera_frame = ttk.LabelFrame(main_frame, text=get_text("camera_preview", "相機即時預覽"))
        self.camera_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.camera_display = ttk.Label(self.camera_frame, anchor=tk.CENTER)
        self.camera_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.camera_display.configure(background='#f0f0f0')

        # 添加高度限制，防止過度擴展
        self.camera_frame.configure(height=self.display_height)

        # 拍照按鈕
        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.capture_btn = ttk.Button(
            self.button_frame,
            text=get_text("capture_photo", "拍攝照片"),
            style='Accent.TButton',
            command=self._on_capture
        )
        self.capture_btn.pack(side=tk.LEFT, padx=5)

        self.inspect_btn = ttk.Button(
            self.button_frame,
            text=get_text("analyze_photo", "分析照片"),
            style='Accent.TButton',
            command=self._on_analyze,
            state=tk.DISABLED
        )
        self.inspect_btn.pack(side=tk.LEFT, padx=5)

        # 預覽區域
        self.preview_frame = ttk.LabelFrame(main_frame, text=get_text("captured_photo", "已拍攝照片"))
        self.preview_frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

        self.preview_display = ttk.Label(self.preview_frame, anchor=tk.CENTER)
        self.preview_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.preview_display.configure(background='#f0f0f0')

        # 同樣添加高度限制
        self.preview_frame.configure(height=300)

        # 添加進度條
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")

        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, expand=True)
        self.progress_bar.pack_forget()  # 初始時隱藏

        # 狀態文字
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.grid(row=4, column=0, padx=5, pady=5, sticky="ew")

    #==========================================================================
    # 第三部分：事件處理
    #==========================================================================
    def _on_capture(self):
        """拍照按鈕點擊事件"""
        if 'capture_photo' in self.callbacks and self.callbacks['capture_photo']:
            self.callbacks['capture_photo']()

    def _on_analyze(self):
        """分析按鈕點擊事件"""
        if 'analyze_photo' in self.callbacks and self.callbacks['analyze_photo']:
            self.callbacks['analyze_photo']()

    # ==========================================================================
    # 第四部分：UI更新方法
    # ==========================================================================
    def update_camera_preview(self, frame):
        """
        更新相機預覽圖像

        Args:
            frame: OpenCV 圖像幀
        """
        try:
            if frame is None:
                return

            # 轉換 OpenCV 的 BGR 格式為 RGB 格式
            if len(frame.shape) == 3:  # 彩色圖像
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:  # 灰度圖像
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

            # 轉換為 Tkinter 可用的格式
            img = Image.fromarray(rgb_frame)

            # 使用固定的顯示大小，避免過度擴展
            max_width = self.display_width
            max_height = int(self.display_height * 0.7)  # 相機預覽使用70%的高度

            # 保持原始比例縮放
            aspect_ratio = img.width / img.height
            if max_width / max_height > aspect_ratio:
                new_width = int(max_height * aspect_ratio)
                new_height = max_height
            else:
                new_width = max_width
                new_height = int(max_width / aspect_ratio)

            # 調整圖像大小
            img = img.resize((new_width, new_height), Resampling.LANCZOS)

            # 轉換為 Tkinter 可用的格式
            self.camera_img = ImageTk.PhotoImage(image=img)

            # 更新顯示
            self.camera_display.configure(image=self.camera_img)

            # 強制更新布局
            self.update_idletasks()

        except Exception as e:
            logging.error(f"更新相機預覽時發生錯誤：{str(e)}")

    def update_photo_preview(self, frame):
        """
        更新照片預覽圖像

        Args:
            frame: OpenCV 圖像幀
        """
        try:
            if frame is None:
                return

            # 轉換 OpenCV 的 BGR 格式為 RGB 格式
            if len(frame.shape) == 3:  # 彩色圖像
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:  # 灰度圖像
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

            # 轉換為 Tkinter 可用的格式
            img = Image.fromarray(rgb_frame)

            # 計算合適的顯示大小
            width, height = self.preview_display.winfo_width(), self.preview_display.winfo_height()
            if width <= 1 or height <= 1:  # 如果控件尚未完全初始化
                width, height = 640, 480

            # 保持原始比例縮放
            aspect_ratio = img.width / img.height
            if width / height > aspect_ratio:
                new_width = int(height * aspect_ratio)
                new_height = height
            else:
                new_width = width
                new_height = int(width / aspect_ratio)

            # 調整圖像大小
            img = img.resize((new_width, new_height), Resampling.LANCZOS)

            # 轉換為 Tkinter 可用的格式
            self.preview_img = ImageTk.PhotoImage(image=img)

            # 更新顯示
            self.preview_display.configure(image=self.preview_img)

            # 啟用分析按鈕
            self.inspect_btn.configure(state=tk.NORMAL)

        except Exception as e:
            logging.error(f"更新照片預覽時發生錯誤：{str(e)}")

    def show_loading(self):
        """顯示載入進度條"""
        self.progress_bar.pack(fill=tk.X, expand=True)
        self.progress_bar.start(10)
        self.capture_btn.configure(state=tk.DISABLED)
        self.inspect_btn.configure(state=tk.DISABLED)
        self.status_label.configure(text=get_text("analyzing", "正在分析照片..."))

    def hide_loading(self):
        """隱藏載入進度條"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.capture_btn.configure(state=tk.NORMAL)
        self.inspect_btn.configure(state=tk.NORMAL)
        self.status_label.configure(text=get_text("analysis_completed", "分析完成"))

    def set_status(self, text):
        """設置狀態文字"""
        self.status_label.configure(text=text)

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