"""
主視圖 - CustomTkinter 優化配色版本
根據用戶反饋優化字體大小和配色方案，打造簡潔活潑的界面
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

# 設定 CustomTkinter 外觀和活潑配色
ctk.set_appearance_mode("dark")  # 使用深色模式作為基礎
ctk.set_default_color_theme("blue")  # 藍色主題

# 定義活潑配色方案
class ColorScheme:
    # 主要顏色 - 活潑但不刺眼
    PRIMARY_BLUE = "#1f6aa5"      # 主藍色
    ACCENT_BLUE = "#4a9eff"       # 明亮藍色
    SUCCESS_GREEN = "#4ade80"     # 成功綠色
    WARNING_ORANGE = "#fb923c"    # 警告橙色
    ERROR_RED = "#f87171"         # 錯誤紅色
    PURPLE_ACCENT = "#a855f7"     # 紫色強調
    
    # 文字顏色
    TEXT_PRIMARY = "#ffffff"      # 主要文字
    TEXT_SECONDARY = "#d1d5db"    # 次要文字
    TEXT_ACCENT = "#60a5fa"       # 強調文字
    
    # 背景顏色
    BG_DARK = "#1e1e1e"          # 深色背景
    BG_CARD = "#2d2d2d"          # 卡片背景

# 字體大小系統 - 根據截圖優化
class FontSizes:
    HUGE = 52        # 超大數字顯示
    LARGE = 18       # 大標題
    TITLE = 15       # 標題
    SUBTITLE = 13    # 副標題  
    BODY = 12        # 正文
    SMALL = 11       # 小字
    TINY = 10        # 極小字


class MainView:
    """主視圖 - 優化配色和字體版本"""
    
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
        
        # 設定最佳尺寸
        optimal_width = min(max(int(screen_width * 0.85), 1400), 1800)
        optimal_height = min(max(int(screen_height * 0.85), 1000), 1200)
        
        # 計算居中位置
        x = (screen_width - optimal_width) // 2
        y = (screen_height - optimal_height) // 2
        
        self.root.geometry(f"{optimal_width}x{optimal_height}+{x}+{y}")
        self.root.minsize(1400, 1000)
        self.root.resizable(True, True)
        
        # UI 變量
        self.status_var = tk.StringVar(value="狀態: 系統就緒")
        self.camera_fps_var = tk.StringVar(value="相機: 0 FPS")
        self.processing_fps_var = tk.StringVar(value="處理: 0 FPS")
        self.detection_fps_var = tk.StringVar(value="檢測: 0 FPS")
        self.object_count_var = tk.StringVar(value="000")
        self.camera_info_var = tk.StringVar(value="相機: 未連接")
        self.method_var = tk.StringVar(value="circle")
        
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
        
        logging.info("CustomTkinter 優化配色版本初始化完成")
    
    def create_ui(self):
        """創建優化的用戶界面"""
        # 主容器
        main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=4, pady=4)
        
        # 頂部工具欄
        self.create_top_toolbar(main_container)
        
        # 主要內容區域（三欄布局）
        content_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=(2, 0))
        
        # 配置三欄權重 - 更合理的比例
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
        """創建頂部工具欄 - 活潑配色"""
        toolbar = ctk.CTkFrame(parent, height=45)
        toolbar.pack(fill="x", padx=2, pady=(2, 4))
        
        # 左側控制組
        left_frame = ctk.CTkFrame(toolbar, fg_color="transparent")
        left_frame.pack(side="left", padx=15, pady=8)
        
        # 連線控制 - 使用活潑顏色
        conn_frame = ctk.CTkFrame(left_frame)
        conn_frame.pack(side="left", padx=(0, 15))
        
        ctk.CTkLabel(
            conn_frame, 
            text="連線:", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left", padx=(10, 5), pady=5)
        
        self.connection_switch = ctk.CTkButton(
            conn_frame,
            text="○",
            command=self.toggle_connection_switch,
            width=35,
            height=28,
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold"),
            fg_color=ColorScheme.BG_CARD,
            hover_color=ColorScheme.SUCCESS_GREEN
        )
        self.connection_switch.pack(side="left", padx=(0, 10), pady=5)
        
        # 啟動按鈕 - 醒目的藍色
        self.start_processing_btn = ctk.CTkButton(
            left_frame,
            text="▶️ 啟動處理",
            command=self.toggle_processing,
            state="disabled",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            height=32,
            fg_color=ColorScheme.ACCENT_BLUE,
            hover_color=ColorScheme.PRIMARY_BLUE
        )
        self.start_processing_btn.pack(side="left", padx=(0, 15))
        
        # 檢測方法選擇
        method_frame = ctk.CTkFrame(left_frame)
        method_frame.pack(side="left")
        
        ctk.CTkLabel(
            method_frame, 
            text="檢測方法:", 
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(side="left", padx=(10, 5), pady=5)
        
        self.detection_method = ctk.CTkOptionMenu(
            method_frame,
            values=["circle", "contour"],
            variable=self.method_var,
            command=self.on_method_changed,
            width=100,
            font=ctk.CTkFont(size=FontSizes.BODY),
            dropdown_font=ctk.CTkFont(size=FontSizes.BODY)
        )
        self.detection_method.pack(side="left", padx=(0, 10), pady=5)
        
        # 右側設定按鈕 - 活潑的橙色
        self.settings_btn = ctk.CTkButton(
            toolbar,
            text="⚙️",
            command=self.open_settings,
            width=35,
            height=35,
            font=ctk.CTkFont(size=FontSizes.LARGE),
            fg_color=ColorScheme.WARNING_ORANGE,
            hover_color="#ea580c"
        )
        self.settings_btn.pack(side="right", padx=15, pady=5)
    
    def create_left_panel(self, parent):
        """創建左側設備面板 - 優化字體"""
        left_panel = ctk.CTkFrame(parent)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 2), pady=0)
        
        # 設備標題 - 加大字體
        ctk.CTkLabel(
            left_panel,
            text="設備",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(pady=(15, 10))
        
        # 設備選擇區域
        device_frame = ctk.CTkFrame(left_panel)
        device_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        self.device_combobox = ctk.CTkComboBox(
            device_frame,
            values=["未檢測到設備"],
            state="readonly",
            command=self.on_device_selected,
            font=ctk.CTkFont(size=FontSizes.BODY),
            dropdown_font=ctk.CTkFont(size=FontSizes.BODY)
        )
        self.device_combobox.pack(fill="x", padx=10, pady=10)
        
        # 連接狀態 - 更大更明顯
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
        
        # 曝光時間設置 - 改善可讀性
        exposure_frame = ctk.CTkFrame(left_panel)
        exposure_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        ctk.CTkLabel(
            exposure_frame, 
            text="曝光時間 (μs)", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(pady=(10, 5))
        
        self.exposure_slider = ctk.CTkSlider(
            exposure_frame,
            from_=100,
            to=10000,
            variable=self.exposure_var,
            command=self.on_exposure_changed,
            progress_color=ColorScheme.ACCENT_BLUE,
            button_color=ColorScheme.PRIMARY_BLUE
        )
        self.exposure_slider.pack(fill="x", padx=10, pady=5)
        
        self.exposure_label = ctk.CTkLabel(
            exposure_frame, 
            text="1000.0",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.SUCCESS_GREEN
        )
        self.exposure_label.pack(pady=(0, 10))
        
        # 即時檢測開關 - 更大更明顯
        self.enable_detection_var = tk.BooleanVar(value=True)
        self.detection_checkbox = ctk.CTkCheckBox(
            left_panel,
            text="啟用即時檢測",
            variable=self.enable_detection_var,
            command=self.toggle_detection,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY,
            checkmark_color=ColorScheme.SUCCESS_GREEN
        )
        self.detection_checkbox.pack(pady=15)
        
        # 視頻控制區域
        ctk.CTkLabel(
            left_panel,
            text="🎬 視頻控制",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.PURPLE_ACCENT
        ).pack(pady=(10, 10))
        
        # 模式選擇 - 更好的間距和字體
        mode_frame = ctk.CTkFrame(left_panel)
        mode_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        ctk.CTkLabel(
            mode_frame, 
            text="模式:", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        # 模式單選按鈕 - 更大更清楚
        self.mode_live = ctk.CTkRadioButton(
            mode_frame,
            text="實時",
            variable=self.mode_var,
            value="live",
            command=self.change_mode,
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.mode_live.pack(anchor="w", padx=25, pady=3)
        
        self.mode_recording = ctk.CTkRadioButton(
            mode_frame,
            text="錄影",
            variable=self.mode_var,
            value="recording",
            command=self.change_mode,
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.mode_recording.pack(anchor="w", padx=25, pady=3)
        
        self.mode_playback = ctk.CTkRadioButton(
            mode_frame,
            text="回放",
            variable=self.mode_var,
            value="playback",
            command=self.change_mode,
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_PRIMARY
        )
        self.mode_playback.pack(anchor="w", padx=25, pady=(3, 15))
    
    def create_center_panel(self, parent):
        """創建中央視頻面板 - 優化顯示"""
        center_panel = ctk.CTkFrame(parent)
        center_panel.grid(row=0, column=1, sticky="nsew", padx=2, pady=0)
        
        # 配置網格權重
        center_panel.grid_rowconfigure(1, weight=1)
        center_panel.grid_columnconfigure(0, weight=1)
        
        # 視頻標題欄 - 更好的視覺效果
        header_frame = ctk.CTkFrame(center_panel, height=45)
        header_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        header_frame.grid_propagate(False)
        
        # 左側相機信息
        left_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_header.pack(side="left", padx=15, pady=8)
        
        self.camera_info_label = ctk.CTkLabel(
            left_header,
            text="📹 Basler acA640-300gm - 實時影像",
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold"),
            text_color=ColorScheme.TEXT_ACCENT
        )
        self.camera_info_label.pack()
        
        # 右側縮放控制 - 更活潑的按鈕
        right_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_header.pack(side="right", padx=15, pady=8)
        
        # 縮放選單
        ctk.CTkLabel(
            right_header, 
            text="🔍", 
            font=ctk.CTkFont(size=FontSizes.SUBTITLE)
        ).pack(side="left", padx=(0, 5))
        
        self.zoom_var = tk.StringVar(value="100%")
        zoom_menu = ctk.CTkOptionMenu(
            right_header,
            values=["50%", "75%", "100%", "125%", "150%"],
            variable=self.zoom_var,
            width=80,
            command=self.change_zoom,
            font=ctk.CTkFont(size=FontSizes.SMALL)
        )
        zoom_menu.pack(side="left", padx=5)
        
        # 縮放按鈕 - 活潑顏色
        zoom_buttons = ctk.CTkFrame(right_header, fg_color="transparent")
        zoom_buttons.pack(side="left", padx=10)
        
        ctk.CTkButton(
            zoom_buttons, text="+", width=30, height=25,
            command=lambda: self.zoom_change(1.25),
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.SUCCESS_GREEN
        ).pack(side="left", padx=1)
        
        ctk.CTkButton(
            zoom_buttons, text="-", width=30, height=25,
            command=lambda: self.zoom_change(0.8),
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.WARNING_ORANGE
        ).pack(side="left", padx=1)
        
        ctk.CTkButton(
            zoom_buttons, text="□", width=30, height=25,
            command=self.fit_to_window,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.PURPLE_ACCENT
        ).pack(side="left", padx=1)
        
        # 視頻顯示區域
        video_container = ctk.CTkFrame(center_panel, corner_radius=8)
        video_container.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        video_container.grid_rowconfigure(0, weight=1)
        video_container.grid_columnconfigure(0, weight=1)
        
        # 視頻標籤 - 更好的占位符
        self.video_label = ctk.CTkLabel(
            video_container,
            text="Basler acA640-300gm\n📹 Camera Ready\n配置開始捕獲取得影像",
            font=ctk.CTkFont(size=FontSizes.SUBTITLE),
            text_color=ColorScheme.TEXT_SECONDARY,
            width=640,
            height=480
        )
        self.video_label.grid(row=0, column=0, padx=15, pady=15)
        
        # 底部信息欄 - 更好的FPS顯示
        info_frame = ctk.CTkFrame(center_panel, height=40)
        info_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        info_frame.grid_propagate(False)
        
        # 分辨率信息
        self.resolution_label = ctk.CTkLabel(
            info_frame, 
            text="640 x 480 │ Mono8 │ 8 bit",
            font=ctk.CTkFont(size=FontSizes.BODY),
            text_color=ColorScheme.TEXT_SECONDARY
        )
        self.resolution_label.pack(side="left", padx=20, pady=10)
        
        # FPS 顯示區域 - 活潑顏色
        fps_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        fps_frame.pack(side="right", padx=20, pady=5)
        
        self.camera_fps_display = ctk.CTkLabel(
            fps_frame,
            textvariable=self.camera_fps_var,
            text_color=ColorScheme.SUCCESS_GREEN,
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold")
        )
        self.camera_fps_display.pack(side="left", padx=8)
        
        self.processing_fps_display = ctk.CTkLabel(
            fps_frame,
            textvariable=self.processing_fps_var,
            text_color=ColorScheme.ACCENT_BLUE,
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold")
        )
        self.processing_fps_display.pack(side="left", padx=8)
        
        self.detection_fps_display = ctk.CTkLabel(
            fps_frame,
            textvariable=self.detection_fps_var,
            text_color=ColorScheme.PURPLE_ACCENT,
            font=ctk.CTkFont(size=FontSizes.SMALL, weight="bold")
        )
        self.detection_fps_display.pack(side="left", padx=8)
    
    def create_right_panel(self, parent):
        """創建右側檢測面板 - 大幅優化字體大小"""
        right_panel = ctk.CTkFrame(parent)
        right_panel.grid(row=0, column=2, sticky="nsew", padx=(2, 0), pady=0)
        
        # 檢測計數標題 - 更大更醒目
        ctk.CTkLabel(
            right_panel,
            text="▶ 檢測計數",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.TEXT_ACCENT
        ).pack(pady=(15, 10))
        
        # 當前計數顯示 - 超大數字
        count_frame = ctk.CTkFrame(right_panel)
        count_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        ctk.CTkLabel(
            count_frame, 
            text="當前計數", 
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(pady=(15, 5))
        
        # 超大數字顯示 - 主要焦點
        self.count_label = ctk.CTkLabel(
            count_frame,
            textvariable=self.object_count_var,
            font=ctk.CTkFont(size=FontSizes.HUGE, weight="bold"),
            text_color=ColorScheme.PRIMARY_BLUE
        )
        self.count_label.pack(pady=(5, 15))
        
        # 目標設定區域 - 更好的字體
        target_frame = ctk.CTkFrame(right_panel)
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
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold")
        )
        self.target_entry.pack(pady=8)
        
        # 進度條 - 更明顯
        self.progress_bar = ctk.CTkProgressBar(
            target_frame, 
            width=200, 
            height=20,
            progress_color=ColorScheme.SUCCESS_GREEN
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
        
        # 控制按鈕 - 活潑顏色和更大字體
        button_frame = ctk.CTkFrame(right_panel)
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
            hover_color="#16a34a"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            buttons_container,
            text="⏸ 停止",
            command=self.stop_detection,
            height=35,
            width=90,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.ERROR_RED,
            hover_color="#dc2626"
        ).pack(side="left", padx=5)
        
        # 重置按鈕 - 醒目顏色
        ctk.CTkButton(
            button_frame,
            text="🔄 重置計數",
            command=self.reset_count,
            height=32,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            fg_color=ColorScheme.WARNING_ORANGE,
            hover_color="#ea580c"
        ).pack(pady=(0, 15))
        
        # 檢測參數標題 - 更大字體
        ctk.CTkLabel(
            right_panel,
            text="🔧 檢測參數",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.PURPLE_ACCENT
        ).pack(pady=(10, 10))
        
        # 參數調整區域 - 大幅改善字體
        params_frame = ctk.CTkFrame(right_panel)
        params_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        # 最小面積 - 更大更清楚的字體
        min_area_container = ctk.CTkFrame(params_frame)
        min_area_container.pack(fill="x", padx=10, pady=(15, 10))
        
        ctk.CTkLabel(
            min_area_container, 
            text="最小面積", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(pady=(5, 3))
        
        self.min_area_slider = ctk.CTkSlider(
            min_area_container,
            from_=10,
            to=500,
            variable=self.min_area_var,
            command=self.update_detection_params,
            progress_color=ColorScheme.SUCCESS_GREEN,
            button_color=ColorScheme.SUCCESS_GREEN
        )
        self.min_area_slider.pack(fill="x", padx=8, pady=3)
        
        self.min_area_label = ctk.CTkLabel(
            min_area_container, 
            text="100",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.SUCCESS_GREEN
        )
        self.min_area_label.pack(pady=(3, 8))
        
        # 最大面積 - 同樣改善
        max_area_container = ctk.CTkFrame(params_frame)
        max_area_container.pack(fill="x", padx=10, pady=(0, 15))
        
        ctk.CTkLabel(
            max_area_container, 
            text="最大面積", 
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.TEXT_PRIMARY
        ).pack(pady=(5, 3))
        
        self.max_area_slider = ctk.CTkSlider(
            max_area_container,
            from_=1000,
            to=10000,
            variable=self.max_area_var,
            command=self.update_detection_params,
            progress_color=ColorScheme.WARNING_ORANGE,
            button_color=ColorScheme.WARNING_ORANGE
        )
        self.max_area_slider.pack(fill="x", padx=8, pady=3)
        
        self.max_area_label = ctk.CTkLabel(
            max_area_container, 
            text="5000",
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),
            text_color=ColorScheme.WARNING_ORANGE
        )
        self.max_area_label.pack(pady=(3, 8))
        
        # 即時統計區域 - 最重要的改善！大字體！
        stats_frame = ctk.CTkFrame(right_panel)
        stats_frame.pack(fill="x", padx=12, pady=(0, 15))
        
        # 統計標題 - 更大更醒目
        ctk.CTkLabel(
            stats_frame,
            text="📊 即時統計",
            font=ctk.CTkFont(size=FontSizes.TITLE, weight="bold"),
            text_color=ColorScheme.SUCCESS_GREEN
        ).pack(pady=(15, 10))
        
        # 檢測品質 - 大大改善字體大小！
        self.quality_label = ctk.CTkLabel(
            stats_frame,
            text="檢測品質: 良好",
            text_color=ColorScheme.SUCCESS_GREEN,
            font=ctk.CTkFont(size=FontSizes.SUBTITLE, weight="bold")  # 從小字改為副標題大小
        )
        self.quality_label.pack(pady=8)
        
        # 檢測 FPS - 也大大改善！
        self.detection_fps_stat = ctk.CTkLabel(
            stats_frame,
            textvariable=self.detection_fps_var,
            font=ctk.CTkFont(size=FontSizes.BODY, weight="bold"),  # 從極小字改為正文大小
            text_color=ColorScheme.PURPLE_ACCENT
        )
        self.detection_fps_stat.pack(pady=(0, 15))
    
    def create_status_panel(self, parent):
        """創建底部狀態面板 - 優化字體"""
        status_panel = ctk.CTkFrame(parent, height=50)
        status_panel.pack(fill="x", padx=2, pady=(4, 2))
        status_panel.pack_propagate(False)
        
        # 左側狀態
        left_status = ctk.CTkFrame(status_panel, fg_color="transparent")
        left_status.pack(side="left", fill="y", padx=15, pady=8)
        
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
        right_status.pack(side="right", fill="y", padx=15, pady=8)
        
        # 時間戳 - 稍微增大
        self.timestamp_label = ctk.CTkLabel(
            right_status,
            text="2025-08-07 15:09:18",
            font=ctk.CTkFont(size=FontSizes.SMALL),
            text_color=ColorScheme.TEXT_SECONDARY
        )
        self.timestamp_label.pack(side="right", padx=(20, 0))
        
        # 物件計數 - 更醒目
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
                self.connection_switch.configure(text="●", fg_color=ColorScheme.SUCCESS_GREEN)
                self.start_processing_btn.configure(state="normal")
            else:
                self.connection_switch_on = False
        else:
            self.disconnect_device()
            self.connection_switch.configure(text="○", fg_color=ColorScheme.BG_CARD)
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
                text_color=ColorScheme.SUCCESS_GREEN
            )
            self.camera_info_var.set("相機: 已連接")
            self.start_processing_btn.configure(state="normal")
        else:
            self.connection_status.configure(
                text="● 未連接", 
                text_color=ColorScheme.ERROR_RED
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
                
                if 'processing_fps' in data:
                    fps = data['processing_fps']
                    self.processing_fps_var.set(f"處理: {fps:.1f} FPS")
                
                if 'detection_fps' in data:
                    fps = data['detection_fps']
                    self.detection_fps_var.set(f"檢測: {fps:.1f} FPS")
                    
            elif event_type == 'camera_stats_updated':
                if data and 'current_fps' in data:
                    fps = data['current_fps']
                    self.camera_fps_var.set(f"相機: {fps:.1f} FPS")
                    
            elif event_type == 'system_status':
                if data:
                    self.status_var.set(f"狀態: {data}")
                    
            elif event_type == 'system_error':
                if data:
                    self.status_var.set(f"錯誤: {data}")
                    
        except Exception as e:
            logging.error(f"處理控制器事件錯誤: {str(e)}")
    
    def run(self):
        """運行主循環"""
        try:
            logging.info("CustomTkinter 優化配色版本開始運行")
            self.root.mainloop()
        except Exception as e:
            logging.error(f"主循環運行錯誤: {str(e)}")
            raise
        finally:
            logging.info("CustomTkinter 優化配色版本已停止")