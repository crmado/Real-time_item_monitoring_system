"""
Basler MVC 精簡高性能系統
專注於 Basler acA640-300gm 相機和核心檢測功能
"""

__version__ = "1.0.0"
__author__ = "Basler MVC Team"
__description__ = "Basler acA640-300gm 精簡高性能工業相機系統"

# 核心組件
from .models import BaslerCameraModel, DetectionModel
from .controllers import MainController  
from .views import MainView

__all__ = [
    'BaslerCameraModel',
    'DetectionModel', 
    'MainController',
    'MainView'
]