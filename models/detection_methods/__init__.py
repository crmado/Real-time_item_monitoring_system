"""
檢測方法管理總模塊
負責註冊和提供各種檢測方法
"""
# 導入各分類模塊
from . import traditional
from . import shape_detection
from . import deep_learning
from . import specialized

# 合併所有分類的方法
available_methods = {}
available_methods.update(traditional.methods)
available_methods.update(shape_detection.methods)
available_methods.update(deep_learning.methods)
available_methods.update(specialized.methods)

def get_detection_method(method_name, **kwargs):
    """
    工廠函數 - 創建指定的檢測方法實例
    
    Args:
        method_name: 檢測方法名稱
        **kwargs: 傳遞給檢測方法構造函數的參數
        
    Returns:
        detection_method: 檢測方法實例
    """
    if method_name not in available_methods:
        raise ValueError(f"未知的檢測方法：{method_name}")
        
    # 創建並返回檢測方法實例
    return available_methods[method_name](**kwargs)

def list_available_methods():
    """
    列出所有可用的檢測方法
    
    Returns:
        methods: 可用檢測方法列表
    """
    return list(available_methods.keys())

def list_methods_by_type(method_type):
    """
    列出指定類型的所有可用檢測方法
    
    Args:
        method_type: 檢測方法類型 ('traditional', 'shape', 'deep_learning', 'specialized')
    
    Returns:
        methods: 指定類型的可用檢測方法列表
    """
    methods_of_type = []
    
    if method_type == 'traditional':
        methods_of_type = list(traditional.methods.keys())
    elif method_type == 'shape':
        methods_of_type = list(shape_detection.methods.keys())
    elif method_type == 'deep_learning':
        methods_of_type = list(deep_learning.methods.keys())
    elif method_type == 'specialized':
        methods_of_type = list(specialized.methods.keys())
        
    return methods_of_type 