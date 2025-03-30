"""
傳統檢測方法模塊
包括基於OpenCV的傳統圖像處理方法
"""
# 導入各個傳統檢測方法
from .background_subtraction import BackgroundSubtractionDetection
from .threshold_based import ThresholdBasedDetection

# 註冊可用的傳統檢測方法
methods = {
    'background_subtraction': BackgroundSubtractionDetection,
    'threshold': ThresholdBasedDetection,
}

# 如果有其他傳統方法，可以繼續添加
# 例如：
# from .edge_detection import EdgeBasedDetection
# methods['edge'] = EdgeBasedDetection 