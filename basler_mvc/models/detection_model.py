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
from .detection_base import DetectionMethod

# 標記增強檢測是否可用（稍後動態加載）
ENHANCED_DETECTION_AVAILABLE = False


class CircleDetection(DetectionMethod):
    """霍夫圓檢測方法 - 高性能優化版"""
    
    def __init__(self):
        """初始化圓形檢測"""
        # 🚀 極速優化參數（針對實時處理）
        self.resize_factor = 0.3      # 圖像縮小70%大幅提升性能
        self.dp = 3.0                 # 進一步增大dp減少計算量
        self.min_dist = 30            # 適度調整最小距離
        self.param1 = 120             # 提高閾值減少計算
        self.param2 = 70              # 提高閾值
        self.min_radius = 8           # 調整最小半徑
        self.max_radius = 50          # 限制最大半徑
        self.min_area = 100           # 調整面積範圍
        self.max_area = 5000
        self.blur_kernel = 3          # 使用更小的模糊核
        
        logging.info("✅ 高性能圓形檢測初始化完成")
    
    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """高速幀處理 - 輕量化優化"""
        if frame is None:
            return None
            
        try:
            # 🚀 關鍵優化：縮小圖像處理
            height, width = frame.shape[:2]
            new_height = int(height * self.resize_factor)
            new_width = int(width * self.resize_factor)
            
            # 快速縮放（使用最快的插值方法）
            small_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_NEAREST)
            
            # 轉灰度
            if len(small_frame.shape) == 3:
                gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = small_frame
                
            # 🚀 優化：使用更快的中值濾波
            blurred = cv2.medianBlur(gray, self.blur_kernel)
            return blurred
            
        except Exception as e:
            logging.error(f"處理幀錯誤: {str(e)}")
            return None
    
    def detect_objects(self, processed_frame: np.ndarray, min_area: int = None, max_area: int = None) -> List[Tuple]:
        """高性能霍夫圓檢測"""
        if processed_frame is None:
            return []
            
        try:
            # 🚀 優化的圓檢測（在縮小的圖像上）
            circles = cv2.HoughCircles(
                processed_frame,
                cv2.HOUGH_GRADIENT,
                dp=self.dp,
                minDist=int(self.min_dist * self.resize_factor),
                param1=self.param1,
                param2=self.param2,
                minRadius=int(self.min_radius * self.resize_factor),
                maxRadius=int(self.max_radius * self.resize_factor)
            )
            
            objects = []
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                scale_factor = 1.0 / self.resize_factor
                
                min_a = min_area if min_area is not None else self.min_area
                max_a = max_area if max_area is not None else self.max_area
                
                for (x, y, r) in circles:
                    # 🚀 關鍵：縮放回原始尺寸
                    orig_x = int(x * scale_factor)
                    orig_y = int(y * scale_factor)
                    orig_r = int(r * scale_factor)
                    area = np.pi * orig_r * orig_r
                    
                    if min_a <= area <= max_a:
                        # 返回 (x, y, w, h, centroid, area, radius)
                        bbox_x = int(orig_x - orig_r)
                        bbox_y = int(orig_y - orig_r)
                        bbox_w = int(orig_r * 2)
                        bbox_h = int(orig_r * 2)
                        objects.append((bbox_x, bbox_y, bbox_w, bbox_h, (orig_x, orig_y), area, orig_r))
            
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
                    logging.info(f"更新參數 {key}: {value}")
            return True
        except Exception as e:
            logging.error(f"設置參數錯誤: {str(e)}")
            return False


