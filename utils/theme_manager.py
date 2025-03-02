"""
主題管理模組
管理應用程式主題切換
"""
from tkinter import ttk


class ThemeManager:
    """主題管理類別"""

    def __init__(self, root, default_theme="light", config_manager=None):
        """
        初始化主題管理器

        Args:
            root: tkinter 根視窗
        """
        self.root = root
        self.current_theme = default_theme
        self._define_themes()
        self.config_manager = config_manager

        # 先嘗試從配置載入主題，如果失敗使用預設主題
        if config_manager:
            loaded_theme = config_manager.get('appearance', 'theme', fallback=default_theme)
            self.current_theme = loaded_theme

        # 初始化時立即套用主題
        self.apply_theme(self.current_theme)

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
            'entry_fg': '#000000',  # 輸入框文字
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
        if hasattr(self, 'config_manager') and self.config_manager:
            self.save_theme_preference(self.config_manager)

        return True

    def save_theme_preference(self, config_manager=None):
        """
        儲存當前主題偏好設定

        Args:
            config_manager: 配置管理器實例
        """
        if config_manager:
            config_manager.set('appearance', 'theme', self.current_theme)
            config_manager.save()

    def load_theme_preference(self, config_manager=None):
        """
        載入並應用儲存的主題偏好設定

        Args:
            config_manager: 配置管理器實例

        Returns:
            str: 載入的主題名稱
        """
        if config_manager:
            theme = config_manager.get('appearance', 'theme', fallback='light')
            self.apply_theme(theme)
            return theme
        return self.current_theme