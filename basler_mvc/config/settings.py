"""
系統配置設定
集中管理所有配置參數
"""

import os
from pathlib import Path
from typing import Dict, Any

# 項目根目錄
PROJECT_ROOT = Path(__file__).parent.parent

# ==================== 相機配置 ====================

CAMERA_CONFIG = {
    # Basler acA640-300gm 特定設置
    'target_model': 'acA640-300gm',
    'default_width': 640,
    'default_height': 480,
    'default_pixel_format': 'Mono8',
    'default_exposure_time': 1000.0,  # 微秒
    'default_gain': 0.0,
    'target_fps': 350.0,  # 接近理論最大值 376
    'enable_jumbo_frames': True,
    'packet_size': 9000,
    
    # 抓取策略
    'grab_strategy': 'LatestImageOnly',
    'grab_timeout': 1,  # 毫秒
    
    # 緩衝設置 - 優化記憶體使用
    'frame_buffer_size': 3,
    'enable_frame_queue': True
}

# ==================== 檢測配置 ====================

DETECTION_CONFIG = {
    # 通用檢測設置
    'default_method': 'circle',
    'enable_detection': True,
    'min_area': 100,
    'max_area': 5000,
    
    # 圓形檢測參數
    'circle_detection': {
        'dp': 1.2,
        'min_dist': 20,
        'param1': 50,
        'param2': 30,
        'min_radius': 5,
        'max_radius': 100,
        'gaussian_kernel_size': 5
    },
    
    # 輪廓檢測參數
    'contour_detection': {
        'threshold_value': 127,
        'morphology_kernel_size': 3,
        'contour_mode': 'RETR_EXTERNAL',
        'contour_method': 'CHAIN_APPROX_SIMPLE'
    }
}

# ==================== 性能配置 ====================

PERFORMANCE_CONFIG = {
    # 線程設置
    'enable_multithreading': True,
    'processing_thread_count': 1,
    'max_processing_queue_size': 5,
    
    # 顯示設置
    'ui_update_fps': 120,  # 🚀 UI 更新頻率 (大幅提升)
    'frame_skip_ratio': 4,  # 顯示時跳幀比例
    'auto_resize_display': True,
    'max_display_width': 800,
    'max_display_height': 600,
    
    # 統計設置
    'stats_update_interval': 0.5,  # 秒
    'fps_calculation_window': 100,  # 增加計算視窗提升高速模式準確性
    'enable_performance_logging': True,
    'dynamic_ui_update': True,      # 動態調整UI更新頻率
    'adaptive_frame_skip': True,    # 自適應跳幀
    'memory_optimization': True     # 記憶體優化模式
}

# ==================== UI 配置 ====================

UI_CONFIG = {
    # 主窗口
    'window_title': '🚀 Basler acA640-300gm 精簡高性能系統',
    'window_size': (1100, 800),
    'window_resizable': True,
    'window_icon': None,
    
    # 主題
    'theme': 'default',
    'font_family': 'Arial',
    'font_size': 9,
    'status_font_size': 10,
    'title_font_size': 12,
    
    # 顏色
    'colors': {
        'camera_fps': 'green',
        'processing_fps': 'blue', 
        'detection_fps': 'purple',
        'object_count': 'blue',
        'error': 'red',
        'warning': 'orange',
        'success': 'green'
    },
    
    # 控件設置
    'button_width': 12,
    'entry_width': 8,
    'spinbox_width': 8
}

# ==================== 日誌配置 ====================

LOGGING_CONFIG = {
    'log_level': 'INFO',
    'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'log_file': 'basler_mvc.log',
    'max_log_size': 50 * 1024 * 1024,  # 提升至50MB應對高速模式
    'backup_count': 10,                 # 增加備份數量
    'enable_console_logging': True,
    'enable_file_logging': True,
    'enable_structured_logging': True,  # 新增結構化日誌
    'performance_logging': True,        # 新增性能日誌
    'enable_rotation': True,            # 啟用日誌輪轉
    'log_rotation_when': 'midnight',    # 每日輪轉
    'log_rotation_interval': 1,         # 輪轉間隔
    'log_compression': True             # 壓縮舊日誌檔案
}

# ==================== 系統路徑 ====================

