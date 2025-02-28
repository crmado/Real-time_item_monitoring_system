# views/main_window.py (修改)
"""
主視窗
整合所有UI組件
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
import datetime
import os
from PIL import Image, ImageTk

from .components.control_panel import ControlPanel
from .components.video_panel import VideoPanel
from .components.settings_panel import SettingsPanel
from .components.setting.settings_dialog import SettingsDialog
from utils.language import get_text
from utils.config import Config


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
        self.root = root
        self.config_manager = config_manager
        self.root.title(get_text("app_title", "物件監測系統"))

        # 載入設定
        self.load_config()

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
        self.root.minsize(800, 600)
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
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 頂部面板 (新增)
        self.create_top_panel()

        # 控制面板
        self.control_panel = ControlPanel(self.main_frame)

        # 視訊面板
        self.video_panel = VideoPanel(self.main_frame)

        # 設定面板 (修改為簡化版，不再顯示語言和主題設定)
        self.settings_panel = SettingsPanel(self.main_frame, self.config_manager)

        # 日誌區域
        self.create_log_area()

        # 資訊區域
        self.create_info_area()

    def create_top_panel(self):
        """創建頂部面板，包含設定按鈕"""
        top_frame = ttk.Frame(self.main_frame)
        top_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))

        # 應用標題
        app_title = ttk.Label(
            top_frame,
            text=get_text("app_title", "物件監測系統"),
            font=('Arial', 12, 'bold')
        )
        app_title.pack(side=tk.LEFT, padx=10)

        # 設定按鈕
        self.load_icons()
        self.settings_button = ttk.Button(
            top_frame,
            image=self.settings_icon,
            command=self.open_settings_dialog,
            style='Icon.TButton'
        )
        self.settings_button.pack(side=tk.RIGHT, padx=10)

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

    def create_log_area(self):
        """創建日誌顯示區域"""
        log_frame = ttk.Frame(self.main_frame)
        log_frame.grid(row=3, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))

        ttk.Label(log_frame, text=get_text("system_log", "系統日誌：")).grid(row=0, column=0, sticky=tk.W)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=70,
            height=8,
            wrap=tk.WORD
        )
        self.log_text.grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))

    def create_info_area(self):
        """創建資訊顯示區域"""
        info_frame = ttk.Frame(self.main_frame)
        info_frame.grid(row=3, column=1, padx=30, pady=10, sticky=(tk.E, tk.S))

        ttk.Label(info_frame, text=get_text("current_time", "目前時間：")).grid(row=0, column=0, sticky=tk.W)
        self.time_label = ttk.Label(info_frame, text="")
        self.time_label.grid(row=1, column=0, sticky=tk.W)

    def setup_layout(self):
        """設置組件布局"""
        # 調整布局，將控制面板改為在頂部面板下方
        self.control_panel.grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)
        self.video_panel.grid(row=2, column=0, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.settings_panel.grid(row=2, column=1, padx=10, sticky=tk.N)

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
        # 假設有一個主題管理器可以應用主題

        # 更新其他設定
        # ...

    def on_settings_applied(self):
        """設定應用回調"""
        # 從設定面板獲取最新設定
        settings = self.settings_panel.get_settings()
        if not settings:
            return

        # 更新配置
        self.config_manager.update(settings)

        # 記錄日誌
        self.log_message(get_text("settings_updated", "設定已更新"))

    def on_language_changed(self, language_code):
        """
        語言變更處理函數

        Args:
            language_code: 語言代碼
        """
        # 更新視窗標題
        self.root.title(get_text("app_title", "物件監測系統"))

        # 更新各組件的語言
        self.update_components_language()

        # 記錄日誌
        self.log_message(f"語言已變更為：{language_code}")

    #==========================================================================
    # 第四部分：設定與語言管理
    #==========================================================================
    def update_components_language(self):
        """更新所有組件的語言"""
        # 更新控制面板
        if hasattr(self.control_panel, 'update_language'):
            self.control_panel.update_language()

        # 更新設定面板
        if hasattr(self.settings_panel, 'update_language'):
            self.settings_panel.update_language()

        # 更新日誌區域標籤
        for widget in self.main_frame.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label):
                        if "系統日誌" in child.cget('text') or "System Log" in child.cget('text'):
                            child.configure(text=get_text("system_log", "系統日誌："))
                        elif "目前時間" in child.cget('text') or "Current Time" in child.cget('text'):
                            child.configure(text=get_text("current_time", "目前時間："))

    #==========================================================================
    # 第五部分：日誌與工具方法
    #==========================================================================
    def start_time_update(self):
        """開始更新時間顯示"""

        def update_time():
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.configure(text=current_time)
            self.root.after(1000, update_time)

        update_time()

    def log_message(self, message):
        """
        記錄訊息到日誌區域

        Args:
            message: 要記錄的訊息
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"

            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)

            logging.info(message)
        except Exception as e:
            print(f"記錄訊息時發生錯誤：{str(e)}")

    def get_components(self):
        """
        獲取所有UI組件

        Returns:
            dict: UI組件字典
        """
        return {
            'control_panel': self.control_panel,
            'video_panel': self.video_panel,
            'settings_panel': self.settings_panel
        }

    def apply_theme(self, theme):
        """
        應用主題

        Args:
            theme:
        """

        pass