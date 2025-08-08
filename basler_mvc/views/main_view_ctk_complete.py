"""
主視圖 - CustomTkinter 完整版本
基於原始 main_view.py 功能，使用 CustomTkinter 解決顯示問題
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import time
import logging
from typing import Optional, Dict, Any

# 設定 CustomTkinter 外觀
ctk.set_appearance_mode("system")  # 自動適應系統主題
ctk.set_default_color_theme("blue")  # 藍色主題


class MainView:
    """主視圖 - CustomTkinter 完整功能版本"""
    
    def __init__(self, controller):
        """初始化主視圖"""
        self.controller = controller
        
        # 創建主窗口
        self.root = ctk.CTk()
        
        # 註冊為控制器觀察者
        self.controller.add_view_observer(self.on_controller_event)
        
        # 視窗設置 - 響應式設計
        self.root.title("🚀 Basler acA640-300gm 精簡高性能系統")
        
        # 獲取螢幕尺寸並設定視窗大小
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 設定最佳尺寸（螢幕的80%但不超過最大值，不低於最小值）
        optimal_width = min(max(int(screen_width * 0.8), 1200), 1800)
        optimal_height = min(max(int(screen_height * 0.8), 900), 1200)
        
        # 計算居中位置
        x = (screen_width - optimal_width) // 2
        y = (screen_height - optimal_height) // 2
        
        self.root.geometry(f"{optimal_width}x{optimal_height}+{x}+{y}")
        self.root.minsize(1200, 900)  # 設置最小尺寸確保所有元素可見
        self.root.resizable(True, True)
        
        # UI 變量 - 美觀的FPS顯示格式
        self.status_var = tk.StringVar(value="狀態: 系統就緒")
        self.camera_fps_var = tk.StringVar(value="相機: 0 fps(0.0 MB/s)")
        self.processing_fps_var = tk.StringVar(value="處理: 0 fps")
        self.detection_fps_var = tk.StringVar(value="檢測: 0 fps")
        self.object_count_var = tk.StringVar(value="000")
        self.camera_info_var = tk.StringVar(value="相機: 未連接")
        self.method_var = tk.StringVar(value="circle")
        
        # 相機參數變量
        self.exposure_var = tk.DoubleVar(value=1000.0)
        self.min_area_var = tk.IntVar(value=100)
        self.max_area_var = tk.IntVar(value=5000)
        self.target_count_var = tk.IntVar(value=100)
        
        # 模式變量 - 實時、錄影、回放
        self.mode_var = tk.StringVar(value="live")
        
        # 連接和處理狀態
        self.connection_switch_on = False
        self.is_processing_active = False
        
        # 視頻顯示
        self.video_label = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.display_size = (640, 480)
        
        # 設備相關
        self.device_listbox = None
        self.devices = []
        
        # FPS平滑顯示緩衝區
        self.fps_history = {
            'camera': [],
            'processing': [],
            'detection': []
        }
        self.fps_update_counter = 0
        
        # 創建UI
        self.create_ui()
        
        # 初始化
        self.refresh_device_list()
        self.update_connection_ui()
        self.initialize_display_status()
        
        logging.info("CustomTkinter 完整版主視圖初始化完成")
    
    def create_ui(self):
        """創建響應式用戶界面 - 三欄布局"""
        # 主容器 - 緊湊布局，最大化視頻區域
        main_container = ctk.CTkFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=2, pady=2)
        
        # 頂部工具欄（固定高度）
        self.create_top_toolbar(main_container)
        
        # 主要內容區域（三欄布局）
        content_frame = ctk.CTkFrame(main_container)
        content_frame.pack(fill="both", expand=True, pady=(1, 0))
        
        # 配置三欄權重
        content_frame.grid_columnconfigure(0, weight=1, minsize=250)  # 左側面板
        content_frame.grid_columnconfigure(1, weight=3, minsize=600)  # 中央區域
        content_frame.grid_columnconfigure(2, weight=1, minsize=250)  # 右側面板
        content_frame.grid_rowconfigure(0, weight=1)
        
        # 創建三個主要面板
        self.create_left_panel(content_frame)
        self.create_center_panel(content_frame)
        self.create_right_panel(content_frame)
        
        # 底部狀態欄（固定高度）
        self.create_status_panel(main_container)
    
    def create_top_toolbar(self, parent):
        """創建頂部工具欄"""
        # 主工具欄
        main_toolbar = ctk.CTkFrame(parent, height=40)
        main_toolbar.pack(fill="x", padx=1, pady=(1, 2))
        
        # 左側控制組
        left_controls = ctk.CTkFrame(main_toolbar)
        left_controls.pack(side="left", padx=8, pady=5)
        
        # 連接開關控制
        connection_control = ctk.CTkFrame(left_controls)
        connection_control.pack(side="left", padx=5)
        
        ctk.CTkLabel(connection_control, text="連線:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(5, 2))
        
        self.connection_switch = ctk.CTkButton(
            connection_control,
            text="○",
            command=self.toggle_connection_switch,
            width=30,
            height=25,
            font=ctk.CTkFont(size=14)
        )
        self.connection_switch.pack(side="left", padx=2)
        
        # 啟動/停止控制組
        start_controls = ctk.CTkFrame(left_controls)
        start_controls.pack(side="left", padx=10)
        
        self.start_processing_btn = ctk.CTkButton(
            start_controls,
            text="▶️ 啟動處理",
            command=self.toggle_processing,
            state="disabled"
        )
        self.start_processing_btn.pack(side="left", padx=5)
        
        # 檢測方法選擇
        method_frame = ctk.CTkFrame(start_controls)
        method_frame.pack(side="left", padx=10)
        
        ctk.CTkLabel(method_frame, text="檢測方法:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 5))
        
        self.detection_method = ctk.CTkOptionMenu(
            method_frame,
            values=["circle", "contour"],
            variable=self.method_var,
            command=self.on_method_changed,
            width=100
        )
        self.detection_method.pack(side="left")
        
        # 右側工具組
        right_tools = ctk.CTkFrame(main_toolbar)
        right_tools.pack(side="right", padx=8, pady=5)
        
        self.settings_btn = ctk.CTkButton(
            right_tools,
            text="⚙️",
            command=self.open_settings,
            width=30,
            height=30,
            font=ctk.CTkFont(size=16)
        )
        self.settings_btn.pack(side="right")
    
    def create_left_panel(self, parent):
        """創建左側設備面板"""
        left_panel = ctk.CTkFrame(parent)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 1), pady=0)
        
        # 設備標題
        device_title = ctk.CTkLabel(
            left_panel,
            text="設備",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        device_title.pack(pady=(10, 5))
        
        # 設備列表容器
        device_container = ctk.CTkFrame(left_panel)
        device_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 設備下拉選單
        device_select_frame = ctk.CTkFrame(device_container)
        device_select_frame.pack(fill="x", padx=5, pady=5)
        
        self.device_combobox = ctk.CTkComboBox(
            device_select_frame,
            values=["未檢測到設備"],
            state="readonly",
            command=self.on_device_selected
        )
        self.device_combobox.pack(fill="x", padx=5, pady=5)
        
        # 連接狀態
        status_frame = ctk.CTkFrame(device_container)
        status_frame.pack(fill="x", padx=5, pady=5)
        
        self.connection_status = ctk.CTkLabel(
            status_frame,
            text="● 未連接",
            text_color="red",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.connection_status.pack(pady=10)
        
        # 相機設置區域
        camera_settings = ctk.CTkFrame(left_panel)
        camera_settings.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            camera_settings,
            text="📷 相機設置",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(pady=(10, 5))
        
        # 曝光時間設置
        exposure_frame = ctk.CTkFrame(camera_settings)
        exposure_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(exposure_frame, text="曝光時間 (μs)", font=ctk.CTkFont(size=11)).pack()
        
        self.exposure_slider = ctk.CTkSlider(
            exposure_frame,
            from_=100,
            to=10000,
            variable=self.exposure_var,
            command=self.on_exposure_changed
        )
        self.exposure_slider.pack(fill="x", padx=5, pady=5)
        
        self.exposure_label = ctk.CTkLabel(exposure_frame, text="1000.0")
        self.exposure_label.pack()
        
        # 即時檢測開關
        self.enable_detection_var = tk.BooleanVar(value=True)
        self.detection_checkbox = ctk.CTkCheckBox(
            camera_settings,
            text="啟用即時檢測",
            variable=self.enable_detection_var,
            command=self.toggle_detection
        )
        self.detection_checkbox.pack(pady=10)
        
        # 視頻控制區域
        video_control = ctk.CTkFrame(left_panel)
        video_control.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            video_control,
            text="🎬 視頻控制",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(pady=(10, 5))
        
        # 模式選擇 - 單選按鈕組
        mode_frame = ctk.CTkFrame(video_control)
        mode_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(mode_frame, text="模式:", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=10)
        
        self.mode_live = ctk.CTkRadioButton(
            mode_frame,
            text="實時",
            variable=self.mode_var,
            value="live",
            command=self.change_mode
        )
        self.mode_live.pack(anchor="w", padx=20, pady=2)
        
        self.mode_recording = ctk.CTkRadioButton(
            mode_frame,
            text="錄影",
            variable=self.mode_var,
            value="recording",
            command=self.change_mode
        )
        self.mode_recording.pack(anchor="w", padx=20, pady=2)
        
        self.mode_playback = ctk.CTkRadioButton(
            mode_frame,
            text="回放",
            variable=self.mode_var,
            value="playback",
            command=self.change_mode
        )
        self.mode_playback.pack(anchor="w", padx=20, pady=(2, 15))
    
    def create_center_panel(self, parent):
        """創建中央視頻顯示面板"""
        center_panel = ctk.CTkFrame(parent)
        center_panel.grid(row=0, column=1, sticky="nsew", padx=1, pady=0)
        
        # 配置中央面板的網格
        center_panel.grid_rowconfigure(1, weight=1)
        center_panel.grid_columnconfigure(0, weight=1)
        
        # 視頻標題欄
        video_header = ctk.CTkFrame(center_panel)
        video_header.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 2))
        
        # 相機信息和縮放控制
        header_left = ctk.CTkFrame(video_header)
        header_left.pack(side="left", padx=10, pady=5)
        
        self.camera_info_label = ctk.CTkLabel(
            header_left,
            text="📹 Basler acA640-300gm - 實時影像",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.camera_info_label.pack()
        
        # 縮放控制
        zoom_frame = ctk.CTkFrame(video_header)
        zoom_frame.pack(side="right", padx=10, pady=5)
        
        ctk.CTkLabel(zoom_frame, text="🔍", font=ctk.CTkFont(size=14)).pack(side="left")
        
        self.zoom_var = tk.StringVar(value="100%")
        zoom_menu = ctk.CTkOptionMenu(
            zoom_frame,
            values=["50%", "75%", "100%", "125%", "150%"],
            variable=self.zoom_var,
            width=80,
            command=self.change_zoom
        )
        zoom_menu.pack(side="left", padx=5)
        
        # 添加控制按鈕
        controls_frame = ctk.CTkFrame(zoom_frame)
        controls_frame.pack(side="left", padx=10)
        
        ctk.CTkButton(controls_frame, text="+", width=30, command=lambda: self.zoom_change(1.25)).pack(side="left", padx=2)
        ctk.CTkButton(controls_frame, text="-", width=30, command=lambda: self.zoom_change(0.8)).pack(side="left", padx=2)
        ctk.CTkButton(controls_frame, text="□", width=30, command=self.fit_to_window).pack(side="left", padx=2)
        
        # 視頻顯示區域
        video_container = ctk.CTkFrame(center_panel)
        video_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=2)
        video_container.grid_rowconfigure(0, weight=1)
        video_container.grid_columnconfigure(0, weight=1)
        
        # 創建視頻標籤
        self.video_label = ctk.CTkLabel(
            video_container,
            text="Basler acA640-300gm\n📹 Camera Ready\n配置開始捕獲取得影像",
            font=ctk.CTkFont(size=16),
            width=640,
            height=480
        )
        self.video_label.grid(row=0, column=0, padx=10, pady=10)
        
        # 底部信息欄
        info_frame = ctk.CTkFrame(center_panel, height=40)
        info_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=(2, 5))
        info_frame.grid_propagate(False)
        
        # 分辨率信息
        self.resolution_label = ctk.CTkLabel(info_frame, text="640 x 480 │ Mono8 │ 8 bit")
        self.resolution_label.pack(side="left", padx=15, pady=10)
        
        # 右側狀態信息
        status_right = ctk.CTkFrame(info_frame)
        status_right.pack(side="right", padx=15, pady=5)
        
        # FPS 顯示
        self.fps_display_frame = ctk.CTkFrame(status_right)
        self.fps_display_frame.pack(side="right")
        
        self.camera_fps_display = ctk.CTkLabel(
            self.fps_display_frame,
            textvariable=self.camera_fps_var,
            text_color="green",
            font=ctk.CTkFont(size=10)
        )
        self.camera_fps_display.pack(side="left", padx=5)
        
        self.processing_fps_display = ctk.CTkLabel(
            self.fps_display_frame,
            textvariable=self.processing_fps_var,
            text_color="blue",
            font=ctk.CTkFont(size=10)
        )
        self.processing_fps_display.pack(side="left", padx=5)
        
        self.detection_fps_display = ctk.CTkLabel(
            self.fps_display_frame,
            textvariable=self.detection_fps_var,
            text_color="purple",
            font=ctk.CTkFont(size=10)
        )
        self.detection_fps_display.pack(side="left", padx=5)
    
    def create_right_panel(self, parent):
        """創建右側檢測計數面板"""
        right_panel = ctk.CTkFrame(parent)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(1, 0), pady=0)
        
        # 檢測計數標題
        count_title = ctk.CTkLabel(
            right_panel,
            text="▶ 檢測計數",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        count_title.pack(pady=(10, 5))
        
        # 當前計數顯示
        count_display_frame = ctk.CTkFrame(right_panel)
        count_display_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(count_display_frame, text="當前計數", font=ctk.CTkFont(size=12)).pack(pady=(10, 5))
        
        self.count_label = ctk.CTkLabel(
            count_display_frame,
            textvariable=self.object_count_var,
            font=ctk.CTkFont(size=48, weight="bold"),
            text_color="#1f6aa5"
        )
        self.count_label.pack(pady=10)
        
        # 目標數量和進度
        target_frame = ctk.CTkFrame(right_panel)
        target_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(target_frame, text="目標數量:", font=ctk.CTkFont(size=11)).pack()
        
        self.target_entry = ctk.CTkEntry(
            target_frame,
            textvariable=self.target_count_var,
            width=100,
            justify="center"
        )
        self.target_entry.pack(pady=5)
        
        # 進度條
        self.progress_bar = ctk.CTkProgressBar(target_frame, width=200)
        self.progress_bar.pack(pady=10, padx=10, fill="x")
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(target_frame, text="0 / 100")
        self.progress_label.pack()
        
        # 控制按鈕
        control_buttons = ctk.CTkFrame(target_frame)
        control_buttons.pack(pady=10)
        
        ctk.CTkButton(
            control_buttons,
            text="▶ 開始",
            command=self.start_detection,
            height=30,
            width=80
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            control_buttons,
            text="⏸ 停止",
            command=self.stop_detection,
            height=30,
            width=80
        ).pack(side="left", padx=2)
        
        # 重置計數按鈕
        ctk.CTkButton(
            target_frame,
            text="🔄 重置計數",
            command=self.reset_count,
            height=30
        ).pack(pady=(10, 15))
        
        # 檢測參數調整
        params_frame = ctk.CTkFrame(right_panel)
        params_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            params_frame,
            text="🔧 檢測參數",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(10, 5))
        
        # 最小面積滑桿
        min_area_frame = ctk.CTkFrame(params_frame)
        min_area_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(min_area_frame, text="最小面積", font=ctk.CTkFont(size=10)).pack()
        
        self.min_area_slider = ctk.CTkSlider(
            min_area_frame,
            from_=10,
            to=500,
            variable=self.min_area_var,
            command=self.update_detection_params
        )
        self.min_area_slider.pack(fill="x", padx=5, pady=2)
        
        self.min_area_label = ctk.CTkLabel(min_area_frame, text="100")
        self.min_area_label.pack()
        
        # 最大面積滑桿
        max_area_frame = ctk.CTkFrame(params_frame)
        max_area_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(max_area_frame, text="最大面積", font=ctk.CTkFont(size=10)).pack()
        
        self.max_area_slider = ctk.CTkSlider(
            max_area_frame,
            from_=1000,
            to=10000,
            variable=self.max_area_var,
            command=self.update_detection_params
        )
        self.max_area_slider.pack(fill="x", padx=5, pady=2)
        
        self.max_area_label = ctk.CTkLabel(max_area_frame, text="5000")
        self.max_area_label.pack(pady=(0, 15))
        
        # 即時統計
        stats_frame = ctk.CTkFrame(right_panel)
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            stats_frame,
            text="📊 即時統計",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(pady=(10, 5))
        
        # 檢測品質指示器
        self.quality_label = ctk.CTkLabel(
            stats_frame,
            text="檢測品質: 良好",
            text_color="green",
            font=ctk.CTkFont(size=11)
        )
        self.quality_label.pack(pady=5)
        
        # 檢測 FPS
        self.detection_fps_stat = ctk.CTkLabel(
            stats_frame,
            textvariable=self.detection_fps_var,
            font=ctk.CTkFont(size=10),
            text_color="purple"
        )
        self.detection_fps_stat.pack(pady=(0, 15))
    
    def create_status_panel(self, parent):
        """創建底部狀態面板"""
        status_panel = ctk.CTkFrame(parent, height=60)
        status_panel.pack(fill="x", padx=1, pady=(2, 1))
        status_panel.pack_propagate(False)
        
        # 左側狀態信息
        left_status = ctk.CTkFrame(status_panel)
        left_status.pack(side="left", fill="y", padx=10, pady=5)
        
        self.status_label = ctk.CTkLabel(
            left_status,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack(side="left", padx=10)
        
        self.camera_info_status = ctk.CTkLabel(
            left_status,
            textvariable=self.camera_info_var,
            font=ctk.CTkFont(size=11)
        )
        self.camera_info_status.pack(side="left", padx=20)
        
        # 右側時間和統計信息
        right_status = ctk.CTkFrame(status_panel)
        right_status.pack(side="right", fill="y", padx=10, pady=5)
        
        # 時間戳
        self.timestamp_label = ctk.CTkLabel(
            right_status,
            text="2025-08-07 15:09:18",
            font=ctk.CTkFont(size=9),
            text_color="gray"
        )
        self.timestamp_label.pack(side="right", padx=10)
        
        # 物件計數顯示
        self.object_count_status = ctk.CTkLabel(
            right_status,
            text="物件: 0",
            font=ctk.CTkFont(size=11),
            text_color="#1f6aa5"
        )
        self.object_count_status.pack(side="right", padx=15)
    
    # ==================== 事件處理函數 ====================
    
    def toggle_connection_switch(self):
        """切換連接開關"""
        self.connection_switch_on = not self.connection_switch_on
        if self.connection_switch_on:
            # 嘗試連接
            success = self.connect_device()
            if success:
                self.connection_switch.configure(text="●", fg_color="green")
                self.start_processing_btn.configure(state="normal")
            else:
                self.connection_switch_on = False
                self.connection_switch.configure(text="○")
        else:
            # 斷開連接
            self.disconnect_device()
            self.connection_switch.configure(text="○")
            self.start_processing_btn.configure(state="disabled")
    
    def toggle_processing(self):
        """切換處理狀態"""
        self.is_processing_active = not self.is_processing_active
        if self.is_processing_active:
            success = self.controller.start_capture()
            if success:
                self.start_processing_btn.configure(text="⏸️ 停止處理")
            else:
                self.is_processing_active = False
        else:
            self.controller.stop_capture()
            self.start_processing_btn.configure(text="▶️ 啟動處理")
    
    def on_method_changed(self, method):
        """檢測方法改變"""
        self.controller.set_detection_method(method)
        logging.info(f"檢測方法已改為: {method}")
    
    def on_device_selected(self, device_name):
        """設備選擇改變"""
        logging.info(f"選擇設備: {device_name}")
    
    def on_exposure_changed(self, value):
        """曝光時間改變"""
        exposure = int(float(value))
        self.exposure_label.configure(text=f"{exposure}")
        # 即時應用曝光設置
        if self.connection_switch_on:
            self.controller.set_exposure_time(exposure)
    
    def change_mode(self):
        """更改系統模式"""
        mode = self.mode_var.get()
        success = self.controller.switch_mode(mode)
        if success:
            logging.info(f"系統模式已切換為: {mode}")
        else:
            logging.error(f"切換模式失敗: {mode}")
    
    def change_zoom(self, zoom_str):
        """更改顯示縮放"""
        zoom_percent = int(zoom_str.replace('%', ''))
        logging.info(f"縮放設置為: {zoom_percent}%")
        # 實現縮放邏輯
        self.apply_zoom(zoom_percent / 100.0)
    
    def zoom_change(self, factor):
        """縮放改變"""
        current_zoom_str = self.zoom_var.get()
        current_zoom = int(current_zoom_str.replace('%', ''))
        new_zoom = max(25, min(200, int(current_zoom * factor)))
        self.zoom_var.set(f"{new_zoom}%")
        self.apply_zoom(new_zoom / 100.0)
    
    def fit_to_window(self):
        """適合視窗大小"""
        self.zoom_var.set("100%")
        self.apply_zoom(1.0)
    
    def apply_zoom(self, factor):
        """應用縮放"""
        # 實現縮放顯示邏輯
        self.display_size = (int(640 * factor), int(480 * factor))
        logging.info(f"應用縮放: {factor:.2f}, 顯示大小: {self.display_size}")
    
    def start_detection(self):
        """開始檢測"""
        if self.controller.start_batch_detection():
            logging.info("批次檢測已啟動")
        else:
            messagebox.showerror("錯誤", "啟動檢測失敗")
    
    def stop_detection(self):
        """停止檢測"""
        if self.controller.stop_batch_detection():
            logging.info("批次檢測已停止")
    
    def reset_count(self):
        """重置計數"""
        self.object_count_var.set("000")
        self.progress_bar.set(0)
        self.progress_label.configure(text="0 / 100")
        logging.info("計數已重置")
    
    def update_detection_params(self, value):
        """更新檢測參數"""
        min_area = int(self.min_area_var.get())
        max_area = int(self.max_area_var.get())
        
        self.min_area_label.configure(text=str(min_area))
        self.max_area_label.configure(text=str(max_area))
        
        # 更新控制器參數
        params = {
            'min_area': min_area,
            'max_area': max_area
        }
        self.controller.update_detection_parameters(params)
    
    def toggle_detection(self):
        """切換檢測開關"""
        enabled = self.enable_detection_var.get()
        self.controller.toggle_detection(enabled)
        status = "已啟用" if enabled else "已停用"
        logging.info(f"即時檢測 {status}")
    
    def open_settings(self):
        """開啟設定"""
        # 實現設定對話框
        messagebox.showinfo("設定", "設定功能開發中...")
    
    # ==================== 設備管理 ====================
    
    def refresh_device_list(self):
        """刷新設備列表"""
        try:
            cameras = self.controller.detect_cameras()
            self.devices = cameras
            
            if cameras:
                device_names = []
                for i, camera in enumerate(cameras):
                    status = "✅" if camera.get('is_target', False) else "⚠️"
                    device_name = f"{status} {camera['model']} ({camera.get('serial', 'N/A')})"
                    device_names.append(device_name)
                
                self.device_combobox.configure(values=device_names)
                self.device_combobox.set(device_names[0])
            else:
                self.device_combobox.configure(values=["未檢測到設備"])
                self.device_combobox.set("未檢測到設備")
                
        except Exception as e:
            logging.error(f"刷新設備列表失敗: {str(e)}")
            self.device_combobox.configure(values=[f"檢測失敗: {str(e)}"])
            self.device_combobox.set(f"檢測失敗: {str(e)}")
    
    def connect_device(self) -> bool:
        """連接設備"""
        try:
            if not self.devices:
                messagebox.showwarning("警告", "沒有檢測到可用設備")
                return False
            
            # 連接第一個設備
            success = self.controller.connect_camera(0)
            if success:
                self.update_connection_ui()
                return True
            else:
                messagebox.showerror("錯誤", "相機連接失敗")
                return False
                
        except Exception as e:
            logging.error(f"連接設備錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"連接失敗: {str(e)}")
            return False
    
    def disconnect_device(self):
        """斷開設備連接"""
        try:
            self.controller.disconnect_camera()
            self.update_connection_ui()
        except Exception as e:
            logging.error(f"斷開設備錯誤: {str(e)}")
    
    def update_connection_ui(self):
        """更新連接狀態UI"""
        if hasattr(self.controller, 'camera_model') and self.controller.camera_model.is_connected:
            self.connection_status.configure(text="● 已連接", text_color="green")
            self.camera_info_var.set("相機: 已連接")
            self.start_processing_btn.configure(state="normal")
        else:
            self.connection_status.configure(text="● 未連接", text_color="red")
            self.camera_info_var.set("相機: 未連接")
            self.start_processing_btn.configure(state="disabled")
    
    def initialize_display_status(self):
        """初始化顯示狀態"""
        # 設置初始狀態
        self.status_var.set("狀態: 系統就緒")
        self.update_connection_ui()
        
        # 開始時間戳更新
        self.update_timestamp()
    
    def update_timestamp(self):
        """更新時間戳"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.timestamp_label.configure(text=current_time)
        self.root.after(1000, self.update_timestamp)
    
    # ==================== 顯示更新 ====================
    
    def update_frame(self, frame):
        """更新視頻幀顯示"""
        try:
            with self.frame_lock:
                if frame is None:
                    return
                
                # 調整幀大小以適合顯示
                height, width = frame.shape[:2]
                
                # 計算顯示尺寸（保持比例）
                display_width, display_height = self.display_size
                
                if len(frame.shape) == 3:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                else:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                
                # 調整大小
                frame_resized = cv2.resize(frame_rgb, (display_width, display_height))
                
                # 轉換為 PIL 格式
                pil_image = Image.fromarray(frame_resized)
                photo = ImageTk.PhotoImage(pil_image)
                
                # 更新顯示
                self.video_label.configure(image=photo, text="")
                self.video_label.image = photo  # 保持引用
                
                self.current_frame = frame
                
        except Exception as e:
            logging.error(f"更新幀顯示錯誤: {str(e)}")
    
    def on_controller_event(self, event_type: str, data: Any = None):
        """處理控制器事件"""
        try:
            if event_type == 'frame_processed':
                if data and 'frame' in data:
                    self.update_frame(data['frame'])
                    
                # 更新計數
                if 'object_count' in data:
                    count = data['object_count']
                    self.object_count_var.set(f"{count:03d}")
                    self.object_count_status.configure(text=f"物件: {count}")
                    
                    # 更新進度條
                    target = self.target_count_var.get()
                    if target > 0:
                        progress = min(count / target, 1.0)
                        self.progress_bar.set(progress)
                        self.progress_label.configure(text=f"{count} / {target}")
                
                # 更新 FPS - 美觀格式
                if 'processing_fps' in data:
                    fps = data['processing_fps']
                    if fps >= 100:
                        self.processing_fps_var.set(f"處理: {fps:.0f} fps")
                    else:
                        self.processing_fps_var.set(f"處理: {fps:.1f} fps")
                
                if 'detection_fps' in data:
                    fps = data['detection_fps']
                    if fps >= 100:
                        self.detection_fps_var.set(f"檢測: {fps:.0f} fps")
                    else:
                        self.detection_fps_var.set(f"檢測: {fps:.1f} fps")
                    
            elif event_type == 'camera_stats_updated':
                if data and 'current_fps' in data:
                    fps = data['current_fps']
                    # 計算數據傳輸速率
                    bytes_per_frame = 640 * 480 * 1  # Mono8
                    bytes_per_second = bytes_per_frame * fps
                    mb_per_second = bytes_per_second / (1024 * 1024)
                    
                    if fps >= 100:
                        self.camera_fps_var.set(f"相機: {fps:.0f} fps({mb_per_second:.1f} MB/s)")
                    else:
                        self.camera_fps_var.set(f"相機: {fps:.1f} fps({mb_per_second:.1f} MB/s)")
                    
            elif event_type == 'system_status':
                if data:
                    self.status_var.set(f"狀態: {data}")
                    
            elif event_type == 'system_error':
                if data:
                    self.status_var.set(f"錯誤: {data}")
                    logging.error(f"系統錯誤: {data}")
                    
        except Exception as e:
            logging.error(f"處理控制器事件錯誤: {str(e)}")
    
    def run(self):
        """運行主循環"""
        try:
            logging.info("CustomTkinter 完整版主視圖開始運行")
            self.root.mainloop()
        except Exception as e:
            logging.error(f"主循環運行錯誤: {str(e)}")
            raise
        finally:
            logging.info("CustomTkinter 完整版主視圖已停止")