PATHS = {
    'project_root': PROJECT_ROOT,
    'logs_dir': PROJECT_ROOT / 'logs',
    'config_dir': PROJECT_ROOT / 'config',
    'models_dir': PROJECT_ROOT / 'models',
    'views_dir': PROJECT_ROOT / 'views', 
    'controllers_dir': PROJECT_ROOT / 'controllers'
}

# ==================== 開發配置 ====================

DEV_CONFIG = {
    'debug_mode': False,
    'enable_test_camera': False,  # 是否啟用測試相機（無實體設備時）
    'mock_frame_rate': 206,  # 🚀 測試相機高速幀率
    'enable_detailed_logging': False,
    'log_frame_processing': False
}

# ==================== 配置驗證 ====================

def validate_config() -> bool:
    """驗證配置有效性"""
    try:
        # 檢查必要目錄
        for path_name, path_value in PATHS.items():
            if not isinstance(path_value, Path):
                print(f"❌ 路徑配置錯誤: {path_name}")
                return False
        
        # 檢查數值範圍
        if not (1 <= PERFORMANCE_CONFIG['ui_update_fps'] <= 240):
            print("❌ UI更新頻率超出範圍 (1-240)")
            return False
            
        if not (100 <= CAMERA_CONFIG['target_fps'] <= 400):
            print("❌ 相機目標FPS超出範圍 (100-400)")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 配置驗證失敗: {str(e)}")
        return False

# ==================== 配置獲取函數 ====================

def get_camera_config() -> Dict[str, Any]:
    """獲取相機配置"""
    return CAMERA_CONFIG.copy()

def get_detection_config() -> Dict[str, Any]:
    """獲取檢測配置"""
    return DETECTION_CONFIG.copy()

def get_performance_config() -> Dict[str, Any]:
    """獲取性能配置"""
    return PERFORMANCE_CONFIG.copy()

def get_ui_config() -> Dict[str, Any]:
    """獲取UI配置"""
    return UI_CONFIG.copy()

def get_logging_config() -> Dict[str, Any]:
    """獲取日誌配置"""
    return LOGGING_CONFIG.copy()

def get_all_config() -> Dict[str, Any]:
    """獲取所有配置"""
    return {
        'camera': CAMERA_CONFIG,
        'detection': DETECTION_CONFIG,
        'performance': PERFORMANCE_CONFIG,
        'ui': UI_CONFIG,
        'logging': LOGGING_CONFIG,
        'paths': {k: str(v) for k, v in PATHS.items()},
        'dev': DEV_CONFIG
    }

# ==================== 運行時配置更新 ====================

def update_config(section: str, updates: Dict[str, Any]) -> bool:
    """運行時更新配置"""
    try:
        config_map = {
            'camera': CAMERA_CONFIG,
            'detection': DETECTION_CONFIG, 
            'performance': PERFORMANCE_CONFIG,
            'ui': UI_CONFIG,
            'dev': DEV_CONFIG
        }
        
        if section not in config_map:
            return False
        
        config_map[section].update(updates)
        return True
        
    except Exception:
        return False

# ==================== 配置熱重載支援 ====================

def init_config_manager():
    """初始化配置管理器並載入當前配置"""
    try:
        from ..utils.config_manager import init_config_manager
        
        all_config = get_all_config()
        init_config_manager(all_config, PROJECT_ROOT / 'config' / 'runtime_config.json')
        
        logging.info("✅ 配置管理器初始化完成，支援熱重載")
        return True
        
    except ImportError as e:
        logging.warning(f"配置管理器不可用: {str(e)}")
        return False

def hot_reload_config(section: str, updates: Dict[str, Any]) -> bool:
    """熱重載配置"""
    try:
        from ..utils.config_manager import hot_reload_config
        return hot_reload_config(section, updates)
    except ImportError:
        logging.warning("配置熱重載不可用，使用靜態更新")
        return update_config(section, updates)

# 自動驗證配置
if __name__ == "__main__":
    if validate_config():
        print("✅ 配置驗證通過")
        
        # 嘗試初始化配置管理器
        if init_config_manager():
            print("✅ 配置管理器初始化完成")
        else:
            print("⚠️ 配置管理器初始化失敗，將使用靜態配置")
    else:
        print("❌ 配置驗證失敗")