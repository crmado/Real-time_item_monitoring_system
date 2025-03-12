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

        # 設定固定顯示大小
        self.display_width = 800
        self.display_height = 600
        self.last_frame = None

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
            style='VideoContainer.TFrame'
        )
        self.image_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        self.image_container.pack_propagate(False)  # 防止容器自動調整大小
        
        # 影像標籤
        self.image_label = ttk.Label(
            self.image_container,
            style='Video.TLabel',
            text="請選擇相機"
        )
        self.image_label.pack(fill=tk.BOTH, expand=True)

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
            if frame is None:
                logging.warning("更新圖像時收到空幀")
                print("更新圖像時收到空幀")
                return
                
            # 保存最後一幀，用於窗口大小變化時重新顯示
            self.last_frame = frame.copy()
            
            # 轉換 OpenCV 的 BGR 格式為 RGB 格式
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            print(f"已轉換 BGR 到 RGB，幀尺寸: {rgb_frame.shape}")

            # 調整影像大小，保持比例
            frame_height, frame_width = frame.shape[:2]
            aspect_ratio = frame_width / frame_height
            print(f"原始幀尺寸: {frame_width}x{frame_height}, 比例: {aspect_ratio:.2f}")
            print(f"顯示區域尺寸: {self.display_width}x{self.display_height}")

            if self.display_width / self.display_height > aspect_ratio:
                new_height = self.display_height
                new_width = int(self.display_height * aspect_ratio)
            else:
                new_width = self.display_width
                new_height = int(self.display_width / aspect_ratio)
                
            print(f"調整後的尺寸: {new_width}x{new_height}")

            # 調整影像大小
            img = Image.fromarray(rgb_frame)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"已調整圖像大小為: {new_width}x{new_height}")

            # 轉換為 Tkinter 可用的格式
            img_tk = ImageTk.PhotoImage(image=img)
            print("已轉換為 Tkinter 格式")

            # 更新顯示
            self.image_label.configure(image=img_tk)
            self.image_label.image = img_tk  # 保持引用，防止被垃圾回收
            print("已更新圖像標籤")
            
            # 確保標籤可見
            self.image_label.pack(fill=tk.BOTH, expand=True)
            print("已確保圖像標籤可見")
            
            # 更新顯示大小
            self.display_width = new_width
            self.display_height = new_height
            print(f"已更新顯示大小為: {self.display_width}x{self.display_height}")
            
            # 強制更新 Tkinter
            self.update_idletasks()
            print("已強制更新 Tkinter 界面")

        except Exception as e:
            logging.error(f"更新圖像顯示時發生錯誤：{str(e)}")
            print(f"更新圖像顯示時發生錯誤：{str(e)}")
            import traceback
            traceback.print_exc()

    def resize(self, event=None):
        """
        處理視窗大小變化
        
        Args:
            event: 事件對象
        """
        # 當視窗大小變化時，保持固定大小
        if hasattr(self, 'last_frame') and self.last_frame is not None:
            self.update_image(self.last_frame)

    def set_callback(self, event_name, callback):
        """
        設置回調函數
        
        Args:
            event_name: 事件名稱
            callback: 回調函數
        """
        self.callbacks[event_name] = callback
        
    def update_ui_text(self):
        """更新視頻面板中的所有文字"""
        # 視頻面板通常沒有太多文字元素，但如果有，可以在這裡更新
        # 例如，如果有提示標籤
        if hasattr(self, 'hint_label'):
            self.hint_label.configure(text=get_text("roi_drag_hint", "拖曳綠線調整ROI位置"))

    def get_display_size(self):
        """
        獲取顯示區域大小

        Returns:
            tuple: (寬度, 高度)
        """
        return self.display_width, self.display_height