class ContourDetection(DetectionMethod):
    """輪廓檢測方法 - 增強版"""
    
    def __init__(self):
        """初始化輪廓檢測"""
        self.threshold_value = 127
        self.min_area = 100
        self.max_area = 10000
        self.morphology_kernel_size = 3
        
        # 🎯 新增自適應參數
        self.adaptive_threshold = True
        self.noise_reduction = True
        self.edge_enhancement = True
        
        logging.info("增強輪廓檢測初始化完成")
    
    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """增強幀處理 - 自適應算法"""
        if frame is None:
            return None
            
        try:
            # 轉灰度
            if len(frame.shape) == 3:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                gray = frame
                
            # 🎯 噪聲減少
            if self.noise_reduction:
                gray = cv2.medianBlur(gray, 5)
                
            # 🎯 邊緣增強
            if self.edge_enhancement:
                gray = cv2.addWeighted(gray, 1.5, cv2.GaussianBlur(gray, (0, 0), 2), -0.5, 0)
                
            # 🎯 自適應二值化或固定閾值
            if self.adaptive_threshold:
                binary = cv2.adaptiveThreshold(
                    gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                    cv2.THRESH_BINARY, 11, 2
                )
            else:
                _, binary = cv2.threshold(gray, self.threshold_value, 255, cv2.THRESH_BINARY)
            
            # 形態學處理
            kernel = np.ones((self.morphology_kernel_size, self.morphology_kernel_size), np.uint8)
            processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            processed = cv2.morphologyEx(processed, cv2.MORPH_OPEN, kernel)  # 額外的開運算去除噪點
            
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


