"""
拍照面板組件
負責拍照和顯示分析結果
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import logging
import numpy as np

from utils.language import get_text


class PhotoPanel(ttk.Frame):
    """拍照面板類別"""

    # ==========================================================================
    # 第一部分：基本屬性和初始化
    # ==========================================================================
    def __init__(self, parent, **kwargs):
        """
        初始化拍照面板

        Args:
            parent: 父級視窗
            **kwargs: 其他參數
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.callbacks = {}

        # 設定預設顯示大小
        self.display_width = 640
        self.display_height = 480

        # 分析結果
        self.analysis_result = None

        # 創建UI元件
        self.create_widgets()

    # ==========================================================================
    # 第二部分：UI元件創建
    # ==========================================================================
    def create_widgets(self):
        """創建拍照面板組件"""
        # 主框架
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左側面板 - 相機預覽和拍照按鈕
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 相機預覽標籤
        preview_frame = ttk.LabelFrame(left_frame, text=get_text("camera_preview", "相機即時預覽"))
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 影像標籤
        self.preview_container = ttk.Frame(
            preview_frame,
            width=self.display_width,
            height=self.display_height
        )
        self.preview_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.preview_container.pack_propagate(False)

        self.preview_label = ttk.Label(
            self.preview_container,
            style='Video.TLabel',
            text=get_text("no_camera", "未連接相機")
        )
        self.preview_label.pack(fill=tk.BOTH, expand=True)

        # 拍照按鈕
        self.capture_button = ttk.Button(
            left_frame,
            text=get_text("capture_photo", "拍攝"),
            style='Accent.TButton',
            command=self._on_capture
        )
        self.capture_button.pack(pady=10)

        # 右側面板 - 分析結果顯示
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 上方結果
        top_results_frame = ttk.Frame(right_frame)
        top_results_frame.pack(fill=tk.X, expand=False, pady=5)

        # 原始圖像
        original_frame = ttk.LabelFrame(top_results_frame, text=get_text("original_image", "原始圖像"))
        original_frame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)

        self.original_container = ttk.Frame(original_frame, width=200, height=200)
        self.original_container.pack(padx=2, pady=2)
        self.original_container.pack_propagate(False)

        self.original_label = ttk.Label(self.original_container)
        self.original_label.pack(fill=tk.BOTH, expand=True)

        # 分析圖像
        analysis_frame = ttk.LabelFrame(top_results_frame, text=get_text("analysis_image", "分析圖像"))
        analysis_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.NSEW)

        self.analysis_container = ttk.Frame(analysis_frame, width=200, height=200)
        self.analysis_container.pack(padx=2, pady=2)
        self.analysis_container.pack_propagate(False)

        self.analysis_label = ttk.Label(self.analysis_container)
        self.analysis_label.pack(fill=tk.BOTH, expand=True)

        # 中間結果
        middle_results_frame = ttk.Frame(right_frame)
        middle_results_frame.pack(fill=tk.X, expand=False, pady=5)

        # 左側分析結果
        left_result_frame = ttk.LabelFrame(middle_results_frame, text=get_text("detection_result", "檢測結果"))
        left_result_frame.grid(row=0, column=0, padx=5, pady=5, sticky=tk.NSEW)

        self.left_result_container = ttk.Frame(left_result_frame, width=200, height=100)
        self.left_result_container.pack(padx=2, pady=2)
        self.left_result_container.pack_propagate(False)

        self.left_result_label = ttk.Label(self.left_result_container)
        self.left_result_label.pack(fill=tk.BOTH, expand=True)

        # 右側分析結果
        right_result_frame = ttk.LabelFrame(middle_results_frame, text=get_text("analysis_data", "分析數據"))
        right_result_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.NSEW)

        self.right_result_container = ttk.Frame(right_result_frame, width=200, height=100)
        self.right_result_container.pack(padx=2, pady=2)
        self.right_result_container.pack_propagate(False)

        self.right_result_label = ttk.Label(self.right_result_container)
        self.right_result_label.pack(fill=tk.BOTH, expand=True)

        # 波形圖
        waveform_frame = ttk.LabelFrame(right_frame, text=get_text("waveform", "波形圖"))
        waveform_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.waveform_container = ttk.Frame(waveform_frame, height=120)
        self.waveform_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.waveform_canvas = tk.Canvas(self.waveform_container, bg="black")
        self.waveform_canvas.pack(fill=tk.BOTH, expand=True)

        # 分析結果區域
        result_frame = ttk.LabelFrame(right_frame, text=get_text("analysis_result", "檢測結果"))
        result_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)

        self.result_text = tk.Text(result_frame, height=3, width=30, bg="#FFD0D0")
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.result_text.config(state=tk.DISABLED)

    # ==========================================================================
    # 第三部分：事件處理
    # ==========================================================================
    def _on_capture(self):
        """當點擊拍照按鈕時處理"""
        if 'capture_photo' in self.callbacks and self.callbacks['capture_photo']:
            self.callbacks['capture_photo']()

    # ==========================================================================
    # 第四部分：數據更新
    # ==========================================================================
    def update_preview(self, frame):
        """
        更新預覽圖像

        Args:
            frame: OpenCV 圖像幀
        """
        try:
            # 轉換 OpenCV 的 BGR 格式為 RGB 格式
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 調整圖像大小
            preview_img = self._resize_image(rgb_frame, self.preview_container.winfo_width(),
                                             self.preview_container.winfo_height())
            self.preview_label.configure(image=preview_img)
            self.preview_label.image = preview_img

        except Exception as e:
            logging.error(f"更新預覽圖像時發生錯誤：{str(e)}")

    def update_analysis_results(self, analysis_result):
        """
        更新分析結果

        Args:
            analysis_result: 分析結果字典
        """
        try:
            if not analysis_result or not analysis_result.get("success", False):
                self._show_error_message("分析失敗：" + analysis_result.get("message", "未知錯誤"))
                return

            self.analysis_result = analysis_result

            # 更新原始圖像
            if "original_image" in analysis_result:
                original_rgb = cv2.cvtColor(analysis_result["original_image"], cv2.COLOR_BGR2RGB)
                original_img = self._resize_image(original_rgb, 200, 200)
                self.original_label.configure(image=original_img)
                self.original_label.image = original_img

            # 更新分析圖像 - 這裡假設有處理過的圖像
            if "processed_image" in analysis_result:
                # 如果是灰度圖，轉換為彩色顯示
                processed_img = analysis_result["processed_image"]
                if len(processed_img.shape) == 2:  # 灰度圖
                    processed_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
                else:
                    processed_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)

                processed_tk = self._resize_image(processed_img, 200, 200)
                self.analysis_label.configure(image=processed_tk)
                self.analysis_label.image = processed_tk

            # 更新波形圖
            if "waveform_data" in analysis_result:
                self._draw_waveform(analysis_result["waveform_data"])

            # 更新結果文本
            quality_score = analysis_result.get("analysis_result", {}).get("quality_score", 0)
            has_circles = analysis_result.get("analysis_result", {}).get("has_circles", False)

            status = "有缺陷" if not has_circles else "正常"
            result_text = f"檢測狀態: {status}\n檢測分數: {quality_score:.2f}"

            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(1.0, result_text)
            self.result_text.config(state=tk.DISABLED)

        except Exception as e:
            logging.error(f"更新分析結果時發生錯誤：{str(e)}")
            self._show_error_message(f"顯示分析結果時發生錯誤：{str(e)}")

    # ==========================================================================
    # 第五部分：工具方法
    # ==========================================================================
    def _resize_image(self, image, width, height):
        """調整圖像大小並轉換為Tkinter格式"""
        # 如果圖像為None，返回None
        if image is None:
            return None

        img_height, img_width = image.shape[:2]
        aspect_ratio = img_width / img_height

        if width / height > aspect_ratio:
            new_height = height
            new_width = int(height * aspect_ratio)
        else:
            new_width = width
            new_height = int(width / aspect_ratio)

        # 調整圖像大小
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # 轉換為Tkinter格式
        img = Image.fromarray(resized)
        img_tk = ImageTk.PhotoImage(image=img)

        return img_tk

    def _draw_waveform(self, waveform_data):
        """繪製波形圖"""
        if not waveform_data:
            return

        # 清除畫布
        self.waveform_canvas.delete("all")

        # 獲取畫布尺寸
        canvas_width = self.waveform_canvas.winfo_width()
        canvas_height = self.waveform_canvas.winfo_height()

        # 如果畫布還未實際渲染，使用預設值
        if canvas_width <= 1:
            canvas_width = 400
        if canvas_height <= 1:
            canvas_height = 100

        # 計算縮放因子
        x_scale = canvas_width / (len(waveform_data) - 1)
        y_max = max(waveform_data)
        y_min = min(waveform_data)
        y_range = max(1, y_max - y_min)  # 避免除以零
        y_scale = 0.8 * canvas_height / y_range

        # 繪製波形
        points = []
        for i, val in enumerate(waveform_data):
            x = i * x_scale
            # 反轉y座標，使較大的值顯示在頂部
            y = canvas_height - ((val - y_min) * y_scale + 0.1 * canvas_height)
            points.append(x)
            points.append(y)

        if len(points) >= 4:  # 至少需要兩個點才能繪製一條線
            self.waveform_canvas.create_line(points, fill="red", width=2, smooth=True)

    def _show_error_message(self, message):
        """在結果文本區域顯示錯誤訊息"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, f"錯誤：{message}")
        self.result_text.config(state=tk.DISABLED)

    def set_callback(self, event_name, callback):
        """設置回調函數"""
        self.callbacks[event_name] = callback