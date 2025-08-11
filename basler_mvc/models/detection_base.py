"""
檢測方法基類 - 避免循環導入
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
import numpy as np


class DetectionMethod(ABC):
    """檢測方法抽象基類"""
    
    @abstractmethod
    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """處理影像幀"""
        pass
        
    @abstractmethod
    def detect_objects(self, processed_frame: np.ndarray, min_area: int = None, max_area: int = None) -> List[Tuple]:
        """檢測物件"""
        pass
    
    @abstractmethod
    def set_parameters(self, params: Dict[str, Any]) -> bool:
        """設置參數"""
        pass
    
    @property
    def name(self) -> str:
        """檢測方法名稱"""
        return self.__class__.__name__
