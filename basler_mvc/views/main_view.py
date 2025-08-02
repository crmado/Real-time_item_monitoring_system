"""
主視圖 - MVC 架構核心
精簡的用戶界面，專注於 Basler 相機和檢測功能
使用樣式分離架構，實現統一的視覺設計管理
"""

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import time
import logging
from typing import Optional, Dict, Any

# 導入優化後的樣式管理系統
from ..styles import ThemeManager, AppleTheme


class MainView:
    """主視圖 - 精簡高性能版本"""
    
    def __init__(self, controller):
        """初始化主視圖"""
        self.controller = controller
        self.root = tk.Tk()
        
        # 視窗設置 - 響應式設計
        self.root.title("🚀 Basler acA640-300gm 精簡高性能系統")
        
        # 獲取螢幕尺寸
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
        
        # 面板狀態控制
        self.left_panel_visible = True
        self.right_panel_visible = True
        self.panels_width_ratio = {'left': 0.2, 'center': 0.6, 'right': 0.2}
        
        # UI 變量
        self.status_var = tk.StringVar(value="狀態: 系統就緒")
        self.camera_fps_var = tk.StringVar(value="相機: 0 FPS")
        self.processing_fps_var = tk.StringVar(value="處理: 0 FPS")
        self.detection_fps_var = tk.StringVar(value="檢測: 0 FPS")
        self.object_count_var = tk.StringVar(value="物件: 0")
        self.camera_info_var = tk.StringVar(value="相機: 未連接")
        self.method_var = tk.StringVar(value="circle")
        
        # 視頻顯示
        self.video_label = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # 顯示設置
        self.display_size = (800, 600)
        self.auto_resize = True
        
        # 參數設置
        self.param_vars = {}
        
        # 相機參數
        self.exposure_var = None
        
        # 初始化優化的主題管理器
        self.theme_manager = ThemeManager(self.root, AppleTheme)
        
        # 創建UI
        self.create_ui()
        
        # 註冊為控制器觀察者
        self.controller.add_view_observer(self.on_controller_event)
        
        logging.info("主視圖初始化完成")
    
    def create_ui(self):
        """創建響應式用戶界面 - 三欄布局"""
        # 主容器 - Liquid Glass風格
        main_container = ttk.Frame(self.root, style='Apple.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 頂部工具欄（固定高度）
        self.create_top_toolbar(main_container)
        
        # 主要內容區域（三欄布局）
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(3, 0))
        
        # 配置三欄權重
        content_frame.grid_columnconfigure(0, weight=20, minsize=200)  # 左側面板 20%
        content_frame.grid_columnconfigure(1, weight=60, minsize=600)  # 中央區域 60%
        content_frame.grid_columnconfigure(2, weight=20, minsize=200)  # 右側面板 20%
        content_frame.grid_rowconfigure(0, weight=1)
        
        # 創建三個主要面板
        self.create_left_panel(content_frame)
        self.create_center_panel(content_frame)
        self.create_right_panel(content_frame)
        
        # 底部狀態欄（固定高度）
        self.create_status_panel(main_container)
        
        # 綁定視窗大小變化事件
        self.root.bind('<Configure>', self.on_window_resize)
        
        # 初始化顯示狀態
        self.root.after(100, self.initialize_display_status)
    
    def create_top_toolbar(self, parent):
        """創建專業級工具欄 - 仿Basler pylon Viewer"""
        # 主工具欄 - 專業設計
        main_toolbar = tk.Frame(parent, bg='#f0f0f0', height=50)
        main_toolbar.pack(fill=tk.X, padx=2, pady=(2, 5))
        main_toolbar.pack_propagate(False)
        
        # 左側控制組
        left_controls = tk.Frame(main_toolbar, bg='#f0f0f0')
        left_controls.pack(side=tk.LEFT, padx=10, pady=8)
        
        # 面板切換按鈕
        self.left_panel_btn = tk.Button(left_controls, text="◀", width=3, height=1,
                                       font=('Arial', 10), relief='flat',
                                       bg='#e0e0e0', activebackground='#d0d0d0',
                                       command=self.toggle_left_panel)
        self.left_panel_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.right_panel_btn = tk.Button(left_controls, text="▶", width=3, height=1,
                                        font=('Arial', 10), relief='flat',
                                        bg='#e0e0e0', activebackground='#d0d0d0',
                                        command=self.toggle_right_panel)
        self.right_panel_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 分隔線
        sep1 = tk.Frame(main_toolbar, bg='#c0c0c0', width=1)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 主要控制按鈕 - 專業樣式
        main_controls = tk.Frame(main_toolbar, bg='#f0f0f0')
        main_controls.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 🚀 一鍵啟動按鈕 - 醒目的藍色
        self.start_btn = tk.Button(main_controls, text="🚀 一鍵啟動", 
                                  font=('Arial', 10, 'bold'),
                                  bg='#007aff', fg='white',
                                  activebackground='#0056cc', activeforeground='white',
                                  relief='flat', borderwidth=0,
                                  padx=15, pady=5,
                                  command=self.auto_start_system)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        # 停止按鈕 - 專業樣式
        self.stop_btn = tk.Button(main_controls, text="⏹️ 停止",
                                 font=('Arial', 10),
                                 bg='#f2f2f7', fg='#007aff',
                                 activebackground='#e5e5ea',
                                 relief='solid', borderwidth=1,
                                 padx=12, pady=5,
                                 command=self.stop_system)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 分隔線
        sep2 = tk.Frame(main_toolbar, bg='#c0c0c0', width=1)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 相機控制組
        camera_controls = tk.Frame(main_toolbar, bg='#f0f0f0')
        camera_controls.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 檢測相機按鈕
        self.detect_btn = tk.Button(camera_controls, text="🔍 檢測相機",
                                   font=('Arial', 9),
                                   bg='#f2f2f7', fg='#007aff',
                                   activebackground='#e5e5ea',
                                   relief='solid', borderwidth=1,
                                   padx=10, pady=4,
                                   command=self.detect_cameras)
        self.detect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 連接相機按鈕
        self.connect_btn = tk.Button(camera_controls, text="🔗 連接",
                                    font=('Arial', 9),
                                    bg='#f2f2f7', fg='#007aff',
                                    activebackground='#e5e5ea',
                                    relief='solid', borderwidth=1,
                                    padx=10, pady=4,
                                    command=self.connect_camera)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # 檢測方法選擇
        method_frame = tk.Frame(camera_controls, bg='#f0f0f0')
        method_frame.pack(side=tk.LEFT)
        
        tk.Label(method_frame, text="檢測方法:", 
                font=('Arial', 9), bg='#f0f0f0').pack(side=tk.LEFT, padx=(0, 5))
        
        # 創建檢測方法下拉框 - 使用ttk保持一致性
        self.detection_method = ttk.Combobox(method_frame, values=["circle"], 
                                           state="readonly", width=8,
                                           font=('Arial', 9))
        self.detection_method.set("circle")
        self.detection_method.pack(side=tk.LEFT)
        self.detection_method.bind('<<ComboboxSelected>>', self.on_method_changed)
        
        # 右側工具組
        right_tools = tk.Frame(main_toolbar, bg='#f0f0f0')
        right_tools.pack(side=tk.RIGHT, padx=10, pady=8)
        
        # 工具按鈕
        self.settings_btn = tk.Button(right_tools, text="⚙️", width=3, height=1,
                                     font=('Arial', 10), relief='flat',
                                     bg='#e0e0e0', activebackground='#d0d0d0',
                                     command=self.open_parameter_dialog)
        self.settings_btn.pack(side=tk.RIGHT, padx=1)
        
        self.stats_btn = tk.Button(right_tools, text="📊", width=3, height=1,
                                  font=('Arial', 10), relief='flat',
                                  bg='#e0e0e0', activebackground='#d0d0d0',
                                  command=self.show_performance_report)
        self.stats_btn.pack(side=tk.RIGHT, padx=1)
        
        self.help_btn = tk.Button(right_tools, text="❓", width=3, height=1,
                                 font=('Arial', 10), relief='flat',
                                 bg='#e0e0e0', activebackground='#d0d0d0',
                                 command=self.show_about)
        self.help_btn.pack(side=tk.RIGHT, padx=1)
    
    def create_left_panel(self, parent):
        """創建左側設備控制面板 - Apple風格"""
        # 左側面板容器
        self.left_panel = ttk.Frame(parent, style='Apple.TFrame')
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # 設備資訊卡片
        device_frame = ttk.LabelFrame(self.left_panel, text="📱 設備", 
                                     style='Apple.TLabelframe')
        device_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 相機資訊顯示 - 現代化樣式
        self.camera_info_label = ttk.Label(device_frame, textvariable=self.camera_info_var, 
                                          style='Apple.TLabel', wraplength=180)
        self.camera_info_label.pack(fill=tk.X, pady=(0, 8))
        
        # 連接狀態指示器 - Apple風格
        status_frame = ttk.Frame(device_frame, style='Apple.TFrame')
        status_frame.pack(fill=tk.X, pady=(0, 8))
        
        # 狀態指示燈容器
        indicator_frame = tk.Frame(status_frame, bg='#ffffff')
        indicator_frame.pack(fill=tk.X)
        
        self.connection_indicator = tk.Label(indicator_frame, text="●", 
                                           font=self.theme_manager.get_font(
                                               self.theme_manager.theme.Typography.FONT_SIZE_BODY,
                                               self.theme_manager.theme.Typography.FONT_WEIGHT_BOLD
                                           ), 
                                           fg=self.theme_manager.get_color('ERROR_RED'), 
                                           bg=self.theme_manager.get_color('BACKGROUND_CARD'))
        self.connection_indicator.pack(side=tk.LEFT)
        
        tk.Label(indicator_frame, text="連接狀態", 
                font=self.theme_manager.get_font(self.theme_manager.theme.Typography.FONT_SIZE_BODY),
                fg=self.theme_manager.get_color('TEXT_SECONDARY'), 
                bg=self.theme_manager.get_color('BACKGROUND_CARD')).pack(side=tk.LEFT, padx=(8, 0))
        
        # 相機設置卡片
        camera_settings_frame = ttk.LabelFrame(self.left_panel, text="🎥 相機設置", 
                                             style='Apple.TLabelframe')
        camera_settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 曝光時間控制 - 優化排版
        exp_frame = ttk.Frame(camera_settings_frame, style='Apple.TFrame')
        exp_frame.pack(fill=tk.X, pady=(0, 8))
        
        exp_label_frame = ttk.Frame(exp_frame, style='Apple.TFrame')
        exp_label_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(exp_label_frame, text="曝光時間 (μs)", style='Apple.TLabel').pack(side=tk.LEFT)
        self.exposure_label = ttk.Label(exp_label_frame, text="1000.0", 
                                       style='AppleSubtitle.TLabel')
        self.exposure_label.pack(side=tk.RIGHT)
        
        self.exposure_var = tk.DoubleVar(value=1000.0)
        exp_scale = ttk.Scale(exp_frame, from_=200, to=10000, 
                             variable=self.exposure_var, orient=tk.HORIZONTAL,
                             style='Apple.Horizontal.TScale',
                             command=self.on_exposure_changed_scale)
        exp_scale.pack(fill=tk.X)
        
        # 檢測開關 - Apple風格
        detection_frame = ttk.Frame(camera_settings_frame, style='Apple.TFrame')
        detection_frame.pack(fill=tk.X, pady=(8, 0))
        
        self.detection_enabled = tk.BooleanVar(value=True)
        detection_check = ttk.Checkbutton(detection_frame, text="啟用即時檢測", 
                                         variable=self.detection_enabled,
                                         command=self.on_detection_toggle)
        detection_check.pack(anchor=tk.W)
    
    def create_center_panel(self, parent):
        """創建專業級相機顯示區域 - 仿Basler官方設計"""
        # 中央面板容器
        self.center_panel = ttk.Frame(parent, style='Apple.TFrame')
        self.center_panel.grid(row=0, column=1, sticky="nsew", 
                              padx=self.theme_manager.get_dimension('SPACING_MD'))
        
        # 主視頻框架 - 專業相機界面
        main_video_frame = ttk.LabelFrame(self.center_panel, text="📷 Basler acA640-300gm - 實時影像", 
                                         style='Apple.TLabelframe')
        main_video_frame.pack(fill=tk.BOTH, expand=True)
        
        # 圖像工具欄 - 仿Basler設計
        self.create_image_toolbar(main_video_frame)
        
        # 影像顯示容器 - 專業設計
        image_container = tk.Frame(main_video_frame, 
                                  bg='#2c2c2c',  # 深色背景像專業軟件
                                  relief='sunken', 
                                  bd=2)
        image_container.pack(fill=tk.BOTH, expand=True, 
                           padx=3, pady=3)
        
        # 視頻顯示區域 - 專業相機風格
        self.video_label = tk.Label(image_container, 
                                   text="Basler acA640-300gm\n\n🎥 Camera Ready\n點擊開始獲取影像", 
                                   anchor=tk.CENTER, 
                                   font=self.theme_manager.get_font(
                                       self.theme_manager.theme.Typography.FONT_SIZE_BODY
                                   ),
                                   background='#1e1e1e',  # 深色背景
                                   foreground='#ffffff',   # 白色文字
                                   relief='flat',
                                   bd=0)
        self.video_label.pack(expand=True, fill=tk.BOTH)
        
        # 圖像信息狀態欄 - 仿Basler設計
        self.create_image_status_bar(main_video_frame)
        
        # 底部性能統計欄
        self.create_performance_bar(main_video_frame)
    
    def create_image_toolbar(self, parent):
        """創建圖像工具欄 - 仿Basler pylon Viewer"""
        toolbar_frame = tk.Frame(parent, bg='#f0f0f0', height=35)
        toolbar_frame.pack(fill=tk.X, padx=2, pady=(2, 0))
        toolbar_frame.pack_propagate(False)
        
        # 左側圖像控制按鈕
        left_tools = tk.Frame(toolbar_frame, bg='#f0f0f0')
        left_tools.pack(side=tk.LEFT, padx=5, pady=3)
        
        # 縮放控制
        self.zoom_fit_btn = tk.Button(left_tools, text="🔍", width=3, height=1,
                                     font=('Arial', 10), relief='flat',
                                     bg='#e0e0e0', activebackground='#d0d0d0',
                                     command=self.zoom_fit)
        self.zoom_fit_btn.pack(side=tk.LEFT, padx=1)
        
        self.zoom_100_btn = tk.Button(left_tools, text="1:1", width=3, height=1,
                                     font=('Arial', 8), relief='flat',
                                     bg='#e0e0e0', activebackground='#d0d0d0',
                                     command=self.zoom_100)
        self.zoom_100_btn.pack(side=tk.LEFT, padx=1)
        
        # 分隔線
        separator1 = tk.Frame(toolbar_frame, bg='#c0c0c0', width=1)
        separator1.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 圖像工具
        image_tools = tk.Frame(toolbar_frame, bg='#f0f0f0')
        image_tools.pack(side=tk.LEFT, padx=5, pady=3)
        
        self.crosshair_btn = tk.Button(image_tools, text="✛", width=3, height=1,
                                      font=('Arial', 10), relief='flat',
                                      bg='#e0e0e0', activebackground='#d0d0d0',
                                      command=self.toggle_crosshair)
        self.crosshair_btn.pack(side=tk.LEFT, padx=1)
        
        self.roi_btn = tk.Button(image_tools, text="□", width=3, height=1,
                                font=('Arial', 10), relief='flat',
                                bg='#e0e0e0', activebackground='#d0d0d0',
                                command=self.toggle_roi)
        self.roi_btn.pack(side=tk.LEFT, padx=1)
        
        # 右側圖像信息
        right_info = tk.Frame(toolbar_frame, bg='#f0f0f0')
        right_info.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 縮放顯示
        self.zoom_label = tk.Label(right_info, text="100%", 
                                  font=('Arial', 9), bg='#f0f0f0')
        self.zoom_label.pack(side=tk.RIGHT, padx=5)
    
    def create_image_status_bar(self, parent):
        """創建圖像信息狀態欄"""
        status_frame = tk.Frame(parent, bg='#e8e8e8', height=25)
        status_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        status_frame.pack_propagate(False)
        
        # 左側圖像信息
        left_info = tk.Frame(status_frame, bg='#e8e8e8')
        left_info.pack(side=tk.LEFT, padx=8, pady=2)
        
        # 分辨率信息
        self.resolution_var = tk.StringVar(value="640 × 480")
        resolution_label = tk.Label(left_info, textvariable=self.resolution_var,
                                   font=('Arial', 9), bg='#e8e8e8')
        resolution_label.pack(side=tk.LEFT)
        
        # 分隔符
        sep1 = tk.Label(left_info, text=" | ", font=('Arial', 9), bg='#e8e8e8')
        sep1.pack(side=tk.LEFT)
        
        # 像素格式
        self.pixel_format_var = tk.StringVar(value="Mono8")
        format_label = tk.Label(left_info, textvariable=self.pixel_format_var,
                               font=('Arial', 9), bg='#e8e8e8')
        format_label.pack(side=tk.LEFT)
        
        # 分隔符
        sep2 = tk.Label(left_info, text=" | ", font=('Arial', 9), bg='#e8e8e8')
        sep2.pack(side=tk.LEFT)
        
        # 位深度
        self.bit_depth_var = tk.StringVar(value="8 bit")
        depth_label = tk.Label(left_info, textvariable=self.bit_depth_var,
                              font=('Arial', 9), bg='#e8e8e8')
        depth_label.pack(side=tk.LEFT)
        
        # 右側狀態信息
        right_info = tk.Frame(status_frame, bg='#e8e8e8')
        right_info.pack(side=tk.RIGHT, padx=8, pady=2)
        
        # 獲取狀態
        self.acquisition_status_var = tk.StringVar(value="就緒")
        status_label = tk.Label(right_info, textvariable=self.acquisition_status_var,
                               font=('Arial', 9), bg='#e8e8e8', fg='#007aff')
        status_label.pack(side=tk.RIGHT)
    
    def create_performance_bar(self, parent):
        """創建底部性能統計欄"""
        perf_frame = tk.Frame(parent, bg='#f8f9fa', height=30)
        perf_frame.pack(fill=tk.X, padx=2, pady=(0, 2))
        perf_frame.pack_propagate(False)
        
        # 左側FPS信息 - 使用圖標
        fps_container = tk.Frame(perf_frame, bg='#f8f9fa')
        fps_container.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 相機FPS
        camera_fps_frame = tk.Frame(fps_container, bg='#f8f9fa')
        camera_fps_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(camera_fps_frame, text="📷", font=('Arial', 10), bg='#f8f9fa').pack(side=tk.LEFT)
        camera_fps_label = tk.Label(camera_fps_frame, textvariable=self.camera_fps_var,
                                   font=('Arial', 9, 'bold'), fg='#34c759', bg='#f8f9fa')
        camera_fps_label.pack(side=tk.LEFT, padx=(2, 0))
        
        # 處理FPS
        processing_fps_frame = tk.Frame(fps_container, bg='#f8f9fa')
        processing_fps_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(processing_fps_frame, text="⚡", font=('Arial', 10), bg='#f8f9fa').pack(side=tk.LEFT)
        processing_fps_label = tk.Label(processing_fps_frame, textvariable=self.processing_fps_var,
                                       font=('Arial', 9, 'bold'), fg='#007aff', bg='#f8f9fa')
        processing_fps_label.pack(side=tk.LEFT, padx=(2, 0))
        
        # 檢測FPS
        detection_fps_frame = tk.Frame(fps_container, bg='#f8f9fa')
        detection_fps_frame.pack(side=tk.LEFT)
        
        tk.Label(detection_fps_frame, text="🔍", font=('Arial', 10), bg='#f8f9fa').pack(side=tk.LEFT)
        detection_fps_label = tk.Label(detection_fps_frame, textvariable=self.detection_fps_var,
                                      font=('Arial', 9, 'bold'), fg='#af52de', bg='#f8f9fa')
        detection_fps_label.pack(side=tk.LEFT, padx=(2, 0))
        
        # 右側物件計數 - 專業顯示
        count_container = tk.Frame(perf_frame, bg='#fff3cd', relief='solid', bd=1)
        count_container.pack(side=tk.RIGHT, padx=10, pady=3)
        
        count_inner = tk.Frame(count_container, bg='#fff3cd')
        count_inner.pack(padx=8, pady=2)
        
        tk.Label(count_inner, text="檢測物件:", 
                font=('Arial', 9), fg='#856404', bg='#fff3cd').pack(side=tk.LEFT)
        
        count_value = tk.Label(count_inner, textvariable=self.object_count_var, 
                              font=('Arial', 11, 'bold'), fg='#d73527', bg='#fff3cd')
        count_value.pack(side=tk.LEFT, padx=(5, 0))
    
    # 圖像控制功能
    def zoom_fit(self):
        """縮放至適合"""
        self.zoom_label.config(text="Fit")
        
    def zoom_100(self):
        """100%縮放"""
        self.zoom_label.config(text="100%")
        
    def toggle_crosshair(self):
        """切換十字線"""
        pass
        
    def toggle_roi(self):
        """切換ROI"""
        pass
    
    def update_video_status(self, status):
        """更新視頻狀態顯示"""
        if hasattr(self, 'acquisition_status_var'):
            self.acquisition_status_var.set(status)
        
        if hasattr(self, 'video_label'):
            if status == "獲取中":
                self.video_label.config(
                    text="📷 正在獲取影像...\n\nBasler acA640-300gm\n實時影像串流中",
                    fg='#00ff00'  # 綠色表示活動
                )
            elif status == "就緒":
                self.video_label.config(
                    text="Basler acA640-300gm\n\n🎥 Camera Ready\n點擊開始獲取影像",
                    fg='#ffffff'
                )
    
    def create_right_panel(self, parent):
        """創建右側參數控制面板 - Apple風格"""
        # 右側面板容器
        self.right_panel = ttk.Frame(parent, style='Apple.TFrame')
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        
        # 批次計數系統（Apple風格）
        self.create_compact_batch_counter()
        
        # 檢測參數調整
        self.create_detection_parameters()
        
        # 實時統計
        self.create_realtime_statistics()
    
    def create_compact_batch_counter(self):
        """創建專業級批次計數器 - 仿Basler pylon Viewer"""
        # 主框架 - 專業樣式
        batch_frame = tk.LabelFrame(self.right_panel, text=" 批次計數 ", 
                                   font=('Arial', 10, 'bold'), fg='#333333',
                                   bg='#f8f9fa', relief='solid', bd=1)
        batch_frame.pack(fill=tk.X, pady=(0, 8), padx=3)
        
        # 當前計數顯示區域 - 專業設計
        count_container = tk.Frame(batch_frame, bg='#ffffff', relief='sunken', bd=1)
        count_container.pack(fill=tk.X, pady=(8, 10), padx=8)
        
        # 標題
        count_title = tk.Label(count_container, text="當前計數", 
                              font=('Arial', 9), fg='#666666', bg='#ffffff')
        count_title.pack(pady=(8, 2))
        
        # 大數字顯示 - 專業樣式
        self.batch_count_var = tk.StringVar(value="000")
        count_display = tk.Label(count_container, 
                               textvariable=self.batch_count_var,
                               font=('Arial', 32, 'bold'), 
                               fg='#007aff', bg='#ffffff')
        count_display.pack(pady=(0, 8))
        
        # 目標設置區域 - 專業布局
        target_container = tk.Frame(batch_frame, bg='#f8f9fa')
        target_container.pack(fill=tk.X, pady=(0, 8), padx=8)
        
        tk.Label(target_container, text="目標數量:", 
                font=('Arial', 9), fg='#333333', bg='#f8f9fa').pack(side=tk.LEFT)
        
        self.target_count_var = tk.IntVar(value=100)
        target_entry = tk.Entry(target_container, textvariable=self.target_count_var,
                               font=('Arial', 10), width=8, justify='center',
                               relief='solid', bd=1)
        target_entry.pack(side=tk.RIGHT)
        target_entry.bind('<Return>', self.on_target_changed)
        
        # 進度顯示區域 - 專業樣式
        progress_container = tk.Frame(batch_frame, bg='#f8f9fa')
        progress_container.pack(fill=tk.X, pady=(0, 8), padx=8)
        
        # 進度條 - 專業外觀
        self.batch_progress = ttk.Progressbar(progress_container,
                                            mode='determinate',
                                            maximum=100, value=0)
        self.batch_progress.pack(fill=tk.X, pady=(0, 5))
        
        # 進度文字 - 居中顯示
        self.progress_text = tk.Label(progress_container, text="0 / 100", 
                                     font=('Arial', 9), fg='#666666', bg='#f8f9fa')
        self.progress_text.pack()
        
        # 控制按鈕區域 - 專業布局
        btn_container = tk.Frame(batch_frame, bg='#f8f9fa')
        btn_container.pack(fill=tk.X, pady=(5, 8), padx=8)
        
        # 開始按鈕 - 醒目設計
        self.start_batch_btn = tk.Button(btn_container, text="▶ 開始",
                                        font=('Arial', 9, 'bold'),
                                        bg='#34c759', fg='white',
                                        activebackground='#28a745',
                                        relief='flat', borderwidth=0,
                                        padx=12, pady=4,
                                        command=self.start_batch)
        self.start_batch_btn.pack(side=tk.LEFT)
        
        # 停止按鈕 - 專業樣式
        self.stop_batch_btn = tk.Button(btn_container, text="⏹ 停止",
                                       font=('Arial', 9),
                                       bg='#f2f2f7', fg='#ff3b30',
                                       activebackground='#e5e5ea',
                                       relief='solid', borderwidth=1,
                                       padx=12, pady=4,
                                       state='disabled',
                                       command=self.stop_batch)
        self.stop_batch_btn.pack(side=tk.RIGHT)
    
    def create_detection_parameters(self):
        """創建檢測參數調整區域 - Apple風格"""
        params_frame = ttk.LabelFrame(self.right_panel, text="🔧 檢測參數", 
                                     style='Apple.TLabelframe')
        params_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 最小面積控制
        min_area_frame = ttk.Frame(params_frame, style='Apple.TFrame')
        min_area_frame.pack(fill=tk.X, pady=(0, 8))
        
        min_label_frame = ttk.Frame(min_area_frame, style='Apple.TFrame')
        min_label_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(min_label_frame, text="最小面積", style='Apple.TLabel').pack(side=tk.LEFT)
        self.min_area_var = tk.IntVar(value=100)
        self.min_area_label = ttk.Label(min_label_frame, text="100", style='AppleSubtitle.TLabel')
        self.min_area_label.pack(side=tk.RIGHT)
        
        min_scale = ttk.Scale(min_area_frame, from_=10, to=2000, 
                             variable=self.min_area_var, orient=tk.HORIZONTAL,
                             style='Apple.Horizontal.TScale',
                             command=self.on_parameter_changed_scale)
        min_scale.pack(fill=tk.X)
        
        # 最大面積控制
        max_area_frame = ttk.Frame(params_frame, style='Apple.TFrame')
        max_area_frame.pack(fill=tk.X)
        
        max_label_frame = ttk.Frame(max_area_frame, style='Apple.TFrame')
        max_label_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(max_label_frame, text="最大面積", style='Apple.TLabel').pack(side=tk.LEFT)
        self.max_area_var = tk.IntVar(value=5000)
        self.max_area_label = ttk.Label(max_label_frame, text="5000", style='AppleSubtitle.TLabel')
        self.max_area_label.pack(side=tk.RIGHT)
        
        max_scale = ttk.Scale(max_area_frame, from_=100, to=20000, 
                             variable=self.max_area_var, orient=tk.HORIZONTAL,
                             style='Apple.Horizontal.TScale',
                             command=self.on_parameter_changed_scale)
        max_scale.pack(fill=tk.X)
    
    def create_realtime_statistics(self):
        """創建實時統計顯示 - Apple風格"""
        stats_frame = ttk.LabelFrame(self.right_panel, text="📊 即時統計", 
                                    style='Apple.TLabelframe')
        stats_frame.pack(fill=tk.BOTH, expand=True)
        
        # 檢測品質顯示
        quality_container = tk.Frame(stats_frame, bg='#ffffff')
        quality_container.pack(fill=tk.X, pady=(0, 10))
        
        quality_title = tk.Label(quality_container, text="檢測品質", 
                               font=self.theme_manager.get_font(
                                   self.theme_manager.theme.Typography.FONT_SIZE_BODY
                               ), 
                               fg=self.theme_manager.get_color('TEXT_SECONDARY'), 
                               bg=self.theme_manager.get_color('BACKGROUND_CARD'))
        quality_title.pack(side=tk.LEFT)
        
        self.quality_var = tk.StringVar(value="良好")
        self.quality_label = tk.Label(quality_container, textvariable=self.quality_var, 
                                     font=self.theme_manager.get_font(
                                         self.theme_manager.theme.Typography.FONT_SIZE_BODY,
                                         self.theme_manager.theme.Typography.FONT_WEIGHT_BOLD
                                     ), 
                                     fg=self.theme_manager.get_color('SUCCESS_GREEN'), 
                                     bg=self.theme_manager.get_color('BACKGROUND_CARD'))
        self.quality_label.pack(side=tk.RIGHT)
        
        # 性能統計
        perf_container = tk.Frame(stats_frame, bg=self.theme_manager.get_color('BACKGROUND_CARD'))
        perf_container.pack(fill=tk.X)
        
        # 檢測FPS顯示
        fps_label = tk.Label(perf_container, textvariable=self.detection_fps_var, 
                            font=self.theme_manager.get_font(
                                self.theme_manager.theme.Typography.FONT_SIZE_BODY
                            ), 
                            fg=self.theme_manager.get_color('INFO_PURPLE'), 
                            bg=self.theme_manager.get_color('BACKGROUND_CARD'))
        fps_label.pack(anchor=tk.W, pady=2)
    
    def toggle_left_panel(self):
        """切換左側面板顯示/隱藏"""
        if self.left_panel_visible:
            self.left_panel.grid_remove()
            self.left_panel_visible = False
        else:
            self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
            self.left_panel_visible = True
    
    def toggle_right_panel(self):
        """切換右側面板顯示/隱藏"""
        if self.right_panel_visible:
            self.right_panel.grid_remove()
            self.right_panel_visible = False
        else:
            self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(2, 0))
            self.right_panel_visible = True
    
    def on_window_resize(self, event):
        """處理視窗大小變化"""
        if event.widget == self.root:
            # 根據視窗寬度調整面板可見性
            window_width = self.root.winfo_width()
            
            if window_width < 1000:
                # 小視窗：只顯示中央面板
                if self.left_panel_visible:
                    self.toggle_left_panel()
                if self.right_panel_visible:
                    self.toggle_right_panel()
            elif window_width < 1200:
                # 中等視窗：顯示中央和右側面板
                if self.left_panel_visible:
                    self.toggle_left_panel()
                if not self.right_panel_visible:
                    self.toggle_right_panel()
            else:
                # 大視窗：顯示所有面板
                if not self.left_panel_visible:
                    self.toggle_left_panel()
                if not self.right_panel_visible:
                    self.toggle_right_panel()
    
    def on_exposure_changed_scale(self, value):
        """曝光滑塊變化回調"""
        try:
            exposure_time = float(value)
            self.exposure_label.config(text=f"{exposure_time:.1f}")
            success = self.controller.set_exposure_time(exposure_time)
            if success:
                self.status_var.set(f"狀態: 曝光時間已調整為 {exposure_time:.1f}μs")
        except Exception as e:
            logging.error(f"調整曝光時間錯誤: {str(e)}")
    
    def on_parameter_changed_scale(self, value):
        """檢測參數滑塊變化回調"""
        try:
            # 更新顯示的數值標籤
            if hasattr(self, 'min_area_label'):
                self.min_area_label.config(text=str(self.min_area_var.get()))
            if hasattr(self, 'max_area_label'):
                self.max_area_label.config(text=str(self.max_area_var.get()))
            
            # 更新檢測參數
            params = {
                'min_area': self.min_area_var.get(),
                'max_area': self.max_area_var.get()
            }
            self.controller.update_detection_parameters(params)
        except Exception as e:
            logging.error(f"更新檢測參數錯誤: {str(e)}")
    
        
    # ==================== 批次控制方法 ====================
    
    def start_batch(self):
        """開始新批次"""
        try:
            if hasattr(self, 'batch_mode') and self.batch_mode != 'running':
                self.batch_mode = 'running'
                self.current_batch_count = 0
                self.batch_start_time = time.time()
                
                # 更新UI狀態
                if hasattr(self, 'start_batch_btn'):
                    self.start_batch_btn.config(state='disabled')
                if hasattr(self, 'stop_batch_btn'):
                    self.stop_batch_btn.config(state='normal')
                
                # 通知控制器開始批次檢測
                if hasattr(self.controller, 'start_batch_detection'):
                    self.controller.start_batch_detection()
                    
                logging.info(f"✅ 開始新批次，目標: {self.target_count_var.get()}")
                
        except Exception as e:
            logging.error(f"開始批次錯誤: {str(e)}")
    
    def stop_batch(self):
        """停止當前批次"""
        try:
            if hasattr(self, 'batch_mode') and self.batch_mode == 'running':
                self.batch_mode = 'idle'
                
                # 更新UI狀態
                if hasattr(self, 'start_batch_btn'):
                    self.start_batch_btn.config(state='normal')
                if hasattr(self, 'stop_batch_btn'):
                    self.stop_batch_btn.config(state='disabled')
                
                # 通知控制器停止檢測
                if hasattr(self.controller, 'stop_batch_detection'):
                    self.controller.stop_batch_detection()
                    
                logging.info(f"⏹️ 手動停止批次，當前計數: {getattr(self, 'current_batch_count', 0)}")
                
        except Exception as e:
            logging.error(f"停止批次錯誤: {str(e)}")
    
    def on_target_changed(self):
        """目標數量改變回調"""
        try:
            target = self.target_count_var.get()
            current_count = getattr(self, 'current_batch_count', 0)
            
            # 更新進度條
            if hasattr(self, 'batch_progress'):
                progress_percentage = (current_count / target * 100) if target > 0 else 0
                self.batch_progress.config(value=progress_percentage)
                
            logging.info(f"目標數量已更改為: {target}")
            
        except Exception as e:
            logging.error(f"更改目標數量錯誤: {str(e)}")
    
    def initialize_display_status(self):
        """初始化顯示狀態"""
        try:
            # 初始化批次狀態
            self.batch_mode = 'idle'
            self.current_batch_count = 0
            self.total_batches_today = 0
            self.total_items_today = 0
            self.batch_start_time = None
            
            # 設置初始檢測品質
            if hasattr(self, 'quality_var') and self.quality_var:
                self.quality_var.set("良好")
            
            logging.info("✅ 響應式UI系統初始化完成")
            
        except Exception as e:
            logging.debug(f"初始化顯示狀態錯誤: {str(e)}")
    
    def create_status_panel(self, parent):
        """創建專業級系統狀態欄 - 仿Basler pylon Viewer"""
        # 主狀態欄 - 專業設計
        main_status_bar = tk.Frame(parent, bg='#e8e8e8', height=40)
        main_status_bar.pack(fill=tk.X, pady=(5, 0))
        main_status_bar.pack_propagate(False)
        
        # 左側系統狀態
        left_status = tk.Frame(main_status_bar, bg='#e8e8e8')
        left_status.pack(side=tk.LEFT, padx=10, pady=8)
        
        # 狀態指示器
        status_indicator = tk.Frame(left_status, bg='#e8e8e8')
        status_indicator.pack(side=tk.LEFT)
        
        tk.Label(status_indicator, text="狀態:", 
                font=('Arial', 9), bg='#e8e8e8', fg='#333333').pack(side=tk.LEFT)
        
        self.status_display = tk.Label(status_indicator, textvariable=self.status_var,
                                     font=('Arial', 9, 'bold'), 
                                     bg='#e8e8e8', fg='#34c759')
        self.status_display.pack(side=tk.LEFT, padx=(5, 15))
        
        # 相機信息
        camera_info = tk.Frame(left_status, bg='#e8e8e8')
        camera_info.pack(side=tk.LEFT)
        
        tk.Label(camera_info, text="相機:", 
                font=('Arial', 9), bg='#e8e8e8', fg='#333333').pack(side=tk.LEFT)
        
        self.camera_display = tk.Label(camera_info, textvariable=self.camera_info_var,
                                     font=('Arial', 9), 
                                     bg='#e8e8e8', fg='#666666')
        self.camera_display.pack(side=tk.LEFT, padx=(5, 0))
        
        # 中間性能統計 - 專業布局
        center_stats = tk.Frame(main_status_bar, bg='#e8e8e8')
        center_stats.pack(side=tk.LEFT, expand=True, padx=20, pady=8)
        
        # FPS統計區域
        fps_container = tk.Frame(center_stats, bg='#e8e8e8')
        fps_container.pack()
        
        # 相機FPS
        camera_fps_frame = tk.Frame(fps_container, bg='#e8e8e8')
        camera_fps_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(camera_fps_frame, text="相機:", 
                font=('Arial', 9), bg='#e8e8e8', fg='#333333').pack(side=tk.LEFT)
        camera_fps_display = tk.Label(camera_fps_frame, textvariable=self.camera_fps_var,
                                     font=('Arial', 9, 'bold'), 
                                     bg='#e8e8e8', fg='#34c759')
        camera_fps_display.pack(side=tk.LEFT, padx=(3, 0))
        
        # 處理FPS
        processing_fps_frame = tk.Frame(fps_container, bg='#e8e8e8')
        processing_fps_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(processing_fps_frame, text="處理:", 
                font=('Arial', 9), bg='#e8e8e8', fg='#333333').pack(side=tk.LEFT)
        processing_fps_display = tk.Label(processing_fps_frame, textvariable=self.processing_fps_var,
                                         font=('Arial', 9, 'bold'), 
                                         bg='#e8e8e8', fg='#007aff')
        processing_fps_display.pack(side=tk.LEFT, padx=(3, 0))
        
        # 檢測FPS
        detection_fps_frame = tk.Frame(fps_container, bg='#e8e8e8')
        detection_fps_frame.pack(side=tk.LEFT)
        
        tk.Label(detection_fps_frame, text="檢測:", 
                font=('Arial', 9), bg='#e8e8e8', fg='#333333').pack(side=tk.LEFT)
        detection_fps_display = tk.Label(detection_fps_frame, textvariable=self.detection_fps_var,
                                        font=('Arial', 9, 'bold'), 
                                        bg='#e8e8e8', fg='#af52de')
        detection_fps_display.pack(side=tk.LEFT, padx=(3, 0))
        
        # 右側時間戳
        right_status = tk.Frame(main_status_bar, bg='#e8e8e8')
        right_status.pack(side=tk.RIGHT, padx=10, pady=8)
        
        import time
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_display = tk.Label(right_status, text=current_time,
                                   font=('Arial', 9), 
                                   bg='#e8e8e8', fg='#666666')
        self.time_display.pack()
        
        # 定時更新時間
        self.update_time_display()
    
    def update_time_display(self):
        """更新時間顯示"""
        try:
            import time
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(self, 'time_display'):
                self.time_display.config(text=current_time)
            # 每秒更新一次時間
            self.root.after(1000, self.update_time_display)
        except Exception as e:
            logging.debug(f"更新時間顯示錯誤: {str(e)}")
    
    # ==================== 事件處理 ====================
    
    def on_controller_event(self, event_type: str, data: Any = None):
        """處理控制器事件"""
        try:
            # 線程安全的UI更新
            self.root.after(0, self._handle_event, event_type, data)
        except Exception as e:
            logging.error(f"處理事件錯誤: {str(e)}")
    
    def _handle_event(self, event_type: str, data: Any = None):
        """處理事件的內部方法"""
        try:
            if event_type == 'system_status':
                self.status_var.set(f"狀態: {data}")
            
            elif event_type == 'system_error':
                self.status_var.set(f"錯誤: {data}")
                messagebox.showerror("系統錯誤", data)
            
            elif event_type == 'camera_cameras_detected':
                self._on_cameras_detected(data)
            
            elif event_type == 'camera_camera_connected':
                self._on_camera_connected(data)
                self.update_video_status("就緒")
            
            elif event_type == 'frame_processed':
                self._on_frame_processed(data)
            
            elif event_type.startswith('camera_') or event_type.startswith('detection_'):
                self._update_status_display()
                
        except Exception as e:
            logging.error(f"處理事件錯誤: {str(e)}")
    
    def _on_cameras_detected(self, cameras):
        """處理相機檢測結果"""
        if not cameras:
            messagebox.showwarning("檢測結果", "未檢測到 Basler 相機")
            return
        
        info = f"檢測到 {len(cameras)} 台相機:\n\n"
        for i, camera in enumerate(cameras):
            status = "✅ 目標型號" if camera.get('is_target', False) else "⚠️ 其他型號"
            info += f"相機 {i+1}: {camera['model']} ({status})\n"
            info += f"序列號: {camera['serial']}\n\n"
        
        messagebox.showinfo("檢測結果", info)
    
    def _on_camera_connected(self, camera_info):
        """處理相機連接"""
        model = camera_info.get('model', 'Unknown')
        serial = camera_info.get('serial', 'N/A')
        self.camera_info_var.set(f"相機: {model} ({serial})")
    
    def _on_frame_processed(self, data):
        """處理幀更新 - 批次模式"""
        try:
            frame = data.get('frame')
            if frame is not None:
                with self.frame_lock:
                    self.current_frame = frame
                    
                # 立即更新視頻顯示 - 始終更新畫面
                self.root.after(0, self._update_video_display)
                
                # 第一幀時的特殊日誌
                if hasattr(self, '_first_frame_logged') == False:
                    self._first_frame_logged = True
                    logging.info(f"視圖收到第一幀，尺寸: {frame.shape}")
            
            # 處理批次計數邏輯
            count = data.get('object_count', 0)
            self.object_count_var.set(f"物件: {count}")
            
            # 只有在批次運行時才更新計數
            if self.batch_mode == 'running':
                # 檢測到新物件時增加批次計數
                if count > 0:
                    self.current_batch_count += count
                    self._update_batch_display()
                    
                    # 檢查是否達到目標數量
                    target = self.target_count_var.get()
                    if self.current_batch_count >= target:
                        # 達到目標，完成批次
                        self.complete_batch()
            
            # 安全地更新檢測品質顯示（即使停止檢測也顯示）
            try:
                self._update_detection_quality(data)
            except Exception as e:
                logging.debug(f"更新檢測品質錯誤: {str(e)}")
            
        except Exception as e:
            logging.error(f"處理幀更新錯誤: {str(e)}")
    
    def _update_batch_display(self):
        """更新批次顯示"""
        try:
            # 更新計數顯示
            self.batch_count_var.set(f"{self.current_batch_count:03d}")
            
            # 更新進度條
            target = self.target_count_var.get()
            progress_percentage = min((self.current_batch_count / target * 100), 100) if target > 0 else 0
            self.batch_progress.config(value=progress_percentage)
            
            # 更新進度文字
            self.progress_text.config(text=f"{self.current_batch_count} / {target}")
            
            # 更新狀態（接近完成時改變顏色）
            if self.current_batch_count >= target * 0.9:
                self.batch_status_indicator.config(fg='#f39c12')  # 橙色警告
                self.batch_status_text.config(text="即將完成")
            
        except Exception as e:
            logging.error(f"更新批次顯示錯誤: {str(e)}")
    
    
    def _update_detection_quality(self, data):
        """更新檢測品質指示"""
        try:
            detection_fps = data.get('detection_fps', 0)
            processing_fps = data.get('processing_fps', 0)
            
            if detection_fps > 500 and processing_fps > 200:
                quality = "極佳"
                color = '#2ecc71'  # 綠色
            elif detection_fps > 200 and processing_fps > 100:
                quality = "良好"
                color = '#3498db'  # 藍色
            elif detection_fps > 50:
                quality = "一般"
                color = '#f39c12'  # 橙色
            else:
                quality = "需優化"
                color = '#e74c3c'  # 紅色
            
            self.quality_var.set(quality)
            # 動態更新品質標籤顏色
            quality_widgets = [w for w in self.root.winfo_children() if isinstance(w, tk.Label)]
            for widget in quality_widgets:
                if hasattr(widget, 'textvariable') and widget['textvariable'] == str(self.quality_var):
                    widget.config(foreground=color)
                    break
                    
        except Exception as e:
            logging.error(f"更新檢測品質錯誤: {str(e)}")
    
    def _update_status_display(self):
        """更新狀態顯示"""
        try:
            status = self.controller.get_system_status()
            
            self.camera_fps_var.set(f"相機: {status['camera_fps']:.1f} FPS")
            self.processing_fps_var.set(f"處理: {status['processing_fps']:.1f} FPS")
            self.detection_fps_var.set(f"檢測: {status['detection_fps']:.1f} FPS")
            
        except Exception as e:
            logging.error(f"更新狀態顯示錯誤: {str(e)}")
    
    def _update_video_display(self):
        """更新視頻顯示"""
        try:
            with self.frame_lock:
                if self.current_frame is None:
                    return
                frame = self.current_frame.copy()
            
            # 調整大小
            h, w = frame.shape[:2]
            max_w, max_h = self.display_size
            
            if w > max_w or h > max_h:
                scale = min(max_w/w, max_h/h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h))
            
            # 轉換為 Tkinter 格式
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            elif len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            pil_image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(pil_image)
            
            # 更新顯示
            if self.video_label and self.video_label.winfo_exists():
                self.video_label.configure(image=photo, text="")  # 清除文字
                self.video_label.image = photo  # 保持引用避免垃圾回收
                
                # 第一次顯示幀時的日誌
                if not hasattr(self, '_first_display_logged'):
                    self._first_display_logged = True
                    logging.info("成功顯示第一幀到UI")
                
        except Exception as e:
            logging.error(f"更新視頻顯示錯誤: {str(e)}")
    
    # ==================== 控制方法 ====================
    
    def detect_cameras(self):
        """檢測相機"""
        self.controller.detect_cameras()
    
    def connect_camera(self):
        """連接相機"""
        self.controller.connect_camera()
    
    def auto_start_system(self):
        """一鍵啟動系統 - 自動檢測並啟動相機"""
        self.update_video_status("獲取中")
        self.controller.auto_start_camera_system()
    
    def start_system(self):
        """啟動系統"""
        self.update_video_status("獲取中")
        self.controller.start_system()
    
    def stop_system(self):
        """停止系統"""
        self.update_video_status("就緒")
        self.controller.stop_system()
    
    def restart_system(self):
        """重啟系統"""
        self.controller.restart_system()
    
    def on_method_changed(self, event=None):
        """檢測方法改變"""
        method = self.method_var.get()
        self.controller.set_detection_method(method)
    
    def on_detection_toggle(self):
        """檢測開關切換"""
        enabled = self.detection_enabled.get()
        self.controller.toggle_detection(enabled)
    
    def on_parameter_changed(self):
        """參數改變"""
        params = {
            'min_area': self.min_area_var.get(),
            'max_area': self.max_area_var.get()
        }
        self.controller.update_detection_parameters(params)
    
    def on_exposure_changed(self):
        """曝光時間改變"""
        try:
            exposure_time = self.exposure_var.get()
            success = self.controller.set_exposure_time(exposure_time)
            if success:
                self.status_var.set(f"狀態: 曝光時間已調整為 {exposure_time}μs")
            else:
                self.status_var.set("狀態: 曝光時間調整失敗")
        except Exception as e:
            logging.error(f"調整曝光時間錯誤: {str(e)}")
    
    def open_parameter_dialog(self):
        """打開參數設置對話框"""
        # 簡化版參數對話框
        dialog = tk.Toplevel(self.root)
        dialog.title("參數設置")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        
        # 使對話框模態
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="檢測參數設置", font=('Arial', 12, 'bold')).pack(pady=10)
        
        # 參數框架
        param_frame = ttk.LabelFrame(dialog, text="參數", padding=10)
        param_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 這裡可以添加更多參數設置
        ttk.Label(param_frame, text="當前已支援在主界面快速調整參數").pack()
        
        # 按鈕
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="確定", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def show_performance_report(self):
        """顯示性能報告"""
        try:
            report = self.controller.get_performance_report()
            
            report_text = "🚀 系統性能報告\n"
            report_text += "=" * 50 + "\n\n"
            
            # 相機性能
            cam_perf = report['camera_performance']
            report_text += f"📹 相機性能: {cam_perf['grade']}\n"
            report_text += f"   FPS: {cam_perf['fps']:.1f}\n"
            report_text += f"   總幀數: {cam_perf['total_frames']}\n\n"
            
            # 處理性能
            proc_perf = report['processing_performance']
            report_text += f"⚙️ 處理性能: {proc_perf['grade']}\n"
            report_text += f"   FPS: {proc_perf['fps']:.1f}\n"
            report_text += f"   總幀數: {proc_perf['total_frames']}\n\n"
            
            # 檢測性能
            det_perf = report['detection_performance']
            report_text += f"🔍 檢測性能:\n"
            report_text += f"   FPS: {det_perf['fps']:.1f}\n"
            report_text += f"   物件數: {det_perf['object_count']}\n"
            report_text += f"   方法: {det_perf['method']}\n\n"
            
            # 系統效率
            sys_eff = report['system_efficiency']
            report_text += f"📊 系統效率:\n"
            report_text += f"   處理效率: {sys_eff['fps_ratio']:.2%}\n"
            report_text += f"   運行時間: {sys_eff['elapsed_time']:.1f}s"
            
            messagebox.showinfo("性能報告", report_text)
            
        except Exception as e:
            messagebox.showerror("錯誤", f"生成性能報告失敗: {str(e)}")
    
    def show_about(self):
        """顯示關於信息"""
        about_text = """🚀 Basler acA640-300gm 精簡高性能系統

🎯 專為極致性能設計:
• 型號: acA640-300gm (640×480)
• 像素格式: Mono8
• 目標FPS: 280+

🔥 核心特色:
✓ 精簡 MVC 架構
✓ 高性能多線程處理
✓ 實時影像檢測
✓ 零延遲幀獲取

⚡ 檢測方法:
• 圓形檢測 (霍夫變換)
• 輪廓檢測 (形態學)

🏆 這是工業相機處理的精簡高效版本！
專注核心功能，追求極致性能。"""
        
        messagebox.showinfo("關於系統", about_text)
    
    # ==================== 生命週期 ====================
    
    def run(self):
        """運行主視圖"""
        # 設置關閉處理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 啟動主循環
        self.root.mainloop()
    
    def on_closing(self):
        """關閉處理"""
        try:
            # 確認關閉
            if messagebox.askokcancel("確認", "確定要關閉系統嗎？"):
                self.controller.cleanup()
                self.root.destroy()
        except Exception as e:
            logging.error(f"關閉錯誤: {str(e)}")
            self.root.destroy()