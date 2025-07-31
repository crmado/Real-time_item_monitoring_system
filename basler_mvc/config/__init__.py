"""
配置模塊初始化
"""

from .settings import (
    get_camera_config,
    get_detection_config,
    get_performance_config,
    get_ui_config,
    get_logging_config,
    get_all_config,
    validate_config,
    update_config
)

__all__ = [
    'get_camera_config',
    'get_detection_config', 
    'get_performance_config',
    'get_ui_config',
    'get_logging_config',
    'get_all_config',
    'validate_config',
    'update_config'
]