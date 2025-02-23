"""
影像處理模型
處理所有與影像處理相關的功能
"""

import cv2
import numpy as np


class ImageProcessor:
    """影像處理類別"""

    def __init__(self):
        """初始化影像處理器"""
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=20000,
            varThreshold=16,
            detectShadows=True
        )

    def process_frame(self, frame):
        """
        處理單幀影像

        Args:
            frame: 輸入的影像幀

        Returns:
            processed_frame: 處理後的影像幀
        """
        # 使用背景減除器
        fg_mask = self.bg_subtractor.apply(frame)

        # 影像模糊化
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)

        # 邊緣檢測
        edges = cv2.Canny(blurred, 50, 110)

        # 使用遮罩
        result = cv2.bitwise_and(edges, edges, mask=fg_mask)

        # 二值化
        _, thresh = cv2.threshold(result, 30, 255, cv2.THRESH_BINARY)

        # 膨脹操作
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=1)

        # 閉合操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)

        return closed

    @staticmethod
    def detect_objects(processed, min_area=10, max_area=150):
        """
        檢測物件

        Args:
            processed: 處理過的影像
            min_area: 最小物件面積
            max_area: 最大物件面積

        Returns:
            valid_objects: 符合條件的物件列表
        """
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            processed,
            connectivity=4
        )

        valid_objects = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if min_area < area < max_area:
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                centroid = centroids[i]
                valid_objects.append((x, y, w, h, centroid))
        return valid_objects

    def draw_detection_results(self, frame, objects):
        """
        在影像上繪製檢測結果

        Args:
            frame: 原始影像
            objects: 檢測到的物件列表

        Returns:
            frame: 繪製結果後的影像
        """
        for x, y, w, h, _ in objects:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return frame