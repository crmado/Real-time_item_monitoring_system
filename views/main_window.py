"""
主視窗
整合所有UI組件
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
import datetime
import os
import threading
import time

import numpy as np # type: ignore
from PIL import Image, ImageTk # type: ignore

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
        
        # 根據螢幕大小設定視窗屬性
        self.set_window_size_by_screen()
        
        # 初始化主题管理器
        self.theme_manager = ThemeManager(root)
        
        # 配置根窗口的行列权重
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # 将自身放置在根窗口中
        self.pack(fill=tk.BOTH, expand=True)
        
        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", self.on_window_resize)
        
        # 创建组件
        self.create_widgets()
        
        # 註冊回調函數
        self.register_callbacks()
        
        # 如果提供了系统控制器，则初始化
        if system_controller:
            system_controller.initialize(self)
        
        # 延遲加載相機，避免啟動時UI卡頓
        # 使用after將相機初始化延遲到主視窗完全顯示後
        self.root.after(100, self.delayed_camera_initialization)

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
            text=get_text("app_title", "實時物品檢測系統"),
            style='HeaderTitle.TLabel'
        )
        title_label.pack(side=tk.LEFT)

        # 右侧控制按钮
        control_buttons = ttk.Frame(self.header, style='Header.TFrame')
        control_buttons.pack(side=tk.RIGHT, padx=10, pady=5)

        # 设置按钮
        self.settings_btn = ttk.Button(
            control_buttons,
            text=get_text("settings", "設置"),
            style='Header.TButton',
            command=self._on_settings
        )
        self.settings_btn.pack(side=tk.RIGHT, padx=5)

        # 创建可调整的上下分隔面板
        self.paned_window = ttk.PanedWindow(self.main_frame, orient=tk.VERTICAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 上半部分为内容区域
        self.content = ttk.Frame(self.paned_window, style='Content.TFrame')
        self.paned_window.add(self.content, weight=70)  # 70%的空间
        
        # 下半部分为日志区域
        self.log_container = ttk.Frame(self.paned_window, style='Content.TFrame')
        self.paned_window.add(self.log_container, weight=30)  # 30%的空间
        
        # 設置分隔線初始位置 (大約在視窗70%的位置)
        def set_sash_position():
            # 在UI完全加載後設置分隔線位置
            window_height = self.winfo_height()
            if window_height > 0:
                sash_pos = int(window_height * 0.7)
                try:
                    self.paned_window.sashpos(0, sash_pos)
                except:
                    pass  # 忽略可能的錯誤
        
        # 在UI完全加載後設置分隔線位置
        self.after(100, set_sash_position)

        # 修改为固定比例布局
        # 左側控制面板：中間視頻面板：右側設置面板 = 2.5 : 7 : 2.5
        self.content.columnconfigure(0, weight=25)  # 左侧控制面板 (25%)
        self.content.columnconfigure(1, weight=70)  # 中间视频/照片面板 (70%)
        self.content.columnconfigure(2, weight=25)  # 右侧设置面板 (25%)
        self.content.rowconfigure(0, weight=1)      # 行高度比例

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

        # 創建日誌顯示區域 (在日志容器中)
        self.create_log_area()

        # 創建底部狀態欄
        self.status_bar = ttk.Frame(self.main_frame, style='Footer.TFrame')
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=0, pady=0)

        # 狀態資訊  
        self.status_label = ttk.Label(
            self.status_bar,
            text=get_text("status_ready", "就緒"),
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

    def create_log_area(self):
        """創建日誌顯示區域"""
        # 使用log_container作為父元素
        # 創建日誌標題和控制按鈕的框架
        log_header = ttk.Frame(self.log_container)
        log_header.pack(fill=tk.X, side=tk.TOP, padx=5, pady=2)
        
        # 創建日誌標題
        log_title = ttk.Label(log_header, text=get_text("log_title", "系統日誌"))
        log_title.pack(side=tk.LEFT, padx=5, pady=2)
        
        # 創建日誌控制按鈕框架
        log_buttons = ttk.Frame(log_header)
        log_buttons.pack(side=tk.RIGHT, padx=5, pady=2)
        
        # 清除日誌按鈕
        clear_log_btn = ttk.Button(
            log_buttons,
            text=get_text("clear_log", "清除日誌"),
            command=self.clear_log
        )
        clear_log_btn.pack(side=tk.RIGHT, padx=5)
        
        # 顯示/隱藏日誌按鈕
        self.log_visible = tk.BooleanVar(value=True)
        self.toggle_log_btn = ttk.Button(
            log_buttons,
            text=get_text("hide_log", "隱藏日誌"),
            command=self.toggle_log_visibility
        )
        self.toggle_log_btn.pack(side=tk.RIGHT, padx=5)
        
        # 創建日誌文本區域 - 使用fill=BOTH和expand=True填充整個容器
        self.log_text = scrolledtext.ScrolledText(self.log_container, height=15, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.log_text.config(state=tk.DISABLED)  # 設為只讀

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

        # 更新日誌區域按鈕
        if hasattr(self, 'toggle_log_btn'):
            if self.log_visible.get():
                self.toggle_log_btn.configure(text=get_text("hide_log", "隱藏日誌"))
            else:
                self.toggle_log_btn.configure(text=get_text("show_log", "顯示日誌"))

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
        # 過濾掉"檢測到X個物體"的訊息，避免日誌區域過於雜亂
        if "檢測到" in message and "個物體" in message:
            return
            
        # 獲取當前時間
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{current_time}] {message}\n"

        # 在日誌區域顯示
        if hasattr(self, 'log_text'):
            self.log_text.config(state=tk.NORMAL)  # 臨時啟用編輯
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)  # 自動滾動到最新日誌
            self.log_text.config(state=tk.DISABLED)  # 恢復只讀狀態

    def clear_log(self):
        """清除日誌顯示區域的內容"""
        if hasattr(self, 'log_text'):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.log_message(get_text("log_cleared", "日誌已清除"))

    def toggle_log_visibility(self):
        """切換日誌顯示區域的可見性"""
        if self.log_visible.get():
            # 隱藏日誌
            self.paned_window.forget(self.log_container)
            self.log_visible.set(False)
            self.toggle_log_btn.configure(text=get_text("show_log", "顯示日誌"))
            
            # 在底部重新添加顯示按鈕
            self.toggle_log_frame = ttk.Frame(self.main_frame)
            self.toggle_log_frame.pack(fill=tk.X, side=tk.BOTTOM, before=self.status_bar)
            self.show_log_btn = ttk.Button(
                self.toggle_log_frame, 
                text=get_text("show_log", "顯示日誌"),
                command=self.toggle_log_visibility
            )
            self.show_log_btn.pack(side=tk.RIGHT, padx=5, pady=2)
        else:
            # 顯示日誌
            # 移除臨時的顯示按鈕框架
            if hasattr(self, 'toggle_log_frame'):
                self.toggle_log_frame.destroy()
            
            # 將日誌區域添加回PanedWindow
            self.paned_window.add(self.log_container, weight=30)
            self.log_visible.set(True)
            self.toggle_log_btn.configure(text=get_text("hide_log", "隱藏日誌"))
            
            # 更新一下佈局
            self.root.update_idletasks()

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

    def show_splash_screen(self):
        """顯示啟動畫面"""
        # 創建啟動視窗
        self.splash = tk.Toplevel(self.root)
        self.splash.title("")
        self.splash.overrideredirect(True)  # 無邊框窗口
        
        # 計算啟動畫面位置（居中）
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        splash_width = 400
        splash_height = 300
        position_x = int((screen_width - splash_width) / 2)
        position_y = int((screen_height - splash_height) / 2)
        
        # 設置啟動畫面大小和位置
        self.splash.geometry(f"{splash_width}x{splash_height}+{position_x}+{position_y}")
        
        # 設置啟動畫面內容
        splash_frame = ttk.Frame(self.splash)
        splash_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加標題
        title_label = ttk.Label(
            splash_frame,
            text=get_text("app_title", "即時物品監測系統"),
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=(40, 20))
        
        # 添加版本信息
        version_label = ttk.Label(
            splash_frame,
            text=f"v{VERSION}",
            font=("Arial", 12)
        )
        version_label.pack(pady=10)
        
        # 添加加載進度條
        self.splash_progress = ttk.Progressbar(
            splash_frame, 
            length=300, 
            mode='indeterminate'
        )
        self.splash_progress.pack(pady=20)
        self.splash_progress.start(10)
        
        # 添加加載狀態文本
        self.splash_status = ttk.Label(
            splash_frame,
            text=get_text("initializing", "正在初始化..."),
            font=("Arial", 10)
        )
        self.splash_status.pack(pady=10)
        
        # 確保啟動畫面顯示在最前面
        self.splash.attributes('-topmost', True)
        self.splash.update()

    def close_splash_screen(self):
        """關閉啟動畫面"""
        if hasattr(self, 'splash') and self.splash is not None:
            self.splash_progress.stop()
            self.splash.destroy()
            self.splash = None

    def update_splash_status(self, status):
        """更新啟動畫面狀態文本"""
        if hasattr(self, 'splash_status') and self.splash_status is not None:
            self.splash_status.config(text=status)
            self.splash.update()

    def delayed_camera_initialization(self):
        """延遲初始化相機，避免啟動時UI卡頓"""
        # 檢查是否有系統控制器
        if not hasattr(self, 'system_controller') or self.system_controller is None:
            logging.error("系統控制器未初始化，無法加載相機")
            return
            
        # 在單獨的線程中初始化相機
        def init_camera():
            try:
                # 獲取可用相機源
                if hasattr(self.system_controller, 'camera_manager'):
                    # 更新UI訊息
                    self.log_message("正在檢測相機...")
                    
                    # 獲取相機列表
                    available_sources = self.system_controller.camera_manager.get_available_sources()
                    logging.info(f"可用相機源: {available_sources}")
                    
                    # 在主線程中更新UI
                    self.root.after(0, lambda: self.control_panel.set_camera_sources(available_sources))
                    
                    # 選擇默認相機但不立即開啟
                    default_camera = None
                    if "Built-in Camera" in available_sources:
                        default_camera = "Built-in Camera"
                    elif "USB Camera 0" in available_sources:
                        default_camera = "USB Camera 0"
                    elif available_sources:
                        default_camera = available_sources[0]
                    
                    if default_camera:
                        logging.info(f"默認選擇相機: {default_camera}")
                        # 在主線程中設置默認相機
                        self.root.after(0, lambda: self.control_panel.set_camera_source(default_camera))
                    else:
                        self.log_message("未檢測到相機")
            except Exception as e:
                logging.error(f"初始化相機時發生錯誤: {str(e)}")
                self.log_message(f"初始化相機時發生錯誤: {str(e)}")
        
        # 使用線程執行初始化
        threading.Thread(target=init_camera, daemon=True).start()

    def on_window_resize(self, event):
        """處理窗口大小變化事件"""
        # 只處理來自根窗口的事件
        if event.widget == self.root:
            # 調整分隔線位置
            if hasattr(self, 'paned_window'):
                # 設置分隔線位置為窗口高度的70%
                window_height = self.winfo_height()
                if window_height > 0:
                    try:
                        self.paned_window.sashpos(0, int(window_height * 0.7))
                    except:
                        pass  # 忽略可能的錯誤

    def set_window_size_by_screen(self):
        """設定視窗基本屬性，使用固定的常見視窗大小"""
        # 使用固定的視窗大小（常見的HD尺寸）
        window_width = 1280
        window_height = 720
        
        # 固定的最小視窗大小
        min_width = 1024
        min_height = 768
        
        # 應用設定
        self.root.title(get_text("app_title", "即時物品監測系統"))
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(min_width, min_height)
        
        logging.info(f"設定視窗大小: {window_width}x{window_height}, 最小大小: {min_width}x{min_height}")