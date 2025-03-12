"""
主視窗
整合所有UI組件
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
import datetime
import os

import cv2
import numpy as np
from PIL import Image, ImageTk

from .components.control_panel import ControlPanel
from .components.video_panel import VideoPanel
from .components.settings_panel import SettingsPanel
from .components.setting.settings_dialog import SettingsDialog
from utils.language import get_text
from views.components.photo_panel import PhotoPanel
from views.components.analysis_panel import AnalysisPanel
from utils.ui_style_manager import UIStyleManager


class MainWindow:
    """
    /// 主視窗類別
    /// 功能結構：
    /// 第一部分：基本屬性和初始化
    /// 第二部分：UI元件創建
    /// 第三部分：事件處理
    /// 第四部分：設定與語言管理
    /// 第五部分：日誌與工具方法
    """

    #==========================================================================
    # 第一部分：基本屬性和初始化
    #==========================================================================
    def __init__(self, root, config_manager):
        """
        初始化主視窗

        Args:
            root: Tkinter root 物件
            config_manager: 配置管理器實例
        """
        self.settings_panel = None
        self.video_panel = None
        self.photo_panel = None
        self.control_panel = None
        self.main_frame = None
        self.analysis_panel = None
        self.root = root
        self.config_manager = config_manager
        self.root.title(get_text("app_title", "物件監測系統"))

        # 初始化UI樣式管理器
        theme_name = self.config_manager.get('ui.theme', 'light')
        self.ui_style_manager = UIStyleManager(root, theme_name)

        # 載入設定
        self.load_config()

        # 當前模式（監測模式或拍照模式）
        self.current_mode = "monitoring"    # 可選值: "monitoring" 或 "photo"

        # 設定視窗基本屬性
        self.setup_window()

        # 創建UI元件
        self.create_components()

        # 設置布局
        self.setup_layout()

        # 註冊回調函數
        self.register_callbacks()

        # 啟動時間更新
        self.start_time_update()

    def setup_window(self):
        """設定視窗基本屬性"""
        self.root.minsize(1024, 768)  # 增加最小視窗大小，確保所有元素可見
        self.root.geometry("1200x800")  # 設定預設視窗大小
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

    def load_config(self):
        """載入配置"""
        # 從配置檔載入設定
        # 配置會在創建UI元件時使用
        pass

    #==========================================================================
    # 第二部分：UI元件創建
    #==========================================================================
    def create_components(self):
        """創建所有UI組件"""
        # 主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky=f"{tk.N}{tk.S}{tk.E}{tk.W}")
        
        # 頂部區域（標題和控制面板）
        self.create_header_area()
        
        # 內容區域（視訊/拍照面板和設定/分析面板）
        self.create_content_area()
        
        # 底部區域（日誌和狀態欄）
        self.create_footer_area()

    def create_header_area(self):
        """創建頂部區域，包含標題和控制面板"""
        # 頂部框架
        self.header_frame = ttk.Frame(self.main_frame, style='Header.TFrame')
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky=f"{tk.W}{tk.E}")
        
        # 應用標題
        app_title = ttk.Label(
            self.header_frame,
            text=get_text("app_title", "物件監測系統"),
            style='Title.TLabel'
        )
        app_title.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 控制面板
        self.control_panel = ControlPanel(self.header_frame)
        self.control_panel.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)
        
        # 設定按鈕
        self.load_icons()
        self.settings_button = ttk.Button(
            self.header_frame,
            image=self.settings_icon if self.settings_icon else None,
            text="" if self.settings_icon else "⚙",  # 如果沒有圖標，使用文字符號
            width=3 if not self.settings_icon else None,
            command=self.open_settings_dialog,
            style='Icon.TButton'
        )
        self.settings_button.pack(side=tk.RIGHT, padx=10, pady=5)

    def create_content_area(self):
        """創建內容區域，包含視訊/拍照面板和設定/分析面板"""
        # 視訊面板（初始顯示）
        self.video_panel = VideoPanel(self.main_frame)
        self.video_panel.grid(row=1, column=0, padx=(10, 5), pady=10, sticky=f"{tk.N}{tk.S}{tk.E}{tk.W}")
        self.video_panel.configure(style='Video.TFrame')
        
        # 拍照面板（初始隱藏）
        self.photo_panel = PhotoPanel(self.main_frame)
        self.photo_panel.grid(row=1, column=0, padx=(10, 5), pady=10, sticky=f"{tk.N}{tk.S}{tk.E}{tk.W}")
        self.photo_panel.configure(style='Video.TFrame')
        self.photo_panel.grid_remove()  # 隱藏拍照面板
        
        # 設定面板（初始顯示）
        self.settings_panel = SettingsPanel(self.main_frame, self.config_manager)
        self.settings_panel.grid(row=1, column=1, padx=(5, 10), pady=10, sticky=f"{tk.N}{tk.S}{tk.E}{tk.W}")
        self.settings_panel.configure(style='Settings.TFrame')
        
        # 分析面板（初始隱藏）
        self.analysis_panel = AnalysisPanel(self.main_frame)
        self.analysis_panel.grid(row=1, column=1, padx=(5, 10), pady=10, sticky=f"{tk.N}{tk.S}{tk.E}{tk.W}")
        self.analysis_panel.configure(style='Settings.TFrame')
        self.analysis_panel.grid_remove()  # 隱藏分析面板

    def create_footer_area(self):
        """創建底部區域，包含日誌和狀態欄"""
        # 底部框架
        self.footer_frame = ttk.Frame(self.main_frame, style='Footer.TFrame')
        self.footer_frame.grid(row=2, column=0, columnspan=2, sticky=f"{tk.W}{tk.E}{tk.S}")
        
        # 日誌區域
        self.create_log_area()
        
        # 狀態欄
        self.create_status_bar()

    def create_log_area(self):
        """創建日誌顯示區域"""
        log_frame = ttk.Frame(self.footer_frame, style='Log.TFrame')
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 日誌標題
        ttk.Label(
            log_frame, 
            text=get_text("system_log", "系統日誌："),
            style='Title.TLabel'
        ).pack(side=tk.TOP, anchor=tk.W, padx=5, pady=2)
        
        # 日誌文本區域
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=70,
            height=8,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_status_bar(self):
        """創建狀態欄"""
        status_frame = ttk.Frame(self.footer_frame, style='Footer.TFrame')
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 左側顯示時間
        time_frame = ttk.Frame(status_frame, style='Footer.TFrame')
        time_frame.pack(side=tk.LEFT)
        
        ttk.Label(
            time_frame, 
            text=get_text("current_time", "目前時間："),
            style='TLabel'
        ).pack(side=tk.LEFT)
        
        self.time_label = ttk.Label(time_frame, text="", style='TLabel')
        self.time_label.pack(side=tk.LEFT, padx=5)
        
        # 右側顯示版本信息
        version_label = ttk.Label(
            status_frame, 
            text="v1.0.0",
            style='TLabel'
        )
        version_label.pack(side=tk.RIGHT, padx=10)

    def load_icons(self):
        """載入圖標"""
        try:
            # 創建icons目錄（如果不存在）
            icons_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "icons"
            )
            if not os.path.exists(icons_dir):
                os.makedirs(icons_dir)

            # 設定圖標路徑
            settings_icon_path = os.path.join(icons_dir, "settings.png")

            # 檢查圖標是否存在，不存在則創建預設圖標
            if not os.path.exists(settings_icon_path):
                # 如果需要，可以在這裡添加代碼動態創建圖標
                # 暫時使用文字代替
                self.settings_icon = None
            else:
                # 載入並調整圖標大小
                icon = Image.open(settings_icon_path)
                icon = icon.resize((24, 24), Image.Resampling.LANCZOS)
                self.settings_icon = ImageTk.PhotoImage(icon)

        except Exception as e:
            logging.error(f"載入圖標時發生錯誤：{str(e)}")
            self.settings_icon = None

    def setup_layout(self):
        """設置組件布局"""
        # 設定行列的權重
        self.main_frame.grid_rowconfigure(1, weight=1)  # 內容區域可擴展
        self.main_frame.grid_columnconfigure(0, weight=3)  # 視訊/拍照面板佔較多空間
        self.main_frame.grid_columnconfigure(1, weight=1)  # 設定/分析面板佔較少空間

    #==========================================================================
    # 第三部分：事件處理
    #==========================================================================
    def register_callbacks(self):
        """註冊回調函數"""
        # 註冊語言變更回調
        self.settings_panel.set_callback('settings_applied', self.on_settings_applied)

    def open_settings_dialog(self):
        """開啟設定對話框"""
        dialog = SettingsDialog(self.root, self.config_manager)
        self.root.wait_window(dialog)

        # 如果設定已保存，應用新設定
        if dialog.result:
            self.apply_settings()

    def apply_settings(self):
        """應用最新設定"""
        # 更新語言
        language_code = self.config_manager.get('system.language', 'zh_TW')
        self.on_language_changed(language_code)

        # 更新主題
        theme = self.config_manager.get('ui.theme', 'light')
        self.ui_style_manager.set_theme(theme)

        if hasattr(self, 'system_controller') and self.system_controller is not None:
            self.system_controller.handle_theme_change(theme)

        # 更新其他設定
        self.log_message(get_text("settings_updated", "設定已更新"))

    def set_system_controller(self, controller):
        """設定系統控制器引用"""
        self.system_controller = controller

    def on_settings_applied(self):
        """設定應用回調"""
        # 從設定面板獲取最新設定
        settings = self.settings_panel.get_settings()
        if not settings:
            return

        # 更新配置
        self.config_manager.update(settings)

        # 記錄日誌
        self.log_message(get_text("settings_applied", "已套用設定"))

    #==========================================================================
    # 第四部分：設定與語言管理
    #==========================================================================
    def on_language_changed(self, language_code):
        """
        語言變更回調

        Args:
            language_code: 語言代碼
        """
        # 更新所有UI元件的文字
        self.update_ui_text()

    def update_ui_text(self):
        """更新所有UI元件的文字"""
        # 更新視窗標題
        self.root.title(get_text("app_title", "物件監測系統"))

        # 更新各面板文字
        # 這裡可以添加更多元件的文字更新
        pass

    #==========================================================================
    # 第五部分：日誌與工具方法
    #==========================================================================
    def log_message(self, message):
        """
        記錄日誌訊息

        Args:
            message: 日誌訊息
        """
        # 獲取當前時間
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{current_time}] {message}\n"

        # 在日誌區域顯示
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)  # 自動滾動到最新日誌

        # 同時記錄到日誌文件
        logging.info(message)

    def start_time_update(self):
        """啟動時間更新"""
        self.update_time()

    def update_time(self):
        """更新時間顯示"""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)  # 每秒更新一次

    def switch_mode(self, mode):
        """
        切換模式

        Args:
            mode: 模式名稱，'monitoring' 或 'photo'
        """
        if mode == self.current_mode:
            return

        self.current_mode = mode

        if mode == "monitoring":
            # 顯示監測模式UI
            self.video_panel.grid()
            self.settings_panel.grid()
            self.photo_panel.grid_remove()
            self.analysis_panel.grid_remove()

            # 更新控制面板按鈕文字
            self.control_panel.mode_button.config(
                text=get_text("mode_switch", "切換到拍照模式")
            )

            # 記錄日誌
            self.log_message(get_text("switch_to_monitoring", "已切換到監測模式"))

        elif mode == "photo":
            # 顯示拍照模式UI
            self.video_panel.grid_remove()
            self.settings_panel.grid_remove()
            self.photo_panel.grid()
            self.analysis_panel.grid()

            # 更新控制面板按鈕文字
            self.control_panel.mode_button.config(
                text=get_text("mode_switch_back", "切換到監測模式")
            )

            # 記錄日誌
            self.log_message(get_text("switch_to_photo", "已切換到拍照模式"))

    def get_current_mode(self):
        """
        獲取當前模式

        Returns:
            str: 當前模式名稱
        """
        return self.current_mode