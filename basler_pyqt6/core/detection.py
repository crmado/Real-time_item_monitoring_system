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
        self.method = DetectionMethod.BACKGROUND  # 改用背景減除法（與master分支一致）
        self.detected_objects: List[Dict] = []

        # 檢測參數（基於master分支優化）
        self.params = {
            # 背景減除參數（針對小零件優化 - 可檢測150+個微小零件）
            'background': {
                'min_area': 1,           # 最小面積（檢測極微小零件）
                'max_area': 5000,        # 最大面積
                'var_threshold': 2,      # 超低變化閾值（極高靈敏度）
                'history': 1000,         # 背景歷史幀數
                'learning_rate': 0.0005, # 更低的學習率（背景更穩定）
                'binary_threshold': 1,   # 二值化閾值
                'morph_kernel_size': 2,  # 較小的核（保留更多細節）
            },
            # 圓形檢測參數（備用）
            'circle': {
                'dp': 1.2,
                'min_dist': 25,
                'param1': 100,
                'param2': 40,
                'min_radius': 5,
                'max_radius': 80,
                'min_area': 100,    # 最小面積過濾
                'max_area': 10000   # 最大面積過濾
            },
            # 輪廓檢測參數（備用）
            'contour': {
                'threshold': 127,
                'kernel_size': 3,
                'min_area': 100,
                'max_area': 10000
            }
        }

        # 背景減除器（用於小零件檢測）
        self.bg_subtractor = None

        logger.info("✅ 檢測控制器初始化完成（使用背景減除法）")

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

        # 使用圓形檢測參數
        circle_params = self.params['circle']

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")

            for i, (x, y, r) in enumerate(circles):
                area = np.pi * r * r

                if circle_params['min_area'] <= area <= circle_params['max_area']:
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

        # 使用輪廓檢測參數
        contour_params = self.params['contour']

        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)

            if contour_params['min_area'] <= area <= contour_params['max_area']:
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
        """背景減除檢測（用於小零件）- 使用master分支優化參數"""
        bg_params = self.params['background']

        # 初始化背景減除器（使用master分支的高靈敏度參數）
        if self.bg_subtractor is None:
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=bg_params['history'],           # 1000幀歷史
                varThreshold=bg_params['var_threshold'], # 極低閾值(3)提高靈敏度
                detectShadows=False                      # 不檢測陰影
            )
            logger.info(f"✅ 背景減除器初始化: history={bg_params['history']}, varThreshold={bg_params['var_threshold']}")

        # 應用背景減除（使用較低的學習率保持背景穩定）
        fg_mask = self.bg_subtractor.apply(frame, learningRate=bg_params['learning_rate'])

        # 二值化處理（使用極低閾值檢測微小變化）
        _, fg_mask = cv2.threshold(
            fg_mask,
            bg_params['binary_threshold'],  # 極低閾值(1)
            255,
            cv2.THRESH_BINARY
        )

        # 形態學處理（去除噪點，保留小零件）
        kernel_size = bg_params['morph_kernel_size']
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)   # 去除小噪點
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)  # 填充小孔洞

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

            # 使用master分支的面積範圍（2-3000）
            if bg_params['min_area'] <= area <= bg_params['max_area']:
                x, y, w, h = cv2.boundingRect(contour)

                # 繪製綠色邊界框
                cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # 計算中心點
                cx = x + w // 2
                cy = y + h // 2

                # 繪製中心點
                cv2.circle(result_frame, (cx, cy), 2, (0, 0, 255), -1)

                objects.append({
                    'id': i,
                    'type': 'background',
                    'x': int(cx),
                    'y': int(cy),
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
