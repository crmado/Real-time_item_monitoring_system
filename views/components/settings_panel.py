"""
設定面板組件
包含計數顯示和參數設定
"""

import tkinter as tk
from tkinter import ttk
import logging

from utils.language import get_text
from utils.settings_manager import get_settings_manager


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
    def __init__(self, parent, config_manager=None, system_controller=None):
        """
        初始化設定面板

        Args:
            parent: 父級元件
            config_manager: 配置管理器（已棄用，保留參數是為了向後兼容）
            system_controller: 系統控制器（已棄用，保留參數是為了向後兼容）
        """
        super().__init__(parent)
        
        # 初始化設定管理器
        self.settings_manager = get_settings_manager()
        
        # 初始化變數
        self.target_count = self.settings_manager.get('target_count', 1000)
        self.buffer_point = self.settings_manager.get('buffer_point', 950)
        
        # 初始化回調函數字典
        self.callbacks = {
            'settings_applied': None,
            'reset_count': None
        }
        
        # 創建UI元件
        self.create_widgets()
        
        # 註冊設定變更觀察者
        self._register_settings_observers()
        
        # 記錄初始化完成
        logging.info(f"設定面板初始化完成，目標數量={self.target_count}，緩衝點={self.buffer_point}")

    def _register_settings_observers(self):
        """註冊設定變更觀察者"""
        self.settings_manager.register_observer('target_count', self._on_target_count_changed)
        self.settings_manager.register_observer('buffer_point', self._on_buffer_point_changed)
        logging.info("已註冊設定變更觀察者")

    def _on_target_count_changed(self, key, value):
        """目標數量變更回調"""
        self.target_count = value
        if hasattr(self, 'target_entry'):
            self.target_entry.delete(0, tk.END)
            self.target_entry.insert(0, str(value))
        logging.info(f"目標數量已更新：{value}")

    def _on_buffer_point_changed(self, key, value):
        """緩衝點變更回調"""
        self.buffer_point = value
        if hasattr(self, 'buffer_entry'):
            self.buffer_entry.delete(0, tk.END)
            self.buffer_entry.insert(0, str(value))
        logging.info(f"緩衝點已更新：{value}")

    def load_config(self):
        """從設定管理器載入設定"""
        try:
            # 從設定管理器載入設定
            self.target_count = self.settings_manager.get('target_count', 1000)
            self.buffer_point = self.settings_manager.get('buffer_point', 950)
            logging.info(f"已從設定管理器載入設定：目標數量={self.target_count}，緩衝點={self.buffer_point}")
            return True
        except Exception as e:
            logging.error(f"載入配置時出錯：{str(e)}")
            # 使用默認值
            self.target_count = 1000
            self.buffer_point = 950
            logging.info(f"使用默認設定：目標數量={self.target_count}，緩衝點={self.buffer_point}")
            return False

    def update_ui(self):
        """更新UI元件以反映當前設定"""
        try:
            logging.info(f"更新設定面板UI，目標數量={self.target_count}，緩衝點={self.buffer_point}")
            
            # 更新輸入框的值
            if hasattr(self, 'target_entry'):
                self.target_entry.delete(0, tk.END)
                self.target_entry.insert(0, str(self.target_count))
                
            if hasattr(self, 'buffer_entry'):
                self.buffer_entry.delete(0, tk.END)
                self.buffer_entry.insert(0, str(self.buffer_point))
                
            # 更新語言
            self.update_language()
            
            # 強制更新
            self.update()
            
            logging.info("已更新設定面板UI")
        except Exception as e:
            logging.error(f"更新設定面板UI時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    #==========================================================================
    # 第二部分：UI元件創建
    #==========================================================================
    def create_widgets(self):
        """創建UI元件"""
        # 創建標題
        self.title_label = ttk.Label(
            self,
            text=get_text("settings", "設定"),
            font=("Arial", 14, "bold"),
            style='Title.TLabel'
        )
        self.title_label.pack(pady=(10, 20), anchor=tk.W)
        
        # 創建設定框架
        settings_frame = ttk.Frame(self)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 創建目標數量設定
        target_frame = ttk.Frame(settings_frame)
        target_frame.pack(fill=tk.X, pady=5)
        
        self.target_count_label = ttk.Label(
            target_frame,
            text=get_text("target_count", "預計數量："),
            width=15,
            anchor=tk.W
        )
        self.target_count_label.pack(side=tk.LEFT, padx=5)
        
        self.target_entry = ttk.Entry(target_frame, width=10)
        self.target_entry.insert(0, str(self.target_count))
        self.target_entry.pack(side=tk.LEFT, padx=5)
        
        # 創建緩衝點設定
        buffer_frame = ttk.Frame(settings_frame)
        buffer_frame.pack(fill=tk.X, pady=5)
        
        self.buffer_point_label = ttk.Label(
            buffer_frame,
            text=get_text("buffer_point", "緩衝點："),
            width=15,
            anchor=tk.W
        )
        self.buffer_point_label.pack(side=tk.LEFT, padx=5)
        
        self.buffer_entry = ttk.Entry(buffer_frame, width=10)
        self.buffer_entry.insert(0, str(self.buffer_point))
        self.buffer_entry.pack(side=tk.LEFT, padx=5)
        
        # 創建當前計數顯示
        count_frame = ttk.Frame(settings_frame)
        count_frame.pack(fill=tk.X, pady=5)
        
        self.current_count_label = ttk.Label(
            count_frame,
            text=get_text("current_count", "目前數量："),
            width=15,
            anchor=tk.W
        )
        self.current_count_label.pack(side=tk.LEFT, padx=5)
        
        self.count_label = ttk.Label(
            count_frame,
            text="0",
            width=10,
            anchor=tk.W
        )
        self.count_label.pack(side=tk.LEFT, padx=5)
        
        # 添加重置計數按鈕
        self.reset_count_button = ttk.Button(
            count_frame,
            text=get_text("reset_count", "重置計數"),
            command=self._on_reset_count
        )
        self.reset_count_button.pack(side=tk.RIGHT, padx=5)
        
        # 創建套用設定按鈕
        button_frame = ttk.Frame(settings_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.apply_settings_button = ttk.Button(
            button_frame,
            text=get_text("apply_settings", "套用設定"),
            command=self._on_apply_settings
        )
        self.apply_settings_button.pack(side=tk.RIGHT, padx=5)
        
        # 更新UI以確保所有元件顯示正確的值
        self.update_ui()
        
        logging.info("已創建設定面板UI元件")

    #==========================================================================
    # 第三部分：事件處理
    #==========================================================================
    def _on_reset_count(self):
        """當點擊重置計數按鈕時處理"""
        # 將計數重置為0
        self.update_count(0)
        
        # 如果有系統控制器，更新檢測控制器的計數
        if 'reset_count' in self.callbacks and self.callbacks['reset_count']:
            try:
                self.callbacks['reset_count']()
                logging.info("已調用重置計數回調")
            except Exception as e:
                logging.error(f"調用重置計數回調時出錯：{str(e)}")
        else:
            logging.warning("未註冊重置計數回調")
            
        logging.info("已重置計數為0")

    def _on_apply_settings(self):
        """當點擊套用設定按鈕時處理"""
        # 獲取設定值
        settings = self.get_settings()
        if not settings:
            logging.error("無法套用設定：設定值無效")
            return
            
        # 更新設定管理器
        result = self.settings_manager.update(settings)
        
        if result:
            logging.info(f"已套用設定：{settings}")
            
            # 如果有回調函數，調用它
            if self.callbacks['settings_applied']:
                try:
                    self.callbacks['settings_applied'](settings)
                except Exception as e:
                    logging.error(f"調用設定套用回調函數時出錯：{str(e)}")
        else:
            logging.error("套用設定失敗")

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

            return {
                'target_count': target_count,
                'buffer_point': buffer_point
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
        if hasattr(self, 'apply_settings_button'):
            self.apply_settings_button.configure(text=get_text("apply_settings", "套用設定"))

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