"""
圖示管理模組 - 統一管理所有 SVG 圖示
自動處理開發環境和打包環境的路徑差異
"""

import sys
from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QSize


def _get_resources_dir() -> Path:
    """
    獲取 resources 目錄路徑（支援開發和打包環境）

    開發環境：basler_pyqt6/resources/
    打包環境：_MEIPASS/resources/
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包環境
        base_path = Path(sys._MEIPASS)
        return base_path / "resources"
    else:
        # 開發環境
        return Path(__file__).parent


# 圖示目錄路徑
ICONS_DIR = _get_resources_dir() / "icons"


class IconManager:
    """圖示管理器 - 負責載入和快取 SVG 圖示"""

    _cache = {}

    @staticmethod
    def get_icon(name: str, size: int = 24) -> QIcon:
        """
        獲取圖示

        Args:
            name: 圖示名稱（不含 .svg 副檔名）
            size: 圖示大小（像素）

        Returns:
            QIcon 物件（找不到圖示時返回空 QIcon）
        """
        cache_key = f"{name}_{size}"

        # 檢查快取
        if cache_key in IconManager._cache:
            return IconManager._cache[cache_key]

        # 載入 SVG
        icon_path = ICONS_DIR / f"{name}.svg"

        if not icon_path.exists():
            # 圖示不存在時，返回空 QIcon（不中斷程式）
            # print(f"⚠️ 圖示不存在: {icon_path}")
            return QIcon()

        # 使用 QIcon 直接載入 SVG（PyQt6 會自動處理）
        icon = QIcon(str(icon_path))

        # 快取圖示
        IconManager._cache[cache_key] = icon

        return icon

    @staticmethod
    def get_pixmap(name: str, size: int = 24) -> QPixmap:
        """
        獲取圖示的 Pixmap（用於 QLabel）

        Args:
            name: 圖示名稱
            size: 圖示大小

        Returns:
            QPixmap 物件
        """
        icon = IconManager.get_icon(name, size)
        return icon.pixmap(QSize(size, size))


# 快捷函數
def get_icon(name: str, size: int = 24) -> QIcon:
    """快捷獲取圖示"""
    return IconManager.get_icon(name, size)


def get_pixmap(name: str, size: int = 24) -> QPixmap:
    """快捷獲取 Pixmap"""
    return IconManager.get_pixmap(name, size)


# 預定義的圖示名稱（方便 IDE 自動完成）
class Icons:
    """圖示名稱常數"""

    # 按鈕圖示
    PLAY = "play"
    STOP = "stop"
    PAUSE = "pause"
    RESET = "replay"
    SEARCH = "search"
    SETTINGS = "settings"

    # 狀態圖示
    TOGGLE_ON = "toggle_on"
    TOGGLE_OFF = "toggle_off"
    CHECKMARK = "checkmark"

    # 資訊圖示
    CHART = "chart"
    LIGHTNING = "lightning"
    VIDEO = "hangout_video"
    TRACK_CHANGES = "track_changes"
