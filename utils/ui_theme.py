"""
UI主題管理模組
負責定義和管理應用程式的顏色和UI樣式
"""

class UITheme:
    """UI主題類別，定義應用程式的顏色和樣式"""

    # 預設主題顏色
    DEFAULT_COLORS = {
        # 主要顏色
        'primary': '#1976D2',       # 主要強調色（深藍色）
        'secondary': '#43A047',     # 次要強調色（綠色）
        'success': '#2E7D32',       # 成功提示色（深綠色）
        'warning': '#F57C00',       # 警告提示色（橙色）
        'danger': '#D32F2F',        # 危險提示色（紅色）
        'info': '#0288D1',          # 信息提示色（藍色）
        
        # 背景顏色
        'bg_main': '#F5F5F5',       # 主背景色（淺灰色）
        'bg_panel': '#FFFFFF',      # 面板背景色（白色）
        'bg_header': '#1976D2',     # 頂部區域背景色（深藍色）
        'bg_footer': '#E0E0E0',     # 底部區域背景色（灰色）
        'bg_control': '#FFFFFF',    # 控制區域背景色（白色）
        'bg_video': '#000000',      # 視頻區域背景色（黑色）
        'bg_settings': '#FFFFFF',   # 設定區域背景色（白色）
        
        # 文字顏色
        'text_primary': '#212121',  # 主要文字顏色（深灰色）
        'text_secondary': '#757575', # 次要文字顏色（灰色）
        'text_light': '#FFFFFF',    # 淺色文字（白色）
        'text_dark': '#000000',     # 深色文字（黑色）
        
        # 邊框顏色
        'border': '#E0E0E0',        # 邊框顏色（淺灰色）
        'border_light': '#F5F5F5',  # 淺色邊框（更淺的灰色）
        'border_dark': '#BDBDBD',   # 深色邊框（深灰色）
        
        # 按鈕顏色
        'button_bg': '#FFFFFF',     # 按鈕背景色（白色）
        'button_fg': '#212121',     # 按鈕文字顏色（深灰色）
        'button_accent_bg': '#1976D2', # 強調按鈕背景色（深藍色）
        'button_accent_fg': '#FFFFFF', # 強調按鈕文字顏色（白色）
        
        # 輸入框顏色
        'input_bg': '#FFFFFF',      # 輸入框背景色（白色）
        'input_fg': '#212121',      # 輸入框文字顏色（深灰色）
        'input_border': '#E0E0E0',  # 輸入框邊框顏色（淺灰色）
        
        # 狀態顏色
        'hover': '#E3F2FD',         # 懸停效果顏色（淺藍色）
        'active': '#BBDEFB',        # 活動狀態顏色（中藍色）
        'disabled': '#BDBDBD',      # 禁用狀態顏色（灰色）
        
        # 陰影效果
        'shadow': 'rgba(0, 0, 0, 0.1)'  # 陰影顏色（半透明黑色）
    }
    
    # 暗色主題顏色
    DARK_COLORS = {
        # 主要顏色
        'primary': '#0096FF',       # 主要強調色（亮藍色）
        'secondary': '#3CB371',     # 次要強調色（亮綠色）
        'success': '#5CB85C',       # 成功提示色（亮綠色）
        'warning': '#F0AD4E',       # 警告提示色（亮黃色）
        'danger': '#D9534F',        # 危險提示色（亮紅色）
        'info': '#5BC0DE',          # 信息提示色（亮藍色）
        
        # 背景顏色
        'bg_main': '#1E1E1E',       # 主背景色（深灰色）
        'bg_panel': '#252525',      # 面板背景色（深灰色）
        'bg_header': '#333333',     # 頂部區域背景色（深灰色）
        'bg_footer': '#333333',     # 底部區域背景色（深灰色）
        'bg_control': '#2A2A2A',    # 控制區域背景色（深灰色）
        'bg_video': '#000000',      # 視頻區域背景色（黑色）
        'bg_settings': '#2D2D2D',   # 設定區域背景色（深灰色）
        
        # 文字顏色
        'text_primary': '#FFFFFF',  # 主要文字顏色（白色）
        'text_secondary': '#AAAAAA', # 次要文字顏色（淺灰色）
        'text_light': '#FFFFFF',    # 淺色文字（白色）
        'text_dark': '#CCCCCC',     # 深色文字（淺灰色）
        
        # 邊框顏色
        'border': '#444444',        # 邊框顏色（深灰色）
        'border_light': '#555555',  # 淺色邊框（灰色）
        'border_dark': '#222222',   # 深色邊框（深灰色）
        
        # 按鈕顏色
        'button_bg': '#333333',     # 按鈕背景色（深灰色）
        'button_fg': '#FFFFFF',     # 按鈕文字顏色（白色）
        'button_accent_bg': '#0096FF', # 強調按鈕背景色（亮藍色）
        'button_accent_fg': '#FFFFFF', # 強調按鈕文字顏色（白色）
        
        # 輸入框顏色
        'input_bg': '#2A2A2A',      # 輸入框背景色（深灰色）
        'input_fg': '#FFFFFF',      # 輸入框文字顏色（白色）
        'input_border': '#444444',  # 輸入框邊框顏色（深灰色）
    }
    
    def __init__(self, theme_name='light'):
        """
        初始化UI主題
        
        Args:
            theme_name: 主題名稱，'light'或'dark'
        """
        self.theme_name = theme_name
        self.colors = self.DEFAULT_COLORS.copy() if theme_name == 'light' else self.DARK_COLORS.copy()
    
    def get_color(self, color_name):
        """
        獲取指定顏色
        
        Args:
            color_name: 顏色名稱
            
        Returns:
            str: 顏色代碼
        """
        return self.colors.get(color_name, '#000000')  # 默認返回黑色
    
    def set_theme(self, theme_name):
        """
        設置主題
        
        Args:
            theme_name: 主題名稱，'light'或'dark'
            
        Returns:
            bool: 是否成功設置
        """
        if theme_name not in ['light', 'dark']:
            return False
            
        self.theme_name = theme_name
        self.colors = self.DEFAULT_COLORS.copy() if theme_name == 'light' else self.DARK_COLORS.copy()
        return True
    
    def get_all_colors(self):
        """
        獲取所有顏色
        
        Returns:
            dict: 顏色字典
        """
        return self.colors.copy() 