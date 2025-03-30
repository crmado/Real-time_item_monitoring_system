"""
圓形檢測方法
使用霍夫變換進行圓形物體檢測
"""
import cv2
import numpy as np
import logging
from ..base_detection import DetectionMethod

class CircleDetection(DetectionMethod):
    """基於霍夫變換的圓形檢測方法"""
    
    def __init__(self):
        """初始化圓形檢測方法"""
        # 預處理參數
        self.gaussian_kernel = (5, 5)
        
        # 霍夫圓檢測參數
        self.dp = 1.2  # 累加器解析度與圖像解析度的比值
        self.min_dist = 20  # 檢測到的圓心之間的最小距離
        self.param1 = 50  # Canny邊緣檢測的高閾值
        self.param2 = 30  # 累加器閾值
        self.min_radius = 10  # 最小半徑
        self.max_radius = 100  # 最大半徑
        
        # 物體檢測參數
        self.min_object_area = 10
        self.max_object_area = 150
        
        logging.info("初始化圓形檢測方法完成")
    
    @property
    def method_type(self):
        """檢測方法類型"""
        return "shape"
    
    def process_frame(self, frame):
        """
        使用圓形檢測方法處理單幀影像
        
        Args:
            frame: 輸入的影像幀
            
        Returns:
            processed_frame: 處理後的影像幀
        """
        if frame is None or frame.size == 0:
            return None
            
        try:
            # 轉換為灰度圖
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 高斯模糊去噪
            blurred = cv2.GaussianBlur(gray, self.gaussian_kernel, 0)
            
            return blurred
        
        except Exception as e:
            logging.error(f"處理幀時發生錯誤: {str(e)}")
            return None
    
    def detect_objects(self, processed, min_area=None, max_area=None):
        """
        使用霍夫圓檢測物件
        
        Args:
            processed: 處理過的影像
            min_area: 最小物件面積 (未使用，保留參數一致性)
            max_area: 最大物件面積 (未使用，保留參數一致性)
            
        Returns:
            valid_objects: 符合條件的物件列表
        """
        if processed is None or processed.size == 0:
            return []
            
        try:
            # 使用霍夫圓檢測
            circles = cv2.HoughCircles(
                processed,
                cv2.HOUGH_GRADIENT,
                dp=self.dp,
                minDist=self.min_dist,
                param1=self.param1,
                param2=self.param2,
                minRadius=self.min_radius,
                maxRadius=self.max_radius
            )
            
            valid_objects = []
            if circles is not None:
                circles = np.uint16(np.around(circles))
                for i in circles[0, :]:
                    # 圓心坐標和半徑
                    center_x, center_y, radius = i[0], i[1], i[2]
                    
                    # 計算外接矩形
                    x = int(center_x - radius)
                    y = int(center_y - radius)
                    w = int(radius * 2)
                    h = int(radius * 2)
                    
                    # 計算面積
                    area = np.pi * (radius ** 2)
                    
                    # 面積過濾
                    min_a = min_area if min_area is not None else self.min_object_area
                    max_a = max_area if max_area is not None else self.max_object_area
                    
                    if min_a < area < max_a:
                        centroid = (center_x, center_y)
                        valid_objects.append((x, y, w, h, centroid))
            
            return valid_objects
            
        except Exception as e:
            logging.error(f"圓形檢測時發生錯誤：{str(e)}")
            return []
    
    def set_parameters(self, params):
        """
        設置處理參數
        
        Args:
            params: 參數字典
            
        Returns:
            bool: 是否成功設置
        """
        try:
            if 'dp' in params:
                self.dp = params['dp']
                
            if 'min_dist' in params:
                self.min_dist = params['min_dist']
                
            if 'param1' in params:
                self.param1 = params['param1']
                
            if 'param2' in params:
                self.param2 = params['param2']
                
            if 'min_radius' in params:
                self.min_radius = params['min_radius']
                
            if 'max_radius' in params:
                self.max_radius = params['max_radius']
                
            if 'min_object_area' in params:
                self.min_object_area = params['min_object_area']
                
            if 'max_object_area' in params:
                self.max_object_area = params['max_object_area']
                
            return True
        except Exception as e:
            logging.error(f"設置圓形檢測參數時發生錯誤：{str(e)}")
            return False 