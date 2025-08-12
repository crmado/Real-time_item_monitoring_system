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
        # 🎯 平衡檢測 - 減少誤判，保持準確性
        self.min_area = 25   # 🔧 提高最小面積，過濾雜訊 (8→25)  
        self.max_area = 3000 # 🔧 適中的上限 (4000→3000)
        
        # 物件形狀過濾參數 - 適度嚴格，減少雜訊
        self.min_aspect_ratio = 0.1  # 更合理的長寬比 (0.003→0.1)
        self.max_aspect_ratio = 8.0  # 適度限制極端形狀 (20.0→8.0)
        self.min_extent = 0.2        # 合理的填充比例要求 (0.0003→0.2)
        self.max_solidity = 1.0      # 嚴格的結實性限制 (3.0→1.0)
        
        # 🎯 適度敏感背景減除 - 平衡檢測與雜訊
        self.bg_history = 700    # 增加歷史幀數穩定背景 (500→700)
        self.bg_var_threshold = 12  # 🔧 提高閾值減少雜訊 (3→12)
        self.detect_shadows = False  # 關閉陰影檢測
        
        # 🎯 保守邊緣檢測 - 減少雜訊檢測
        self.gaussian_blur_kernel = (5, 5)  # 增加模糊減少雜訊 (3→5)
        self.canny_low_threshold = 20        # 🔧 提高低閾值 (8→20)
        self.canny_high_threshold = 60       # 🔧 提高高閾值 (35→60) 
        self.binary_threshold = 15           # 🔧 提高二值化閾值 (5→15)
        
        # 🔍 加強雜訊過濾 - 使用更大的形態學核
        self.dilate_kernel_size = (3, 3)    # 🔧 適度的核大小 (2→3)
        self.dilate_iterations = 1           # 🔧 保持適度膨脹
        self.close_kernel_size = (5, 5)     # 🔧 更大的核，更好的填補 (3→5)
        
        # 🎯 額外的雜訊過濾
        self.opening_kernel_size = (4, 4)   # 🆕 開運算核，去除小雜訊
        self.opening_iterations = 2          # 🆕 多次開運算去噪
        
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
        
        # 🎯 提高追蹤穩定性 - 減少誤判
        self.track_lifetime = 10  # 增加追蹤週期，提高穩定性 (5→10)
        self.min_track_frames = 3  # 需要多幀確認，減少誤判 (1→3)
        self.crossing_threshold = 0.1   # 提高穿越閾值，更保守 (0.03→0.1)
        self.confidence_threshold = 0.1  # 提高置信度要求 (0.03→0.1)
        
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
        
        # 📸 合成調試圖片功能 - 整合所有分析階段於一張圖片
        self.debug_save_enabled = True   # 🎯 啟用調試圖片保存
        self.debug_save_dir = "/Users/crmado/github/Real-time_item_monitoring_system/basler_mvc/recordings/composite_debug"
        self.debug_frame_counter = 0
        self.max_debug_frames = 200     # 🎯 限制調試圖片數量避免占用過多空間
        
        # 🆕 合成調試圖片模式 - 預設啟用 
        self.composite_debug_enabled = True  # 合成調試圖片開關（預設啟用）
        
        # 🎯 動態中間段計算參數
        self.total_video_frames = None   # 影片總幀數（由視頻播放器提供）
        self.skip_start_ratio = 0.3      # 跳過前30%
        self.save_middle_ratio = 0.4     # 保存中間40%（30%-70%區間）
        self.total_processed_frames = 0  # 總處理幀數計數器
        self.current_session_dir = None  # 當前會話目錄
        self.manual_save_triggered = False  # 手動觸發保存
        self.manual_trigger_active = False  # 手動觸發狀態
        self._temp_debug_data = None  # 臨時調試數據
        
        logging.info("🔍 背景減除檢測方法初始化完成 (🎯 極度高靈敏度 - 專門優化小零件檢測)")
    
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
            
            # 4. 🚀 多角度檢測策略 - 結合多種方法提高檢測率
            
            # 🔧 方法1: 超極小化形態學處理 - 最大化保留小零件
            # 使用多層次微型開運算，漸進式去噪，保留極小零件
            micro_kernel = np.ones((1, 1), np.uint8)  # 微型核保留最小特徵
            fg_step1 = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, micro_kernel, iterations=1)
            
            # 第二層：稍大一點的核，但迭代次數減少
            nano_kernel = np.ones((2, 2), np.uint8)  
            fg_cleaned = cv2.morphologyEx(fg_step1, cv2.MORPH_OPEN, nano_kernel, iterations=1)
            
            # 🔧 方法2: 多敏感度邊緣檢測
            # 使用兩種不同敏感度的邊緣檢測
            strong_edges = cv2.Canny(blurred, self.canny_low_threshold, self.canny_high_threshold)
            sensitive_edges = cv2.Canny(blurred, self.canny_low_threshold//2, self.canny_high_threshold//2)
            
            # 🔧 方法3: 自適應閾值檢測 - 補強小零件檢測
            gray_roi = cv2.cvtColor(process_region, cv2.COLOR_BGR2GRAY) if len(process_region.shape) == 3 else process_region
            adaptive_thresh = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # 結合前景遮罩和邊緣檢測
            filtered_strong = cv2.bitwise_and(strong_edges, strong_edges, mask=fg_cleaned)
            filtered_sensitive = cv2.bitwise_and(sensitive_edges, sensitive_edges, mask=fg_cleaned)
            filtered_adaptive = cv2.bitwise_and(adaptive_thresh, adaptive_thresh, mask=fg_cleaned)
            
            # 5. 二值化和合併
            _, thresh_strong = cv2.threshold(filtered_strong, self.binary_threshold, 255, cv2.THRESH_BINARY)
            _, thresh_sensitive = cv2.threshold(filtered_sensitive, self.binary_threshold//2, 255, cv2.THRESH_BINARY)
            
            # 6. 🚀 多方法聯合檢測 - 提高召回率
            # 聯合多種檢測方法的結果
            combined = cv2.bitwise_or(fg_cleaned, thresh_strong)
            combined = cv2.bitwise_or(combined, thresh_sensitive)
            combined = cv2.bitwise_or(combined, filtered_adaptive)
            
            # 7. 🔧 加強雜訊過濾的形態學處理
            # 多階段去噪，強化雜訊過濾能力
            
            # 第一階段：強化開運算去除小雜訊
            opening_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.opening_kernel_size)
            opened_stage1 = cv2.morphologyEx(combined, cv2.MORPH_OPEN, opening_kernel, iterations=self.opening_iterations)
            
            # 第二階段：中等核心開運算，進一步清理
            medium_open_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            opened_stage2 = cv2.morphologyEx(opened_stage1, cv2.MORPH_OPEN, medium_open_kernel, iterations=1)
            
            # 適度膨脹連接相近的零件區域
            dilate_kernel = np.ones(self.dilate_kernel_size, np.uint8)
            dilated = cv2.dilate(opened_stage2, dilate_kernel, iterations=self.dilate_iterations)
            
            # 閉合運算填補零件內部的小洞
            close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.close_kernel_size)
            processed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, close_kernel, iterations=1)
            
            # 📸 調試圖片保存 (如果啟用) - 完整序列保存
            should_create_debug_data = (
                self.debug_save_enabled and 
                self.debug_frame_counter < self.max_debug_frames
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
            # 🎯 強制使用極小零件檢測參數，避免被外部覆蓋
            # 只有當外部參數更小時才採用，確保捕獲極小零件
            min_a = min(min_area if min_area is not None else float('inf'), self.min_area)
            max_a = max(max_area if max_area is not None else 0, self.max_area)
            
            # 連通組件標記 (Connected Component Labeling)
            # 參考 partsCounts_v1.py 的實現
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                processed_frame, connectivity=self.connectivity
            )
            
            current_objects = []
            
            # 🔍 調試：記錄總組件數
            if self.current_frame_count % 20 == 0:  # 每20幀記錄一次
                logging.debug(f"總連通組件數: {num_labels-1}, 面積範圍: {min_a}-{max_a}")
            
            # 遍歷所有連通組件 (跳過背景，從1開始)
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                
                # 🔍 調試：記錄面積過濾
                if self.current_frame_count % 20 == 0 and i <= 3:  # 每20幀記錄前3個組件
                    logging.debug(f"組件{i}: 面積={area}, 是否通過面積過濾={min_a < area < max_a}")
                
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
                    
                    # 🔍 超極度放寬形狀過濾 - 專門為小零件檢測優化
                    shape_valid = (
                        aspect_ratio > self.min_aspect_ratio and  # 超寬鬆值 0.005
                        extent > self.min_extent and              # 超寬鬆值 0.0005  
                        solidity <= self.max_solidity             # 超放寬值 2.0
                    )
                    
                    # 🔍 詳細調試信息：記錄所有過濾情況 
                    if not shape_valid and self.current_frame_count % 5 == 0:  # 更頻繁的調試記錄
                        reasons = []
                        if aspect_ratio <= self.min_aspect_ratio:
                            reasons.append(f"長寬比太小({aspect_ratio:.4f} <= {self.min_aspect_ratio})")
                        if extent <= self.min_extent:
                            reasons.append(f"填充比例太小({extent:.4f} <= {self.min_extent})")
                        if solidity > self.max_solidity:
                            reasons.append(f"結實性太大({solidity:.3f} > {self.max_solidity})")
                        
                        logging.debug(f"🚫 小零件被過濾: 面積={area}, 原因={'; '.join(reasons)}")
                    
                    # 🔍 記錄通過檢測的小零件
                    if shape_valid and area < 50 and self.current_frame_count % 5 == 0:
                        logging.debug(f"✅ 檢測到小零件: 面積={area}, 長寬比={aspect_ratio:.3f}, 位置=({x},{y})")
                    
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
                # 🔍 調試：記錄追蹤狀態 (每20幀記錄一次)
                if self.current_frame_count % 20 == 0:
                    logging.debug(f"🔍 開始追蹤: 檢測物件數={len(current_objects)}, 啟用計數={self.enable_crossing_count}")
                self._update_object_tracking(current_objects)
            
            # 💾 保存檢測結果供調試使用
            self.last_detected_objects = current_objects.copy()
            
            # 📸 保存調試圖片的條件 - 只在視頻回放模式下啟用
            should_save = (
                self._temp_debug_data is not None and 
                self.debug_frame_counter < self.max_debug_frames and
                self.debug_save_enabled and
                self.composite_debug_enabled
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
                save_reason = f"第{self.debug_frame_counter+1}幀 (檢測到 {len(current_objects)} 個物件)"
                
                # 🖼️ 使用新的合成調試圖片保存方法
                self._save_composite_debug_image(
                    self._temp_debug_data['frame'],           # 原始幀
                    self._temp_debug_data['process_region'],  # ROI區域
                    self._temp_debug_data['fg_mask'],         # 前景遮罩
                    self._temp_debug_data['fg_cleaned'],      # 合併檢測結果
                    self._temp_debug_data['processed'],       # 最終處理結果
                    current_objects                           # 檢測到的物件
                )
                self.debug_frame_counter += 1
                
                # 每50幀記錄一次進度
                if self.debug_frame_counter % 50 == 0:
                    logging.info(f"🖼️ 合成調試圖片 {save_reason}，已保存 {self.debug_frame_counter}/{self.max_debug_frames}")
                
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
            
            # 🔍 調試：記錄檢測結果
            if self.current_frame_count % 20 == 0:  # 每20幀記錄一次
                logging.debug(f"最終檢測到物件數: {len(current_objects)}")
            
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
            
            # 🔍 調試：記錄軌跡狀態 (每20幀記錄一次)
            if self.current_frame_count % 20 == 0:
                logging.debug(f"🎯 軌跡狀態: 總軌跡數={len(new_tracks)}, 當前穿越計數={self.crossing_counter}")
            
            # 🎯 簡化高效穿越計數邏輯 - 提升檢測速度
            for track_id, track in new_tracks.items():
                if not track['counted'] and track['in_roi_frames'] >= self.min_track_frames:
                    # 簡化檢查：只要物件在ROI中出現就計數
                    y_travel = track['max_y'] - track['min_y']
                    
                    # 檢查是否為重複計數（簡化版）
                    is_duplicate = self._check_duplicate_detection_simple(track)
                    
                    # 🎯 提高計數要求：確保穩定檢測，減少誤判
                    valid_crossing = (
                        y_travel >= 10 and          # 🔧 提高移動要求，確保真實移動 (1→10像素)
                        track['in_roi_frames'] >= self.min_track_frames and  # 確保多幀穩定檢測
                        not is_duplicate            # 非重複檢測
                    )
                    
                    # 🔍 調試：記錄計數邏輯 (每10幀記錄一次)
                    if self.current_frame_count % 10 == 0 and track_id in list(new_tracks.keys())[:2]:
                        logging.debug(f"物件{track_id}: Y移動={y_travel}px, 重複={is_duplicate}, 在ROI幀數={track['in_roi_frames']}, 有效穿越={valid_crossing}")
                    
                    if valid_crossing:
                        # 記錄到歷史中防止重複
                        self._add_to_history(track)
                        
                        self.crossing_counter += 1
                        track['counted'] = True
                        
                        # 🔍 重要：記錄每次成功計數 (性能影響小但很重要)
                        logging.info(f"✅ 成功計數 #{self.crossing_counter} - 物件{track_id} (Y移動: {y_travel}px)")
            
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
    
    def _save_composite_debug_image(self, original_frame, roi_region, fg_mask, combined_mask, final_processed, detected_objects):
        """保存合成調試圖片 - 將所有分析階段合併為一張大圖"""
        try:
            import os
            import time
            from datetime import datetime
            
            # 初始化會話資料夾 (只在第一次時創建)
            if self.current_session_dir is None:
                now = datetime.now()
                session_folder = now.strftime("%Y%m%d_%H%M%S")
                self.current_session_dir = os.path.join(self.debug_save_dir, f"composite_{session_folder}")
                
                # 確保目錄存在
                os.makedirs(self.current_session_dir, exist_ok=True)
                
                # 創建當前會話的資訊檔案
                info_file = os.path.join(self.current_session_dir, "session_info.txt")
                with open(info_file, 'w', encoding='utf-8') as f:
                    f.write(f"🎯 合成調試會話開始時間: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"檢測方法: 背景減除檢測 (合成圖片模式)\n")
                    f.write(f"ROI高度: {self.roi_height}px\n")
                    f.write(f"ROI位置比例: {self.roi_position_ratio}\n")
                    f.write(f"最大調試幀數: {self.max_debug_frames}\n")
                    f.write(f"圖片格式: 3x2合成布局\n\n")
                
                logging.info(f"🖼️ 開始新的合成調試會話: {self.current_session_dir}")
            
            timestamp = int(time.time() * 1000)
            frame_id = f"{self.debug_frame_counter:04d}_{timestamp}"
            
            # 🎨 創建合成圖片布局 (3列 x 2行)
            # 準備各個圖片組件
            
            # 1. 原始圖片 (帶ROI標記)
            original_with_roi = original_frame.copy()
            roi_y = int(self.frame_height * self.roi_position_ratio)
            cv2.rectangle(original_with_roi, (0, roi_y), 
                         (self.frame_width, roi_y + self.roi_height), (0, 255, 0), 3)
            cv2.putText(original_with_roi, f"ROI ({self.roi_height}px)", 
                       (10, roi_y - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            # 2. ROI區域 (彩色)
            roi_color = roi_region.copy()
            if len(roi_color.shape) == 2:
                roi_color = cv2.cvtColor(roi_color, cv2.COLOR_GRAY2BGR)
            
            # 3. 前景遮罩 (轉彩色以便合成)
            fg_mask_color = cv2.cvtColor(fg_mask, cv2.COLOR_GRAY2BGR)
            
            # 4. 合併檢測結果 (轉彩色)
            combined_color = cv2.cvtColor(combined_mask, cv2.COLOR_GRAY2BGR)
            
            # 5. 最終處理結果 (轉彩色)
            final_color = cv2.cvtColor(final_processed, cv2.COLOR_GRAY2BGR)
            
            # 6. 檢測結果圖 (在ROI上繪製檢測框)
            detection_result = roi_color.copy()
            if detected_objects:
                for obj in detected_objects:
                    x, y, w, h, centroid, area, radius = obj
                    # 轉換回ROI座標
                    roi_y_offset = int(self.frame_height * self.roi_position_ratio)
                    local_y = y - roi_y_offset
                    local_centroid = (centroid[0], centroid[1] - roi_y_offset)
                    
                    if 0 <= local_y < self.roi_height and 0 <= local_centroid[1] < self.roi_height:
                        # 繪製邊界框
                        cv2.rectangle(detection_result, (x, local_y), (x + w, local_y + h), (0, 255, 0), 2)
                        # 繪製中心點
                        cv2.circle(detection_result, local_centroid, 4, (255, 0, 0), -1)
                        # 標註面積
                        cv2.putText(detection_result, f'{int(area)}', 
                                   (x, max(5, local_y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            
            # 🏗️ 調整所有圖片到統一尺寸
            target_height = 300  # 統一高度
            target_width = 400   # 統一寬度
            
            def resize_and_pad(img, target_h, target_w):
                """調整圖片尺寸到固定尺寸並保持比例"""
                h, w = img.shape[:2]
                
                # 計算縮放比例，保持圖片比例
                scale_h = target_h / h
                scale_w = target_w / w
                scale = min(scale_h, scale_w)  # 使用較小的縮放比例保持比例
                
                new_h = int(h * scale)
                new_w = int(w * scale)
                
                # 縮放圖片
                resized = cv2.resize(img, (new_w, new_h))
                
                # 創建固定尺寸的畫布
                canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
                
                # 計算居中位置
                start_y = (target_h - new_h) // 2
                start_x = (target_w - new_w) // 2
                
                # 將縮放後的圖片放到畫布中央
                canvas[start_y:start_y+new_h, start_x:start_x+new_w] = resized
                
                return canvas
            
            # 調整所有圖片尺寸
            img1 = resize_and_pad(original_with_roi, target_height, target_width)
            img2 = resize_and_pad(roi_color, target_height, target_width)
            img3 = resize_and_pad(fg_mask_color, target_height, target_width)
            img4 = resize_and_pad(combined_color, target_height, target_width)
            img5 = resize_and_pad(final_color, target_height, target_width)
            img6 = resize_and_pad(detection_result, target_height, target_width)
            
            # 添加標題文字
            def add_title(img, title, bg_color=(0, 0, 0)):
                """在圖片頂部添加標題"""
                h, w = img.shape[:2]
                title_height = 40
                titled_img = np.full((h + title_height, w, 3), bg_color, dtype=np.uint8)
                titled_img[title_height:, :] = img
                
                # 添加標題文字
                cv2.putText(titled_img, title, (10, 25), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                return titled_img
            
            # 為每張圖片添加標題
            img1_titled = add_title(img1, "1. Original + ROI")
            img2_titled = add_title(img2, "2. ROI Region")  
            img3_titled = add_title(img3, "3. Foreground Mask")
            img4_titled = add_title(img4, "4. Combined Detection")
            img5_titled = add_title(img5, "5. Final Processed")
            img6_titled = add_title(img6, f"6. Objects ({len(detected_objects)})")
            
            # 🖼️ 合成最終圖片 (3x2布局)
            # 第一行
            row1 = np.hstack([img1_titled, img2_titled, img3_titled])
            # 第二行  
            row2 = np.hstack([img4_titled, img5_titled, img6_titled])
            
            # 合併兩行
            composite_img = np.vstack([row1, row2])
            
            # 🏷️ 添加底部參數信息
            info_height = 120
            info_panel = np.zeros((info_height, composite_img.shape[1], 3), dtype=np.uint8)
            
            # 參數文字信息
            params_text = [
                f"Frame: {self.debug_frame_counter:04d} | Count: {self.crossing_counter} | Objects: {len(detected_objects)}",
                f"ROI: {self.roi_height}px @ {self.roi_position_ratio:.2f} | MinArea: {self.min_area} | MaxArea: {self.max_area}",
                f"BG Threshold: {self.bg_var_threshold} | Binary: {self.binary_threshold} | Canny: {self.canny_low_threshold}-{self.canny_high_threshold}",
                f"Time: {datetime.fromtimestamp(timestamp/1000).strftime('%H:%M:%S.%f')[:-3]}"
            ]
            
            # 在信息面板上添加文字
            for i, text in enumerate(params_text):
                y_pos = 25 + i * 25
                cv2.putText(info_panel, text, (10, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # 合併信息面板
            final_composite = np.vstack([composite_img, info_panel])
            
            # 💾 保存合成圖片
            save_path = f"{self.current_session_dir}/composite_debug_{frame_id}.jpg"
            cv2.imwrite(save_path, final_composite)
            
            # 📊 每50幀記錄一次進度
            if self.debug_frame_counter % 50 == 0:
                logging.info(f"🖼️ 合成調試圖片已保存 {self.debug_frame_counter}/{self.max_debug_frames}")
            
        except Exception as e:
            logging.error(f"保存合成調試圖片錯誤: {str(e)}")
    
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

    def enable_composite_debug(self, enabled: bool = True, mode: str = "playback"):
        """啟用或禁用合成調試圖片保存"""
        # 🎯 只在視頻回放模式下允許調試圖片保存
        if mode in ["live", "recording"]:
            self.composite_debug_enabled = False
            self.debug_save_enabled = False
            logging.info(f"🖼️ {mode}模式下自動禁用調試圖片保存（性能優化）")
            return
            
        self.composite_debug_enabled = enabled
        self.debug_save_enabled = enabled
        
        if enabled:
            self.debug_frame_counter = 0  # 重置計數器
            self.current_session_dir = None  # 重置會話目錄
            logging.info(f"🖼️ 合成調試圖片保存已啟用 (模式: {mode})")
        else:
            logging.info("🖼️ 合成調試圖片保存已禁用")

    def get_composite_debug_info(self) -> Dict[str, Any]:
        """獲取合成調試圖片保存信息"""
        return {
            'enabled': self.composite_debug_enabled,
            'frames_saved': self.debug_frame_counter,
            'max_frames': self.max_debug_frames,
            'save_directory': self.debug_save_dir,
            'current_session': self.current_session_dir,
            'progress_percentage': (self.debug_frame_counter / self.max_debug_frames) * 100 if self.max_debug_frames > 0 else 0,
            'layout': '3x2 composite layout with annotations'
        }

    @property
    def name(self) -> str:
        return "BackgroundSubtractionDetection"


