"""
主視圖 - CustomTkinter 版本
解決跨平台顯示模糊問題，支援高 DPI 和自動縮放
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
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
    """主視圖 - CustomTkinter 高清版本"""
    
    def __init__(self, controller):
        """初始化主視圖"""
        self.controller = controller
        
        # 創建主窗口
        self.root = ctk.CTk()
        
        # 註冊為控制器觀察者
        self.controller.add_view_observer(self.on_controller_event)
        
        # 視窗設置
        self.root.title("🚀 Basler acA640-300gm 精簡高性能系統")
        
        # 獲取螢幕尺寸並設定視窗大小
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 設定最佳尺寸（螢幕的85%）
        optimal_width = min(int(screen_width * 0.85), 1600)
        optimal_height = min(int(screen_height * 0.85), 1000)
        
        # 計算居中位置
        x = (screen_width - optimal_width) // 2
        y = (screen_height - optimal_height) // 2
        
        self.root.geometry(f"{optimal_width}x{optimal_height}+{x}+{y}")
        self.root.minsize(1200, 800)
        
        # UI 變量
        self.status_var = ctk.StringVar(value="狀態: 系統就緒")
        self.camera_fps_var = ctk.StringVar(value="相機: 0 FPS")
        self.processing_fps_var = ctk.StringVar(value="處理: 0 FPS")
        self.detection_fps_var = ctk.StringVar(value="檢測: 0 FPS")
        self.object_count_var = ctk.StringVar(value="當前計數: 000")
        self.method_var = ctk.StringVar(value="circle")
        self.exposure_var = ctk.DoubleVar(value=1000.0)
        self.min_area_var = ctk.IntVar(value=100)
        self.max_area_var = ctk.IntVar(value=5000)
        self.target_count_var = ctk.IntVar(value=100)
        
        # 模式變量
        self.mode_var = ctk.StringVar(value="live")
        
        # 視頻顯示
        self.video_label = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # 顯示設置
        self.display_size = (640, 480)
        
        # 設備列表
        self.device_listbox = None
        self.devices = []
        
        # 創建UI
        self.create_ui()
        
        # 初始化
        self.refresh_device_list()
        self.update_connection_ui()
        
        logging.info("CustomTkinter 主視圖初始化完成")
    
    def create_ui(self):
        """創建用戶界面"""
        # 創建主要框架
        self.create_main_layout()
        
        # 創建各個面板
        self.create_left_panel()
        self.create_center_panel()
        self.create_right_panel()
        self.create_bottom_status()
    
    def create_main_layout(self):
        """創建主要佈局"""
        # 配置主窗口的網格權重
        self.root.grid_columnconfigure(1, weight=1)  # 中間列可擴展
        self.root.grid_rowconfigure(0, weight=1)     # 主要行可擴展
        
        # 左側面板
        self.left_frame = ctk.CTkFrame(self.root)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        
        # 中間面板（視頻顯示）
        self.center_frame = ctk.CTkFrame(self.root)
        self.center_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=10)
        
        # 右側面板
        self.right_frame = ctk.CTkFrame(self.root)
        self.right_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)
        
        # 底部狀態欄
        self.status_frame = ctk.CTkFrame(self.root, height=100)
        self.status_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))
        self.status_frame.grid_propagate(False)
    
    def create_left_panel(self):
        """創建左側控制面板"""
        # 面板標題
        title_label = ctk.CTkLabel(
            self.left_frame, 
            text="📷 設備控制",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(15, 10))
        
        # 設備列表區域
        device_frame = ctk.CTkFrame(self.left_frame)
        device_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(device_frame, text="偵測到的設備", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 5))
        
        # 設備列表框
        self.device_listbox = ctk.CTkTextbox(device_frame, height=100, width=250)
        self.device_listbox.pack(padx=10, pady=(0, 10))
        
        # 連接按鈕
        self.connect_btn = ctk.CTkButton(
            device_frame,
            text="🔗 連接設備",
            command=self.connect_device,
            height=35
        )
        self.connect_btn.pack(pady=(0, 15))
        
        # 連接狀態
        self.connection_status = ctk.CTkLabel(
            device_frame,
            text="● 未連接",
            text_color="red",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.connection_status.pack(pady=(0, 10))
        
        # 控制按鈕區域
        control_frame = ctk.CTkFrame(self.left_frame)
        control_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(control_frame, text="🎮 相機控制", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 5))
        
        # 開始/停止按鈕
        self.start_btn = ctk.CTkButton(
            control_frame,
            text="▶️ 開始捕獲",
            command=self.start_capture,
            height=35
        )
        self.start_btn.pack(pady=5, padx=10, fill="x")
        
        self.stop_btn = ctk.CTkButton(
            control_frame,
            text="⏹️ 停止捕獲",
            command=self.stop_capture,
            height=35
        )
        self.stop_btn.pack(pady=5, padx=10, fill="x")
        
        # 曝光控制
        exposure_frame = ctk.CTkFrame(control_frame)
        exposure_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(exposure_frame, text="曝光時間 (μs)", font=ctk.CTkFont(size=11)).pack()
        
        self.exposure_entry = ctk.CTkEntry(
            exposure_frame,
            textvariable=self.exposure_var,
            width=100,
            justify="center"
        )
        self.exposure_entry.pack(pady=5)
        
        ctk.CTkButton(
            exposure_frame,
            text="套用曝光",
            command=self.apply_exposure,
            height=25
        ).pack(pady=(5, 10))
        
        # 啟用即時檢測
        self.enable_detection_var = ctk.BooleanVar(value=True)
        self.detection_checkbox = ctk.CTkCheckBox(
            control_frame,
            text="啟用即時檢測",
            variable=self.enable_detection_var,
            command=self.toggle_detection
        )
        self.detection_checkbox.pack(pady=(10, 15))
        
        # 檢測方法選擇
        method_frame = ctk.CTkFrame(self.left_frame)
        method_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(method_frame, text="🔍 檢測方法", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 5))
        
        self.method_menu = ctk.CTkOptionMenu(
            method_frame,
            values=["circle", "contour"],
            variable=self.method_var,
            command=self.change_detection_method
        )
        self.method_menu.pack(pady=(0, 15), padx=10)
        
        # 模式選擇
        mode_frame = ctk.CTkFrame(self.left_frame)
        mode_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(mode_frame, text="📺 系統模式", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 5))
        
        # 模式單選按鈕
        self.mode_live = ctk.CTkRadioButton(mode_frame, text="實時", variable=self.mode_var, value="live", command=self.change_mode)
        self.mode_live.pack(anchor="w", padx=20, pady=2)
        
        self.mode_recording = ctk.CTkRadioButton(mode_frame, text="錄影", variable=self.mode_var, value="recording", command=self.change_mode)
        self.mode_recording.pack(anchor="w", padx=20, pady=2)
        
        self.mode_playback = ctk.CTkRadioButton(mode_frame, text="回放", variable=self.mode_var, value="playback", command=self.change_mode)
        self.mode_playback.pack(anchor="w", padx=20, pady=(2, 15))
    
    def create_center_panel(self):
        """創建中央視頻顯示面板"""
        # 配置中央面板的網格
        self.center_frame.grid_rowconfigure(1, weight=1)
        self.center_frame.grid_columnconfigure(0, weight=1)
        
        # 頂部工具欄
        toolbar_frame = ctk.CTkFrame(self.center_frame)
        toolbar_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        # 相機信息標籤
        self.camera_info_label = ctk.CTkLabel(
            toolbar_frame,
            text="📹 Basler acA640-300gm - 實時影像",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.camera_info_label.pack(side="left", padx=10, pady=8)
        
        # 縮放控制
        zoom_frame = ctk.CTkFrame(toolbar_frame)
        zoom_frame.pack(side="right", padx=10, pady=5)
        
        ctk.CTkLabel(zoom_frame, text="🔍").pack(side="left", padx=(5, 0))
        
        self.zoom_var = ctk.StringVar(value="100%")
        zoom_menu = ctk.CTkOptionMenu(
            zoom_frame,
            values=["50%", "75%", "100%", "125%", "150%"],
            variable=self.zoom_var,
            width=80,
            command=self.change_zoom
        )
        zoom_menu.pack(side="left", padx=5)
        
        # 視頻顯示區域
        video_frame = ctk.CTkFrame(self.center_frame)
        video_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        video_frame.grid_rowconfigure(0, weight=1)
        video_frame.grid_columnconfigure(0, weight=1)
        
        # 創建視頻標籤
        self.video_label = ctk.CTkLabel(
            video_frame,
            text="Basler acA640-300gm\n📹 Camera Ready\n配置開始捕獲取得影像",
            font=ctk.CTkFont(size=16),
            width=640,
            height=480
        )
        self.video_label.grid(row=0, column=0, padx=20, pady=20)
        
        # 底部信息欄
        info_frame = ctk.CTkFrame(self.center_frame, height=40)
        info_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
        info_frame.grid_propagate(False)
        
        # 分辨率信息
        self.resolution_label = ctk.CTkLabel(info_frame, text="640 x 480 │ Mono8 │ 8 bit")
        self.resolution_label.pack(side="left", padx=15, pady=10)
        
        # 物件計數顯示
        self.count_display = ctk.CTkLabel(
            info_frame,
            text="物件: 0",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#1f6aa5"
        )
        self.count_display.pack(side="right", padx=15, pady=10)
    
    def create_right_panel(self):
        """創建右側參數控制面板"""
        # 標題
        title_label = ctk.CTkLabel(
            self.right_frame,
            text="⚙️ 檢測設定",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_label.pack(pady=(15, 10))
        
        # 當前計數顯示
        count_frame = ctk.CTkFrame(self.right_frame)
        count_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(count_frame, text="當前計數", font=ctk.CTkFont(size=12)).pack(pady=(10, 5))
        
        self.count_label = ctk.CTkLabel(
            count_frame,
            textvariable=self.object_count_var,
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#1f6aa5"
        )
        self.count_label.pack(pady=10)
        
        # 目標數量設定
        target_frame = ctk.CTkFrame(self.right_frame)
        target_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(target_frame, text="目標數量:", font=ctk.CTkFont(size=11)).pack(pady=(10, 5))
        
        self.target_entry = ctk.CTkEntry(
            target_frame,
            textvariable=self.target_count_var,
            width=100,
            justify="center"
        )
        self.target_entry.pack(pady=5)
        
        # 進度條
        self.progress_bar = ctk.CTkProgressBar(target_frame, width=200)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        ctk.CTkLabel(target_frame, text="0 / 100").pack(pady=(0, 10))
        
        # 重置按鈕
        ctk.CTkButton(
            target_frame,
            text="🔄 重置計數",
            command=self.reset_count,
            height=30
        ).pack(pady=(5, 15))
        
        # 檢測參數
        params_frame = ctk.CTkFrame(self.right_frame)
        params_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(params_frame, text="🔧 檢測參數", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 5))
        
        # 最小面積
        ctk.CTkLabel(params_frame, text="最小面積", font=ctk.CTkFont(size=10)).pack(pady=(5, 0))
        self.min_area_slider = ctk.CTkSlider(
            params_frame,
            from_=10,
            to=500,
            variable=self.min_area_var,
            command=self.update_detection_params
        )
        self.min_area_slider.pack(pady=5, padx=10, fill="x")
        
        self.min_area_label = ctk.CTkLabel(params_frame, text="100")
        self.min_area_label.pack()
        
        # 最大面積
        ctk.CTkLabel(params_frame, text="最大面積", font=ctk.CTkFont(size=10)).pack(pady=(10, 0))
        self.max_area_slider = ctk.CTkSlider(
            params_frame,
            from_=1000,
            to=10000,
            variable=self.max_area_var,
            command=self.update_detection_params
        )
        self.max_area_slider.pack(pady=5, padx=10, fill="x")
        
        self.max_area_label = ctk.CTkLabel(params_frame, text="5000")
        self.max_area_label.pack(pady=(0, 15))
        
        # 統計信息
        stats_frame = ctk.CTkFrame(self.right_frame)
        stats_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(stats_frame, text="📊 系統統計", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(10, 5))
        
        # 檢測品質指示器
        quality_frame = ctk.CTkFrame(stats_frame)
        quality_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(quality_frame, text="檢測品質").pack()
        self.quality_label = ctk.CTkLabel(
            quality_frame,
            text="良好",
            text_color="green",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.quality_label.pack(pady=(0, 10))
        
        # 檢測 FPS 顯示
        self.detection_fps_label = ctk.CTkLabel(
            stats_frame,
            textvariable=self.detection_fps_var,
            font=ctk.CTkFont(size=10)
        )
        self.detection_fps_label.pack(pady=(5, 15))
    
    def create_bottom_status(self):
        """創建底部狀態欄"""
        # 狀態信息
        status_info_frame = ctk.CTkFrame(self.status_frame)
        status_info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # 狀態：攝影機連接狀態
        self.status_label = ctk.CTkLabel(
            status_info_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=11)
        )
        self.status_label.pack(side="left", padx=10)
        
        # 相機信息
        self.camera_info_status = ctk.CTkLabel(
            status_info_frame,
            text="相機: 未連接",
            font=ctk.CTkFont(size=11)
        )
        self.camera_info_status.pack(side="left", padx=20)
        
        # 性能信息框架
        perf_frame = ctk.CTkFrame(self.status_frame)
        perf_frame.pack(side="right", padx=10, pady=10)
        
        # FPS 信息
        self.camera_fps_label = ctk.CTkLabel(
            perf_frame,
            textvariable=self.camera_fps_var,
            text_color="green",
            font=ctk.CTkFont(size=10)
        )
        self.camera_fps_label.pack(side="left", padx=5)
        
        self.processing_fps_label = ctk.CTkLabel(
            perf_frame,
            textvariable=self.processing_fps_var,
            text_color="blue",
            font=ctk.CTkFont(size=10)
        )
        self.processing_fps_label.pack(side="left", padx=5)
        
        # 時間戳
        self.timestamp_label = ctk.CTkLabel(
            perf_frame,
            text="2025-08-07 15:09:18",
            font=ctk.CTkFont(size=9),
            text_color="gray"
        )
        self.timestamp_label.pack(side="left", padx=10)
    
    def refresh_device_list(self):
        """刷新設備列表"""
        try:
            cameras = self.controller.detect_cameras()
            self.devices = cameras
            
            # 清空列表
            self.device_listbox.delete("1.0", "end")
            
            if cameras:
                for i, camera in enumerate(cameras):
                    status = "✅ 目標型號" if camera.get('is_target', False) else "⚠️ 其他型號"
                    device_text = f"相機 {i+1}: {camera['model']} ({status})\n"
                    self.device_listbox.insert("end", device_text)
            else:
                self.device_listbox.insert("end", "未檢測到任何 Basler 相機設備\n")
                
        except Exception as e:
            logging.error(f"刷新設備列表失敗: {str(e)}")
            self.device_listbox.delete("1.0", "end")
            self.device_listbox.insert("end", f"設備檢測失敗: {str(e)}\n")
    
    def connect_device(self):
        """連接設備"""
        try:
            if not self.devices:
                messagebox.showwarning("警告", "沒有檢測到可用設備")
                return
            
            # 連接第一個設備（簡化版本）
            success = self.controller.connect_camera(0)
            if success:
                self.update_connection_ui()
                messagebox.showinfo("成功", "相機連接成功！")
            else:
                messagebox.showerror("錯誤", "相機連接失敗")
                
        except Exception as e:
            logging.error(f"連接設備錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"連接失敗: {str(e)}")
    
    def update_connection_ui(self):
        """更新連接狀態UI"""
        if hasattr(self.controller, 'camera_model') and self.controller.camera_model.is_connected:
            self.connection_status.configure(text="● 已連接", text_color="green")
            self.connect_btn.configure(text="🔗 已連接")
            self.start_btn.configure(state="normal")
        else:
            self.connection_status.configure(text="● 未連接", text_color="red")
            self.connect_btn.configure(text="🔗 連接設備")
            self.start_btn.configure(state="disabled")
    
    def start_capture(self):
        """開始捕獲"""
        try:
            success = self.controller.start_capture()
            if success:
                self.start_btn.configure(text="⏸️ 捕獲中...", state="disabled")
                self.stop_btn.configure(state="normal")
        except Exception as e:
            logging.error(f"開始捕獲錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"開始捕獲失敗: {str(e)}")
    
    def stop_capture(self):
        """停止捕獲"""
        try:
            self.controller.stop_capture()
            self.start_btn.configure(text="▶️ 開始捕獲", state="normal")
            self.stop_btn.configure(state="disabled")
        except Exception as e:
            logging.error(f"停止捕獲錯誤: {str(e)}")
    
    def apply_exposure(self):
        """應用曝光設置"""
        try:
            exposure = self.exposure_var.get()
            success = self.controller.set_exposure_time(exposure)
            if success:
                messagebox.showinfo("成功", f"曝光時間已設置為 {exposure} μs")
            else:
                messagebox.showerror("錯誤", "設置曝光時間失敗")
        except Exception as e:
            logging.error(f"設置曝光錯誤: {str(e)}")
            messagebox.showerror("錯誤", f"設置失敗: {str(e)}")
    
    def toggle_detection(self):
        """切換檢測開關"""
        enabled = self.enable_detection_var.get()
        self.controller.toggle_detection(enabled)
    
    def change_detection_method(self, method):
        """更改檢測方法"""
        self.controller.set_detection_method(method)
    
    def change_mode(self):
        """更改系統模式"""
        mode = self.mode_var.get()
        self.controller.switch_mode(mode)
    
    def change_zoom(self, zoom_str):
        """更改顯示縮放"""
        zoom_percent = int(zoom_str.replace('%', ''))
        # 實現縮放邏輯
        logging.info(f"縮放設置為: {zoom_percent}%")
    
    def reset_count(self):
        """重置計數"""
        # 實現重置邏輯
        self.object_count_var.set("當前計數: 000")
        self.progress_bar.set(0)
    
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
    
    def update_frame(self, frame):
        """更新視頻幀顯示"""
        try:
            with self.frame_lock:
                if frame is None:
                    return
                
                # 調整幀大小以適合顯示
                height, width = frame.shape[:2]
                
                # 計算顯示尺寸（保持比例）
                display_width = 640
                display_height = int(height * display_width / width)
                
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
                    self.object_count_var.set(f"當前計數: {count:03d}")
                    
                    # 更新進度條
                    target = self.target_count_var.get()
                    if target > 0:
                        progress = min(count / target, 1.0)
                        self.progress_bar.set(progress)
                
                # 更新 FPS
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
                    logging.error(f"系統錯誤: {data}")
                    
        except Exception as e:
            logging.error(f"處理控制器事件錯誤: {str(e)}")
    
    def run(self):
        """運行主循環"""
        try:
            logging.info("CustomTkinter 主視圖開始運行")
            
            # 更新時間戳的定時器
            def update_timestamp():
                current_time = time.strftime("%Y-%m-%d %H:%M:%S")
                self.timestamp_label.configure(text=current_time)
                self.root.after(1000, update_timestamp)
            
            update_timestamp()
            
            self.root.mainloop()
            
        except Exception as e:
            logging.error(f"主循環運行錯誤: {str(e)}")
            raise
        finally:
            logging.info("CustomTkinter 主視圖已停止")