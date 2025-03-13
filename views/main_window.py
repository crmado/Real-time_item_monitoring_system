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
from utils.theme_manager import ThemeManager
from utils.settings_manager import get_settings_manager

# 版本号
VERSION = "1.0.0"

class MainWindow(tk.Frame):
    """
    主窗口类
    整合所有UI组件
    """

    #==========================================================================
    # 第一部分：基本屬性和初始化
    #==========================================================================
    def __init__(self, root, system_controller=None):
        """
        初始化主窗口
        
        Args:
            root: Tkinter 根窗口
            system_controller: 系统控制器
        """
        super().__init__(root)
        self.root = root
        self.system_controller = system_controller
        
        # 设置窗口属性
        self.root.title(get_text("app_title", "实时物品监测系统"))
        self.root.geometry("1280x720")
        self.root.minsize(800, 600)
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager(root)
        
        # 配置根窗口的行列权重
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 将自身放置在根窗口中
        self.pack(fill=tk.BOTH, expand=True)
        
        # 创建组件
        self.create_widgets()
        
        # 註冊回調函數
        self.register_callbacks()
        
        # 如果提供了系统控制器，则初始化
        if system_controller:
            system_controller.initialize(self)

    def get_components(self):
        """
        獲取所有UI組件

        Returns:
            dict: 包含所有UI組件的字典
        """
        return {
            'control_panel': self.control_panel,
            'video_panel': self.video_panel,
            'photo_panel': self.photo_panel,
            'settings_panel': self.settings_panel,
            'analysis_panel': self.analysis_panel
        }

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
        self.config_manager = self.system_controller.config_manager

        # 應用設定
        self.apply_settings()

        # 設定語言
        language_code = self.config_manager.get('system.language', 'zh_TW')
        self.on_language_changed(language_code)

        # 設定主題
        theme = self.config_manager.get('ui.theme', 'light')
        self.theme_manager.set_theme(theme)

        # 設定視窗樣式
        self.style = ttk.Style()
        self.style.configure('Main.TFrame', background=self.theme_manager.get_main_color())
        self.style.configure('Header.TFrame', background=self.theme_manager.get_main_color())
        self.style.configure('Content.TFrame', background=self.theme_manager.get_main_color())
        self.style.configure('Footer.TFrame', background=self.theme_manager.get_main_color())
        self.style.configure('Header.TLabel', background=self.theme_manager.get_main_color())
        self.style.configure('HeaderTitle.TLabel', background=self.theme_manager.get_main_color())
        self.style.configure('Header.TButton', background=self.theme_manager.get_main_color())


    #==========================================================================
    # 第二部分：UI元件創建
    #==========================================================================
    def create_widgets(self):
        """创建主窗口组件"""
        # 创建主框架
        self.main_frame = ttk.Frame(self, style='Main.TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建顶部标题栏
        self.header = ttk.Frame(self.main_frame, style='Header.TFrame')
        self.header.pack(fill=tk.X, padx=0, pady=0)

        # 标题和logo
        logo_frame = ttk.Frame(self.header, style='Header.TFrame')
        logo_frame.pack(side=tk.LEFT, padx=10, pady=5)

        # 添加应用图标
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'icon.png')
            if os.path.exists(icon_path):
                icon_img = Image.open(icon_path)
                icon_img = icon_img.resize((32, 32), Image.Resampling.LANCZOS)
                self.icon_photo = ImageTk.PhotoImage(icon_img)
                icon_label = ttk.Label(logo_frame, image=self.icon_photo, style='Header.TLabel')
                icon_label.pack(side=tk.LEFT, padx=(0, 10))
        except Exception as e:
            logging.error(f"加载图标时出错: {str(e)}")

        # 应用标题
        title_label = ttk.Label(
            logo_frame, 
            text=get_text("app_title", "实时物品监测系统"),
            style='HeaderTitle.TLabel'
        )
        title_label.pack(side=tk.LEFT)

        # 右侧控制按钮
        control_buttons = ttk.Frame(self.header, style='Header.TFrame')
        control_buttons.pack(side=tk.RIGHT, padx=10, pady=5)

        # 设置按钮
        self.settings_btn = ttk.Button(
            control_buttons,
            text=get_text("settings", "设置"),
            style='Header.TButton',
            command=self._on_settings
        )
        self.settings_btn.pack(side=tk.RIGHT, padx=5)

        # 创建内容区域
        self.content = ttk.Frame(self.main_frame, style='Content.TFrame')
        self.content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 使用网格布局
        self.content.columnconfigure(0, weight=1)  # 左侧控制面板
        self.content.columnconfigure(1, weight=4)  # 右侧视频/照片面板

        # 创建左侧控制面板
        self.control_panel = ControlPanel(self.content)
        self.control_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 创建右侧视频面板（默认显示）
        self.video_panel = VideoPanel(self.content)
        self.video_panel.grid(row=0, column=1, sticky="nsew")

        # 创建右侧照片面板（初始隐藏）
        self.photo_panel = PhotoPanel(self.content)
        self.photo_panel.grid(row=0, column=1, sticky="nsew")
        self.photo_panel.grid_remove()  # 初始隐藏
        
        # 创建设置面板
        self.settings_panel = self.create_settings_panel()
        self.settings_panel.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        
        # 创建分析面板（初始隐藏）
        self.analysis_panel = AnalysisPanel(self.content)
        self.analysis_panel.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        self.analysis_panel.grid_remove()  # 初始隐藏

        # 创建底部状态栏
        self.status_bar = ttk.Frame(self.main_frame, style='Footer.TFrame')
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)

        # 状态信息
        self.status_label = ttk.Label(
            self.status_bar,
            text=get_text("status_ready", "就绪"),
            style='Footer.TLabel'
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=5)

        # 版本信息
        version_label = ttk.Label(
            self.status_bar,
            text=f"v{VERSION}",
            style='Footer.TLabel'
        )
        version_label.pack(side=tk.RIGHT, padx=10, pady=5)

        # 初始化当前模式
        self.current_mode = "monitoring"  # 默认为监控模式

    def create_settings_panel(self):
        """創建設定面板"""
        # 創建設定面板，使用content作為父級元件
        self.settings_panel = SettingsPanel(self.content)
        
        # 如果有系統控制器，設置回調
        if hasattr(self, 'system_controller') and self.system_controller:
            self.settings_panel.set_callback('settings_applied', self.system_controller.handle_apply_settings)
            
        return self.settings_panel

    #==========================================================================
    # 第三部分：事件處理
    #==========================================================================
    def register_callbacks(self):
        """註冊回調函數"""
        # 註冊設定面板的回調函數
        if hasattr(self, 'settings_panel'):
            self.settings_panel.set_callback('settings_applied', self.on_settings_applied)
            logging.info("已註冊設定面板的回調函數")

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
        self.theme_manager.set_theme(theme)

        if hasattr(self, 'system_controller') and self.system_controller is not None:
            self.system_controller.handle_theme_change(theme)

        # 更新其他設定
        self.log_message(get_text("settings_updated", "設定已更新"))

    def set_system_controller(self, controller):
        """
        设置系统控制器
        
        Args:
            controller: 系统控制器实例
        """
        self.system_controller = controller

    def on_settings_applied(self, settings):
        """
        設定應用回調
        
        Args:
            settings: 設定值字典
        """
        # 如果沒有設定值，直接返回
        if not settings:
            logging.error("無法套用設定：設定值為空")
            return

        # 如果有系統控制器，將設定傳遞給它
        if self.system_controller and hasattr(self.system_controller, 'handle_apply_settings'):
            self.system_controller.handle_apply_settings(settings)
            logging.info(f"已將設定傳遞給系統控制器: {settings}")
        else:
            logging.warning("無法套用設定：系統控制器不存在或沒有 handle_apply_settings 方法")

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

        # 更新標題標籤
        for widget in self.header.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label) and hasattr(child, 'cget') and child.cget('text') != '':
                        if 'HeaderTitle' in str(child):
                            child.configure(text=get_text("app_title", "物件監測系統"))

        # 更新設定按鈕
        if hasattr(self, 'settings_btn'):
            self.settings_btn.configure(text=get_text("settings", "設定"))

        # 更新控制面板
        if hasattr(self, 'control_panel'):
            self.control_panel.update_ui_text()

        # 更新設定面板
        if hasattr(self, 'settings_panel'):
            self.settings_panel.update_ui_text()

        # 更新狀態標籤
        if hasattr(self, 'status_label'):
            current_status = self.status_label.cget('text')
            if current_status == "就绪" or current_status == "就緒":
                self.status_label.configure(text=get_text("status_ready", "就緒"))
            elif current_status == "正在运行" or current_status == "正在運行":
                self.status_label.configure(text=get_text("status_running", "正在運行"))
            elif current_status == "已停止":
                self.status_label.configure(text=get_text("status_stopped", "已停止"))

        # 更新視頻面板
        if hasattr(self, 'video_panel'):
            self.video_panel.update_ui_text()

        # 更新照片面板
        if hasattr(self, 'photo_panel'):
            self.photo_panel.update_ui_text()

        # 更新分析面板
        if hasattr(self, 'analysis_panel'):
            self.analysis_panel.update_ui_text()

        # 強制更新 Tkinter
        self.root.update_idletasks()

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
        if hasattr(self, 'log_text'):
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
        if hasattr(self, 'time_label'):
            self.time_label.config(text=current_time)
            self.root.after(1000, self.update_time)  # 每秒更新一次

    def switch_mode(self, mode):
        """
        切换模式
        
        Args:
            mode: 模式名称 ("monitoring" 或 "photo")
        """
        if mode == self.current_mode:
            return
            
        self.current_mode = mode
        
        if mode == "monitoring":
            # 显示视频面板，隐藏照片面板
            self.video_panel.grid()
            self.photo_panel.grid_remove()
            
            # 更新控制面板状态
            if hasattr(self.control_panel, 'current_mode'):
                self.control_panel.current_mode.set("monitoring")
                
        elif mode == "photo":
            # 显示照片面板，隐藏视频面板
            self.video_panel.grid_remove()
            self.photo_panel.grid()
            
            # 更新控制面板状态
            if hasattr(self.control_panel, 'current_mode'):
                self.control_panel.current_mode.set("photo")

    def get_current_mode(self):
        """
        獲取當前模式

        Returns:
            str: 當前模式名稱
        """
        return self.current_mode

    def _on_settings(self):
        """处理设置按钮点击事件"""
        try:
            # 如果有系统控制器，调用其处理方法
            if self.system_controller and hasattr(self.system_controller, '_on_settings'):
                self.system_controller._on_settings()
            else:
                # 否则显示简单的消息框
                from tkinter import messagebox
                messagebox.showinfo("设置", "设置功能尚未实现")
        except Exception as e:
            logging.error(f"打开设置对话框时出错: {str(e)}")