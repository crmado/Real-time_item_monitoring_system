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
        self.language_var = tk.StringVar(value="繁體中文")  # 默认值
        
        try:
            # 獲取可用語言
            languages = get_available_languages()
            if not languages:
                languages = ['zh_TW']
                
            language_display = [f"{get_language_name(lang)}" for lang in languages]
            
            self.language_combo = ttk.Combobox(
                lang_frame,
                width=20,
                textvariable=self.language_var,
                values=language_display,
                state="readonly"
            )
            self.language_combo.pack(padx=10, pady=10)

            # 設定當前語言
            current_language = self.config_manager.get('system.language', 'zh_TW')
            if current_language in languages:
                default_index = languages.index(current_language)
                self.language_combo.current(default_index)
            else:
                # 如果当前语言不在列表中，默认选择第一个
                self.language_combo.current(0)
                
        except Exception as e:
            logging.error(f"初始化语言下拉框时出错: {str(e)}")
            # 创建一个简单的标签代替下拉框
            ttk.Label(lang_frame, text="繁體中文 (默认)").pack(padx=10, pady=10)

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
            try:
                if hasattr(self, 'language_combo') and self.language_combo.winfo_exists():
                    selected_index = self.language_combo.current()
                    languages = get_available_languages()
                    language_code = languages[selected_index] if selected_index >= 0 and selected_index < len(languages) else 'zh_TW'
                else:
                    language_code = 'zh_TW'  # 默認使用繁體中文
            except Exception as e:
                logging.warning(f"獲取語言設置時出錯: {str(e)}")
                language_code = 'zh_TW'  # 默認使用繁體中文

            # 獲取檢測設定
            try:
                # 檢查 UI 元素是否存在
                if hasattr(self, 'target_entry') and self.target_entry.winfo_exists():
                    target_count = int(self.target_entry.get())
                else:
                    target_count = 1000  # 默認值
                    
                if hasattr(self, 'buffer_entry') and self.buffer_entry.winfo_exists():
                    buffer_point = int(self.buffer_entry.get())
                else:
                    buffer_point = 950  # 默認值
                    
                if hasattr(self, 'roi_entry') and self.roi_entry.winfo_exists():
                    roi_position = int(self.roi_entry.get()) / 100.0  # 從百分比轉為小數
                else:
                    roi_position = 0.5  # 默認值
                    
                if hasattr(self, 'min_area_entry') and self.min_area_entry.winfo_exists():
                    min_area = int(self.min_area_entry.get())
                else:
                    min_area = 10  # 默認值
                    
                if hasattr(self, 'max_area_entry') and self.max_area_entry.winfo_exists():
                    max_area = int(self.max_area_entry.get())
                else:
                    max_area = 150  # 默認值
            except ValueError as e:
                logging.error(f"獲取檢測設置時出錯: {str(e)}")
                # 使用默認值
                target_count = 1000
                buffer_point = 950
                roi_position = 0.5
                min_area = 10
                max_area = 150

            # 驗證設定
            if buffer_point >= target_count:
                buffer_point = target_count - 1  # 自動修正
                logging.warning("緩衝點大於或等於預計數量，已自動修正")

            if min_area >= max_area:
                min_area = max_area - 1  # 自動修正
                logging.warning("最小面積大於或等於最大面積，已自動修正")

            if not (0 <= roi_position <= 1):
                roi_position = 0.5  # 自動修正
                logging.warning("ROI 位置超出範圍，已自動修正為 50%")

            # 獲取其他設定
            try:
                if hasattr(self, 'check_update_var'):
                    check_updates = self.check_update_var.get()
                else:
                    check_updates = True
                    
                if hasattr(self, 'backup_config_var'):
                    backup_config = self.backup_config_var.get()
                else:
                    backup_config = True
                    
                if hasattr(self, 'theme_var'):
                    theme = self.theme_var.get()
                else:
                    theme = 'light'
                    
                if hasattr(self, 'font_size_var'):
                    font_size = self.font_size_var.get()
                else:
                    font_size = 'medium'
                    
                if hasattr(self, 'show_performance_var'):
                    show_performance = self.show_performance_var.get()
                else:
                    show_performance = True
            except Exception as e:
                logging.warning(f"獲取其他設置時出錯: {str(e)}")
                # 使用默認值
                check_updates = True
                backup_config = True
                theme = 'light'
                font_size = 'medium'
                show_performance = True

            # 返回設定字典
            return {
                'system.language': language_code,
                'system.check_updates': check_updates,
                'system.backup_config': backup_config,
                'ui.theme': theme,
                'ui.font_size': font_size,
                'ui.show_performance': show_performance,
                'detection.target_count': target_count,
                'detection.buffer_point': buffer_point,
                'detection.roi_default_position': roi_position,
                'detection.min_object_area': min_area,
                'detection.max_object_area': max_area
            }

        except Exception as e:
            logging.error(f"獲取設定值時發生錯誤：{str(e)}")
            # 返回默認設定
            return {
                'system.language': 'zh_TW',
                'system.check_updates': True,
                'system.backup_config': True,
                'ui.theme': 'light',
                'ui.font_size': 'medium',
                'ui.show_performance': True,
                'detection.target_count': 1000,
                'detection.buffer_point': 950,
                'detection.roi_default_position': 0.5,
                'detection.min_object_area': 10,
                'detection.max_object_area': 150
            }