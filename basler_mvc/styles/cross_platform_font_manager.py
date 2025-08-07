"""
跨平台字體管理系統
解決字體一致性、編碼和平台差異問題
"""

import platform
import tkinter.font as tkFont
import locale
import sys
import logging
from typing import Dict, List, Tuple, Optional


class CrossPlatformFontManager:
    """跨平台字體管理器 - 解決字體一致性和編碼問題"""
    
    def __init__(self):
        self.platform_name = platform.system().lower()
        self.available_fonts = list(tkFont.families())
        self.encoding = self._detect_system_encoding()
        self.font_cache = {}
        
        # 初始化平台特定設定
        self._setup_platform_fonts()
        
        logging.info(f"✅ 跨平台字體管理器初始化完成 - 平台: {self.platform_name}, 編碼: {self.encoding}")
    
    def _detect_system_encoding(self) -> str:
        """檢測系統編碼，確保字體正確顯示"""
        try:
            # 嘗試多種方式檢測編碼
            encodings = [
                locale.getpreferredencoding(),
                sys.getdefaultencoding(),
                'utf-8',
                'gbk',
                'big5'
            ]
            
            # 測試編碼是否有效
            test_text = "測試字體編碼"
            for encoding in encodings:
                try:
                    test_text.encode(encoding)
                    logging.info(f"檢測到系統編碼: {encoding}")
                    return encoding
                except (UnicodeEncodeError, LookupError):
                    continue
            
            # 默認使用UTF-8
            return 'utf-8'
            
        except Exception as e:
            logging.warning(f"編碼檢測失敗，使用默認UTF-8: {str(e)}")
            return 'utf-8'
    
    def _setup_platform_fonts(self):
        """設置平台特定的字體配置"""
        
        if self.platform_name == 'windows':
            self.platform_fonts = {
                'primary': [
                    'Microsoft YaHei UI',      # 微軟雅黑 UI
                    'Microsoft YaHei',         # 微軟雅黑  
                    'Segoe UI Variable',       # Windows 11 標準
                    'Segoe UI',                # Windows 10 標準
                    'Microsoft JhengHei UI',   # 微軟正黑體 UI
                    'Microsoft JhengHei',      # 微軟正黑體
                    'SimSun'                   # 宋體（回退）
                ],
                'mono': [
                    'Cascadia Code',           # Windows Terminal 字體
                    'Cascadia Mono',
                    'Consolas',                # Visual Studio 標準
                    'Courier New',
                    'SimSun'                   # 回退
                ],
                'display': [
                    'Microsoft YaHei UI',
                    'Segoe UI Variable Display',
                    'Segoe UI',
                    'Microsoft JhengHei UI'
                ]
            }
            
        elif self.platform_name == 'darwin':  # macOS
            self.platform_fonts = {
                'primary': [
                    'SF Pro Display',          # Apple 系統字體
                    'SF Pro Text',
                    'PingFang TC',             # 蘋方-繁體中文
                    'PingFang SC',             # 蘋方-簡體中文
                    'Helvetica Neue',          # 經典字體
                    'Arial Unicode MS',        # Unicode 支援
                    'Arial'                    # 回退
                ],
                'mono': [
                    'SF Mono',                 # Apple 等寬字體
                    'Monaco',                  # macOS 經典等寬
                    'Menlo',
                    'Courier New'
                ],
                'display': [
                    'SF Pro Display',
                    'SF Compact Display',
                    'Helvetica Neue'
                ]
            }
            
        else:  # Linux 及其他系統
            self.platform_fonts = {
                'primary': [
                    'Noto Sans CJK TC',        # Google Noto 繁體中文
                    'Noto Sans CJK SC',        # Google Noto 簡體中文
                    'Source Han Sans TC',      # Adobe 思源黑體繁體
                    'Source Han Sans SC',      # Adobe 思源黑體簡體
                    'WenQuanYi Micro Hei',     # 文泉驛微米黑
                    'DejaVu Sans',             # Linux 標準
                    'Liberation Sans',
                    'Arial',
                    'FreeSans'                 # 回退
                ],
                'mono': [
                    'Noto Sans Mono CJK TC',
                    'Source Code Pro',
                    'DejaVu Sans Mono',
                    'Liberation Mono',
                    'Courier New'
                ],
                'display': [
                    'Noto Sans CJK TC',
                    'Source Han Sans TC',
                    'DejaVu Sans'
                ]
            }
    
    def get_best_font(self, font_type: str = 'primary', size: int = 12, weight: str = 'normal') -> Tuple[str, int, str]:
        """
        獲取最佳可用字體
        
        Args:
            font_type: 字體類型 ('primary', 'mono', 'display')
            size: 字體大小
            weight: 字體權重
            
        Returns:
            (字體名稱, 大小, 權重) 元組
        """
        
        # 建立快取鍵
        cache_key = f"{font_type}_{size}_{weight}_{self.platform_name}"
        if cache_key in self.font_cache:
            return self.font_cache[cache_key]
        
        # 獲取平台字體列表
        font_candidates = self.platform_fonts.get(font_type, self.platform_fonts['primary'])
        
        # 尋找第一個可用的字體
        selected_font = None
        for font_name in font_candidates:
            if font_name in self.available_fonts:
                selected_font = font_name
                logging.debug(f"選中字體: {font_name} (類型: {font_type})")
                break
        
        # 如果沒有找到，使用系統默認
        if not selected_font:
            selected_font = 'Arial'  # 最通用的回退字體
            logging.warning(f"未找到合適字體，使用回退字體: {selected_font}")
        
        # 平台特定大小調整
        adjusted_size = self._adjust_font_size(size)
        
        result = (selected_font, adjusted_size, weight)
        self.font_cache[cache_key] = result
        
        return result
    
    def _adjust_font_size(self, size: int) -> int:
        """根據平台調整字體大小"""
        
        # macOS 通常需要稍微大一點的字體
        if self.platform_name == 'darwin':
            return int(size * 1.1)
        
        # Linux 系統可能需要調整
        elif self.platform_name == 'linux':
            return int(size * 1.05)
        
        # Windows 保持原大小
        return size
    
    def test_unicode_support(self, font_name: str) -> bool:
        """測試字體是否支援 Unicode 字符"""
        try:
            test_font = tkFont.Font(family=font_name, size=12)
            # 測試常見的中文字符
            test_chars = ['中', '文', '測', '試', '系', '統']
            
            for char in test_chars:
                if not test_font.measure(char):
                    return False
            
            return True
            
        except Exception:
            return False
    
    def get_safe_text(self, text: str) -> str:
        """獲取安全的文字顯示，處理編碼問題"""
        try:
            # 嘗試編碼和解碼測試
            if isinstance(text, bytes):
                text = text.decode(self.encoding, errors='replace')
            
            # 確保可以編碼
            text.encode(self.encoding, errors='replace')
            return text
            
        except (UnicodeDecodeError, UnicodeEncodeError):
            # 如果出現編碼問題，使用安全模式
            try:
                return text.encode('ascii', errors='ignore').decode('ascii')
            except:
                return "顯示錯誤"
    
    def create_font_object(self, font_type: str = 'primary', size: int = 12, weight: str = 'normal') -> tkFont.Font:
        """創建字體物件"""
        family, adjusted_size, font_weight = self.get_best_font(font_type, size, weight)
        
        try:
            font_obj = tkFont.Font(
                family=family,
                size=adjusted_size,
                weight=font_weight
            )
            
            # 測試字體是否正常工作
            if not self.test_unicode_support(family):
                logging.warning(f"字體 {family} Unicode 支援不完整")
            
            return font_obj
            
        except Exception as e:
            logging.error(f"創建字體物件失敗: {str(e)}")
            # 回退到系統默認字體
            return tkFont.Font()
    
    def get_platform_specific_config(self) -> Dict:
        """獲取平台特定的UI配置"""
        
        if self.platform_name == 'windows':
            return {
                'button_padding': (8, 4),
                'entry_padding': (6, 3),
                'frame_padding': (10, 8),
                'border_width': 1,
                'relief_style': 'flat'
            }
            
        elif self.platform_name == 'darwin':
            return {
                'button_padding': (12, 6),
                'entry_padding': (8, 4),
                'frame_padding': (12, 10),
                'border_width': 0,
                'relief_style': 'flat'
            }
            
        else:  # Linux
            return {
                'button_padding': (10, 5),
                'entry_padding': (7, 4),
                'frame_padding': (11, 9),
                'border_width': 1,
                'relief_style': 'solid'
            }
    
    def log_font_info(self):
        """記錄字體資訊以便除錯"""
        logging.info(f"=== 字體系統資訊 ===")
        logging.info(f"平台: {self.platform_name}")
        logging.info(f"編碼: {self.encoding}")
        logging.info(f"可用字體數量: {len(self.available_fonts)}")
        
        # 記錄已選字體
        for font_type in ['primary', 'mono', 'display']:
            family, size, weight = self.get_best_font(font_type)
            logging.info(f"{font_type} 字體: {family}")
        
        # 測試中文顯示
        test_text = "系統測試字體顯示"
        safe_text = self.get_safe_text(test_text)
        logging.info(f"中文測試: {safe_text}")


# 全域字體管理器實例
_font_manager = None

def get_font_manager() -> CrossPlatformFontManager:
    """獲取全域字體管理器實例"""
    global _font_manager
    if _font_manager is None:
        _font_manager = CrossPlatformFontManager()
    return _font_manager


# 便利函數
def get_platform_font(font_type: str = 'primary', size: int = 12, weight: str = 'normal') -> Tuple[str, int, str]:
    """獲取平台適配字體 - 便利函數"""
    return get_font_manager().get_best_font(font_type, size, weight)

def create_platform_font(font_type: str = 'primary', size: int = 12, weight: str = 'normal') -> tkFont.Font:
    """創建平台適配字體物件 - 便利函數"""
    return get_font_manager().create_font_object(font_type, size, weight)

def safe_text(text: str) -> str:
    """安全文字處理 - 便利函數"""
    return get_font_manager().get_safe_text(text)
