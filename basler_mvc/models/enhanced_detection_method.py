#!/usr/bin/env python3
"""
背景減除檢測方法 - 基於前後景分析的物件檢測和計數
參考 partsCounts_v1.py 的實現方式
"""

import cv2
import numpy as np
import logging
from typing import List, Tuple, Optional, Dict, Any
from .detection_base import DetectionMethod


class BackgroundSubtractionDetection(DetectionMethod):
    """
    背景減除檢測方法 - 基於前後景分析
    參考 partsCounts_v1.py 的高效實現
    """
    
    def __init__(self):
        """初始化背景減除檢測"""
        # 🎯 小零件檢測優化 - 降低面積限制以捕獲更小零件
        self.min_area = 5    # 🔍 降低以檢測更小零件 (原12→5)
        self.max_area = 1000 # 適中上限
        
        # 物件形狀過濾參數 - 使用調試工具中成功的寬鬆參數
        self.min_aspect_ratio = 0.1  # 非常寬鬆的長寬比範圍
        self.max_aspect_ratio = 10.0 # 允許各種形狀的物件
        self.min_extent = 0.01       # 極低的填充比例要求
        self.max_solidity = 1.1      # 放寬結實性限制，允許不規則形狀
        
        # 🎯 平衡靈敏度和性能的背景減除參數 - 減少雜訊
        self.bg_history = 1000   # 增加歷史幀數，提高穩定性
        self.bg_var_threshold = 12  # 適度提高，減少過度敏感
        self.detect_shadows = False  # 關閉陰影檢測
        
        # 🎯 平衡性能的影像處理參數 - 減少雜訊保持效果
        self.gaussian_blur_kernel = (3, 3)  # 減少模糊，保留細節
        self.canny_low_threshold = 20        # 適度提高，減少邊緣雜訊
        self.canny_high_threshold = 80       # 適中設定
        self.binary_threshold = 15           # 適度提高，過濾弱訊號
        
        # 🎯 平衡性能的形態學處理參數 - 減少計算負荷
        self.dilate_kernel_size = (3, 3)    # 適中核大小
        self.dilate_iterations = 2           # 減少迭代，提高性能
        self.close_kernel_size = (5, 5)     # 適中核大小
        
        # 連通組件參數
        self.connectivity = 4  # 4-連通或8-連通
        
        # 🎯 ROI 檢測區域參數 (根據影像分析結果優化)
        self.roi_enabled = True
        self.roi_height = 80  # ROI 區域高度 (保持80以捕獲完整零件)
        self.roi_position_ratio = 0.15  # ROI 位置比例 (調整到0.15，更靠近頂部)
        self.current_roi_y = 0  # 當前ROI的Y座標
        
        # 🎯 物件追蹤和計數參數
        self.enable_crossing_count = True
        self.crossing_tolerance_x = 30  # x方向追蹤容差 (減小以提高精確度)
        self.crossing_tolerance_y = 60  # y方向追蹤容差 (增大以適應ROI高度)
        
        # 🎯 簡化高效追蹤參數 - 提升檢測速度
        self.track_lifetime = 8   # 減少追蹤生命週期，提高效率
        self.min_track_frames = 1  # 單幀即可計數
        self.crossing_threshold = 0.05  # 極簡化穿越邏輯
        self.confidence_threshold = 0.05  # 極簡化置信度檢查
        
        # 🛡️ 簡化防重複機制 - 提升性能
        self.counted_objects_history = []  # 已計數物件的歷史記錄
        self.history_length = 10  # 減少歷史長度，提高效率
        self.duplicate_distance_threshold = 25  # 簡化重複檢測距離
        
        # 追蹤狀態
        self.object_tracks = {}
        self.crossing_counter = 0
        self.frame_width = 640  # 預設寬度，會在第一幀時更新
        self.frame_height = 480  # 預設高度，會在第一幀時更新
        self.current_frame_count = 0  # 當前幀計數
        
        # 初始化背景減除器
        self.bg_subtractor = None
        self._reset_background_subtractor()
        
        # 🎯 專注於核心檢測功能，移除多餘統計
        
        # 📸 算法分析照片保存功能 - 分析ROI區域檢測問題
        self.debug_save_enabled = True   # 🎯 重新啟用：分析小零件檢測準確性
        self.debug_save_dir = "/Users/crmado/github/Real-time_item_monitoring_system/basler_mvc/recordings/test_analysis"
        self.debug_frame_counter = 0
        self.max_debug_frames = 20   # 🎯 中間段保存20張有價值的調試照片
        
        # 🎯 動態中間段計算參數
        self.total_video_frames = None   # 影片總幀數（由視頻播放器提供）
        self.skip_start_ratio = 0.3      # 跳過前30%
        self.save_middle_ratio = 0.4     # 保存中間40%（30%-70%區間）
        self.total_processed_frames = 0  # 總處理幀數計數器
        self.current_session_dir = None  # 當前會話目錄
        self.manual_save_triggered = False  # 手動觸發保存
        self.manual_trigger_active = False  # 手動觸發狀態
        self._temp_debug_data = None  # 臨時調試數據
        
        logging.info("🔍 背景減除檢測方法初始化完成 (🎯 超高靈敏度 + 200張中間段調試)")
    
    def _reset_background_subtractor(self):
        """重置背景減除器"""
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.bg_history,
            varThreshold=self.bg_var_threshold,
            detectShadows=self.detect_shadows
        )
        logging.debug("背景減除器已重置")
    
    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """基於背景減除的影像預處理 - 支援ROI區域檢測"""
        if frame is None:
            return None
        
        try:
            # 🚀🚀 206fps模式：簡化幀計數
            self.total_processed_frames += 1
            
            # 更新幀尺寸
            self.frame_height, self.frame_width = frame.shape[:2]
            
            # 🎯 ROI 區域提取 (參考 partsCounts_v1.py)
            if self.roi_enabled:
                roi_y = int(self.frame_height * self.roi_position_ratio)
                roi = frame[roi_y:roi_y + self.roi_height, :]
                
                # 存儲ROI位置信息供後續使用
                self.current_roi_y = roi_y
                self.current_roi_height = self.roi_height
                
                # 對ROI區域進行處理
                process_region = roi
            else:
                # 全圖檢測
                process_region = frame
                self.current_roi_y = 0
                self.current_roi_height = self.frame_height
            
            # 1. 背景減除獲得前景遮罩
            fg_mask = self.bg_subtractor.apply(process_region)
            
            # 2. 高斯模糊減少噪聲
            blurred = cv2.GaussianBlur(process_region, self.gaussian_blur_kernel, 0)
            
            # 3. Canny邊緣檢測
            edges = cv2.Canny(blurred, self.canny_low_threshold, self.canny_high_threshold)
            
            # 4. 🚀 極度優化的檢測策略 - 最大限度減少雜訊
            
            # 🔧 方法1: 極強化前景遮罩過濾
            # 使用漸進式開運算去除各種尺寸的雜訊
            small_noise_kernel = np.ones((3, 3), np.uint8)
            fg_step1 = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, small_noise_kernel)
            
            medium_noise_kernel = np.ones((5, 5), np.uint8)
            fg_step2 = cv2.morphologyEx(fg_step1, cv2.MORPH_OPEN, medium_noise_kernel)
            
            large_noise_kernel = np.ones((7, 7), np.uint8)
            fg_cleaned = cv2.morphologyEx(fg_step2, cv2.MORPH_OPEN, large_noise_kernel)
            
            # 🔧 方法2: 只使用強邊緣配合前景遮罩
            # 提高邊緣檢測閾值，只保留強邊緣
            strong_edges = cv2.Canny(blurred, self.canny_low_threshold, self.canny_high_threshold)
            filtered_edges = cv2.bitwise_and(strong_edges, strong_edges, mask=fg_cleaned)
            
            # 5. 二值化強邊緣
            _, thresh = cv2.threshold(filtered_edges, self.binary_threshold, 255, cv2.THRESH_BINARY)
            
            # 6. 🚀 簡化檢測結果 - 主要依賴清理後的前景遮罩
            # 優先使用清理後的前景遮罩，邊緣檢測作為輔助
            combined = cv2.bitwise_or(fg_cleaned, thresh)
            
            # 7. 🔧 強化形態學處理 - 專門針對雜訊優化
            # 多重開運算去除各種尺寸的雜訊
            open_kernel_1 = np.ones((2, 2), np.uint8)
            opened_1 = cv2.morphologyEx(combined, cv2.MORPH_OPEN, open_kernel_1)
            
            open_kernel_2 = np.ones((3, 3), np.uint8)
            opened_2 = cv2.morphologyEx(opened_1, cv2.MORPH_OPEN, open_kernel_2)
            
            # 適度膨脹和閉合
            dilate_kernel = np.ones(self.dilate_kernel_size, np.uint8)
            dilated = cv2.dilate(opened_2, dilate_kernel, iterations=self.dilate_iterations)
            
            close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.close_kernel_size)
            processed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, close_kernel)
            
            # 📸 調試圖片保存 (如果啟用) - 動態中間段保存
            should_create_debug_data = (
                self.debug_save_enabled and 
                self.debug_frame_counter < self.max_debug_frames and
                self._is_in_save_window()  # 🎯 使用動態中間段檢查
            )
            
            self._temp_debug_data = {
                'frame': frame.copy(),
                'process_region': process_region.copy(),
                'fg_mask': fg_mask.copy(),
                'fg_cleaned': fg_cleaned.copy(),
                'processed': processed.copy()
            } if should_create_debug_data else None
            
            # 🔧 檢查手動觸發文件
            self._check_manual_trigger_file()
            
            return processed
            
        except Exception as e:
            logging.error(f"背景減除預處理錯誤: {str(e)}")
            return None
    
    def detect_objects(self, processed_frame: np.ndarray, min_area: int = None, max_area: int = None) -> List[Tuple]:
        """基於連通組件的物件檢測 - 支援穿越計數"""
        if processed_frame is None:
            return []
        
        try:
            min_a = min_area if min_area is not None else self.min_area
            max_a = max_area if max_area is not None else self.max_area
            
            # 連通組件標記 (Connected Component Labeling)
            # 參考 partsCounts_v1.py 的實現
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                processed_frame, connectivity=self.connectivity
            )
            
            current_objects = []
            
            # 遍歷所有連通組件 (跳過背景，從1開始)
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                
                # 面積篩選
                if min_a < area < max_a:
                    # 提取邊界框信息 (ROI座標)
                    x = stats[i, cv2.CC_STAT_LEFT]
                    y = stats[i, cv2.CC_STAT_TOP]
                    w = stats[i, cv2.CC_STAT_WIDTH]
                    h = stats[i, cv2.CC_STAT_HEIGHT]
                    
                    # 🔧 形狀過濾 - 減少雜訊誤判
                    # 計算長寬比
                    aspect_ratio = w / h if h > 0 else 0
                    
                    # 計算填充比例 (物件面積 / 邊界框面積)
                    bbox_area = w * h
                    extent = area / bbox_area if bbox_area > 0 else 0
                    
                    # 計算凸包結實性 (需要提取輪廓)
                    try:
                        # 提取當前組件的遮罩
                        component_mask = (labels == i).astype(np.uint8) * 255
                        contours, _ = cv2.findContours(component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        if contours:
                            contour = contours[0]  # 取最大輪廓
                            hull = cv2.convexHull(contour)
                            hull_area = cv2.contourArea(hull)
                            solidity = area / hull_area if hull_area > 0 else 0
                        else:
                            solidity = 1.0  # 如果無法計算，給予預設值
                    except:
                        solidity = 1.0  # 錯誤時給予預設值
                    
                    # 🚀 嚴格的形狀過濾條件
                    shape_valid = (
                        self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio and
                        extent >= self.min_extent and
                        solidity <= self.max_solidity
                    )
                    
                    if shape_valid:
                        # 獲取質心 (ROI座標)
                        roi_centroid = tuple(map(int, centroids[i]))
                        
                        # 轉換為全圖座標
                        global_centroid = (roi_centroid[0], roi_centroid[1] + self.current_roi_y)
                        global_y = y + self.current_roi_y
                        
                        # 計算等效圓半徑
                        radius = np.sqrt(area / np.pi)
                        
                        # 添加到當前物件列表 (使用全圖座標)
                        # 格式: (x, global_y, w, h, global_centroid, area, radius)
                        current_objects.append((x, global_y, w, h, global_centroid, area, radius))
            
            # 🎯 執行物件追蹤和穿越計數 (參考 partsCounts_v1.py)
            if self.enable_crossing_count:
                self._update_object_tracking(current_objects)
            
            # 💾 保存檢測結果供調試使用
            self.last_detected_objects = current_objects.copy()
            
            # 📸 保存調試圖片的條件
            should_save = (
                self._temp_debug_data is not None and 
                self.debug_frame_counter < self.max_debug_frames and
                (
                    len(current_objects) > 0 or  # 檢測到物件
                    self.manual_save_triggered   # 或手動觸發
                )
            )
            
            # 🎯 在剛進入中間段保存窗口時記錄日誌
            if self.total_video_frames is not None:
                start_frame = int(self.total_video_frames * self.skip_start_ratio)
                if (self.total_processed_frames == start_frame + 1 and self.debug_save_enabled):
                    end_frame = int(self.total_video_frames * (self.skip_start_ratio + self.save_middle_ratio))
                    logging.info(f"📸 開始保存影片中間段調試圖片")
                    logging.info(f"   保存範圍: 第{start_frame}幀 - 第{end_frame}幀")
                    logging.info(f"   預計保存約 {end_frame - start_frame} 幀的數據")
            
            if should_save:
                save_reason = f"中間段檢測到 {len(current_objects)} 個物件" if len(current_objects) > 0 else "手動觸發"
                
                self._save_debug_images(
                    self._temp_debug_data['frame'],
                    self._temp_debug_data['process_region'], 
                    self._temp_debug_data['fg_mask'],
                    self._temp_debug_data['fg_cleaned'],
                    self._temp_debug_data['processed']
                )
                self.debug_frame_counter += 1
                logging.info(f"📸 {save_reason}，已保存調試圖片 {self.debug_frame_counter}/{self.max_debug_frames}")
                
                # 重置手動觸發標記
                self.manual_save_triggered = False
            
            # 清理臨時數據，強制釋放記憶體
            if self._temp_debug_data is not None:
                del self._temp_debug_data
            self._temp_debug_data = None
            
            # 🚀🚀 206fps模式：移除強制垃圾回收以提升性能
            # import gc  # 已禁用
            # if self.debug_frame_counter % 10 == 0:  # 已禁用
            #     gc.collect()  # 已禁用
            
            # 🎯 專注於核心檢測，已移除統計功能
            
            return current_objects
            
        except Exception as e:
            logging.error(f"背景減除檢測錯誤: {str(e)}")
            return []
    
    def _update_object_tracking(self, current_objects: List[Tuple]):
        """改進的物件追蹤和穿越計數邏輯"""
        try:
            self.current_frame_count += 1
            
            # ROI區域邊界
            roi_top = self.current_roi_y
            roi_bottom = self.current_roi_y + self.roi_height
            roi_center = self.current_roi_y + self.roi_height // 2
            
            # 新的追蹤字典
            new_tracks = {}
            
            # 為每個檢測到的物件尋找匹配的追蹤
            for obj in current_objects:
                x, y, w, h, centroid, area, radius = obj
                cx, cy = centroid
                
                matched = False
                best_match_id = None
                best_match_distance = float('inf')
                
                # 與現有追蹤進行匹配 (找最佳匹配)
                for track_id, track in self.object_tracks.items():
                    # 計算距離
                    distance = np.sqrt((cx - track['x'])**2 + (cy - track['y'])**2)
                    
                    # 檢查是否在容差範圍內
                    if (abs(cx - track['x']) < self.crossing_tolerance_x and 
                        abs(cy - track['y']) < self.crossing_tolerance_y and
                        distance < best_match_distance):
                        
                        best_match_distance = distance
                        best_match_id = track_id
                        matched = True
                
                if matched and best_match_id is not None:
                    # 更新現有追蹤
                    old_track = self.object_tracks[best_match_id]
                    new_tracks[best_match_id] = {
                        'x': cx,
                        'y': cy,
                        'first_frame': old_track.get('first_frame', self.current_frame_count),
                        'last_frame': self.current_frame_count,
                        'positions': old_track.get('positions', []) + [(cx, cy)],
                        'counted': old_track.get('counted', False),
                        'in_roi_frames': old_track.get('in_roi_frames', 0) + 1,
                        'max_y': max(old_track.get('max_y', cy), cy),
                        'min_y': min(old_track.get('min_y', cy), cy)
                    }
                else:
                    # 創建新的追蹤
                    new_track_id = max(self.object_tracks.keys()) + 1 if self.object_tracks else 0
                    new_tracks[new_track_id] = {
                        'x': cx,
                        'y': cy,
                        'first_frame': self.current_frame_count,
                        'last_frame': self.current_frame_count,
                        'positions': [(cx, cy)],
                        'counted': False,
                        'in_roi_frames': 1,
                        'max_y': cy,
                        'min_y': cy
                    }
            
            # 🎯 簡化高效穿越計數邏輯 - 提升檢測速度
            for track_id, track in new_tracks.items():
                if not track['counted'] and track['in_roi_frames'] >= self.min_track_frames:
                    # 簡化檢查：只要物件在ROI中出現就計數
                    y_travel = track['max_y'] - track['min_y']
                    
                    # 檢查是否為重複計數（簡化版）
                    is_duplicate = self._check_duplicate_detection_simple(track)
                    
                    # 🚀 極簡計數邏輯：在ROI中檢測到 + 有基本移動 + 非重複
                    valid_crossing = (
                        y_travel >= 5 and  # 基本的Y軸移動（5像素）
                        not is_duplicate   # 非重複檢測
                    )
                    
                    if valid_crossing:
                        # 記錄到歷史中防止重複
                        self._add_to_history(track)
                        
                        self.crossing_counter += 1
                        track['counted'] = True
                        
                        # 🚀🚀 206fps模式：移除計數日誌以提升性能
                        # if self.crossing_counter % 10 == 0:  # 已禁用
                        #     logging.debug(f"✅ 計數檢查點 #{self.crossing_counter}")  # 已禁用
            
            # 清理過期的追蹤 (生命週期管理)
            current_time = self.current_frame_count
            for track_id in list(new_tracks.keys()):
                track = new_tracks[track_id]
                if current_time - track['last_frame'] > self.track_lifetime:
                    del new_tracks[track_id]
            
            # 更新追蹤狀態
            self.object_tracks = new_tracks
            
        except Exception as e:
            logging.error(f"物件追蹤更新錯誤: {str(e)}")
    
    def _check_duplicate_detection_simple(self, track: Dict) -> bool:
        """簡化版重複檢測 - 提升性能"""
        try:
            current_pos = (track['x'], track['y'])
            
            # 只檢查最近的幾個歷史記錄
            recent_history = self.counted_objects_history[-5:] if len(self.counted_objects_history) > 5 else self.counted_objects_history
            
            for hist_pos in recent_history:
                distance = abs(current_pos[0] - hist_pos[0]) + abs(current_pos[1] - hist_pos[1])  # 使用曼哈頓距離，更快
                
                if distance < self.duplicate_distance_threshold:
                    return True  # 發現重複
            
            return False
            
        except Exception:
            return False
    
    def _add_to_history(self, track: Dict):
        """添加已計數物件到歷史記錄"""
        try:
            position = (track['x'], track['y'])
            self.counted_objects_history.append(position)
            
            # 保持歷史記錄在限制範圍內
            if len(self.counted_objects_history) > self.history_length:
                self.counted_objects_history.pop(0)
                
        except Exception as e:
            logging.error(f"添加歷史記錄錯誤: {str(e)}")
    
    def get_crossing_count(self) -> int:
        """獲取穿越計數"""
        return self.crossing_counter
    
    def get_tracking_stats(self) -> Dict[str, Any]:
        """獲取追蹤統計信息 (用於調試)"""
        active_tracks = len(self.object_tracks)
        counted_tracks = sum(1 for track in self.object_tracks.values() if track.get('counted', False))
        
        return {
            'crossing_count': self.crossing_counter,
            'active_tracks': active_tracks,
            'counted_tracks': counted_tracks,
            'frame_count': self.current_frame_count,
            'roi_height': self.roi_height,
            'roi_position': self.roi_position_ratio,
            'history_length': len(self.counted_objects_history),
            'accuracy_features': {
                'min_track_frames': self.min_track_frames,
                'confidence_threshold': self.confidence_threshold,
                'duplicate_prevention': True
            }
        }
    
    def get_accuracy_metrics(self) -> Dict[str, Any]:
        """獲取準確率相關指標"""
        return {
            'total_crossings': self.crossing_counter,
            'confidence_threshold': self.confidence_threshold,
            'min_tracking_frames': self.min_track_frames,
            'duplicate_prevention_enabled': True,
            'history_buffer_size': len(self.counted_objects_history),
            'roi_optimization': {
                'height': self.roi_height,
                'position': self.roi_position_ratio,
                'coverage_threshold': self.crossing_threshold
            }
        }
    
    def reset_crossing_count(self):
        """重置穿越計數"""
        self.crossing_counter = 0
        self.object_tracks = {}
        self.current_frame_count = 0
        self.total_processed_frames = 0  # 🎯 重置總幀數計數器
        self.debug_frame_counter = 0     # 🎯 重置調試圖片計數器
        self.counted_objects_history = []  # 清理歷史記錄
        logging.info("🔄 穿越計數、追蹤、歷史記錄和調試計數器已重置")
    
    def set_video_info(self, total_frames: int, fps: float = 206):
        """設定影片信息，用於動態計算中間段"""
        self.total_video_frames = total_frames
        
        # 計算中間段的開始和結束幀
        start_frame = int(total_frames * self.skip_start_ratio)
        end_frame = int(total_frames * (self.skip_start_ratio + self.save_middle_ratio))
        
        duration_sec = total_frames / fps
        start_time = start_frame / fps
        end_time = end_frame / fps
        
        # 🚀🚀 206fps模式：簡化影片信息日誌
        logging.info(f"🎬 影片: {total_frames}幀, {fps:.1f}fps")
    
    def _is_in_save_window(self) -> bool:
        """檢查當前是否在保存窗口內（影片中間段）"""
        if self.total_video_frames is None:
            # 如果沒有設定影片總幀數，使用舊邏輯
            return self.total_processed_frames > 100  # 簡單跳過前100幀
        
        start_frame = int(self.total_video_frames * self.skip_start_ratio)
        end_frame = int(self.total_video_frames * (self.skip_start_ratio + self.save_middle_ratio))
        
        return start_frame <= self.total_processed_frames <= end_frame
    
    def get_debug_status(self) -> Dict[str, Any]:
        """獲取調試狀態信息"""
        if self.total_video_frames is not None:
            start_frame = int(self.total_video_frames * self.skip_start_ratio)
            end_frame = int(self.total_video_frames * (self.skip_start_ratio + self.save_middle_ratio))
            
            return {
                'total_processed_frames': self.total_processed_frames,
                'total_video_frames': self.total_video_frames,
                'save_start_frame': start_frame,
                'save_end_frame': end_frame,
                'debug_frame_counter': self.debug_frame_counter,
                'max_debug_frames': self.max_debug_frames,
                'is_in_save_window': self._is_in_save_window(),
                'save_progress': f"{self.total_processed_frames - start_frame}/{end_frame - start_frame}" if self._is_in_save_window() else "未在保存窗口內"
            }
        else:
            return {
                'total_processed_frames': self.total_processed_frames,
                'total_video_frames': None,
                'debug_frame_counter': self.debug_frame_counter,
                'max_debug_frames': self.max_debug_frames,
                'is_in_save_window': self.total_processed_frames > 100,
                'note': '未設定影片總幀數，使用簡化邏輯'
            }
    
    def get_roi_info(self) -> Dict[str, Any]:
        """獲取ROI區域信息"""
        return {
            'enabled': self.roi_enabled,
            'y': getattr(self, 'current_roi_y', 0),
            'height': self.roi_height,
            'width': self.frame_width,
            'position_ratio': self.roi_position_ratio
        }
    
    def set_roi_position(self, position_ratio: float):
        """設置ROI位置比例"""
        self.roi_position_ratio = max(0.0, min(1.0, position_ratio))
        logging.info(f"🎯 ROI位置已更新: {self.roi_position_ratio:.2f}")
    
    def reset_background_model(self):
        """重置背景模型 - 用於切換視頻或重新開始計數"""
        self._reset_background_subtractor()
        self.reset_crossing_count()
        logging.info("🔄 背景模型和計數已重置")
    
    def set_parameters(self, params: Dict[str, Any]) -> bool:
        """設置檢測參數"""
        try:
            for key, value in params.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    logging.debug(f"更新背景減除檢測參數 {key}: {value}")
            
            # 如果更新了背景減除器相關參數，需要重置
            bg_params = ['bg_history', 'bg_var_threshold', 'detect_shadows']
            if any(param in params for param in bg_params):
                self._reset_background_subtractor()
                
            return True
        except Exception as e:
            logging.error(f"設置背景減除檢測參數錯誤: {str(e)}")
            return False
    
    # 🧹 已移除不需要的統計和自適應函數，專注於核心檢測
    
    def _save_debug_images(self, original_frame, roi_region, fg_mask, combined_mask, final_processed):
        """保存調試圖片 - 用於分析前後景分離效果"""
        try:
            import os
            import time
            from datetime import datetime
            
            # 初始化會話資料夾 (只在第一次時創建)
            if self.current_session_dir is None:
                now = datetime.now()
                session_folder = now.strftime("%Y%m%d_%H%M%S")
                self.current_session_dir = os.path.join(self.debug_save_dir, f"session_{session_folder}")
                
                # 確保目錄存在
                os.makedirs(self.current_session_dir, exist_ok=True)
                
                # 清理舊檔案
                self._cleanup_debug_folder()
                
                # 創建當前會話的資訊檔案
                info_file = os.path.join(self.current_session_dir, "session_info.txt")
                with open(info_file, 'w', encoding='utf-8') as f:
                    f.write(f"調試會話開始時間: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"檢測方法: 背景減除檢測\n")
                    f.write(f"ROI高度: {self.roi_height}px\n")
                    f.write(f"ROI位置比例: {self.roi_position_ratio}\n")
                    f.write(f"最大調試幀數: {self.max_debug_frames}\n\n")
                
                logging.info(f"📸 開始新的調試會話: {self.current_session_dir}")
            
            timestamp = int(time.time() * 1000)  # 毫秒時間戳
            frame_id = f"{self.debug_frame_counter:03d}_{timestamp}"
            
            # 使用當前會話目錄
            save_dir = self.current_session_dir
            
            # 1. 保存原始完整幀 (帶ROI標記)
            original_with_roi = original_frame.copy()
            roi_y = int(self.frame_height * self.roi_position_ratio)
            
            # 繪製ROI區域
            cv2.rectangle(original_with_roi, (0, roi_y), 
                         (self.frame_width, roi_y + self.roi_height), (0, 255, 0), 2)
            cv2.putText(original_with_roi, f"ROI ({self.roi_height}px)", 
                       (10, roi_y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            cv2.imwrite(f"{save_dir}/01_original_with_roi_{frame_id}.jpg", original_with_roi)
            
            # 2. 保存ROI原始區域
            cv2.imwrite(f"{save_dir}/02_roi_region_{frame_id}.jpg", roi_region)
            
            # 3. 保存前景遮罩 (背景減除結果)
            cv2.imwrite(f"{save_dir}/03_foreground_mask_{frame_id}.jpg", fg_mask)
            
            # 4. 保存合併遮罩 (多重檢測結果合併)
            cv2.imwrite(f"{save_dir}/04_combined_detection_{frame_id}.jpg", combined_mask)
            
            # 5. 保存最終處理結果 (形態學處理後)
            cv2.imwrite(f"{save_dir}/05_final_processed_{frame_id}.jpg", final_processed)
            
            # 6. 保存檢測到的物件 (如果有)
            if hasattr(self, 'last_detected_objects') and self.last_detected_objects:
                detection_result = roi_region.copy()
                if len(detection_result.shape) == 2:
                    detection_result = cv2.cvtColor(detection_result, cv2.COLOR_GRAY2BGR)
                
                # 繪製檢測到的物件
                for obj in self.last_detected_objects:
                    x, y, w, h, centroid, area, radius = obj
                    # 轉換回ROI座標
                    roi_y_offset = int(self.frame_height * self.roi_position_ratio)
                    local_y = y - roi_y_offset
                    local_centroid = (centroid[0], centroid[1] - roi_y_offset)
                    
                    if 0 <= local_y < self.roi_height:
                        # 繪製邊界框
                        cv2.rectangle(detection_result, (x, local_y), (x + w, local_y + h), (0, 255, 0), 2)
                        # 繪製中心點
                        cv2.circle(detection_result, local_centroid, 3, (255, 0, 0), -1)
                        # 標註面積
                        cv2.putText(detection_result, f'{int(area)}', 
                                   (x, local_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                
                cv2.imwrite(f"{save_dir}/06_detected_objects_{frame_id}.jpg", detection_result)
            
            # 7. 保存檢測參數信息
            info_file = f"{save_dir}/07_detection_params_{frame_id}.txt"
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write(f"檢測參數信息 - 幀 {self.debug_frame_counter}\n")
                f.write(f"時間戳: {timestamp}\n")
                f.write(f"ROI高度: {self.roi_height}px\n")
                f.write(f"ROI位置比例: {self.roi_position_ratio}\n")
                f.write(f"背景減除閾值: {self.bg_var_threshold}\n")
                f.write(f"二值化閾值: {self.binary_threshold}\n")
                f.write(f"最小面積: {self.min_area}\n")
                f.write(f"最大面積: {self.max_area}\n")
                f.write(f"Canny低閾值: {self.canny_low_threshold}\n")
                f.write(f"Canny高閾值: {self.canny_high_threshold}\n")
                f.write(f"膨脹核大小: {self.dilate_kernel_size}\n")
                f.write(f"膨脹迭代次數: {self.dilate_iterations}\n")
                f.write(f"檢測到物件數: {len(getattr(self, 'last_detected_objects', []))}\n")
                f.write(f"穿越計數: {self.crossing_counter}\n")
            
            # 🚀 減少日誌輸出，只在完成時記錄
            if self.debug_frame_counter >= self.max_debug_frames:
                logging.info(f"📸 調試圖片保存完成 {self.max_debug_frames}/{self.max_debug_frames}")
            
        except Exception as e:
            logging.error(f"保存調試圖片錯誤: {str(e)}")
    
    def _cleanup_debug_folder(self):
        """清理調試資料夾中的舊檔案"""
        try:
            import os
            import glob
            
            # 刪除所有調試檔案
            for pattern in ['*.jpg', '*.txt']:
                files = glob.glob(os.path.join(self.debug_save_dir, pattern))
                for file in files:
                    try:
                        os.remove(file)
                    except:
                        pass
            
            logging.info("🗑️ 清理舊的調試檔案完成")
            
        except Exception as e:
            logging.debug(f"清理調試資料夾錯誤: {str(e)}")
    
    def _check_manual_trigger_file(self):
        """檢查手動觸發文件"""
        try:
            from pathlib import Path
            trigger_file = Path("/tmp/basler_debug_trigger.txt")
            
            if trigger_file.exists():
                # 讀取觸發信號
                trigger_content = trigger_file.read_text().strip()
                if trigger_content.startswith("TRIGGER_"):
                    # 強制啟用調試保存
                    self.manual_trigger_active = True
                    logging.info(f"📸 檢測到手動觸發信號: {trigger_content}")
                    
                    # 刪除觸發文件
                    trigger_file.unlink()
                    
        except Exception as e:
            logging.debug(f"檢查手動觸發文件錯誤: {str(e)}")
    
    def enable_debug_save(self, enabled: bool = True):
        """啟用或禁用調試圖片保存"""
        self.debug_save_enabled = enabled
        if enabled:
            self.debug_frame_counter = 0  # 重置計數器
            logging.info("📸 調試圖片保存已啟用")
        else:
            logging.info("📸 調試圖片保存已禁用")
    
    def get_debug_info(self) -> Dict[str, Any]:
        """獲取調試信息"""
        return {
            'debug_enabled': self.debug_save_enabled,
            'frames_saved': self.debug_frame_counter,
            'max_frames': self.max_debug_frames,
            'save_directory': self.debug_save_dir,
            'current_session': self.current_session_dir
        }
    
    def trigger_manual_save(self):
        """手動觸發保存當前幀 - 用於捕捉特定畫面"""
        self.manual_save_triggered = True
        logging.info("🔧 手動觸發調試圖片保存")

    @property
    def name(self) -> str:
        return "BackgroundSubtractionDetection"


