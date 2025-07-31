"""
影像檢測 Model - MVC 架構核心
專注於核心影像識別算法的數據管理
"""

import cv2
import numpy as np
import logging
import threading
import time
from typing import Optional, List, Dict, Any, Tuple, Callable
from collections import deque
from abc import ABC, abstractmethod


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


class CircleDetection(DetectionMethod):
    """霍夫圓檢測方法 - 精簡版"""
    
    def __init__(self):
        """初始化圓形檢測"""
        # 高效參數設置
        self.dp = 1.2
        self.min_dist = 20
        self.param1 = 50
        self.param2 = 30
        self.min_radius = 5
        self.max_radius = 100
        self.min_area = 50
        self.max_area = 8000
        
        logging.info("圓形檢測初始化完成")
    
    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """快速幀處理"""
        if frame is None:
            return None
            
        try:
            # 轉灰度
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
                
            # 高斯濾波
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            return blurred
            
        except Exception as e:
            logging.error(f"處理幀錯誤: {str(e)}")
            return None
    
    def detect_objects(self, processed_frame: np.ndarray, min_area: int = None, max_area: int = None) -> List[Tuple]:
        """霍夫圓檢測"""
        if processed_frame is None:
            return []
            
        try:
            circles = cv2.HoughCircles(
                processed_frame,
                cv2.HOUGH_GRADIENT,
                dp=self.dp,
                minDist=self.min_dist,
                param1=self.param1,
                param2=self.param2,
                minRadius=self.min_radius,
                maxRadius=self.max_radius
            )
            
            objects = []
            if circles is not None:
                circles = np.uint16(np.around(circles))
                
                min_a = min_area if min_area is not None else self.min_area
                max_a = max_area if max_area is not None else self.max_area
                
                for i in circles[0, :]:
                    x, y, r = i[0], i[1], i[2]
                    area = np.pi * (r ** 2)
                    
                    if min_a <= area <= max_a:
                        # 返回 (x, y, w, h, centroid, area, radius)
                        bbox_x = int(x - r)
                        bbox_y = int(y - r)
                        bbox_w = int(r * 2)
                        bbox_h = int(r * 2)
                        objects.append((bbox_x, bbox_y, bbox_w, bbox_h, (x, y), area, r))
            
            return objects
            
        except Exception as e:
            logging.error(f"圓檢測錯誤: {str(e)}")
            return []
    
    def set_parameters(self, params: Dict[str, Any]) -> bool:
        """設置檢測參數"""
        try:
            for key, value in params.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            logging.error(f"設置參數錯誤: {str(e)}")
            return False


