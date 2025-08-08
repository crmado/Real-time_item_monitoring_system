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
        
        # UI 變量 - 美觀的FPS顯示格式
        self.status_var = tk.StringVar(value="狀態: 系統就緒")
        self.camera_fps_var = tk.StringVar(value="相機: 0 fps(0.0 MB/s)")
        self.processing_fps_var = tk.StringVar(value="處理: 0 fps")
        self.detection_fps_var = tk.StringVar(value="檢測: 0 fps")
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
        
        # 初始化跨平台主題管理器
        self.theme_manager = ThemeManager(self.root, AppleTheme)
        
        # 記錄跨平台 UI 啟動資訊
        logging.info(f"✅ 跨平台 UI 系統已啟用 - 平台: {self.theme_manager.ui_manager.platform_name}")
        
        # 🎨 統一配色系統 - 使用 option_add 設置全局樣式
        self._setup_global_color_scheme()
        
        # 創建UI
        self.create_ui()
        
        # 初始化設備列表
        self.refresh_device_list()
        
        # 初始化UI狀態
        self.update_connection_ui()
        
        # 註冊為控制器觀察者
        self.controller.add_view_observer(self.on_controller_event)
        
        logging.info("主視圖初始化完成")
    
    def _setup_global_color_scheme(self):
        """🎨 設置全局統一配色方案 - 使用 option_add 和 tk_setPalette"""
        try:
            # 獲取跨平台顏色
            bg_primary = self.theme_manager.get_platform_color('background_primary')
            bg_card = self.theme_manager.get_platform_color('background_card')
            bg_secondary = self.theme_manager.get_platform_color('background_secondary')
            text_primary = self.theme_manager.get_platform_color('text_primary')
            text_secondary = self.theme_manager.get_platform_color('text_secondary')
            primary_blue = self.theme_manager.get_platform_color('primary_blue')
            border_light = self.theme_manager.get_platform_color('border_light')
            
            # 🌈 使用 tk_setPalette 設置全局調色板（這是關鍵！）
            self.root.tk_setPalette(
                background=bg_primary,
                foreground=text_primary,
                activeBackground=primary_blue,
                activeForeground='white',
                selectBackground=primary_blue,
                selectForeground='white',
                insertBackground=text_primary,
                highlightBackground=border_light,
                highlightColor=primary_blue
            )
            
            # 🎯 使用 option_add 設置特定組件的詳細樣式
            # Frame 樣式
            self.root.option_add('*Frame.background', bg_card)
            self.root.option_add('*Frame.relief', 'flat')
            
            # Button 樣式
            self.root.option_add('*Button.background', primary_blue)
            self.root.option_add('*Button.foreground', 'white')
            self.root.option_add('*Button.activeBackground', '#0056cc')
            self.root.option_add('*Button.relief', 'flat')
            self.root.option_add('*Button.borderWidth', '0')
            
            # Label 樣式
            self.root.option_add('*Label.background', bg_card)
            self.root.option_add('*Label.foreground', text_primary)
            
            # Entry 樣式
            self.root.option_add('*Entry.background', bg_card)
            self.root.option_add('*Entry.foreground', text_primary)
            self.root.option_add('*Entry.insertBackground', text_primary)
            self.root.option_add('*Entry.selectBackground', primary_blue)
            self.root.option_add('*Entry.selectForeground', 'white')
            
            # Listbox 樣式
            self.root.option_add('*Listbox.background', bg_card)
            self.root.option_add('*Listbox.foreground', text_primary)
            self.root.option_add('*Listbox.selectBackground', primary_blue)
            self.root.option_add('*Listbox.selectForeground', 'white')
            
            # LabelFrame 樣式
            self.root.option_add('*LabelFrame.background', bg_card)
            self.root.option_add('*LabelFrame.foreground', text_primary)
            
            # 設置根窗口背景
            self.root.configure(background=bg_primary)
            
            # 🔧 強制修復 TTK 灰底問題（關鍵修復！）
            self._force_fix_ttk_gray_background()
            
            logging.info(f"✅ 全局配色方案已設置 - 主色: {primary_blue}, 背景: {bg_primary}")
            
        except Exception as e:
            logging.error(f"❌ 設置全局配色失敗: {str(e)}")
    
    def _force_fix_ttk_gray_background(self):
        """🔧 強制修復 TTK 灰底問題"""
        try:
            # 獲取淺色配色
            bg_card = self.theme_manager.get_platform_color('background_card')
            bg_primary = self.theme_manager.get_platform_color('background_primary')
            text_primary = self.theme_manager.get_platform_color('text_primary')
            primary_blue = self.theme_manager.get_platform_color('primary_blue')
            border_light = self.theme_manager.get_platform_color('border_light')
            
            # 強制覆蓋所有 TTK 默認樣式（這是關鍵！）
            self.theme_manager.style.configure('TFrame', 
                                             background=bg_card, 
                                             relief='flat',
                                             borderwidth=0)
            
            self.theme_manager.style.configure('TLabel', 
                                             background=bg_card, 
                                             foreground=text_primary)
            
            self.theme_manager.style.configure('TButton', 
                                             background=primary_blue, 
                                             foreground='white',
                                             relief='flat',
                                             borderwidth=0)
            
            self.theme_manager.style.configure('TEntry', 
                                             fieldbackground=bg_card,
                                             bordercolor=border_light)
            
            self.theme_manager.style.configure('TLabelframe', 
                                             background=bg_card,
                                             bordercolor=border_light)
            
            self.theme_manager.style.configure('TLabelframe.Label', 
                                             background=bg_card, 
                                             foreground=text_primary)
            
            # 設置全局默認樣式（最重要的一步！）
            self.theme_manager.style.configure('.', background=bg_card)
            
            logging.info("🔧 TTK 灰底問題強制修復完成")
            
        except Exception as e:
            logging.error(f"❌ TTK 修復失敗: {str(e)}")
    
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
        """創建緊湊專業工具欄 - 使用跨平台配色"""
        # 主工具欄 - 使用跨平台顏色
        toolbar_bg = self.theme_manager.get_platform_color('background_primary')
        main_toolbar = tk.Frame(parent, bg=toolbar_bg, height=35)
        main_toolbar.pack(fill=tk.X, padx=1, pady=(1, 2))
        main_toolbar.pack_propagate(False)
        
        # 左側控制組
        left_controls = tk.Frame(main_toolbar, bg=toolbar_bg)
        left_controls.pack(side=tk.LEFT, padx=8, pady=5)
        
        # 移除不必要的面板切換按鈕 - 簡化界面
        
        # 分隔線 - 使用跨平台邊框顏色
        border_color = self.theme_manager.get_platform_color('border_light')
        sep1 = tk.Frame(main_toolbar, bg=border_color, width=1)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 連接開關控制 - 使用跨平台背景
        connection_control = tk.Frame(main_toolbar, bg=toolbar_bg)
        connection_control.pack(side=tk.LEFT, padx=8, pady=3)
        
        # 連接開關按鈕框架 - 使用跨平台框架
        self.connection_switch_frame = self.theme_manager.create_cross_platform_frame(
            connection_control, frame_type="transparent"
        )
        self.connection_switch_frame.pack(side=tk.LEFT)
        
        # 使用跨平台標籤和安全文字處理
        connection_label = self.theme_manager.create_cross_platform_label(
            self.connection_switch_frame, 
            self.theme_manager.get_safe_text("連線:"), 
            label_type="body"
        )
        connection_label.pack(side=tk.LEFT, padx=(0, 8))
        
        # 使用跨平台開關按鈕
        self.connection_switch = self.theme_manager.create_cross_platform_button(
            self.connection_switch_frame,
            "○",
            command=self.toggle_connection_switch, 
            button_type="secondary"
        )
        self.connection_switch.configure(width=3, height=1)
        self.connection_switch.pack(side=tk.LEFT)
        
        # 儲存開關狀態
        self.connection_switch_on = False
        
        # 分隔線 - 使用跨平台邊框顏色
        sep2 = tk.Frame(main_toolbar, bg=border_color, width=1)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # 啟動/停止控制組 - 使用跨平台背景
        start_controls = tk.Frame(main_toolbar, bg=toolbar_bg)
        start_controls.pack(side=tk.LEFT, padx=8, pady=3)
        
        # 使用跨平台啟動處理按鈕
        self.start_processing_btn = self.theme_manager.create_cross_platform_button(
            start_controls, 
            self.theme_manager.get_safe_text("▶️ 啟動處理"),
            command=self.toggle_processing,
            button_type="primary"
        )
        self.start_processing_btn.configure(state='disabled', padx=12, pady=6)  # 初始禁用
        self.start_processing_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 儲存處理狀態
        self.is_processing_active = False
        
        # 檢測方法選擇 - 使用跨平台框架
        method_frame = tk.Frame(start_controls, bg=toolbar_bg)
        method_frame.pack(side=tk.LEFT)
        
        # 使用跨平台標籤
        method_label = self.theme_manager.create_cross_platform_label(
            method_frame, 
            self.theme_manager.get_safe_text("檢測方法:"),
            label_type="body"
        )
        method_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # 創建檢測方法下拉框 - 使用ttk保持一致性，字體增大
        self.detection_method = ttk.Combobox(method_frame, values=["circle"], 
                                           state="readonly", width=8,
                                           font=('Arial', 12))  # 字體從9增大到12
        self.detection_method.set("circle")
        self.detection_method.pack(side=tk.LEFT)
        self.detection_method.bind('<<ComboboxSelected>>', self.on_method_changed)
        
        # 右側工具組 - 使用跨平台背景
        right_tools = tk.Frame(main_toolbar, bg=toolbar_bg)
        right_tools.pack(side=tk.RIGHT, padx=8, pady=5)
        
        # 使用跨平台設定按鈕
        self.settings_btn = self.theme_manager.create_cross_platform_button(
            right_tools, 
            "⚙️", 
            command=self.open_parameter_dialog,
            button_type="secondary"
        )
        self.settings_btn.configure(width=3, height=1)
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
        
        # 設備列表區域 - 使用跨平台背景
        card_bg = self.theme_manager.get_platform_color('background_card')
        device_list_frame = tk.Frame(device_frame, bg=card_bg)
        device_list_frame.pack(fill=tk.X, pady=(5, 8))
        
        # 設備列表（用Listbox實現）- 使用跨平台背景
        border_color = self.theme_manager.get_platform_color('border_light')
        listbox_frame = tk.Frame(device_list_frame, bg=card_bg, relief='sunken', bd=1)
        listbox_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 使用跨平台配色的列表框
        text_color = self.theme_manager.get_platform_color('text_primary')
        primary_color = self.theme_manager.get_platform_color('primary_blue')
        
        self.device_listbox = tk.Listbox(
            listbox_frame,
            height=3,
            font=self.theme_manager.get_platform_font('primary', 10),
            bg=card_bg,
            fg=text_color,
            selectbackground=primary_color,
            selectforeground='white',
            activestyle='none',
            borderwidth=0,
            highlightthickness=0
        )
        self.device_listbox.pack(fill=tk.X, padx=2, pady=2)
        
        # 綁定雙擊事件
        self.device_listbox.bind('<Double-Button-1>', self.on_device_double_click)
        
        # 提示文字
        # 使用跨平台提示標籤
        hint_label = self.theme_manager.create_cross_platform_label(
            device_list_frame, 
            self.theme_manager.get_safe_text("雙擊設備進行連接"),
            label_type="caption"
        )
        hint_label.pack(anchor='w')
        
        # 分隔線 - 使用跨平台邊框顏色
        border_color = self.theme_manager.get_platform_color('border_light')
        separator = tk.Frame(device_frame, height=1, bg=border_color)
        separator.pack(fill=tk.X, pady=(5, 5))
        
        # 連接狀態顯示 - 使用跨平台背景
        card_bg = self.theme_manager.get_platform_color('background_card')
        status_frame = tk.Frame(device_frame, bg=card_bg)
        status_frame.pack(fill=tk.X, pady=(0, 8))
        
        # 使用跨平台狀態標籤
        self.connection_status_label = self.theme_manager.create_cross_platform_status_display(
            status_frame, status_type="error"
        )
        self.connection_status_label.configure(
            text=self.theme_manager.get_safe_text("● 未連接")
        )
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
        
        # 視頻錄製和回放控制面板
        self.create_video_control_panel()
    
    def create_video_control_panel(self):
        """創建視頻錄製和回放控制面板"""
        # 視頻控制主框架
        video_frame = ttk.LabelFrame(self.left_panel, text="🎬 視頻控制", 
                                   style='Apple.TLabelframe')
        video_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 模式選擇區域
        mode_frame = ttk.Frame(video_frame, style='Apple.TFrame')
        mode_frame.pack(fill=tk.X, pady=(5, 8))
        
        ttk.Label(mode_frame, text="模式:", style='Apple.TLabel').pack(side=tk.LEFT)
        
        # 模式變數和單選按鈕
        self.video_mode = tk.StringVar(value="live")
        
        modes = [
            ("實時", "live"),
            ("錄製", "recording"), 
            ("回放", "playback")
        ]
        
        mode_buttons_frame = ttk.Frame(mode_frame, style='Apple.TFrame')
        mode_buttons_frame.pack(side=tk.RIGHT)
        
        for text, value in modes:
            rb = ttk.Radiobutton(mode_buttons_frame, text=text, value=value,
                               variable=self.video_mode, 
                               command=self.on_video_mode_change)
            rb.pack(side=tk.LEFT, padx=2)
        
        # 錄製控制區域
        self.recording_frame = ttk.Frame(video_frame, style='Apple.TFrame')
        self.recording_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 檔名輸入
        filename_frame = ttk.Frame(self.recording_frame, style='Apple.TFrame')
        filename_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filename_frame, text="檔名:", style='Apple.TLabel').pack(side=tk.LEFT)
        
        self.recording_filename = tk.StringVar(value=self.generate_recording_filename())
        filename_entry = ttk.Entry(filename_frame, textvariable=self.recording_filename, 
                                 width=15, font=('Arial', 9))
        filename_entry.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 錄製按鈕
        record_button_frame = ttk.Frame(self.recording_frame, style='Apple.TFrame')
        record_button_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 使用跨平台錄製按鈕
        self.record_btn = self.theme_manager.create_cross_platform_button(
            record_button_frame, 
            self.theme_manager.get_safe_text("🔴 開始錄製"),
            command=self.toggle_recording,
            button_type="danger"
        )
        self.record_btn.configure(padx=8, pady=4)
        self.record_btn.pack(side=tk.LEFT)
        
        # 使用跨平台錄製狀態標籤
        self.recording_status = self.theme_manager.create_cross_platform_label(
            record_button_frame, "", label_type="caption"
        )
        self.recording_status.pack(side=tk.RIGHT)
        
        # 回放控制區域
        self.playback_frame = ttk.Frame(video_frame, style='Apple.TFrame')
        self.playback_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 檔案選擇
        file_frame = ttk.Frame(self.playback_frame, style='Apple.TFrame')
        file_frame.pack(fill=tk.X, pady=(0, 5))
        
        file_btn = tk.Button(file_frame, text="選擇視頻", font=('Arial', 9),
                           command=self.select_video_file, relief='solid', bd=1)
        file_btn.pack(side=tk.LEFT)
        
        self.selected_video_path = tk.StringVar(value="未選擇")
        video_label = tk.Label(file_frame, textvariable=self.selected_video_path,
                             font=('Arial', 8), fg='#666666')
        video_label.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 播放控制按鈕
        playback_controls = ttk.Frame(self.playback_frame, style='Apple.TFrame')
        playback_controls.pack(fill=tk.X, pady=(0, 5))
        
        self.play_btn = tk.Button(playback_controls, text="▶️", font=('Arial', 10),
                                 command=self.toggle_playback, relief='solid', bd=1, width=3)
        self.play_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.pause_btn = tk.Button(playback_controls, text="⏸️", font=('Arial', 10),
                                  command=self.pause_playback, relief='solid', bd=1, width=3)
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.stop_btn = tk.Button(playback_controls, text="⏹️", font=('Arial', 10),
                                 command=self.stop_playback, relief='solid', bd=1, width=3)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        # 播放速度控制
        speed_frame = ttk.Frame(playback_controls, style='Apple.TFrame')
        speed_frame.pack(side=tk.RIGHT)
        
        tk.Label(speed_frame, text="速度:", font=('Arial', 9)).pack(side=tk.LEFT)
        
        self.playback_speed = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(speed_frame, from_=0.1, to=3.0, variable=self.playback_speed,
                              orient=tk.HORIZONTAL, length=60, command=self.on_speed_change)
        speed_scale.pack(side=tk.LEFT, padx=(2, 0))
        
        # 進度條
        progress_frame = ttk.Frame(self.playback_frame, style='Apple.TFrame')
        progress_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.video_progress = tk.DoubleVar()
        self.progress_scale = ttk.Scale(progress_frame, from_=0, to=1, 
                                       variable=self.video_progress,
                                       orient=tk.HORIZONTAL, 
                                       command=self.on_progress_change)
        self.progress_scale.pack(fill=tk.X)
        
        # 幀信息
        info_frame = ttk.Frame(self.playback_frame, style='Apple.TFrame')
        info_frame.pack(fill=tk.X)
        
        self.frame_info = tk.Label(info_frame, text="", font=('Arial', 8), fg='#666666')
        self.frame_info.pack()
        
        # 初始化界面狀態
        self.update_video_control_ui()
        
        # 狀態變數
        self.is_recording = False
        self.is_playing = False
        self.video_loaded = False
    
    def create_center_panel(self, parent):
        """創建滿版專業相機顯示區域 - 使用跨平台配色"""
        # 中央面板容器 - 使用跨平台背景
        primary_bg = self.theme_manager.get_platform_color('background_primary')
        self.center_panel = tk.Frame(parent, bg=primary_bg)
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=1, pady=1)
        
        # 主視頻框架 - 使用跨平台標籤框架
        main_video_frame = self.theme_manager.create_cross_platform_frame(
            self.center_panel, frame_type="card"
        )
        main_video_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # 標題標籤
        title_label = self.theme_manager.create_cross_platform_label(
            main_video_frame,
            self.theme_manager.get_safe_text("📷 Basler acA640-300gm - 實時影像"),
            label_type="subtitle"
        )
        title_label.pack(pady=(5, 0))
        
        # 圖像工具欄 - 超緊湊設計
        self.create_compact_image_toolbar(main_video_frame)
        
        # 影像顯示容器 - 使用跨平台深色背景
        secondary_bg = self.theme_manager.get_platform_color('background_secondary')
        image_container = tk.Frame(main_video_frame, 
                                  bg=secondary_bg,
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
        """創建超緊湊圖像工具欄 - 使用跨平台配色"""
        toolbar_bg = self.theme_manager.get_platform_color('background_primary')
        toolbar_frame = tk.Frame(parent, bg=toolbar_bg, height=25)
        toolbar_frame.pack(fill=tk.X, padx=1, pady=0)
        toolbar_frame.pack_propagate(False)
        
        # 左側工具按鈕 - 超緊湊
        left_tools = tk.Frame(toolbar_frame, bg=toolbar_bg)
        left_tools.pack(side=tk.LEFT, padx=3, pady=2)
        
        # 縮放控制 - 使用跨平台按鈕
        self.zoom_fit_btn = self.theme_manager.create_cross_platform_button(
            left_tools, "🔍", command=self.zoom_fit, button_type="secondary"
        )
        self.zoom_fit_btn.configure(width=2, height=1)
        self.zoom_fit_btn.pack(side=tk.LEFT, padx=1)
        
        self.zoom_100_btn = self.theme_manager.create_cross_platform_button(
            left_tools, "1:1", command=self.zoom_100, button_type="secondary"
        )
        self.zoom_100_btn.configure(width=2, height=1)
        self.zoom_100_btn.pack(side=tk.LEFT, padx=1)
        
        # 圖像工具 - 使用跨平台按鈕
        self.crosshair_btn = self.theme_manager.create_cross_platform_button(
            left_tools, "✛", command=self.toggle_crosshair, button_type="secondary"
        )
        self.crosshair_btn.configure(width=2, height=1)
        self.crosshair_btn.pack(side=tk.LEFT, padx=1)
        
        self.roi_btn = self.theme_manager.create_cross_platform_button(
            left_tools, "□", command=self.toggle_roi, button_type="secondary"
        )
        self.roi_btn.configure(width=2, height=1)
        self.roi_btn.pack(side=tk.LEFT, padx=1)
        
        # 右側縮放信息 - 使用跨平台框架
        right_info = tk.Frame(toolbar_frame, bg=toolbar_bg)
        right_info.pack(side=tk.RIGHT, padx=3, pady=2)
        
        self.zoom_label = self.theme_manager.create_cross_platform_label(
            right_info, "100%", label_type="body"
        )
        self.zoom_label.pack(side=tk.RIGHT)
    
    def create_compact_image_status_bar(self, parent):
        """創建超緊湊圖像信息狀態欄 - 使用跨平台配色"""
        status_bg = self.theme_manager.get_platform_color('background_secondary')
        status_frame = tk.Frame(parent, bg=status_bg, height=18)
        status_frame.pack(fill=tk.X, padx=1, pady=0)
        status_frame.pack_propagate(False)
        
        # 左側圖像信息 - 緊湊布局
        left_info = tk.Frame(status_frame, bg=status_bg)
        left_info.pack(side=tk.LEFT, padx=5, pady=1)
        
        # 分辨率信息 - 使用跨平台標籤
        self.resolution_var = tk.StringVar(value="640 × 480")
        resolution_label = self.theme_manager.create_cross_platform_label(
            left_info, "", label_type="caption"
        )
        resolution_label.configure(textvariable=self.resolution_var)
        resolution_label.pack(side=tk.LEFT)
        
        # 分隔符
        sep1 = self.theme_manager.create_cross_platform_label(
            left_info, " | ", label_type="caption"
        )
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
        """開始新批次 - 支持視頻回放模式"""
        try:
            # 🎯 關鍵修復：檢查當前模式
            current_mode = self.controller.get_current_mode() if hasattr(self.controller, 'get_current_mode') else 'live'
            
            # 檢查批次狀態
            if hasattr(self, 'batch_mode') and self.batch_mode == 'running':
                messagebox.showinfo("提示", "批次檢測已在運行中")
                return
            
            # 模式專用檢查和處理
            if current_mode == 'playback':
                # 🎯 視頻回放模式檢查
                if not hasattr(self, 'video_loaded') or not self.video_loaded:
                    messagebox.showwarning("警告", "請先選擇並載入視頻檔案")
                    return
                
                # 啟動視頻回放檢測
                if hasattr(self.controller, 'start_batch_detection'):
                    success = self.controller.start_batch_detection()
                    if success:
                        # 更新UI狀態
                        self.batch_mode = 'running'
                        self.current_batch_count = 0
                        self.batch_start_time = time.time()
                        
                        if hasattr(self, 'start_batch_btn'):
                            self.start_batch_btn.config(state='disabled', text="🔄 檢測中")
                        if hasattr(self, 'stop_batch_btn'):
                            self.stop_batch_btn.config(state='normal')
                        
                        logging.info(f"✅ 視頻回放批次檢測已啟動，目標: {self.target_count_var.get()}")
                    else:
                        messagebox.showerror("錯誤", "啟動視頻檢測失敗")
                        return
                        
            elif current_mode == 'live':
                # 📹 實時相機模式檢查
                if not self.is_camera_connected:
                    messagebox.showwarning("警告", "請先連接相機")
                    return
                
                # 啟動相機檢測
                if hasattr(self.controller, 'start_batch_detection'):
                    success = self.controller.start_batch_detection()
                    if success:
                        # 更新UI狀態
                        self.batch_mode = 'running'
                        self.current_batch_count = 0
                        self.batch_start_time = time.time()
                        
                        if hasattr(self, 'start_batch_btn'):
                            self.start_batch_btn.config(state='disabled', text="🔄 檢測中")
                        if hasattr(self, 'stop_batch_btn'):
                            self.stop_batch_btn.config(state='normal')
                        
                        logging.info(f"✅ 相機批次檢測已啟動，目標: {self.target_count_var.get()}")
                    else:
                        messagebox.showerror("錯誤", "啟動相機檢測失敗")
                        return
                        
            else:
                messagebox.showinfo("提示", f"不支持的模式: {current_mode}")
                return
                
        except Exception as e:
            logging.error(f"啟動批次檢測錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"啟動失敗: {str(e)}")
            
            # 復原按鈕狀態
            if hasattr(self, 'start_batch_btn'):
                self.start_batch_btn.config(state='normal', text="▶ 開始")
            if hasattr(self, 'stop_batch_btn'):
                self.stop_batch_btn.config(state='disabled')
    
    def stop_batch(self):
        """停止當前批次 - 支持視頻回放模式"""
        try:
            if hasattr(self, 'batch_mode') and self.batch_mode == 'running':
                self.batch_mode = 'idle'
                
                # 🔄 修復：正確恢原UI狀態和按鈕文字
                if hasattr(self, 'start_batch_btn'):
                    self.start_batch_btn.config(state='normal', text="▶ 開始")
                if hasattr(self, 'stop_batch_btn'):
                    self.stop_batch_btn.config(state='disabled')
                
                # 通知控制器停止檢測
                if hasattr(self.controller, 'stop_batch_detection'):
                    success = self.controller.stop_batch_detection()
                    if success:
                        logging.info(f"⏹️ 手動停止批次，當前計數: {getattr(self, 'current_batch_count', 0)}")
                    else:
                        logging.warning("停止批次檢測失敗")
                
        except Exception as e:
            logging.error(f"停止批次錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"停止失敗: {str(e)}")
            
            # 確保恢原按鈕狀態
            if hasattr(self, 'start_batch_btn'):
                self.start_batch_btn.config(state='normal', text="▶ 開始")
            if hasattr(self, 'stop_batch_btn'):
                self.stop_batch_btn.config(state='disabled')
    
    def complete_batch(self):
        """完成批次 - 達到目標數量時調用"""
        try:
            if hasattr(self, 'batch_mode') and self.batch_mode == 'running':
                self.batch_mode = 'completed'
                
                # 更新UI狀態
                if hasattr(self, 'start_batch_btn'):
                    self.start_batch_btn.config(state='normal', text="▶ 開始")
                if hasattr(self, 'stop_batch_btn'):
                    self.stop_batch_btn.config(state='disabled')
                
                # 通知控制器停止檢測
                if hasattr(self.controller, 'stop_batch_detection'):
                    self.controller.stop_batch_detection()
                
                # 給出完成提示
                final_count = getattr(self, 'current_batch_count', 0)
                target = self.target_count_var.get()
                elapsed_time = time.time() - getattr(self, 'batch_start_time', time.time())
                
                completion_msg = f"🎉 批次完成！\n\n"
                completion_msg += f"目標數量: {target}\n"
                completion_msg += f"實際計數: {final_count}\n"
                completion_msg += f"耗時: {elapsed_time:.1f} 秒\n\n"
                
                if final_count >= target:
                    completion_msg += "✅ 目標達成！"
                else:
                    completion_msg += "⚠️ 未達成目標"
                
                messagebox.showinfo("批次完成", completion_msg)
                
                # 更新統計
                if hasattr(self, 'total_batches_today'):
                    self.total_batches_today += 1
                if hasattr(self, 'total_items_today'):
                    self.total_items_today += final_count
                
                logging.info(f"🎉 批次完成 - 目標: {target}, 實際: {final_count}, 耗時: {elapsed_time:.1f}s")
                
                # 重置批次狀態
                self.batch_mode = 'idle'
                
        except Exception as e:
            logging.error(f"完成批次錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"完成批次失敗: {str(e)}")
    
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
            
            # 視頻事件處理
            elif event_type.startswith('recorder_') or event_type.startswith('player_'):
                self.handle_video_events(event_type, data)
            
            elif event_type == 'mode_changed':
                # 模式切換事件
                mode = data.get('mode', 'live')
                self.video_mode.set(mode)
                self.update_video_control_ui()
                description = data.get('description', mode)
                self.status_var.set(f"模式: {description}")
                
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
        """更新狀態顯示 - 根據模式動態顯示"""
        try:
            status = self.controller.get_system_status()
            current_mode = status.get('current_mode', 'live')
            
            # 🎯 關鍵修復：根據系統模式顯示不同數據
            if current_mode == 'playback':
                # 視頻回放模式：顯示視頻相關數據
                self._update_playback_status_display(status)
            else:
                # 實時相機模式：顯示相機數據
                self._update_camera_status_display(status)
            
        except Exception as e:
            logging.error(f"更新狀態顯示錯誤: {str(e)}")
    
    def _update_camera_status_display(self, status):
        """更新相機模式狀態顯示 - 修正處理速度顯示"""
        try:
            # 添加到歷史記錄
            self.fps_history['camera'].append(status['camera_fps'])
            self.fps_history['processing'].append(status['processing_fps'])
            self.fps_history['detection'].append(status['detection_fps'])
            
            # 限制歷史記錄大小
            for key in self.fps_history:
                if len(self.fps_history[key]) > 10:
                    self.fps_history[key].pop(0)
            
            # 每5次更新才刷新一次顯示
            self.fps_update_counter += 1
            if self.fps_update_counter >= 5:
                self.fps_update_counter = 0
                
                # 計算平滑的平均值
                camera_avg = sum(self.fps_history['camera']) / len(self.fps_history['camera']) if self.fps_history['camera'] else 0
                processing_avg = sum(self.fps_history['processing']) / len(self.fps_history['processing']) if self.fps_history['processing'] else 0
                detection_avg = sum(self.fps_history['detection']) / len(self.fps_history['detection']) if self.fps_history['detection'] else 0
                
                # 格式化顯示文字
                camera_fps_text = f"{min(camera_avg, 999.0):.1f} fps" if camera_avg < 1000 else "999+ fps"
                processing_fps_text = f"{min(processing_avg, 999.0):.1f} fps" if processing_avg < 1000 else "999+ fps"
                detection_fps_text = f"{min(detection_avg, 999.0):.1f} fps" if detection_avg < 1000 else "999+ fps"
                
                # 計算數據速率
                data_rate = (camera_avg * 86) / 1024  # MB/s
                data_rate_text = f"({data_rate:.1f} MB/s)" if data_rate < 1000 else "(999+ MB/s)"
                
                # 🚀 新的邏輯結構：
                # 第一欄：工業相機運行幀率
                # 第二欄：檢測處理幀率（每秒檢測幀數）
                # 第三欄：有意義的關聯信息（處理效率、物件數等）
                
                # 計算處理效率（處理速度 / 相機速度）
                processing_efficiency = (processing_avg / camera_avg * 100) if camera_avg > 0 else 0
                efficiency_text = f"({processing_efficiency:.1f}%)"
                
                # 獲取物件計數信息
                object_count = status.get('object_count', 0)
                total_processed = status.get('processing_total_frames', 0)
                
                self.camera_fps_var.set(f"相機: {camera_fps_text} {data_rate_text}")
                self.processing_fps_var.set(f"處理: {processing_fps_text} {efficiency_text}")
                self.detection_fps_var.set(f"物件: {object_count} / {total_processed}幀")
                
                # 🎯 記錄詳細資訊用於調試
                logging.debug(f"📊 相機狀態 - 處理: {processing_avg:.1f}fps, 相機: {camera_avg:.1f}fps, 檢測: {detection_avg:.1f}fps")
                
        except Exception as e:
            logging.error(f"更新相機狀態顯示錯誤: {str(e)}")
    
    def _update_playback_status_display(self, status):
        """更新視頻回放模式狀態顯示 - 邏輯版本"""
        try:
            # 🎯 視頻回放專用狀態顯示
            video_processing_fps = status.get('video_processing_fps', 0)  # 檢測處理幀率
            detection_fps = status.get('detection_fps', 0)
            video_fps = status.get('video_fps', 0)  # 視頻原始幀率
            
            # 🎬 視頻規格信息（用於參考）
            video_info = status.get('video_info', {})
            width = video_info.get('width', 0)
            height = video_info.get('height', 0)
            codec = video_info.get('codec', 'N/A')
            
            # 🎯 時間軸信息
            time_format = status.get('time_format', '00:00 / 00:00')
            video_progress = status.get('video_progress', 0)
            
            # 格式化顯示
            processing_fps_text = f"{min(video_processing_fps, 999.0):.1f} fps" if video_processing_fps < 1000 else "999+ fps"
            detection_fps_text = f"{min(detection_fps, 999.0):.1f} fps" if detection_fps < 1000 else "999+ fps"
            
            # 🚀 新顯示結構：第一欄顯示平均處理速度，不是視頻FPS
            progress_text = f"({video_progress:.1f}%)"
            
            # 🎬 視頻規格信息作為參考
            if width > 0 and height > 0:
                spec_text = f"{width}x{height} {codec}"
            else:
                spec_text = f"{video_fps:.1f}fps"
            
            # 🚀 新的邏輯結構（回放模式）：
            # 第一欄：視頻原始FPS（作為參考）
            # 第二欄：檢測處理幀率（每秒檢測幀數）  
            # 第三欄：時間軸 + 視頻規格
            
            # 獲取物件計數信息
            object_count = status.get('object_count', 0)
            total_processed = status.get('total_frames_processed', 0)
            
            self.camera_fps_var.set(f"視頻: {video_fps:.1f}fps {progress_text}")
            self.processing_fps_var.set(f"處理: {processing_fps_text}")
            self.detection_fps_var.set(f"{time_format} [{spec_text}]")
            
            # 🎯 記錄詳細資訊用於調試
            logging.debug(f"📊 回放狀態 - 處理: {video_processing_fps:.1f}fps, 檢測: {detection_fps:.1f}fps")
            
        except Exception as e:
            logging.error(f"更新視頻回放狀態顯示錯誤: {str(e)}")
    
    def _format_time(self, seconds: float) -> str:
        """格式化時間顯示"""
        if seconds < 0:
            return "00:00"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _get_video_fps(self) -> float:
        """獲取視頻 FPS 信息 - 使用實際視頻規格"""
        try:
            # 🎯 從 controller獲取實際視頻的 FPS
            status = self.controller.get_system_status()
            if status.get('current_mode') == 'playback':
                actual_fps = status.get('video_fps', 0)
                if actual_fps > 0:
                    logging.debug(f"獲取實際視頻 FPS: {actual_fps:.2f}")
                    return actual_fps
                else:
                    logging.warning(f"視頻FPS異常: {actual_fps}, 使用預設值")
                    return 25.0  # 備用預設值
            return 25.0  # 非回放模式預設值
        except Exception as e:
            logging.error(f"獲取視頻 FPS 失敗: {e}")
            return 25.0  # 備用預設值
            
    # 注意：這個方法保留作為備用，主要使用frame_data中的fps
    
    def _format_video_spec(self, video_info: dict) -> str:
        """格式化視頻規格信息顯示"""
        try:
            width = video_info.get('width', 0)
            height = video_info.get('height', 0)
            fps = video_info.get('fps', 0)
            codec = video_info.get('codec', 'N/A')
            
            if width > 0 and height > 0:
                return f"{width}x{height}@{fps:.0f}fps/{codec}"
            elif fps > 0:
                return f"{fps:.1f}fps"
            else:
                return "N/A"
        except:
            return "N/A"
    
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
        """設備列表雙擊事件 - 線程安全版本"""
        try:
            selection = self.device_listbox.curselection()
            if not selection or not self.detected_cameras:
                self.status_var.set("錯誤: 請選擇有效的設備")
                return
                
            selected_index = selection[0]
            if selected_index >= len(self.detected_cameras):
                self.status_var.set("錯誤: 設備索引無效")
                return
            
            selected_camera = self.detected_cameras[selected_index]
            camera_model = selected_camera['model']
            
            # 🔒 防止重複連接
            if self.is_camera_connected and self.selected_camera_index == selected_index:
                self.status_var.set(f"狀態: {camera_model} 已經連接")
                return
            
            # 🛑 如果已經連接其他設備，先安全斷開
            if self.is_camera_connected:
                self.status_var.set("狀態: 斷開現有連接...")
                self.disconnect_camera()
                time.sleep(0.5)  # 確保斷開完成
            
            # 🔗 開始連接過程
            self.selected_camera_index = selected_index
            self.status_var.set(f"狀態: 正在連接 {camera_model}...")
            
            # 禁用相關按鈕防止重複操作
            self._disable_connection_controls()
            
            try:
                # 🎯 連接相機（控制器會自動處理線程安全）
                success = self.controller.connect_camera(selected_index)
                
                if success:
                    # ✅ 連接成功
                    self.is_camera_connected = True
                    self.connection_switch_on = True
                    
                    # 🚀 自動啟動捕獲（使用控制器的統一方法）
                    capture_success = self.controller.start_capture()
                    if capture_success:
                        self.status_var.set(f"狀態: {camera_model} 已連接並開始捕獲")
                        logging.info(f"✅ 設備連接並啟動成功: {camera_model}")
                    else:
                        self.status_var.set(f"狀態: {camera_model} 已連接，但啟動捕獲失敗")
                        logging.warning(f"⚠️ 設備連接成功但捕獲失敗: {camera_model}")
                    
                    # 更新UI狀態
                    self.update_connection_ui()
                    self.update_device_list_ui()
                    
                else:
                    # ❌ 連接失敗
                    self.status_var.set(f"錯誤: 無法連接 {camera_model}")
                    logging.error(f"❌ 設備連接失敗: {camera_model}")
                    
                    # 重置狀態
                    self.is_camera_connected = False
                    self.connection_switch_on = False
                    self.selected_camera_index = -1
                    
            finally:
                # 恢復按鈕狀態
                self._enable_connection_controls()
                
        except Exception as e:
            logging.error(f"❌ 設備雙擊連接錯誤: {str(e)}")
            self.status_var.set(f"錯誤: 連接操作失敗 - {str(e)}")
            
            # 確保狀態一致性
            self.is_camera_connected = False
            self.connection_switch_on = False
            self.selected_camera_index = -1
            self.update_connection_ui()
            self._enable_connection_controls()
    
    def _disable_connection_controls(self):
        """禁用連接相關控制"""
        try:
            if hasattr(self, 'connection_switch'):
                self.connection_switch.config(state='disabled')
            if hasattr(self, 'device_listbox'):
                self.device_listbox.config(state='disabled')
        except Exception as e:
            logging.debug(f"禁用控制錯誤: {str(e)}")
    
    def _enable_connection_controls(self):
        """啟用連接相關控制"""
        try:
            if hasattr(self, 'connection_switch'):
                self.connection_switch.config(state='normal')
            if hasattr(self, 'device_listbox'):
                self.device_listbox.config(state='normal')
        except Exception as e:
            logging.debug(f"啟用控制錯誤: {str(e)}")
    
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
    
    # ==================== 視頻控制事件處理 ====================
    
    def generate_recording_filename(self):
        """生成錄製檔名"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"camera_rec_{timestamp}"
    
    def on_video_mode_change(self):
        """視頻模式切換 - 添加檢查和用戶反饋"""
        mode = self.video_mode.get()
        
        try:
            # 🎯 關鍵修復：檢查是否有正在運行的批次檢測
            if hasattr(self, 'batch_mode') and self.batch_mode == 'running':
                result = messagebox.askyesno("確認", 
                    f"當前有正在運行的批次檢測，\n切換到模式 '{mode}' 將停止檢測。\n\n是否繼續？")
                if not result:
                    # 用戶取消，恢原模式選擇
                    current_mode = self.controller.get_current_mode()
                    self.video_mode.set(current_mode)
                    return
                else:
                    # 用戶確認，停止批次檢測
                    self.stop_batch()
            
            # 嘗試切換模式
            success = self.controller.switch_mode(mode)
            
            if success:
                self.update_video_control_ui()
                
                # 給出用戶反饋
                mode_names = {
                    'live': '實時檢測模式',
                    'recording': '錄製模式', 
                    'playback': '視頻回放模式'
                }
                logging.info(f"✅ 已切換到: {mode_names.get(mode, mode)}")
                
                # 清理批次狀態（新模式下重新開始）
                if hasattr(self, 'batch_mode'):
                    self.batch_mode = 'idle'
                if hasattr(self, 'current_batch_count'):
                    self.current_batch_count = 0
                    
                # 更新批次顯示
                if hasattr(self, 'batch_count_var'):
                    self.batch_count_var.set("000")
                if hasattr(self, 'progress_text'):
                    self.progress_text.config(text=f"0 / {self.target_count_var.get()}")
                if hasattr(self, 'batch_progress'):
                    self.batch_progress.config(value=0)
                    
            else:
                # 切換失敗，恢原原來的模式選擇
                current_mode = self.controller.get_current_mode()
                self.video_mode.set(current_mode)
                messagebox.showerror("錯誤", f"切換到模式 '{mode}' 失敗")
                
        except Exception as e:
            logging.error(f"視頻模式切換錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"模式切換失敗: {str(e)}")
            
            # 恢原原來的模式選擇
            try:
                current_mode = self.controller.get_current_mode()
                self.video_mode.set(current_mode)
            except:
                pass
        
    def update_video_control_ui(self):
        """更新視頻控制UI狀態"""
        mode = self.video_mode.get()
        
        # 根據模式顯示/隱藏對應控制面板
        if mode == "recording":
            self.recording_frame.pack(fill=tk.X, pady=(0, 5))
            self.playback_frame.pack_forget()
        elif mode == "playback":
            self.recording_frame.pack_forget()
            self.playback_frame.pack(fill=tk.X, pady=(0, 5))
        else:  # live
            self.recording_frame.pack_forget()
            self.playback_frame.pack_forget()
    
    def toggle_recording(self):
        """切換錄製狀態"""
        if not self.is_recording:
            # 開始錄製
            filename = self.recording_filename.get().strip()
            if not filename:
                messagebox.showerror("錯誤", "請輸入錄製檔名")
                return
                
            success = self.controller.start_recording(filename)
            if success:
                self.is_recording = True
                self.record_btn.config(text="⏹️ 停止錄製", bg='#ff9500')
                self.recording_status.config(text="錄製中...", fg='#ff4444')
        else:
            # 停止錄製
            info = self.controller.stop_recording()
            self.is_recording = False
            self.record_btn.config(text="🔴 開始錄製", bg='#ff4444')
            self.recording_status.config(text="錄製完成", fg='#34c759')
            
            if info:
                messagebox.showinfo("錄製完成", 
                                  f"錄製完成！\n"
                                  f"檔案: {info.get('filename', 'unknown')}\n"
                                  f"幀數: {info.get('frames_recorded', 0)}\n"
                                  f"時長: {info.get('duration', 0):.1f}秒")
    
    def select_video_file(self):
        """選擇視頻文件"""
        from tkinter import filedialog
        filetypes = [
            ("Video files", "*.avi *.mp4 *.mov *.mkv"),
            ("AVI files", "*.avi"),
            ("MP4 files", "*.mp4"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="選擇視頻文件",
            filetypes=filetypes
        )
        
        if filename:
            success = self.controller.load_video(filename)
            if success:
                import os
                self.selected_video_path.set(os.path.basename(filename))
                self.video_loaded = True
                self.play_btn.config(state='normal')
            else:
                messagebox.showerror("錯誤", "無法加載視頻文件")
    
    def toggle_playback(self):
        """切換播放狀態"""
        if not self.video_loaded:
            messagebox.showwarning("警告", "請先選擇視頻文件")
            return
            
        if not self.is_playing:
            # 開始播放
            success = self.controller.start_video_playback()
            if success:
                self.is_playing = True
                self.play_btn.config(text="⏸️")
        else:
            # 暫停播放
            self.controller.pause_video_playback()
            self.play_btn.config(text="▶️")
    
    def pause_playback(self):
        """暫停播放"""
        if self.is_playing:
            self.controller.pause_video_playback()
    
    def stop_playback(self):
        """停止播放"""
        if self.is_playing:
            self.controller.stop_video_playback()
            self.is_playing = False
            self.play_btn.config(text="▶️")
            self.video_progress.set(0)
            self.frame_info.config(text="")
    
    def on_speed_change(self, value):
        """播放速度改變"""
        speed = float(value)
        self.controller.set_playback_speed(speed)
    
    def on_progress_change(self, value):
        """進度條改變"""
        if self.video_loaded:
            progress = float(value)
            self.controller.seek_video_to_progress(progress)
    
    def update_video_progress(self, progress, frame_number, total_frames, video_timestamp=None, fps=None):
        """更新視頻播放進度 - 時間軸版本"""
        self.video_progress.set(progress)
        
        # 🎯 關鍵修復：使用實際視頻規格顯示時間
        if video_timestamp is not None and fps is not None and fps > 0:
            # 使用實際視頻FPS計算時間
            current_time = video_timestamp
            total_time = total_frames / fps
            
            # 格式化時間顯示
            current_time_str = self._format_time(current_time)
            total_time_str = self._format_time(total_time)
            
            # 🚀 顯示時間格式（使用實際FPS: {fps:.1f}）
            self.frame_info.config(text=f"時間: {current_time_str}/{total_time_str}")
            
            # 第一次顯示時記錄FPS信息
            if frame_number == 1:
                logging.info(f"🎬 視頻規格 - FPS: {fps:.2f}, 總時長: {total_time:.2f}秒")
        else:
            # 備用顯示：如果沒有時間信息，仍顯示幀數
            self.frame_info.config(text=f"幀: {frame_number}/{total_frames}")
            
            # 警告：缺少FPS信息
            if frame_number == 1:
                logging.warning(f"⚠️ 視頻缺少FPS信息，使用幀數顯示: fps={fps}, timestamp={video_timestamp}")
    
    def handle_video_events(self, event_type, data):
        """處理視頻相關事件 - 時間軸版本"""
        try:
            if event_type == 'player_frame_ready':
                # 🎯 更新進度，使用實際視頻規格信息
                progress = data.get('progress', 0)
                frame_number = data.get('frame_number', 0)
                total_frames = data.get('total_frames', 0)
                video_timestamp = data.get('video_timestamp')  # 視頻時間戳
                fps = data.get('fps')  # 🎯 直接從視頻數據獲取實際FPS
                
                # 🚀 使用實際視頻規格更新進度顯示
                self.update_video_progress(progress, frame_number, total_frames, video_timestamp, fps)
                
                # 記錄實際使用的FPS值用於調試
                if frame_number % 100 == 0 and fps:  # 每100幀記錄一次
                    logging.debug(f"視頻規格 - FPS: {fps:.2f}, 幀 {frame_number}/{total_frames}")
                
            elif event_type == 'player_playback_finished':
                self.is_playing = False
                self.play_btn.config(text="▶️")
                
            elif event_type == 'recorder_recording_progress':
                frames = data.get('frames_recorded', 0)
                duration = data.get('duration', 0)
                self.recording_status.config(text=f"錄製中... {frames}幀 {duration:.1f}s")
                
        except Exception as e:
            logging.error(f"處理視頻事件錯誤: {str(e)}")