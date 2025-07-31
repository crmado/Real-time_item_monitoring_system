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
        
        # 批次計數面板（在狀態面板上方）
        self.create_count_display_panel(main_frame)
        
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
        """創建視頻面板 - 重新設計佈局"""
        # 視頻顯示區域（占用最大空間）
        video_frame = ttk.LabelFrame(parent, text="📺 實時檢測畫面 (640x480)", padding=5)
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 視頻顯示標籤
        self.video_label = ttk.Label(video_frame, text="正在初始化相機...", 
                                    anchor=tk.CENTER, font=('Arial', 12),
                                    background='#1a1a1a', foreground='#00ff00',
                                    relief=tk.SUNKEN, borderwidth=2)
        self.video_label.pack(expand=True, fill=tk.BOTH)
    
    def create_count_display_panel(self, parent):
        """創建工業批次計數面板 - 緊湊設計"""
        count_frame = ttk.LabelFrame(parent, text="🏭 批次計數系統", padding=5)
        count_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 主計數容器（緊湊設計）
        main_count_container = tk.Frame(count_frame, bg='#2c3e50', relief=tk.RAISED, bd=2)
        main_count_container.pack(fill=tk.X, pady=2)
        
        # 左側：當前批次計數
        left_container = tk.Frame(main_count_container, bg='#2c3e50')
        left_container.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)
        
        # 當前批次標題
        batch_title = tk.Label(left_container, text="本批計數", 
                             font=('Arial', 12, 'bold'),
                             fg='#ffffff', bg='#2c3e50')
        batch_title.pack()
        
        # 數字顯示（緊湊版）
        self.batch_count_var = tk.StringVar(value="000")
        try:
            digital_font = ('Consolas', 32, 'bold')  # 較小字體
            batch_count_label = tk.Label(left_container, 
                                       textvariable=self.batch_count_var,
                                       font=digital_font,
                                       fg='#00ff41', bg='#2c3e50',
                                       width=4, height=1)
        except:
            digital_font = ('Courier New', 32, 'bold')
            batch_count_label = tk.Label(left_container, 
                                       textvariable=self.batch_count_var,
                                       font=digital_font,
                                       fg='#00ff41', bg='#2c3e50',
                                       width=4, height=1)
        batch_count_label.pack()
        
        # 批次進度條
        self.create_batch_progress(left_container)
        
        # 中間：批次設定
        middle_container = tk.Frame(main_count_container, bg='#2c3e50')
        middle_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.create_batch_settings(middle_container)
        
        # 右側：狀態指示器
        right_container = tk.Frame(main_count_container, bg='#2c3e50')
        right_container.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=5)
        
        # 批次狀態指示燈（緊湊版）
        self.batch_status_indicator = tk.Label(right_container, text="●", 
                                             font=('Arial', 24, 'bold'),
                                             fg='#ff4444', bg='#2c3e50')
        self.batch_status_indicator.pack(pady=(2, 2))
        
        # 狀態文字
        self.batch_status_text = tk.Label(right_container, text="等待開始",
                                        font=('Arial', 14, 'bold'),
                                        fg='#ffffff', bg='#2c3e50')
        self.batch_status_text.pack()
        
        # 批次控制按鈕
        self.create_batch_controls(right_container)
        
        # 底部：統計信息
        self.create_batch_statistics(count_frame)
    
    def create_batch_progress(self, parent):
        """創建批次進度條"""
        # 進度條容器
        progress_frame = tk.Frame(parent, bg='#2c3e50')
        progress_frame.pack(fill=tk.X, pady=(10, 5))
        
        # 進度條
        from tkinter import ttk
        self.batch_progress = ttk.Progressbar(progress_frame, 
                                            length=120, 
                                            mode='determinate',
                                            maximum=100,
                                            value=0)
        self.batch_progress.pack()
        
        # 進度文字
        self.progress_text = tk.Label(progress_frame, text="0 / 100", 
                                    font=('Arial', 10),
                                    fg='#cccccc', bg='#2c3e50')
        self.progress_text.pack(pady=(2, 0))
    
    def create_batch_settings(self, parent):
        """創建批次設定區域"""
        # 設定標題
        settings_title = tk.Label(parent, text="批次設定", 
                                font=('Arial', 12, 'bold'),
                                fg='#ffffff', bg='#2c3e50')
        settings_title.pack(anchor=tk.W)
        
        # 目標數量設定
        target_frame = tk.Frame(parent, bg='#2c3e50')
        target_frame.pack(fill=tk.X, pady=(5, 2))
        
        tk.Label(target_frame, text="目標數量:", 
               font=('Arial', 10),
               fg='#cccccc', bg='#2c3e50').pack(side=tk.LEFT)
        
        self.target_count_var = tk.IntVar(value=100)
        target_spinbox = ttk.Spinbox(target_frame, 
                                   from_=1, to=1000, 
                                   textvariable=self.target_count_var,
                                   width=6,
                                   command=self.on_target_changed)
        target_spinbox.pack(side=tk.RIGHT)
        
        # 當前批次號
        batch_num_frame = tk.Frame(parent, bg='#2c3e50')
        batch_num_frame.pack(fill=tk.X, pady=2)
        
        tk.Label(batch_num_frame, text="批次號:", 
               font=('Arial', 10),
               fg='#cccccc', bg='#2c3e50').pack(side=tk.LEFT)
        
        self.batch_number_var = tk.StringVar(value="001")
        tk.Label(batch_num_frame, textvariable=self.batch_number_var,
               font=('Arial', 10, 'bold'),
               fg='#00ff41', bg='#2c3e50').pack(side=tk.RIGHT)
        
        # 自動模式開關
        auto_frame = tk.Frame(parent, bg='#2c3e50')
        auto_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.auto_mode_var = tk.BooleanVar(value=True)
        auto_check = ttk.Checkbutton(auto_frame, 
                                   text="自動模式",
                                   variable=self.auto_mode_var)
        auto_check.pack(side=tk.LEFT)
    
    def create_batch_controls(self, parent):
        """創建批次控制按鈕"""
        # 添加標題
        controls_title = tk.Label(parent, text="控制操作", 
                                font=('Arial', 10, 'bold'),
                                fg='#ffffff', bg='#2c3e50')
        controls_title.pack(pady=(5, 2))
        
        # 開始批次按鈕
        self.start_batch_btn = tk.Button(parent, 
                                       text="▶ 開始",
                                       font=('Arial', 9, 'bold'),
                                       bg='#27ae60', fg='white',
                                       activebackground='#2ecc71',
                                       command=self.start_batch,
                                       width=8, height=1,
                                       relief=tk.RAISED, bd=2)
        self.start_batch_btn.pack(pady=1)
        
        # 停止批次按鈕
        self.stop_batch_btn = tk.Button(parent, 
                                      text="⏹ 停止",
                                      font=('Arial', 9, 'bold'),
                                      bg='#e74c3c', fg='white',
                                      activebackground='#c0392b',
                                      command=self.stop_batch,
                                      width=8, height=1,
                                      state='disabled',
                                      relief=tk.RAISED, bd=2)
        self.stop_batch_btn.pack(pady=1)
        
        # 重置批次按鈕
        self.reset_batch_btn = tk.Button(parent, 
                                       text="🔄 重置",
                                       font=('Arial', 9, 'bold'),
                                       bg='#f39c12', fg='white',
                                       activebackground='#e67e22',
                                       command=self.reset_batch,
                                       width=8, height=1,
                                       relief=tk.RAISED, bd=2)
        self.reset_batch_btn.pack(pady=1)
    
    def create_batch_statistics(self, parent):
        """創建批次統計區域 - 緊湊版"""
        stats_frame = tk.Frame(parent, bg='#34495e')
        stats_frame.pack(fill=tk.X, pady=(2, 0))
        
        # 今日批次統計（簡化版）
        self.create_stat_widget(stats_frame, "今日批次", "0", "#3498db")
        self.create_stat_widget(stats_frame, "總計", "0", "#e74c3c")
        self.create_stat_widget(stats_frame, "速度", "0/分", "#2ecc71")
        
        # 初始化批次狀態
        self.batch_mode = 'idle'  # idle, running, paused, completed
        self.current_batch_count = 0
        self.total_batches_today = 0
        self.total_items_today = 0
        self.batch_start_time = None
        
        # 添加使用說明
        help_frame = tk.Frame(parent, bg='#f8f9fa')
        help_frame.pack(fill=tk.X, pady=(2, 0))
        
        help_text = tk.Label(help_frame, 
                           text="💡 使用說明：點擊「開始批次」按鈕啟動計數，達到目標數量將自動停止", 
                           font=('Arial', 10),
                           fg='#6c757d', bg='#f8f9fa',
                           padx=10, pady=3)
        help_text.pack(anchor=tk.W)
        
    # ==================== 批次控制方法 ====================
    
    def start_batch(self):
        """開始新批次"""
        try:
            if self.batch_mode == 'idle':
                self.batch_mode = 'running'
                self.current_batch_count = 0
                self.batch_start_time = time.time()
                
                # 更新UI狀態
                self.batch_status_indicator.config(fg='#00ff41')  # 綠色
                self.batch_status_text.config(text="計數中")
                
                # 按鈕狀態
                self.start_batch_btn.config(state='disabled')
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
            if self.batch_mode == 'running':
                self.batch_mode = 'idle'
                
                # 更新UI狀態
                self.batch_status_indicator.config(fg='#ffaa00')  # 橙色
                self.batch_status_text.config(text="已停止")
                
                # 按鈕狀態
                self.start_batch_btn.config(state='normal')
                self.stop_batch_btn.config(state='disabled')
                
                # 通知控制器停止檢測
                if hasattr(self.controller, 'stop_batch_detection'):
                    self.controller.stop_batch_detection()
                    
                logging.info(f"⏹️ 手動停止批次，當前計數: {self.current_batch_count}")
                
        except Exception as e:
            logging.error(f"停止批次錯誤: {str(e)}")
    
    def reset_batch(self):
        """重置批次計數"""
        try:
            # 先停止如果正在運行
            if self.batch_mode == 'running':
                self.stop_batch()
            
            # 重置計數
            self.current_batch_count = 0
            self.batch_count_var.set("000")
            
            # 重置進度條
            self.batch_progress.config(value=0)
            self.progress_text.config(text=f"0 / {self.target_count_var.get()}")
            
            # 更新狀態
            self.batch_status_indicator.config(fg='#ff4444')  # 紅色
            self.batch_status_text.config(text="等待開始")
            
            logging.info("🔄 批次已重置")
            
        except Exception as e:
            logging.error(f"重置批次錯誤: {str(e)}")
    
    def on_target_changed(self):
        """目標數量改變回調"""
        try:
            target = self.target_count_var.get()
            self.progress_text.config(text=f"{self.current_batch_count} / {target}")
            
            # 更新進度條最大值
            if hasattr(self, 'batch_progress'):
                progress_percentage = (self.current_batch_count / target * 100) if target > 0 else 0
                self.batch_progress.config(value=progress_percentage)
                
            logging.info(f"目標數量已更改為: {target}")
            
        except Exception as e:
            logging.error(f"更改目標數量錯誤: {str(e)}")
    
    def complete_batch(self):
        """完成當前批次"""
        try:
            if self.batch_mode == 'running':
                self.batch_mode = 'completed'
                
                # 更新統計
                self.total_batches_today += 1
                self.total_items_today += self.current_batch_count
                
                # 更新批次號
                current_num = int(self.batch_number_var.get())
                self.batch_number_var.set(f"{current_num + 1:03d}")
                
                # 更新UI狀態
                self.batch_status_indicator.config(fg='#3498db')  # 藍色
                self.batch_status_text.config(text="已完成")
                
                # 按鈕狀態
                self.start_batch_btn.config(state='normal')
                self.stop_batch_btn.config(state='disabled')
                
                # 更新統計顯示
                self.update_batch_statistics()
                
                # 計算批次時間
                if self.batch_start_time:
                    batch_time = time.time() - self.batch_start_time
                    rate = self.current_batch_count / (batch_time / 60) if batch_time > 0 else 0
                    logging.info(f"🎉 批次完成！數量: {self.current_batch_count}, 用時: {batch_time:.1f}秒, 速度: {rate:.1f}/分鐘")
                
                # 自動模式下準備下一批次
                if self.auto_mode_var.get():
                    self.root.after(2000, self._auto_start_next_batch)  # 2秒後自動開始下一批次
                    
        except Exception as e:
            logging.error(f"完成批次錯誤: {str(e)}")
    
    def _auto_start_next_batch(self):
        """自動開始下一批次"""
        try:
            if self.batch_mode == 'completed' and self.auto_mode_var.get():
                self.reset_batch()
                self.root.after(500, self.start_batch)  # 延遲500ms開始
                
        except Exception as e:
            logging.error(f"自動開始下一批次錯誤: {str(e)}")
    
    def update_batch_statistics(self):
        """更新批次統計顯示"""
        try:
            if hasattr(self, 'stat_vars'):
                self.stat_vars.get('今日批次', tk.StringVar()).set(f"{self.total_batches_today}")
                self.stat_vars.get('總計數量', tk.StringVar()).set(f"{self.total_items_today}")
                
                # 計算平均速度
                if self.total_batches_today > 0 and self.batch_start_time:
                    total_time = time.time() - self.batch_start_time
                    avg_rate = self.total_items_today / (total_time / 60) if total_time > 0 else 0
                    self.stat_vars.get('平均速度', tk.StringVar()).set(f"{avg_rate:.0f}/分鐘")
                    
        except Exception as e:
            logging.error(f"更新批次統計錯誤: {str(e)}")
        
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
            # 檢查批次組件是否存在
            if hasattr(self, 'batch_status_indicator') and self.batch_status_indicator:
                self.batch_status_indicator.config(fg='#ff4444')  # 紅色表示等待
                
            if hasattr(self, 'batch_status_text') and self.batch_status_text:
                self.batch_status_text.config(text="等待開始")
            
            # 初始化統計數據
            self._daily_total = 0
            
            # 設置初始檢測品質
            if hasattr(self, 'quality_var') and self.quality_var:
                self.quality_var.set("待檢測")
            
            logging.info("✅ 批次計數系統初始化完成")
            
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