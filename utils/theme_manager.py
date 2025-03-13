"""
主題管理模組
管理應用程式主題切換，使用觀察者模式通知主題變更
"""
from tkinter import ttk
import logging
from typing import Dict, Any, List, Callable, Optional


class ThemeManager:
    """主題管理類別"""

    def __init__(self, root, default_theme="light", config_manager=None):
        """
        初始化主題管理器

        Args:
            root: tkinter 根視窗
            default_theme: 預設主題
            config_manager: 配置管理器（已棄用，保留參數是為了向後兼容）
        """
        self.root = root
        self.current_theme = default_theme
        self.observers: List[Callable[[str], None]] = []  # 觀察者列表，用於通知主題變更
        self._define_themes()
        
        # 從設定管理器載入主題
        try:
            from utils.settings_manager import get_settings_manager
            settings_manager = get_settings_manager()
            loaded_theme = settings_manager.get('theme', default_theme)
            self.current_theme = loaded_theme
        except Exception as e:
            logging.warning(f"從設定管理器載入主題時出錯：{str(e)}，使用預設主題：{default_theme}")
            # 向後兼容：嘗試從配置管理器載入
            if config_manager:
                loaded_theme = config_manager.get('ui.theme', fallback=default_theme)
                self.current_theme = loaded_theme

        # 初始化時立即套用主題
        self.apply_theme(self.current_theme)
        logging.info(f"主題管理器初始化完成，當前主題：{self.current_theme}")

    def _define_themes(self):
        """定義亮色和暗色主題樣式"""
        # 定義亮色主題
        self.light_theme = {
            'bg': '#f0f0f0',
            'fg': '#000000',
            'button_bg': '#e0e0e0',
            'button_fg': '#000000',
            'accent': '#0078d7',
            'accent_fg': '#ffffff',
            'entry_bg': '#ffffff',
            'entry_fg': '#000000',
            'panel_bg': '#f5f5f5'
        }

        # 定義暗色主題
        self.dark_theme = {
            'bg': '#1e1e1e',  # 更深的背景色
            'fg': '#ffffff',  # 更亮的文字顏色
            'button_bg': '#333333',  # 按鈕背景
            'button_fg': '#ffffff',  # 按鈕文字
            'accent': '#0096ff',  # 更亮的藍色調
            'accent_fg': '#ffffff',  # 強調按鈕文字
            'entry_bg': '#2a2a2a',  # 輸入框背景
            'entry_fg': '#ffffff',  # 輸入框文字
            'panel_bg': '#252525'  # 面板背景
        }

    def apply_theme(self, theme_name):
        """
        套用指定主題

        Args:
            theme_name: 主題名稱 ('light' 或 'dark')

        Returns:
            bool: 是否成功套用
        """
        if theme_name not in ["light", "dark"]:
            return False

        # 如果主題沒有變更，不重新應用
        if self.current_theme == theme_name and hasattr(self, '_theme_applied'):
            return True

        old_theme = self.current_theme
        self.current_theme = theme_name
        theme = self.light_theme if theme_name == "light" else self.dark_theme

        # 設定 ttk 樣式
        style = ttk.Style(self.root)
        style.theme_use('clam')  # 使用較為彈性的基礎主題

        # 設定一般元件樣式
        style.configure('TFrame', background=theme['bg'])
        style.configure('TLabel', background=theme['bg'], foreground=theme['fg'])
        style.configure('TButton', background=theme['button_bg'], foreground=theme['button_fg'])
        style.configure('TEntry', background=theme['entry_bg'], foreground=theme['entry_fg'])

        # 完善下拉選單樣式設定
        style.configure('TCombobox',
                        background=theme['entry_bg'],
                        foreground=theme['entry_fg'],
                        fieldbackground=theme['entry_bg'])

        # 設定下拉選單各狀態的樣式映射
        style.map('TCombobox',
                  fieldbackground=[('readonly', theme['entry_bg'])],
                  foreground=[('readonly', theme['entry_fg'])],
                  selectbackground=[('readonly', theme['accent'])],
                  selectforeground=[('readonly', theme['accent_fg'])])

        # 配置下拉清單顏色 (popup menu)
        self.root.option_add('*TCombobox*Listbox.background', theme['entry_bg'])
        self.root.option_add('*TCombobox*Listbox.foreground', theme['entry_fg'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', theme['accent'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', theme['accent_fg'])

        style.configure('TCheckbutton', background=theme['bg'], foreground=theme['fg'])
        style.configure('TRadiobutton', background=theme['bg'], foreground=theme['fg'])
        style.configure('TSpinbox', background=theme['entry_bg'], foreground=theme['entry_fg'])

        # 設定強調按鈕樣式
        style.configure('Accent.TButton', background=theme['accent'], foreground=theme['accent_fg'])

        # 設定 tk 元件樣式
        self.root.configure(background=theme['bg'])

        # 標記主題已被應用
        self._theme_applied = True

        # 自動保存主題設定
        try:
            from utils.settings_manager import get_settings_manager
            settings_manager = get_settings_manager()
            settings_manager.set('theme', theme_name)
        except Exception as e:
            logging.warning(f"保存主題設定時出錯：{str(e)}")
            # 向後兼容：嘗試使用配置管理器保存
            if hasattr(self, 'config_manager') and self.config_manager:
                self.save_theme_preference(self.config_manager)
        
        # 如果主題確實變更了，通知觀察者
        if old_theme != theme_name:
            self._notify_observers(theme_name)
            
        return True

    def save_theme_preference(self, config_manager=None):
        """
        儲存當前主題偏好設定（向後兼容方法）

        Args:
            config_manager: 配置管理器實例
        """
        if config_manager:
            config_manager.set('ui.theme', self.current_theme)
            config_manager.save()

    def load_theme_preference(self, config_manager=None):
        """
        載入並應用儲存的主題偏好設定（向後兼容方法）

        Args:
            config_manager: 配置管理器實例

        Returns:
            str: 載入的主題名稱
        """
        if config_manager:
            theme = config_manager.get('ui.theme', fallback='light')
            self.apply_theme(theme)
            return theme
        return self.current_theme
        
    def get_main_color(self):
        """
        獲取當前主題的主要背景色

        Returns:
            str: 背景色代碼
        """
        theme = self.light_theme if self.current_theme == "light" else self.dark_theme
        return theme['bg']
        
    def get_theme(self):
        """
        獲取當前主題名稱

        Returns:
            str: 主題名稱
        """
        return self.current_theme
        
    def register_observer(self, callback: Callable[[str], None]):
        """
        註冊主題變更觀察者

        Args:
            callback: 回調函數，接收主題名稱作為參數
        """
        if callback not in self.observers:
            self.observers.append(callback)
            logging.info(f"已註冊主題變更觀察者")

    def unregister_observer(self, callback: Callable[[str], None]):
        """
        取消註冊主題變更觀察者

        Args:
            callback: 回調函數
        """
        if callback in self.observers:
            self.observers.remove(callback)
            logging.info(f"已取消註冊主題變更觀察者")

    def _notify_observers(self, theme_name: str):
        """
        通知主題變更觀察者

        Args:
            theme_name: 新的主題名稱
        """
        for callback in self.observers:
            try:
                callback(theme_name)
            except Exception as e:
                logging.error(f"通知主題變更觀察者時出錯：{str(e)}")


# 全局主題管理器實例
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager(root=None) -> Optional[ThemeManager]:
    """
    獲取全局主題管理器實例
    
    Args:
        root: tkinter 根視窗，如果是第一次調用且 _theme_manager 為 None，則必須提供

    Returns:
        ThemeManager: 主題管理器實例
    """
    global _theme_manager
    if _theme_manager is None:
        if root is None:
            logging.error("首次獲取主題管理器時必須提供 root 參數")
            return None
        _theme_manager = ThemeManager(root)
    return _theme_manager


def apply_theme(theme_name, root=None):
    """
    便捷函數：套用指定主題
    
    Args:
        theme_name: 主題名稱
        root: tkinter 根視窗，如果是第一次調用且 _theme_manager 為 None，則必須提供
        
    Returns:
        bool: 是否成功套用
    """
    theme_manager = get_theme_manager(root)
    if theme_manager:
        return theme_manager.apply_theme(theme_name)
    return False


def get_current_theme(root=None):
    """
    便捷函數：獲取當前主題名稱
    
    Args:
        root: tkinter 根視窗，如果是第一次調用且 _theme_manager 為 None，則必須提供
        
    Returns:
        str: 主題名稱
    """
    theme_manager = get_theme_manager(root)
    if theme_manager:
        return theme_manager.get_theme()
    return "light"  # 默認主題


def register_theme_observer(callback: Callable[[str], None], root=None):
    """
    便捷函數：註冊主題變更觀察者
    
    Args:
        callback: 回調函數，接收主題名稱作為參數
        root: tkinter 根視窗，如果是第一次調用且 _theme_manager 為 None，則必須提供
    """
    theme_manager = get_theme_manager(root)
    if theme_manager:
        theme_manager.register_observer(callback)


def unregister_theme_observer(callback: Callable[[str], None], root=None):
    """
    便捷函數：取消註冊主題變更觀察者
    
    Args:
        callback: 回調函數
        root: tkinter 根視窗，如果是第一次調用且 _theme_manager 為 None，則必須提供
    """
    theme_manager = get_theme_manager(root)
    if theme_manager:
        theme_manager.unregister_observer(callback)