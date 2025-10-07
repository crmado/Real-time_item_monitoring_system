"""
小零件檢測控制器 - 基於 basler_mvc 的背景減除算法
整合 SORT 追蹤算法（卡爾曼濾波器 + 匈牙利算法）
"""

import cv2
import numpy as np
import logging
import os
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# 嘗試導入 SORT 追蹤器（如果可用）
try:
    from .kalman_tracker import (
        KalmanBoxTracker,
        associate_detections_to_trackers
    )
    SORT_AVAILABLE = True
    logger.info("✅ SORT 追蹤算法已啟用（卡爾曼濾波器 + 匈牙利算法）")
except ImportError as e:
    SORT_AVAILABLE = False
    logger.warning(f"⚠️ SORT 追蹤算法不可用（缺少依賴）: {e}")
    logger.warning("   請安裝: pip install filterpy scipy")


class DetectionController:
    """小零件檢測控制器 - 背景減除 + 物件追蹤"""

    def __init__(self, use_sort=False):  # 禁用 SORT，使用傳統追蹤
        self.enabled = False
        self.detected_objects: List[Dict] = []

        # 🚀 高速檢測模式控制
        self.ultra_high_speed_mode = False
        self.target_fps = 280

        # 🎯 SORT 追蹤算法控制
        self.use_sort = use_sort and SORT_AVAILABLE
        self.kalman_trackers: List[KalmanBoxTracker] = [] if self.use_sort else None
        self.max_age = 3  # 追蹤器最大未匹配幀數
        self.min_hits = 3  # 開始計數前的最小命中次數
        self.iou_threshold = 0.3  # IOU 匹配閾值

        # 🎯 極小零件檢測參數 - 基於 basler_mvc
        self.min_area = 1           # 🔧 降低最小面積捕捉更小零件 (2→1)
        self.max_area = 5000        # 🔧 提高最大面積避免過濾 (3000→5000)

        # 物件形狀過濾參數 - 為小零件放寬條件
        self.min_aspect_ratio = 0.001  # 極度寬鬆的長寬比
        self.max_aspect_ratio = 100.0
        self.min_extent = 0.001        # 極度降低填充比例要求
        self.max_solidity = 5.0        # 極度放寬結實性限制

        # 🎯 超穩定背景減除 - 專為小零件長期檢測優化
        self.bg_history = 500           # 🔧 降低歷史幀數加快背景建立 (1000→500)
        self.bg_var_threshold = 2       # 🔧 進一步降低閾值提高敏感度 (3→2)
        self.detect_shadows = False
        self.bg_learning_rate = 0.0005  # 🔧 降低學習率避免小零件被納入背景 (0.001→0.0005)

        # 🚀 高速模式參數
        self.high_speed_bg_history = 100
        self.high_speed_bg_var_threshold = 8
        self.high_speed_min_area = 1
        self.high_speed_max_area = 2000
        self.high_speed_binary_threshold = 3

        # 🎯 極高敏感度邊緣檢測
        self.gaussian_blur_kernel = (1, 1)  # 最小模糊保留最多細節
        self.canny_low_threshold = 2        # 🔧 進一步降低閾值 (3→2)
        self.canny_high_threshold = 8       # 🔧 進一步降低閾值 (10→8)
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
        self.roi_height = 150  # 🔧 擴大 ROI 區域高度 (120→150)
        self.roi_position_ratio = 0.10  # 🔧 稍微上移 ROI 位置 (0.12→0.10)
        self.current_roi_y = 0
        self.current_roi_height = 150

        # 🎯 物件追蹤和計數參數
        self.enable_crossing_count = True
        self.crossing_tolerance_x = 35
        self.crossing_tolerance_y = 50

        # 追蹤穩定性參數
        self.track_lifetime = 20
        self.min_track_frames = 3  # 🍯 與 MVC 一致：確保穩定追蹤
        self.crossing_threshold = 0.12
        self.confidence_threshold = 0.10

        # 防重複機制
        self.counted_objects_history = []
        self.history_length = 25
        self.duplicate_distance_threshold = 30  # 🔧 與 MVC 一致
        self.temporal_tolerance = 12  # 🔧 與 MVC 一致

        # 空間網格追蹤
        self.position_based_tracking = True  # 🎯 與 MVC 一致：啟用位置追蹤
        self.spatial_grid = {}
        self.grid_cell_size = 30  # 🎯 與 MVC 一致

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

        # 輸出追蹤算法狀態
        logger.info("✅ 檢測控制器初始化完成 (基於 basler_mvc 算法)")
        logger.info(f"ℹ️ 使用{'SORT' if self.use_sort else '傳統'}追蹤算法")

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

            # 🐛 調試：每 500 幀輸出完整診斷報告
            if self.total_processed_frames % 500 == 0:
                logger.info(f"{'='*60}")
                logger.info(f"🔍 診斷報告 - 第 {self.total_processed_frames} 幀")
                logger.info(f"{'='*60}")
                logger.info(f"📊 [最終結果] 幀{self.total_processed_frames}: "
                          f"檢測到 {len(detected_objects)} 個物件, "
                          f"追蹤算法: {'SORT' if self.use_sort else '傳統'}, "
                          f"當前計數: {self.crossing_counter}")
                logger.info(f"{'='*60}")

            # 執行物件追蹤和穿越計數
            if self.enable_crossing_count and len(detected_objects) > 0:
                if self.use_sort:
                    # 使用 SORT 算法（卡爾曼濾波器 + 匈牙利算法）
                    self._update_object_tracking_sort(detected_objects)
                else:
                    # 使用傳統追蹤算法
                    tracking_objects = []
                    for obj in detected_objects:
                        x, y, w, h = obj['x'], obj['y'], obj['w'], obj['h']
                        cx, cy = obj['cx'], obj['cy']
                        area = obj['area']
                        radius = max(w, h) // 2
                        tracking_objects.append((x, y, w, h, (cx, cy), area, radius))
                    self._update_object_tracking(tracking_objects)

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

        # 🐛 調試：檢查前景遮罩
        if self.total_processed_frames % 500 == 0:
            fg_pixels = cv2.countNonZero(fg_mask)
            roi_total = process_region.shape[0] * process_region.shape[1]
            fg_ratio = (fg_pixels / roi_total * 100) if roi_total > 0 else 0
            logger.info(f"  ➊ [背景減除] 前景像素={fg_pixels} ({fg_ratio:.2f}%), 學習率={self.current_learning_rate}")

        # 2. 高斯模糊減少噪聲
        blurred = cv2.GaussianBlur(process_region, self.gaussian_blur_kernel, 0)

        # 3. Canny邊緣檢測
        edges = cv2.Canny(blurred, self.canny_low_threshold, self.canny_high_threshold)

        # 4. 多角度檢測策略
        # 方法1: 極度溫和的前景遮罩處理 - 針對小零件優化
        # 🔧 關鍵修正：使用最小核心避免消除小零件
        tiny_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))  # 5→2: 極小核心
        fg_cleaned = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, tiny_kernel, iterations=1)  # 只做一次閉合填充小孔
        # ❌ 移除所有開運算和中值濾波 - 它們會消除小零件

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

        # 🐛 調試：檢查最終處理結果
        if self.total_processed_frames % 500 == 0:
            # 檢查各階段像素數
            fg_cleaned_pixels = cv2.countNonZero(fg_cleaned)
            combined_pixels = cv2.countNonZero(combined)
            processed_pixels = cv2.countNonZero(processed)

            logger.info(f"  ➋ [形態處理] 清理後={fg_cleaned_pixels}px, 聯合檢測={combined_pixels}px, 最終={processed_pixels}px")

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

            # 🔍 調試：記錄連通組件信息
            if self.total_processed_frames % 500 == 0:
                min_area = self.high_speed_min_area if self.ultra_high_speed_mode else self.min_area
                max_area = self.high_speed_max_area if self.ultra_high_speed_mode else self.max_area

                # 統計組件面積分佈
                if num_labels > 1:
                    all_areas = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
                    areas_in_range = [a for a in all_areas if min_area <= a <= max_area]

                    logger.info(f"📊 [連通組件] 幀{self.total_processed_frames}: "
                              f"總組件={num_labels-1}, "
                              f"面積範圍內={len(areas_in_range)}, "
                              f"範圍=[{min_area}, {max_area}]")

                    if all_areas:
                        area_stats = {
                            '最小': min(all_areas),
                            '最大': max(all_areas),
                            '平均': int(sum(all_areas) / len(all_areas))
                        }
                        logger.info(f"   面積統計: {area_stats}")
                        # 顯示前10個組件的面積
                        sample_areas = sorted(all_areas)[:10]
                        logger.info(f"   前10個組件面積: {sample_areas}")
                else:
                    logger.warning(f"⚠️ [連通組件] 幀{self.total_processed_frames}: 沒有檢測到任何組件！")

            detected_objects = []
            min_area = self.high_speed_min_area if self.ultra_high_speed_mode else self.min_area
            max_area = self.high_speed_max_area if self.ultra_high_speed_mode else self.max_area

            # 🔍 統計過濾信息
            filter_stats = {
                'total': num_labels - 1,
                'area_filtered': 0,
                'shape_filtered': 0,
                'passed': 0
            }

            for i in range(1, num_labels):  # 跳過背景 (label 0)
                area = stats[i, cv2.CC_STAT_AREA]

                # 面積過濾
                if area < min_area or area > max_area:
                    filter_stats['area_filtered'] += 1
                    continue

                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP] + self.current_roi_y  # 加上 ROI 偏移
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]

                cx = int(centroids[i][0])
                cy = int(centroids[i][1]) + self.current_roi_y  # 加上 ROI 偏移

                # 形狀驗證
                if not self._validate_shape(w, h, area):
                    filter_stats['shape_filtered'] += 1
                    continue

                filter_stats['passed'] += 1
                detected_objects.append({
                    'x': x,
                    'y': y,
                    'w': w,
                    'h': h,
                    'cx': cx,
                    'cy': cy,
                    'area': area
                })

            # 🔍 輸出過濾統計
            if self.total_processed_frames % 500 == 0:
                logger.info(f"📊 [物件過濾] 幀{self.total_processed_frames}: "
                          f"總組件={filter_stats['total']}, "
                          f"面積過濾={filter_stats['area_filtered']}, "
                          f"形狀過濾={filter_stats['shape_filtered']}, "
                          f"✅通過={filter_stats['passed']}")

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
        self.spatial_grid.clear()
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

    def _update_object_tracking(self, current_objects: List[Tuple]):
        """改進的物件追蹤和穿越計數邏輯"""
        try:
            self.current_frame_count += 1

            # ROI區域邊界
            roi_top = self.current_roi_y
            roi_bottom = self.current_roi_y + self.roi_height
            roi_center = self.current_roi_y + self.roi_height // 2

            # 🔧 改進的追蹤匹配邏輯：實現一對一匹配，避免多物件沖突
            new_tracks = {}
            used_track_ids = set()  # 記錄已經匹配的追蹤ID

            # 🎯 清理空間網格並重建 (每幀重新計算網格佔用)
            self.spatial_grid.clear()

            # 🚫 移除虛擬物件生成邏輯 - 只使用真實檢測物件
            all_objects = current_objects

            # 🎯 第一階段：為每個檢測物件找到最佳匹配
            object_track_matches = []  # [(object_index, track_id, distance, is_virtual), ...]

            for obj_idx, obj in enumerate(all_objects):
                x, y, w, h, centroid, area, radius = obj
                cx, cy = centroid

                best_match_id = None
                best_match_distance = float('inf')

                # 與現有追蹤進行匹配 (找最佳匹配)
                for track_id, track in self.object_tracks.items():
                    if track_id in used_track_ids:  # 跳過已經被匹配的追蹤
                        continue

                    # 計算距離
                    distance = np.sqrt((cx - track['x'])**2 + (cy - track['y'])**2)

                    # 🔧 精密微調: 增強匹配穩定性，使用更寬鬆的容差
                    tolerance_x = self.crossing_tolerance_x
                    tolerance_y = self.crossing_tolerance_y

                    # 🍯 加入距離穩定性加權: 近距離匹配優先權更高
                    distance_weight = 1.0 + (distance / 100.0)  # 距離越近優先權越高

                    # 檢查是否在容差範圍內
                    if (abs(cx - track['x']) < tolerance_x and
                        abs(cy - track['y']) < tolerance_y and
                        distance / distance_weight < best_match_distance):

                        best_match_distance = distance / distance_weight  # 使用加權後的距離
                        best_match_id = track_id

                # 記錄匹配結果
                if best_match_id is not None:
                    object_track_matches.append((obj_idx, best_match_id, best_match_distance))

            # 🎯 第二階段：按距離排序，確保最佳匹配優先
            object_track_matches.sort(key=lambda x: x[2])  # 按距離排序

            # 🎯 第三階段：執行一對一匹配（含網格驗證）
            # grid_conflicted_objects = set()  # 🔧 記錄因網格衝突被跳過的物件

            for match_data in object_track_matches:
                obj_idx, track_id, distance = match_data

                if track_id not in used_track_ids:
                    # 執行匹配
                    obj = all_objects[obj_idx]
                    x, y, w, h, centroid, area, radius = obj
                    cx, cy = centroid

                    # 🎯 網格驗證：檢查空間衝突
                    grid_pos = self._get_grid_position(cx, cy)
                    grid_conflict = grid_pos in self.spatial_grid

                    if not grid_conflict or not self.position_based_tracking:
                        # 無網格衝突或未啟用位置追蹤，執行匹配
                        old_track = self.object_tracks[track_id]
                        new_tracks[track_id] = {
                            'x': cx,
                            'y': cy,
                            'first_frame': old_track.get('first_frame', self.current_frame_count),
                            'last_frame': self.current_frame_count,
                            'positions': old_track.get('positions', []) + [(cx, cy)],
                            'counted': old_track.get('counted', False),
                            'in_roi_frames': old_track.get('in_roi_frames', 0) + 1,
                            'max_y': max(old_track.get('max_y', cy), cy),
                            'min_y': min(old_track.get('min_y', cy), cy),
                            'grid_position': grid_pos,  # 記錄網格位置
                        }
                        used_track_ids.add(track_id)

                        # 佔用網格
                        if self.position_based_tracking:
                            self.spatial_grid[grid_pos] = track_id

                        logger.debug(f"🔗 物件{obj_idx}匹配到追蹤{track_id}, 距離={distance:.1f}px, 網格={grid_pos}")
                    else:
                        # 有網格衝突，記錄並跳過，防止重複創建
                        conflicted_track = self.spatial_grid[grid_pos]
                        # grid_conflicted_objects.add(obj_idx)  # 🔧 記錄衝突物件
                        logger.warning(f"⚠️ 網格衝突: 物件{obj_idx}與追蹤{conflicted_track}在網格{grid_pos}衝突，跳過匹配")

            # 🎯 第四階段：為未匹配的物件（包括虛擬物件）創建新追蹤或嘗試恢復
            matched_objects = {match[0] for match in object_track_matches if match[1] in used_track_ids}

            for obj_idx, obj in enumerate(all_objects):
                if obj_idx not in matched_objects:
                    x, y, w, h, centroid, area, radius = obj
                    cx, cy = centroid

                    # 🔄 追蹤恢復機制：嘗試從lost_tracks中恢復匹配的追蹤
                    recovered_track_id = None
                    best_recovery_distance = float('inf')
                    best_recovery_track_id = None

                    # 遍歷失去的追蹤尋找可能的恢復匹配
                    for lost_track_id, lost_track in self.lost_tracks.items():
                        # 計算空間距離
                        spatial_distance = np.sqrt((cx - lost_track['x'])**2 + (cy - lost_track['y'])**2)
                        # 計算時間間隔
                        temporal_distance = self.current_frame_count - lost_track['last_frame']

                        # 🔧 精密微調恢復條件：適度擴大恢復範圍以減少ID變更
                        recovery_tolerance_x = self.crossing_tolerance_x * 1.4  # 35*1.4=49px
                        recovery_tolerance_y = self.crossing_tolerance_y * 1.3  # 50*1.3=65px

                        if (abs(cx - lost_track['x']) < recovery_tolerance_x and
                            abs(cy - lost_track['y']) < recovery_tolerance_y and
                            temporal_distance <= self.temporal_tolerance and
                            spatial_distance < best_recovery_distance):

                            best_recovery_distance = spatial_distance
                            best_recovery_track_id = lost_track_id

                    # 如果找到合適的恢復匹配
                    if best_recovery_track_id is not None:
                        recovered_track_id = best_recovery_track_id
                        recovered_track = self.lost_tracks[recovered_track_id]

                        # 🎯 檢查恢復位置的網格衝突
                        recovery_grid_pos = self._get_grid_position(cx, cy)
                        if recovery_grid_pos not in self.spatial_grid or not self.position_based_tracking:
                            # 🍯 關鍵修正：恢復追蹤時保持完整狀態，特別是計數狀態
                            was_counted = recovered_track.get('counted', False)
                            new_tracks[recovered_track_id] = {
                                'x': cx,
                                'y': cy,
                                'first_frame': recovered_track.get('first_frame', self.current_frame_count),
                                'last_frame': self.current_frame_count,
                                'positions': recovered_track.get('positions', []) + [(cx, cy)],
                                'counted': was_counted,  # 🛡️ 嚴格保持原始計數狀態
                                'in_roi_frames': recovered_track.get('in_roi_frames', 0) + 1,
                                'max_y': max(recovered_track.get('max_y', cy), cy),
                                'min_y': min(recovered_track.get('min_y', cy), cy),
                                'grid_position': recovery_grid_pos,
                                'recovered': True,  # 🆕 標記為恢復的追蹤
                                'recovery_frame': self.current_frame_count
                            }

                            # 🔍 調試：記錄恢復狀態
                            if was_counted:
                                logger.debug(f"🔄 恢復已計數追蹤{recovered_track_id}，跳過重複計數")

                            # 佔用網格
                            if self.position_based_tracking:
                                self.spatial_grid[recovery_grid_pos] = recovered_track_id
                        else:
                            # 恢復位置有網格衝突，放棄恢復
                            recovered_track_id = None
                            logger.warning(f"⚠️ 追蹤恢復失敗: 網格{recovery_grid_pos}已被佔用")

                        # 從lost_tracks中移除已恢復的追蹤
                        del self.lost_tracks[recovered_track_id]

                        logger.info(f"🔄 成功恢復追蹤{recovered_track_id}(counted={recovered_track.get('counted', False)}): 距離={best_recovery_distance:.1f}px, 時間間隔={self.current_frame_count - recovered_track['last_frame']}幀")

                    if not recovered_track_id:

                        # 🎯 檢查新追蹤位置的網格衝突（僅對真實物件）
                        new_grid_pos = self._get_grid_position(cx, cy)
                        if new_grid_pos not in self.spatial_grid or not self.position_based_tracking:
                            # 創建新的追蹤
                            new_track_id = max(list(self.object_tracks.keys()) + list(new_tracks.keys()) + [0]) + 1
                            new_tracks[new_track_id] = {
                                'x': cx,
                                'y': cy,
                                'first_frame': self.current_frame_count,
                                'last_frame': self.current_frame_count,
                                'positions': [(cx, cy)],
                                'counted': False,
                                'in_roi_frames': 1,
                                'max_y': cy,
                                'min_y': cy,
                                'grid_position': new_grid_pos
                            }

                            # 佔用網格
                            if self.position_based_tracking:
                                self.spatial_grid[new_grid_pos] = new_track_id

                            logger.debug(f"🆕 物件{obj_idx}創建新追蹤{new_track_id}, 網格={new_grid_pos}")
                        else:
                            # 新位置有網格衝突，跳過創建
                            conflicted_track = self.spatial_grid[new_grid_pos]
                            logger.warning(f"⚠️ 新追蹤創建失敗: 物件{obj_idx}在網格{new_grid_pos}與追蹤{conflicted_track}衝突")
                    else:
                        logger.debug(f"🔄 物件{obj_idx}恢復追蹤{recovered_track_id}")

            # 🔍 調試：記錄軌跡狀態和網格衝突統計 (每20幀記錄一次)
            if self.current_frame_count % 20 == 0:
                logger.debug(f"🎯 軌跡狀態: 總軌跡數={len(new_tracks)}, 當前穿越計數={self.crossing_counter}")

            # 🎯 增強的穿越計數邏輯 - 加入恢復追蹤安全檢查
            for track_id, track in new_tracks.items():
                # 🛡️ 多重安全檢查：防止恢復的已計數追蹤被重複計數
                is_recovered = track.get('recovered', False)
                already_counted = track.get('counted', False)

                if not already_counted and track['in_roi_frames'] >= self.min_track_frames:
                    # 簡化檢查：只要物件在ROI中出現就計數
                    y_travel = track['max_y'] - track['min_y']

                    # 檢查是否為重複計數（簡化版）
                    is_duplicate = self._check_duplicate_detection_simple(track)

                    # 🎯 與 MVC 一致的計數條件
                    valid_crossing = (
                        y_travel >= 8 and           # 🍯 與 MVC 一致：確保真實穿越
                        track['in_roi_frames'] >= self.min_track_frames and  # 確保穩定檢測
                        not is_duplicate            # 非重複檢測
                    )

                    # 🔍 增強調試：記錄計數邏輯和恢復狀態 (每10幀記錄一次)
                    if self.current_frame_count % 10 == 0 and track_id in list(new_tracks.keys())[:2]:
                        logger.debug(f"物件{track_id}: Y移動={y_travel}px, 重複={is_duplicate}, 在ROI幀數={track['in_roi_frames']}, 恢復={is_recovered}, 有效穿越={valid_crossing}")

                    if valid_crossing:
                        # 🛡️ 最終安全檢查：再次確認未計數
                        if not track.get('counted', False):
                            # 記錄到歷史中防止重複
                            self._add_to_history(track)

                            self.crossing_counter += 1
                            track['counted'] = True

                            # 🔍 重要：記錄每次成功計數 (性能影響小但很重要)
                            recovery_status = "恢復" if is_recovered else "新建"
                            logger.info(f"✅ 成功計數 #{self.crossing_counter} - 物件{track_id}({recovery_status}) (Y移動: {y_travel}px)")
                        else:
                            logger.warning(f"⚠️ 阻止重複計數: 物件{track_id}已被計數")

            # 🔧 改進的追蹤生命週期管理：移動失去的追蹤到lost_tracks
            current_time = self.current_frame_count

            # 🔧 改進的追蹤生命週期管理：確保完整狀態保存
            for track_id, track in self.object_tracks.items():
                if track_id not in new_tracks:
                    # 🛡️ 確保完整狀態保存，特別是計數狀態
                    self.lost_tracks[track_id] = {
                        **track,  # 保留所有原始狀態
                        'lost_frame': current_time,  # 記錄失去的時間
                        'lost_reason': 'no_detection'  # 記錄失去原因
                    }
                    logger.debug(f"🔄 追蹤{track_id}失去匹配(counted={track.get('counted', False)})，移動到lost_tracks")

            # 清理過期的lost_tracks
            for track_id in list(self.lost_tracks.keys()):
                track = self.lost_tracks[track_id]
                if current_time - track['last_frame'] > self.temporal_tolerance:
                    del self.lost_tracks[track_id]
                    logger.debug(f"🗑️ 清理過期lost_track {track_id}")

            # 更新追蹤狀態
            self.object_tracks = new_tracks

        except Exception as e:
            logger.error(f"物件追蹤更新錯誤: {str(e)}")

    def _check_duplicate_detection_simple(self, track: Dict) -> bool:
        """🔧 增強版重複檢測 - 加入時間與空間雙重考量 🔍 特別針對ID變更的重複計數問題"""
        try:
            current_pos = (track['x'], track['y'])
            current_frame = self.current_frame_count

            # 🛡️ 特別檢查: 如果是恢復的追蹤，適度放寬檢查範圍
            is_recovered = track.get('recovered', False)
            detection_threshold = self.duplicate_distance_threshold * (1.2 if is_recovered else 1.0)

            # 🆕 檢查歷史記錄中的時空重複
            for hist_entry in self.counted_objects_history:
                if isinstance(hist_entry, tuple) and len(hist_entry) == 2:
                    # 新格式：(position, frame_number)
                    hist_pos, hist_frame = hist_entry

                    # 🎯 時空距離檢測：同時考慮空間距離和時間間隔
                    spatial_distance = abs(current_pos[0] - hist_pos[0]) + abs(current_pos[1] - hist_pos[1])
                    temporal_distance = current_frame - hist_frame

                    # 🛡️ 精密微調的重複檢測：使用動態闾值
                    if (spatial_distance < detection_threshold and
                        temporal_distance <= self.temporal_tolerance):
                        status = "恢復" if is_recovered else "新建"
                        logger.debug(f"🚫 檢測到重複({status}): 空間距離={spatial_distance:.1f}<{detection_threshold:.1f}, 時間間隔={temporal_distance}幀")
                        return True

                elif isinstance(hist_entry, tuple) and len(hist_entry) == 2 and isinstance(hist_entry[0], (int, float)):
                    # 舊格式：(x, y) - 向後相容
                    hist_pos = hist_entry
                    spatial_distance = abs(current_pos[0] - hist_pos[0]) + abs(current_pos[1] - hist_pos[1])

                    # 🔧 使用動態闾值處理舊格式記錄
                    if spatial_distance < detection_threshold:
                        status = "恢復" if is_recovered else "新建"
                        logger.debug(f"🚫 檢測到舊格式重複({status}): 空間距離={spatial_distance:.1f}<{detection_threshold:.1f}")
                        return True

            return False

        except Exception as e:
            logger.debug(f"重複檢測錯誤: {str(e)}")
            return False

    def _add_to_history(self, track: Dict):
        """🔧 添加已計數物件到歷史記錄 - 包含時間信息"""
        try:
            position = (track['x'], track['y'])
            frame_number = self.current_frame_count

            # 🆕 新格式：同時記錄位置和時間
            history_entry = (position, frame_number)
            self.counted_objects_history.append(history_entry)

            # 保持歷史記錄在限制範圍內
            if len(self.counted_objects_history) > self.history_length:
                self.counted_objects_history.pop(0)

            logger.debug(f"📝 添加到歷史: 位置={position}, 幀號={frame_number}")

        except Exception as e:
            logger.error(f"添加歷史記錄錯誤: {str(e)}")

    def _get_grid_position(self, x: int, y: int) -> Tuple[int, int]:
        """將像素座標轉換為網格座標"""
        grid_x = x // self.grid_cell_size
        grid_y = y // self.grid_cell_size
        return (grid_x, grid_y)

    def _update_object_tracking_sort(self, detected_objects: List[Dict]):
        """
        使用 SORT 算法更新物件追蹤（卡爾曼濾波器 + 匈牙利算法）

        Args:
            detected_objects: 檢測到的物件列表 [{'x': cx, 'y': cy, 'w': w, 'h': h, ...}, ...]
        """
        if not self.use_sort:
            logger.warning("SORT 追蹤未啟用")
            return

        try:
            self.current_frame_count += 1

            # 🐛 調試：每 50 幀輸出一次 SORT 狀態
            if self.current_frame_count % 50 == 0:
                logger.info(f"🎯 SORT 追蹤 (第 {self.current_frame_count} 幀): "
                          f"檢測={len(detected_objects)}, "
                          f"追蹤器={len(self.kalman_trackers)}, "
                          f"計數={self.crossing_counter}")

            # 1. 準備檢測結果：轉換為 numpy 陣列 [x, y, w, h]
            detections = np.array([[obj['x'], obj['y'], obj['w'], obj['h']]
                                   for obj in detected_objects])

            # 2. 對所有追蹤器進行預測
            trackers_pred = np.zeros((len(self.kalman_trackers), 4))
            to_del = []

            for t, trk in enumerate(self.kalman_trackers):
                pred = trk.predict()
                trackers_pred[t] = pred

                # 標記無效的追蹤器
                if np.any(np.isnan(pred)):
                    to_del.append(t)

            # 移除無效追蹤器
            for t in reversed(to_del):
                self.kalman_trackers.pop(t)
            trackers_pred = np.delete(trackers_pred, to_del, axis=0)

            # 3. 使用匈牙利算法進行最優匹配
            if len(trackers_pred) > 0:
                matched, unmatched_dets, unmatched_trks = associate_detections_to_trackers(
                    detections, trackers_pred, self.iou_threshold
                )
            else:
                matched = np.empty((0, 2), dtype=int)
                unmatched_dets = np.arange(len(detections))
                unmatched_trks = np.empty((0,), dtype=int)

            # 4. 更新已匹配的追蹤器
            for m in matched:
                det_idx, trk_idx = m[0], m[1]
                self.kalman_trackers[trk_idx].update(detections[det_idx])

            # 5. 為未匹配的檢測創建新追蹤器
            for i in unmatched_dets:
                trk = KalmanBoxTracker(detections[i])
                self.kalman_trackers.append(trk)

            # 6. 更新追蹤器列表並執行計數邏輯
            i = len(self.kalman_trackers)
            for trk in reversed(self.kalman_trackers):
                i -= 1

                # 移除長時間未更新的追蹤器
                if trk.time_since_update > self.max_age:
                    self.kalman_trackers.pop(i)
                    continue

                # 計數邏輯：只對穩定追蹤且未計數的物件計數
                if (trk.time_since_update == 0 and
                    trk.hit_streak >= self.min_hits and
                    not trk.counted):

                    # 檢查穿越條件
                    y_travel = trk.get_y_travel()

                    # 檢查重複（基於位置）
                    current_pos = trk.get_position()
                    is_duplicate = self._check_duplicate_simple(current_pos)

                    # 驗證穿越
                    valid_crossing = (
                        y_travel >= 8 and  # Y軸移動距離
                        trk.hit_streak >= self.min_hits and  # 穩定追蹤
                        not is_duplicate  # 非重複
                    )

                    if valid_crossing:
                        self.crossing_counter += 1
                        trk.counted = True

                        # 記錄到歷史
                        self._add_to_history_simple(current_pos)

                        logger.info(f"✅ SORT計數 #{self.crossing_counter} - 追蹤器{trk.id} "
                                   f"(命中:{trk.hit_streak}, Y移動:{y_travel:.1f}px)")
                    else:
                        # 🐛 調試：記錄未計數的原因（每 100 次檢查輸出一次）
                        if self.current_frame_count % 100 == 0:
                            logger.debug(f"⏭️ 追蹤器{trk.id}未計數: "
                                       f"Y移動={y_travel:.1f}px (需要>=8), "
                                       f"命中={trk.hit_streak} (需要>={self.min_hits}), "
                                       f"重複={is_duplicate}")

            # 7. 調試：記錄追蹤狀態 (每20幀)
            if self.current_frame_count % 20 == 0:
                active_trackers = len(self.kalman_trackers)
                counted_trackers = sum(1 for trk in self.kalman_trackers if trk.counted)
                logger.debug(f"🎯 SORT狀態: 追蹤器={active_trackers}, "
                           f"已計數={counted_trackers}, 總計數={self.crossing_counter}")

        except Exception as e:
            logger.error(f"SORT 追蹤更新錯誤: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def _check_duplicate_simple(self, position: Tuple[float, float]) -> bool:
        """簡化的重複檢測（用於 SORT）"""
        try:
            current_x, current_y = position
            current_frame = self.current_frame_count

            for hist_entry in self.counted_objects_history:
                if isinstance(hist_entry, tuple) and len(hist_entry) == 2:
                    hist_pos, hist_frame = hist_entry
                    spatial_dist = abs(current_x - hist_pos[0]) + abs(current_y - hist_pos[1])
                    temporal_dist = current_frame - hist_frame

                    if (spatial_dist < self.duplicate_distance_threshold and
                        temporal_dist <= self.temporal_tolerance):
                        return True

            return False
        except Exception as e:
            logger.debug(f"重複檢測錯誤: {str(e)}")
            return False

    def _add_to_history_simple(self, position: Tuple[float, float]):
        """簡化的歷史記錄（用於 SORT）"""
        try:
            frame_number = self.current_frame_count
            history_entry = (position, frame_number)
            self.counted_objects_history.append(history_entry)

            if len(self.counted_objects_history) > self.history_length:
                self.counted_objects_history.pop(0)

            logger.debug(f"📝 添加到歷史: 位置={position}, 幀號={frame_number}")
        except Exception as e:
            logger.error(f"添加歷史記錄錯誤: {str(e)}")
