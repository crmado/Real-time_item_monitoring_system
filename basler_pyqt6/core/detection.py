"""
小零件檢測控制器 - 基於 basler_mvc 的背景減除算法
"""

import cv2
import numpy as np
import logging
import os
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DetectionController:
    """小零件檢測控制器 - 背景減除 + 物件追蹤"""

    def __init__(self):
        self.enabled = False
        self.detected_objects: List[Dict] = []

        # 🚀 高速檢測模式控制
        self.ultra_high_speed_mode = False
        self.target_fps = 280

        # 🎯 極小零件檢測參數 - 基於 basler_mvc
        self.min_area = 2           # 極小零件最小面積
        self.max_area = 3000        # 最大面積

        # 物件形狀過濾參數 - 為小零件放寬條件
        self.min_aspect_ratio = 0.001  # 極度寬鬆的長寬比
        self.max_aspect_ratio = 100.0
        self.min_extent = 0.001        # 極度降低填充比例要求
        self.max_solidity = 5.0        # 極度放寬結實性限制

        # 🎯 超穩定背景減除 - 專為小零件長期檢測優化
        self.bg_history = 1000          # 大幅增加歷史幀數
        self.bg_var_threshold = 3       # 極低閾值確保最高靈敏度
        self.detect_shadows = False
        self.bg_learning_rate = 0.001   # 極低學習率避免小零件被納入背景

        # 🚀 高速模式參數
        self.high_speed_bg_history = 100
        self.high_speed_bg_var_threshold = 8
        self.high_speed_min_area = 1
        self.high_speed_max_area = 2000
        self.high_speed_binary_threshold = 3

        # 🎯 極高敏感度邊緣檢測
        self.gaussian_blur_kernel = (1, 1)  # 最小模糊保留最多細節
        self.canny_low_threshold = 3        # 極低閾值提高敏感度
        self.canny_high_threshold = 10      # 極低閾值提高敏感度
        self.binary_threshold = 1           # 極低閾值提高敏感度

        # 🔍 分離優化的形態學處理
        self.dilate_kernel_size = (1, 1)    # 最小核避免過度膨脹
        self.dilate_iterations = 0           # 禁用膨脹以保留小零件
        self.close_kernel_size = (1, 1)     # 禁用閉合避免零件粘連
        self.enable_watershed_separation = True  # 啟用分水嶺分離算法

        # 🎯 最小化雜訊過濾
        self.opening_kernel_size = (1, 1)   # 最小開運算核
        self.opening_iterations = 0          # 禁用開運算以保留小零件

        # 連通組件參數
        self.connectivity = 4  # 4-連通或8-連通

        # 🎯 ROI 檢測區域參數
        self.roi_enabled = True
        self.roi_height = 120  # ROI區域高度
        self.roi_position_ratio = 0.12  # 位置比例
        self.current_roi_y = 0
        self.current_roi_height = 120

        # 🎯 物件追蹤和計數參數
        self.enable_crossing_count = True
        self.crossing_tolerance_x = 35
        self.crossing_tolerance_y = 50

        # 追蹤穩定性參數
        self.track_lifetime = 20
        self.min_track_frames = 3
        self.crossing_threshold = 0.12
        self.confidence_threshold = 0.10

        # 防重複機制
        self.counted_objects_history = []
        self.history_length = 25
        self.duplicate_distance_threshold = 30
        self.temporal_tolerance = 12

        # 追蹤狀態
        self.object_tracks = {}
        self.lost_tracks = {}
        self.crossing_counter = 0
        self.frame_width = 640
        self.frame_height = 480
        self.current_frame_count = 0
        self.total_processed_frames = 0

        # 背景減除器
        self.bg_subtractor = None
        self._reset_background_subtractor()

        # 📸 調試圖片功能
        self.debug_save_enabled = False
        self.debug_save_dir = "basler_pyqt6/recordings/debug"
        self.debug_frame_counter = 0
        self.max_debug_frames = 100

        logger.info("✅ 檢測控制器初始化完成 (基於 basler_mvc 算法)")

    def _reset_background_subtractor(self):
        """重置背景減除器"""
        if self.ultra_high_speed_mode:
            history = self.high_speed_bg_history
            var_threshold = self.high_speed_bg_var_threshold
        else:
            history = self.bg_history
            var_threshold = self.bg_var_threshold

        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=self.detect_shadows
        )
        self.current_learning_rate = self.bg_learning_rate
        logger.debug(f"背景減除器已重置: history={history}, var_threshold={var_threshold}")

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
        """
        處理幀並執行小零件檢測

        Returns:
            (處理後的圖像, 檢測結果列表)
        """
        if frame is None or not self.enabled:
            return frame, []

        try:
            self.total_processed_frames += 1
            self.frame_height, self.frame_width = frame.shape[:2]

            # 🎯 ROI 區域提取
            if self.roi_enabled:
                roi_y = int(self.frame_height * self.roi_position_ratio)
                process_region = frame[roi_y:roi_y + self.roi_height, :]
                self.current_roi_y = roi_y
                self.current_roi_height = self.roi_height
            else:
                process_region = frame
                self.current_roi_y = 0
                self.current_roi_height = self.frame_height

            # 執行檢測處理
            if self.ultra_high_speed_mode:
                processed = self._ultra_high_speed_processing(process_region)
            else:
                processed = self._standard_processing(process_region)

            # 檢測物件
            detected_objects = self._detect_objects(processed)

            # 繪製結果
            result_frame = self._draw_detection_results(frame.copy(), detected_objects)

            self.detected_objects = detected_objects
            return result_frame, detected_objects

        except Exception as e:
            logger.error(f"❌ 檢測失敗: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return frame, []

    def _standard_processing(self, process_region: np.ndarray) -> np.ndarray:
        """標準模式處理流程 - 完整的多重檢測策略 (基於 basler_mvc)"""
        # 1. 背景減除獲得前景遮罩
        fg_mask = self.bg_subtractor.apply(process_region, learningRate=self.current_learning_rate)

        # 2. 高斯模糊減少噪聲
        blurred = cv2.GaussianBlur(process_region, self.gaussian_blur_kernel, 0)

        # 3. Canny邊緣檢測
        edges = cv2.Canny(blurred, self.canny_low_threshold, self.canny_high_threshold)

        # 4. 多角度檢測策略
        # 方法1: 增強前景遮罩濾波
        fg_median = cv2.medianBlur(fg_mask, 5)
        enhanced_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_step1 = cv2.morphologyEx(fg_median, cv2.MORPH_OPEN, enhanced_kernel, iterations=1)
        close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        fg_step2 = cv2.morphologyEx(fg_step1, cv2.MORPH_CLOSE, close_kernel, iterations=1)
        final_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_cleaned = cv2.morphologyEx(fg_step2, cv2.MORPH_OPEN, final_kernel, iterations=1)

        # 方法2: 多敏感度邊緣檢測
        strong_edges = cv2.Canny(blurred, self.canny_low_threshold, self.canny_high_threshold)
        sensitive_edges = cv2.Canny(blurred, self.canny_low_threshold//2, self.canny_high_threshold//2)

        # 方法3: 自適應閾值檢測
        gray_roi = cv2.cvtColor(process_region, cv2.COLOR_BGR2GRAY) if len(process_region.shape) == 3 else process_region
        adaptive_thresh = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                cv2.THRESH_BINARY, 11, 2)

        # 5. 邊緣增強
        edge_enhanced = cv2.bitwise_and(sensitive_edges, sensitive_edges, mask=fg_cleaned)
        _, edge_thresh = cv2.threshold(edge_enhanced, 1, 255, cv2.THRESH_BINARY)

        adaptive_enhanced = cv2.bitwise_and(adaptive_thresh, adaptive_thresh, mask=fg_cleaned)
        _, adaptive_thresh_clean = cv2.threshold(adaptive_enhanced, 127, 255, cv2.THRESH_BINARY)

        # 6. 三重聯合檢測
        temp_combined = cv2.bitwise_or(fg_cleaned, edge_thresh)
        combined = cv2.bitwise_or(temp_combined, adaptive_thresh_clean)

        # 7. 極度簡化形態學處理 - 最大化保留小零件
        if self.opening_kernel_size != (1, 1):
            opening_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.opening_kernel_size)
            opened_stage1 = cv2.morphologyEx(combined, cv2.MORPH_OPEN, opening_kernel, iterations=self.opening_iterations)
        else:
            opened_stage1 = combined.copy()

        # 最小化膨脹
        if self.dilate_kernel_size != (1, 1) and self.dilate_iterations > 0:
            dilate_kernel = np.ones(self.dilate_kernel_size, np.uint8)
            dilated = cv2.dilate(opened_stage1, dilate_kernel, iterations=self.dilate_iterations)
        else:
            dilated = opened_stage1.copy()

        # 關鍵：最小化閉合運算
        if self.close_kernel_size != (1, 1):
            close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.close_kernel_size)
            processed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, close_kernel, iterations=1)
        else:
            processed = dilated.copy()

        return processed

    def _ultra_high_speed_processing(self, process_region: np.ndarray) -> np.ndarray:
        """超高速處理模式 - 簡化流程"""
        fg_mask = self.bg_subtractor.apply(process_region, learningRate=self.current_learning_rate)
        kernel = np.ones((3, 3), np.uint8)
        processed = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        processed = cv2.dilate(processed, kernel, iterations=1)
        return processed

    def _detect_objects(self, processed: np.ndarray) -> List[Dict]:
        """檢測物件 - 使用連通組件分析"""
        if processed is None:
            return []

        try:
            # 使用連通組件分析
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                processed, connectivity=self.connectivity
            )

            detected_objects = []
            min_area = self.high_speed_min_area if self.ultra_high_speed_mode else self.min_area
            max_area = self.high_speed_max_area if self.ultra_high_speed_mode else self.max_area

            for i in range(1, num_labels):  # 跳過背景 (label 0)
                area = stats[i, cv2.CC_STAT_AREA]

                # 面積過濾
                if area < min_area or area > max_area:
                    continue

                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP] + self.current_roi_y  # 加上 ROI 偏移
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]

                cx = int(centroids[i][0])
                cy = int(centroids[i][1]) + self.current_roi_y  # 加上 ROI 偏移

                # 形狀驗證
                if not self._validate_shape(w, h, area):
                    continue

                detected_objects.append({
                    'x': x,
                    'y': y,
                    'w': w,
                    'h': h,
                    'cx': cx,
                    'cy': cy,
                    'area': area
                })

            return detected_objects

        except Exception as e:
            logger.error(f"檢測物件錯誤: {str(e)}")
            return []

    def _validate_shape(self, width: int, height: int, area: float) -> bool:
        """驗證形狀參數"""
        if width <= 0 or height <= 0:
            return False

        # 長寬比
        aspect_ratio = width / height if height > width else height / width
        if aspect_ratio < self.min_aspect_ratio or aspect_ratio > self.max_aspect_ratio:
            return False

        # 填充度
        extent = area / (width * height)
        if extent < self.min_extent:
            return False

        return True

    def _draw_detection_results(self, frame: np.ndarray, objects: List[Dict]) -> np.ndarray:
        """繪製檢測結果"""
        try:
            # 繪製 ROI 區域
            if self.roi_enabled:
                cv2.rectangle(frame,
                            (0, self.current_roi_y),
                            (self.frame_width, self.current_roi_y + self.current_roi_height),
                            (255, 255, 0), 2)

            # 繪製檢測到的物件
            for obj in objects:
                x, y, w, h = obj['x'], obj['y'], obj['w'], obj['h']
                cx, cy = obj['cx'], obj['cy']
                area = obj['area']

                # 繪製邊界框
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # 繪製中心點
                cv2.circle(frame, (cx, cy), 3, (255, 0, 0), -1)

                # 標註面積
                cv2.putText(frame, f'{int(area)}',
                          (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # 顯示統計信息
            info_text = f'Objects: {len(objects)} | Counted: {self.crossing_counter}'
            cv2.putText(frame, info_text,
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            return frame

        except Exception as e:
            logger.error(f"繪製檢測結果錯誤: {str(e)}")
            return frame

    def enable(self):
        """啟用檢測"""
        self.enabled = True
        self._reset_background_subtractor()
        logger.info("檢測已啟用")

    def disable(self):
        """禁用檢測"""
        self.enabled = False
        logger.info("檢測已禁用")

    def reset(self):
        """重置檢測狀態"""
        self.crossing_counter = 0
        self.object_tracks.clear()
        self.lost_tracks.clear()
        self.counted_objects_history.clear()
        self.current_frame_count = 0
        self.total_processed_frames = 0
        self._reset_background_subtractor()
        logger.info("檢測狀態已重置")

    def get_count(self) -> int:
        """獲取計數"""
        return self.crossing_counter

    def set_parameters(self, **kwargs):
        """設置檢測參數"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"參數更新: {key} = {value}")

        # 如果更新了背景參數，重置背景減除器
        bg_params = ['bg_history', 'bg_var_threshold', 'detect_shadows', 'bg_learning_rate']
        if any(key in kwargs for key in bg_params):
            self._reset_background_subtractor()

    def set_roi_enabled(self, enabled: bool):
        """設置 ROI 啟用狀態"""
        self.roi_enabled = enabled
        logger.info(f"ROI 檢測: {'啟用' if enabled else '禁用'}")

    def set_ultra_high_speed_mode(self, enabled: bool, target_fps: int = 280):
        """設置超高速模式"""
        self.ultra_high_speed_mode = enabled
        self.target_fps = target_fps
        self._reset_background_subtractor()
        logger.info(f"超高速模式: {'啟用' if enabled else '禁用'} (目標 {target_fps} fps)")
