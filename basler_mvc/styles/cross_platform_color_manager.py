"""
跨平台顏色管理系統
解決不同平台間顏色顯示差異，確保視覺一致性
"""

import platform
import tkinter as tk
from tkinter import ttk
import logging
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ColorProfile:
    """顏色配置檔案"""
    gamma: float = 2.2
    brightness_adjust: float = 1.0
    contrast_adjust: float = 1.0
    saturation_adjust: float = 1.0


class CrossPlatformColorManager:
    """跨平台顏色管理器"""
    
    def __init__(self):
        self.platform_name = platform.system().lower()
        self.color_cache = {}
        
        # 初始化平台特定顏色配置
        self._setup_platform_colors()
        self._setup_color_profiles()
        
        logging.info(f"✅ 跨平台顏色管理器初始化完成 - 平台: {self.platform_name}")
    
    def _setup_platform_colors(self):
        """設置平台特定顏色配置"""
        
        # 通用基礎顏色 - 🎨 優化對比度版本
        base_colors = {
            'primary_blue': '#0051D5',      # 優化後藍色 (對比度6.69:1)
            'success_green': '#34C759', 
            'warning_orange': '#FF9500',
            'error_red': '#FF3B30',
            'info_purple': '#AF52DE',
            'text_primary': '#1D1D1F',
            'text_secondary': '#6D6D70',    # 優化後灰色 (對比度5.16:1)
            'background_primary': '#F8F9FA', # 統一背景色
            'background_card': '#FFFFFF',
            'border_light': '#6D6D70'       # 符合AA標準邊框 (對比度5.16:1)
        }
        
        if self.platform_name == 'windows':
            # Windows 平台顏色調整
            self.platform_colors = {
                **base_colors,
                # Windows 需要稍微深一點的顏色以增強可見性
                'primary_blue': '#0040B8',      # 基於優化藍色，更深
                'text_primary': '#1C1C1C',
                'text_secondary': '#5F5F65',    # 基於優化灰色，更深
                'background_primary': '#F3F3F3',
                'border_light': '#5F5F65',     # 基於AA標準邊框，更深
                
                # Windows 特有的系統顏色
                'system_accent': self._get_windows_accent_color(),
                'system_background': '#F0F0F0',
                'system_button_face': '#F0F0F0',
                'system_button_text': '#000000',
                'system_window': '#FFFFFF'
            }
            
        elif self.platform_name == 'darwin':  # macOS
            # macOS 平台顏色調整 - 🎨 使用優化後顏色
            self.platform_colors = {
                **base_colors,
                # macOS 使用優化後的高對比度顏色 (符合WCAG AA標準)
                'text_primary': '#1D1D1F',       # 使用優化文字色
                'text_secondary': '#6D6D70',     # 使用優化次要文字色 (對比度5.16:1)
                'background_primary': '#F8F9FA',
                'border_light': '#6D6D70',       # 使用優化邊框色 (對比度5.16:1)
                
                # macOS 特有顏色 - 也使用優化版本
                'control_accent': '#0051D5',     # 使用優化藍色 (對比度6.69:1)
                'control_background': '#FFFFFF',
                'separator': '#6D6D70',          # 使用優化分隔線色
                'label_color': '#1D1D1F',        # 使用優化標籤色
                'secondary_label_color': '#6D6D70' # 使用優化次要標籤色
            }
            
        else:  # Linux 及其他系統
            # Linux 平台顏色調整
            self.platform_colors = {
                **base_colors,
                # Linux 使用更高對比度的顏色
                'primary_blue': '#0066CC',
                'text_primary': '#1A1A1A',
                'text_secondary': '#6A6A6A',
                'background_primary': '#F5F5F5',
                'background_card': '#FDFDFD',
                'border_light': '#DBDBDB',
                
                # Linux 特有顏色
                'gtk_theme_bg': '#FFFFFF',
                'gtk_theme_fg': '#000000',
                'selection_bg': '#0066CC',
                'selection_fg': '#FFFFFF'
            }
    
    def _setup_color_profiles(self):
        """設置平台特定的顏色配置檔案"""
        
        if self.platform_name == 'windows':
            self.color_profile = ColorProfile(
                gamma=2.2,
                brightness_adjust=1.1,  # Windows 稍微亮一點
                contrast_adjust=1.05,
                saturation_adjust=0.95
            )
            
        elif self.platform_name == 'darwin':
            self.color_profile = ColorProfile(
                gamma=1.8,  # macOS 使用不同的 gamma 值
                brightness_adjust=1.0,
                contrast_adjust=1.0,
                saturation_adjust=1.0
            )
            
        else:  # Linux
            self.color_profile = ColorProfile(
                gamma=2.2,
                brightness_adjust=1.05,
                contrast_adjust=1.1,    # Linux 需要更高對比度
                saturation_adjust=0.9
            )
    
    def _get_windows_accent_color(self) -> str:
        """獲取 Windows 系統強調色"""
        try:
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(registry, r"SOFTWARE\Microsoft\Windows\DWM")
            value, _ = winreg.QueryValueEx(key, "AccentColor")
            winreg.CloseKey(key)
            
            # 轉換為 hex 顏色
            color = f"#{value:06X}"
            return color
            
        except Exception:
            # 如果無法獲取，返回默認顏色
            return '#0078D4'
    
    def adjust_color_for_platform(self, color: str, adjust_type: str = 'auto') -> str:
        """根據平台調整顏色"""
        
        # 建立快取鍵
        cache_key = f"{color}_{adjust_type}_{self.platform_name}"
        if cache_key in self.color_cache:
            return self.color_cache[cache_key]
        
        try:
            # 解析顏色
            if color.startswith('#'):
                r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            else:
                # 嘗試從平台顏色字典獲取
                if color in self.platform_colors:
                    adjusted_color = self.platform_colors[color]
                    self.color_cache[cache_key] = adjusted_color
                    return adjusted_color
                else:
                    # 回退到原顏色
                    self.color_cache[cache_key] = color
                    return color
            
            # 應用平台特定調整
            if adjust_type == 'auto':
                r = int(r * self.color_profile.brightness_adjust * self.color_profile.contrast_adjust)
                g = int(g * self.color_profile.brightness_adjust * self.color_profile.contrast_adjust)
                b = int(b * self.color_profile.brightness_adjust * self.color_profile.contrast_adjust)
            
            # 確保顏色值在有效範圍內
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            adjusted_color = f"#{r:02X}{g:02X}{b:02X}"
            self.color_cache[cache_key] = adjusted_color
            
            return adjusted_color
            
        except Exception as e:
            logging.warning(f"顏色調整失敗 {color}: {str(e)}")
            self.color_cache[cache_key] = color
            return color
    
    def get_platform_color(self, color_name: str) -> str:
        """獲取平台特定顏色"""
        return self.platform_colors.get(color_name, '#000000')
    
    def get_contrast_color(self, background_color: str) -> str:
        """根據背景顏色獲取對比色"""
        try:
            # 解析背景顏色
            if background_color.startswith('#'):
                r, g, b = int(background_color[1:3], 16), int(background_color[3:5], 16), int(background_color[5:7], 16)
            else:
                # 從平台顏色獲取
                bg_color = self.get_platform_color(background_color)
                r, g, b = int(bg_color[1:3], 16), int(bg_color[3:5], 16), int(bg_color[5:7], 16)
            
            # 計算亮度
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            
            # 根據亮度選擇對比色
            if luminance > 0.5:
                return self.get_platform_color('text_primary')
            else:
                return '#FFFFFF'
                
        except Exception:
            # 回退到黑色
            return self.get_platform_color('text_primary')
    
    def create_color_scheme(self, base_color: str) -> Dict[str, str]:
        """基於基礎顏色創建配色方案"""
        try:
            # 解析基礎顏色
            r, g, b = int(base_color[1:3], 16), int(base_color[3:5], 16), int(base_color[5:7], 16)
            
            # 生成配色方案
            return {
                'primary': base_color,
                'light': f"#{min(255, r+40):02X}{min(255, g+40):02X}{min(255, b+40):02X}",
                'dark': f"#{max(0, r-40):02X}{max(0, g-40):02X}{max(0, b-40):02X}",
                'muted': f"#{r//2+127:02X}{g//2+127:02X}{b//2+127:02X}",
                'contrast': self.get_contrast_color(base_color)
            }
            
        except Exception:
            # 回退到默認配色
            return {
                'primary': self.get_platform_color('primary_blue'),
                'light': self.get_platform_color('primary_blue'),
                'dark': self.get_platform_color('primary_blue'),
                'muted': self.get_platform_color('text_secondary'),
                'contrast': self.get_platform_color('text_primary')
            }
    
    def apply_platform_style_to_widget(self, widget: tk.Widget, style_type: str = 'default') -> None:
        """將平台特定樣式應用到 widget"""
        
        try:
            if style_type == 'button':
                widget.configure(
                    bg=self.get_platform_color('primary_blue'),
                    fg=self.get_contrast_color('primary_blue'),
                    activebackground=self.adjust_color_for_platform(self.get_platform_color('primary_blue'), 'lighter'),
                    relief='flat' if self.platform_name == 'darwin' else 'raised',
                    borderwidth=0 if self.platform_name == 'darwin' else 1
                )
                
            elif style_type == 'entry':
                widget.configure(
                    bg=self.get_platform_color('background_card'),
                    fg=self.get_platform_color('text_primary'),
                    insertbackground=self.get_platform_color('text_primary'),
                    selectbackground=self.get_platform_color('primary_blue'),
                    selectforeground=self.get_contrast_color('primary_blue'),
                    relief='solid',
                    borderwidth=1,
                    highlightcolor=self.get_platform_color('primary_blue')
                )
                
            elif style_type == 'frame':
                widget.configure(
                    bg=self.get_platform_color('background_card'),
                    relief='flat',
                    borderwidth=0
                )
                
            elif style_type == 'label':
                widget.configure(
                    bg=self.get_platform_color('background_card'),
                    fg=self.get_platform_color('text_primary')
                )
                
        except Exception as e:
            logging.warning(f"應用樣式失敗 {style_type}: {str(e)}")
    
    def get_ttk_style_config(self) -> Dict:
        """獲取 ttk 樣式配置"""
        
        return {
            'TButton': {
                'configure': {
                    'background': self.get_platform_color('primary_blue'),
                    'foreground': self.get_contrast_color('primary_blue'),
                    'focuscolor': 'none',
                    'relief': 'flat' if self.platform_name == 'darwin' else 'raised'
                },
                'map': {
                    'background': [
                        ('active', self.adjust_color_for_platform(self.get_platform_color('primary_blue'), 'lighter')),
                        ('pressed', self.adjust_color_for_platform(self.get_platform_color('primary_blue'), 'darker'))
                    ]
                }
            },
            'TEntry': {
                'configure': {
                    'fieldbackground': self.get_platform_color('background_card'),
                    'foreground': self.get_platform_color('text_primary'),
                    'bordercolor': self.get_platform_color('border_light'),
                    'selectbackground': self.get_platform_color('primary_blue'),
                    'selectforeground': self.get_contrast_color('primary_blue')
                },
                'map': {
                    'bordercolor': [('focus', self.get_platform_color('primary_blue'))]
                }
            },
            'TFrame': {
                'configure': {
                    'background': self.get_platform_color('background_card'),
                    'relief': 'flat'
                }
            },
            'TLabel': {
                'configure': {
                    'background': self.get_platform_color('background_card'),
                    'foreground': self.get_platform_color('text_primary')
                }
            }
        }
    
    def log_color_info(self):
        """記錄顏色系統資訊"""
        logging.info(f"=== 顏色系統資訊 ===")
        logging.info(f"平台: {self.platform_name}")
        logging.info(f"顏色配置檔案: Gamma={self.color_profile.gamma}, 亮度={self.color_profile.brightness_adjust}")
        
        # 記錄主要顏色
        main_colors = ['primary_blue', 'text_primary', 'background_primary']
        for color_name in main_colors:
            color_value = self.get_platform_color(color_name)
            logging.info(f"{color_name}: {color_value}")


# 全域顏色管理器實例
_color_manager = None

def get_color_manager() -> CrossPlatformColorManager:
    """獲取全域顏色管理器實例"""
    global _color_manager
    if _color_manager is None:
        _color_manager = CrossPlatformColorManager()
    return _color_manager


# 便利函數
def get_platform_color(color_name: str) -> str:
    """獲取平台特定顏色 - 便利函數"""
    return get_color_manager().get_platform_color(color_name)

def adjust_color(color: str, adjust_type: str = 'auto') -> str:
    """調整顏色 - 便利函數"""
    return get_color_manager().adjust_color_for_platform(color, adjust_type)

def get_contrast_color(background_color: str) -> str:
    """獲取對比色 - 便利函數"""
    return get_color_manager().get_contrast_color(background_color)
