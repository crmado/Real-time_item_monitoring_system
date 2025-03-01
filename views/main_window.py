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
from views.components.photo_panel import PhotoPanel
from views.components.analysis_panel import AnalysisPanel
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

        # # 頂部面板 (新增)
        # self.create_top_panel()

        # 控制面板
        self.control_panel = ControlPanel(self.main_frame)

        # 拍照面板（拍照模式）
        self.photo_panel = PhotoPanel(self.main_frame)

        # 分析面板（拍照模式）
        self.analysis_panel = AnalysisPanel(self.main_frame)

        # 預設顯示視訊面板，隱藏拍照面板
        self.current_mode = "monitoring"  # 'monitoring' or 'photo'

        # 視訊面板
        self.video_panel = VideoPanel(self.main_frame)

        # 設定面板
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
        info_frame.grid(row=3, column=1, padx=10, pady=10, sticky=(tk.E, tk.S))

        # 左側顯示時間
        time_frame = ttk.Frame(info_frame)
        time_frame.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(time_frame, text=get_text("current_time", "目前時間：")).grid(row=0, column=0, sticky=tk.W)
        self.time_label = ttk.Label(time_frame, text="")
        self.time_label.grid(row=1, column=0, sticky=tk.W)

        # 右側顯示設定圖標
        self.load_icons()
        settings_frame = ttk.Frame(info_frame)
        settings_frame.pack(side=tk.RIGHT)

        self.settings_button = ttk.Button(
            settings_frame,
            image=self.settings_icon if self.settings_icon else None,
            text="" if self.settings_icon else "⚙",  # 如果沒有圖標，使用文字符號
            width=3 if not self.settings_icon else None,
            command=self.open_settings_dialog
        )
        self.settings_button.pack(padx=5, pady=5)

    def setup_layout(self):
        """設置組件布局"""
        # 調整布局，確保所有元素可見且美觀
        self.control_panel.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=(tk.W, tk.E))

        # 視訊面板占據主要空間（初始顯示）
        self.video_panel.grid(row=1, column=0, padx=(0, 10), pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 拍照面板（初始隱藏）
        self.photo_panel.grid(row=1, column=0, padx=(0, 10), pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.photo_panel.grid_remove()  # 隱藏拍照面板

        # 分析結果面板（初始隱藏）
        self.analysis_panel.grid(row=1, column=0, padx=(0, 10), pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.analysis_panel.grid_remove()  # 隱藏分析結果面板

        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=3)  # 視訊/拍照面板佔較多空間

        # 設定面板在視訊面板右側
        self.settings_panel.grid(row=1, column=1, padx=(0, 10), pady=10, sticky=(tk.N, tk.E, tk.W))
        self.main_frame.grid_columnconfigure(1, weight=1)  # 設定面板佔較少空間

        # 日誌區域跨兩列
        # 已在 create_log_area 中設置

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

    def toggle_mode(self):
        """切換監測/拍照模式"""
        if self.current_mode == "monitoring":
            # 切換到拍照模式
            self.video_panel.grid_remove()
            self.photo_panel.grid()
            self.analysis_panel.grid_remove()
            self.current_mode = "photo"
            self.control_panel.update_mode_button_text(True)
            self.log_message(get_text("switched_to_photo", "已切換到拍照模式"))
        elif self.current_mode == "photo":
            # 切換到監測模式
            self.photo_panel.grid_remove()
            self.analysis_panel.grid_remove()
            self.video_panel.grid()
            self.current_mode = "monitoring"
            self.control_panel.update_mode_button_text(False)
            self.log_message(get_text("switched_to_monitoring", "已切換到監測模式"))
        elif self.current_mode == "analysis":
            # 從分析結果返回到拍照模式
            self.analysis_panel.grid_remove()
            self.photo_panel.grid()
            self.current_mode = "photo"
            self.log_message(get_text("back_to_photo", "已返回到拍照模式"))

    def show_analysis_results(self, result):
        """
        顯示分析結果

        Args:
            result: 分析結果數據
        """
        # 隱藏拍照面板
        self.photo_panel.grid_remove()

        # 顯示分析結果面板
        self.analysis_panel.grid()

        # 更新分析結果
        self.analysis_panel.update_analysis_results(result)

        # 設置當前模式
        self.current_mode = "analysis"

        # 記錄日誌
        self.log_message(get_text("analysis_completed", "分析完成"))

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