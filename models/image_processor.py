"""
影像處理模型
處理所有與影像處理相關的功能
支持多種檢測方法，便於擴展
"""
import logging
import cv2 # type: ignore
import numpy as np # type: ignore
from concurrent.futures import ThreadPoolExecutor
from abc import ABC, abstractmethod

# 導入檢測方法管理器
from .detection_methods import get_detection_method, list_available_methods, list_methods_by_type


# ==================================================================
# 檢測方法的抽象基類
# ==================================================================
class DetectionMethod(ABC):
    """檢測方法抽象基類"""
    
    @abstractmethod
    def process_frame(self, frame):
        """處理影像幀"""
        pass
        
    @abstractmethod
    def detect_objects(self, processed_frame, min_area=None, max_area=None):
        """檢測物件"""
        pass
    
    @property
    def name(self):
        """檢測方法名稱"""
        return self.__class__.__name__


# ==================================================================
# 傳統檢測方法：使用背景減除和連通區域分析
# ==================================================================
class TraditionalDetection(DetectionMethod):
    """傳統基於背景減除的檢測方法"""
    
    def __init__(self):
        """初始化傳統檢測方法"""
        # 背景減除器參數
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=20000,           # 使用20000幀歷史
            varThreshold=16,         # 閾值設為16
            detectShadows=True       # 啟用陰影檢測
        )

        # 核心參數
        self.gaussian_kernel = (5, 5)  # 高斯核為5x5
        self.dilate_kernel = np.ones((3, 3), np.uint8)  # 膨脹核為3x3
        self.close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))  # 閉合核為5x5橢圓

        # 閾值參數
        self.canny_threshold1 = 50   # Canny低閾值為50
        self.canny_threshold2 = 110  # Canny高閾值為110
        self.binary_threshold = 30   # 二值化閾值為30
        
        # 物體檢測參數
        self.min_object_area = 10    # 最小物體面積為10
        self.max_object_area = 150   # 最大物體面積為150
        
        logging.info("初始化傳統檢測方法完成")
    
    def process_frame(self, frame):
        """
        使用傳統方法處理單幀影像
        
        Args:
            frame: 輸入的影像幀

        Returns:
            processed_frame: 處理後的影像幀
        """
        if frame is None or frame.size == 0:
            return None

        try:
            # 1. 背景減除
            fg_mask = self.bg_subtractor.apply(frame)
            
            # 2. 高斯模糊去噪
            blurred = cv2.GaussianBlur(frame, self.gaussian_kernel, 0)
            
            # 3. Canny 邊緣檢測
            edges = cv2.Canny(blurred, self.canny_threshold1, self.canny_threshold2)
            
            # 4. 使用前景遮罩過濾邊緣
            result = cv2.bitwise_and(edges, edges, mask=fg_mask)
            
            # 5. 二值化處理
            _, thresh = cv2.threshold(result, self.binary_threshold, 255, cv2.THRESH_BINARY)
            
            # 6. 膨脹操作填充空洞
            dilated = cv2.dilate(thresh, self.dilate_kernel, iterations=1)
            
            # 7. 使用橢圓形核心進行閉合操作
            closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, self.close_kernel)
            
            return closed
            
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
        if processed is None or processed.size == 0:
            return []

        # 使用指定或默認的面積參數
        min_area = min_area if min_area is not None else self.min_object_area
        max_area = max_area if max_area is not None else self.max_object_area

        try:
            # 使用連通區域分析 - 連通度為4
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                processed,
                connectivity=4  # 只考慮上下左右連通，不考慮對角線
            )

            # 過濾物體
            valid_objects = []
            for i in range(1, num_labels):  # 從1開始，忽略背景(0)
                area = stats[i, cv2.CC_STAT_AREA]
                # 按面積過濾物體
                if min_area < area < max_area:
                    x = stats[i, cv2.CC_STAT_LEFT]
                    y = stats[i, cv2.CC_STAT_TOP]
                    w = stats[i, cv2.CC_STAT_WIDTH]
                    h = stats[i, cv2.CC_STAT_HEIGHT]
                    centroid = centroids[i]
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
            if 'min_object_area' in params:
                self.min_object_area = params['min_object_area']

            if 'max_object_area' in params:
                self.max_object_area = params['max_object_area']

            if 'canny_threshold1' in params:
                self.canny_threshold1 = params['canny_threshold1']

            if 'canny_threshold2' in params:
                self.canny_threshold2 = params['canny_threshold2']

            if 'binary_threshold' in params:
                self.binary_threshold = params['binary_threshold']

            # 更新背景減除器
            history = params.get('bg_history', 20000)
            threshold = params.get('bg_threshold', 16)
            shadows = params.get('detect_shadows', True)

            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=history,
                varThreshold=threshold,
                detectShadows=shadows
            )

            return True
        except Exception as e:
            logging.error(f"設置影像處理參數時發生錯誤：{str(e)}")
            return False