class ContourDetection(DetectionMethod):
    """輪廓檢測方法 - 精簡版"""
    
    def __init__(self):
        """初始化輪廓檢測"""
        self.threshold_value = 127
        self.min_area = 100
        self.max_area = 10000
        self.morphology_kernel_size = 3
        
        logging.info("輪廓檢測初始化完成")
    
    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """快速幀處理"""
        if frame is None:
            return None
            
        try:
            # 轉灰度
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
                
            # 二值化
            _, binary = cv2.threshold(gray, self.threshold_value, 255, cv2.THRESH_BINARY)
            
            # 形態學處理
            kernel = np.ones((self.morphology_kernel_size, self.morphology_kernel_size), np.uint8)
            processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            
            return processed
            
        except Exception as e:
            logging.error(f"處理幀錯誤: {str(e)}")
            return None
    
    def detect_objects(self, processed_frame: np.ndarray, min_area: int = None, max_area: int = None) -> List[Tuple]:
        """輪廓檢測"""
        if processed_frame is None:
            return []
            
        try:
            contours, _ = cv2.findContours(processed_frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            objects = []
            min_a = min_area if min_area is not None else self.min_area
            max_a = max_area if max_area is not None else self.max_area
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                if min_a <= area <= max_a:
                    x, y, w, h = cv2.boundingRect(contour)
                    centroid_x = x + w // 2
                    centroid_y = y + h // 2
                    objects.append((x, y, w, h, (centroid_x, centroid_y), area, 0))
            
            return objects
            
        except Exception as e:
            logging.error(f"輪廓檢測錯誤: {str(e)}")
            return []
    
    def set_parameters(self, params: Dict[str, Any]) -> bool:
        """設置檢測參數"""
        try:
            for key, value in params.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            logging.error(f"設置參數錯誤: {str(e)}")
            return False


class DetectionModel:
    """影像檢測數據模型 - 高性能版本"""
    
    def __init__(self):
        """初始化檢測模型"""
        # 可用檢測方法
        self.available_methods = {
            'circle': CircleDetection(),
            'contour': ContourDetection()
        }
        
        # 當前檢測方法
        self.current_method = self.available_methods['circle']
        self.method_name = 'circle'
        
        # 檢測參數
        self.detection_params = {
            'min_area': 100,
            'max_area': 5000,
            'enable_detection': True
        }
        
        # 檢測結果
        self.latest_objects = []
        self.object_count = 0
        self.detection_lock = threading.Lock()
        
        # 性能統計
        self.detection_times = deque(maxlen=100)
        self.detection_fps = 0.0
        
        # 觀察者模式
        self.observers = []
        
        logging.info("檢測模型初始化完成")
    
    def add_observer(self, observer: Callable):
        """添加觀察者"""
        self.observers.append(observer)
    
    def notify_observers(self, event_type: str, data: Any = None):
        """通知觀察者"""
        for observer in self.observers:
            try:
                observer(event_type, data)
            except Exception as e:
                logging.error(f"通知觀察者錯誤: {str(e)}")
    
    def set_detection_method(self, method_name: str) -> bool:
        """設置檢測方法"""
        if method_name in self.available_methods:
            self.current_method = self.available_methods[method_name]
            self.method_name = method_name
            logging.info(f"切換檢測方法: {method_name}")
            self.notify_observers('method_changed', method_name)
            return True
        return False
    
    def update_parameters(self, params: Dict[str, Any]) -> bool:
        """更新檢測參數"""
        try:
            self.detection_params.update(params)
            
            # 更新當前檢測方法的參數
            method_params = {k: v for k, v in params.items() 
                           if k not in ['min_area', 'max_area', 'enable_detection']}
            
            if method_params:
                self.current_method.set_parameters(method_params)
            
            self.notify_observers('parameters_updated', self.detection_params)
            return True
        except Exception as e:
            logging.error(f"更新參數錯誤: {str(e)}")
            return False
    
    def detect_frame(self, frame: np.ndarray) -> Tuple[List[Tuple], np.ndarray]:
        """檢測單幀 - 高性能版本"""
        if frame is None or not self.detection_params.get('enable_detection', True):
            return [], frame
        
        start_time = time.time()
        
        try:
            # 預處理
            processed_frame = self.current_method.process_frame(frame)
            if processed_frame is None:
                return [], frame
            
            # 檢測物件
            objects = self.current_method.detect_objects(
                processed_frame,
                self.detection_params.get('min_area'),
                self.detection_params.get('max_area')
            )
            
            # 更新結果
            with self.detection_lock:
                self.latest_objects = objects
                self.object_count = len(objects)
            
            # 更新性能統計
            detection_time = time.time() - start_time
            self.detection_times.append(detection_time)
            
            if len(self.detection_times) >= 10:
                avg_time = sum(self.detection_times) / len(self.detection_times)
                self.detection_fps = 1.0 / avg_time if avg_time > 0 else 0
            
            # 繪製檢測結果
            result_frame = self._draw_detections(frame.copy(), objects)
            
            # 通知觀察者
            self.notify_observers('detection_completed', {
                'object_count': len(objects),
                'detection_fps': self.detection_fps,
                'objects': objects
            })
            
            return objects, result_frame
            
        except Exception as e:
            logging.error(f"檢測錯誤: {str(e)}")
            return [], frame
    
    def _draw_detections(self, frame: np.ndarray, objects: List[Tuple]) -> np.ndarray:
        """繪製檢測結果"""
        try:
            for obj in objects:
                x, y, w, h, centroid, area, radius = obj
                
                # 繪製邊界框
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # 繪製中心點
                cv2.circle(frame, centroid, 3, (255, 0, 0), -1)
                
                # 如果是圓檢測，繪製圓
                if self.method_name == 'circle' and radius > 0:
                    cv2.circle(frame, centroid, int(radius), (0, 0, 255), 2)
                
                # 標註面積
                cv2.putText(frame, f'{int(area)}', 
                           (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 顯示總數
            cv2.putText(frame, f'Count: {len(objects)}', 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            return frame
            
        except Exception as e:
            logging.error(f"繪製檢測結果錯誤: {str(e)}")
            return frame
    
    def get_latest_results(self) -> Dict[str, Any]:
        """獲取最新檢測結果"""
        with self.detection_lock:
            return {
                'objects': self.latest_objects.copy(),
                'count': self.object_count,
                'method': self.method_name,
                'detection_fps': self.detection_fps,
                'parameters': self.detection_params.copy()
            }
    
    def get_available_methods(self) -> List[str]:
        """獲取可用檢測方法"""
        return list(self.available_methods.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取檢測統計"""
        return {
            'current_method': self.method_name,
            'object_count': self.object_count,
            'detection_fps': self.detection_fps,
            'available_methods': self.get_available_methods(),
            'parameters': self.detection_params.copy()
        }