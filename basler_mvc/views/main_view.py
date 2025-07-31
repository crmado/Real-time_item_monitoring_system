"""
主視圖 - MVC 架構核心
精簡的用戶界面，專注於 Basler 相機和檢測功能
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


class MainView:
    """主視圖 - 精簡高性能版本"""
    
    def __init__(self, controller):
        """初始化主視圖"""
        self.controller = controller
        self.root = tk.Tk()
        
        # 視窗設置
        self.root.title("🚀 Basler acA640-300gm 精簡高性能系統")
        self.root.geometry("1100x800")
        self.root.resizable(True, True)
        
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
        
        # 創建UI
        self.create_ui()
        
        # 註冊為控制器觀察者
        self.controller.add_view_observer(self.on_controller_event)
        
        logging.info("主視圖初始化完成")
    
    def create_ui(self):
        """創建用戶界面"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 頂部控制面板
        self.create_control_panel(main_frame)
        
        # 中間視頻和檢測面板
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.create_video_panel(middle_frame)
        self.create_detection_panel(middle_frame)
        
        # 底部狀態面板
        self.create_status_panel(main_frame)
        
        # 初始化顯示狀態
        self.root.after(100, self.initialize_display_status)  # 延遲初始化確保所有組件已創建
    
    def create_control_panel(self, parent):
        """創建控制面板"""
        control_frame = ttk.LabelFrame(parent, text="🎮 系統控制", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 按鈕行
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        # 主要控制按鈕（簡化流程）
        ttk.Button(button_frame, text="🚀 一鍵啟動", 
                  command=self.auto_start_system, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="⏹️ 停止系統", 
                  command=self.stop_system, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🔄 重啟系統", 
                  command=self.restart_system, width=12).pack(side=tk.LEFT, padx=2)
        
        # 分隔線
        ttk.Separator(button_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 進階控制按鈕（保留手動控制）
        ttk.Button(button_frame, text="🔍 檢測相機", 
                  command=self.detect_cameras, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="🔗 連接相機", 
                  command=self.connect_camera, width=12).pack(side=tk.LEFT, padx=2)
        
        # 分隔線
        ttk.Separator(button_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 檢測控制
        ttk.Button(button_frame, text="📊 性能報告", 
                  command=self.show_performance_report, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="⚙️ 設置參數", 
                  command=self.open_parameter_dialog, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="❓ 關於", 
                  command=self.show_about, width=12).pack(side=tk.RIGHT, padx=2)
    
    def create_video_panel(self, parent):
        """創建視頻面板"""
        # 主視頻容器
        main_video_frame = ttk.Frame(parent)
        main_video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 視頻顯示區域
        video_frame = ttk.LabelFrame(main_video_frame, text="📺 實時檢測畫面 (640x480)", padding=5)
        video_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # 視頻顯示標籤
        self.video_label = ttk.Label(video_frame, text="正在初始化相機...", 
                                    anchor=tk.CENTER, font=('Arial', 12),
                                    background='#1a1a1a', foreground='#00ff00',
                                    relief=tk.SUNKEN, borderwidth=2)
        self.video_label.pack(expand=True, fill=tk.BOTH)
        
        # 大型計數顯示面板
        self.create_count_display_panel(main_video_frame)
    
    def create_count_display_panel(self, parent):
        """創建大型計數顯示面板"""
        count_frame = ttk.LabelFrame(parent, text="📊 檢測計數", padding=10)
        count_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 主計數容器
        main_count_container = tk.Frame(count_frame, bg='#2c3e50', relief=tk.RAISED, bd=3)
        main_count_container.pack(fill=tk.X, pady=5)
        
        # 大型數字顯示
        self.large_count_var = tk.StringVar(value="0000")
        # 使用系統兼容的等寬字體
        try:
            digital_font = ('Consolas', 48, 'bold')  # Windows
            large_count_label = tk.Label(main_count_container, 
                                       textvariable=self.large_count_var,
                                       font=digital_font,
                                       fg='#00ff41', bg='#2c3e50',
                                       width=8, height=2)
        except:
            # 備用字體
            digital_font = ('Courier New', 48, 'bold')
            large_count_label = tk.Label(main_count_container, 
                                       textvariable=self.large_count_var,
                                       font=digital_font,
                                       fg='#00ff41', bg='#2c3e50',
                                       width=8, height=2)
        large_count_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        # 狀態指示器區域
        status_container = tk.Frame(main_count_container, bg='#2c3e50')
        status_container.pack(side=tk.RIGHT, fill=tk.Y, padx=20)
        
        # 檢測狀態指示燈
        self.status_indicator = tk.Label(status_container, text="●", 
                                       font=('Arial', 24, 'bold'),
                                       fg='#ff4444', bg='#2c3e50')
        self.status_indicator.pack(pady=(10, 5))
        
        # 狀態文字
        self.status_text = tk.Label(status_container, text="離線",
                                  font=('Arial', 12, 'bold'),
                                  fg='#ffffff', bg='#2c3e50')
        self.status_text.pack()
        
        # 檢測速率顯示
        self.rate_text = tk.Label(status_container, text="0 物件/秒",
                                font=('Arial', 10),
                                fg='#cccccc', bg='#2c3e50')
        self.rate_text.pack(pady=(5, 0))
        
        # 統計信息容器
        stats_container = tk.Frame(count_frame, bg='#34495e')
        stats_container.pack(fill=tk.X, pady=(5, 0))
        
        # 今日統計
        self.create_stat_widget(stats_container, "今日總計", "0", "#3498db")
        self.create_stat_widget(stats_container, "平均大小", "0 px²", "#e74c3c")
        self.create_stat_widget(stats_container, "檢測精度", "100%", "#2ecc71")
    
    def create_stat_widget(self, parent, title, value, color):
        """創建統計小組件"""
        stat_frame = tk.Frame(parent, bg='#34495e')
        stat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # 標題
        title_label = tk.Label(stat_frame, text=title, 
                             font=('Arial', 9), 
                             fg='#bdc3c7', bg='#34495e')
        title_label.pack()
        
        # 數值
        value_var = tk.StringVar(value=value)
        value_label = tk.Label(stat_frame, textvariable=value_var,
                             font=('Arial', 14, 'bold'),
                             fg=color, bg='#34495e')
        value_label.pack()
        
        # 保存變量引用以便後續更新
        if not hasattr(self, 'stat_vars'):
            self.stat_vars = {}
        self.stat_vars[title] = value_var
    
    def initialize_display_status(self):
        """初始化顯示狀態"""
        try:
            # 檢查組件是否存在
            if hasattr(self, 'status_indicator') and self.status_indicator:
                self.status_indicator.config(fg='#ff4444')  # 紅色表示離線
                
            if hasattr(self, 'status_text') and self.status_text:
                self.status_text.config(text="系統啟動中")
                
            if hasattr(self, 'rate_text') and self.rate_text:
                self.rate_text.config(text="0 物件/秒")
            
            # 初始化統計數據
            self._daily_total = 0
            
            # 設置初始檢測品質
            if hasattr(self, 'quality_var') and self.quality_var:
                self.quality_var.set("待檢測")
            
            logging.info("✅ 大型計數顯示面板初始化完成")
            
        except Exception as e:
            logging.debug(f"初始化顯示狀態錯誤: {str(e)}")
    
    def create_detection_panel(self, parent):
        """創建檢測面板"""
        detection_frame = ttk.LabelFrame(parent, text="🔍 檢測設置", padding=10)
        detection_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # 檢測方法選擇
        method_frame = ttk.Frame(detection_frame)
        method_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(method_frame, text="檢測方法:").pack(anchor=tk.W)
        method_combo = ttk.Combobox(method_frame, textvariable=self.method_var, 
                                   values=['circle', 'contour'], state='readonly', width=15)
        method_combo.pack(fill=tk.X, pady=(2, 0))
        method_combo.bind('<<ComboboxSelected>>', self.on_method_changed)
        
        # 檢測開關
        ttk.Separator(detection_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        self.detection_enabled = tk.BooleanVar(value=True)
        detection_check = ttk.Checkbutton(detection_frame, text="啟用檢測", 
                                         variable=self.detection_enabled,
                                         command=self.on_detection_toggle)
        detection_check.pack(anchor=tk.W)
        
        # 相機參數
        ttk.Separator(detection_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(detection_frame, text="相機參數:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        # 曝光時間調整
        exposure_frame = ttk.Frame(detection_frame)
        exposure_frame.pack(fill=tk.X, pady=2)
        ttk.Label(exposure_frame, text="曝光時間:", width=8).pack(side=tk.LEFT)
        self.exposure_var = tk.DoubleVar(value=1000.0)  # 默認1ms
        exposure_spin = ttk.Spinbox(exposure_frame, from_=200, to=10000, 
                                   textvariable=self.exposure_var, width=8,
                                   increment=100,
                                   command=self.on_exposure_changed)
        exposure_spin.pack(side=tk.RIGHT)
        ttk.Label(exposure_frame, text="μs", width=3).pack(side=tk.RIGHT)
        
        # 快速參數
        ttk.Separator(detection_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(detection_frame, text="檢測參數:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        # 最小面積
        min_area_frame = ttk.Frame(detection_frame)
        min_area_frame.pack(fill=tk.X, pady=2)
        ttk.Label(min_area_frame, text="最小面積:", width=8).pack(side=tk.LEFT)
        self.min_area_var = tk.IntVar(value=100)
        min_area_spin = ttk.Spinbox(min_area_frame, from_=10, to=2000, 
                                   textvariable=self.min_area_var, width=8,
                                   command=self.on_parameter_changed)
        min_area_spin.pack(side=tk.RIGHT)
        
        # 最大面積
        max_area_frame = ttk.Frame(detection_frame)
        max_area_frame.pack(fill=tk.X, pady=2)
        ttk.Label(max_area_frame, text="最大面積:", width=8).pack(side=tk.LEFT)
        self.max_area_var = tk.IntVar(value=5000)
        max_area_spin = ttk.Spinbox(max_area_frame, from_=100, to=20000, 
                                   textvariable=self.max_area_var, width=8,
                                   command=self.on_parameter_changed)
        max_area_spin.pack(side=tk.RIGHT)
        
        # 檢測結果顯示（簡化版 - 主要顯示在大型面板）
        ttk.Separator(detection_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(detection_frame, text="檢測狀態:", font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        # 簡潔的狀態顯示
        status_info_frame = ttk.Frame(detection_frame)
        status_info_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_info_frame, text="當前物件:", width=8).pack(side=tk.LEFT)
        ttk.Label(status_info_frame, textvariable=self.object_count_var, 
                 font=('Arial', 10, 'bold'), foreground='#2ecc71').pack(side=tk.RIGHT)
        
        # 檢測品質指示器
        quality_frame = ttk.Frame(detection_frame)
        quality_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(quality_frame, text="檢測品質:", width=8).pack(side=tk.LEFT)
        self.quality_var = tk.StringVar(value="優秀")
        ttk.Label(quality_frame, textvariable=self.quality_var, 
                 font=('Arial', 10, 'bold'), foreground='#3498db').pack(side=tk.RIGHT)
    
    def create_status_panel(self, parent):
        """創建狀態面板"""
        status_frame = ttk.LabelFrame(parent, text="📊 系統狀態", padding=5)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 狀態行1：系統狀態
        status_row1 = ttk.Frame(status_frame)
        status_row1.pack(fill=tk.X)
        
        ttk.Label(status_row1, textvariable=self.status_var, 
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(status_row1, textvariable=self.camera_info_var, 
                 font=('Arial', 9)).pack(side=tk.RIGHT)
        
        # 狀態行2：性能統計
        status_row2 = ttk.Frame(status_frame)
        status_row2.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(status_row2, textvariable=self.camera_fps_var, 
                 font=('Arial', 9), foreground='green').pack(side=tk.LEFT)
        ttk.Label(status_row2, textvariable=self.processing_fps_var, 
                 font=('Arial', 9), foreground='blue').pack(side=tk.LEFT, padx=(20, 0))
        ttk.Label(status_row2, textvariable=self.detection_fps_var, 
                 font=('Arial', 9), foreground='purple').pack(side=tk.LEFT, padx=(20, 0))
    
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
        """處理幀更新"""
        try:
            frame = data.get('frame')
            if frame is not None:
                with self.frame_lock:
                    self.current_frame = frame
                    
                # 立即更新視頻顯示
                self.root.after(0, self._update_video_display)
                
                # 第一幀時的特殊日誌
                if hasattr(self, '_first_frame_logged') == False:
                    self._first_frame_logged = True
                    logging.info(f"視圖收到第一幀，尺寸: {frame.shape}")
            
            # 更新檢測結果和大型顯示面板
            count = data.get('object_count', 0)
            self.object_count_var.set(f"物件: {count}")
            
            # 安全地更新大型計數顯示
            try:
                self._update_large_count_display(count, data)
                self._update_detection_quality(data)
            except Exception as e:
                logging.debug(f"更新大型顯示面板錯誤: {str(e)}")
            
        except Exception as e:
            logging.error(f"處理幀更新錯誤: {str(e)}")
    
    def _update_large_count_display(self, count, data):
        """更新大型計數顯示"""
        try:
            # 更新主計數顯示
            self.large_count_var.set(f"{count:04d}")
            
            # 更新狀態指示器
            if count > 0:
                self.status_indicator.config(fg='#00ff41')  # 綠色
                self.status_text.config(text="檢測中")
            else:
                self.status_indicator.config(fg='#ffaa00')  # 橙色
                self.status_text.config(text="待檢測")
            
            # 計算檢測速率（物件/秒）
            detection_fps = data.get('detection_fps', 0)
            if detection_fps > 0:
                rate = min(count * detection_fps / 60, count)  # 粗略估算
                self.rate_text.config(text=f"{rate:.1f} 物件/秒")
            else:
                self.rate_text.config(text="0 物件/秒")
                
            # 更新統計信息
            if hasattr(self, 'stat_vars'):
                # 更新今日總計（這裡簡化處理）
                if hasattr(self, '_daily_total'):
                    self._daily_total += count
                else:
                    self._daily_total = count
                
                self.stat_vars.get('今日總計', tk.StringVar()).set(f"{self._daily_total}")
                
                # 更新平均大小（如果有物件數據）
                objects = data.get('objects', [])
                if objects:
                    avg_area = sum(obj[5] if len(obj) > 5 else 0 for obj in objects) / len(objects)
                    self.stat_vars.get('平均大小', tk.StringVar()).set(f"{avg_area:.0f} px²")
                
                # 檢測精度（基於FPS表現）
                processing_fps = data.get('processing_fps', 0)
                if processing_fps > 150:
                    accuracy = "優秀"
                elif processing_fps > 100:
                    accuracy = "良好"
                else:
                    accuracy = "一般"
                self.stat_vars.get('檢測精度', tk.StringVar()).set(accuracy)
                
        except Exception as e:
            logging.error(f"更新大型計數顯示錯誤: {str(e)}")
    
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
        self.controller.auto_start_camera_system()
    
    def start_system(self):
        """啟動系統"""
        self.controller.start_system()
    
    def stop_system(self):
        """停止系統"""
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