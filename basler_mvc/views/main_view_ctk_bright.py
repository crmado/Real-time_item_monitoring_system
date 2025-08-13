"""
主視圖 - CustomTkinter 明亮清晰版本
根據用戶要求改為明亮背景，整體清晰清楚
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

# 設定 CustomTkinter 外觀 - 明亮清晰模式
ctk.set_appearance_mode("light")  # 使用明亮模式
ctk.set_default_color_theme("blue")  # 藍色主題

# 定義明亮清晰配色方案
class ColorScheme:
    # 主要顏色 - 明亮清晰但專業
    PRIMARY_BLUE = "#2563eb"      # 明亮主藍色
    ACCENT_BLUE = "#3b82f6"       # 強調藍色
    SUCCESS_GREEN = "#059669"     # 專業綠色
    WARNING_ORANGE = "#d97706"    # 明亮橙色
    ERROR_RED = "#dc2626"         # 清晰紅色
    PURPLE_ACCENT = "#7c3aed"     # 明亮紫色
    
    # 文字顏色 - 深色文字在淺色背景上
    TEXT_PRIMARY = "#111827"      # 深色主要文字
    TEXT_SECONDARY = "#6b7280"    # 中灰色次要文字
    TEXT_ACCENT = "#2563eb"       # 藍色強調文字
    TEXT_SUCCESS = "#059669"      # 綠色文字
    TEXT_WARNING = "#d97706"      # 橙色文字
    TEXT_ERROR = "#dc2626"        # 紅色文字
    
    # 背景顏色 - 明亮清晰
    BG_PRIMARY = "#f9fafb"       # 主背景 - 非常淺的灰色
    BG_CARD = "#ffffff"          # 白色卡片背景
    BG_SECONDARY = "#f3f4f6"     # 次要背景
    BG_ACCENT = "#eff6ff"        # 淺藍色背景

# 字體大小系統
class FontSizes:
    HUGE = 52        # 超大數字顯示
    LARGE = 18       # 大標題
    TITLE = 15       # 標題
    SUBTITLE = 13    # 副標題  
    BODY = 12        # 正文
    SMALL = 11       # 小字
    TINY = 10        # 極小字


class MainView:
    """主視圖 - 明亮清晰版本"""
    
    def __init__(self, controller):
        """初始化主視圖"""
        self.controller = controller
        
        # 創建主窗口
        self.root = ctk.CTk()
        self.root.configure(fg_color=ColorScheme.BG_PRIMARY)
        
        # 註冊為控制器觀察者
        self.controller.add_view_observer(self.on_controller_event)
        
        # 🎯 註冊為相機模型的觀察者（設備監控）
        try:
            if hasattr(self.controller, 'camera_model') and self.controller.camera_model:
                self.controller.camera_model.add_observer(self.on_device_list_changed)
                logging.info("✅ 已註冊為設備監控觀察者")
            else:
                logging.warning("⚠️ 相機模型不存在，跳過觀察者註冊")
        except Exception as e:
            logging.error(f"註冊設備監控觀察者失敗: {str(e)}")
        
        # 視窗設置
        self.root.title("🚀 Basler acA640-300gm 精簡高性能系統")
        
        # 獲取螢幕尺寸並設定視窗大小
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        optimal_width = min(max(int(screen_width * 0.85), 1400), 1800)
        optimal_height = min(max(int(screen_height * 0.85), 1000), 1200)
        
        x = (screen_width - optimal_width) // 2
        y = (screen_height - optimal_height) // 2
        
        self.root.geometry(f"{optimal_width}x{optimal_height}+{x}+{y}")
        self.root.minsize(1400, 1000)
        self.root.resizable(True, True)
        
        # 🎯 設置窗口關閉處理
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # UI 變量 - 修正FPS顯示格式
        self.status_var = tk.StringVar(value="狀態: 系統就緒")
        # 美觀的FPS顯示格式 - 包含中文標籤
        self.camera_fps_var = tk.StringVar(value="相機: 0 fps(0.0 MB/s)")
        self.processing_fps_var = tk.StringVar(value="處理: 0 fps")
        self.detection_fps_var = tk.StringVar(value="檢測: 0 fps")
        self.object_count_var = tk.StringVar(value="000")
        self.camera_info_var = tk.StringVar(value="相機: 未連接")
        self.method_var = tk.StringVar(value="background")
        
        # 🎯 包裝計數系統變量
        self.total_count_var = tk.StringVar(value="0")      # 當前計數：總累計
        self.segment_count_var = tk.StringVar(value="0")    # 目前計數：當前段
        self.package_count_var = tk.StringVar(value="0")    # 包裝數
        
        # FPS刷新控制
        self.last_fps_update = 0
        self.fps_update_interval = 1.0  # 1秒更新一次
        
        # 相機參數變量
        self.exposure_var = tk.DoubleVar(value=1000.0)
        self.min_area_var = tk.IntVar(value=100)
        self.max_area_var = tk.IntVar(value=5000)
        self.target_count_var = tk.IntVar(value=100)
        
        # 模式變量
        self.mode_var = tk.StringVar(value="live")
        
        # 連接和處理狀態
        self.connection_switch_on = False
        self.is_processing_active = False
        
        # 🔧 錄製時間更新定時器
        self.recording_timer_active = False
        
        # 視頻顯示
        self.video_label = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.display_size = (640, 480)
        
        # 設備相關
        self.device_combobox = None
        self.devices = []
        
        # 創建UI
        self.create_ui()
        
        # 初始化
        self.refresh_device_list()
        self.update_connection_ui()
        self.initialize_display_status()
        self.initialize_batch_variables()
        
        # 🎯 啟動設備監控
        self._start_device_monitoring()
        
        logging.info("CustomTkinter 明亮清晰版本初始化完成")
    
    def create_ui(self):
        """創建明亮清晰的用戶界面"""
        # 主容器 - 使用明亮背景
        main_container = ctk.CTkFrame(self.root, fg_color=ColorScheme.BG_PRIMARY, corner_radius=0)
        main_container.pack(fill="both", expand=True, padx=6, pady=6)
        
        # 頂部工具欄
        self.create_top_toolbar(main_container)
        
        # 主要內容區域（三欄布局）
        content_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(4, 0))
        
        # 配置三欄權重
        content_frame.grid_columnconfigure(0, weight=1, minsize=280)  # 左側面板
        content_frame.grid_columnconfigure(1, weight=2, minsize=600)  # 中央區域
        content_frame.grid_columnconfigure(2, weight=1, minsize=280)  # 右側面板
        content_frame.grid_rowconfigure(0, weight=1)
        
        # 創建三個主要面板
        self.create_left_panel(content_frame)
        self.create_center_panel(content_frame)
        self.create_right_panel(content_frame)
        
        # 底部狀態欄
        self.create_status_panel(main_container)
    
    def create_top_toolbar(self, parent):
        """創建頂部工具欄 - 明亮風格"""
        toolbar = ctk.CTkFrame(parent, height=50, fg_color=ColorScheme.BG_CARD)
        toolbar.pack(fill="x", padx=2, pady=(2, 4))
        
        # 左側控制組
        left_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        left_frame.pack(side="left", padx=15, pady=10)
        
        # 連線控制
        conn_frame = ctk.CTkFrame(left_frame, fg_color=ColorScheme.BG_SECONDARY)
        conn_frame.pack(side="left", padx=(0, 15))
        
        ctk.CTkLabel(
            conn_frame, 
            text="連線:", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left", padx=(12, 6), pady=8)
        
        self.connection_switch = ctk.CTkButton(
            conn_frame,
            text="○",
            command=self.toggle_connection_switch,
            width=35,
            height=30,
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold"),
            fg_color=ColorScheme.BG_SECONDARY,
            hover_color=ColorScheme.SUCCESS_GREEN,
            text_color=ColorScheme.TEXT_PRIMARY,
            border_width=2,
            border_color=ColorScheme.TEXT_SECONDARY
        )
        self.connection_switch.pack(side="left", padx=(0, 12), pady=8)
        
        # 啟動按鈕
        self.start_processing_btn = ctk.CTkButton(
            left_frame,
            text="▶️ 啟動處理",
            command=self.toggle_processing,
            state="disabled",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            height=34,
            fg_color=ColorScheme.ACCENT_BLUE,
            hover_color=ColorScheme.PRIMARY_BLUE,
            text_color="white"
        )
        self.start_processing_btn.pack(side="left", padx=(0, 15))
        
        # 檢測方法選擇
        method_frame = ctk.CTkFrame(left_frame, fg_color=ColorScheme.BG_SECONDARY)
        method_frame.pack(side="left")
        
        ctk.CTkLabel(
            method_frame, 
            text="檢測方法:", 
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left", padx=(12, 6), pady=8)
        
        self.detection_method = ctk.CTkOptionMenu(
            method_frame,
            values=["background", "hybrid", "circle", "contour"],
            variable=self.method_var,
            command=self.on_method_changed,
            width=120,
            font=ctk.CTkFont(size=FontSizes.BODY),
            dropdown_font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.BG_CARD,
            button_color=ColorScheme.ACCENT_BLUE,
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.detection_method.pack(side="left", padx=(0, 6), pady=8)
        
        # 🎯 100%準確率指示器
        self.accuracy_indicator = ctk.CTkLabel(
            method_frame,
            text="🎯 100%",
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold"),
            text_color="#10b981",  # 綠色
            width=50
        )
        self.accuracy_indicator.pack(side="left", padx=(0, 12), pady=8)
        
        # 右側設定按鈕
        self.settings_btn = ctk.CTkButton(
            toolbar,
            text="⚙️",
            command=self.open_settings,
            width=40,
            height=40,
            font=ctk.CTkFont(size=FontSizes.LARGE),
            fg_color=ColorScheme.WARNING_ORANGE,
            hover_color="#b45309",
            text_color="white"
        )
        self.settings_btn.pack(side="right", padx=15, pady=5)
    
    def create_left_panel(self, parent):
        """創建左側設備面板"""
        left_panel = ctk.CTkFrame(parent, fg_color=ColorScheme.BG_CARD)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=0)
        
        # 創建可滾動框架以避免內容過多時的佈局問題
        left_scrollable = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="transparent",
            scrollbar_button_color=ColorScheme.ACCENT_BLUE,
            scrollbar_button_hover_color=ColorScheme.PRIMARY_BLUE
        )
        left_scrollable.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 設備標題
        ctk.CTkLabel(
            left_scrollable,
            text="設備",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(pady=(15, 10))
        
        # 設備選擇區域
        device_frame = ctk.CTkFrame(left_scrollable, fg_color=ColorScheme.BG_SECONDARY)
        device_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        self.device_combobox = ctk.CTkComboBox(
            device_frame,
            values=["未檢測到設備"],
            state="readonly",
            command=self.on_device_selected,
            font=ctk.CTkFont(size=FontSizes.BODY),
            dropdown_font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.BG_CARD,
            border_color=ColorScheme.TEXT_SECONDARY,
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.device_combobox.pack(fill="x", padx=12, pady=(12, 5))
        
        # 🎯 設備刷新按鈕和監控狀態 - 改進布局但保持原色
        refresh_button_frame = ctk.CTkFrame(device_frame, fg_color="transparent")
        refresh_button_frame.pack(fill="x", padx=12, pady=(0, 12))
        
        self.refresh_devices_button = ctk.CTkButton(
            refresh_button_frame,
            text="🔄 手動刷新",
            command=self.refresh_devices_manually,
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold"),
            fg_color=ColorScheme.ACCENT_BLUE,
            hover_color=ColorScheme.PRIMARY_BLUE,
            text_color="#ffffff",
            width=120,
            height=28
        )
        self.refresh_devices_button.pack(side="left")
        
        # 設備監控狀態指示器
        self.monitor_status_label = ctk.CTkLabel(
            refresh_button_frame,
            text="🔍 監控中",
            font=ctk.CTkFont(size=FontSizes.SMALL),
            text_color=ColorScheme.SUCCESS_GREEN
        )
        self.monitor_status_label.pack(side="right", padx=(10, 0))
        
        # 連接狀態
        self.connection_status = ctk.CTkLabel(
            device_frame,
            text="● 未連接",
            text_color=ColorScheme.ERROR_RED,
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold")
        )
        self.connection_status.pack(pady=(5, 15))
        
        # 相機設置標題
        ctk.CTkLabel(
            left_scrollable,
            text="📷 相機設置",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.TEXT_ACCENT
        ).pack(pady=(0, 10))
        
        # 曝光時間設置 - 保持原色但改進布局
        exposure_frame = ctk.CTkFrame(left_scrollable, fg_color=ColorScheme.BG_SECONDARY)
        exposure_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        # 標題和輸入框
        exp_label_frame = ctk.CTkFrame(exposure_frame, fg_color="transparent")
        exp_label_frame.pack(fill="x", padx=12, pady=(12, 5))
        
        ctk.CTkLabel(
            exp_label_frame, 
            text="曝光時間 (μs)", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left")
        
        # 右側輸入控件組
        exp_input_frame = ctk.CTkFrame(exp_label_frame, fg_color="transparent")
        exp_input_frame.pack(side="right")
        
        # 數字輸入框
        self.exposure_entry = ctk.CTkEntry(
            exp_input_frame, 
            textvariable=self.exposure_var,
            width=80, height=28,
            justify="center",
            font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.BG_CARD,
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.exposure_entry.pack(side="left")
        self.exposure_entry.bind('<Return>', self.on_exposure_entry_changed)
        self.exposure_entry.bind('<FocusOut>', self.on_exposure_entry_changed)
        
        # 箭頭按鈕
        exp_arrow_frame = ctk.CTkFrame(exp_input_frame, fg_color="transparent")
        exp_arrow_frame.pack(side="left", padx=(5, 0))
        
        ctk.CTkButton(
            exp_arrow_frame, text="▲", width=20, height=14,
            command=lambda: self.adjust_exposure(100),
            font=ctk.CTkFont(size=10),
            fg_color=ColorScheme.ACCENT_BLUE,
            hover_color=ColorScheme.PRIMARY_BLUE
        ).pack()
        
        ctk.CTkButton(
            exp_arrow_frame, text="▼", width=20, height=14,
            command=lambda: self.adjust_exposure(-100),
            font=ctk.CTkFont(size=10),
            fg_color=ColorScheme.ACCENT_BLUE,
            hover_color=ColorScheme.PRIMARY_BLUE
        ).pack()
        
        # 曝光值顯示標籤 
        self.exposure_label = ctk.CTkLabel(
            exp_input_frame,
            text="1000",
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY,
            width=40
        )
        self.exposure_label.pack(side="left", padx=(5, 0))
        
        # 滑動條
        self.exposure_slider = ctk.CTkSlider(
            exposure_frame,
            from_=100,
            to=10000,
            variable=self.exposure_var,
            command=self.on_exposure_changed,
            progress_color=ColorScheme.ACCENT_BLUE,
            button_color=ColorScheme.PRIMARY_BLUE,
            fg_color=ColorScheme.BG_CARD
        )
        self.exposure_slider.pack(fill="x", padx=12, pady=5)
        
        # 即時檢測開關
        self.enable_detection_var = tk.BooleanVar(value=True)
        self.detection_checkbox = ctk.CTkCheckBox(
            left_scrollable,
            text="啟用即時檢測",
            variable=self.enable_detection_var,
            command=self.toggle_detection,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY,
            checkmark_color=ColorScheme.SUCCESS_GREEN,
            fg_color=ColorScheme.BG_SECONDARY,
            hover_color=ColorScheme.BG_ACCENT
        )
        self.detection_checkbox.pack(pady=15)
        
        # 影像控制區域
        ctk.CTkLabel(
            left_scrollable,
            text="🎬 影像控制",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.PURPLE_ACCENT
        ).pack(pady=(10, 10))
        
        # 模式選擇
        mode_frame = ctk.CTkFrame(left_scrollable, fg_color=ColorScheme.BG_SECONDARY)
        mode_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        ctk.CTkLabel(
            mode_frame, 
            text="模式:", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(anchor="w", padx=15, pady=(12, 5))
        
        # 模式單選按鈕
        self.mode_live = ctk.CTkRadioButton(
            mode_frame,
            text="實時",
            variable=self.mode_var,
            value="live",
            command=self.change_mode,
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY,
            fg_color=ColorScheme.ACCENT_BLUE,
            hover_color=ColorScheme.BG_ACCENT
        )
        self.mode_live.pack(anchor="w", padx=25, pady=3)
        
        self.mode_recording = ctk.CTkRadioButton(
            mode_frame,
            text="錄影",
            variable=self.mode_var,
            value="recording",
            command=self.change_mode,
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY,
            fg_color=ColorScheme.ACCENT_BLUE,
            hover_color=ColorScheme.BG_ACCENT
        )
        self.mode_recording.pack(anchor="w", padx=25, pady=3)
        
        self.mode_playback = ctk.CTkRadioButton(
            mode_frame,
            text="回放",
            variable=self.mode_var,
            value="playback",
            command=self.change_mode,
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY,
            fg_color=ColorScheme.ACCENT_BLUE,
            hover_color=ColorScheme.BG_ACCENT
        )
        self.mode_playback.pack(anchor="w", padx=25, pady=(3, 15))
        
        # 錄製控件區域
        self.recording_frame = ctk.CTkFrame(left_scrollable, fg_color=ColorScheme.BG_SECONDARY)
        # 預設隱藏，根據模式顯示
        
        # 檔名輸入
        filename_frame = ctk.CTkFrame(self.recording_frame, fg_color="transparent")
        filename_frame.pack(fill="x", padx=12, pady=(12, 8))
        
        ctk.CTkLabel(
            filename_frame, 
            text="檔名:", 
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(anchor="w")
        
        self.recording_filename = tk.StringVar(value=self.generate_recording_filename())
        filename_entry = ctk.CTkEntry(
            filename_frame, 
            textvariable=self.recording_filename,
            width=180, height=28,
            font=ctk.CTkFont(size=FontSizes.SMALL),
            fg_color=ColorScheme.BG_CARD,
            text_color=ColorScheme.TEXT_PRIMARY
        )
        filename_entry.pack(fill="x", pady=(5, 0))
        
        # 錄製按鈕和狀態
        record_control_frame = ctk.CTkFrame(self.recording_frame, fg_color="transparent")
        record_control_frame.pack(fill="x", padx=12, pady=(8, 12))
        
        self.record_button = ctk.CTkButton(
            record_control_frame,
            text="● 錄製",
            command=self.toggle_recording,
            height=32,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.ERROR_RED,
            hover_color="#b91c1c",
            text_color="white"
        )
        self.record_button.pack(fill="x", pady=(0, 8))
        
        self.recording_status = ctk.CTkLabel(
            record_control_frame,
            text="未錄製",
            font=ctk.CTkFont(size=FontSizes.SMALL),
            text_color=ColorScheme.TEXT_SECONDARY
        )
        self.recording_status.pack()
        
        # 回放控件區域
        self.playback_frame = ctk.CTkFrame(left_scrollable, fg_color=ColorScheme.BG_SECONDARY)
        # 預設隱藏，根據模式顯示
        
        # 檔案選擇
        file_frame = ctk.CTkFrame(self.playback_frame, fg_color="transparent")
        file_frame.pack(fill="x", padx=12, pady=(12, 8))
        
        ctk.CTkLabel(
            file_frame, 
            text="視頻檔案:", 
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(anchor="w")
        
        file_select_frame = ctk.CTkFrame(file_frame, fg_color="transparent")
        file_select_frame.pack(fill="x", pady=(5, 0))
        
        self.playback_file = tk.StringVar(value="未選擇檔案")
        self.file_label = ctk.CTkLabel(
            file_select_frame,
            textvariable=self.playback_file,
            font=ctk.CTkFont(size=FontSizes.SMALL),
            text_color=ColorScheme.TEXT_SECONDARY,
            wraplength=300,  # 設置換行寬度
            anchor="w",      # 左對齊
            justify="left"   # 文字左對齊
        )
        self.file_label.pack(side="left", fill="x", expand=True)
        
        ctk.CTkButton(
            file_select_frame,
            text="瀏覽",
            command=self.select_playback_file,
            width=60, height=24,
            font=ctk.CTkFont(size=FontSizes.SMALL),
            fg_color=ColorScheme.ACCENT_BLUE,
            hover_color=ColorScheme.PRIMARY_BLUE
        ).pack(side="right", padx=(5, 0))
        
        # 播放控件
        playback_controls = ctk.CTkFrame(self.playback_frame, fg_color="transparent")
        playback_controls.pack(fill="x", padx=12, pady=(8, 8))
        
        control_buttons = ctk.CTkFrame(playback_controls, fg_color="transparent")
        control_buttons.pack()
        
        # 🎥 簡化影片控制：只保留播放/暫停按鈕
        self.play_btn = ctk.CTkButton(
            control_buttons, text="▶️", width=40, height=32,
            command=self.toggle_playback,  # 使用現有的方法
            font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.SUCCESS_GREEN,
            hover_color="#047857"
        )
        self.play_btn.pack(side="left", padx=4)
        
        # 添加停止按鈕
        self.stop_btn = ctk.CTkButton(
            control_buttons, text="⏹️", width=40, height=32,
            command=self.stop_playback,  # 使用現有的方法
            font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.ERROR_RED,
            hover_color="#b91c1c"
        )
        self.stop_btn.pack(side="left", padx=4)
        
        # 🎯 新增：視頻進度條
        progress_frame = ctk.CTkFrame(self.playback_frame, fg_color="transparent")
        progress_frame.pack(fill="x", padx=12, pady=(8, 8))
        
        ctk.CTkLabel(
            progress_frame, 
            text="播放進度:", 
            font=ctk.CTkFont(size=FontSizes.SMALL),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(anchor="w")
        
        # 進度條
        self.video_progress = tk.DoubleVar(value=0.0)
        self.progress_slider = ctk.CTkSlider(
            progress_frame,
            from_=0.0,
            to=1.0,
            variable=self.video_progress,
            command=self.on_progress_changed,
            progress_color=ColorScheme.SUCCESS_GREEN,
            button_color=ColorScheme.SUCCESS_GREEN
        )
        self.progress_slider.pack(fill="x", pady=(5, 5))
        
        # 時間顯示
        self.time_label = ctk.CTkLabel(
            progress_frame, 
            text="00:00 / 00:00",
            font=ctk.CTkFont(size=FontSizes.SMALL, family="monospace"),
            text_color=ColorScheme.TEXT_ACCENT
        )
        self.time_label.pack()
        
        # 播放速度
        speed_frame = ctk.CTkFrame(self.playback_frame, fg_color="transparent")
        speed_frame.pack(fill="x", padx=12, pady=(8, 12))
        
        ctk.CTkLabel(
            speed_frame, 
            text="播放速度:", 
            font=ctk.CTkFont(size=FontSizes.SMALL),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(anchor="w")
        
        self.playback_speed = tk.DoubleVar(value=1.0)
        speed_slider = ctk.CTkSlider(
            speed_frame,
            from_=0.1,
            to=3.0,
            variable=self.playback_speed,
            command=self.on_speed_changed,
            progress_color=ColorScheme.PURPLE_ACCENT,
            button_color=ColorScheme.PURPLE_ACCENT
        )
        speed_slider.pack(fill="x", pady=(5, 5))
        
        self.speed_label = ctk.CTkLabel(
            speed_frame, 
            text="1.0x",
            font=ctk.CTkFont(size=FontSizes.SMALL),
            text_color=ColorScheme.TEXT_ACCENT
        )
        self.speed_label.pack()
        
        # 初始化狀態
        self.is_recording = False
        self.is_playing = False
        self.is_detecting = False
        self.camera_connected = False
        self.video_loaded = False
        
        # 隐藏錄製和回放框架（預設為實時模式）
        self.recording_frame.pack_forget()
        self.playback_frame.pack_forget()
        
        # 初始化按鈕狀態
        self.update_button_states()
    
    def create_center_panel(self, parent):
        """創建中央視頻面板"""
        center_panel = ctk.CTkFrame(parent, fg_color=ColorScheme.BG_CARD)
        center_panel.grid(row=0, column=1, sticky="nsew", padx=2, pady=0)
        
        # 配置網格權重
        center_panel.grid_rowconfigure(1, weight=1)
        center_panel.grid_columnconfigure(0, weight=1)
        
        # 視頻標題欄
        header_frame = ctk.CTkFrame(center_panel, height=50, fg_color=ColorScheme.BG_ACCENT)
        header_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        header_frame.grid_propagate(False)
        
        # 左側相機信息
        left_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_header.pack(side="left", padx=15, pady=10)
        
        self.camera_info_label = ctk.CTkLabel(
            left_header,
            text="📹 Basler acA640-300gm - 實時影像",
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold"),
            text_color=ColorScheme.TEXT_ACCENT
        )
        self.camera_info_label.pack()
        
        # 右側縮放控制
        right_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_header.pack(side="right", padx=15, pady=10)
        
        # 縮放選單
        ctk.CTkLabel(
            right_header, 
            text="🔍", 
            font=ctk.CTkFont(size=FontSizes.SUBTITLE),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left", padx=(0, 5))
        
        self.zoom_var = tk.StringVar(value="100%")
        zoom_menu = ctk.CTkOptionMenu(
            right_header,
            values=["50%", "75%", "100%", "125%", "150%"],
            variable=self.zoom_var,
            width=80,
            command=self.change_zoom,
            font=ctk.CTkFont(size=FontSizes.SMALL),
            fg_color=ColorScheme.BG_CARD,
            button_color=ColorScheme.ACCENT_BLUE,
            text_color=ColorScheme.TEXT_PRIMARY
        )
        zoom_menu.pack(side="left", padx=5)
        
        # 縮放按鈕
        zoom_buttons = ctk.CTkFrame(right_header, fg_color="transparent")
        zoom_buttons.pack(side="left", padx=10)
        
        ctk.CTkButton(
            zoom_buttons, text="+", width=32, height=26,
            command=lambda: self.zoom_change(1.25),
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.SUCCESS_GREEN,
            text_color="white"
        ).pack(side="left", padx=1)
        
        ctk.CTkButton(
            zoom_buttons, text="-", width=32, height=26,
            command=lambda: self.zoom_change(0.8),
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.WARNING_ORANGE,
            text_color="white"
        ).pack(side="left", padx=1)
        
        ctk.CTkButton(
            zoom_buttons, text="□", width=32, height=26,
            command=self.fit_to_window,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.PURPLE_ACCENT,
            text_color="white"
        ).pack(side="left", padx=1)
        
        # 視頻顯示區域
        video_container = ctk.CTkFrame(center_panel, corner_radius=8, fg_color=ColorScheme.BG_SECONDARY)
        video_container.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        video_container.grid_rowconfigure(0, weight=1)
        video_container.grid_columnconfigure(0, weight=1)
        
        # 視頻標籤
        self.video_label = ctk.CTkLabel(
            video_container,
            text="Basler acA640-300gm\n📹 Camera Ready\n配置開始捕獲取得影像",
            font=ctk.CTkFont(size=FontSizes.SUBTITLE),
            text_color=ColorScheme.TEXT_SECONDARY,
            width=640,
            height=480
        )
        self.video_label.grid(row=0, column=0, padx=15, pady=15)
        
        # 底部信息欄
        info_frame = ctk.CTkFrame(center_panel, height=45, fg_color=ColorScheme.BG_SECONDARY)
        info_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        info_frame.grid_propagate(False)
        
        # 分辨率信息
        self.resolution_label = ctk.CTkLabel(
            info_frame, 
            text="640 x 480 │ Mono8 │ 8 bit",
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.resolution_label.pack(side="left", padx=20, pady=12)
        
        # FPS 顯示區域
        fps_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        fps_frame.pack(side="right", padx=20, pady=8)
        
        # 固定寬度的FPS顯示標籤 - 加寬以容納新格式
        self.camera_fps_display = ctk.CTkLabel(
            fps_frame,
            textvariable=self.camera_fps_var,
            text_color=ColorScheme.TEXT_SUCCESS,
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold", family="monospace"),
            width=160,  # 🎯 加寬以容納 "相機: 280 fps(82.5 MB/s)" 格式
            anchor="w"  # 左對齊
        )
        self.camera_fps_display.pack(side="left", padx=5)
        
        self.processing_fps_display = ctk.CTkLabel(
            fps_frame,
            textvariable=self.processing_fps_var,
            text_color=ColorScheme.TEXT_ACCENT,
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold", family="monospace"),
            width=90,  # 🎯 適度寬度用於 "處理: 280 fps" 格式
            anchor="w"  # 左對齊
        )
        self.processing_fps_display.pack(side="left", padx=5)
        
        self.detection_fps_display = ctk.CTkLabel(
            fps_frame,
            textvariable=self.detection_fps_var,
            text_color=ColorScheme.PURPLE_ACCENT,
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold", family="monospace"),
            width=90,  # 🎯 適度寬度用於 "處理: 280 fps" 格式
            anchor="w"  # 左對齊
        )
        self.detection_fps_display.pack(side="left", padx=5)
    
    def create_right_panel(self, parent):
        """創建右側檢測面板"""
        right_panel = ctk.CTkFrame(parent, fg_color=ColorScheme.BG_CARD)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(2, 0), pady=0)
        
        # 創建可滾動框架來解決內容過多的問題
        scrollable_frame = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="transparent",
            scrollbar_button_color=ColorScheme.ACCENT_BLUE,
            scrollbar_button_hover_color=ColorScheme.PRIMARY_BLUE
        )
        scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 檢測計數標題
        ctk.CTkLabel(
            scrollable_frame,
            text="▶ 檢測計數",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.TEXT_ACCENT
        ).pack(pady=(15, 10))
        
        # 🎯 包裝計數系統顯示
        package_frame = ctk.CTkFrame(scrollable_frame, fg_color=ColorScheme.BG_ACCENT)
        package_frame.pack(fill="x", padx=12, pady=(0, 10))
        
        # 包裝數顯示
        package_header_frame = ctk.CTkFrame(package_frame, fg_color="transparent")
        package_header_frame.pack(fill="x", pady=(10, 5))
        
        ctk.CTkLabel(
            package_header_frame,
            text="📦 包裝數:",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left", padx=(15, 5))
        
        self.package_count_label = ctk.CTkLabel(
            package_header_frame,
            textvariable=self.package_count_var,
            font=ctk.CTkFont(size=FontSizes.LARGE, weight="bold"),
            text_color=ColorScheme.SUCCESS_GREEN
        )
        self.package_count_label.pack(side="left")
        
        # 當前計數顯示
        count_frame = ctk.CTkFrame(scrollable_frame, fg_color=ColorScheme.BG_ACCENT)
        count_frame.pack(fill="x", padx=12, pady=(0, 10))
        
        ctk.CTkLabel(
            count_frame, 
            text="📊 檢測計數", 
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(pady=(15, 5))
        
        # 超大數字顯示 - 顯示檢測計數（總累計與當前段一致）
        self.count_label = ctk.CTkLabel(
            count_frame,
            textvariable=self.segment_count_var,
            font=ctk.CTkFont(size=FontSizes.HUGE, weight="bold"),
            text_color=ColorScheme.PRIMARY_BLUE
        )
        self.count_label.pack(pady=(5, 15))
        
        # 目標設定區域
        target_frame = ctk.CTkFrame(scrollable_frame, fg_color=ColorScheme.BG_SECONDARY)
        target_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        ctk.CTkLabel(
            target_frame, 
            text="目標數量:", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(pady=(15, 5))
        
        self.target_entry = ctk.CTkEntry(
            target_frame,
            textvariable=self.target_count_var,
            width=120,
            height=35,
            justify="center",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.BG_CARD,
            border_color=ColorScheme.TEXT_SECONDARY,
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.target_entry.pack(pady=8)
        
        # 當目標計數變更時，更新進度標籤
        self.target_count_var.trace_add('write', self._update_progress_label)
        
        # 進度條
        self.progress_bar = ctk.CTkProgressBar(
            target_frame, 
            width=200, 
            height=20,
            progress_color=ColorScheme.SUCCESS_GREEN,
            fg_color=ColorScheme.BG_CARD
        )
        self.progress_bar.pack(pady=12, padx=15, fill="x")
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(
            target_frame, 
            text=f"0 / {self.target_count_var.get()}",  # 動態顯示目標計數
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_ACCENT
        )
        self.progress_label.pack(pady=(0, 15))
        
        # 控制按鈕
        button_frame = ctk.CTkFrame(scrollable_frame, fg_color=ColorScheme.BG_SECONDARY)
        button_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        buttons_container = ctk.CTkFrame(button_frame, fg_color="transparent")
        buttons_container.pack(pady=15)
        
        # 🎯 增強檢測按鈕 - 添加狀態指示
        self.start_detection_btn = ctk.CTkButton(
            buttons_container,
            text="▶ 開始檢測",
            command=self.start_detection,
            height=35,
            width=110,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.SUCCESS_GREEN,
            hover_color="#047857",
            text_color="white"
        )
        self.start_detection_btn.pack(side="left", padx=5)
        
        self.stop_detection_btn = ctk.CTkButton(
            buttons_container,
            text="⏸ 停止檢測",
            command=self.stop_detection,
            height=35,
            width=110,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.ERROR_RED,
            hover_color="#b91c1c",
            text_color="white",
            state="disabled"  # 初始為禁用狀態
        )
        self.stop_detection_btn.pack(side="left", padx=5)
        
        # 批次控制按鈕區域已移除 - 功能已整合到"開始檢測"按鈕中
        
        # 批次狀態顯示
        batch_status_frame = ctk.CTkFrame(scrollable_frame, fg_color=ColorScheme.BG_SECONDARY)
        batch_status_frame.pack(fill="x", padx=12, pady=(5, 15))
        
        # 輪數顯示
        ctk.CTkLabel(
            batch_status_frame,
            text="當前輪數:",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left", padx=(15, 5))
        
        self.round_count_var = ctk.StringVar(value="0")
        ctk.CTkLabel(
            batch_status_frame,
            textvariable=self.round_count_var,
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold"),
            text_color=ColorScheme.PRIMARY_BLUE
        ).pack(side="left", padx=(0, 15))
        
        # 震動機狀態
        ctk.CTkLabel(
            batch_status_frame,
            text="震動機狀態:",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left", padx=(15, 5))
        
        self.vibration_status_var = ctk.StringVar(value="未連接")
        self.vibration_status_label = ctk.CTkLabel(
            batch_status_frame,
            textvariable=self.vibration_status_var,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color="#dc2626"  # 紅色表示未連接
        )
        self.vibration_status_label.pack(side="left", padx=(0, 15))
        
        # 檢測參數標題
        ctk.CTkLabel(
            scrollable_frame,
            text="🔧 檢測參數",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.PURPLE_ACCENT
        ).pack(pady=(10, 10))
        
        # 🎯 ROI設定區域 (僅在background方法時顯示)
        self.roi_frame = ctk.CTkFrame(scrollable_frame, fg_color=ColorScheme.BG_ACCENT)
        self.roi_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        # ROI標題
        ctk.CTkLabel(
            self.roi_frame,
            text="🎯 100%準確率 ROI 設定",
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold"),
            text_color=ColorScheme.TEXT_SUCCESS
        ).pack(pady=(15, 10))
        
        # ROI高度控制
        roi_height_container = ctk.CTkFrame(self.roi_frame, fg_color="transparent")
        roi_height_container.pack(fill="x", padx=12, pady=(0, 10))
        
        ctk.CTkLabel(
            roi_height_container,
            text="ROI高度 (像素):",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left")
        
        self.roi_height_var = tk.IntVar(value=50)
        self.roi_height_entry = ctk.CTkEntry(
            roi_height_container,
            textvariable=self.roi_height_var,
            width=80,
            font=ctk.CTkFont(size=FontSizes.BODY)
        )
        self.roi_height_entry.pack(side="right", padx=(5, 0))
        self.roi_height_entry.bind('<Return>', self.update_roi_settings)
        
        # ROI位置控制  
        roi_position_container = ctk.CTkFrame(self.roi_frame, fg_color="transparent")
        roi_position_container.pack(fill="x", padx=12, pady=(0, 15))
        
        ctk.CTkLabel(
            roi_position_container,
            text="ROI位置比例:",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left")
        
        self.roi_position_var = tk.DoubleVar(value=0.1)
        self.roi_position_slider = ctk.CTkSlider(
            roi_position_container,
            from_=0.0,
            to=0.8,
            variable=self.roi_position_var,
            command=self.update_roi_settings,
            width=150,
            progress_color=ColorScheme.TEXT_SUCCESS,
            button_color=ColorScheme.TEXT_SUCCESS
        )
        self.roi_position_slider.pack(side="right", padx=(10, 0))
        
        # ROI重置按鈕
        ctk.CTkButton(
            self.roi_frame,
            text="🔄 重置計數",
            command=self.reset_crossing_count,
            width=120,
            height=32,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.WARNING_ORANGE,
            hover_color="#b45309",
            text_color="white"
        ).pack(pady=(0, 15))
        
        # 參數調整區域
        params_frame = ctk.CTkFrame(scrollable_frame, fg_color=ColorScheme.BG_SECONDARY)
        params_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        # 最小面積 - 增強版
        min_area_container = ctk.CTkFrame(params_frame, fg_color="transparent")
        min_area_container.pack(fill="x", padx=12, pady=(15, 10))
        
        # 標題和輸入框
        min_label_frame = ctk.CTkFrame(min_area_container, fg_color="transparent")
        min_label_frame.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(
            min_label_frame, 
            text="最小面積", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left")
        
        # 右側輸入控件組
        min_input_frame = ctk.CTkFrame(min_label_frame, fg_color="transparent")
        min_input_frame.pack(side="right")
        
        # 數字輸入框
        self.min_area_entry = ctk.CTkEntry(
            min_input_frame, 
            textvariable=self.min_area_var,
            width=60, height=28,
            justify="center",
            font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.BG_CARD,
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.min_area_entry.pack(side="left")
        self.min_area_entry.bind('<Return>', self.on_min_area_entry_changed)
        self.min_area_entry.bind('<FocusOut>', self.on_min_area_entry_changed)
        
        # 箭頭按鈕
        arrow_frame = ctk.CTkFrame(min_input_frame, fg_color="transparent")
        arrow_frame.pack(side="left", padx=(5, 0))
        
        ctk.CTkButton(
            arrow_frame, text="▲", width=20, height=14,
            command=lambda: self.adjust_min_area(10),
            font=ctk.CTkFont(size=10),
            fg_color=ColorScheme.SUCCESS_GREEN,
            hover_color="#047857"
        ).pack()
        
        ctk.CTkButton(
            arrow_frame, text="▼", width=20, height=14,
            command=lambda: self.adjust_min_area(-10),
            font=ctk.CTkFont(size=10),
            fg_color=ColorScheme.SUCCESS_GREEN,
            hover_color="#047857"
        ).pack()
        
        # 滑動條
        self.min_area_slider = ctk.CTkSlider(
            min_area_container,
            from_=10,
            to=500,
            variable=self.min_area_var,
            command=self.update_detection_params,
            progress_color=ColorScheme.SUCCESS_GREEN,
            button_color=ColorScheme.SUCCESS_GREEN,
            fg_color=ColorScheme.BG_CARD
        )
        self.min_area_slider.pack(fill="x", padx=8, pady=3)
        
        # 最大面積 - 增強版
        max_area_container = ctk.CTkFrame(params_frame, fg_color="transparent")
        max_area_container.pack(fill="x", padx=12, pady=(10, 15))
        
        # 標題和輸入框
        max_label_frame = ctk.CTkFrame(max_area_container, fg_color="transparent")
        max_label_frame.pack(fill="x", pady=(0, 5))
        
        ctk.CTkLabel(
            max_label_frame, 
            text="最大面積", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left")
        
        # 右側輸入控件組
        max_input_frame = ctk.CTkFrame(max_label_frame, fg_color="transparent")
        max_input_frame.pack(side="right")
        
        # 數字輸入框
        self.max_area_entry = ctk.CTkEntry(
            max_input_frame, 
            textvariable=self.max_area_var,
            width=60, height=28,
            justify="center",
            font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.BG_CARD,
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.max_area_entry.pack(side="left")
        self.max_area_entry.bind('<Return>', self.on_max_area_entry_changed)
        self.max_area_entry.bind('<FocusOut>', self.on_max_area_entry_changed)
        
        # 箭頭按鈕
        arrow_frame2 = ctk.CTkFrame(max_input_frame, fg_color="transparent")
        arrow_frame2.pack(side="left", padx=(5, 0))
        
        ctk.CTkButton(
            arrow_frame2, text="▲", width=20, height=14,
            command=lambda: self.adjust_max_area(100),
            font=ctk.CTkFont(size=10),
            fg_color=ColorScheme.WARNING_ORANGE,
            hover_color="#b45309"
        ).pack()
        
        ctk.CTkButton(
            arrow_frame2, text="▼", width=20, height=14,
            command=lambda: self.adjust_max_area(-100),
            font=ctk.CTkFont(size=10),
            fg_color=ColorScheme.WARNING_ORANGE,
            hover_color="#b45309"
        ).pack()
        
        # 滑動條
        self.max_area_slider = ctk.CTkSlider(
            max_area_container,
            from_=1000,
            to=10000,
            variable=self.max_area_var,
            command=self.update_detection_params,
            progress_color=ColorScheme.WARNING_ORANGE,
            button_color=ColorScheme.WARNING_ORANGE,
            fg_color=ColorScheme.BG_CARD
        )
        self.max_area_slider.pack(fill="x", padx=8, pady=3)
        
        # 即時統計區域 - 重點改善！
        stats_frame = ctk.CTkFrame(scrollable_frame, fg_color=ColorScheme.BG_ACCENT)
        stats_frame.pack(fill="x", padx=12, pady=(0, 20))
        
        # 統計標題 - 明顯改善
        ctk.CTkLabel(
            stats_frame,
            text="📊 即時統計",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.TEXT_SUCCESS
        ).pack(pady=(15, 10))
        
        # 檢測品質 - 大字體！
        self.quality_label = ctk.CTkLabel(
            stats_frame,
            text="檢測品質: 良好",
            text_color=ColorScheme.TEXT_SUCCESS,
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold")
        )
        self.quality_label.pack(pady=8)
        
        # 檢測 FPS - 大字體！
        self.detection_fps_stat = ctk.CTkLabel(
            stats_frame,
            textvariable=self.detection_fps_var,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.PURPLE_ACCENT
        )
        self.detection_fps_stat.pack(pady=(0, 15))
    
    def create_status_panel(self, parent):
        """創建底部狀態面板"""
        status_panel = ctk.CTkFrame(parent, height=50, fg_color=ColorScheme.BG_CARD)
        status_panel.pack(fill="x", padx=2, pady=(4, 2))
        status_panel.pack_propagate(False)
        
        # 左側狀態
        left_status = ctk.CTkFrame(status_panel, fg_color="transparent")
        left_status.pack(side="left", fill="y", padx=15, pady=10)
        
        self.status_label = ctk.CTkLabel(
            left_status,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.status_label.pack(side="left", padx=(0, 30))
        
        self.camera_info_status = ctk.CTkLabel(
            left_status,
            textvariable=self.camera_info_var,
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_ACCENT
        )
        self.camera_info_status.pack(side="left")
        
        # 🔴 錄製狀態指示器
        self.recording_indicator = ctk.CTkLabel(
            left_status,
            text="",  # 預設為空
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color="#dc2626"  # 紅色
        )
        self.recording_indicator.pack(side="left", padx=(20, 0))
        
        # 右側狀態
        right_status = ctk.CTkFrame(status_panel, fg_color="transparent")
        right_status.pack(side="right", fill="y", padx=15, pady=10)
        
        # 時間戳
        self.timestamp_label = ctk.CTkLabel(
            right_status,
            text="2025-08-07 15:09:18",
            font=ctk.CTkFont(size=FontSizes.SMALL),
            text_color=ColorScheme.TEXT_SECONDARY
        )
        self.timestamp_label.pack(side="right", padx=(20, 0))
        
        # 物件計數
        self.object_count_status = ctk.CTkLabel(
            right_status,
            text="物件: 0",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.PRIMARY_BLUE
        )
        self.object_count_status.pack(side="right", padx=(0, 20))
    
    # ==================== 事件處理函數 ====================
    
    def toggle_connection_switch(self):
        """切換連接開關"""
        self.connection_switch_on = not self.connection_switch_on
        if self.connection_switch_on:
            success = self.connect_device()
            if success:
                self.connection_switch.configure(
                    text="●", 
                    fg_color=ColorScheme.SUCCESS_GREEN,
                    text_color="white",
                    border_color=ColorScheme.SUCCESS_GREEN
                )
                self.start_processing_btn.configure(state="normal")
            else:
                self.connection_switch_on = False
        else:
            self.disconnect_device()
            self.connection_switch.configure(
                text="○", 
                fg_color=ColorScheme.BG_SECONDARY,
                text_color=ColorScheme.TEXT_PRIMARY,
                border_color=ColorScheme.TEXT_SECONDARY
            )
            self.start_processing_btn.configure(state="disabled")
    
    def toggle_processing(self):
        """切換處理狀態 - 根據當前模式"""
        try:
            current_mode = self.mode_var.get()
            
            if not self.is_processing_active:
                # 🚀 開始處理
                logging.info(f"🚀 啟動處理 - 模式: {current_mode}")
                
                success = self.controller.start_capture()
                if success:
                    self.is_processing_active = True
                    self.start_processing_btn.configure(
                        text="⏸️ 停止處理",
                        fg_color=ColorScheme.ERROR_RED
                    )
                    self.status_var.set(f"狀態: {current_mode}模式處理中...")
                    
                    # 🔧 更新所有按鈕狀態（鎖定模式切換）
                    self.update_button_states()
                    logging.info(f"✅ {current_mode}模式處理已啟動")
                else:
                    self.status_var.set("狀態: 處理啟動失敗")
                    logging.error(f"❌ {current_mode}模式處理啟動失敗")
            else:
                # 🛑 停止處理
                logging.info(f"🛑 停止處理 - 模式: {current_mode}")
                
                self.controller.stop_capture()
                self.is_processing_active = False
                self.start_processing_btn.configure(
                    text="▶️ 啟動處理",
                    fg_color=ColorScheme.ACCENT_BLUE
                )
                self.status_var.set("狀態: 處理已停止")
                
                # 🔧 更新所有按鈕狀態（解鎖模式切換）
                self.update_button_states()
                logging.info(f"✅ {current_mode}模式處理已停止")
                
        except Exception as e:
            logging.error(f"切換處理狀態錯誤: {str(e)}")
            self.status_var.set("狀態: 處理切換失敗")
            self.is_processing_active = False
            self.update_button_states()
    
    def on_method_changed(self, method):
        """檢測方法改變"""
        self.controller.set_detection_method(method)
        
        # 🎯 更新準確率指示器
        if method == "background":
            self.accuracy_indicator.configure(
                text="🎯 100%",
                text_color="#10b981"  # 綠色
            )
        elif method == "hybrid":
            self.accuracy_indicator.configure(
                text="🔄 混合",
                text_color="#f59e0b"  # 橙色
            )
        else:
            self.accuracy_indicator.configure(
                text="⚠️ 標準",
                text_color="#6b7280"  # 灰色
            )
        
        # 🖼️ 根據系統模式啟用合成調試功能
        if method == "background":
            try:
                detection_method = self.controller.detection_model.current_method
                if hasattr(detection_method, 'enable_composite_debug'):
                    # 獲取當前系統模式
                    current_mode = self.mode_var.get()
                    detection_method.enable_composite_debug(True, mode=current_mode)
                    
                    if current_mode == "playback":
                        debug_info = detection_method.get_composite_debug_info()
                        logging.info(f"🖼️ 合成調試功能已啟用 (回放模式)，保存目錄: {debug_info['save_directory']}")
                    else:
                        logging.info(f"🖼️ {current_mode}模式下調試圖片保存已禁用（性能優化）")
            except Exception as e:
                logging.warning(f"設置合成調試功能失敗: {str(e)}")
        
        logging.info(f"檢測方法已改為: {method} {'(100%準確率模式+合成調試)' if method == 'background' else ''}")
        
        # 🎯 根據方法顯示/隱藏ROI設定
        if hasattr(self, 'roi_frame'):
            if method == "background":
                self.roi_frame.pack(fill="x", padx=12, pady=(0, 15))
                # 🔄 切換到background方法時立即同步計數
                self.root.after(100, self.sync_count_display)
            else:
                self.roi_frame.pack_forget()
    
    def update_roi_settings(self, event=None):
        """更新ROI設定"""
        try:
            if self.method_var.get() == "background":
                roi_height = self.roi_height_var.get()
                roi_position = self.roi_position_var.get()
                
                # 更新檢測方法的ROI設定
                detection_method = self.controller.detection_model.current_method
                if hasattr(detection_method, 'roi_height'):
                    detection_method.roi_height = roi_height
                if hasattr(detection_method, 'roi_position_ratio'):
                    detection_method.roi_position_ratio = roi_position
                
                logging.info(f"🎯 ROI設定已更新: 高度={roi_height}px, 位置={roi_position:.2f}")
                
        except Exception as e:
            logging.error(f"更新ROI設定錯誤: {str(e)}")
    
    def reset_crossing_count(self):
        """重置穿越計數"""
        try:
            if self.method_var.get() == "background":
                detection_method = self.controller.detection_model.current_method
                if hasattr(detection_method, 'reset_crossing_count'):
                    detection_method.reset_crossing_count()
                    logging.info("🔄 穿越計數已重置")
                    
                    # 🎯 重置包裝計數系統
                    if hasattr(self.controller, 'reset_package_counting'):
                        self.controller.reset_package_counting()
                    
                    # 🎯 立即同步重置界面顯示
                    self.object_count_var.set("000")
                    self.total_count_var.set("0")
                    self.segment_count_var.set("000")
                    self.package_count_var.set("0")
                    
                    if hasattr(self, 'object_count_status'):
                        self.object_count_status.configure(text="物件: 0")
                    if hasattr(self, 'progress_bar'):
                        self.progress_bar.set(0)
                    if hasattr(self, 'progress_label'):
                        target = self.target_count_var.get()
                        self.progress_label.configure(text=f"0 / {target}")
                    
                    # 🔄 強制界面刷新
                    self.root.update_idletasks()
                        
        except Exception as e:
            logging.error(f"重置計數錯誤: {str(e)}")
    
    def sync_count_display(self):
        """同步計數顯示 - 確保進度條與累加計數一致（所有檢測方法）"""
        try:
            current_method = self.method_var.get()
            
            # 🔧 關鍵修正：處理所有檢測方法，避免進度條跳動
            if current_method == "background":
                # Background 方法：使用穿越計數
                detection_method = self.controller.detection_model.current_method
                if hasattr(detection_method, 'get_crossing_count'):
                    crossing_count = detection_method.get_crossing_count()
                    
                    target = self.target_count_var.get()
                    if target > 0:
                        progress = min(crossing_count / target, 1.0)
                        if hasattr(self, 'progress_bar'):
                            self.progress_bar.set(progress)
                        if hasattr(self, 'progress_label'):
                            # 🎯 統一顯示格式
                            if crossing_count > target:
                                self.progress_label.configure(
                                    text=f"{crossing_count} / {target} (超出)",
                                    text_color=ColorScheme.ERROR_RED
                                )
                            else:
                                self.progress_label.configure(
                                    text=f"{crossing_count} / {target}",
                                    text_color=ColorScheme.TEXT_PRIMARY
                                )
                    
                    logging.debug(f"🔄 Background累加計數同步: {crossing_count}")
            else:
                # 🎯 其他方法：保持當前進度條狀態，不重置
                # 避免每2秒重置進度條，讓 on_frame_processed 正常更新
                logging.debug(f"🔄 {current_method}方法：保持當前進度條狀態")
                    
        except Exception as e:
            logging.error(f"同步計數顯示錯誤: {str(e)}")
    
    def _update_progress_label(self, *args):
        """當目標計數變更時更新進度標籤"""
        try:
            if hasattr(self, 'progress_label'):
                current_count = 0
                # 嘗試獲取當前計數
                if hasattr(self, 'object_count_var'):
                    try:
                        current_count = int(self.object_count_var.get())
                    except (ValueError, TypeError):
                        current_count = 0
                
                target = self.target_count_var.get()
                self.progress_label.configure(text=f"{current_count} / {target}")
                
                # 同時更新進度條
                if hasattr(self, 'progress_bar') and target > 0:
                    progress = min(current_count / target, 1.0)
                    self.progress_bar.set(progress)
                    
        except Exception as e:
            logging.debug(f"更新進度標籤錯誤: {str(e)}")
    
    def on_device_selected(self, device_name):
        """設備選擇改變"""
        logging.info(f"選擇設備: {device_name}")
    
    # ==================== 🎯 設備監控和刷新功能 ====================
    
    def refresh_devices_manually(self):
        """手動刷新設備列表"""
        try:
            # 暫時禁用刷新按鈕，避免重複點擊
            self.refresh_devices_button.configure(state="disabled", text="刷新中...")
            
            # 強制刷新設備列表
            devices = self.controller.force_refresh_device_list()
            
            # 更新UI設備列表
            self._update_device_combobox(devices)
            
            # 顯示結果訊息
            if devices:
                logging.info(f"🔄 手動刷新完成，找到 {len(devices)} 台設備")
                # 臨時顯示刷新成功
                original_text = self.monitor_status_label.cget("text")
                self.monitor_status_label.configure(text="✅ 已刷新", text_color=ColorScheme.SUCCESS_GREEN)
                self.root.after(2000, lambda: self.monitor_status_label.configure(
                    text=original_text, text_color=ColorScheme.SUCCESS_GREEN
                ))
            else:
                logging.warning("⚠️ 手動刷新完成，未找到任何設備")
                # 臨時顯示未找到設備
                original_text = self.monitor_status_label.cget("text")
                self.monitor_status_label.configure(text="⚠️ 無設備", text_color=ColorScheme.WARNING_ORANGE)
                self.root.after(2000, lambda: self.monitor_status_label.configure(
                    text=original_text, text_color=ColorScheme.SUCCESS_GREEN
                ))
                
        except Exception as e:
            logging.error(f"手動刷新設備失敗: {str(e)}")
            # 顯示錯誤狀態
            original_text = self.monitor_status_label.cget("text")
            self.monitor_status_label.configure(text="❌ 刷新失敗", text_color=ColorScheme.ERROR_RED)
            self.root.after(3000, lambda: self.monitor_status_label.configure(
                text=original_text, text_color=ColorScheme.SUCCESS_GREEN
            ))
        finally:
            # 恢復刷新按鈕
            self.root.after(1000, lambda: self.refresh_devices_button.configure(
                state="normal", text="🔄 手動刷新"
            ))
    
    def _update_device_combobox(self, devices: list):
        """更新設備下拉選單"""
        try:
            if devices:
                device_names = []
                for i, camera in enumerate(devices):
                    status = "✅" if camera.get('is_target', False) else "⚠️"
                    device_name = f"{status} {camera['model']}"
                    device_names.append(device_name)
                
                # 更新下拉選單選項
                self.device_combobox.configure(values=device_names)
                
                # 如果當前沒有選擇，自動選擇第一個設備
                if self.device_combobox.get() == "未檢測到設備" or not self.device_combobox.get():
                    self.device_combobox.set(device_names[0])
                    
                # 更新內部設備列表
                self.devices = devices
                
                logging.info(f"🔄 設備列表已更新: {len(devices)} 台設備")
                
            else:
                # 沒有設備時的處理
                self.device_combobox.configure(values=["未檢測到設備"])
                self.device_combobox.set("未檢測到設備")
                self.devices = []
                
        except Exception as e:
            logging.error(f"更新設備下拉選單失敗: {str(e)}")
    
    def on_device_list_changed(self, event_type: str, data: dict):
        """處理設備列表變化事件（觀察者模式回調）"""
        try:
            if event_type == 'device_list_changed':
                current_devices = data.get('current_devices', [])
                added_devices = data.get('added_devices', [])
                removed_devices = data.get('removed_devices', [])
                
                # 記錄設備變化
                if added_devices:
                    for device in added_devices:
                        logging.info(f"🔌 新設備接入: {device['model']}")
                
                if removed_devices:
                    for device in removed_devices:
                        logging.info(f"🔌 設備斷開: {device['model']}")
                
                # 更新UI設備列表
                self._update_device_combobox(current_devices)
                
                # 更新監控狀態指示器（臨時顯示變化）
                if added_devices or removed_devices:
                    original_text = self.monitor_status_label.cget("text")
                    change_text = f"🔄 檢測到變化"
                    self.monitor_status_label.configure(text=change_text, text_color=ColorScheme.ACCENT_BLUE)
                    self.root.after(3000, lambda: self.monitor_status_label.configure(
                        text=original_text, text_color=ColorScheme.SUCCESS_GREEN
                    ))
                    
            elif event_type == 'device_list_refreshed':
                devices = data.get('devices', [])
                self._update_device_combobox(devices)
                
        except Exception as e:
            logging.error(f"處理設備列表變化事件失敗: {str(e)}")
    
    def _start_device_monitoring(self):
        """啟動設備監控功能"""
        try:
            logging.info("🔍 正在啟動設備監控...")
            
            # 檢查控制器和相機模型是否存在
            if not hasattr(self, 'controller') or not self.controller:
                logging.warning("⚠️ 控制器不存在，跳過設備監控")
                return
                
            if not hasattr(self.controller, 'camera_model') or not self.controller.camera_model:
                logging.warning("⚠️ 相機模型不存在，跳過設備監控")
                return
            
            # 啟動設備監控
            success = self.controller.start_device_monitor()
            
            if success:
                logging.info("🔍 設備監控已啟動")
                if hasattr(self, 'monitor_status_label'):
                    self.monitor_status_label.configure(
                        text="🔍 監控中", 
                        text_color=ColorScheme.SUCCESS_GREEN
                    )
            else:
                logging.warning("⚠️ 設備監控啟動失敗")
                if hasattr(self, 'monitor_status_label'):
                    self.monitor_status_label.configure(
                        text="⚠️ 監控失敗", 
                        text_color=ColorScheme.WARNING_ORANGE
                    )
                
        except Exception as e:
            logging.error(f"啟動設備監控失敗: {str(e)}")
            import traceback
            logging.debug(traceback.format_exc())
            
            if hasattr(self, 'monitor_status_label'):
                self.monitor_status_label.configure(
                    text="❌ 監控錯誤", 
                    text_color=ColorScheme.ERROR_RED
                )
    
    def _on_closing(self):
        """窗口關閉時的清理處理"""
        try:
            logging.info("🔚 正在關閉應用程序...")
            
            # 停止設備監控
            self.controller.stop_device_monitor()
            logging.info("🔍 設備監控已停止")
            
            # 停止所有相機和檢測活動
            if hasattr(self.controller, 'force_stop_all'):
                self.controller.force_stop_all()
                logging.info("📷 所有系統活動已停止")
            
            # 銷毀窗口
            self.root.destroy()
            logging.info("✅ 應用程序已安全關閉")
            
        except Exception as e:
            logging.error(f"關閉應用程序時發生錯誤: {str(e)}")
            # 強制退出
            self.root.destroy()
    
    def on_exposure_changed(self, value):
        """曝光時間改變"""
        exposure = int(float(value))
        self.exposure_label.configure(text=f"{exposure}")
        if self.connection_switch_on:
            self.controller.set_exposure_time(exposure)
    
    def change_mode(self):
        """更改系統模式"""
        mode = self.mode_var.get()
        success = self.controller.switch_mode(mode)
        if success:
            logging.info(f"系統模式已切換為: {mode}")
    
    def change_zoom(self, zoom_str):
        """更改顯示縮放"""
        zoom_percent = int(zoom_str.replace('%', ''))
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
        self.display_size = (int(640 * factor), int(480 * factor))
    
    def start_detection(self):
        """開始檢測 - 完全獨立的檢測功能，不影響影片播放"""
        try:
            # 🛡️ 防重複點擊保護
            if self.is_detecting:
                logging.warning("⚠️ 檢測已在運行中，忽略重複啟動")
                return
            
            # 🎯 立即禁用按鈕防止重複點擊
            self.start_detection_btn.configure(
                text="🔄 啟動中...", 
                state="disabled",
                fg_color=ColorScheme.WARNING_ORANGE
            )
            
            # 🔧 關鍵修復：檢測功能完全獨立，不干預播放狀態
            detection_status = "檢測啟動中"
            if self.is_playing:
                detection_status += "（影片播放不受影響）"
            
            self.status_var.set(f"狀態: {detection_status}")
            
            # 重置計數
            self.object_count_var.set("000")
            
            # 啟動檢測
            success = self.controller.start_batch_detection()
            
            if success:
                # 🎯 只有成功啟動後才設置檢測狀態
                self.is_detecting = True
                self.start_detection_btn.configure(
                    text="✅ 檢測運行中",
                    fg_color=ColorScheme.SUCCESS_GREEN
                )
                self.stop_detection_btn.configure(state="normal")
                self.status_var.set("狀態: 檢測已啟動，正在處理...")
                # 🔧 更新按鈕狀態 - 禁用模式切換和錄製
                self.update_button_states()
                logging.info("✅ 批次檢測已啟動")
            else:
                # 啟動失敗，恢復按鈕狀態
                self.start_detection_btn.configure(
                    text="▶ 開始檢測",
                    state="normal",
                    fg_color=ColorScheme.SUCCESS_GREEN
                )
                self.stop_detection_btn.configure(state="disabled")
                self.status_var.set("狀態: 檢測啟動失敗")
                self.update_button_states()
                logging.error("❌ 批次檢測啟動失敗")
                
        except Exception as e:
            logging.error(f"啟動檢測時出錯: {str(e)}")
            # 出錯時還原狀態
            self.is_detecting = False
            self.start_detection_btn.configure(
                text="▶ 開始檢測",
                state="normal", 
                fg_color=ColorScheme.SUCCESS_GREEN
            )
            self.stop_detection_btn.configure(state="disabled")
            self.status_var.set("狀態: 檢測啟動出錯")
            self.update_button_states()
    
    def stop_detection(self):
        """🔧 停止檢測 - 改善線程停止機制"""
        try:
            # 🎯 先顯示停止狀態，但不改變 is_detecting
            self.stop_detection_btn.configure(
                text="🔄 停止中...",
                state="disabled"
            )
            self.status_var.set("狀態: 正在停止檢測...")
            
            # 🔧 記錄原始狀態以便恢復
            original_detecting_state = self.is_detecting
            
            # 🔧 給UI一點時間更新，避免界面卡住
            self.root.update_idletasks()
            
            # 停止檢測 - 使用更長的超時時間
            logging.info("🔄 開始停止檢測程序...")
            success = self.controller.stop_batch_detection()
            
            # 🎯 根據停止結果更新狀態
            if success:
                # 停止成功 - 完全重置狀態
                self.is_detecting = False
                self.status_var.set("狀態: 檢測已停止")
                logging.info("✅ 批次檢測已停止")
                
                # 🔧 額外確認：檢查相機是否真的停止了
                if hasattr(self.controller, 'camera_model') and self.controller.camera_model:
                    if self.controller.camera_model.is_grabbing:
                        logging.warning("⚠️ 相機仍在捕獲中，強制狀態同步")
                        self.is_detecting = True  # 保持檢測狀態
                        self.status_var.set("狀態: 檢測停止未完成")
            else:
                # 停止失敗 - 恢復原始狀態
                self.is_detecting = original_detecting_state
                self.status_var.set("狀態: 檢測停止失敗")
                logging.error("❌ 批次檢測停止失敗")
            
            # 🔧 關鍵修復：延遲更新按鈕狀態，避免立即觸發其他狀態檢查
            # 使用 after 方法延遲執行，避免在停止過程中觸發衝突
            self.root.after(100, self._delayed_button_state_update)
            
            # 🔧 額外的恢復檢查
            if not self.is_detecting:
                # 確保停止按鈕被正確禁用
                self.stop_detection_btn.configure(
                    text="⏸ 停止檢測",
                    state="disabled"
                )
                # 確保開始按鈕可用
                if (hasattr(self.controller, 'camera_model') and 
                    self.controller.camera_model and 
                    self.controller.camera_model.is_connected):
                    self.start_detection_btn.configure(
                        text="▶ 開始檢測",
                        state="normal",
                        fg_color=ColorScheme.SUCCESS_GREEN
                    )
            
        except Exception as e:
            logging.error(f"停止檢測時出錯: {str(e)}")
            # 出錯時強制重置狀態
            self.is_detecting = False
            self.status_var.set("狀態: 停止檢測出錯，已重置")
            self.update_button_states()
    
    def _delayed_button_state_update(self):
        """🔧 延遲的按鈕狀態更新，避免在停止檢測時的狀態衝突"""
        try:
            # 檢查UI是否仍然有效
            if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                self.update_button_states()
            else:
                logging.debug("UI已銷毀，跳過延遲按鈕狀態更新")
        except Exception as e:
            logging.debug(f"延遲按鈕狀態更新失敗: {str(e)}")
    
    def reset_count(self):
        """重置計數"""
        self.object_count_var.set("000")
        self.progress_bar.set(0)
    
    def force_reset_all_states(self):
        """強制重置所有狀態 - 當系統卡住時使用"""
        try:
            logging.warning("🔥 執行強制狀態重置...")
            
            # 🔧 強制重置內部狀態
            self.is_detecting = False
            self.is_recording = False
            
            # 🔧 重置按鈕狀態
            try:
                if hasattr(self, 'start_detection_btn') and self.start_detection_btn:
                    self.start_detection_btn.configure(
                        text="▶ 開始檢測",
                        state="normal",
                        fg_color=ColorScheme.SUCCESS_GREEN
                    )
                    
                if hasattr(self, 'stop_detection_btn') and self.stop_detection_btn:
                    self.stop_detection_btn.configure(
                        text="⏸ 停止檢測",
                        state="disabled"
                    )
                    
                if hasattr(self, 'record_button') and self.record_button:
                    self.record_button.configure(
                        text="🔴 開始錄製",
                        state="normal",
                        fg_color=ColorScheme.ERROR_RED
                    )
            except Exception as e:
                logging.error(f"重置按鈕狀態失敗: {str(e)}")
            
            # 🔧 嘗試強制停止控制器
            try:
                if hasattr(self, 'controller') and self.controller:
                    # 強制停止相機
                    if (hasattr(self.controller, 'camera_model') and 
                        self.controller.camera_model):
                        self.controller.camera_model.stop_capture()
                    
                    # 強制停止處理循環
                    if hasattr(self.controller, '_stop_processing'):
                        self.controller._stop_processing()
            except Exception as e:
                logging.error(f"強制停止控制器失敗: {str(e)}")
            
            # 🔧 更新狀態顯示
            self.status_var.set("狀態: 已強制重置，請重新開始")
            
            # 🔧 更新所有按鈕狀態
            self.update_button_states()
            
            logging.info("✅ 強制狀態重置完成")
            
        except Exception as e:
            logging.error(f"強制重置失敗: {str(e)}")
            self.status_var.set("狀態: 重置失敗，建議重啟程式")
    
    def update_detection_params(self, value):
        """更新檢測參數"""
        try:
            min_area = int(self.min_area_var.get())
            max_area = int(self.max_area_var.get())
            
            # 🔧 安全檢查：只有當標籤存在時才更新
            if hasattr(self, 'min_area_label') and self.min_area_label:
                self.min_area_label.configure(text=str(min_area))
            if hasattr(self, 'max_area_label') and self.max_area_label:
                self.max_area_label.configure(text=str(max_area))
            
            params = {'min_area': min_area, 'max_area': max_area}
            self.controller.update_detection_parameters(params)
        except Exception as e:
            logging.error(f"更新檢測參數錯誤: {str(e)}")
    
    def toggle_detection(self):
        """切換檢測開關"""
        try:
            enabled = self.enable_detection_var.get()
            self.controller.toggle_detection(enabled)
            logging.info(f"✅ 檢測開關已切換為: {'開啟' if enabled else '關閉'}")
        except Exception as e:
            logging.error(f"❌ 切換檢測開關時出錯: {str(e)}")
            # 重置開關狀態
            self.enable_detection_var.set(not self.enable_detection_var.get())
            messagebox.showerror("錯誤", f"切換檢測開關失敗: {str(e)}")
    
    def open_settings(self):
        """開啟設定"""
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
                    device_name = f"{status} {camera['model']}"
                    device_names.append(device_name)
                
                self.device_combobox.configure(values=device_names)
                self.device_combobox.set(device_names[0])
            else:
                self.device_combobox.configure(values=["未檢測到設備"])
                self.device_combobox.set("未檢測到設備")
                
        except Exception as e:
            logging.error(f"刷新設備列表失敗: {str(e)}")
    
    def connect_device(self) -> bool:
        """連接設備"""
        try:
            if not self.devices:
                messagebox.showwarning("警告", "沒有檢測到可用設備")
                return False
            
            success = self.controller.connect_camera(0)
            if success:
                self.update_connection_ui()
                return True
            else:
                messagebox.showerror("錯誤", "相機連接失敗")
                return False
                
        except Exception as e:
            logging.error(f"連接設備錯誤: {str(e)}")
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
            # 🔧 修復：更新相機連接狀態變量
            self.camera_connected = True
            self.connection_status.configure(
                text="● 已連接", 
                text_color=ColorScheme.TEXT_SUCCESS
            )
            self.camera_info_var.set("相機: 已連接")
            self.start_processing_btn.configure(state="normal")
        else:
            # 🔧 修復：更新相機連接狀態變量
            self.camera_connected = False
            self.connection_status.configure(
                text="● 未連接", 
                text_color=ColorScheme.TEXT_ERROR
            )
            self.camera_info_var.set("相機: 未連接")
            self.start_processing_btn.configure(state="disabled")
        
        # 🎯 重要：更新按鈕狀態以反映新的連接狀態
        self.update_button_states()
    
    def initialize_display_status(self):
        """初始化顯示狀態"""
        self.status_var.set("狀態: 系統就緒")
        self.update_connection_ui()
        self.update_timestamp()
        
        # 🎯 啟動計數同步 (每2秒同步一次)
        self.sync_count_timer()
    
    def update_timestamp(self):
        """更新時間戳"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.timestamp_label.configure(text=current_time)
        self.root.after(1000, self.update_timestamp)
    
    def sync_count_timer(self):
        """定期同步計數顯示"""
        try:
            # 每2秒同步一次計數
            self.sync_count_display()
            self.root.after(2000, self.sync_count_timer)
        except Exception as e:
            logging.error(f"同步計數定時器錯誤: {str(e)}")
            # 出錯後仍然繼續定時器
            self.root.after(2000, self.sync_count_timer)
    
    # ==================== 顯示更新 ====================
    
    def update_frame(self, frame):
        """更新視頻幀顯示 - 包含ROI和檢測結果"""
        try:
            import cv2  # 🔧 移到方法開頭，確保整個方法都能使用
            
            with self.frame_lock:
                if frame is None:
                    return
                
                height, width = frame.shape[:2]
                display_width, display_height = self.display_size
                
                # 🎯 繪製ROI區域和檢測結果
                frame_with_overlay = self._draw_detection_overlay(frame.copy())
                
                if len(frame_with_overlay.shape) == 3:
                    frame_rgb = cv2.cvtColor(frame_with_overlay, cv2.COLOR_BGR2RGB)
                else:
                    frame_rgb = cv2.cvtColor(frame_with_overlay, cv2.COLOR_GRAY2RGB)
                
                frame_resized = cv2.resize(frame_rgb, (display_width, display_height))
                
                pil_image = Image.fromarray(frame_resized)
                photo = ImageTk.PhotoImage(pil_image)
                
                self.video_label.configure(image=photo, text="")
                self.video_label.image = photo
                self.current_frame = frame
                
        except Exception as e:
            logging.error(f"更新幀顯示錯誤: {str(e)}")
    
    def _draw_detection_overlay(self, frame):
        """繪製ROI區域和檢測結果覆蓋層"""
        try:
            import cv2
            
            if frame is None:
                return frame
            
            height, width = frame.shape[:2]
            
            # 🎯 繪製ROI區域 (僅當使用background方法時)
            if self.method_var.get() == "background":
                # 獲取ROI設定
                try:
                    detection_method = self.controller.detection_model.current_method
                    if hasattr(detection_method, 'roi_enabled') and detection_method.roi_enabled:
                        roi_height = getattr(detection_method, 'roi_height', 50)
                        roi_position_ratio = getattr(detection_method, 'roi_position_ratio', 0.1)
                        
                        # 計算ROI位置
                        roi_y = int(height * roi_position_ratio)
                        roi_bottom = roi_y + roi_height
                        
                        # 繪製ROI區域 (綠色半透明矩形)
                        overlay = frame.copy()
                        cv2.rectangle(overlay, (0, roi_y), (width, roi_bottom), (0, 255, 0), -1)
                        frame = cv2.addWeighted(frame, 0.8, overlay, 0.2, 0)
                        
                        # 繪製ROI邊界線 (亮綠色)
                        cv2.line(frame, (0, roi_y), (width, roi_y), (0, 255, 0), 2)
                        cv2.line(frame, (0, roi_bottom), (width, roi_bottom), (0, 255, 0), 2)
                        
                        # 添加ROI標籤
                        cv2.putText(frame, f"ROI ({roi_height}px)", (10, roi_y - 10), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                        # 移除重複的影像計數顯示，只使用右側面板計數
                        # 注釋掉重複的黃色計數顯示
                        # if hasattr(detection_method, 'get_crossing_count'):
                        #     count = detection_method.get_crossing_count()
                        #     cv2.putText(frame, f"Count: {count:03d}", (10, 40), 
                        #               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)
                        
                except Exception as roi_error:
                    logging.debug(f"ROI繪製錯誤: {str(roi_error)}")
            
            # 🔍 為其他檢測方法顯示基本計數
            else:
                # 對於非background方法，顯示基本物件計數
                try:
                    count_text = self.object_count_var.get()
                    cv2.putText(frame, f"Objects: {count_text}", (10, 40), 
                              cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 3)
                except:
                    pass
            
            return frame
            
        except Exception as e:
            logging.error(f"繪製檢測覆蓋層錯誤: {str(e)}")
            return frame
    
    def on_controller_event(self, event_type: str, data: Any = None):
        """🔧 處理控制器事件 - 安全的UI更新機制"""
        try:
            # 🔧 關鍵修復：在處理任何事件前檢查UI狀態
            if not hasattr(self, 'root') or not self.root:
                logging.debug("UI根組件不存在，跳過事件處理")
                return
                
            # 檢查UI是否仍然有效
            try:
                if not self.root.winfo_exists():
                    logging.debug("UI根組件已銷毀，跳過事件處理")
                    return
            except:
                logging.debug("UI應用已銷毀，跳過事件處理")
                return
                
            if event_type == 'frame_processed':
                if data and 'frame' in data:
                    self.update_frame(data['frame'])
                    
                # 🎯 包裝計數系統顯示邏輯
                if 'crossing_count' in data:
                    # background方法：使用穿越計數作為主要顯示
                    crossing_count = data['crossing_count']
                    
                    # 🎯 更新包裝計數系統顯示 - 確保總累計與當前段顯示一致
                    if 'current_segment_count' in data:
                        count_value = data['current_segment_count']
                        # 🔧 安全的UI更新：檢查組件是否存在
                        if hasattr(self, 'total_count_var') and self.total_count_var:
                            self.total_count_var.set(f"{count_value:03d}")
                        if hasattr(self, 'segment_count_var') and self.segment_count_var:
                            self.segment_count_var.set(f"{count_value:03d}")
                    
                    if 'package_count' in data:
                        if hasattr(self, 'package_count_var') and self.package_count_var:
                            self.package_count_var.set(str(data['package_count']))
                    
                    # 🔍 強制顯示實時檢測數 + 累積穿越數
                    frame_objects = data.get('object_count', 0)  # 每幀檢測數
                    objects_list = data.get('objects', [])       # 檢測物件列表
                    real_count = max(frame_objects, len(objects_list))  # 確保計數正確
                    
                    # 🔧 安全的UI更新：檢查組件是否存在且有效
                    if hasattr(self, 'object_count_var') and self.object_count_var:
                        self.object_count_var.set(f"{real_count:03d}")
                    if hasattr(self, 'object_count_status') and self.object_count_status:
                        try:
                            self.object_count_status.configure(text=f"🔍檢測: {real_count} | 📊累積: {crossing_count}")
                        except Exception as status_error:
                            logging.debug(f"狀態標籤更新失敗: {str(status_error)}")
                    
                    # 🔍 調試：每10幀記錄一次實時數據
                    if hasattr(self, '_debug_counter'):
                        self._debug_counter += 1
                    else:
                        self._debug_counter = 1
                    
                    if self._debug_counter % 10 == 0:
                        logging.debug(f"UI更新: 檢測={real_count}, 累積={crossing_count}, 原始objects={len(objects_list)}")
                    
                    # 更新總計數（用於批次記錄）
                    if hasattr(self, 'is_calculating') and self.is_calculating:
                        self.total_count = crossing_count
                    
                    # 🔧 進度條更新已移至統一邏輯處理，避免重複更新
                
                elif 'object_count' in data:
                    # 🎯 只更新右側面板顯示，不影響進度條
                    frame_count = data['object_count']
                    
                    # 右側面板顯示每幀檢測數
                    self.object_count_var.set(f"{frame_count:03d}")
                    self.object_count_status.configure(text=f"物件: {frame_count}")
                
                # 🎯 統一進度條更新邏輯：只使用累計計數
                cumulative_count = 0
                if 'crossing_count' in data and data['crossing_count'] is not None:
                    cumulative_count = data['crossing_count']
                elif 'total_detected_count' in data and data['total_detected_count'] is not None:
                    cumulative_count = data['total_detected_count']
                
                # 只有累計計數大於0時才更新進度條
                if cumulative_count > 0:
                    target = self.target_count_var.get()
                    if target > 0:
                        progress = min(cumulative_count / target, 1.0)
                        self.progress_bar.set(progress)
                        
                        # 更新進度標籤
                        if cumulative_count > target:
                            self.progress_label.configure(
                                text=f"{cumulative_count} / {target} (超出)",
                                text_color=ColorScheme.ERROR_RED
                            )
                        else:
                            self.progress_label.configure(
                                text=f"{cumulative_count} / {target}",
                                text_color=ColorScheme.TEXT_PRIMARY
                            )
                        
                        # 更新總計數（用於批次記錄）
                        if hasattr(self, 'is_calculating') and self.is_calculating:
                            self.total_count = cumulative_count
                            
                            # 🌀 自適應震動頻率調整
                            self.adjust_vibration_frequency(target, cumulative_count)
                            
                            # 檢查是否接近目標數量
                            if cumulative_count >= target * 0.95:  # 達到95%時開始準備
                                logging.info(f"📊 接近目標數量 ({cumulative_count}/{target})，準備完成本輪")
                                if cumulative_count >= target:
                                    # 達到目標，完成本輪
                                    self.complete_current_round()
                
                # 🎯 更新視頻播放進度
                if 'progress' in data and hasattr(self, 'video_progress'):
                    progress = data['progress']
                    self._updating_progress = True
                    try:
                        self.video_progress.set(progress)
                    finally:
                        self._updating_progress = False
                
                # 🎯 更新時間顯示
                if 'timestamp' in data and hasattr(self, 'time_label'):
                    timestamp = data.get('timestamp', 0)
                    video_status = self.controller.get_video_player_status()
                    time_format = video_status.get('time_format', '00:00 / 00:00')
                    self.time_label.configure(text=time_format)
                
                # 使用控制器的FPS更新
                if 'processing_fps' in data:
                    fps = data['processing_fps']
                    self.update_fps_display('processing', fps)
                
                if 'detection_fps' in data:
                    fps = data['detection_fps']
                    self.update_fps_display('detection', fps)
                    
            elif event_type == 'camera_stats_updated':
                if data and 'current_fps' in data:
                    fps = data['current_fps']
                    self.update_fps_display('camera', fps)
                    
            elif event_type == 'system_status':
                if data:
                    self.status_var.set(f"狀態: {data}")
                    
            elif event_type == 'system_error':
                if data:
                    self.status_var.set(f"錯誤: {data}")
            
            # 🎯 新增：相機連接狀態事件
            elif event_type == 'camera_connected':
                self.camera_connected = True
                logging.info("✅ 相機已連接")
                self.status_var.set("狀態: 相機已連接，可以開始檢測")
                self.update_button_states()
                
            elif event_type == 'camera_disconnected':
                self.camera_connected = False
                logging.info("❌ 相機已斷開")
                self.status_var.set("狀態: 相機已斷開連接")
                self.update_button_states()
            
            # 🎯 新增：視頻播放器事件處理
            elif event_type == 'player_video_loaded':
                self.video_loaded = True
                # 🔧 重要：重置播放狀態，確保UI與實際狀態同步
                self.is_playing = False
                if hasattr(self, 'play_btn'):
                    self.play_btn.configure(text="▶️")
                    
                if data:
                    video_name = data.get('filename', '未知視頻')
                    logging.info(f"✅ 視頻已加載: {video_name}")
                    self.status_var.set(f"狀態: 視頻已加載 - {video_name}")
                else:
                    logging.info("✅ 視頻已加載")
                    self.status_var.set("狀態: 視頻已加載，可以開始回放")
                self.update_button_states()
                
            elif event_type == 'player_playback_finished':
                logging.info("🏁 視頻播放完成")
                self.status_var.set("狀態: 視頻播放完成，可重新播放")
                self.is_playing = False
                if hasattr(self, 'play_btn'):
                    self.play_btn.configure(text="▶ 重播")
                # 重置進度條到開始位置，準備重新播放
                if hasattr(self, 'video_progress'):
                    self._updating_progress = True
                    try:
                        self.video_progress.set(0.0)
                        # 重置視頻到開始位置
                        self.controller.seek_video_to_progress(0.0)
                    finally:
                        self._updating_progress = False
                # 注意：播放完成後視頻仍然加載，只是停止播放
                # 不要設置 self.video_loaded = False
            
            elif event_type == 'player_playback_started':
                logging.info("▶️ 視頻播放已開始")
                self.status_var.set("狀態: 視頻播放中")
                self.is_playing = True
                if hasattr(self, 'play_btn'):
                    self.play_btn.configure(text="⏸️")
            
            elif event_type == 'player_playback_paused':
                logging.info("⏸️ 視頻播放已暫停")
                self.status_var.set("狀態: 視頻播放已暫停")
                self.is_playing = False
                if hasattr(self, 'play_btn'):
                    self.play_btn.configure(text="▶️")
                    
            elif event_type == 'player_playback_resumed':
                logging.info("▶️ 視頻播放已恢復")
                self.status_var.set("狀態: 視頻播放中")
                self.is_playing = True
                if hasattr(self, 'play_btn'):
                    self.play_btn.configure(text="⏸️")
                    
            elif event_type == 'player_playback_stopped':
                logging.info("⏹️ 視頻播放已停止")
                self.status_var.set("狀態: 視頻播放已停止")
                self.is_playing = False
                if hasattr(self, 'play_btn'):
                    self.play_btn.configure(text="▶️")
                    
        except Exception as e:
            logging.error(f"處理控制器事件錯誤: {str(e)}")
    
    # 新增的功能方法
    
    def update_button_states(self):
        """🎯 統一的按鈕狀態管理 - 根據系統狀態智能啟用/禁用按鈕"""
        try:
            # 🔧 更嚴格的安全檢查：確保UI組件存在且有效
            if not hasattr(self, 'root') or not self.root:
                logging.debug("UI根組件不存在，跳過按鈕狀態更新")
                return
                
            # 🎯 檢查核心狀態屬性是否存在（防止初始化順序問題）
            required_attrs = ['is_detecting', 'is_recording', 'is_playing', 'camera_connected', 'video_loaded']
            for attr in required_attrs:
                if not hasattr(self, attr):
                    logging.debug(f"狀態屬性 {attr} 不存在，跳過按鈕狀態更新")
                    return
                
            try:
                # 檢查root是否還存在
                if not self.root.winfo_exists():
                    logging.debug("UI根組件已銷毀，跳過按鈕狀態更新")
                    return
            except:
                # winfo_exists() 本身可能會拋出異常如果應用已銷毀
                logging.debug("UI應用已銷毀，跳過按鈕狀態更新")
                return
                
            current_mode = self.mode_var.get()
            
            # 🎯 檢查是否有任何處理正在運行 - 分離播放和檢測狀態
            is_processing_running = (hasattr(self.controller, 'is_running') and self.controller.is_running)
            is_live_running = (current_mode == "live" and self.is_detecting)
            is_recording_running = (current_mode == "recording" and is_processing_running)
            
            # 🔧 關鍵修復：播放狀態與檢測狀態完全分離
            # 播放功能：純粹的影片播放控制
            # 檢測功能：獨立的檢測算法開關
            
            # 📹 檢測按鈕邏輯 - 添加屬性檢查避免初始化順序問題
            can_detect = False
            detect_tooltip = ""
            
            if current_mode == "live" and self.camera_connected:
                can_detect = True
            elif current_mode == "playback" and self.video_loaded:
                can_detect = True
            elif current_mode == "live" and not self.camera_connected:
                detect_tooltip = "需要連接相機才能開始檢測"
            elif current_mode == "playback" and not self.video_loaded:
                detect_tooltip = "需要選擇視頻檔案才能開始檢測"
            
            # 🔧 簡化的按鈕更新邏輯，避免winfo_exists調用
            try:
                if (hasattr(self, 'start_detection_btn') and 
                    self.start_detection_btn is not None):
                    # 🔧 關鍵修復：檢測功能與播放功能完全分離
                    # 檢測按鈕：控制檢測算法的啟用/禁用
                    # 播放按鈕：控制影片的播放/暫停
                    # 兩者互不干擾，可以獨立操作
                    if can_detect and not self.is_detecting:
                        # 在 playback 模式下，檢測是在視頻上進行物件檢測
                        if current_mode == "playback":
                            detect_text = "🔍 視頻檢測"
                        else:
                            detect_text = "▶ 開始檢測"
                        
                        self.start_detection_btn.configure(
                            state="normal",
                            fg_color=ColorScheme.SUCCESS_GREEN,
                            text=detect_text
                        )
                    elif not can_detect:
                        self.start_detection_btn.configure(
                            state="disabled",
                            fg_color="#666666",  # 灰色
                            text="❌ 無影像源"
                        )
            except Exception as e:
                logging.debug(f"更新開始檢測按鈕失敗: {str(e)}")
            
            # 停止檢測按鈕
            try:
                if (hasattr(self, 'stop_detection_btn') and 
                    self.stop_detection_btn is not None):
                    if self.is_detecting:
                        self.stop_detection_btn.configure(state="normal")
                    else:
                        self.stop_detection_btn.configure(state="disabled")
            except Exception as e:
                logging.debug(f"更新停止檢測按鈕失敗: {str(e)}")
            

            # 🎥 錄製按鈕邏輯（實時模式）
            if hasattr(self, 'record_button'):
                if is_live_running and not self.is_recording:
                    # 🚫 即時影像運行時禁用錄製功能
                    self.record_button.configure(
                        state="disabled",
                        text="⛔ 請先停止檢測",
                        fg_color="#666666"
                    )
                elif current_mode == "live" and self.camera_connected and not self.is_recording and not is_live_running:
                    self.record_button.configure(
                        state="normal",
                        text="🔴 開始錄製",
                        fg_color=ColorScheme.ERROR_RED
                    )
                elif current_mode == "live" and not self.camera_connected:
                    self.record_button.configure(
                        state="disabled",
                        text="❌ 無相機",
                        fg_color="#666666"
                    )
                elif current_mode != "live":
                    self.record_button.configure(
                        state="disabled", 
                        text="⛔ 僅限實時模式",
                        fg_color="#666666"
                    )
                elif self.is_recording:
                    # 錄製中狀態
                    self.record_button.configure(
                        state="normal",
                        text="⏹ 停止錄製",
                        fg_color=ColorScheme.WARNING_ORANGE
                    )
            
            # 🎬 模式切換按鈕控制 - 任何處理運行時禁用模式切換
            try:
                mode_buttons = [
                    ('mode_live', '實時'),
                    ('mode_recording', '錄製'),
                    ('mode_playback', '回放')
                ]
                
                for button_attr, mode_name in mode_buttons:
                    if hasattr(self, button_attr):
                        button = getattr(self, button_attr)
                        if button is not None:
                            if is_processing_running or is_live_running or is_recording_running:
                                # 🔒 任何處理運行時，只允許當前模式可選，其他禁用
                                current_button_mode = button_attr.replace('mode_', '')
                                if current_button_mode == current_mode:
                                    button.configure(state="normal")
                                else:
                                    button.configure(state="disabled")
                            else:
                                # 正常情況下所有模式都可選
                                button.configure(state="normal")
            except Exception as e:
                logging.debug(f"更新模式按鈕失敗: {str(e)}")
            
            # 🔴 更新底部錄製指示器
            try:
                if hasattr(self, 'recording_indicator'):
                    current_mode = getattr(self, 'mode_var', tk.StringVar()).get()
                    is_recording_mode = (current_mode == "recording")
                    is_processing_active = (hasattr(self.controller, 'is_running') and 
                                           self.controller.is_running)
                    
                    if is_recording_mode and is_processing_active:
                        # 錄製中 - 啟動定時器更新
                        if not self.recording_timer_active:
                            self.recording_timer_active = True
                            self.update_recording_timer()  # 立即開始更新
                    else:
                        # 非錄製狀態 - 停止定時器並隱藏指示器
                        self.recording_timer_active = False
                        self.recording_indicator.configure(text="")
            except Exception as e:
                logging.debug(f"更新錄製指示器失敗: {str(e)}")
            
            # 🎬 視頻播放相關按鈕 - 即時影像運行時禁用
            try:
                if hasattr(self, 'play_btn') and self.play_btn is not None:
                    if is_live_running:
                        # 即時影像運行時禁用播放按鈕
                        self.play_btn.configure(
                            state="disabled",
                            text="⛔ 即時檢測中"
                        )
                    elif current_mode == "playback":
                        if self.video_loaded:
                            # 🎬 根據實際播放狀態設置按鈕文字，但不影響檢測功能
                            if hasattr(self, 'is_playing') and self.is_playing:
                                play_text = "⏸️ 暫停"
                            else:
                                play_text = "▶ 播放"
                            self.play_btn.configure(
                                state="normal",
                                text=play_text
                            )
                        else:
                            self.play_btn.configure(
                                state="disabled",
                                text="❌ 無視頻"
                            )
                    else:
                        self.play_btn.configure(
                            state="disabled",
                            text="⛔ 僅限回放模式"
                        )
            except Exception as e:
                logging.debug(f"更新播放按鈕失敗: {str(e)}")
            
            # 📊 狀態提示更新
            if not self.camera_connected and not self.video_loaded:
                self.status_var.set("狀態: 請連接相機或選擇視頻檔案")
            elif current_mode == "live" and not self.camera_connected:
                self.status_var.set("狀態: 請連接相機以開始檢測")
            elif current_mode == "playback" and not self.video_loaded:
                self.status_var.set("狀態: 請選擇視頻檔案以開始回放")
                
        except Exception as e:
            logging.error(f"更新按鈕狀態時出錯: {str(e)}")

    def update_fps_display(self, fps_type, fps_value):
        """控制FPS顯示更新頻率和格式 - 美觀版本"""
        import time
        current_time = time.time()
        
        # 只有超過更新間隔才更新顯示
        if current_time - self.last_fps_update < self.fps_update_interval:
            return
        
        self.last_fps_update = current_time
        
        # 🎯 美觀格式：中文標籤 + 數字 fps(MB/s)
        if fps_type == 'camera' and fps_value > 0:
            # Basler acA640-300gm: 640x480 Mono8 = 307,200 bytes per frame
            bytes_per_frame = 640 * 480 * 1  # Mono8 = 1 byte per pixel
            bytes_per_second = bytes_per_frame * fps_value
            mb_per_second = bytes_per_second / (1024 * 1024)  # Convert to MB/s
            
            # 格式化顯示（包含中文標籤）
            if fps_value >= 100:
                display_text = f"相機: {fps_value:.0f} fps({mb_per_second:.1f} MB/s)"
            else:
                display_text = f"相機: {fps_value:.1f} fps({mb_per_second:.1f} MB/s)"
            
            self.camera_fps_var.set(display_text)
            
        elif fps_type == 'processing':
            # 處理FPS（包含中文標籤）
            if fps_value >= 100:
                display_text = f"處理: {fps_value:.0f} fps"
            else:
                display_text = f"處理: {fps_value:.1f} fps"
            self.processing_fps_var.set(display_text)
            
        elif fps_type == 'detection':
            # 檢測FPS（包含中文標籤）
            if fps_value >= 100:
                display_text = f"檢測: {fps_value:.0f} fps"
            else:
                display_text = f"檢測: {fps_value:.1f} fps"
            self.detection_fps_var.set(display_text)
    
    def adjust_exposure(self, delta):
        """調整曝光時間"""
        current = self.exposure_var.get()
        new_value = max(100, min(10000, current + delta))
        self.exposure_var.set(new_value)
        self.on_exposure_changed(new_value)
    
    def on_exposure_entry_changed(self, event=None):
        """曝光時間輸入框變化回調"""
        try:
            exposure = self.exposure_var.get()
            if exposure < 100 or exposure > 10000:
                self.exposure_var.set(max(100, min(10000, exposure)))
                return
            self.on_exposure_changed(exposure)
        except (ValueError, TypeError):
            self.exposure_var.set(1000)  # 預設值
    
    def adjust_min_area(self, delta):
        """調整最小面積"""
        current = self.min_area_var.get()
        new_value = max(1, min(1000, current + delta))
        self.min_area_var.set(new_value)
        self.update_detection_params(new_value)
    
    def adjust_max_area(self, delta):
        """調整最大面積"""
        current = self.max_area_var.get()
        new_value = max(1000, min(10000, current + delta))
        self.max_area_var.set(new_value)
        self.update_detection_params(new_value)
    
    def on_min_area_entry_changed(self, event=None):
        """最小面積輸入框變化回調"""
        try:
            min_area = self.min_area_var.get()
            if min_area < 1 or min_area > 1000:
                self.min_area_var.set(max(1, min(1000, min_area)))
                return
            self.update_detection_params(min_area)
        except (ValueError, TypeError):
            self.min_area_var.set(100)  # 預設值
    
    def on_max_area_entry_changed(self, event=None):
        """最大面積輸入框變化回調"""
        try:
            max_area = self.max_area_var.get()
            if max_area < 1000 or max_area > 10000:
                self.max_area_var.set(max(1000, min(10000, max_area)))
                return
            self.update_detection_params(max_area)
        except (ValueError, TypeError):
            self.max_area_var.set(5000)  # 預設值
    
    def generate_recording_filename(self):
        """產生錄製檔案名稱"""
        import datetime
        now = datetime.datetime.now()
        return f"recording_{now.strftime('%Y%m%d_%H%M%S')}.avi"
    
    def get_recording_time(self):
        """獲取錄製時間"""
        try:
            if (hasattr(self.controller, 'camera_model') and 
                hasattr(self.controller.camera_model, 'video_recorder') and
                self.controller.camera_model.video_recorder and
                hasattr(self.controller.camera_model.video_recorder, 'recording_start_time') and
                self.controller.camera_model.video_recorder.recording_start_time):
                
                import time
                elapsed = time.time() - self.controller.camera_model.video_recorder.recording_start_time
                
                # 格式化為 MM:SS
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                return f"{minutes:02d}:{seconds:02d}"
            else:
                return "00:00"
        except Exception:
            return "00:00"
    
    def update_recording_timer(self):
        """更新錄製計時器 - 每秒調用"""
        try:
            if hasattr(self, 'recording_indicator') and self.recording_timer_active:
                current_mode = getattr(self, 'mode_var', tk.StringVar()).get()
                is_recording_mode = (current_mode == "recording")
                is_processing_active = (hasattr(self.controller, 'is_running') and 
                                       self.controller.is_running)
                
                if is_recording_mode and is_processing_active:
                    # 錄製中 - 更新時間顯示
                    recording_time = self.get_recording_time()
                    self.recording_indicator.configure(text=f"🔴 錄製中 {recording_time}")
                    
                    # 1秒後再次更新
                    self.root.after(1000, self.update_recording_timer)
                else:
                    # 停止錄製 - 清理定時器
                    self.recording_timer_active = False
                    self.recording_indicator.configure(text="")
        except Exception as e:
            logging.debug(f"更新錄製計時器失敗: {str(e)}")
            self.recording_timer_active = False
    
    def change_mode(self):
        """更改系統模式"""
        mode = self.mode_var.get()
        
        # 隱藏所有面板
        self.recording_frame.pack_forget()
        self.playback_frame.pack_forget()
        
        # 根據模式顯示對應的面板
        if mode == "recording":
            # 🔧 錄製模式：系統自動管理，不顯示檔名輸入區域
            pass  # 錄製模式下不顯示額外控制面板，透過右側「啟動處理」來錄製
        elif mode == "playback":
            self.playback_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        # 通知控制器
        success = self.controller.switch_mode(mode)
        
        # 🎯 重要：切換模式後更新按鈕狀態
        self.update_button_states()
        if success:
            logging.info(f"系統模式已切換為: {mode}")
    
    def toggle_recording(self):
        """切換錄製狀態 - 防重複點擊版本"""
        try:
            if not self.is_recording:
                # 🛡️ 防重複點擊 - 檢查是否正在其他操作中
                if self.is_detecting:
                    self.recording_status.configure(text="錯誤: 請先停止檢測", text_color=ColorScheme.ERROR_RED)
                    return
                
                # 開始錄製
                filename = self.recording_filename.get().strip()
                if not filename:
                    self.recording_status.configure(text="錯誤: 請輸入檔名", text_color=ColorScheme.ERROR_RED)
                    return
                
                # 🎯 立即禁用按鈕防止重複點擊
                self.record_button.configure(text="🔄 啟動錄製...", state="disabled")
                self.recording_status.configure(text="正在啟動錄製...", text_color=ColorScheme.WARNING_ORANGE)
                
                success = self.controller.start_recording(filename)
                if success:
                    self.is_recording = True
                    self.record_button.configure(text="⏹ 停止錄製", state="normal")
                    self.recording_status.configure(text="錄製中...", text_color=ColorScheme.ERROR_RED)
                    logging.info(f"✅ 錄製已開始: {filename}")
                else:
                    # 啟動失敗，恢復狀態
                    self.record_button.configure(text="🔴 開始錄製", state="normal")
                    self.recording_status.configure(text="錄製啟動失敗", text_color=ColorScheme.ERROR_RED)
                    logging.error("❌ 錄製啟動失敗")
                
                # 🔧 更新按鈕狀態
                self.update_button_states()
            else:
                # 停止錄製
                self.record_button.configure(text="🔄 停止中...", state="disabled")
                self.recording_status.configure(text="正在停止錄製...", text_color=ColorScheme.WARNING_ORANGE)
                
                info = self.controller.stop_recording()
                self.is_recording = False
                self.record_button.configure(text="🔴 開始錄製", state="normal")
                self.recording_status.configure(text="錄製完成", text_color=ColorScheme.SUCCESS_GREEN)
                
                if info:
                    logging.info(f"✅ 錄製已完成: {info.get('filename', 'unknown')}")
                
                # 🔧 更新按鈕狀態
                self.update_button_states()
                
        except Exception as e:
            logging.error(f"錄製操作錯誤: {str(e)}")
            self.recording_status.configure(text="錄製操作失敗", text_color=ColorScheme.ERROR_RED)
            self.update_button_states()
    
    def select_playback_file(self):
        """選擇回放檔案"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            title="選擇視頻檔案",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")]
        )
        if filename:
            import os
            # 處理長檔案名 - 如果太長則截斷並添加...
            basename = os.path.basename(filename)
            if len(basename) > 50:  # 如果檔案名超過50個字符
                display_name = basename[:25] + "..." + basename[-22:]  # 顯示前25和後22個字符
            else:
                display_name = basename
            self.playback_file.set(display_name)
            
            # 🔧 關鍵修復：確保UI模式與控制器同步
            # 選擇視頻檔案時自動切換到回放模式
            if self.mode_var.get() != "playback":
                logging.info("📺 選擇視頻檔案，自動切換到回放模式")
                self.mode_var.set("playback")
                self.change_mode()  # 觸發模式切換
            
            success = self.controller.set_playback_file(filename)
            
            # 🎯 注意：視頻加載狀態將通過 player_video_loaded 事件更新
            # 不需要在這裡手動設置 self.video_loaded
            if not success:
                logging.error(f"❌ 視頻檔案設置失敗: {filename}")
                self.status_var.set("狀態: 視頻檔案設置失敗")
                self.video_loaded = False
                self.update_button_states()
    
    def toggle_playback(self):
        """🎬 影片播放/暫停控制（完全獨立，不影響檢測功能）"""
        # 🎯 檢查視頻是否已加載
        if not self.video_loaded or self.playback_file.get() == "未選擇檔案":
            messagebox.showwarning("警告", "請先選擇視頻檔案")
            return
        
        try:
            # 🔧 簡化狀態管理：直接基於UI狀態進行操作，避免複雜的狀態同步
            if self.is_playing:
                # 暫停播放
                success = self.controller.pause_video_playback()
                if success:
                    self.is_playing = False
                    self.play_btn.configure(text="▶️")
                    self.status_var.set("狀態: 視頻已暫停")
                    logging.info("⏸️ 視頻播放已暫停")
                else:
                    messagebox.showerror("錯誤", "視頻暫停失敗")
            else:
                # 開始播放
                # 🎯 關鍵修復：播放功能完全獨立，不涉及檢測參數
                success = self.controller.start_video_playback()
                if success:
                    self.is_playing = True
                    self.play_btn.configure(text="⏸️")
                    self.status_var.set("狀態: 視頻播放中")
                    logging.info("▶️ 視頻播放已開始")
                else:
                    messagebox.showerror("錯誤", "視頻播放啟動失敗，請檢查檔案是否有效")
                    
        except Exception as e:
            logging.error(f"切換播放狀態時出錯: {str(e)}")
            # 發生錯誤時重置狀態
            self.is_playing = False
            self.play_btn.configure(text="▶️")
            messagebox.showerror("錯誤", f"播放控制出錯: {str(e)}")
    
    def pause_playback(self):
        """暫停回放"""
        if self.is_playing:
            self.controller.pause_video_playback()
            self.is_playing = False
            self.play_btn.configure(text="▶️")
    
    def stop_playback(self):
        """停止回放並重置進度條"""
        self.controller.stop_video_playback()
        self.is_playing = False
        self.play_btn.configure(text="▶️")
        
        # 重置進度條到開始位置
        if hasattr(self, 'video_progress'):
            self._updating_progress = True
            try:
                self.video_progress.set(0.0)
                # 同時重置視頻到開始位置
                self.controller.seek_video_to_progress(0.0)
            finally:
                self._updating_progress = False
    
    def on_speed_changed(self, speed):
        """播放速度變化"""
        speed_val = float(speed)
        self.speed_label.configure(text=f"{speed_val:.1f}x")
        self.controller.set_playback_speed(speed_val)
    
    def on_progress_changed(self, progress):
        """進度條變化 - 用戶拖拽進度條"""
        if hasattr(self, '_updating_progress') and self._updating_progress:
            return  # 避免循環更新
            
        progress_val = float(progress)
        # 跳轉到指定進度
        success = self.controller.seek_video_to_progress(progress_val)
        if success:
            logging.info(f"用戶跳轉到進度: {progress_val*100:.1f}%")
    
    # ==================== 批次處理控制方法 ====================
    
    # 原有的模型計算相關函數已移除，功能已整合到"開始檢測"中
    
    # ==================== 震動機控制方法 ====================
    
    def connect_vibration_machine(self):
        """連接震動機"""
        try:
            # 模擬連接震動機 - 實際應用中這裡會有真實的硬體連接邏輯
            logging.info("🔗 連接震動機...")
            
            # 這裡可以添加實際的震動機連接邏輯
            # 例如串口通信、TCP連接等
            
            # 模擬連接成功
            self.vibration_connected = True
            self.vibration_frequency = 50  # 初始頻率
            
            # 更新狀態顯示
            self.vibration_status_var.set("已連接")
            self.vibration_status_label.configure(text_color=ColorScheme.SUCCESS_GREEN)
            
            logging.info("✅ 震動機連接成功")
            return True
            
        except Exception as e:
            logging.error(f"震動機連接錯誤: {str(e)}")
            self.vibration_status_var.set("連接失敗")
            self.vibration_status_label.configure(text_color="#dc2626")
            return False
    
    def start_vibration_machine(self):
        """啟動震動機"""
        try:
            if not hasattr(self, 'vibration_connected') or not self.vibration_connected:
                return False
                
            logging.info("🌀 啟動震動機...")
            
            # 設定初始頻率
            self.vibration_frequency = 50  # Hz
            
            # 這裡可以添加實際的震動機啟動命令
            # 例如發送串口命令：self.send_vibration_command(f"START:{self.vibration_frequency}")
            
            self.vibration_status_var.set(f"運行中 ({self.vibration_frequency}Hz)")
            self.vibration_status_label.configure(text_color=ColorScheme.PRIMARY_BLUE)
            
            logging.info(f"✅ 震動機已啟動，頻率: {self.vibration_frequency}Hz")
            return True
            
        except Exception as e:
            logging.error(f"啟動震動機錯誤: {str(e)}")
            return False
    
    def stop_vibration_machine(self):
        """停止震動機"""
        try:
            if not hasattr(self, 'vibration_connected') or not self.vibration_connected:
                return True
                
            logging.info("⏸ 停止震動機...")
            
            # 這裡可以添加實際的震動機停止命令
            # 例如發送串口命令：self.send_vibration_command("STOP")
            
            self.vibration_status_var.set("已停止")
            self.vibration_status_label.configure(text_color=ColorScheme.WARNING_ORANGE)
            
            logging.info("✅ 震動機已停止")
            return True
            
        except Exception as e:
            logging.error(f"停止震動機錯誤: {str(e)}")
            return False
    
    def adjust_vibration_frequency(self, target_count, current_count):
        """根據計數接近程度調整震動頻率"""
        try:
            if not hasattr(self, 'vibration_connected') or not self.vibration_connected:
                return
                
            # 計算剩餘數量比例
            remaining_ratio = (target_count - current_count) / target_count
            
            # 根據剩餘比例調整頻率
            if remaining_ratio > 0.8:
                # 剩餘80%以上，維持高頻率
                new_frequency = 50
            elif remaining_ratio > 0.5:
                # 剩餘50%-80%，中等頻率
                new_frequency = 35
            elif remaining_ratio > 0.2:
                # 剩餘20%-50%，低頻率
                new_frequency = 20
            else:
                # 剩餘20%以下，最低頻率
                new_frequency = 10
            
            # 如果頻率有變化才更新
            if abs(new_frequency - self.vibration_frequency) >= 5:
                self.vibration_frequency = new_frequency
                
                # 這裡發送頻率調整命令
                # self.send_vibration_command(f"FREQ:{new_frequency}")
                
                self.vibration_status_var.set(f"運行中 ({new_frequency}Hz)")
                logging.info(f"📊 震動頻率已調整為: {new_frequency}Hz (剩餘比例: {remaining_ratio:.1%})")
                
        except Exception as e:
            logging.error(f"調整震動頻率錯誤: {str(e)}")
    
    # ==================== 批次記錄方法 ====================
    
    def record_batch_result(self):
        """記錄批次結果"""
        try:
            if not hasattr(self, 'current_round') or not hasattr(self, 'total_count'):
                return
                
            import datetime
            import json
            from pathlib import Path
            
            # 創建記錄目錄
            records_dir = Path("batch_records")
            records_dir.mkdir(exist_ok=True)
            
            # 準備記錄數據
            record_data = {
                "timestamp": datetime.datetime.now().isoformat(),
                "round_number": self.current_round,
                "part_count": self.total_count,
                "target_count": int(self.target_entry.get()) if hasattr(self, 'target_entry') else 100,
                "detection_method": "current_method",  # 可以從controller獲取
                "status": "completed"
            }
            
            # 保存到文件
            filename = f"batch_record_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            file_path = records_dir / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(record_data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"📋 批次記錄已保存: {file_path}")
            
        except Exception as e:
            logging.error(f"記錄批次結果錯誤: {str(e)}")
    
    def complete_current_round(self):
        """完成當前輪並詢問是否繼續下一輪"""
        try:
            logging.info(f"✅ 完成第 {self.current_round} 輪，計數: {self.total_count}")
            
            # 停止震動機
            self.stop_vibration_machine()
            
            # 記錄本輪結果
            self.record_batch_result()
            
            # 詢問用戶是否繼續下一輪（這裡可以實現自動或手動模式）
            # 暫時實現自動停止模式
            self.stop_detection()
            
            # 可以在這裡添加彈窗詢問是否繼續下一輪
            # result = messagebox.askyesno("完成本輪", f"第 {self.current_round} 輪已完成\n"
            #                                        f"計數: {self.total_count}\n"
            #                                        f"是否開始下一輪？")
            # if result:
            #     self.next_round()
            
        except Exception as e:
            logging.error(f"完成當前輪錯誤: {str(e)}")
    
    def next_round(self):
        """開始下一輪"""
        try:
            self.current_round += 1
            self.total_count = 0
            
            # 更新顯示
            self.round_count_var.set(str(self.current_round))
            self.object_count_var.set("000")
            self.progress_bar.set(0)
            
            # 重啟震動機
            self.start_vibration_machine()
            
            logging.info(f"🔄 開始第 {self.current_round} 輪")
            
        except Exception as e:
            logging.error(f"開始下一輪錯誤: {str(e)}")
    
    # ==================== 初始化批次變數 ====================
    
    def initialize_batch_variables(self):
        """初始化批次處理相關變數"""
        self.is_calculating = False
        self.vibration_connected = False
        self.vibration_frequency = 50
        self.current_round = 0
        self.total_count = 0
    
    def run(self):
        """運行主循環"""
        try:
            logging.info("CustomTkinter 明亮清晰版本開始運行")
            self.root.mainloop()
        except Exception as e:
            logging.error(f"主循環運行錯誤: {str(e)}")
            raise
        finally:
            logging.info("CustomTkinter 明亮清晰版本已停止")