class HybridDetection(DetectionMethod):
    """混合檢測方法 - 結合圓形和輪廓檢測的優點"""
    
    def __init__(self):
        """初始化混合檢測"""
        self.circle_detector = CircleDetection()
        self.contour_detector = ContourDetection()
        
        # 混合策略參數
        self.use_circle_primary = True  # 優先使用圓形檢測
        self.confidence_threshold = 0.7  # 置信度閾值
        self.merge_nearby_detections = True  # 合併鄰近檢測
        self.merge_distance_threshold = 50  # 合併距離閾值
        
        # 自適應參數
        self.auto_switch_method = True  # 根據檢測效果自動切換方法
        self.circle_success_rate = 1.0  # 圓形檢測成功率
        self.contour_success_rate = 1.0  # 輪廓檢測成功率
        
        logging.info("🔄 混合檢測初始化完成")
    
    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """混合預處理 - 同時為兩種檢測方法準備"""
        if frame is None:
            return None
        
        # 返回原始幀，讓各個檢測方法自己處理
        return frame
    
    def detect_objects(self, frame: np.ndarray, min_area: int = None, max_area: int = None) -> List[Tuple]:
        """混合檢測 - 智能結合多種方法"""
        if frame is None:
            return []
        
        try:
            circle_objects = []
            contour_objects = []
            
            # 🎯 並行檢測（如果性能允許）
            if self.use_circle_primary:
                # 先嘗試圓形檢測
                processed_circle = self.circle_detector.process_frame(frame)
                if processed_circle is not None:
                    circle_objects = self.circle_detector.detect_objects(
                        processed_circle, min_area, max_area
                    )
                
                # 如果圓形檢測結果不理想，補充輪廓檢測
                if len(circle_objects) == 0 or self.auto_switch_method:
                    processed_contour = self.contour_detector.process_frame(frame)
                    if processed_contour is not None:
                        contour_objects = self.contour_detector.detect_objects(
                            processed_contour, min_area, max_area
                        )
            else:
                # 優先輪廓檢測
                processed_contour = self.contour_detector.process_frame(frame)
                if processed_contour is not None:
                    contour_objects = self.contour_detector.detect_objects(
                        processed_contour, min_area, max_area
                    )
                
                # 補充圓形檢測
                if len(contour_objects) == 0 or self.auto_switch_method:
                    processed_circle = self.circle_detector.process_frame(frame)
                    if processed_circle is not None:
                        circle_objects = self.circle_detector.detect_objects(
                            processed_circle, min_area, max_area
                        )
            
            # 🎯 智能融合結果
            final_objects = self._merge_detections(circle_objects, contour_objects)
            
            # 🎯 更新成功率統計（用於自動切換方法）
            if self.auto_switch_method:
                self._update_success_rates(len(circle_objects), len(contour_objects))
            
            return final_objects
            
        except Exception as e:
            logging.error(f"混合檢測錯誤: {str(e)}")
            return []
    
    def _merge_detections(self, circle_objects: List[Tuple], contour_objects: List[Tuple]) -> List[Tuple]:
        """智能融合檢測結果"""
        if not self.merge_nearby_detections:
            # 簡單策略：選擇較好的結果
            if len(circle_objects) >= len(contour_objects):
                return circle_objects
            else:
                return contour_objects
        
        # 高級策略：合併鄰近檢測，去除重複
        all_objects = []
        all_objects.extend([(obj, 'circle') for obj in circle_objects])
        all_objects.extend([(obj, 'contour') for obj in contour_objects])
        
        if not all_objects:
            return []
        
        merged_objects = []
        used_indices = set()
        
        for i, (obj1, type1) in enumerate(all_objects):
            if i in used_indices:
                continue
                
            x1, y1, w1, h1, centroid1, area1, radius1 = obj1
            group = [obj1]
            used_indices.add(i)
            
            # 尋找鄰近的檢測結果
            for j, (obj2, type2) in enumerate(all_objects[i+1:], i+1):
                if j in used_indices:
                    continue
                    
                x2, y2, w2, h2, centroid2, area2, radius2 = obj2
                distance = np.sqrt((centroid1[0] - centroid2[0])**2 + (centroid1[1] - centroid2[1])**2)
                
                if distance < self.merge_distance_threshold:
                    group.append(obj2)
                    used_indices.add(j)
            
            # 從群組中選擇最佳檢測結果
            if len(group) == 1:
                merged_objects.append(group[0])
            else:
                best_obj = self._select_best_detection(group)
                merged_objects.append(best_obj)
        
        return merged_objects
    
    def _select_best_detection(self, group: List[Tuple]) -> Tuple:
        """從群組中選擇最佳檢測結果"""
        # 簡單策略：選擇面積最接近中位數的檢測結果
        areas = [obj[5] for obj in group]  # area is at index 5
        median_area = np.median(areas)
        
        best_obj = group[0]
        min_diff = abs(best_obj[5] - median_area)
        
        for obj in group[1:]:
            diff = abs(obj[5] - median_area)
            if diff < min_diff:
                min_diff = diff
                best_obj = obj
        
        return best_obj
    
    def _update_success_rates(self, circle_count: int, contour_count: int):
        """更新檢測方法成功率統計"""
        # 簡化的成功率評估
        decay_factor = 0.95  # 衰減因子
        
        self.circle_success_rate = (self.circle_success_rate * decay_factor + 
                                  (1.0 if circle_count > 0 else 0.0) * (1 - decay_factor))
        self.contour_success_rate = (self.contour_success_rate * decay_factor + 
                                   (1.0 if contour_count > 0 else 0.0) * (1 - decay_factor))
        
        # 自動調整優先檢測方法
        if self.circle_success_rate > self.contour_success_rate + 0.1:
            self.use_circle_primary = True
        elif self.contour_success_rate > self.circle_success_rate + 0.1:
            self.use_circle_primary = False
    
    def set_parameters(self, params: Dict[str, Any]) -> bool:
        """設置混合檢測參數"""
        try:
            # 更新自身參數
            for key, value in params.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            # 將相關參數傳遞給子檢測器
            self.circle_detector.set_parameters(params)
            self.contour_detector.set_parameters(params)
            
            return True
        except Exception as e:
            logging.error(f"設置混合檢測參數錯誤: {str(e)}")
            return False
    
    @property
    def name(self) -> str:
        return "HybridDetection"


