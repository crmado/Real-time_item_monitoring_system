"""
深度學習檢測方法模塊
包括基於深度學習的物體檢測方法，如YOLO、SSD等
"""
# 導入各個深度學習檢測方法
try:
    from .yolo_detection import YOLODetection
    has_yolo = True
except ImportError:
    has_yolo = False
    
# 註冊可用的深度學習檢測方法
methods = {}

# 如果YOLO可用，則添加到方法字典
if has_yolo:
    methods['yolo'] = YOLODetection

# 如果有其他深度學習檢測方法，可以繼續添加
# 例如：
# try:
#     from .ssd_detection import SSDDetection
#     methods['ssd'] = SSDDetection
# except ImportError:
#     pass 