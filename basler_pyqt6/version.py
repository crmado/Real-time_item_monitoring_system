"""
版本管理模組
集中管理應用版本信息
"""

__version__ = "2.0.2"
__version_info__ = (2, 0, 2)

# 應用元數據
APP_NAME = "Basler Vision System"
APP_NAME_SHORT = "BaslerVision"
APP_AUTHOR = "Industrial Vision"
APP_COPYRIGHT = "© 2025 Industrial Vision"
APP_DESCRIPTION = "高性能工業相機視覺檢測系統"

# 更新服務器配置
# 請將下面的地址改為你的實際服務器地址
# 範例：
#   - "http://192.168.1.100:5000/api"  (內網測試)
#   - "https://updates.yourdomain.com/api"  (生產環境，建議使用 HTTPS)
UPDATE_SERVER_URL = "http://172.105.217.66:5000/api"  # 請修改為你的服務器地址
UPDATE_CHECK_INTERVAL = 86400  # 24 小時檢查一次（秒）

# 構建信息
BUILD_DATE = "2025-10-16"
BUILD_TYPE = "release"  # release / beta / alpha

# 開發模式配置（通過環境變數控制）
# 使用方式: export DEBUG_MODE=true && python basler_pyqt6/main_v2.py
# DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
DEBUG_MODE = True

# 測試資料目錄
TEST_DATA_DIR = "basler_pyqt6/testData/新工業相機收集資料"


def get_version_string() -> str:
    """獲取版本字符串"""
    return f"{__version__}"


def get_full_version_string() -> str:
    """獲取完整版本信息"""
    return f"{APP_NAME} v{__version__} ({BUILD_TYPE})"


def compare_versions(current: str, remote: str) -> int:
    """
    比較兩個版本號

    Args:
        current: 當前版本（如 "2.0.0"）
        remote: 遠程版本（如 "2.1.0"）

    Returns:
        -1: current < remote（需要更新）
         0: current == remote（版本相同）
         1: current > remote（當前版本較新）
    """
    def parse_version(v: str) -> tuple:
        """解析版本字符串為元組"""
        try:
            return tuple(map(int, v.split('.')))
        except:
            return (0, 0, 0)

    current_tuple = parse_version(current)
    remote_tuple = parse_version(remote)

    if current_tuple < remote_tuple:
        return -1
    elif current_tuple > remote_tuple:
        return 1
    else:
        return 0
