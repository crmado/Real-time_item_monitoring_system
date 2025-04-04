"""
拍照面板組件
負責拍照和顯示預覽
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk # type: ignore
from PIL.Image import Resampling  # type: ignore
import cv2 # type: ignore
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

        # 設定固定顯示大小
        self.display_width = 800
        self.display_height = 600
        self.last_camera_frame = None
        self.last_photo_frame = None

        # UI元件
        self.create_widgets()

    # ==========================================================================
    # 第二部分：UI元件創建
    # ==========================================================================
    def create_widgets(self):
        """創建拍照面板組件"""
        main_frame = ttk.Frame(self, style='Video.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # 使用網格布局代替包裝布局
        main_frame.columnconfigure(0, weight=1)  # 設定列的權重
        main_frame.rowconfigure(0, weight=3)  # 相機預覽區域佔比較大
        main_frame.rowconfigure(1, weight=0)  # 按鈕區域不需要擴展
        main_frame.rowconfigure(2, weight=2)  # 已拍攝照片區域佔比適中
        main_frame.rowconfigure(3, weight=0)  # 進度條區域不需要擴展
        main_frame.rowconfigure(4, weight=0)  # 狀態文字區域不需要擴展

        # 相機預覽區域
        self.camera_frame = ttk.Frame(main_frame, style='VideoContainer.TFrame', width=self.display_width, height=int(self.display_height * 0.6))
        self.camera_frame.grid(row=0, column=0, sticky="nsew")
        self.camera_frame.grid_propagate(False)  # 防止容器自動調整大小

        self.camera_display = ttk.Label(self.camera_frame, style='Video.TLabel')
        self.camera_display.pack(fill=tk.BOTH, expand=True)

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
        self.preview_frame = ttk.Frame(main_frame, style='VideoContainer.TFrame', width=self.display_width, height=int(self.display_height * 0.4))
        self.preview_frame.grid(row=2, column=0, sticky="nsew")
        self.preview_frame.grid_propagate(False)  # 防止容器自動調整大小

        self.preview_display = ttk.Label(self.preview_frame, style='Video.TLabel')
        self.preview_display.pack(fill=tk.BOTH, expand=True)

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
    def resize(self, event=None):
        """
        處理視窗大小變化
        
        Args:
            event: 事件對象
        """
        # 當視窗大小變化時，更新顯示尺寸
        if hasattr(self, 'last_camera_frame') and self.last_camera_frame is not None:
            self.update_camera_preview(self.last_camera_frame)
        if hasattr(self, 'last_photo_frame') and self.last_photo_frame is not None:
            self.update_photo_preview(self.last_photo_frame)
            
    def update_camera_preview(self, frame):
        """
        更新相機預覽圖像

        Args:
            frame: OpenCV 圖像幀
        """
        try:
            if frame is None:
                return
                
            # 保存最後一幀，用於窗口大小變化時重新顯示
            self.last_camera_frame = frame.copy()

            # 轉換 OpenCV 的 BGR 格式為 RGB 格式
            if len(frame.shape) == 3:  # 彩色圖像
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:  # 灰度圖像
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

            # 轉換為 Tkinter 可用的格式
            img = Image.fromarray(rgb_frame)

            # 計算適合的顯示大小
            camera_width = self.camera_frame.winfo_width()
            camera_height = self.camera_frame.winfo_height()
            
            # 如果容器尚未完全初始化，使用默認尺寸
            if camera_width <= 1 or camera_height <= 1:
                camera_width = self.display_width
                camera_height = int(self.display_height * 0.6)

            # 保持原始比例縮放
            aspect_ratio = img.width / img.height
            if camera_width / camera_height > aspect_ratio:
                new_width = int(camera_height * aspect_ratio)
                new_height = camera_height
            else:
                new_width = camera_width
                new_height = int(camera_width / aspect_ratio)

            # 調整圖像大小
            img = img.resize((new_width, new_height), Resampling.LANCZOS)

            # 轉換為 Tkinter 可用的格式
            self.camera_img = ImageTk.PhotoImage(image=img)

            # 更新顯示
            self.camera_display.configure(image=self.camera_img)

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
                
            # 保存最後一幀，用於窗口大小變化時重新顯示
            self.last_photo_frame = frame.copy()

            # 轉換 OpenCV 的 BGR 格式為 RGB 格式
            if len(frame.shape) == 3:  # 彩色圖像
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:  # 灰度圖像
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

            # 轉換為 Tkinter 可用的格式
            img = Image.fromarray(rgb_frame)

            # 計算適合的顯示大小
            preview_width = self.preview_frame.winfo_width()
            preview_height = self.preview_frame.winfo_height()
            
            # 如果容器尚未完全初始化，使用默認尺寸
            if preview_width <= 1 or preview_height <= 1:
                preview_width = self.display_width
                preview_height = int(self.display_height * 0.4)

            # 保持原始比例縮放
            aspect_ratio = img.width / img.height
            if preview_width / preview_height > aspect_ratio:
                new_width = int(preview_height * aspect_ratio)
                new_height = preview_height
            else:
                new_width = preview_width
                new_height = int(preview_width / aspect_ratio)

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

    def show_progress(self):
        """显示进度条"""
        self.progress_bar.pack(fill=tk.X, expand=True, padx=5, pady=5)
        self.progress_bar.start(10)  # 开始动画，每10毫秒更新一次
        self.status_label.config(text=get_text("analyzing", "正在分析..."))
        
    def hide_progress(self):
        """隐藏进度条"""
        self.progress_bar.stop()  # 停止动画
        self.progress_bar.pack_forget()  # 隐藏进度条
        self.status_label.config(text=get_text("analysis_complete", "分析完成"))
        
    def set_status(self, text):
        """设置状态文本
        
        Args:
            text: 状态文本
        """
        self.status_label.config(text=text)

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
        
    def update_ui_text(self):
        """更新照片面板中的所有文字"""
        # 更新標題
        if hasattr(self, 'title_label'):
            self.title_label.configure(text=get_text("photo_panel", "照片面板"))
            
        # 更新拍照按鈕
        if hasattr(self, 'capture_button'):
            self.capture_button.configure(text=get_text("capture_photo", "拍攝照片"))
            
        # 更新分析按鈕
        if hasattr(self, 'analyze_button'):
            self.analyze_button.configure(text=get_text("analyze_photo", "分析照片"))
            
        # 更新預覽標籤
        if hasattr(self, 'preview_label'):
            self.preview_label.configure(text=get_text("camera_preview", "相機預覽"))
            
        # 更新照片標籤
        if hasattr(self, 'photo_label'):
            self.photo_label.configure(text=get_text("captured_photo", "拍攝的照片"))