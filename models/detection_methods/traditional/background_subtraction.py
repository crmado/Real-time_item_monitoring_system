"""
背景減除檢測方法
使用背景減除和連通區域分析進行檢測
移植自原始 image_processor.py 中的功能
"""
import cv2
import numpy as np
import logging
from ..base_detection import DetectionMethod

class BackgroundSubtractionDetection(DetectionMethod):
    """基於背景減除的傳統檢測方法"""
    
    def __init__(self):
        """初始化背景減除檢測方法"""
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
        
        logging.info("初始化背景減除檢測方法完成")
    
    @property
    def method_type(self):
        """檢測方法類型"""
        return "traditional"
    
    def process_frame(self, frame):
        """
        使用背景減除方法處理單幀影像
        
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