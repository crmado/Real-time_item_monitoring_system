"""
設定對話框
負責顯示和管理應用程式設定
"""

import tkinter as tk
from tkinter import ttk
import logging

from utils.language import get_text, change_language, get_available_languages, get_language_name
from utils.config import Config


class SettingsDialog(tk.Toplevel):
    """設定對話框類別"""

    def __init__(self, parent, config_manager, **kwargs):
        """
        初始化設定對話框

        Args:
            parent: 父級視窗
            config_manager: 配置管理器實例
            **kwargs: 其他參數
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.config_manager = config_manager
        self.result = None

        # 設定對話框屬性
        self.title(get_text("settings_title", "系統設定"))
        self.geometry("600x500")
        # 或者設定最小大小以確保按鈕不會被截斷
        self.minsize(500, 350)
        self.resizable(False, False)
        self.transient(parent)  # 設為父視窗的附屬視窗
        self.grab_set()  # 模態對話框

        # 建立UI元件
        self.create_widgets()

        # 置中顯示
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        # 綁定關閉事件
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def create_widgets(self):
        """創建對話框元件"""
        # 主框架
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 建立標籤頁
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # 一般設定頁面
        general_tab = ttk.Frame(notebook)
        notebook.add(general_tab, text=get_text("general_settings", "一般設定"))

        # 顯示設定頁面
        display_tab = ttk.Frame(notebook)
        notebook.add(display_tab, text=get_text("display_settings", "顯示設定"))

        # 檢測設定頁面
        detection_tab = ttk.Frame(notebook)
        notebook.add(detection_tab, text=get_text("detection_settings", "檢測設定"))

        # 一般設定內容
        self.create_general_settings(general_tab)

        # 顯示設定內容
        self.create_display_settings(display_tab)

        # 檢測設定內容
        self.create_detection_settings(detection_tab)

        # 底部按鈕
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        # 取消按鈕
        cancel_btn = ttk.Button(
            button_frame,
            text=get_text("cancel", "取消"),
            command=self.on_cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)

        # 保存按鈕
        save_btn = ttk.Button(
            button_frame,
            text=get_text("save", "保存"),
            style='Accent.TButton',
            command=self.on_save
        )
        save_btn.pack(side=tk.RIGHT, padx=5)

    def create_general_settings(self, parent):
        """創建一般設定元件"""
        # 語言設定
        lang_frame = ttk.LabelFrame(parent, text=get_text("language", "語言"))
        lang_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.W)

        # 語言選擇下拉選單
        self.language_var = tk.StringVar()
        self.language_combo = ttk.Combobox(
            lang_frame,
            width=20,
            textvariable=self.language_var,
            state="readonly"
        )
        self.language_combo.pack(padx=10, pady=10)

        # 獲取可用語言
        languages = get_available_languages()
        language_display = [f"{get_language_name(lang)}" for lang in languages]
        self.language_combo['values'] = language_display

        # 設定當前語言
        current_language = self.config_manager.get('system.language', 'zh_TW')
        if current_language in languages:
            default_index = languages.index(current_language)
            self.language_combo.current(default_index)

        # 自動檢查更新
        self.check_update_var = tk.BooleanVar(value=self.config_manager.get('system.check_updates', True))
        check_update_cb = ttk.Checkbutton(
            parent,
            text=get_text("check_updates", "啟動時檢查更新"),
            variable=self.check_update_var
        )
        check_update_cb.pack(fill=tk.X, padx=10, pady=10, anchor=tk.W)

        # 備份配置
        self.backup_config_var = tk.BooleanVar(value=self.config_manager.get('system.backup_config', True))
        backup_config_cb = ttk.Checkbutton(
            parent,
            text=get_text("backup_config", "修改配置前自動備份"),
            variable=self.backup_config_var
        )
        backup_config_cb.pack(fill=tk.X, padx=10, pady=5, anchor=tk.W)

    def create_display_settings(self, parent):
        """創建顯示設定元件"""
        # 主題設定
        theme_frame = ttk.LabelFrame(parent, text=get_text("theme", "主題"))
        theme_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.W)

        # 主題選擇按鈕
        self.theme_var = tk.StringVar(value=self.config_manager.get('ui.theme', 'light'))
        self.light_radio = ttk.Radiobutton(
            theme_frame,
            text=get_text("light_theme", "亮色模式"),
            variable=self.theme_var,
            value="light"
        )
        self.dark_radio = ttk.Radiobutton(
            theme_frame,
            text=get_text("dark_theme", "暗色模式"),
            variable=self.theme_var,
            value="dark"
        )

        self.light_radio.pack(padx=10, pady=5, anchor=tk.W)
        self.dark_radio.pack(padx=10, pady=5, anchor=tk.W)

        # 字體大小
        font_frame = ttk.LabelFrame(parent, text=get_text("font_size", "字體大小"))
        font_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.W)

        self.font_size_var = tk.StringVar(value=self.config_manager.get('ui.font_size', 'medium'))
        self.small_radio = ttk.Radiobutton(
            font_frame,
            text=get_text("small", "小"),
            variable=self.font_size_var,
            value="small"
        )
        self.medium_radio = ttk.Radiobutton(
            font_frame,
            text=get_text("medium", "中"),
            variable=self.font_size_var,
            value="medium"
        )
        self.large_radio = ttk.Radiobutton(
            font_frame,
            text=get_text("large", "大"),
            variable=self.font_size_var,
            value="large"
        )

        self.small_radio.pack(padx=10, pady=5, anchor=tk.W)
        self.medium_radio.pack(padx=10, pady=5, anchor=tk.W)
        self.large_radio.pack(padx=10, pady=5, anchor=tk.W)

        # 顯示效能資訊
        self.show_performance_var = tk.BooleanVar(value=self.config_manager.get('ui.show_performance', True))
        performance_cb = ttk.Checkbutton(
            parent,
            text=get_text("show_performance", "顯示效能資訊"),
            variable=self.show_performance_var
        )
        performance_cb.pack(fill=tk.X, padx=10, pady=10, anchor=tk.W)

    def create_detection_settings(self, parent):
        """創建檢測設定元件"""
        # 預設檢測設定
        default_frame = ttk.LabelFrame(parent, text=get_text("default_detection", "預設檢測設定"))
        default_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.W)

        # 預計數量
        target_frame = ttk.Frame(default_frame)
        target_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(target_frame, text=get_text("target_count", "預計數量：")).pack(side=tk.LEFT)
        self.target_entry = ttk.Entry(target_frame, width=10)
        self.target_entry.pack(side=tk.LEFT, padx=5)
        self.target_entry.insert(0, str(self.config_manager.get('detection.target_count', 1000)))

        # 緩衝點
        buffer_frame = ttk.Frame(default_frame)
        buffer_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(buffer_frame, text=get_text("buffer_point", "緩衝點：")).pack(side=tk.LEFT)
        self.buffer_entry = ttk.Entry(buffer_frame, width=10)
        self.buffer_entry.pack(side=tk.LEFT, padx=5)
        self.buffer_entry.insert(0, str(self.config_manager.get('detection.buffer_point', 950)))

        # ROI 預設位置
        roi_frame = ttk.Frame(default_frame)
        roi_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(roi_frame, text=get_text("roi_position", "ROI 預設位置 (%):")).pack(side=tk.LEFT)
        self.roi_entry = ttk.Entry(roi_frame, width=10)
        self.roi_entry.pack(side=tk.LEFT, padx=5)
        roi_value = self.config_manager.get('detection.roi_default_position', 0.2) * 100
        self.roi_entry.insert(0, str(int(roi_value)))

        # 物件面積範圍
        area_frame = ttk.LabelFrame(parent, text=get_text("object_area", "物件面積範圍"))
        area_frame.pack(fill=tk.X, padx=10, pady=10, anchor=tk.W)

        # 最小面積
        min_frame = ttk.Frame(area_frame)
        min_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(min_frame, text=get_text("min_area", "最小面積:")).pack(side=tk.LEFT)
        self.min_area_entry = ttk.Entry(min_frame, width=10)
        self.min_area_entry.pack(side=tk.LEFT, padx=5)
        self.min_area_entry.insert(0, str(self.config_manager.get('detection.min_object_area', 10)))

        # 最大面積
        max_frame = ttk.Frame(area_frame)
        max_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(max_frame, text=get_text("max_area", "最大面積:")).pack(side=tk.LEFT)
        self.max_area_entry = ttk.Entry(max_frame, width=10)
        self.max_area_entry.pack(side=tk.LEFT, padx=5)
        self.max_area_entry.insert(0, str(self.config_manager.get('detection.max_object_area', 150)))

    def on_save(self):
        """保存設定"""
        try:
            # 獲取並驗證設定
            settings = self.get_settings()
            if not settings:
                return

            # 更新配置
            self.config_manager.update(settings)

            # 設定結果
            self.result = True
            self.destroy()
        except Exception as e:
            logging.error(f"保存設定時發生錯誤：{str(e)}")

    def on_cancel(self):
        """取消設定"""
        self.result = False
        self.destroy()

    def get_settings(self):
        """獲取所有設定值"""
        try:
            # 獲取語言設定
            selected_index = self.language_combo.current()
            languages = get_available_languages()
            language_code = languages[selected_index] if selected_index >= 0 else 'zh_TW'

            # 獲取檢測設定
            target_count = int(self.target_entry.get())
            buffer_point = int(self.buffer_entry.get())
            roi_position = int(self.roi_entry.get()) / 100.0  # 從百分比轉為小數
            min_area = int(self.min_area_entry.get())
            max_area = int(self.max_area_entry.get())

            # 驗證設定
            if buffer_point >= target_count:
                raise ValueError(get_text("error_buffer_target", "緩衝點必須小於預計數量"))

            if min_area >= max_area:
                raise ValueError(get_text("error_min_max_area", "最小面積必須小於最大面積"))

            if not (0 <= roi_position <= 1):
                raise ValueError(get_text("error_roi_position", "ROI 位置必須在 0% 到 100% 之間"))

            # 返回設定字典
            return {
                'system.language': language_code,
                'system.check_updates': self.check_update_var.get(),
                'system.backup_config': self.backup_config_var.get(),
                'ui.theme': self.theme_var.get(),
                'ui.font_size': self.font_size_var.get(),
                'ui.show_performance': self.show_performance_var.get(),
                'detection.target_count': target_count,
                'detection.buffer_point': buffer_point,
                'detection.roi_default_position': roi_position,
                'detection.min_object_area': min_area,
                'detection.max_object_area': max_area
            }

        except ValueError as e:
            logging.error(str(e))
            from tkinter import messagebox
            messagebox.showerror(get_text("settings_error", "設定錯誤"), str(e))
            return None
        except Exception as e:
            logging.error(f"獲取設定值時發生錯誤：{str(e)}")
            return None