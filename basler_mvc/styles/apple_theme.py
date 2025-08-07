"""
Apple風格主題定義
統一管理所有視覺樣式，實現類似CSS的設計分離概念
"""

class AppleTheme:
    """Apple風格主題配置類"""
    
    # ==================== 色彩系統 ====================
    class Colors:
        """Apple標準色彩系統"""
        
        # 主要顏色 - 🎨 優化對比度版本
        PRIMARY_BLUE = '#0051D5'        # 優化後Apple藍 - 主要按鈕 (對比度6.69:1)
        PRIMARY_BLUE_HOVER = '#0040B8'  # 懸停狀態 (更深)
        PRIMARY_BLUE_PRESSED = '#003399' # 按下狀態
        
        # 成功/狀態顏色
        SUCCESS_GREEN = '#34c759'       # Apple綠 - 成功狀態
        WARNING_ORANGE = '#ff9500'      # Apple橙 - 警告
        ERROR_RED = '#ff3b30'          # Apple紅 - 錯誤/強調
        INFO_PURPLE = '#af52de'        # Apple紫 - 信息
        
        # 背景顏色 - 🎨 優化統一版本
        BACKGROUND_PRIMARY = '#F8F9FA'  # 主背景 - 統一淺灰 (與分析器一致)
        BACKGROUND_CARD = '#FFFFFF'     # 卡片背景 - 純白
        BACKGROUND_SECONDARY = '#F2F2F7' # 次要背景
        BACKGROUND_INPUT = '#FFFFFF'    # 輸入框背景
        
        # 文字顏色 - 🎨 優化對比度版本
        TEXT_PRIMARY = '#1d1d1f'       # 主要文字 - 深色
        TEXT_SECONDARY = '#6D6D70'     # 次要文字 - 優化後中灰 (對比度5.16:1)
        TEXT_TERTIARY = '#c7c7cc'      # 三級文字 - 淺灰
        TEXT_ACCENT = '#0051D5'        # 強調文字 - 優化後藍色
        
        # 邊框顏色 - 🎨 優化對比度版本 v3 (達到WCAG標準)
        BORDER_LIGHT = '#6D6D70'       # 淺色邊框 - 符合AA標準 (對比度5.16:1)
        BORDER_MEDIUM = '#48484A'      # 中等邊框 - 更深
        BORDER_DARK = '#2C2C2E'        # 深色邊框 - 最深
        
        # 互動狀態顏色
        HOVER_BACKGROUND = '#f2f2f7'   # 懸停背景
        ACTIVE_BACKGROUND = '#e5e5ea'  # 激活背景
        DISABLED_BACKGROUND = '#f2f2f7' # 禁用背景
        DISABLED_TEXT = '#c7c7cc'      # 禁用文字
    
    # ==================== 字體系統 ====================
    class Typography:
        """字體系統"""
        
        # 字體族
        FONT_FAMILY_PRIMARY = 'SF Pro Display'
        FONT_FAMILY_FALLBACK = 'Segoe UI'
        FONT_FAMILY_MONO = 'SF Mono'
        FONT_FAMILY_MONO_FALLBACK = 'Consolas'
        
        # 字體大小 (針對高解析度螢幕優化，提高可讀性)
        FONT_SIZE_CAPTION = 12         # 說明文字 (增大3px)
        FONT_SIZE_SMALL = 14           # 小字體 (增大3px)
        FONT_SIZE_BODY = 16            # 正文 (增大3px)
        FONT_SIZE_SUBHEADLINE = 18     # 副標題 (增大3px)
        FONT_SIZE_HEADLINE = 20        # 標題 (增大3px)
        FONT_SIZE_TITLE3 = 23          # 三級標題 (增大3px)
        FONT_SIZE_TITLE2 = 25          # 二級標題 (增大3px)
        FONT_SIZE_TITLE1 = 31          # 一級標題 (增大3px)
        FONT_SIZE_LARGE_TITLE = 37     # 大標題 (增大3px)
        FONT_SIZE_DISPLAY = 43         # 顯示文字 (增大3px)
        
        # 字體權重 (tkinter支持的權重)
        FONT_WEIGHT_LIGHT = 'normal'      # tkinter沒有light，使用normal
        FONT_WEIGHT_REGULAR = 'normal'
        FONT_WEIGHT_MEDIUM = 'normal'     # tkinter沒有medium，使用normal
        FONT_WEIGHT_SEMIBOLD = 'bold'     # tkinter沒有semibold，使用bold
        FONT_WEIGHT_BOLD = 'bold'
        
        # 預定義字體組合
        @classmethod
        def get_font(cls, size, weight='normal', family='primary'):
            """獲取字體配置"""
            if family == 'primary':
                font_family = cls.FONT_FAMILY_PRIMARY
            elif family == 'mono':
                font_family = cls.FONT_FAMILY_MONO
            else:
                font_family = cls.FONT_FAMILY_FALLBACK
            
            return (font_family, size, weight)
    
    # ==================== 尺寸系統 ====================
    class Dimensions:
        """尺寸系統"""
        
        # 邊距 (遵循8px網格)
        SPACING_XS = 4      # 極小間距
        SPACING_SM = 8      # 小間距
        SPACING_MD = 12     # 中等間距
        SPACING_LG = 16     # 大間距
        SPACING_XL = 20     # 極大間距
        SPACING_XXL = 24    # 超大間距
        SPACING_XXXL = 32   # 巨大間距
        
        # 組件尺寸
        BUTTON_HEIGHT_SM = 28    # 小按鈕高度
        BUTTON_HEIGHT_MD = 32    # 中按鈕高度
        BUTTON_HEIGHT_LG = 40    # 大按鈕高度
        
        INPUT_HEIGHT = 36        # 輸入框高度
        TOOLBAR_HEIGHT = 60      # 工具欄高度
        STATUSBAR_HEIGHT = 30    # 狀態欄高度
        
        # 圓角
        BORDER_RADIUS_XS = 4     # 極小圓角
        BORDER_RADIUS_SM = 6     # 小圓角
        BORDER_RADIUS_MD = 8     # 中等圓角
        BORDER_RADIUS_LG = 12    # 大圓角
        BORDER_RADIUS_XL = 16    # 極大圓角
        
        # 邊框寬度
        BORDER_WIDTH_THIN = 0.5  # 細邊框
        BORDER_WIDTH_NORMAL = 1  # 普通邊框
        BORDER_WIDTH_THICK = 2   # 粗邊框
        
        # 陰影
        SHADOW_SM = "0 1px 3px rgba(0,0,0,0.1)"      # 小陰影
        SHADOW_MD = "0 4px 6px rgba(0,0,0,0.1)"      # 中陰影
        SHADOW_LG = "0 10px 15px rgba(0,0,0,0.1)"    # 大陰影
        SHADOW_INSET = "inset 0 1px 2px rgba(0,0,0,0.05)" # 內陰影
    
    # ==================== 預定義樣式 ====================
    class Presets:
        """預定義樣式組合"""
        
        @staticmethod
        def primary_button():
            """主要按鈕樣式"""
            return {
                'background': AppleTheme.Colors.PRIMARY_BLUE,
                'foreground': AppleTheme.Colors.BACKGROUND_CARD,
                'font': AppleTheme.Typography.get_font(
                    AppleTheme.Typography.FONT_SIZE_BODY, 
                    AppleTheme.Typography.FONT_WEIGHT_REGULAR
                ),
                'padding': (AppleTheme.Dimensions.SPACING_LG, AppleTheme.Dimensions.SPACING_SM),
                'relief': 'flat',
                'borderwidth': 0,
                'focuscolor': 'none'
            }
        
        @staticmethod
        def secondary_button():
            """次要按鈕樣式"""
            return {
                'background': AppleTheme.Colors.HOVER_BACKGROUND,
                'foreground': AppleTheme.Colors.PRIMARY_BLUE,
                'font': AppleTheme.Typography.get_font(
                    AppleTheme.Typography.FONT_SIZE_BODY, 
                    AppleTheme.Typography.FONT_WEIGHT_REGULAR
                ),
                'padding': (AppleTheme.Dimensions.SPACING_LG, AppleTheme.Dimensions.SPACING_SM),
                'relief': 'flat',
                'borderwidth': 0,
                'focuscolor': 'none'
            }
        
        @staticmethod
        def card_frame():
            """卡片框架樣式"""
            return {
                'background': AppleTheme.Colors.BACKGROUND_CARD,
                'relief': 'solid',
                'borderwidth': AppleTheme.Dimensions.BORDER_WIDTH_THIN,
                'lightcolor': AppleTheme.Colors.BORDER_LIGHT,
                'darkcolor': AppleTheme.Colors.BORDER_LIGHT,
                'padding': (AppleTheme.Dimensions.SPACING_XL, AppleTheme.Dimensions.SPACING_LG)
            }
        
        @staticmethod
        def label_title():
            """標題標籤樣式"""
            return {
                'background': AppleTheme.Colors.BACKGROUND_CARD,
                'foreground': AppleTheme.Colors.TEXT_PRIMARY,
                'font': AppleTheme.Typography.get_font(
                    AppleTheme.Typography.FONT_SIZE_HEADLINE,
                    AppleTheme.Typography.FONT_WEIGHT_BOLD
                )
            }
        
        @staticmethod
        def label_body():
            """正文標籤樣式"""
            return {
                'background': AppleTheme.Colors.BACKGROUND_CARD,
                'foreground': AppleTheme.Colors.TEXT_PRIMARY,
                'font': AppleTheme.Typography.get_font(
                    AppleTheme.Typography.FONT_SIZE_BODY
                )
            }
        
        @staticmethod
        def label_caption():
            """說明文字樣式"""
            return {
                'background': AppleTheme.Colors.BACKGROUND_CARD,
                'foreground': AppleTheme.Colors.TEXT_SECONDARY,
                'font': AppleTheme.Typography.get_font(
                    AppleTheme.Typography.FONT_SIZE_SMALL
                )
            }
        
        @staticmethod
        def progress_bar():
            """進度條樣式"""
            return {
                'background': AppleTheme.Colors.PRIMARY_BLUE,
                'troughcolor': AppleTheme.Colors.HOVER_BACKGROUND,
                'borderwidth': 0,
                'lightcolor': AppleTheme.Colors.PRIMARY_BLUE,
                'darkcolor': AppleTheme.Colors.PRIMARY_BLUE
            }
        
        @staticmethod
        def scale_slider():
            """滑塊樣式"""
            return {
                'background': AppleTheme.Colors.BACKGROUND_CARD,
                'troughcolor': AppleTheme.Colors.HOVER_BACKGROUND,
                'borderwidth': 0,
                'sliderrelief': 'flat',
                'sliderlength': 20,
                'activebackground': AppleTheme.Colors.PRIMARY_BLUE
            }
    
    # ==================== 狀態樣式 ====================
    class States:
        """交互狀態樣式"""
        
        @staticmethod
        def button_states():
            """按鈕狀態樣式"""
            return {
                'primary': {
                    'active': {
                        'background': AppleTheme.Colors.PRIMARY_BLUE_HOVER
                    },
                    'pressed': {
                        'background': AppleTheme.Colors.PRIMARY_BLUE_PRESSED
                    },
                    'disabled': {
                        'background': AppleTheme.Colors.DISABLED_BACKGROUND,
                        'foreground': AppleTheme.Colors.DISABLED_TEXT
                    }
                },
                'secondary': {
                    'active': {
                        'background': AppleTheme.Colors.ACTIVE_BACKGROUND
                    },
                    'pressed': {
                        'background': AppleTheme.Colors.BORDER_LIGHT
                    },
                    'disabled': {
                        'background': AppleTheme.Colors.DISABLED_BACKGROUND,
                        'foreground': AppleTheme.Colors.DISABLED_TEXT
                    }
                }
            }
        
        @staticmethod
        def status_colors():
            """狀態指示顏色"""
            return {
                'connected': AppleTheme.Colors.SUCCESS_GREEN,
                'disconnected': AppleTheme.Colors.ERROR_RED,
                'warning': AppleTheme.Colors.WARNING_ORANGE,
                'info': AppleTheme.Colors.INFO_PURPLE,
                'processing': AppleTheme.Colors.PRIMARY_BLUE
            }
    
    # ==================== 動畫配置 ====================
    class Animations:
        """動畫和過渡效果配置"""
        
        DURATION_FAST = 150      # 快速動畫 (毫秒)
        DURATION_NORMAL = 250    # 普通動畫
        DURATION_SLOW = 350      # 慢速動畫
        
        EASING_EASE_OUT = 'ease-out'
        EASING_EASE_IN = 'ease-in'
        EASING_EASE_IN_OUT = 'ease-in-out'