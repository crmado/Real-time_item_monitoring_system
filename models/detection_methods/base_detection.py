"""
檢測方法抽象基類
定義所有檢測方法必須實現的介面
"""
from abc import ABC, abstractmethod

class DetectionMethod(ABC):
    """檢測方法抽象基類"""
    
    @abstractmethod
    def process_frame(self, frame):
        """
        處理影像幀
        
        Args:
            frame: 輸入的影像幀
            
        Returns:
            processed_frame: 處理後的影像幀
        """
        pass
        
    @abstractmethod
    def detect_objects(self, processed_frame, min_area=None, max_area=None):
        """
        檢測物件
        
        Args:
            processed_frame: 處理過的影像幀
            min_area: 最小物件面積 (可選)
            max_area: 最大物件面積 (可選)
            
        Returns:
            valid_objects: 符合條件的物件列表
        """
        pass
    
    @abstractmethod
    def set_parameters(self, params):
        """
        設置處理參數
        
        Args:
            params: 參數字典
            
        Returns:
            bool: 是否成功設置
        """
        pass
    
    @property
    def name(self):
        """檢測方法名稱"""
        return self.__class__.__name__
    
    @property
    def method_type(self):
        """檢測方法類型"""
        return "base"  # 子類可覆蓋此屬性 