"""
Liquid Glass 主題 - 受Apple 2025年最新設計理念啟發
實現半透明、動態反應、玻璃質感的現代UI設計
"""

class LiquidGlassTheme:
    """Liquid Glass 主題配置類 - Apple 2025年設計語言"""
    
    # ==================== Liquid Glass 色彩系統 ====================
    class Colors:
        """Liquid Glass 半透明色彩系統"""
        
        # 主要玻璃色調 - tkinter兼容的RGB格式
        GLASS_PRIMARY = '#007aff'          # Apple藍
        GLASS_PRIMARY_LIGHT = '#339bff'    # 淺色玻璃藍
        GLASS_PRIMARY_DARK = '#0056cc'     # 深色玻璃藍
        
        # 玻璃表面色彩 - 模擬透明效果
        GLASS_SURFACE_LIGHT = '#f8f9fa'    # 極淺玻璃白
        GLASS_SURFACE_MEDIUM = '#f0f0f2'   # 中等玻璃白
        GLASS_SURFACE_HEAVY = '#e8e8ea'    # 濃重玻璃白
        
        # 環境反射色彩
        REFLECTION_WARM = '#fef9e7'        # 暖色反射
        REFLECTION_COOL = '#e7f7ff'        # 冷色反射
        REFLECTION_NEUTRAL = '#f5f5f7'     # 中性反射
        
        # 動態漸變背景
        BACKGROUND_GLASS = '#f8f9fa'       # 玻璃質背景
        BACKGROUND_FROSTED = '#f9fafb'     # 磨砂玻璃
        BACKGROUND_CRYSTAL = '#ffffff'     # 水晶質感
        
        # 智能適應色彩 - 根據內容動態調整
        ADAPTIVE_LIGHT = '#fafafa'         # 極淺適應色
        ADAPTIVE_MEDIUM = '#f5f5f5'        # 中等適應色
        ADAPTIVE_HEAVY = '#f0f0f0'         # 濃重適應色
        
        # 高對比文字系統
        TEXT_GLASS_PRIMARY = '#1c1c1e'     # 玻璃上主要文字
        TEXT_GLASS_SECONDARY = '#3a3a3c'   # 玻璃上次要文字
        TEXT_GLASS_ACCENT = '#007aff'      # 玻璃上強調文字
        
        # 互動狀態的玻璃效果
        HOVER_GLASS = '#f0f0f2'            # 懸停玻璃效果
        ACTIVE_GLASS = '#e6f3ff'           # 激活玻璃效果
        FOCUS_GLASS = '#cce7ff'            # 聚焦玻璃效果
        
        # 層次化陰影系統
        SHADOW_GLASS_SOFT = '#f0f0f0'      # 柔和玻璃陰影
        SHADOW_GLASS_MEDIUM = '#e0e0e0'    # 中等玻璃陰影
        SHADOW_GLASS_DEEP = '#d0d0d0'      # 深度玻璃陰影
    
    # ==================== 動態字體系統 ====================
    class Typography:
        """動態響應字體系統"""
        
        # SF Pro Display 系列 - Apple 2025標準
        FONT_FAMILY_DISPLAY = 'SF Pro Display'
        FONT_FAMILY_TEXT = 'SF Pro Text' 
        FONT_FAMILY_ROUNDED = 'SF Pro Rounded'
        FONT_FAMILY_MONO = 'SF Mono'
        
        # 回退字體系統
        FONT_FALLBACK_DISPLAY = 'Segoe UI Variable Display'
        FONT_FALLBACK_TEXT = 'Segoe UI Variable Text'
        FONT_FALLBACK_MONO = 'Cascadia Code'
        FONT_FALLBACK_SYSTEM = 'Segoe UI'
        
        # Liquid Glass 字體大小階層
        FONT_SIZE_CAPTION2 = 8            # 極小說明
        FONT_SIZE_CAPTION = 10            # 說明文字
        FONT_SIZE_FOOTNOTE = 12           # 註腳
        FONT_SIZE_SUBHEADLINE = 14        # 副標題  
        FONT_SIZE_CALLOUT = 15            # 標注
        FONT_SIZE_BODY = 16               # 正文 (新標準)
        FONT_SIZE_HEADLINE = 18           # 標題
        FONT_SIZE_TITLE3 = 20             # 三級標題
        FONT_SIZE_TITLE2 = 24             # 二級標題
        FONT_SIZE_TITLE1 = 32             # 一級標題
        FONT_SIZE_LARGE_TITLE = 40        # 大標題
        FONT_SIZE_DISPLAY = 48            # 顯示標題
        
        # 字體權重 - tkinter兼容版本
        FONT_WEIGHT_ULTRALIGHT = 'normal'
        FONT_WEIGHT_LIGHT = 'normal'
        FONT_WEIGHT_REGULAR = 'normal'
        FONT_WEIGHT_MEDIUM = 'normal'
        FONT_WEIGHT_SEMIBOLD = 'bold'
        FONT_WEIGHT_BOLD = 'bold'
        FONT_WEIGHT_HEAVY = 'bold'
        
        @classmethod
        def get_dynamic_font(cls, size, weight='normal', context='display'):
            """獲取動態字體配置"""
            if context == 'display':
                font_family = cls.FONT_FAMILY_DISPLAY
                fallback = cls.FONT_FALLBACK_DISPLAY
            elif context == 'text':
                font_family = cls.FONT_FAMILY_TEXT  
                fallback = cls.FONT_FALLBACK_TEXT
            elif context == 'mono':
                font_family = cls.FONT_FAMILY_MONO
                fallback = cls.FONT_FALLBACK_MONO
            else:
                font_family = cls.FONT_FAMILY_DISPLAY
                fallback = cls.FONT_FALLBACK_SYSTEM
                
            return (font_family, size, weight), (fallback, size, weight)
    
    # ==================== Liquid Glass 尺寸系統 ====================
    class Dimensions:
        """流體玻璃尺寸和間距系統"""
        
        # 流體間距 - 基於12px網格系統
        SPACING_FLUID_XXS = 2      # 極微間距
        SPACING_FLUID_XS = 4       # 極小間距
        SPACING_FLUID_SM = 8       # 小間距
        SPACING_FLUID_MD = 12      # 中等間距
        SPACING_FLUID_LG = 16      # 大間距
        SPACING_FLUID_XL = 24      # 極大間距
        SPACING_FLUID_XXL = 32     # 超大間距
        SPACING_FLUID_XXXL = 48    # 巨大間距
        
        # 玻璃組件尺寸
        GLASS_BUTTON_HEIGHT_SM = 32    # 小玻璃按鈕
        GLASS_BUTTON_HEIGHT_MD = 40    # 中玻璃按鈕  
        GLASS_BUTTON_HEIGHT_LG = 48    # 大玻璃按鈕
        
        GLASS_INPUT_HEIGHT = 44        # 玻璃輸入框
        GLASS_TOOLBAR_HEIGHT = 64      # 玻璃工具欄
        GLASS_CARD_MIN_HEIGHT = 80     # 玻璃卡片最小高度
        
        # Liquid 圓角系統 - 更大的圓角
        BORDER_RADIUS_FLUID_XS = 6     # 流體小圓角
        BORDER_RADIUS_FLUID_SM = 10    # 流體中圓角
        BORDER_RADIUS_FLUID_MD = 14    # 流體大圓角
        BORDER_RADIUS_FLUID_LG = 18    # 流體特大圓角
        BORDER_RADIUS_FLUID_XL = 24    # 流體超大圓角
        BORDER_RADIUS_FLUID_FULL = 999 # 完全圓形
        
        # 玻璃透明度層級
        GLASS_OPACITY_SUBTLE = 0.05    # 微妙透明
        GLASS_OPACITY_LIGHT = 0.1      # 輕度透明
        GLASS_OPACITY_MEDIUM = 0.2     # 中度透明
        GLASS_OPACITY_HEAVY = 0.3      # 重度透明
        GLASS_OPACITY_SOLID = 0.9      # 接近不透明
        
        # 動態模糊系統
        BLUR_SOFT = 2                  # 柔和模糊
        BLUR_MEDIUM = 4                # 中等模糊
        BLUR_HEAVY = 8                 # 重度模糊
        
        # 玻璃陰影深度
        GLASS_SHADOW_FLOAT = "0 2px 8px rgba(0,0,0,0.06)"    # 懸浮陰影
        GLASS_SHADOW_LIFT = "0 4px 16px rgba(0,0,0,0.08)"     # 提升陰影
        GLASS_SHADOW_DEEP = "0 8px 32px rgba(0,0,0,0.12)"     # 深度陰影
    
    # ==================== Liquid Glass 預設樣式 ====================
    class GlassPresets:
        """玻璃質感預設樣式組合"""
        
        @staticmethod
        def glass_primary_button():
            """主要玻璃按鈕"""
            return {
                'background': LiquidGlassTheme.Colors.GLASS_PRIMARY,
                'foreground': '#ffffff',
                'font': LiquidGlassTheme.Typography.get_dynamic_font(
                    LiquidGlassTheme.Typography.FONT_SIZE_BODY, 
                    LiquidGlassTheme.Typography.FONT_WEIGHT_SEMIBOLD
                )[0],
                'relief': 'flat',
                'borderwidth': 0,
                'highlightthickness': 0,
                'activebackground': LiquidGlassTheme.Colors.GLASS_PRIMARY_LIGHT,
                'activeforeground': '#ffffff'
            }
        
        @staticmethod
        def glass_secondary_button():
            """次要玻璃按鈕"""
            return {
                'background': LiquidGlassTheme.Colors.BACKGROUND_FROSTED,
                'foreground': LiquidGlassTheme.Colors.TEXT_GLASS_PRIMARY,
                'font': LiquidGlassTheme.Typography.get_dynamic_font(
                    LiquidGlassTheme.Typography.FONT_SIZE_BODY,
                    LiquidGlassTheme.Typography.FONT_WEIGHT_MEDIUM
                )[0],
                'relief': 'flat',
                'borderwidth': 1,
                'highlightthickness': 0,
                'activebackground': LiquidGlassTheme.Colors.HOVER_GLASS,
                'highlightbackground': LiquidGlassTheme.Colors.GLASS_SURFACE_LIGHT
            }
        
        @staticmethod
        def glass_card():
            """玻璃卡片容器"""
            return {
                'background': LiquidGlassTheme.Colors.BACKGROUND_CRYSTAL,
                'relief': 'flat',
                'borderwidth': 1,
                'highlightthickness': 1,
                'highlightbackground': LiquidGlassTheme.Colors.GLASS_SURFACE_MEDIUM,
                'highlightcolor': LiquidGlassTheme.Colors.GLASS_SURFACE_HEAVY
            }
        
        @staticmethod
        def glass_display_text():
            """玻璃上的顯示文字"""
            return {
                'background': LiquidGlassTheme.Colors.BACKGROUND_CRYSTAL,
                'foreground': LiquidGlassTheme.Colors.TEXT_GLASS_PRIMARY,
                'font': LiquidGlassTheme.Typography.get_dynamic_font(
                    LiquidGlassTheme.Typography.FONT_SIZE_DISPLAY,
                    LiquidGlassTheme.Typography.FONT_WEIGHT_BOLD,
                    'display'
                )[0],
                'relief': 'flat',
                'borderwidth': 0
            }
        
        @staticmethod
        def glass_progress():
            """玻璃進度條"""
            return {
                'background': LiquidGlassTheme.Colors.GLASS_PRIMARY,
                'troughcolor': LiquidGlassTheme.Colors.BACKGROUND_FROSTED,
                'borderwidth': 0,
                'relief': 'flat'
            }
    
    # ==================== 動態交互狀態 ====================
    class InteractionStates:
        """Liquid Glass 交互狀態系統"""
        
        @staticmethod
        def get_hover_effect():
            """懸停效果配置"""
            return {
                'background_overlay': LiquidGlassTheme.Colors.HOVER_GLASS,
                'border_glow': LiquidGlassTheme.Colors.GLASS_SURFACE_HEAVY,
                'transition_duration': 150  # 毫秒
            }
        
        @staticmethod  
        def get_active_effect():
            """激活效果配置"""
            return {
                'background_overlay': LiquidGlassTheme.Colors.ACTIVE_GLASS,
                'scale_factor': 0.98,
                'shadow_intensity': 0.5
            }
        
        @staticmethod
        def get_focus_effect():
            """聚焦效果配置"""
            return {
                'border_glow': LiquidGlassTheme.Colors.FOCUS_GLASS,
                'glow_radius': 4,
                'glow_intensity': 0.6
            }
    
    # ==================== 環境適應系統 ====================
    class AdaptiveSystem:
        """智能環境適應系統"""
        
        @staticmethod
        def get_light_mode_config():
            """亮色模式配置"""
            return {
                'background_tint': LiquidGlassTheme.Colors.REFLECTION_WARM,
                'text_contrast': 0.9,
                'glass_opacity': LiquidGlassTheme.Dimensions.GLASS_OPACITY_LIGHT
            }
        
        @staticmethod
        def get_auto_mode_config():
            """自動模式配置"""
            return {
                'background_tint': LiquidGlassTheme.Colors.REFLECTION_NEUTRAL,
                'text_contrast': 0.85,
                'glass_opacity': LiquidGlassTheme.Dimensions.GLASS_OPACITY_MEDIUM
            }
    
    # ==================== 動畫系統 ====================
    class Animation:
        """Liquid Glass 流暢動畫系統"""
        
        # 動畫時長 (毫秒)
        DURATION_INSTANT = 0
        DURATION_MICRO = 100
        DURATION_QUICK = 200
        DURATION_SMOOTH = 300
        DURATION_SLOW = 500
        
        # 緩動函數
        EASING_EASE = 'ease'
        EASING_EASE_IN_OUT = 'ease-in-out'
        EASING_SPRING = 'cubic-bezier(0.175, 0.885, 0.32, 1.275)'
        
        @staticmethod
        def get_material_transition():
            """材質過渡動畫"""
            return {
                'duration': LiquidGlassTheme.Animation.DURATION_SMOOTH,
                'easing': LiquidGlassTheme.Animation.EASING_EASE_IN_OUT,
                'properties': ['background', 'border', 'opacity']
            }