class DetectionModel:
    """影像檢測數據模型 - 高性能版本"""
    
    def __init__(self):
        """初始化檢測模型"""
        # 可用檢測方法
        self.available_methods = {
            'circle': CircleDetection(),
            'contour': ContourDetection(),
            'hybrid': HybridDetection()  # 🎯 新增混合檢測方法
        }
        
        # 🚀 嘗試加載背景減除檢測方法
        try:
            from .enhanced_detection_method import BackgroundSubtractionDetection
            self.available_methods['background'] = BackgroundSubtractionDetection()
            logging.info("✅ 背景減除檢測方法已載入")
            background_available = True
        except Exception as e:
            logging.warning(f"⚠️ 背景減除檢測方法不可用: {str(e)}")
            background_available = False
        
        # 當前檢測方法 - 優先使用背景減除檢測
        if background_available:
            self.current_method = self.available_methods['background']
            self.method_name = 'background'
            logging.info("🎯 預設使用背景減除檢測方法")
        else:
            self.current_method = self.available_methods['hybrid']
            self.method_name = 'hybrid'
            logging.info("🎯 預設使用混合檢測方法")
        
        # 數據源類型和對應參數
        self.current_source_type = 'camera'  # camera, video
        self.source_params = {
            'camera': {
                'min_area': 100,
                'max_area': 5000,
                'resize_factor': 0.5,  # 工業相機高精度模式
                'high_performance_mode': True
            },
            'video': {
                'min_area': 100,
                'max_area': 5000,
                'resize_factor': 0.5,  # 🎯 視頻回放也使用高精度（GPU加速補償）
                'high_performance_mode': True,  # 🚀 啟用高性能模式
                'gpu_optimized': True  # 🎯 視頻模式優先使用GPU
            }
        }
        
        # 檢測參數 - 根據當前數據源動態設定
        self.detection_params = {
            'enable_detection': True,
            **self.source_params['camera']  # 預設使用相機參數
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
    
    def set_source_type(self, source_type: str, video_info: Dict[str, Any] = None) -> bool:
        """設置數據源類型：camera 或 video，支持動態參數調整"""
        if source_type not in ['camera', 'video']:
            logging.error(f"不支持的數據源類型: {source_type}")
            return False
            
        self.current_source_type = source_type
        
        if source_type == 'video' and video_info:
            # 🎯 新功能：根據實際視頻數據動態調整參數
            optimized_params = self._analyze_video_and_optimize_params(video_info)
            source_params = optimized_params
            
            logging.info(f"🎬 根據視頻規格動態優化參數:")
            logging.info(f"解析度: {video_info.get('width', 'N/A')}x{video_info.get('height', 'N/A')}")
            logging.info(f"FPS: {video_info.get('fps', 'N/A'):.2f}")
            logging.info(f"優化後參數: {optimized_params}")
        else:
            # 使用預設參數
            source_params = self.source_params[source_type]
            logging.info(f"使用預設參數: {source_params}")
        
        # 更新檢測參數
        self.detection_params.update(source_params)
        
        # 同時更新當前檢測方法的參數
        self.current_method.set_parameters(source_params)
        
        logging.info(f"數據源已切換為: {source_type}")
        
        self.notify_observers('source_type_changed', {
            'source_type': source_type,
            'params': source_params,
            'video_info': video_info
        })
        
        return True
    
    def _analyze_video_and_optimize_params(self, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """根據視頻實際數據分析並優化檢測參數"""
        try:
            # 獲取視頻實際規格
            width = video_info.get('width', 640)
            height = video_info.get('height', 480)
            fps = video_info.get('fps', 30.0)
            codec = video_info.get('codec', 'unknown')
            total_frames = video_info.get('total_frames', 0)
            
            # 計算解析度等級
            resolution_pixels = width * height
            
            # 🎯 根據解析度動態調整參數
            if resolution_pixels >= 1920 * 1080:  # 1080p以上
                resize_factor = 0.3  # 高解析度，大幅縮小
                min_radius = 15
                max_radius = 80
                min_area = 200
                max_area = 8000
                logging.info("📺 高解析度視頻，使用優化參數")
            elif resolution_pixels >= 1280 * 720:  # 720p
                resize_factor = 0.4
                min_radius = 10
                max_radius = 60
                min_area = 150
                max_area = 6000
                logging.info("📺 中解析度視頻，使用標準參數")
            else:  # 480p及以下
                resize_factor = 0.6
                min_radius = 5
                max_radius = 40
                min_area = 80
                max_area = 4000
                logging.info("📺 低解析度視頻，使用精細參數")
            
            # 🎯 根據 FPS 調整性能參數 - 更細緻的分級
            if fps >= 120:
                # 超高幀率，極優先性能
                dp = 4.0
                param1 = 150
                param2 = 100
                logging.info(f"⚡ 超高幀率視頻 ({fps:.1f} fps)，極優先性能")
            elif fps >= 60:
                # 高幀率，優先性能
                dp = 3.0
                param1 = 120
                param2 = 80
                logging.info(f"🚀 高幀率視頻 ({fps:.1f} fps)，優先性能")
            elif fps >= 30:
                # 標準幀率，平衡性能和精度
                dp = 2.5
                param1 = 100
                param2 = 65
                logging.info(f"📺 標準幀率視頻 ({fps:.1f} fps)，平衡模式")
            elif fps >= 15:
                # 低幀率，優先精度
                dp = 2.0
                param1 = 80
                param2 = 50
                logging.info(f"🔍 低幀率視頻 ({fps:.1f} fps)，優先精度")
            else:
                # 極低幀率，最高精度
                dp = 1.5
                param1 = 60
                param2 = 40
                logging.info(f"🔬 極低幀率視頻 ({fps:.1f} fps)，最高精度")
            
            # 🎯 根據編碼格式調整
            blur_kernel = 3  # 預設
            if codec.lower() in ['h264', 'h265', 'hevc']:
                blur_kernel = 5  # 壓縮編碼，增加模糊以減少噪點
                logging.info(f"🎥 壓縮編碼 ({codec})，調整模糊參數")
            
            # 🎯 組合優化參數
            optimized_params = {
                'min_area': min_area,
                'max_area': max_area,
                'resize_factor': resize_factor,
                'high_performance_mode': True,
                'gpu_optimized': True,
                # CircleDetection 參數
                'dp': dp,
                'min_dist': int(30 * resize_factor),  # 按縮放比例調整
                'param1': param1,
                'param2': param2,
                'min_radius': min_radius,
                'max_radius': max_radius,
                'blur_kernel': blur_kernel,
                # 視頻規格信息用於記錄
                'source_resolution': f"{width}x{height}",
                'source_fps': fps,
                'source_codec': codec
            }
            
            return optimized_params
            
        except Exception as e:
            logging.error(f"分析視頻參數失敗: {e}")
            # 返回安全的預設參數
            return self.source_params['video'].copy()
    
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
            
            # 更新性能統計 - 防止記憶體洩漏
            detection_time = time.time() - start_time
            self.detection_times.append(detection_time)
            
            # 限制列表大小，防止記憶體無限增長
            if len(self.detection_times) > 100:  # 保持最新100次檢測時間
                self.detection_times.pop(0)
            
            if len(self.detection_times) >= 10:
                avg_time = sum(self.detection_times) / len(self.detection_times)
                self.detection_fps = 1.0 / avg_time if avg_time > 0 else 0
            
            # 🚀 性能優化：只在需要時複製幀
            if len(objects) > 0:
                # 有檢測結果時才複製和繪製
                result_frame = self._draw_detections(frame.copy(), objects)
            else:
                # 無檢測結果時直接在原圖上繪製計數
                result_frame = frame
                cv2.putText(result_frame, f'Count: 0', 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
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