"""
形狀檢測方法模塊
包括圓形、矩形等特定形狀的檢測方法
"""
# 導入各個形狀檢測方法
from .circle_detection import CircleDetection

# 註冊可用的形狀檢測方法
methods = {
    'circle': CircleDetection,
}

# 如果有其他形狀檢測方法，可以繼續添加
# 例如：
# from .rectangle_detection import RectangleDetection
# methods['rectangle'] = RectangleDetection 