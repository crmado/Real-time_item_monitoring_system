"""
YOLO 檢測方法
使用 YOLO (You Only Look Once) 深度學習模型進行物體檢測
"""
import cv2
import numpy as np
import logging
import os
from ..base_detection import DetectionMethod

class YOLODetection(DetectionMethod):
    """基於YOLO的深度學習檢測方法"""
    
    def __init__(self, model_path=None, config_path=None, class_names_path=None):
        """
        初始化YOLO檢測方法
        
        Args:
            model_path: YOLO模型路徑 (.weights文件)
            config_path: 配置文件路徑 (.cfg文件)
            class_names_path: 類別名稱文件路徑 (.names文件)
        """
        # 模型參數
        self.confidence_threshold = 0.5  # 置信度閾值
        self.nms_threshold = 0.4  # 非極大值抑制閾值
        self.input_size = (416, 416)  # 網絡輸入大小
        
        # 模型路徑
        self.model_path = model_path
        self.config_path = config_path
        self.class_names_path = class_names_path
        
        # 類別名稱
        self.class_names = []
        
        # 模型實例
        self.model = None
        
        # 載入類別名稱
        if class_names_path and os.path.exists(class_names_path):
            self._load_class_names()
        
        # 載入模型
        if model_path and config_path and os.path.exists(model_path) and os.path.exists(config_path):
            self.load_model(model_path, config_path)
        
        logging.info("初始化YOLO檢測方法完成")
    
    @property
    def method_type(self):
        """檢測方法類型"""
        return "deep_learning"
    
    def _load_class_names(self):
        """載入類別名稱"""
        try:
            with open(self.class_names_path, 'r') as f:
                self.class_names = [line.strip() for line in f.readlines()]
            logging.info(f"成功載入 {len(self.class_names)} 個類別名稱")
        except Exception as e:
            logging.error(f"載入類別名稱時發生錯誤：{str(e)}")
    
    def load_model(self, model_path, config_path=None):
        """
        載入YOLO模型
        
        Args:
            model_path: 模型路徑
            config_path: 配置文件路徑
            
        Returns:
            bool: 是否成功載入
        """
        # 注意：此方法僅作為示例，實際使用需要確保模型文件存在
        try:
            # 更新路徑
            self.model_path = model_path
            if config_path:
                self.config_path = config_path
            
            # 檢查文件是否存在
            if not os.path.exists(model_path):
                logging.error(f"模型文件不存在：{model_path}")
                return False
            
            if not os.path.exists(self.config_path):
                logging.error(f"配置文件不存在：{self.config_path}")
                return False
            
            # 使用OpenCV的DNN模塊載入YOLO模型
            # 注意：在實際部署中，需要確保OpenCV支持深度學習模型
            logging.info(f"正在載入YOLO模型：{model_path}")
            self.model = cv2.dnn.readNetFromDarknet(self.config_path, self.model_path)
            
            # 設置計算後端（可選）
            # 使用CPU或GPU
            # self.model.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            # self.model.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            
            logging.info("YOLO模型載入成功")
            return True
        except Exception as e:
            logging.error(f"載入YOLO模型時發生錯誤：{str(e)}")
            self.model = None
            return False
    
    def process_frame(self, frame):
        """
        使用YOLO處理單幀影像
        
        Args:
            frame: 輸入的影像幀
            
        Returns:
            processed_frame: 處理後的影像幀，對於YOLO直接返回原幀
        """
        # YOLO不需要特殊的前處理，直接返回原始幀
        return frame
    
    def preprocess(self, frame):
        """
        YOLO輸入前處理
        
        Args:
            frame: 輸入的影像幀
            
        Returns:
            blob: 網絡輸入
        """
        if frame is None or frame.size == 0:
            return None
            
        try:
            # 創建blob
            blob = cv2.dnn.blobFromImage(
                frame, 
                1/255.0, 
                self.input_size, 
                [0, 0, 0], 
                swapRB=True, 
                crop=False
            )
            return blob
        except Exception as e:
            logging.error(f"YOLO前處理時發生錯誤：{str(e)}")
            return None
    
    def detect_objects(self, processed, min_area=None, max_area=None):
        """
        使用YOLO檢測物件
        
        Args:
            processed: 處理過的影像 (原始幀)
            min_area: 最小物件面積
            max_area: 最大物件面積
            
        Returns:
            valid_objects: 符合條件的物件列表
        """
        # 注意：此方法為示例實現，實際使用需要YOLO模型文件
        # 如果模型尚未載入，返回空列表
        if processed is None or processed.size == 0 or self.model is None:
            return []
            
        try:
            # 獲取圖像尺寸
            height, width = processed.shape[:2]
            
            # 前處理
            blob = self.preprocess(processed)
            if blob is None:
                return []
                
            # 設置輸入
            self.model.setInput(blob)
            
            # 獲取輸出層名稱
            layer_names = self.model.getLayerNames()
            output_layers = [layer_names[i - 1] for i in self.model.getUnconnectedOutLayers()]
            
            # 前向傳播
            outputs = self.model.forward(output_layers)
            
            # 後處理獲取檢測框
            boxes, confidences, class_ids = self.postprocess(outputs, (width, height))
            
            # 應用非極大值抑制
            indices = cv2.dnn.NMSBoxes(
                boxes, 
                confidences, 
                self.confidence_threshold, 
                self.nms_threshold
            )
            
            # 格式化為統一格式
            valid_objects = []
            
            # 檢查indices是否為空
            if len(indices) > 0:
                for i in indices:
                    # OpenCV版本兼容性處理
                    if isinstance(i, (list, tuple)):  # OpenCV 4.2 之前的版本
                        i = i[0]
                    
                    box = boxes[i]
                    x, y, w, h = box
                    centroid = (int(x + w/2), int(y + h/2))
                    
                    # 計算面積
                    area = w * h
                    
                    # 應用面積過濾（如果指定）
                    min_a = 0 if min_area is None else min_area
                    max_a = float('inf') if max_area is None else max_area
                    
                    if min_a <= area <= max_a:
                        valid_objects.append((int(x), int(y), int(w), int(h), centroid))
            
            return valid_objects
            
        except Exception as e:
            logging.error(f"YOLO檢測時發生錯誤：{str(e)}")
            return []
    
    def postprocess(self, outputs, frame_shape):
        """
        YOLO輸出後處理
        
        Args:
            outputs: 網絡輸出
            frame_shape: 幀尺寸 (width, height)
            
        Returns:
            boxes: 檢測框列表
            confidences: 置信度列表
            class_ids: 類別ID列表
        """
        boxes = []
        confidences = []
        class_ids = []
        
        width, height = frame_shape
        
        # 處理每個輸出層
        for output in outputs:
            # 處理每個檢測結果
            for detection in output:
                # YOLO輸出格式：[center_x, center_y, width, height, object_confidence, class_scores...]
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                # 過濾低置信度的檢測結果
                if confidence > self.confidence_threshold:
                    # YOLO輸出的是相對坐標，需要轉換為絕對坐標
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    # 計算左上角坐標
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    # 添加到結果列表
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        return boxes, confidences, class_ids
    
    def set_parameters(self, params):
        """
        設置處理參數
        
        Args:
            params: 參數字典
            
        Returns:
            bool: 是否成功設置
        """
        try:
            if 'confidence_threshold' in params:
                self.confidence_threshold = params['confidence_threshold']
                
            if 'nms_threshold' in params:
                self.nms_threshold = params['nms_threshold']
                
            if 'input_size' in params:
                self.input_size = params['input_size']
                
            # 模型路徑相關參數
            if 'model_path' in params and 'config_path' in params:
                model_path = params['model_path']
                config_path = params['config_path']
                if os.path.exists(model_path) and os.path.exists(config_path):
                    self.load_model(model_path, config_path)
            
            if 'class_names_path' in params:
                class_names_path = params['class_names_path']
                if os.path.exists(class_names_path):
                    self.class_names_path = class_names_path
                    self._load_class_names()
                
            return True
        except Exception as e:
            logging.error(f"設置YOLO參數時發生錯誤：{str(e)}")
            return False 