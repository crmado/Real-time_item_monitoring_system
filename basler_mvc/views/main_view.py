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
        
        # 簡化的面板配置 - 固定顯示所有面板
        self.panels_width_ratio = {'left': 0.2, 'center': 0.6, 'right': 0.2}
        
        # UI 變量
        self.status_var = tk.StringVar(value="狀態: 系統就緒")
        self.camera_fps_var = tk.StringVar(value="相機: 0 FPS")
        self.processing_fps_var = tk.StringVar(value="處理: 0 FPS")
        self.detection_fps_var = tk.StringVar(value="檢測: 0 FPS")
        self.object_count_var = tk.StringVar(value="物件: 0")
        self.camera_info_var = tk.StringVar(value="相機: 未連接")
        self.method_var = tk.StringVar(value="circle")
        
        # FPS平滑顯示緩衝區
        self.fps_history = {
            'camera': [],
            'processing': [],
            'detection': []
        }
        self.fps_update_counter = 0
        
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
        
        # 初始化設備列表
        self.refresh_device_list()
        
        # 初始化UI狀態
        self.update_connection_ui()
        
        # 註冊為控制器觀察者
        self.controller.add_view_observer(self.on_controller_event)
        
        logging.info("主視圖初始化完成")
    
    def create_ui(self):
        """創建響應式用戶界面 - 三欄布局"""
        # 主容器 - 緊湊布局，最大化視頻區域
        main_container = ttk.Frame(self.root, style='Apple.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 頂部工具欄（固定高度）
        self.create_top_toolbar(main_container)
        
        # 主要內容區域（三欄布局）
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(1, 0))
        
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
        
        # 初始化顯示狀態
        self.root.after(100, self.initialize_display_status)
    
    def create_top_toolbar(self, parent):
        """創建緊湊專業工具欄 - 最大化中間區域"""
        # 主工具欄 - 緊湊設計
        main_toolbar = tk.Frame(parent, bg='#f0f0f0', height=35)
        main_toolbar.pack(fill=tk.X, padx=1, pady=(1, 2))
        main_toolbar.pack_propagate(False)
        
        # 左側控制組
        left_controls = tk.Frame(main_toolbar, bg='#f0f0f0')
        left_controls.pack(side=tk.LEFT, padx=8, pady=5)
        
        # 移除不必要的面板切換按鈕 - 簡化界面
        
        # 分隔線
        sep1 = tk.Frame(main_toolbar, bg='#c0c0c0', width=1)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 連接開關控制
        connection_control = tk.Frame(main_toolbar, bg='#f0f0f0')
        connection_control.pack(side=tk.LEFT, padx=8, pady=3)
        
        # 連接開關按鈕（仿iOS開關樣式）
        self.connection_switch_frame = tk.Frame(connection_control, bg='#f0f0f0')
        self.connection_switch_frame.pack(side=tk.LEFT)
        
        tk.Label(self.connection_switch_frame, text="連線:", 
                font=('Arial', 11), bg='#f0f0f0', fg='#333333').pack(side=tk.LEFT, padx=(0, 8))
        
        # 開關按鈕
        self.connection_switch = tk.Button(self.connection_switch_frame,
                                         text="○",
                                         font=('Arial', 16),
                                         bg='#e0e0e0', fg='#999999',
                                         activebackground='#d0d0d0',
                                  relief='flat', borderwidth=0,
                                         width=3, height=1,
                                         command=self.toggle_connection_switch)
        self.connection_switch.pack(side=tk.LEFT)
        
        # 儲存開關狀態
        self.connection_switch_on = False
        
        # 分隔線
        sep2 = tk.Frame(main_toolbar, bg='#c0c0c0', width=1)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 啟動/停止控制組
        start_controls = tk.Frame(main_toolbar, bg='#f0f0f0')
        start_controls.pack(side=tk.LEFT, padx=8, pady=3)
        
        # 啟動處理按鈕（僅負責啟動/停止影像處理）
        self.start_processing_btn = tk.Button(start_controls, text="▶️ 啟動處理",
                                            font=('Arial', 12),
                                   bg='#f2f2f7', fg='#007aff',
                                   activebackground='#e5e5ea',
                                   relief='solid', borderwidth=1,
                                            padx=12, pady=6,
                                            command=self.toggle_processing,
                                            state='disabled')  # 初始禁用
        self.start_processing_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 儲存處理狀態
        self.is_processing_active = False
        
        # 檢測方法選擇
        method_frame = tk.Frame(start_controls, bg='#f0f0f0')
        method_frame.pack(side=tk.LEFT)
        
        tk.Label(method_frame, text="檢測方法:", 
                font=('Arial', 12), bg='#f0f0f0').pack(side=tk.LEFT, padx=(0, 5))  # 字體從9增大到12
        
        # 創建檢測方法下拉框 - 使用ttk保持一致性，字體增大
        self.detection_method = ttk.Combobox(method_frame, values=["circle"], 
                                           state="readonly", width=8,
                                           font=('Arial', 12))  # 字體從9增大到12
        self.detection_method.set("circle")
        self.detection_method.pack(side=tk.LEFT)
        self.detection_method.bind('<<ComboboxSelected>>', self.on_method_changed)
        
        # 右側工具組
        right_tools = tk.Frame(main_toolbar, bg='#f0f0f0')
        right_tools.pack(side=tk.RIGHT, padx=8, pady=5)
        
        # 工具按鈕 - 簡化版本，只保留設定按鈕
        self.settings_btn = tk.Button(right_tools, text="⚙️", width=3, height=1,
                                     font=('Arial', 14), relief='flat',
                                     bg='#e0e0e0', activebackground='#d0d0d0',
                                     command=self.open_parameter_dialog)
        self.settings_btn.pack(side=tk.RIGHT, padx=1)
        
        # 移除不必要的性能報告和關於按鈕，簡化界面
    
    def create_left_panel(self, parent):
        """創建左側設備控制面板 - Apple風格"""
        # 左側面板容器
        self.left_panel = ttk.Frame(parent, style='Apple.TFrame')
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # 設備資訊 - 仿Basler專業設計
        device_frame = ttk.LabelFrame(self.left_panel, text="設備", 
                                     style='Apple.TLabelframe')
        device_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 設備列表區域
        device_list_frame = tk.Frame(device_frame, bg='#ffffff')
        device_list_frame.pack(fill=tk.X, pady=(5, 8))
        
        # 設備列表（用Listbox實現）
        listbox_frame = tk.Frame(device_list_frame, bg='#ffffff', relief='sunken', bd=1)
        listbox_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.device_listbox = tk.Listbox(listbox_frame, 
                                       height=3,
                                       font=('Arial', 10),
                                       bg='#ffffff', 
                                       fg='#333333',
                                       selectbackground='#007aff',
                                       selectforeground='white',
                                       activestyle='none',
                                       borderwidth=0,
                                       highlightthickness=0)
        self.device_listbox.pack(fill=tk.X, padx=2, pady=2)
        
        # 綁定雙擊事件
        self.device_listbox.bind('<Double-Button-1>', self.on_device_double_click)
        
        # 提示文字
        hint_label = tk.Label(device_list_frame, 
                            text="雙擊設備進行連接",
                            font=('Arial', 9), 
                            fg='#999999', bg='#ffffff')
        hint_label.pack(anchor='w')
        
        # 分隔線
        separator = tk.Frame(device_frame, height=1, bg='#e0e0e0')
        separator.pack(fill=tk.X, pady=(5, 5))
        
        # 連接狀態顯示
        status_frame = tk.Frame(device_frame, bg='#ffffff')
        status_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.connection_status_label = tk.Label(status_frame, 
                                              text="● 未連接", 
                                              font=('Arial', 10),
                                              fg='#ff3b30', 
                                              bg='#ffffff')
        self.connection_status_label.pack(side=tk.LEFT)
        
        # 儲存連接狀態和設備列表
        self.is_camera_connected = False
        self.detected_cameras = []
        self.selected_camera_index = -1
        
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
        
        # 輸入框和滑動條組合
        exp_input_frame = ttk.Frame(exp_label_frame, style='Apple.TFrame')
        exp_input_frame.pack(side=tk.RIGHT)
        
        self.exposure_var = tk.DoubleVar(value=1000.0)
        self.exposure_entry = ttk.Entry(exp_input_frame, textvariable=self.exposure_var, 
                                       width=8, font=('Arial', 12))
        self.exposure_entry.pack(side=tk.LEFT)
        self.exposure_entry.bind('<Return>', self.on_exposure_entry_changed)
        self.exposure_entry.bind('<FocusOut>', self.on_exposure_entry_changed)
        
        # 初始化更新標誌 - 避免初始化時觸發回調
        self._exposure_updating = False
        self._min_area_updating = False  
        self._max_area_updating = False
        exp_scale = ttk.Scale(exp_frame, from_=100, to=50000,
                             variable=self.exposure_var, orient=tk.HORIZONTAL,
                             style='Apple.Horizontal.TScale',
                             command=self.on_exposure_changed_scale)
        exp_scale.pack(fill=tk.X, pady=(5, 0))
        
        # 檢測開關 - Apple風格
        detection_frame = ttk.Frame(camera_settings_frame, style='Apple.TFrame')
        detection_frame.pack(fill=tk.X, pady=(8, 0))
        
        self.detection_enabled = tk.BooleanVar(value=True)
        detection_check = ttk.Checkbutton(detection_frame, text="啟用即時檢測", 
                                         variable=self.detection_enabled,
                                         command=self.on_detection_toggle)
        detection_check.pack(anchor=tk.W)
    
    def create_center_panel(self, parent):
        """創建滿版專業相機顯示區域 - 完全仿Basler pylon Viewer"""
        # 中央面板容器 - 移除邊距，滿版顯示
        self.center_panel = tk.Frame(parent, bg='#f0f0f0')
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=1, pady=1)
        
        # 主視頻框架 - 緊湊標題
        main_video_frame = tk.LabelFrame(self.center_panel, 
                                        text="📷 Basler acA640-300gm - 實時影像", 
                                        font=('Arial', 9, 'bold'),
                                        fg='#333333', bg='#f0f0f0',
                                        relief='solid', bd=1)
        main_video_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # 圖像工具欄 - 超緊湊設計
        self.create_compact_image_toolbar(main_video_frame)
        
        # 影像顯示容器 - 滿版設計，最小邊距
        image_container = tk.Frame(main_video_frame, 
                                  bg='#2c2c2c',  # 深色背景
                                  relief='sunken', 
                                  bd=1)
        image_container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # 視頻顯示區域 - 完全滿版
        self.video_label = tk.Label(image_container, 
                                   text="Basler acA640-300gm\n\n🎥 Camera Ready\n點擊開始獲取影像", 
                                   anchor=tk.CENTER, 
                                   font=('Arial', 12),
                                   background='#1e1e1e',  # 深色背景
                                   foreground='#ffffff',   # 白色文字
                                   relief='flat',
                                   bd=0)
        self.video_label.pack(expand=True, fill=tk.BOTH)
    
        # 圖像信息狀態欄 - 超緊湊
        self.create_compact_image_status_bar(main_video_frame)
        
        # 底部性能統計欄 - 緊湊版
        self.create_compact_performance_bar(main_video_frame)
    
    def create_compact_image_toolbar(self, parent):
        """創建超緊湊圖像工具欄 - 最小化空間占用"""
        toolbar_frame = tk.Frame(parent, bg='#f0f0f0', height=25)
        toolbar_frame.pack(fill=tk.X, padx=1, pady=0)
        toolbar_frame.pack_propagate(False)
        
        # 左側工具按鈕 - 超緊湊
        left_tools = tk.Frame(toolbar_frame, bg='#f0f0f0')
        left_tools.pack(side=tk.LEFT, padx=3, pady=2)
        
        # 縮放控制 - 小型按鈕
        self.zoom_fit_btn = tk.Button(left_tools, text="🔍", width=2, height=1,
                                     font=('Arial', 11), relief='flat',
                                     bg='#e0e0e0', activebackground='#d0d0d0',
                                     command=self.zoom_fit)
        self.zoom_fit_btn.pack(side=tk.LEFT, padx=1)
        
        self.zoom_100_btn = tk.Button(left_tools, text="1:1", width=2, height=1,
                                     font=('Arial', 7), relief='flat',
                                     bg='#e0e0e0', activebackground='#d0d0d0',
                                     command=self.zoom_100)
        self.zoom_100_btn.pack(side=tk.LEFT, padx=1)
        
        # 圖像工具 - 緊湊版
        self.crosshair_btn = tk.Button(left_tools, text="✛", width=2, height=1,
                                      font=('Arial', 11), relief='flat',
                                      bg='#e0e0e0', activebackground='#d0d0d0',
                                      command=self.toggle_crosshair)
        self.crosshair_btn.pack(side=tk.LEFT, padx=1)
        
        self.roi_btn = tk.Button(left_tools, text="□", width=2, height=1,
                                font=('Arial', 11), relief='flat',
                                bg='#e0e0e0', activebackground='#d0d0d0',
                                command=self.toggle_roi)
        self.roi_btn.pack(side=tk.LEFT, padx=1)
        
        # 右側縮放信息 - 緊湊
        right_info = tk.Frame(toolbar_frame, bg='#f0f0f0')
        right_info.pack(side=tk.RIGHT, padx=3, pady=2)
        
        self.zoom_label = tk.Label(right_info, text="100%", 
                                  font=('Arial', 11), bg='#f0f0f0')
        self.zoom_label.pack(side=tk.RIGHT)
    
    def create_compact_image_status_bar(self, parent):
        """創建超緊湊圖像信息狀態欄"""
        status_frame = tk.Frame(parent, bg='#e8e8e8', height=18)
        status_frame.pack(fill=tk.X, padx=1, pady=0)
        status_frame.pack_propagate(False)
        
        # 左側圖像信息 - 緊湊布局
        left_info = tk.Frame(status_frame, bg='#e8e8e8')
        left_info.pack(side=tk.LEFT, padx=5, pady=1)
        
        # 分辨率信息
        self.resolution_var = tk.StringVar(value="640 × 480")
        resolution_label = tk.Label(left_info, textvariable=self.resolution_var,
                                   font=('Arial', 11), bg='#e8e8e8')
        resolution_label.pack(side=tk.LEFT)
        
        # 分隔符
        sep1 = tk.Label(left_info, text=" | ", font=('Arial', 11), bg='#e8e8e8')
        sep1.pack(side=tk.LEFT)
        
        # 像素格式
        self.pixel_format_var = tk.StringVar(value="Mono8")
        format_label = tk.Label(left_info, textvariable=self.pixel_format_var,
                               font=('Arial', 11), bg='#e8e8e8')
        format_label.pack(side=tk.LEFT)
        
        # 分隔符
        sep2 = tk.Label(left_info, text=" | ", font=('Arial', 11), bg='#e8e8e8')
        sep2.pack(side=tk.LEFT)
        
        # 位深度
        self.bit_depth_var = tk.StringVar(value="8 bit")
        depth_label = tk.Label(left_info, textvariable=self.bit_depth_var,
                              font=('Arial', 11), bg='#e8e8e8')
        depth_label.pack(side=tk.LEFT)
        
        # 右側狀態信息
        right_info = tk.Frame(status_frame, bg='#e8e8e8')
        right_info.pack(side=tk.RIGHT, padx=5, pady=1)
        
        # 獲取狀態
        self.acquisition_status_var = tk.StringVar(value="就緒")
        status_label = tk.Label(right_info, textvariable=self.acquisition_status_var,
                               font=('Arial', 11), bg='#e8e8e8', fg='#007aff')
        status_label.pack(side=tk.RIGHT)
    
    def create_compact_performance_bar(self, parent):
        """創建超緊湊性能統計欄"""
        perf_frame = tk.Frame(parent, bg='#f8f9fa', height=20)
        perf_frame.pack(fill=tk.X, padx=1, pady=0)
        perf_frame.pack_propagate(False)
        
        # 左側FPS信息 - 超緊湊
        fps_container = tk.Frame(perf_frame, bg='#f8f9fa')
        fps_container.pack(side=tk.LEFT, padx=5, pady=2)
        
        # 相機FPS - 緊湊版
        camera_fps_frame = tk.Frame(fps_container, bg='#f8f9fa')
        camera_fps_frame.pack(side=tk.LEFT, padx=(0, 8))
        
        tk.Label(camera_fps_frame, text="📷", font=('Arial', 11), bg='#f8f9fa').pack(side=tk.LEFT)
        camera_fps_label = tk.Label(camera_fps_frame, textvariable=self.camera_fps_var,
                                   font=('Arial', 8, 'bold'), fg='#34c759', bg='#f8f9fa')
        camera_fps_label.pack(side=tk.LEFT, padx=(1, 0))
        
        # 處理FPS - 緊湊版
        processing_fps_frame = tk.Frame(fps_container, bg='#f8f9fa')
        processing_fps_frame.pack(side=tk.LEFT, padx=(0, 8))
        
        tk.Label(processing_fps_frame, text="⚡", font=('Arial', 11), bg='#f8f9fa').pack(side=tk.LEFT)
        processing_fps_label = tk.Label(processing_fps_frame, textvariable=self.processing_fps_var,
                                       font=('Arial', 8, 'bold'), fg='#007aff', bg='#f8f9fa')
        processing_fps_label.pack(side=tk.LEFT, padx=(1, 0))
        
        # 檢測FPS - 緊湊版
        detection_fps_frame = tk.Frame(fps_container, bg='#f8f9fa')
        detection_fps_frame.pack(side=tk.LEFT)
        
        tk.Label(detection_fps_frame, text="🔍", font=('Arial', 11), bg='#f8f9fa').pack(side=tk.LEFT)
        detection_fps_label = tk.Label(detection_fps_frame, textvariable=self.detection_fps_var,
                                      font=('Arial', 8, 'bold'), fg='#af52de', bg='#f8f9fa')
        detection_fps_label.pack(side=tk.LEFT, padx=(1, 0))
        
        # 右側物件計數 - 緊湊顯示
        count_container = tk.Frame(perf_frame, bg='#fff3cd', relief='solid', bd=1)
        count_container.pack(side=tk.RIGHT, padx=5, pady=1)
        
        count_inner = tk.Frame(count_container, bg='#fff3cd')
        count_inner.pack(padx=4, pady=1)
        
        tk.Label(count_inner, text="物件:", 
                font=('Arial', 11), fg='#856404', bg='#fff3cd').pack(side=tk.LEFT)
        
        count_value = tk.Label(count_inner, textvariable=self.object_count_var, 
                              font=('Arial', 9, 'bold'), fg='#d73527', bg='#fff3cd')
        count_value.pack(side=tk.LEFT, padx=(2, 0))
    
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
                              font=('Arial', 12), fg='#666666', bg='#ffffff')
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
                font=('Arial', 12), fg='#333333', bg='#f8f9fa').pack(side=tk.LEFT)
        
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
                                     font=('Arial', 12), fg='#666666', bg='#f8f9fa')
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
                                       font=('Arial', 12),
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
        
        # 最小面積輸入框
        min_input_frame = ttk.Frame(min_label_frame, style='Apple.TFrame')
        min_input_frame.pack(side=tk.RIGHT)
        
        self.min_area_var = tk.IntVar(value=100)
        self.min_area_entry = ttk.Entry(min_input_frame, textvariable=self.min_area_var, 
                                       width=6, font=('Arial', 12))
        self.min_area_entry.pack(side=tk.LEFT)
        self.min_area_entry.bind('<Return>', self.on_min_area_entry_changed)
        self.min_area_entry.bind('<FocusOut>', self.on_min_area_entry_changed)
        
        # 最小面積滑動條
        min_scale = ttk.Scale(min_area_frame, from_=1, to=5000,
                             variable=self.min_area_var, orient=tk.HORIZONTAL,
                             style='Apple.Horizontal.TScale',
                             command=self.on_min_area_changed_scale)
        min_scale.pack(fill=tk.X, pady=(5, 0))
        
        # 最大面積控制
        max_area_frame = ttk.Frame(params_frame, style='Apple.TFrame')
        max_area_frame.pack(fill=tk.X)
        
        max_label_frame = ttk.Frame(max_area_frame, style='Apple.TFrame')
        max_label_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(max_label_frame, text="最大面積", style='Apple.TLabel').pack(side=tk.LEFT)
        
        # 最大面積輸入框
        max_input_frame = ttk.Frame(max_label_frame, style='Apple.TFrame')
        max_input_frame.pack(side=tk.RIGHT)
        
        self.max_area_var = tk.IntVar(value=5000)
        self.max_area_entry = ttk.Entry(max_input_frame, textvariable=self.max_area_var, 
                                       width=6, font=('Arial', 12))
        self.max_area_entry.pack(side=tk.LEFT)
        self.max_area_entry.bind('<Return>', self.on_max_area_entry_changed)
        self.max_area_entry.bind('<FocusOut>', self.on_max_area_entry_changed)
        
        # 最大面積滑動條
        max_scale = ttk.Scale(max_area_frame, from_=100, to=50000,
                             variable=self.max_area_var, orient=tk.HORIZONTAL,
                             style='Apple.Horizontal.TScale',
                             command=self.on_max_area_changed_scale)
        max_scale.pack(fill=tk.X, pady=(5, 0))
    
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
    
    # 移除了複雜的面板切換功能，保持簡潔的固定布局
    
    def on_exposure_changed_scale(self, value):
        """曝光滑塊變化回調"""
        if self._exposure_updating:  # 避免循環更新
            return
            
        try:
            exposure_time = float(value)
            # 模擬10μs步長的精確度控制
            exposure_time = round(exposure_time / 10) * 10
            
            self._exposure_updating = True
            self.exposure_var.set(exposure_time)  # 更新變量到四捨五入後的值
            self._exposure_updating = False
            
            # 只有在相機連接時才嘗試設置曝光時間
            if hasattr(self.controller, 'camera_model') and self.controller.camera_model:
                camera_info = self.controller.camera_model.get_camera_info()
                if camera_info.get('is_connected', False):
                    success = self.controller.set_exposure_time(exposure_time)
                    if success:
                        self.status_var.set(f"狀態: 曝光時間已調整為 {exposure_time:.0f}μs")
                    else:
                        self.status_var.set(f"狀態: 曝光時間設置失敗")
                else:
                    self.status_var.set(f"狀態: 曝光時間已設為 {exposure_time:.0f}μs (相機未連接)")
            else:
                self.status_var.set(f"狀態: 曝光時間已設為 {exposure_time:.0f}μs (相機未連接)")
        except Exception as e:
            logging.error(f"調整曝光時間錯誤: {str(e)}")
    
    def on_exposure_entry_changed(self, event=None):
        """曝光輸入框變化回調"""
        if self._exposure_updating:  # 避免循環更新
            return
            
        try:
            exposure_time = self.exposure_var.get()
            
            # 輸入驗證：檢查曝光時間範圍
            if not (100.0 <= exposure_time <= 50000.0):
                self.status_var.set("錯誤: 曝光時間必須在100-50000μs之間")
                self.exposure_var.set(max(100, min(50000, exposure_time)))  # 自動修正
                return
            
            # 模擬10μs步長的精確度控制
            exposure_time = round(exposure_time / 10) * 10
            
            self._exposure_updating = True
            self.exposure_var.set(exposure_time)
            self._exposure_updating = False
            
            # 只有在相機連接時才嘗試設置曝光時間
            if hasattr(self.controller, 'camera_model') and self.controller.camera_model:
                camera_info = self.controller.camera_model.get_camera_info()
                if camera_info.get('is_connected', False):
                    success = self.controller.set_exposure_time(exposure_time)
                    if success:
                        self.status_var.set(f"狀態: 曝光時間已調整為 {exposure_time:.0f}μs")
                    else:
                        self.status_var.set(f"狀態: 曝光時間設置失敗")
                else:
                    self.status_var.set(f"狀態: 曝光時間已設為 {exposure_time:.0f}μs (相機未連接)")
            else:
                self.status_var.set(f"狀態: 曝光時間已設為 {exposure_time:.0f}μs (相機未連接)")
                
        except (ValueError, TypeError) as e:
            self.status_var.set("錯誤: 請輸入有效的數值")
            logging.error(f"曝光時間輸入格式錯誤: {str(e)}")
        except Exception as e:
            logging.error(f"調整曝光時間錯誤: {str(e)}")
            self.status_var.set("錯誤: 調整曝光時間時發生未知錯誤")
    
    def on_min_area_changed_scale(self, value):
        """最小面積滑塊變化回調"""
        if self._min_area_updating:  # 避免循環更新
            return
            
        try:
            min_area = int(float(value))  # 確保為整數
            
            self._min_area_updating = True
            self.min_area_var.set(min_area)
            self._min_area_updating = False
            
            self._update_detection_parameters()
        except Exception as e:
            logging.error(f"更新最小面積錯誤: {str(e)}")
    
    def on_max_area_changed_scale(self, value):
        """最大面積滑塊變化回調"""
        if self._max_area_updating:  # 避免循環更新
            return
            
        try:
            max_area = round(float(value) / 10) * 10  # 四捨五入到10的倍數
            
            self._max_area_updating = True
            self.max_area_var.set(max_area)
            self._max_area_updating = False
            
            self._update_detection_parameters()
        except Exception as e:
            logging.error(f"更新最大面積錯誤: {str(e)}")
    
    def on_min_area_entry_changed(self, event=None):
        """最小面積輸入框變化回調"""
        if self._min_area_updating:  # 避免循環更新
            return
            
        try:
            min_area = self.min_area_var.get()
            
            # 輸入驗證
            if min_area < 1 or min_area > 5000:
                self.status_var.set("錯誤: 最小面積必須在1-5000之間")
                self.min_area_var.set(max(1, min(5000, min_area)))  # 自動修正
                return
            
            # 檢查邏輯關係
            max_area = self.max_area_var.get()
            if min_area >= max_area:
                self.status_var.set("錯誤: 最小面積必須小於最大面積")
                return
            
            self._update_detection_parameters()
                
        except (ValueError, TypeError) as e:
            self.status_var.set("錯誤: 請輸入有效的整數")
            logging.error(f"最小面積輸入格式錯誤: {str(e)}")
        except Exception as e:
            logging.error(f"更新最小面積錯誤: {str(e)}")
    
    def on_max_area_entry_changed(self, event=None):
        """最大面積輸入框變化回調"""
        if self._max_area_updating:  # 避免循環更新
            return
            
        try:
            max_area = self.max_area_var.get()
            
            # 輸入驗證
            if max_area < 100 or max_area > 50000:
                self.status_var.set("錯誤: 最大面積必須在100-50000之間")
                self.max_area_var.set(max(100, min(50000, max_area)))  # 自動修正
                return
            
            # 模擬10的倍數精確度控制
            max_area = round(max_area / 10) * 10
            
            self._max_area_updating = True
            self.max_area_var.set(max_area)
            self._max_area_updating = False
            
            # 檢查邏輯關係
            min_area = self.min_area_var.get()
            if max_area <= min_area:
                self.status_var.set("錯誤: 最大面積必須大於最小面積")
                return
            
            self._update_detection_parameters()
                
        except (ValueError, TypeError) as e:
            self.status_var.set("錯誤: 請輸入有效的整數")
            logging.error(f"最大面積輸入格式錯誤: {str(e)}")
        except Exception as e:
            logging.error(f"更新最大面積錯誤: {str(e)}")
    
    def _update_detection_parameters(self):
        """統一的檢測參數更新方法"""
        try:
            min_area = self.min_area_var.get()
            max_area = self.max_area_var.get()
            
            params = {
                'min_area': min_area,
                'max_area': max_area
            }
            
            success = self.controller.update_detection_parameters(params)
            if success:
                self.status_var.set(f"狀態: 檢測參數已更新 (面積: {min_area}-{max_area})")
            else:
                self.status_var.set("狀態: 檢測參數更新失敗")
        except Exception as e:
            logging.error(f"更新檢測參數錯誤: {str(e)}")
            self.status_var.set("錯誤: 更新檢測參數時發生錯誤")
    
        
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
        """創建緊湊專業系統狀態欄 - 最大化中間視頻區域"""
        # 主狀態欄 - 緊湊設計
        main_status_bar = tk.Frame(parent, bg='#e8e8e8', height=28)
        main_status_bar.pack(fill=tk.X, pady=(2, 0))
        main_status_bar.pack_propagate(False)
        
        # 左側系統狀態
        left_status = tk.Frame(main_status_bar, bg='#e8e8e8')
        left_status.pack(side=tk.LEFT, padx=8, pady=4)
        
        # 狀態指示器
        status_indicator = tk.Frame(left_status, bg='#e8e8e8')
        status_indicator.pack(side=tk.LEFT)
        
        tk.Label(status_indicator, text="狀態:", 
                font=('Arial', 12), bg='#e8e8e8', fg='#333333').pack(side=tk.LEFT)
        
        self.status_display = tk.Label(status_indicator, textvariable=self.status_var,
                                     font=('Arial', 9, 'bold'), 
                                     bg='#e8e8e8', fg='#34c759')
        self.status_display.pack(side=tk.LEFT, padx=(5, 15))
        
        # 相機信息
        camera_info = tk.Frame(left_status, bg='#e8e8e8')
        camera_info.pack(side=tk.LEFT)
        
        tk.Label(camera_info, text="相機:", 
                font=('Arial', 12), bg='#e8e8e8', fg='#333333').pack(side=tk.LEFT)
        
        self.camera_display = tk.Label(camera_info, textvariable=self.camera_info_var,
                                     font=('Arial', 12), 
                                     bg='#e8e8e8', fg='#666666')
        self.camera_display.pack(side=tk.LEFT, padx=(5, 0))
        
        # 中間性能統計 - 專業布局
        center_stats = tk.Frame(main_status_bar, bg='#e8e8e8')
        center_stats.pack(side=tk.LEFT, expand=True, padx=15, pady=4)
        
        # FPS統計區域
        fps_container = tk.Frame(center_stats, bg='#e8e8e8')
        fps_container.pack()
        
        # 相機FPS
        camera_fps_frame = tk.Frame(fps_container, bg='#e8e8e8')
        camera_fps_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(camera_fps_frame, text="相機:", 
                font=('Arial', 12), bg='#e8e8e8', fg='#333333').pack(side=tk.LEFT)
        camera_fps_display = tk.Label(camera_fps_frame, textvariable=self.camera_fps_var,
                                     font=('Arial', 9, 'bold'), 
                                     bg='#e8e8e8', fg='#34c759')
        camera_fps_display.pack(side=tk.LEFT, padx=(3, 0))
        
        # 處理FPS
        processing_fps_frame = tk.Frame(fps_container, bg='#e8e8e8')
        processing_fps_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Label(processing_fps_frame, text="處理:", 
                font=('Arial', 12), bg='#e8e8e8', fg='#333333').pack(side=tk.LEFT)
        processing_fps_display = tk.Label(processing_fps_frame, textvariable=self.processing_fps_var,
                                         font=('Arial', 9, 'bold'), 
                                         bg='#e8e8e8', fg='#007aff')
        processing_fps_display.pack(side=tk.LEFT, padx=(3, 0))
        
        # 檢測FPS
        detection_fps_frame = tk.Frame(fps_container, bg='#e8e8e8')
        detection_fps_frame.pack(side=tk.LEFT)
        
        tk.Label(detection_fps_frame, text="檢測:", 
                font=('Arial', 12), bg='#e8e8e8', fg='#333333').pack(side=tk.LEFT)
        detection_fps_display = tk.Label(detection_fps_frame, textvariable=self.detection_fps_var,
                                        font=('Arial', 9, 'bold'), 
                                        bg='#e8e8e8', fg='#af52de')
        detection_fps_display.pack(side=tk.LEFT, padx=(3, 0))
        
        # 右側時間戳
        right_status = tk.Frame(main_status_bar, bg='#e8e8e8')
        right_status.pack(side=tk.RIGHT, padx=8, pady=4)
        
        import time
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_display = tk.Label(right_status, text=current_time,
                                   font=('Arial', 12), 
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
            
            elif event_type == 'camera_disconnected':
                self._on_camera_disconnected()
            
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
        
        # 保持舊接口兼容性
        self.camera_info_var.set(f"相機: {model} ({serial})")
        
        # 更新連接狀態
        self.is_camera_connected = True
        self.connection_switch_on = True
        
        # 在設備列表中找到對應設備並設置為選中
        for i, camera in enumerate(self.detected_cameras):
            if camera.get('model') == model and camera.get('serial') == serial:
                self.selected_camera_index = i
                break
        
        self.update_connection_ui()
        self.update_device_list_ui()
    
    def _on_camera_disconnected(self):
        """處理相機斷開連接"""
        # 保持舊接口兼容性
        self.camera_info_var.set("相機: 未連接")
        
        # 更新連接狀態
        self.is_camera_connected = False
        self.connection_switch_on = False
        self.selected_camera_index = -1
        
        self.update_connection_ui()
        self.update_device_list_ui()
        
        # 清空視頻顯示
        self.update_video_status("相機未連接")
    
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
        """更新狀態顯示 - 平滑FPS顯示"""
        try:
            status = self.controller.get_system_status()
            
            # 添加到歷史記錄
            self.fps_history['camera'].append(status['camera_fps'])
            self.fps_history['processing'].append(status['processing_fps'])
            self.fps_history['detection'].append(status['detection_fps'])
            
            # 限制歷史記錄大小 (保持最近10個值)
            for key in self.fps_history:
                if len(self.fps_history[key]) > 10:
                    self.fps_history[key].pop(0)
            
            # 每5次更新才刷新一次顯示 (降低刷新頻率)
            self.fps_update_counter += 1
            if self.fps_update_counter >= 5:
                self.fps_update_counter = 0
                
                # 計算平滑的平均值
                camera_avg = sum(self.fps_history['camera']) / len(self.fps_history['camera']) if self.fps_history['camera'] else 0
                processing_avg = sum(self.fps_history['processing']) / len(self.fps_history['processing']) if self.fps_history['processing'] else 0
                detection_avg = sum(self.fps_history['detection']) / len(self.fps_history['detection']) if self.fps_history['detection'] else 0
                
                # 更新顯示 - 仿Basler格式，防止4位數造成畫面異動
                camera_fps_text = f"{min(camera_avg, 999.0):.1f} fps" if camera_avg < 1000 else "999+ fps"
                processing_fps_text = f"{min(processing_avg, 999.0):.1f} fps" if processing_avg < 1000 else "999+ fps"
                detection_fps_text = f"{min(detection_avg, 999.0):.1f} fps" if detection_avg < 1000 else "999+ fps"
                
                # 計算大致的數據速率（假設每幀約86KB）
                data_rate = (camera_avg * 86) / 1024  # MB/s
                data_rate_text = f"({data_rate:.1f} MB/s)" if data_rate < 1000 else "(999+ MB/s)"
                
                self.camera_fps_var.set(f"相機: {camera_fps_text} {data_rate_text}")
                self.processing_fps_var.set(f"處理: {processing_fps_text}")
                self.detection_fps_var.set(f"檢測: {detection_fps_text}")
            
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
            
            # 更新顯示 - 增強安全檢查
            if (hasattr(self, 'video_label') and self.video_label and 
                hasattr(self.video_label, 'winfo_exists') and self.video_label.winfo_exists()):
                try:
                    self.video_label.configure(image=photo, text="")  # 清除文字
                    self.video_label.image = photo  # 保持引用避免垃圾回收
                except tk.TclError as e:
                    logging.warning(f"視頻標籤配置錯誤: {str(e)}")
                    # 標籤可能已被銷毀，忽略此次更新
                
                # 第一次顯示幀時的日誌
                if not hasattr(self, '_first_display_logged'):
                    self._first_display_logged = True
                    logging.info("成功顯示第一幀到UI")
                
        except Exception as e:
            logging.error(f"更新視頻顯示錯誤: {str(e)}")
    
    # ==================== 控制方法 ====================
    
    def refresh_device_list(self):
        """刷新設備列表"""
        try:
            # 檢測可用相機
            self.detected_cameras = self.controller.detect_cameras()
            
            # 清空列表
            self.device_listbox.delete(0, tk.END)
            
            # 添加檢測到的設備
            if self.detected_cameras:
                for i, camera in enumerate(self.detected_cameras):
                    model = camera.get('model', 'Unknown')
                    serial = camera.get('serial', 'N/A')
                    is_target = camera.get('is_target', False)
                    
                    # 格式化顯示文字
                    display_text = f"{model} ({serial})"
                    if is_target:
                        display_text += " ✓"
                    
                    self.device_listbox.insert(tk.END, display_text)
            else:
                self.device_listbox.insert(tk.END, "未檢測到設備")
                
        except Exception as e:
            logging.error(f"刷新設備列表錯誤: {str(e)}")
            self.device_listbox.delete(0, tk.END)
            self.device_listbox.insert(tk.END, "檢測失敗")
    
    def on_device_double_click(self, event):
        """設備列表雙擊事件"""
        try:
            selection = self.device_listbox.curselection()
            if not selection or not self.detected_cameras:
                return
                
            selected_index = selection[0]
            if selected_index >= len(self.detected_cameras):
                return
                
            # 如果已經連接其他設備，先斷開
            if self.is_camera_connected:
                self.disconnect_camera()
                
            # 連接選中的設備
            self.selected_camera_index = selected_index
            selected_camera = self.detected_cameras[selected_index]
            
            self.status_var.set(f"狀態: 正在連接 {selected_camera['model']}...")
            
            # 嘗試連接 - 使用簡單的連接方法避免重複連接
            success = self.controller.connect_camera(selected_index)
            if success:
                # 連接成功後啟動捕獲
                if self.controller.start_capture():
                    # 啟動處理循環
                    self.controller._start_processing()
                    
                    self.is_camera_connected = True
                    self.connection_switch_on = True
                    self.update_connection_ui()
                    self.update_device_list_ui()
                    self.status_var.set(f"狀態: 已連接 {selected_camera['model']}")
                else:
                    self.status_var.set("錯誤: 啟動捕獲失敗")
            else:
                self.status_var.set("錯誤: 相機連接失敗")
                
        except Exception as e:
            logging.error(f"設備雙擊連接錯誤: {str(e)}")
            self.status_var.set("錯誤: 連接操作失敗")
    
    def toggle_connection_switch(self):
        """切換連接開關"""
        try:
            if self.connection_switch_on:
                # 斷開連接
                self.disconnect_camera()
                self.connection_switch_on = False
            else:
                # 檢查是否有選中的設備
                selection = self.device_listbox.curselection()
                if not selection or not self.detected_cameras:
                    self.status_var.set("錯誤: 請先選擇要連接的設備")
                    return
                    
                # 連接選中的設備
                self.on_device_double_click(None)
                
            self.update_connection_switch_ui()
            
        except Exception as e:
            logging.error(f"切換連接開關錯誤: {str(e)}")
            self.status_var.set("錯誤: 開關操作失敗")
    
    def disconnect_camera(self):
        """斷開相機連接"""
        try:
            self.controller.disconnect_camera()
            self.is_camera_connected = False
            self.selected_camera_index = -1
            self.update_connection_ui()
            self.update_device_list_ui()
            self.status_var.set("狀態: 相機已斷開連接")
        except Exception as e:
            logging.error(f"斷開相機錯誤: {str(e)}")
    
    def update_device_list_ui(self):
        """更新設備列表UI顯示"""
        try:
            # 重新填充列表，更新連接狀態的顯示
            self.device_listbox.delete(0, tk.END)
            
            if self.detected_cameras:
                for i, camera in enumerate(self.detected_cameras):
                    model = camera.get('model', 'Unknown')
                    serial = camera.get('serial', 'N/A')
                    is_target = camera.get('is_target', False)
                    
                    # 格式化顯示文字
                    display_text = f"{model} ({serial})"
                    if is_target:
                        display_text += " ✓"
                    
                    self.device_listbox.insert(tk.END, display_text)
                    
                    # 如果是已連接的設備，設置為粗體（通過選中狀態模擬）
                    if i == self.selected_camera_index and self.is_camera_connected:
                        self.device_listbox.selection_set(i)
            else:
                self.device_listbox.insert(tk.END, "未檢測到設備")
                
        except Exception as e:
            logging.error(f"更新設備列表UI錯誤: {str(e)}")
    
    def update_connection_switch_ui(self):
        """更新連接開關UI"""
        if self.connection_switch_on:
            # 開啟狀態
            self.connection_switch.config(
                text="●",
                bg='#34c759',
                fg='white'
            )
        else:
            # 關閉狀態
            self.connection_switch.config(
                text="○",
                bg='#e0e0e0',
                fg='#999999'
            )
    
    def toggle_camera_connection(self):
        """切換相機連接狀態 - 仿Basler設計"""
        try:
            if self.is_camera_connected:
                # 斷開連接
                self.controller.disconnect_camera()
                self.is_camera_connected = False
                self.connection_switch_on = False
                self.update_connection_ui()
                self.status_var.set("狀態: 相機已斷開連接")
            else:
                # 檢查是否有選中的設備
                selection = self.device_listbox.curselection()
                if not selection or not self.detected_cameras:
                    self.status_var.set("錯誤: 請先雙擊選擇要連接的設備")
                    return
                    
                # 連接選中的設備
                self.on_device_double_click(None)
                
        except Exception as e:
            logging.error(f"切換相機連接錯誤: {str(e)}")
            self.status_var.set("錯誤: 相機連接操作失敗")
    
    def toggle_processing(self):
        """切換影像處理狀態"""
        try:
            if self.is_processing_active:
                # 停止處理
                self.controller.stop_system()
                self.is_processing_active = False
                self.update_processing_ui()
                self.status_var.set("狀態: 影像處理已停止")
            else:
                # 啟動處理
                if not self.is_camera_connected:
                    self.status_var.set("錯誤: 請先連接相機")
                    return
                    
                self.controller.start_system()
                self.is_processing_active = True
                self.update_processing_ui()
                self.status_var.set("狀態: 影像處理已啟動")
        except Exception as e:
            logging.error(f"切換處理狀態錯誤: {str(e)}")
            self.status_var.set("錯誤: 處理狀態切換失敗")
    
    def update_connection_ui(self):
        """更新連接狀態的UI"""
        if self.is_camera_connected:
            # 已連接狀態
            self.connection_status_label.config(
                text="● 已連接",
                fg='#34c759'
            )
            # 啟用相關功能按鈕
            self.start_processing_btn.config(state='normal')
            self.exposure_entry.config(state='normal')
            self.min_area_entry.config(state='normal')
            self.max_area_entry.config(state='normal')
            if hasattr(self, 'detection_method'):
                self.detection_method.config(state='readonly')
        else:
            # 未連接狀態
            self.connection_status_label.config(
                text="● 未連接",
                fg='#ff3b30'
            )
            # 禁用相關功能按鈕
            self.start_processing_btn.config(state='disabled')
            self.exposure_entry.config(state='disabled')
            self.min_area_entry.config(state='disabled')
            self.max_area_entry.config(state='disabled')
            if hasattr(self, 'detection_method'):
                self.detection_method.config(state='disabled')
            
            # 重置處理狀態
            if self.is_processing_active:
                self.is_processing_active = False
                self.update_processing_ui()
        
        # 更新連接開關
        self.update_connection_switch_ui()
    
    def update_processing_ui(self):
        """更新處理狀態的UI"""
        if self.is_processing_active:
            self.start_processing_btn.config(
                text="⏸️ 停止處理",
                bg='#ff9500',
                activebackground='#e6870b'
            )
        else:
            self.start_processing_btn.config(
                text="▶️ 啟動處理",
                bg='#f2f2f7',
                fg='#007aff'
            )
    
    def auto_start_system(self):
        """一鍵啟動系統 - 同時連接相機和啟動處理"""
        try:
            if not self.is_camera_connected:
                # 先連接相機
                self.toggle_camera_connection()
                # 等待連接完成
                self.root.after(1000, self._start_processing_after_connection)
            else:
                # 直接啟動處理
                if not self.is_processing_active:
                    self.toggle_processing()
        except Exception as e:
            logging.error(f"一鍵啟動錯誤: {str(e)}")
    
    def _start_processing_after_connection(self):
        """連接後啟動處理"""
        if self.is_camera_connected and not self.is_processing_active:
            self.toggle_processing()
    
    def start_system(self):
        """啟動系統（舊接口，重定向到新邏輯）"""
        self.auto_start_system()
    
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
    
    # 舊的參數處理函數已被新的輸入框+滑動條組合方式取代
    
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
    
    # 移除了不必要的性能報告和關於功能，簡化界面
    
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