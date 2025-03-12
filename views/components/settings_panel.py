"""
設定面板組件
包含計數顯示和參數設定
"""

import tkinter as tk
from tkinter import ttk
import logging

from utils.language import get_text


class SettingsPanel(ttk.Frame):
    """
    /// 設定面板類別
    /// 功能結構：
    /// 第一部分：基本屬性和初始化
    /// 第二部分：UI元件創建
    /// 第三部分：事件處理
    /// 第四部分：數據管理
    /// 第五部分：工具方法
    """

    #==========================================================================
    # 第一部分：基本屬性和初始化
    #==========================================================================
    def __init__(self, parent, config_manager=None, **kwargs):
        """
        初始化設定面板

        Args:
            parent: 父級視窗
            config_manager: 配置管理器實例
            **kwargs: 其他參數
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.config_manager = config_manager
        self.callbacks = {
            'settings_applied': None
        }

        # 默認值 - 這些只是初始預設值，實際會從配置中讀取
        self.target_count = 1000
        self.buffer_point = 950

        # 創建UI元件
        self.create_widgets()
        
        # 載入配置 - 移到UI元件創建後，確保可以更新UI
        if self.config_manager:
            self.load_config()
        else:
            # 如果沒有配置管理器，嘗試從系統控制器獲取設定
            self.load_from_system_controller()

    def load_config(self):
        """載入配置"""
        if self.config_manager:
            # 嘗試從配置管理器獲取設定值
            # 先檢查是否有帶前綴的鍵名
            if self.config_manager.has('detection.target_count'):
                self.target_count = self.config_manager.get('detection.target_count', 1000)
            # 如果沒有，嘗試不帶前綴的鍵名
            elif self.config_manager.has('target_count'):
                self.target_count = self.config_manager.get('target_count', 1000)
            
            # 同樣處理緩衝點
            if self.config_manager.has('detection.buffer_point'):
                self.buffer_point = self.config_manager.get('detection.buffer_point', 950)
            elif self.config_manager.has('buffer_point'):
                self.buffer_point = self.config_manager.get('buffer_point', 950)
                
            logging.info(f"從配置管理器載入設定：目標數量={self.target_count}，緩衝點={self.buffer_point}")
            
            # 更新UI
            self.update_ui()

    def update_ui(self):
        """更新UI元件的值以反映當前設定"""
        try:
            # 更新預計數量輸入框
            if hasattr(self, 'target_entry'):
                current_value = self.target_entry.get()
                if current_value != str(self.target_count):
                    self.target_entry.delete(0, tk.END)
                    self.target_entry.insert(0, str(self.target_count))
                    # 強制更新輸入框
                    self.target_entry.update()
                
            # 更新緩衝點輸入框
            if hasattr(self, 'buffer_entry'):
                current_value = self.buffer_entry.get()
                if current_value != str(self.buffer_point):
                    self.buffer_entry.delete(0, tk.END)
                    self.buffer_entry.insert(0, str(self.buffer_point))
                    # 強制更新輸入框
                    self.buffer_entry.update()
                
            # 強制更新整個面板
            self.update()
            
            logging.info(f"已更新設定面板UI：目標數量={self.target_count}，緩衝點={self.buffer_point}")
            return True
        except Exception as e:
            logging.error(f"更新設定面板UI時出錯：{str(e)}")
            return False

    def load_from_system_controller(self):
        """從系統控制器載入設定"""
        try:
            # 嘗試獲取主視窗的系統控制器
            if hasattr(self.parent, 'system_controller'):
                controller = self.parent.system_controller
                
                # 從系統控制器的設定中獲取值
                if hasattr(controller, 'settings'):
                    self.target_count = controller.settings.get('target_count', 1000)
                    self.buffer_point = controller.settings.get('buffer_point', 950)
                    logging.info(f"從系統控制器載入設定：目標數量={self.target_count}，緩衝點={self.buffer_point}")
                    
                    # 更新UI
                    self.update_ui()
                else:
                    logging.warning("系統控制器沒有設定屬性")
            else:
                logging.warning("無法從主視窗獲取系統控制器")
        except Exception as e:
            logging.error(f"從系統控制器載入設定時出錯：{str(e)}")
            # 使用默認值

    #==========================================================================
    # 第二部分：UI元件創建
    #==========================================================================
    def create_widgets(self):
        """創建設定面板組件"""
        # 當前計數顯示
        self.create_counter_section()

        # 預計數量設定
        self.create_target_section()

        # 緩衝點設定
        self.create_buffer_section()

        # 設定按鈕
        self.create_settings_button()

    def create_counter_section(self):
        """創建計數器區段"""
        count_frame = ttk.Frame(self)
        count_frame.grid(row=0, column=0, pady=5, sticky=tk.EW)

        ttk.Label(
            count_frame,
            text=get_text("current_count", "目前數量："),
            style='Counter.TLabel'
        ).grid(row=0, column=0)

        self.count_label = ttk.Label(
            count_frame,
            text="0",
            style='CounterNum.TLabel'
        )
        self.count_label.grid(row=0, column=1)

    def create_target_section(self):
        """創建目標數量設定區段"""
        target_frame = ttk.Frame(self)
        target_frame.grid(row=1, column=0, pady=5, sticky=tk.EW)

        ttk.Label(target_frame, text=get_text("target_count", "預計數量：")).grid(row=0, column=0)

        self.target_entry = ttk.Entry(target_frame, width=10)
        self.target_entry.grid(row=0, column=1, padx=5)
        self.target_entry.insert(0, str(self.target_count))

    def create_buffer_section(self):
        """創建緩衝點設定區段"""
        buffer_frame = ttk.Frame(self)
        buffer_frame.grid(row=2, column=0, pady=5, sticky=tk.EW)

        ttk.Label(buffer_frame, text=get_text("buffer_point", "緩衝點：")).grid(row=0, column=0)

        self.buffer_entry = ttk.Entry(buffer_frame, width=10)
        self.buffer_entry.grid(row=0, column=1, padx=5)
        self.buffer_entry.insert(0, str(self.buffer_point))

    def create_settings_button(self):
        """創建設定按鈕"""
        self.apply_settings_button = ttk.Button(
            self,
            text=get_text("apply_settings", "套用設定"),
            style='Accent.TButton',
            command=self._on_apply_settings
        )
        self.apply_settings_button.grid(row=4, column=0, pady=10)

    #==========================================================================
    # 第三部分：事件處理
    #==========================================================================
    def _on_apply_settings(self):
        """當點擊套用設定按鈕時處理"""
        if self.callbacks['settings_applied']:
            # 獲取設定值
            settings = self.get_settings()
            if settings:
                # 調用回調函數，傳遞設定值
                result = self.callbacks['settings_applied'](settings)
                
                if result:
                    # 更新自身的設定值
                    self.target_count = settings['target_count']
                    self.buffer_point = settings['buffer_point']
                    
                    # 重新創建UI元件，確保完全重新繪製
                    self.recreate_ui()
                    
                    logging.info(f"已套用設定並更新UI：{settings}")
                else:
                    logging.error("套用設定失敗")
            else:
                logging.error("無法套用設定：設定值無效")

    #==========================================================================
    # 第四部分：數據管理
    #==========================================================================
    def update_count(self, count):
        """
        更新計數顯示

        Args:
            count: 當前計數
        """
        self.count_label.configure(text=str(count))

    def get_settings(self):
        """
        獲取設定值

        Returns:
            dict: 設定值字典
        """
        try:
            target_count = int(self.target_entry.get())
            buffer_point = int(self.buffer_entry.get())

            # 驗證設定
            if buffer_point >= target_count:
                logging.error(get_text("error_buffer_target", "緩衝點必須小於預計數量"))
                return None

            if buffer_point < 0 or target_count < 0:
                logging.error(get_text("error_negative", "設定值必須為正數"))
                return None

            # 原本返回的是帶前綴的鍵名，改為直接返回鍵名
            return {
                'target_count': target_count,
                'buffer_point': buffer_point
                # 使用一致的格式，不使用 'detection.target_count' 格式
            }
        except ValueError:
            logging.error(get_text("error_invalid_number", "設定值必須為整數"))
            return None

    #==========================================================================
    # 第五部分：工具方法
    #==========================================================================
    def set_callback(self, event_name, callback):
        """
        設置回調函數

        Args:
            event_name: 事件名稱
            callback: 回調函數
        """
        self.callbacks[event_name] = callback

    def update_language(self):
        """更新組件語言"""
        # 更新文字標籤
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label) and not child == self.count_label:
                        if child.cget('text') == "預計數量：" or child.cget('text') == "Estimated Quantity:":
                            child.configure(text=get_text("target_count", "預計數量："))
                        elif child.cget('text') == "緩衝點：" or child.cget('text') == "Buffer Point:":
                            child.configure(text=get_text("buffer_point", "緩衝點："))
                        elif child.cget('text') == "目前數量：" or child.cget('text') == "Current Count:":
                            child.configure(text=get_text("current_count", "目前數量："))

        # 更新按鈕文字
        self.apply_settings_button.configure(text=get_text("apply_settings", "套用設定"))

    def update_ui_text(self):
        """更新設定面板中的所有文字"""
        # 更新標題
        if hasattr(self, 'title_label'):
            self.title_label.configure(text=get_text("settings", "設定"))
            
        # 更新當前計數標籤
        if hasattr(self, 'current_count_label'):
            self.current_count_label.configure(text=get_text("current_count", "目前數量："))
            
        # 更新預計數量標籤
        if hasattr(self, 'target_count_label'):
            self.target_count_label.configure(text=get_text("target_count", "預計數量："))
            
        # 更新緩衝點標籤
        if hasattr(self, 'buffer_point_label'):
            self.buffer_point_label.configure(text=get_text("buffer_point", "緩衝點："))
            
        # 更新套用設定按鈕
        if hasattr(self, 'apply_button'):
            self.apply_button.configure(text=get_text("apply_settings", "套用設定"))

    def recreate_ui(self):
        """重新創建UI元件，確保完全重新繪製"""
        # 保存回調函數
        saved_callbacks = self.callbacks.copy()
        
        # 移除所有現有的子元件
        for widget in self.winfo_children():
            widget.destroy()
            
        # 重新創建UI元件
        self.create_widgets()
        
        # 恢復回調函數
        self.callbacks = saved_callbacks
        
        # 強制更新
        self.update()
        
        logging.info("已重新創建設定面板UI元件")