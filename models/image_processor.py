"""
影像處理模型
處理所有與影像處理相關的功能
"""

import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor


class ImageProcessor:
    """影像處理類別"""

    def __init__(self):
        """初始化影像處理器"""
        # 優化：可配置的背景減除器參數
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=20000,
            varThreshold=16,
            detectShadows=True
        )

        # 預先定義常用的核心以提高效能
        self.gaussian_kernel = (5, 5)
        self.dilate_kernel = np.ones((3, 3), np.uint8)
        self.close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        # 閾值參數
        self.canny_threshold1 = 50
        self.canny_threshold2 = 110
        self.binary_threshold = 30

        # 建立執行緒池以支援平行處理
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

        # 物件檢測參數
        self.min_object_area = 10
        self.max_object_area = 150

    def process_frame(self, frame):
        """
        處理單幀影像 - 優化版本

        Args:
            frame: 輸入的影像幀

        Returns:
            processed_frame: 處理後的影像幀
        """
        if frame is None or frame.size == 0:
            return None

        # 使用背景減除器
        fg_mask = self.bg_subtractor.apply(frame)

        # 影像模糊化 - 使用預先定義的核心
        blurred = cv2.GaussianBlur(frame, self.gaussian_kernel, 0)

        # 邊緣檢測 - 使用預先定義的閾值
        edges = cv2.Canny(blurred, self.canny_threshold1, self.canny_threshold2)

        # 使用遮罩 - 使用numpy向量化操作
        result = cv2.bitwise_and(edges, edges, mask=fg_mask)

        # 二值化 - 使用預先定義的閾值
        _, thresh = cv2.threshold(result, self.binary_threshold, 255, cv2.THRESH_BINARY)

        # 膨脹操作 - 使用預先定義的核心
        dilated = cv2.dilate(thresh, self.dilate_kernel, iterations=1)

        # 閉合操作 - 使用預先定義的核心
        closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, self.close_kernel)

        return closed

    def detect_objects(self, processed, min_area=None, max_area=None):
        """
        檢測物件 - 優化版本

        Args:
            processed: 處理過的影像
            min_area: 最小物件面積 (可選，優先使用類別屬性)
            max_area: 最大物件面積 (可選，優先使用類別屬性)

        Returns:
            valid_objects: 符合條件的物件列表
        """
        if processed is None or processed.size == 0:
            return []

        # 使用指定的參數或類別預設值
        min_area = min_area if min_area is not None else self.min_object_area
        max_area = max_area if max_area is not None else self.max_object_area

        try:
            # 使用連通區域分析
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                processed,
                connectivity=4
            )

            # 使用列表推導式優化物件過濾
            valid_objects = [
                (
                    stats[i, cv2.CC_STAT_LEFT],
                    stats[i, cv2.CC_STAT_TOP],
                    stats[i, cv2.CC_STAT_WIDTH],
                    stats[i, cv2.CC_STAT_HEIGHT],
                    centroids[i]
                )
                for i in range(1, num_labels)
                if min_area < stats[i, cv2.CC_STAT_AREA] < max_area
            ]

            return valid_objects
        except Exception as e:
            import logging
            logging.error(f"物件檢測時發生錯誤：{str(e)}")
            return []

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
                import logging
                logging.error(f"ROI 處理時發生錯誤：{str(e)}")

        return results

    def _process_single_roi(self, roi, line_y):
        """處理單個 ROI 的輔助函數"""
        processed = self.process_frame(roi)
        objects = self.detect_objects(processed)
        return (line_y, objects)

    def draw_detection_results(self, frame, objects):
        """
        在影像上繪製檢測結果

        Args:
            frame: 原始影像
            objects: 檢測到的物件列表

        Returns:
            frame: 繪製結果後的影像
        """
        if frame is None or not objects:
            return frame

        # 創建結果影像的副本，避免修改原始資料
        result_frame = frame.copy()

        # 繪製檢測框
        for x, y, w, h, _ in objects:
            cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        return result_frame

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
            import logging
            logging.error(f"設置影像處理參數時發生錯誤：{str(e)}")
            return False