# ==================================================================
# 圓形檢測方法：使用霍夫圓檢測
# ==================================================================
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


# ==================================================================
# 深度學習檢測方法的基類
# ==================================================================
class DeepLearningDetection(DetectionMethod):
    """深度學習檢測方法基類"""
    
    def __init__(self):
        """初始化深度學習檢測方法"""
        # 模型參數
        self.confidence_threshold = 0.5  # 置信度閾值
        self.nms_threshold = 0.4  # 非極大值抑制閾值
        self.model_path = None  # 模型路徑
        self.model = None  # 模型實例
        
        logging.info("初始化深度學習檢測方法基類")
    
    @abstractmethod
    def load_model(self, model_path):
        """載入模型"""
        pass
    
    @abstractmethod
    def preprocess(self, frame):
        """前處理"""
        pass
    
    @abstractmethod
    def postprocess(self, outputs, frame_shape):
        """後處理"""
        pass


# ==================================================================
# YOLO系列檢測方法
# ==================================================================
class YOLODetection(DeepLearningDetection):
    """YOLO檢測方法"""
    
    def __init__(self, model_path=None, class_names_path=None):
        """
        初始化YOLO檢測方法
        
        Args:
            model_path: YOLO模型路徑 (.weights文件)
            class_names_path: 類別名稱文件路徑 (.names文件)
        """
        super().__init__()
        self.model_path = model_path
        self.config_path = None  # 配置文件路徑 (.cfg文件)
        self.class_names_path = class_names_path
        self.class_names = []  # 類別名稱列表
        self.input_size = (416, 416)  # 網絡輸入大小
        
        # 載入類別名稱
        if class_names_path:
            self._load_class_names()
        
        # 載入模型
        if model_path:
            self.load_model(model_path)
            
        logging.info("初始化YOLO檢測方法完成")
    
    def _load_class_names(self):
        """載入類別名稱"""
        try:
            with open(self.class_names_path, 'r') as f:
                self.class_names = [line.strip() for line in f.readlines()]
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
        try:
            self.model_path = model_path
            self.config_path = config_path
            
            # 如果沒有指定配置文件，嘗試從模型路徑推斷
            if not config_path and model_path:
                model_dir = os.path.dirname(model_path)
                model_name = os.path.basename(model_path).split('.')[0]
                config_path = os.path.join(model_dir, f"{model_name}.cfg")
            
            # 載入YOLO模型
            if os.path.exists(model_path) and os.path.exists(config_path):
                self.model = cv2.dnn.readNetFromDarknet(config_path, model_path)
                
                # 使用CPU或GPU
                # self.model.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                # self.model.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                
                logging.info(f"YOLO模型已成功載入：{model_path}")
                return True
            else:
                logging.error(f"模型或配置文件不存在：{model_path}, {config_path}")
                return False
                
        except Exception as e:
            logging.error(f"載入YOLO模型時發生錯誤：{str(e)}")
            return False
    
    def process_frame(self, frame):
        """
        使用YOLO檢測方法處理單幀影像
        
        Args:
            frame: 輸入的影像幀
            
        Returns:
            processed_frame: 處理後的影像幀，直接返回原幀
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
            processed: 處理過的影像
            min_area: 最小物件面積
            max_area: 最大物件面積
            
        Returns:
            valid_objects: 符合條件的物件列表
        """
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
            output_layers = self.model.getUnconnectedOutLayersNames()
            
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
            for i in indices:
                if isinstance(i, (list, tuple)):  # OpenCV 4.2 之前的版本
                    i = i[0]
                
                box = boxes[i]
                x, y, w, h = box
                centroid = (int(x + w/2), int(y + h/2))
                
                # 計算面積
                area = w * h
                
                # 應用面積過濾
                min_a = min_area if min_area is not None else 0
                max_a = max_area if max_area is not None else float('inf')
                
                if min_a < area < max_a:
                    valid_objects.append((x, y, w, h, centroid))
            
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
        
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > self.confidence_threshold:
                    # YOLO輸出的是中心點坐標和寬高
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    # 計算左上角坐標
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
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
                
            return True
        except Exception as e:
            logging.error(f"設置YOLO參數時發生錯誤：{str(e)}")
            return False


