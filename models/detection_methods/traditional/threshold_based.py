"""
閾值基礎檢測方法
使用不同的閾值處理技術進行物體檢測
"""
import cv2
import numpy as np
import logging
from ..base_detection import DetectionMethod

class ThresholdBasedDetection(DetectionMethod):
    """基於閾值的傳統檢測方法"""
    
    def __init__(self):
        """初始化閾值基礎檢測方法"""
        # 閾值處理參數
        self.threshold_value = 127  # 閾值
        self.max_binary_value = 255  # 閾值處理的最大值
        self.threshold_type = cv2.THRESH_BINARY  # 閾值處理類型
        self.adaptive_method = cv2.ADAPTIVE_THRESH_GAUSSIAN_C  # 自適應閾值方法
        self.block_size = 11  # 用於計算閾值的區域大小
        self.c_value = 2  # 從平均值或加權平均值中減去的常數
        
        # 使用自適應閾值
        self.use_adaptive = False
        
        # 物體檢測參數
        self.min_object_area = 10
        self.max_object_area = 150
        
        logging.info("初始化閾值基礎檢測方法完成")
    
    @property
    def method_type(self):
        """檢測方法類型"""
        return "traditional"
    
    def process_frame(self, frame):
        """
        使用閾值方法處理單幀影像
        
        Args:
            frame: 輸入的影像幀

        Returns:
            processed_frame: 處理後的影像幀
        """
        if frame is None or frame.size == 0:
            return None

        try:
            # 將影像轉換為灰度
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 根據設置選擇普通閾值或自適應閾值
            if self.use_adaptive:
                # 使用自適應閾值處理
                binary = cv2.adaptiveThreshold(
                    gray,
                    self.max_binary_value,
                    self.adaptive_method,
                    self.threshold_type,
                    self.block_size,
                    self.c_value
                )
            else:
                # 使用全局閾值處理
                _, binary = cv2.threshold(
                    gray,
                    self.threshold_value,
                    self.max_binary_value,
                    self.threshold_type
                )
            
            # 此處可以添加額外的處理步驟，如形態學操作等
            # 注意：這個方法只是示例，尚未完全實現
            
            return binary
            
        except Exception as e:
            logging.error(f"處理幀時發生錯誤: {str(e)}")
            return None
            
    def detect_objects(self, processed, min_area=None, max_area=None):
        """
        使用連通區域分析檢測物件

        Args:
            processed: 處理過的影像
            min_area: 最小物件面積 (可選)
            max_area: 最大物件面積 (可選)

        Returns:
            valid_objects: 符合條件的物件列表
        """
        # 注意：這個方法只是示例，尚未完全實現
        if processed is None or processed.size == 0:
            return []

        # 使用指定或默認的面積參數
        min_area = min_area if min_area is not None else self.min_object_area
        max_area = max_area if max_area is not None else self.max_object_area

        try:
            # 使用連通區域分析
            contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 過濾物體
            valid_objects = []
            for contour in contours:
                area = cv2.contourArea(contour)
                if min_area < area < max_area:
                    x, y, w, h = cv2.boundingRect(contour)
                    moments = cv2.moments(contour)
                    if moments["m00"] != 0:
                        cx = int(moments["m10"] / moments["m00"])
                        cy = int(moments["m01"] / moments["m00"])
                    else:
                        cx, cy = x + w // 2, y + h // 2
                    
                    centroid = (cx, cy)
                    valid_objects.append((x, y, w, h, centroid))
            
            return valid_objects
            
        except Exception as e:
            logging.error(f"物件檢測時發生錯誤：{str(e)}")
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
            if 'threshold_value' in params:
                self.threshold_value = params['threshold_value']
                
            if 'max_binary_value' in params:
                self.max_binary_value = params['max_binary_value']
                
            if 'threshold_type' in params:
                self.threshold_type = params['threshold_type']
                
            if 'use_adaptive' in params:
                self.use_adaptive = params['use_adaptive']
                
            if 'adaptive_method' in params:
                self.adaptive_method = params['adaptive_method']
                
            if 'block_size' in params:
                self.block_size = params['block_size']
                
            if 'c_value' in params:
                self.c_value = params['c_value']
                
            if 'min_object_area' in params:
                self.min_object_area = params['min_object_area']
                
            if 'max_object_area' in params:
                self.max_object_area = params['max_object_area']
                
            return True
        except Exception as e:
            logging.error(f"設置閾值處理參數時發生錯誤：{str(e)}")
            return False 