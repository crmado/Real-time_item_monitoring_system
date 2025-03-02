"""
分析結果面板組件
負責顯示分析結果
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from PIL.Image import Resampling
import cv2
import logging
import numpy as np
import base64
import io

from utils.language import get_text


class AnalysisPanel(ttk.Frame):
    """分析結果面板類別"""

    # ==========================================================================
    # 第一部分：基本屬性和初始化
    # ==========================================================================
    def __init__(self, parent, **kwargs):
        """
        初始化分析結果面板

        Args:
            parent: 父級視窗
            **kwargs: 其他參數
        """
        super().__init__(parent, **kwargs)
        self.parent = parent

        # 設定預設顯示大小
        self.display_width = 200
        self.display_height = 200

        # UI元件
        self.create_widgets()

    # ==========================================================================
    # 第二部分：UI元件創建
    # ==========================================================================
    def create_widgets(self):
        """創建分析結果面板組件"""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 創建網格布局
        grid_frame = ttk.Frame(main_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True)

        # 輔助函數：創建標題標籤
        def create_title_label(text):
            label = ttk.Label(
                grid_frame,
                text=text,
                anchor=tk.CENTER,
                font=("Arial", 10, "bold")
            )
            return label

        # 輔助函數：創建圖像顯示區域
        def create_image_display():
            frame = ttk.Frame(grid_frame)
            display = ttk.Label(frame, anchor=tk.CENTER)
            display.pack(fill=tk.BOTH, expand=True)
            display.configure(background="#f0f0f0")
            return frame, display

        # 輸入圖像
        create_title_label(get_text("input_image", "輸入圖像")).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.input_frame, self.input_display = create_image_display()
        self.input_frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # 分析圖像
        create_title_label(get_text("analysis_image", "分析圖像")).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.analysis_frame, self.analysis_display = create_image_display()
        self.analysis_frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        # 展開輸入圖像
        create_title_label(get_text("unwrapped_input", "展開輸入圖像")).grid(row=2, column=0, padx=5, pady=5,
                                                                             sticky="ew")
        self.unwrapped_input_frame, self.unwrapped_input_display = create_image_display()
        self.unwrapped_input_frame.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")

        # 重建圖像
        create_title_label(get_text("unwrapped_pred", "重建圖像")).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.unwrapped_pred_frame, self.unwrapped_pred_display = create_image_display()
        self.unwrapped_pred_frame.grid(row=3, column=1, padx=5, pady=5, sticky="nsew")

        # 誤差圖
        create_title_label(get_text("error_map", "誤差圖")).grid(row=4, column=0, columnspan=2, padx=5, pady=5,
                                                                 sticky="ew")
        self.error_map_frame, self.error_map_display = create_image_display()
        self.error_map_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        # 檢測結果
        self.result_frame = ttk.LabelFrame(main_frame, text=get_text("inspection_result", "檢測結果"))
        self.result_frame.pack(fill=tk.X, padx=5, pady=10)

        self.result_text = tk.Text(self.result_frame, height=5, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.result_text.configure(state=tk.DISABLED)

        # 設置網格布局的大小調整
        for i in range(6):
            grid_frame.grid_rowconfigure(i, weight=1)
        for i in range(2):
            grid_frame.grid_columnconfigure(i, weight=1)

    # ==========================================================================
    # 第三部分：UI更新方法
    # ==========================================================================
    def update_analysis_results(self, result):
        """
        更新分析結果

        Args:
            result: 分析結果數據
        """
        try:
            images = result.get('images', {})

            # 更新輸入圖像
            if 'original_image' in result:
                self._update_image_display(self.input_display, result['original_image'])

            # 更新分析圖像
            if 'analysis' in images:
                self._update_image_display(self.analysis_display, images['analysis'], is_base64=True)

            # 更新展開輸入圖像
            if 'unwrapped_input' in images:
                self._update_image_display(self.unwrapped_input_display, images['unwrapped_input'], is_base64=True)

            # 更新重建圖像
            if 'unwrapped_pred' in images:
                self._update_image_display(self.unwrapped_pred_display, images['unwrapped_pred'], is_base64=True)

            # 更新誤差圖
            if 'error_map' in images:
                self._update_image_display(self.error_map_display, images['error_map'], is_base64=True)

            # 更新檢測結果文字
            is_defective = result.get('is_defective', False)
            score = result.get('score', 0.0)
            mean_error = result.get('mean_error', 0.0)

            result_bg_color = "#ffebee" if is_defective else "#e8f5e9"
            result_text_color = "#ff4444" if is_defective else "#4CAF50"
            status_text = get_text("defective", "有缺陷") if is_defective else get_text("normal", "正常")

            result_text = f"""
                {get_text("inspection_status", "檢測狀態")}: {status_text}
                {get_text("inspection_score", "檢測分數")}: {score:.2E}
                {get_text("mean_error", "平均誤差")}: {mean_error:.2E}
            """

            self.result_text.configure(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, result_text)
            self.result_text.configure(state=tk.DISABLED)

            # 設置結果框的樣式
            self.result_frame.configure(style='Result.TLabelframe')
            self.result_text.configure(background=result_bg_color)

        except Exception as e:
            logging.error(f"更新分析結果時發生錯誤：{str(e)}")
            raise e

    def _update_image_display(self, display_widget, image_data, is_base64=False):
        """
        更新圖像顯示

        Args:
            display_widget: 顯示控件
            image_data: 圖像數據
            is_base64: 是否為base64編碼的圖像
        """
        try:
            # 從不同來源獲取圖像
            if is_base64:
                img = self._process_base64_image(image_data)
            elif isinstance(image_data, np.ndarray):
                img = self._process_numpy_image(image_data)
            else:
                logging.error(f"不支持的圖像數據類型: {type(image_data)}")
                return

            # 調整圖像大小
            img_tk = self._resize_image(img, display_widget)

            # 更新顯示
            display_widget.configure(image=img_tk)
            setattr(display_widget, "_image_reference", img_tk)

        except Exception as e:
            logging.error(f"更新圖像顯示時發生錯誤：{str(e)}")

    def _process_base64_image(self, base64_string):
        """處理base64編碼的圖像"""
        try:
            # 解碼base64字符串
            img_data = base64.b64decode(base64_string)
            img_bytes = io.BytesIO(img_data)
            img = Image.open(img_bytes)
            return img
        except Exception as e:
            logging.error(f"處理base64圖像時發生錯誤：{str(e)}")
            return None

    def _process_numpy_image(self, numpy_img):
        """處理numpy數組格式的圖像"""
        try:
            # 轉換OpenCV格式到PIL格式
            if len(numpy_img.shape) == 2:  # 灰度圖像
                img = Image.fromarray(numpy_img)
            else:  # 彩色圖像
                rgb_img = cv2.cvtColor(numpy_img, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb_img)
            return img
        except Exception as e:
            logging.error(f"處理numpy圖像時發生錯誤：{str(e)}")
            return None

    def _resize_image(self, img, display_widget):
        """調整圖像大小"""
        try:
            if img is None:
                return None

            # 獲取顯示區域大小
            width = display_widget.winfo_width()
            height = display_widget.winfo_height()

            # 如果控件尚未完全初始化
            if width <= 1 or height <= 1:
                width = self.display_width
                height = self.display_height

            # 保持原始比例縮放
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height

            if width / height > aspect_ratio:
                new_width = int(height * aspect_ratio)
                new_height = height
            else:
                new_width = width
                new_height = int(width / aspect_ratio)

            # 調整圖像大小
            img_resized = img.resize((new_width, new_height), Resampling.LANCZOS)

            # 轉換為Tkinter格式
            img_tk = ImageTk.PhotoImage(img_resized)
            return img_tk

        except Exception as e:
            logging.error(f"調整圖像大小時發生錯誤：{str(e)}")
            return None