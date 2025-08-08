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
        
        # UI 變量 - 修正FPS顯示格式
        self.status_var = tk.StringVar(value="狀態: 系統就緒")
        # 固定寬度的FPS顯示（預的6位數空間）
        self.camera_fps_var = tk.StringVar(value="相機:   0.0")
        self.processing_fps_var = tk.StringVar(value="處理:   0.0")
        self.detection_fps_var = tk.StringVar(value="檢測:   0.0")
        self.object_count_var = tk.StringVar(value="000")
        self.camera_info_var = tk.StringVar(value="相機: 未連接")
        self.method_var = tk.StringVar(value="circle")
        
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
            values=["circle", "contour"],
            variable=self.method_var,
            command=self.on_method_changed,
            width=100,
            font=ctk.CTkFont(size=FontSizes.BODY),
            dropdown_font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.BG_CARD,
            button_color=ColorScheme.ACCENT_BLUE,
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.detection_method.pack(side="left", padx=(0, 12), pady=8)
        
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
        
        # 設備標題
        ctk.CTkLabel(
            left_panel,
            text="設備",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(pady=(15, 10))
        
        # 設備選擇區域
        device_frame = ctk.CTkFrame(left_panel, fg_color=ColorScheme.BG_SECONDARY)
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
        self.device_combobox.pack(fill="x", padx=12, pady=12)
        
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
            left_panel,
            text="📷 相機設置",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.TEXT_ACCENT
        ).pack(pady=(0, 10))
        
        # 曝光時間設置 - 增強版
        exposure_frame = ctk.CTkFrame(left_panel, fg_color=ColorScheme.BG_SECONDARY)
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
            left_panel,
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
        
        # 視頻控制區域
        ctk.CTkLabel(
            left_panel,
            text="🎬 視頻控制",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.PURPLE_ACCENT
        ).pack(pady=(10, 10))
        
        # 模式選擇
        mode_frame = ctk.CTkFrame(left_panel, fg_color=ColorScheme.BG_SECONDARY)
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
        self.recording_frame = ctk.CTkFrame(left_panel, fg_color=ColorScheme.BG_SECONDARY)
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
        self.playback_frame = ctk.CTkFrame(left_panel, fg_color=ColorScheme.BG_SECONDARY)
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
            text_color=ColorScheme.TEXT_SECONDARY
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
        
        self.play_btn = ctk.CTkButton(
            control_buttons, text="▶️", width=30, height=30,
            command=self.toggle_playback,
            font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.SUCCESS_GREEN,
            hover_color="#047857"
        )
        self.play_btn.pack(side="left", padx=2)
        
        self.pause_btn = ctk.CTkButton(
            control_buttons, text="⏸️", width=30, height=30,
            command=self.pause_playback,
            font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.WARNING_ORANGE,
            hover_color="#b45309"
        )
        self.pause_btn.pack(side="left", padx=2)
        
        self.stop_btn = ctk.CTkButton(
            control_buttons, text="⏹️", width=30, height=30,
            command=self.stop_playback,
            font=ctk.CTkFont(size=FontSizes.BODY),
            fg_color=ColorScheme.ERROR_RED,
            hover_color="#b91c1c"
        )
        self.stop_btn.pack(side="left", padx=2)
        
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
        
        # 隐藏錄製和回放框架（預設為實時模式）
        self.recording_frame.pack_forget()
        self.playback_frame.pack_forget()
    
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
        
        # 固定寬度的FPS顯示標籤
        self.camera_fps_display = ctk.CTkLabel(
            fps_frame,
            textvariable=self.camera_fps_var,
            text_color=ColorScheme.TEXT_SUCCESS,
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold", family="monospace"),
            width=80,  # 固定寬度
            anchor="w"  # 左對齊
        )
        self.camera_fps_display.pack(side="left", padx=5)
        
        self.processing_fps_display = ctk.CTkLabel(
            fps_frame,
            textvariable=self.processing_fps_var,
            text_color=ColorScheme.TEXT_ACCENT,
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold", family="monospace"),
            width=80,  # 固定寬度
            anchor="w"  # 左對齊
        )
        self.processing_fps_display.pack(side="left", padx=5)
        
        self.detection_fps_display = ctk.CTkLabel(
            fps_frame,
            textvariable=self.detection_fps_var,
            text_color=ColorScheme.PURPLE_ACCENT,
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold", family="monospace"),
            width=80,  # 固定寬度
            anchor="w"  # 左小齊
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
        
        # 當前計數顯示
        count_frame = ctk.CTkFrame(scrollable_frame, fg_color=ColorScheme.BG_ACCENT)
        count_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        ctk.CTkLabel(
            count_frame, 
            text="當前計數", 
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(pady=(15, 5))
        
        # 超大數字顯示
        self.count_label = ctk.CTkLabel(
            count_frame,
            textvariable=self.object_count_var,
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
            text="0 / 100",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_ACCENT
        )
        self.progress_label.pack(pady=(0, 15))
        
        # 控制按鈕
        button_frame = ctk.CTkFrame(scrollable_frame, fg_color=ColorScheme.BG_SECONDARY)
        button_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        buttons_container = ctk.CTkFrame(button_frame, fg_color="transparent")
        buttons_container.pack(pady=15)
        
        ctk.CTkButton(
            buttons_container,
            text="▶ 開始",
            command=self.start_detection,
            height=35,
            width=90,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.SUCCESS_GREEN,
            hover_color="#047857",
            text_color="white"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            buttons_container,
            text="⏸ 停止",
            command=self.stop_detection,
            height=35,
            width=90,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.ERROR_RED,
            hover_color="#b91c1c",
            text_color="white"
        ).pack(side="left", padx=5)
        
        # 重置按鈕
        ctk.CTkButton(
            button_frame,
            text="🔄 重置計數",
            command=self.reset_count,
            height=32,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.WARNING_ORANGE,
            hover_color="#b45309",
            text_color="white"
        ).pack(pady=(0, 15))
        
        # 檢測參數標題
        ctk.CTkLabel(
            scrollable_frame,
            text="🔧 檢測參數",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.PURPLE_ACCENT
        ).pack(pady=(10, 10))
        
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
        """切換處理狀態"""
        self.is_processing_active = not self.is_processing_active
        if self.is_processing_active:
            success = self.controller.start_capture()
            if success:
                self.start_processing_btn.configure(
                    text="⏸️ 停止處理",
                    fg_color=ColorScheme.ERROR_RED
                )
            else:
                self.is_processing_active = False
        else:
            self.controller.stop_capture()
            self.start_processing_btn.configure(
                text="▶️ 啟動處理",
                fg_color=ColorScheme.ACCENT_BLUE
            )
    
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
        """開始檢測"""
        if self.controller.start_batch_detection():
            logging.info("批次檢測已啟動")
    
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
        
        params = {'min_area': min_area, 'max_area': max_area}
        self.controller.update_detection_parameters(params)
    
    def toggle_detection(self):
        """切換檢測開關"""
        enabled = self.enable_detection_var.get()
        self.controller.toggle_detection(enabled)
    
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
            self.connection_status.configure(
                text="● 已連接", 
                text_color=ColorScheme.TEXT_SUCCESS
            )
            self.camera_info_var.set("相機: 已連接")
            self.start_processing_btn.configure(state="normal")
        else:
            self.connection_status.configure(
                text="● 未連接", 
                text_color=ColorScheme.TEXT_ERROR
            )
            self.camera_info_var.set("相機: 未連接")
            self.start_processing_btn.configure(state="disabled")
    
    def initialize_display_status(self):
        """初始化顯示狀態"""
        self.status_var.set("狀態: 系統就緒")
        self.update_connection_ui()
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
                
                height, width = frame.shape[:2]
                display_width, display_height = self.display_size
                
                if len(frame.shape) == 3:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                else:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                
                frame_resized = cv2.resize(frame_rgb, (display_width, display_height))
                pil_image = Image.fromarray(frame_resized)
                photo = ImageTk.PhotoImage(pil_image)
                
                self.video_label.configure(image=photo, text="")
                self.video_label.image = photo
                self.current_frame = frame
                
        except Exception as e:
            logging.error(f"更新幀顯示錯誤: {str(e)}")
    
    def on_controller_event(self, event_type: str, data: Any = None):
        """處理控制器事件"""
        try:
            if event_type == 'frame_processed':
                if data and 'frame' in data:
                    self.update_frame(data['frame'])
                    
                if 'object_count' in data:
                    count = data['object_count']
                    self.object_count_var.set(f"{count:03d}")
                    self.object_count_status.configure(text=f"物件: {count}")
                    
                    target = self.target_count_var.get()
                    if target > 0:
                        progress = min(count / target, 1.0)
                        self.progress_bar.set(progress)
                        self.progress_label.configure(text=f"{count} / {target}")
                
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
                    
        except Exception as e:
            logging.error(f"處理控制器事件錯誤: {str(e)}")
    
    # 新增的功能方法
    
    def update_fps_display(self, fps_type, fps_value):
        """控制FPS顯示更新頻率和格式"""
        import time
        current_time = time.time()
        
        # 只有超過更新間隔才更新顯示
        if current_time - self.last_fps_update < self.fps_update_interval:
            return
        
        self.last_fps_update = current_time
        
        # 固定格式顯示（預的6位數空間）
        if fps_value < 10:
            fps_str = f"  {fps_value:.1f}"
        elif fps_value < 100:
            fps_str = f" {fps_value:.1f}"
        elif fps_value < 1000:
            fps_str = f"{fps_value:.1f}"
        else:
            fps_str = f"{fps_value:.0f}"  # 超過1000時不顯示小數
        
        if fps_type == 'camera':
            self.camera_fps_var.set(f"相機:{fps_str}")
        elif fps_type == 'processing':
            self.processing_fps_var.set(f"處理:{fps_str}")
        elif fps_type == 'detection':
            self.detection_fps_var.set(f"檢測:{fps_str}")
    
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
    
    def change_mode(self):
        """更改系統模式"""
        mode = self.mode_var.get()
        
        # 隱藏所有面板
        self.recording_frame.pack_forget()
        self.playback_frame.pack_forget()
        
        # 根據模式顯示對應的面板
        if mode == "recording":
            self.recording_frame.pack(fill="x", padx=12, pady=(0, 15))
        elif mode == "playback":
            self.playback_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        # 通知控制器
        success = self.controller.switch_mode(mode)
        if success:
            logging.info(f"系統模式已切換為: {mode}")
    
    def toggle_recording(self):
        """切換錄製狀態"""
        if not self.is_recording:
            # 開始錄製
            filename = self.recording_filename.get().strip()
            if not filename:
                self.recording_status.configure(text="錯誤: 請輸入檔名")
                return
            
            success = self.controller.start_recording(filename)
            if success:
                self.is_recording = True
                self.record_button.configure(text="⏹ 停止錄製")
                self.recording_status.configure(text="錄製中...", text_color=ColorScheme.ERROR_RED)
        else:
            # 停止錄製
            info = self.controller.stop_recording()
            self.is_recording = False
            self.record_button.configure(text="● 錄製")
            self.recording_status.configure(text="錄製完成", text_color=ColorScheme.SUCCESS_GREEN)
    
    def select_playback_file(self):
        """選擇回放檔案"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            title="選擇視頻檔案",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")]
        )
        if filename:
            import os
            self.playback_file.set(os.path.basename(filename))
            self.controller.set_playback_file(filename)
    
    def toggle_playback(self):
        """切換播放狀態"""
        if not self.is_playing:
            success = self.controller.start_video_playback()
            if success:
                self.is_playing = True
                self.play_btn.configure(text="⏸️")
        else:
            self.controller.pause_video_playback()
            self.is_playing = False
            self.play_btn.configure(text="▶️")
    
    def pause_playback(self):
        """暫停回放"""
        if self.is_playing:
            self.controller.pause_video_playback()
            self.is_playing = False
            self.play_btn.configure(text="▶️")
    
    def stop_playback(self):
        """停止回放"""
        self.controller.stop_video_playback()
        self.is_playing = False
        self.play_btn.configure(text="▶️")
    
    def on_speed_changed(self, speed):
        """播放速度變化"""
        speed_val = float(speed)
        self.speed_label.configure(text=f"{speed_val:.1f}x")
        self.controller.set_playback_speed(speed_val)
    
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