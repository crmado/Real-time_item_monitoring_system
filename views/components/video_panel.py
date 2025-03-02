"""
視訊顯示面板組件
負責顯示視訊畫面和 ROI 線
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import logging


class VideoPanel(ttk.Frame):
    """視訊顯示面板類別"""
    # ==========================================================================
    # 第一部分：初始化
    # ==========================================================================
    def __init__(self, parent, **kwargs):
        """
        初始化視訊面板

        Args:
            parent: 父級視窗
            **kwargs: 其他參數
        """
        super().__init__(parent, style='Video.TFrame', **kwargs)
        self.parent = parent
        self.callbacks = {}

        # 設定預設顯示大小
        self.display_width = 640
        self.display_height = 480

        self.create_widgets()
        self.bind_events()

    # ==========================================================================
    # 第二部分：容器初始化和視覺樣式
    # ==========================================================================
    def create_widgets(self):
        """創建視訊面板組件"""
        # 建立固定大小的容器
        self.image_container = ttk.Frame(
            self,
            width=self.display_width,
            height=self.display_height,
            style='Video.TFrame'
        )
        self.image_container.grid(row=0, column=0, padx=2, pady=2)
        self.image_container.grid_propagate(False)

        self.image_container.configure(borderwidth=2, relief='solid')

        # 影像標籤
        self.image_label = ttk.Label(
            self.image_container,
            style='Video.TLabel',
            text="Please select a camera"
        )
        self.image_label.grid(row=0, column=0, sticky=f"{tk.N} {tk.S} {tk.E} {tk.W}")

    def bind_events(self):
        """綁定滑鼠事件"""
        self.image_label.bind('<Button-1>', self._on_mouse_down)
        self.image_label.bind('<B1-Motion>', self._on_mouse_drag)
        self.image_label.bind('<ButtonRelease-1>', self._on_mouse_up)

    def _on_mouse_down(self, event):
        """
        滑鼠按下事件處理

        Args:
            event: 事件物件
        """
        if 'roi_drag_start' in self.callbacks:
            self.callbacks['roi_drag_start'](event)

    def _on_mouse_drag(self, event):
        """
        滑鼠拖動事件處理

        Args:
            event: 事件物件
        """
        if 'roi_drag' in self.callbacks:
            self.callbacks['roi_drag'](event)

    def _on_mouse_up(self, event):
        """
        滑鼠釋放事件處理

        Args:
            event: 事件物件
        """
        if 'roi_drag_end' in self.callbacks:
            self.callbacks['roi_drag_end'](event)

    def update_image(self, frame):
        """
        更新顯示的影像

        Args:
            frame: OpenCV 影像幀
        """
        try:
            # 轉換 OpenCV 的 BGR 格式為 RGB 格式
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 調整影像大小，保持比例
            frame_height, frame_width = frame.shape[:2]
            aspect_ratio = frame_width / frame_height

            if self.display_width / self.display_height > aspect_ratio:
                new_height = self.display_height
                new_width = int(self.display_height * aspect_ratio)
            else:
                new_width = self.display_width
                new_height = int(self.display_width / aspect_ratio)

            # 調整影像大小
            img = Image.fromarray(rgb_frame)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 轉換為 Tkinter 可用的格式
            img_tk = ImageTk.PhotoImage(image=img)

            # 更新顯示
            self.image_label.configure(image=img_tk)
            self.image_label.image = img_tk

        except Exception as e:
            logging.error(f"An error occurred while updating the image display：{str(e)}")

    def set_callback(self, event_name, callback):
        """
        設置事件回調函數

        Args:
            event_name: 事件名稱
            callback: 回調函數
        """
        self.callbacks[event_name] = callback

    def get_display_size(self):
        """
        獲取顯示區域大小

        Returns:
            tuple: (寬度, 高度)
        """
        return self.display_width, self.display_height