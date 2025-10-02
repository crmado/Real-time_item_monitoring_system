"""
檢測控制器 - 集成多種檢測算法
"""

import cv2
import numpy as np
import logging
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class DetectionMethod(str, Enum):
    """檢測方法"""
    CIRCLE = "circle"
    CONTOUR = "contour"
    BACKGROUND = "background"


class DetectionController:
    """檢測控制器"""

    def __init__(self):
        self.enabled = False
        self.method = DetectionMethod.CIRCLE
        self.detected_objects: List[Dict] = []

        # 檢測參數
        self.params = {
            'min_area': 100,
            'max_area': 5000,
            'circle': {
                'dp': 1.2,
                'min_dist': 20,
                'param1': 50,
                'param2': 30,
                'min_radius': 5,
                'max_radius': 100
            },
            'contour': {
                'threshold': 127,
                'kernel_size': 3
            }
        }

        # 背景減除器（用於小零件檢測）
        self.bg_subtractor = None

        logger.info("✅ 檢測控制器初始化完成")

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
        """
        處理幀並執行檢測

        Returns:
            (處理後的圖像, 檢測結果列表)
        """
        if frame is None or not self.enabled:
            return frame, []

        try:
            if self.method == DetectionMethod.CIRCLE:
                result_frame, objects = self._detect_circles(frame)
            elif self.method == DetectionMethod.CONTOUR:
                result_frame, objects = self._detect_contours(frame)
            elif self.method == DetectionMethod.BACKGROUND:
                result_frame, objects = self._detect_background(frame)
            else:
                result_frame, objects = frame, []

            self.detected_objects = objects
            return result_frame, objects

        except Exception as e:
            logger.error(f"❌ 檢測失敗: {str(e)}")
            return frame, []

    def _detect_circles(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
        """霍夫圓檢測"""
        # 轉灰度
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # 模糊處理
        blurred = cv2.medianBlur(gray, 5)

        # 圓檢測
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=self.params['circle']['dp'],
            minDist=self.params['circle']['min_dist'],
            param1=self.params['circle']['param1'],
            param2=self.params['circle']['param2'],
            minRadius=self.params['circle']['min_radius'],
            maxRadius=self.params['circle']['max_radius']
        )

        objects = []
        result_frame = frame.copy() if len(frame.shape) == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")

            for i, (x, y, r) in enumerate(circles):
                area = np.pi * r * r

                if self.params['min_area'] <= area <= self.params['max_area']:
                    # 繪製圓形
                    cv2.circle(result_frame, (x, y), r, (0, 255, 0), 2)
                    cv2.circle(result_frame, (x, y), 2, (0, 0, 255), 3)

                    objects.append({
                        'id': i,
                        'type': 'circle',
                        'x': int(x),
                        'y': int(y),
                        'radius': int(r),
                        'area': float(area)
                    })

        return result_frame, objects

    def _detect_contours(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
        """輪廓檢測"""
        # 轉灰度
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # 二值化
        _, binary = cv2.threshold(
            gray,
            self.params['contour']['threshold'],
            255,
            cv2.THRESH_BINARY
        )

        # 形態學操作
        kernel = np.ones(
            (self.params['contour']['kernel_size'],
             self.params['contour']['kernel_size']),
            np.uint8
        )
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # 查找輪廓
        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        objects = []
        result_frame = frame.copy() if len(frame.shape) == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            if self.params['min_area'] <= area <= self.params['max_area']:
                # 計算邊界框
                x, y, w, h = cv2.boundingRect(contour)

                # 繪製輪廓
                cv2.drawContours(result_frame, [contour], -1, (0, 255, 0), 2)
                cv2.rectangle(result_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

                # 計算中心點
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = x + w // 2, y + h // 2

                objects.append({
                    'id': i,
                    'type': 'contour',
                    'x': cx,
                    'y': cy,
                    'area': float(area),
                    'bbox': [int(x), int(y), int(w), int(h)]
                })

        return result_frame, objects

    def _detect_background(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
        """背景減除檢測（用於小零件）"""
        # 初始化背景減除器
        if self.bg_subtractor is None:
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500,
                varThreshold=16,
                detectShadows=False
            )

        # 應用背景減除
        fg_mask = self.bg_subtractor.apply(frame)

        # 形態學處理
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)

        # 查找輪廓
        contours, _ = cv2.findContours(
            fg_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        objects = []
        result_frame = frame.copy()

        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            if area > 50:  # 最小面積
                x, y, w, h = cv2.boundingRect(contour)

                # 繪製邊界框
                cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                objects.append({
                    'id': i,
                    'type': 'background',
                    'x': int(x + w // 2),
                    'y': int(y + h // 2),
                    'area': float(area),
                    'bbox': [int(x), int(y), int(w), int(h)]
                })

        return result_frame, objects

    def set_method(self, method: DetectionMethod):
        """設置檢測方法"""
        self.method = method
        # 切換方法時重置背景減除器
        if method != DetectionMethod.BACKGROUND:
            self.bg_subtractor = None
        logger.info(f"✅ 檢測方法切換為: {method.value}")

    def set_parameters(self, params: Dict[str, Any]):
        """更新檢測參數"""
        self.params.update(params)
        logger.info("✅ 檢測參數已更新")

    def enable(self):
        """啟用檢測"""
        self.enabled = True
        logger.info("✅ 檢測已啟用")

    def disable(self):
        """禁用檢測"""
        self.enabled = False
        logger.info("✅ 檢測已禁用")

    def get_detection_count(self) -> int:
        """獲取檢測數量"""
        return len(self.detected_objects)