# ==================================================================
# ImageProcessor主類：綜合管理所有檢測方法
# ==================================================================
class ImageProcessor:
    """影像處理類 - 管理不同的檢測方法"""

    def __init__(self, default_method='background_subtraction'):
        """
        初始化影像處理器
        
        Args:
            default_method: 默認使用的檢測方法
        """
        # 線程池
        self.thread_pool = ThreadPoolExecutor(max_workers=8)
        
        # 獲取所有可用檢測方法
        self.available_methods = list_available_methods()
        self.methods_by_type = {
            'traditional': list_methods_by_type('traditional'),
            'shape': list_methods_by_type('shape'),
            'deep_learning': list_methods_by_type('deep_learning'),
            'specialized': list_methods_by_type('specialized')
        }
        
        # 檢查默認方法是否可用
        if default_method not in self.available_methods:
            logging.warning(f"默認方法 '{default_method}' 不可用，使用 'background_subtraction' 代替")
            default_method = 'background_subtraction'
        
        # 初始化當前方法
        self.current_method_name = default_method
        self.current_method = get_detection_method(default_method)
        
        logging.info(f"影像處理器初始化完成，默認使用 {self.current_method.method_type}/{self.current_method_name} 檢測方法")
    
    def set_detection_method(self, method_name, **kwargs):
        """
        切換檢測方法
        
        Args:
            method_name: 要切換到的檢測方法名稱
            **kwargs: 傳遞給檢測方法構造函數的參數
            
        Returns:
            bool: 是否成功切換
        """
        try:
            # 檢查方法是否可用
            if method_name not in self.available_methods:
                logging.error(f"未知的檢測方法：{method_name}")
                return False
            
            # 創建新的檢測方法實例
            new_method = get_detection_method(method_name, **kwargs)
            
            # 更新當前方法
            self.current_method_name = method_name
            self.current_method = new_method
            
            logging.info(f"成功切換到 {new_method.method_type}/{method_name} 檢測方法")
            return True
            
        except Exception as e:
            logging.error(f"切換檢測方法時出錯：{str(e)}")
            return False
    
    def process_frame(self, frame):
        """
        使用當前檢測方法處理單幀影像
        
        Args:
            frame: 輸入的影像幀

        Returns:
            processed_frame: 處理後的影像幀
        """
        return self.current_method.process_frame(frame)
            
    def detect_objects(self, processed, min_area=None, max_area=None):
        """
        使用當前檢測方法檢測物件

        Args:
            processed: 處理過的影像
            min_area: 最小物件面積 (可選)
            max_area: 最大物件面積 (可選)

        Returns:
            valid_objects: 符合條件的物件列表
        """
        return self.current_method.detect_objects(processed, min_area, max_area)

    def process_multiple_rois(self, frame, roi_lines, roi_height):
        """
        平行處理多個 ROI 區域

        Args:
            frame: 原始影像
            roi_lines: ROI 線列表
            roi_height: ROI 高度

        Returns:
            results: 各 ROI 的處理結果列表 [(roi_line, objects), ...]
        """
        if frame is None or not roi_lines:
            return []

        results = []
        futures = []

        # 提交所有 ROI 處理任務
        for line_y in roi_lines:
            roi = frame[line_y:line_y + roi_height, :]
            future = self.thread_pool.submit(self._process_single_roi, roi, line_y)
            futures.append(future)

        # 收集所有處理結果
        for future in futures:
            try:
                result = future.result(timeout=0.1)  # 設置超時避免阻塞
                if result:
                    results.append(result)
            except Exception as e:
                logging.error(f"ROI 處理時發生錯誤：{str(e)}")

        return results

    def _process_single_roi(self, roi, line_y):
        """處理單個 ROI 的輔助函數"""
        processed = self.process_frame(roi)
        objects = self.detect_objects(processed)
        return (line_y, objects)

    def draw_detection_results(self, frame, objects, max_boxes=3):
        """
        在影像上繪製檢測結果 - 限制顯示框數量

        Args:
            frame: 原始影像
            objects: 檢測到的物件列表
            max_boxes: 最大顯示框數量，默認為3

        Returns:
            frame: 繪製結果後的影像
        """
        if frame is None or not objects:
            return frame

        # 創建結果影像的副本，避免修改原始資料
        result_frame = frame.copy()

        # 如果對象數量超過限制，只選擇最大的幾個框
        if len(objects) > max_boxes:
            # 根據物件面積排序（寬x高）
            sorted_objects = sorted(objects, key=lambda obj: obj[2] * obj[3], reverse=True)
            # 只取最大的幾個
            objects_to_draw = sorted_objects[:max_boxes]
        else:
            objects_to_draw = objects

        # 繪製檢測框
        for x, y, w, h, _ in objects_to_draw:
            cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
            
            # 添加物件索引標籤
            object_idx = objects_to_draw.index((x, y, w, h, _)) + 1
            cv2.putText(result_frame, f"#{object_idx}", 
                       (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        return result_frame

    def set_parameters(self, params):
        """
        設置當前檢測方法的參數

        Args:
            params: 參數字典

        Returns:
            bool: 是否成功設置
        """
        return self.current_method.set_parameters(params)

    def analyze_photo(self, frame):
        """
        分析拍攝的照片，檢測物體

        Args:
            frame: 輸入的圖像幀

        Returns:
            dict: 分析結果字典
        """
        try:
            if frame is None or frame.size == 0:
                return {"success": False, "message": "無效的圖像"}

            # 臨時切換到圓形檢測方法
            original_method = self.current_method_name
            self.set_detection_method('circle')
            
            # 處理幀
            processed = self.process_frame(frame)
            
            # 檢測物體
            detected_objects = self.detect_objects(processed)
            
            # 生成分析結果
            result = {
                "success": True,
                "original_image": frame,
                "processed_image": processed,
                "analysis_result": {
                    "has_objects": len(detected_objects) > 0,
                    "objects_data": detected_objects,
                    "quality_score": 9.81  # 示例評分
                },
                "waveform_data": self._generate_waveform_data(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) > 2 else frame),
            }
            
            # 恢復原始檢測方法
            self.set_detection_method(original_method)
            
            return result

        except Exception as e:
            logging.error(f"分析照片時發生錯誤：{str(e)}")
            return {"success": False, "message": str(e)}

    def _generate_waveform_data(self, gray_image):
        """
        從灰度圖生成波形數據（示例方法）

        Args:
            gray_image: 灰度圖像

        Returns:
            list: 波形數據點
        """
        # 從圖像中間行獲取灰度值作為波形
        height, width = gray_image.shape
        middle_row = gray_image[height // 2, :]

        # 對數據進行下採樣以減少點數
        waveform = [int(middle_row[i]) for i in range(0, width, 5)]

        return waveform

    def draw_analysis_results(self, frame, analysis_result):
        """
        在圖像上繪製分析結果

        Args:
            frame: 原始圖像
            analysis_result: 分析結果

        Returns:
            frame: 繪製結果後的圖像
        """
        if not analysis_result or not analysis_result.get("success", False):
            return frame

        result_frame = frame.copy()
        
        # 如果檢測到物體，繪製它們
        if analysis_result.get("analysis_result", {}).get("has_objects", False):
            objects = analysis_result["analysis_result"]["objects_data"]
            for x, y, w, h, _ in objects:
                # 繪製物體框
                cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # 繪製中心點
                cx, cy = int(x + w/2), int(y + h/2)
                cv2.circle(result_frame, (cx, cy), 2, (0, 0, 255), 3)

        # 添加質量評分
        quality_score = analysis_result.get("analysis_result", {}).get("quality_score", 0)
        cv2.putText(
            result_frame,
            f"Quality: {quality_score:.2f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )

        return result_frame

# 如果需要導入相關模塊
import os