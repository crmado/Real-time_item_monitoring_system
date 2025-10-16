"""
方法面板模組

不同檢測方法的專用控制面板
"""

from .counting_method_panel import CountingMethodPanel
from .defect_detection_method_panel import DefectDetectionMethodPanel

__all__ = [
    'CountingMethodPanel',
    'DefectDetectionMethodPanel'
]
