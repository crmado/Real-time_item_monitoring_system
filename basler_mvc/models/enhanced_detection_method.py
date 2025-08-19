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
        # 🚀 高速檢測模式控制
        self.ultra_high_speed_mode = False  # 超高速模式 (206-376fps)
        self.target_fps = 280  # 目標FPS，根據相機規格動態調整
        
        # 🎯 極小零件檢測 - 專門為小零件優化參數
        self.min_area = 3    # 🔧 極度降低以捕獲極小零件 (5→3)  
        self.max_area = 3000 # 🔧 適中的上限 (4000→3000)
        
        # 物件形狀過濾參數 - 專為小零件放寬條件
        self.min_aspect_ratio = 0.001 # 極度寬鬆的長寬比適應小零件 (0.01→0.001)
        self.max_aspect_ratio = 100.0 # 極度放寬極端形狀限制 (50.0→100.0)
        self.min_extent = 0.001       # 極度降低填充比例要求 (0.01→0.001)
        self.max_solidity = 5.0       # 極度放寬結實性限制 (2.0→5.0)
        
        # 🎯 超穩定背景減除 - 專為小零件長期檢測優化
        self.bg_history = 1000   # 大幅增加歷史幀數避免快速背景更新 (700→1000)
        self.bg_var_threshold = 3   # 🔧 極低閾值確保最高敏感度 (5→3)
        self.detect_shadows = False  # 關閉陰影檢測
        self.bg_learning_rate = 0.001  # 🆕 極低學習率避免小零件被納入背景
        
        # 🚀 高速模式下的簡化參數 - 也針對小零件優化
        self.high_speed_bg_history = 100      # 高速模式下減少歷史幀數
        self.high_speed_bg_var_threshold = 8  # 高速模式下也降低閾值 (16→8)
        self.high_speed_min_area = 2          # 高速模式下極度降低最小面積 (15→2)
        self.high_speed_max_area = 2000       # 高速模式下降低最大面積
        self.high_speed_binary_threshold = 3  # 高速模式下的二值化閾值
        
        # 🎯 極高敏感度邊緣檢測 - 專為小零件檢測優化
        self.gaussian_blur_kernel = (1, 1)  # 最小模糊保留最多細節 (3→1)
        self.canny_low_threshold = 3         # 🔧 極低闾值提高敏感度 (8→3)
        self.canny_high_threshold = 10       # 🔧 極低闾值提高敏感度 (25→10) 
        self.binary_threshold = 1            # 🔧 極低闾值提高敏感度 (8→1)
        
        # 🔍 極度減少形態學處理 - 最大化保留小零件
        self.dilate_kernel_size = (1, 1)    # 🔧 最小核避免過度膨脹 (2→1)
        self.dilate_iterations = 0           # 🔧 禁用膨脹以保留小零件 (1→0)
        self.close_kernel_size = (1, 1)     # 🔧 最小核避免過度閉合 (3→1)
        
        # 🎯 最小化雜訊過濾 - 最大化保留小零件
        self.opening_kernel_size = (1, 1)   # 🆕 最小開運算核 (2→1)
        self.opening_iterations = 0          # 🆕 禁用開運算以保留小零件 (1→0)
        
        # 連通組件參數
        self.connectivity = 4  # 4-連通或8-連通
        
        # 🎯 ROI 檢測區域參數 (根據影像分析結果優化)
        self.roi_enabled = True
        self.roi_height = 80  # ROI 區域高度 (保持80以捕獲完整零件)
        self.roi_position_ratio = 0.15  # ROI 位置比例 (調整到0.15，更靠近頂部)
        self.current_roi_y = 0  # 當前ROI的Y座標
        
        # 🎯 物件追蹤和計數參數 - 為小零件優化
        self.enable_crossing_count = True
        self.crossing_tolerance_x = 50  # x方向追蹤容差 (增大以適應小零件移動)
        self.crossing_tolerance_y = 80  # y方向追蹤容差 (增大以適應ROI高度)
        
        # 🎯 為小零件降低追蹤門檻 - 提高檢測率
        self.track_lifetime = 8   # 適度的追蹤週期 (10→8)
        self.min_track_frames = 2 # 平衡要求，既避免誤判又保持檢測率 (3→2)
        self.crossing_threshold = 0.05   # 降低穿越閾值，提高小零件敏感度 (0.1→0.05)
        self.confidence_threshold = 0.05  # 降低置信度要求，提高小零件檢測 (0.1→0.05)
        
        # 🛡️ 簡化防重複機制 - 提升性能
        self.counted_objects_history = []  # 已計數物件的歷史記錄
        self.history_length = 10  # 減少歷史長度，提高效率
        self.duplicate_distance_threshold = 15  # 更嚴格的重複檢測距離 (25→15)
        
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
        self.max_debug_frames = float('inf')  # 🎯 保存全部照片，不設限制
        
        # 🆕 合成調試圖片模式 - 預設啟用 
        self.composite_debug_enabled = True  # 合成調試圖片開關（預設啟用）
        
        # 🎯 動態中間段計算參數 - 添加自定義起始幀選項
        self.total_video_frames = None   # 影片總幀數（由視頻播放器提供）
        self.skip_start_ratio = 0.3      # 跳過前30%
        self.save_middle_ratio = 0.4     # 保存中間40%（30%-70%區間）
        self.custom_start_frame = None   # 自定義起始幀（如2500）
        self.total_processed_frames = 0  # 總處理幀數計數器
        self.current_session_dir = None  # 當前會話目錄
        self.manual_save_triggered = False  # 手動觸發保存
        self.manual_trigger_active = False  # 手動觸發狀態
        self._temp_debug_data = None  # 臨時調試數據
        
        logging.info("🔍 背景減除檢測方法初始化完成 (🎯 極度高靈敏度 - 超級小零件檢測優化)")
        logging.info(f"🔧 超敏感參數: min_area={self.min_area}, bg_var_threshold={self.bg_var_threshold}, min_aspect_ratio={self.min_aspect_ratio}, min_extent={self.min_extent}")
        logging.info(f"🔧 最小化形態學: opening={self.opening_kernel_size}x{self.opening_iterations}, dilate={self.dilate_kernel_size}x{self.dilate_iterations}, close={self.close_kernel_size}")
        logging.info(f"🔧 背景穩定性: history={self.bg_history}, learning_rate={self.bg_learning_rate}, var_threshold={self.bg_var_threshold}")
        logging.info(f"🔧 邊緣檢測: canny={self.canny_low_threshold}-{self.canny_high_threshold}, binary_thresh={self.binary_threshold}")
    
    def enable_ultra_high_speed_mode(self, enabled: bool = True, target_fps: int = 280):
        """啟用超高速檢測模式 (206-376fps)"""
        self.ultra_high_speed_mode = enabled
        self.target_fps = target_fps
        
        if enabled:
            # 🚀 自動調整參數以適應目標FPS
            if target_fps >= 350:
                # 376fps模式 - 極度簡化但保持小零件檢測能力
                self.high_speed_bg_history = 50
                self.high_speed_bg_var_threshold = 3  # 🔧 大幅降低以檢測小零件 (20→3)
                self.high_speed_min_area = 3          # 🔧 大幅降低以檢測小零件 (80→3)
                self.high_speed_binary_threshold = 2  # 🔧 極低二值化閾值
                logging.info(f"🚀 啟用376fps超高速模式 (小零件優化)")
            elif target_fps >= 250:
                # 280fps模式 - 平衡簡化但保持小零件檢測
                self.high_speed_bg_history = 100
                self.high_speed_bg_var_threshold = 4  # 🔧 降低以檢測小零件 (16→4)
                self.high_speed_min_area = 4          # 🔧 降低以檢測小零件 (50→4)
                self.high_speed_binary_threshold = 3  # 🔧 低二值化閾值
                logging.info(f"🚀 啟用280fps高速模式 (小零件優化)")
            else:
                # 206fps模式 - 適度簡化但保持小零件檢測
                self.high_speed_bg_history = 150
                self.high_speed_bg_var_threshold = 5  # 🔧 降低以檢測小零件 (14→5)
                self.high_speed_min_area = 5          # 🔧 降低以檢測小零件 (40→5)
                self.high_speed_binary_threshold = 4  # 🔧 適中二值化閾值
                logging.info(f"🚀 啟用206fps模式 (小零件優化)")
            
            # 🔧 重置背景減除器以應用新參數
            self._reset_background_subtractor()
            
            # 🔧 禁用所有調試功能以提升性能
            self.debug_save_enabled = False
            self.composite_debug_enabled = False
            
            logging.info(f"🚀 超高速檢測模式已啟用 - 目標: {target_fps}fps")
        else:
            logging.info("🔧 超高速檢測模式已禁用，恢復標準模式")
    
    def _reset_background_subtractor(self):
        """重置背景減除器 - 支援高速模式"""
        if self.ultra_high_speed_mode:
            # 🚀 高速模式參數
            history = self.high_speed_bg_history
            var_threshold = self.high_speed_bg_var_threshold
            logging.debug(f"🚀 高速模式背景減除器: history={history}, threshold={var_threshold}")
        else:
            # 🎯 標準模式參數
            history = self.bg_history
            var_threshold = self.bg_var_threshold
            logging.debug(f"🎯 標準模式背景減除器: history={history}, threshold={var_threshold}")
        
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=self.detect_shadows
        )
        # 🎯 設置極低學習率防止小零件被納入背景模型
        if hasattr(self, 'bg_learning_rate'):
            self.current_learning_rate = self.bg_learning_rate
        else:
            self.current_learning_rate = 0.001
        logging.debug("背景減除器已重置")
    
    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """基於背景減除的影像預處理 - 支援ROI區域檢測和高速模式"""
        if frame is None:
            return None
        
        try:
            # 🚀🚀 強化幀計數和跳幀檢測
            self.total_processed_frames += 1
            
            # 🔍 檢測跳幀情況 - 記錄處理的每一幀
            if hasattr(self, 'last_processed_frame'):
                frame_gap = self.total_processed_frames - self.last_processed_frame
                if frame_gap > 1:
                    logging.warning(f"⚠️ 檢測到跳幀: 從{self.last_processed_frame}跳到{self.total_processed_frames}, 跳過{frame_gap-1}幀")
            self.last_processed_frame = self.total_processed_frames
            
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
            
            # 🚀 高速模式：大幅簡化處理流程
            if self.ultra_high_speed_mode:
                return self._ultra_high_speed_processing(process_region)
            
            # 🎯 標準模式：完整處理流程
            # 1. 背景減除獲得前景遮罩 - 使用極低學習率
            fg_mask = self.bg_subtractor.apply(process_region, learningRate=self.current_learning_rate)
            
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
            
            # 🚀 簡化檢測策略 - 主要依賴背景減除結果
            # 背景減除已經有很好的檢測效果，避免過度處理
            
            # 5. 最小化處理 - 直接使用前景遮罩
            binary_thresh = self.high_speed_binary_threshold if self.ultra_high_speed_mode else self.binary_threshold
            
            # 6. 🚀 主要依賴前景遮罩 - 最小化干擾
            combined = fg_cleaned.copy()  # 直接使用清理後的前景遮罩
            
            # 7. 🔧 極度簡化形態學處理 - 最大化保留小零件
            # 使用最小化的形態學操作，避免過度過濾
            
            # 第一階段：最小化開運算僅去除1像素雜訊
            if self.opening_kernel_size == (1, 1):
                # 如果是1x1核，完全跳過開運算
                opened_stage1 = combined.copy()
            else:
                opening_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.opening_kernel_size)
                opened_stage1 = cv2.morphologyEx(combined, cv2.MORPH_OPEN, opening_kernel, iterations=self.opening_iterations)
            
            # 跳過第二階段開運算以保留更多小零件
            
            # 最小化膨脹 - 只連接相近像素
            if self.dilate_kernel_size != (1, 1) and self.dilate_iterations > 0:
                dilate_kernel = np.ones(self.dilate_kernel_size, np.uint8)
                dilated = cv2.dilate(opened_stage1, dilate_kernel, iterations=self.dilate_iterations)
            else:
                dilated = opened_stage1.copy()
            
            # 最小化閉合運算
            if self.close_kernel_size != (1, 1):
                close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, self.close_kernel_size)
                processed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, close_kernel, iterations=1)
            else:
                processed = dilated.copy()
            
            # 📸 強制創建調試數據以便分析
            if self.debug_save_enabled:
                self._temp_debug_data = {
                    'frame': frame.copy(),
                    'process_region': process_region.copy(),
                    'fg_mask': fg_mask.copy(),
                    'fg_cleaned': fg_cleaned.copy(),
                    'processed': processed.copy()
                }
            else:
                self._temp_debug_data = None
            
            # 🔧 檢查手動觸發文件
            self._check_manual_trigger_file()
            
            return processed
            
        except Exception as e:
            logging.error(f"背景減除預處理錯誤: {str(e)}")
            return None
    
    def _ultra_high_speed_processing(self, process_region: np.ndarray) -> Optional[np.ndarray]:
        """🚀 超高速處理模式 - 專為206-376fps設計"""
        try:
            # 🚀 步驟1: 極簡背景減除 - 高速模式也使用學習率控制
            fg_mask = self.bg_subtractor.apply(process_region, learningRate=self.current_learning_rate)
            
            # 🚀 步驟2: 單一輕量級形態學處理 (去除最小雜訊)
            kernel = np.ones((3, 3), np.uint8)
            processed = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)
            
            # 🚀 步驟3: 簡單膨脹連接相近區域 (最少處理)
            processed = cv2.dilate(processed, kernel, iterations=1)
            
            # 🚀 完全跳過所有其他處理：
            # - 無高斯模糊
            # - 無Canny邊緣檢測
            # - 無多階段形態學處理
            # - 無調試圖片保存
            # - 最少的logging
            
            return processed
            
        except Exception as e:
            # 🚀 高速模式下最簡化的錯誤處理
            logging.error(f"高速處理錯誤: {str(e)}")
            return None
    
    def detect_objects(self, processed_frame: np.ndarray, min_area: int = None, max_area: int = None) -> List[Tuple]:
        """基於連通組件的物件檢測 - 支援穿越計數和高速模式"""
        if processed_frame is None:
            return []
        
        try:
            # 🚀 高速模式：簡化參數選擇
            if self.ultra_high_speed_mode:
                # 使用高速模式的面積參數，忽略外部參數以確保一致性
                min_a = self.high_speed_min_area
                max_a = self.high_speed_max_area
            else:
                # 🎯 標準模式：強制使用極小零件檢測參數，避免被外部覆蓋
                # 只有當外部參數更小時才採用，確保捕獲極小零件
                min_a = min(min_area if min_area is not None else float('inf'), self.min_area)
                max_a = max(max_area if max_area is not None else 0, self.max_area)
            
            # 連通組件標記 (Connected Component Labeling)
            # 參考 partsCounts_v1.py 的實現
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                processed_frame, connectivity=self.connectivity
            )
            
            current_objects = []
            
            # 🚀 高速模式：減少調試訊息頻率
            debug_interval = 100 if self.ultra_high_speed_mode else 20
            
            # 🔍 調試：強制記錄總組件數和面積信息
            logging.info(f"🔍 總連通組件數: {num_labels-1}, 面積範圍: {min_a}-{max_a}")
            
            # 🔍 記錄所有組件面積
            if num_labels > 1:
                all_areas = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
                logging.info(f"🔍 所有組件面積: {sorted(all_areas)}")
            
            # 遍歷所有連通組件 (跳過背景，從1開始)
            for i in range(1, num_labels):
                area = stats[i, cv2.CC_STAT_AREA]
                
                # 🔍 調試：記錄面積過濾 (詳細調試)
                area_valid = area >= min_a  # 改為只檢查下限，不限制上限
                if i <= 5:  # 只記錄前5個組件
                    logging.info(f"🔍 組件{i}: 面積={area}, 最小面積={min_a}, 通過面積篩選={area_valid}")
                
                # 面積篩選 - 完全移除上限限制，只檢查下限
                if area >= min_a:
                    # 提取邊界框信息 (ROI座標)
                    x = stats[i, cv2.CC_STAT_LEFT]
                    y = stats[i, cv2.CC_STAT_TOP]
                    w = stats[i, cv2.CC_STAT_WIDTH]
                    h = stats[i, cv2.CC_STAT_HEIGHT]
                    
                    # 🚀 高速模式：跳過形狀過濾以提升性能
                    if self.ultra_high_speed_mode:
                        # 高速模式：只要通過面積篩選就接受，跳過所有形狀計算
                        shape_valid = True
                    else:
                        # 🔧 標準模式：完整形狀過濾 - 減少雜訊誤判
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
                        
                        # 🔍 極度寬鬆的形狀過濾 - 優先捕獲小零件
                        shape_valid = (
                            aspect_ratio > 0.001 and              # 極度寬鬆的長寬比 (0.005→0.001)
                            extent > 0.001 and                    # 極度寬鬆的填充比例 (0.005→0.001)
                            solidity <= self.max_solidity and     # 5.0
                            area >= 2                             # 極度降低面積要求 (5→2)
                        )
                        
                        # 🔍 詳細調試信息：記錄所有形狀分析結果
                        logging.info(f"🔍 組件{i} 形狀分析: 面積={area}, 長寬比={aspect_ratio:.4f}, 填充比例={extent:.4f}, 結實性={solidity:.3f}")
                        
                        if not shape_valid:
                            reasons = []
                            if aspect_ratio <= self.min_aspect_ratio:
                                reasons.append(f"長寬比太小({aspect_ratio:.4f} <= {self.min_aspect_ratio})")
                            if extent <= self.min_extent:
                                reasons.append(f"填充比例太小({extent:.4f} <= {self.min_extent})")
                            if solidity > self.max_solidity:
                                reasons.append(f"結實性太大({solidity:.3f} > {self.max_solidity})")
                            
                            logging.info(f"🚫 組件{i}被形狀過濾: 面積={area}, 原因={'; '.join(reasons)}")
                        
                        # 🔍 記錄通過檢測的物件
                        if shape_valid:
                            logging.info(f"✅ 組件{i}通過檢測: 面積={area}, 長寬比={aspect_ratio:.3f}, 位置=({x},{y})")
                    
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
                # 🚀 高速模式：簡化追蹤或完全跳過
                if self.ultra_high_speed_mode:
                    # 高速模式選項1：簡化計數 (直接使用物件數量)
                    self.crossing_counter += len(current_objects)
                    # 跳過複雜的追蹤邏輯以提升性能
                else:
                    # 🔍 標準模式：完整追蹤邏輯
                    # 調試：記錄追蹤狀態 (每20幀記錄一次)
                    if self.current_frame_count % 20 == 0:
                        logging.debug(f"🔍 開始追蹤: 檢測物件數={len(current_objects)}, 啟用計數={self.enable_crossing_count}")
                    self._update_object_tracking(current_objects)
            
            # 💾 保存檢測結果供調試使用
            self.last_detected_objects = current_objects.copy()
            
            # 📸 保存調試圖片的條件 - 只在視頻回放模式下啟用
            # 🚀 高速模式：完全禁用調試圖片保存
            # 🔍 強制保存所有幀以便分析 - 暫時移除條件限制
            should_save = (
                not self.ultra_high_speed_mode and  # 高速模式下強制禁用
                self._temp_debug_data is not None and 
                self.debug_frame_counter < self.max_debug_frames and
                self.debug_save_enabled and
                self.composite_debug_enabled
                # 暫時移除所有條件限制，保存每一幀
            )
            
            # 🎯 在剛進入中間段保存窗口時記錄日誌
            if self.total_video_frames is not None:
                start_frame = int(self.total_video_frames * self.skip_start_ratio)
                if (self.total_processed_frames == start_frame + 1 and self.debug_save_enabled):
                    end_frame = int(self.total_video_frames * (self.skip_start_ratio + self.save_middle_ratio))
                    logging.info(f"📸 開始保存影片中間段調試圖片")
                    logging.info(f"   保存範圍: 第{start_frame}幀 - 第{end_frame}幀")
                    logging.info(f"   預計保存約 {end_frame - start_frame} 幀的數據")
            
            # 🔍 強制更新調試幀計數器確保連續性
            self.debug_frame_counter += 1
            
            if should_save:
                save_reason = f"第{self.debug_frame_counter}幀 (檢測到 {len(current_objects)} 個物件)"
                
                # 🖼️ 使用新的合成調試圖片保存方法
                self._save_composite_debug_image(
                    self._temp_debug_data['frame'],           # 原始幀
                    self._temp_debug_data['process_region'],  # ROI區域
                    self._temp_debug_data['fg_mask'],         # 前景遮罩
                    self._temp_debug_data['fg_cleaned'],      # 合併檢測結果
                    self._temp_debug_data['processed'],       # 最終處理結果
                    current_objects                           # 檢測到的物件
                )
                
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
            
            # 🔍 調試：強制記錄每幀處理結果以分析問題
            logging.info(f"🎯 幀{self.total_processed_frames}: 組件{num_labels-1}→物件{len(current_objects)}, 調試幀號{self.debug_frame_counter}")
            
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
                    
                    # 🎯 為小零件降低計數要求：提高檢測敏感度
                    valid_crossing = (
                        y_travel >= 3 and           # 🔧 降低移動要求提高檢測率 (5→3像素)
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
        
        # 🎯 如果設定了自定義起始幀，記錄相關信息
        if self.custom_start_frame is not None:
            custom_time = self.custom_start_frame / fps
            logging.info(f"📸 自定義起始保存幀: {self.custom_start_frame} (時間: {custom_time:.1f}秒)")
    
    def _is_in_save_window(self) -> bool:
        """檢查當前是否在保存窗口內（影片中間段或自定義起始幀）"""
        # 🎯 優先使用自定義起始幀
        if self.custom_start_frame is not None:
            return self.total_processed_frames >= self.custom_start_frame
        
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
                
                # 🔧 確保圖像是三通道的
                if len(img.shape) == 2:  # 單通道圖像
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                elif len(img.shape) == 3 and img.shape[2] == 1:  # 單通道但有第三維
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                elif len(img.shape) == 3 and img.shape[2] == 4:  # RGBA圖像
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                
                # 計算縮放比例，保持圖片比例
                scale_h = target_h / h
                scale_w = target_w / w
                scale = min(scale_h, scale_w)  # 使用較小的縮放比例保持比例
                
                new_h = int(h * scale)
                new_w = int(w * scale)
                
                # 縮放圖片
                resized = cv2.resize(img, (new_w, new_h))
                
                # 🔧 再次確保縮放後的圖像是三通道的
                if len(resized.shape) == 2:
                    resized = cv2.cvtColor(resized, cv2.COLOR_GRAY2BGR)
                
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
            
            # 🏷️ 添加底部參數信息 - 詳細配置
            info_height = 160  # 增加高度以容納更多參數信息
            info_panel = np.zeros((info_height, composite_img.shape[1], 3), dtype=np.uint8)
            
            # 詳細參數文字信息
            params_text = [
                f"Frame: {self.debug_frame_counter:04d} | Count: {self.crossing_counter} | Objects: {len(detected_objects)} | Total Processed: {self.total_processed_frames}",
                f"ROI: {self.roi_height}px @ {self.roi_position_ratio:.2f} | MinArea: {self.high_speed_min_area if self.ultra_high_speed_mode else self.min_area} | MaxArea: {self.high_speed_max_area if self.ultra_high_speed_mode else self.max_area}",
                f"BG Threshold: {self.high_speed_bg_var_threshold if self.ultra_high_speed_mode else self.bg_var_threshold} | Binary: {self.high_speed_binary_threshold if self.ultra_high_speed_mode else self.binary_threshold} | Canny: {self.canny_low_threshold}-{self.canny_high_threshold}",
                f"Shape Filter - Aspect: >{getattr(self, 'min_aspect_ratio', 0.01):.2f} | Extent: >{getattr(self, 'min_extent', 0.02):.2f} | Solidity: >{getattr(self, 'min_solidity', 0.01):.2f}",
                f"Morph - Opening: {getattr(self, 'opening_kernel_size', (2, 2))} x{getattr(self, 'opening_iterations', 1)} | Closing: {getattr(self, 'closing_kernel_size', (3, 3))} x{getattr(self, 'closing_iterations', 1)}",
                f"Time: {datetime.fromtimestamp(timestamp/1000).strftime('%H:%M:%S.%f')[:-3]} | Gaussian Blur: {self.gaussian_blur_kernel}"
            ]
            
            # 在信息面板上添加文字
            for i, text in enumerate(params_text):
                y_pos = 20 + i * 22  # 調整行間距以適應更多參數
                cv2.putText(info_panel, text, (10, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)  # 稍小字體以容納更多信息
            
            # 合併信息面板
            final_composite = np.vstack([composite_img, info_panel])
            
            # 💾 保存合成圖片 - 強化錯誤處理和格式檢查
            save_path = f"{self.current_session_dir}/composite_debug_{frame_id}.jpg"
            try:
                # 檢查圖片數據完整性
                if final_composite is None or final_composite.size == 0:
                    logging.error(f"🚫 合成圖片數據無效")
                    return
                
                # 確保目錄存在
                import os
                os.makedirs(self.current_session_dir, exist_ok=True)
                
                # 嘗試保存為JPG
                success = cv2.imwrite(save_path, final_composite, [cv2.IMWRITE_JPEG_QUALITY, 95])
                if not success:
                    # 嘗試保存為PNG
                    png_path = save_path.replace('.jpg', '.png')
                    success = cv2.imwrite(png_path, final_composite)
                    if success:
                        logging.info(f"✅ 保存為PNG: {png_path}")
                    else:
                        logging.error(f"🚫 JPG和PNG格式都保存失敗: {save_path}")
                else:
                    logging.debug(f"✅ JPG保存成功: {save_path}")
                    
            except Exception as e:
                logging.error(f"🚫 調試圖片保存異常: {save_path}, 錯誤: {str(e)}")
                import traceback
                logging.error(f"詳細錯誤: {traceback.format_exc()}")
            
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
    
    def get_ultra_high_speed_status(self) -> Dict[str, Any]:
        """獲取超高速模式狀態"""
        return {
            'enabled': self.ultra_high_speed_mode,
            'target_fps': self.target_fps,
            'current_params': {
                'bg_history': self.high_speed_bg_history if self.ultra_high_speed_mode else self.bg_history,
                'bg_var_threshold': self.high_speed_bg_var_threshold if self.ultra_high_speed_mode else self.bg_var_threshold,
                'min_area': self.high_speed_min_area if self.ultra_high_speed_mode else self.min_area,
                'max_area': self.high_speed_max_area if self.ultra_high_speed_mode else self.max_area,
            },
            'optimizations': {
                'shape_filtering_disabled': self.ultra_high_speed_mode,
                'debug_disabled': self.ultra_high_speed_mode,
                'simplified_tracking': self.ultra_high_speed_mode,
                'reduced_logging': self.ultra_high_speed_mode
            }
        }

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
            'progress_percentage': self.debug_frame_counter,  # 顯示已保存數量，無限制模式
            'layout': '3x2 composite layout with annotations',
            'custom_start_frame': self.custom_start_frame
        }
    
    def set_custom_start_frame(self, start_frame: int):
        """設定自定義起始保存幀（例如2500）"""
        self.custom_start_frame = start_frame
        logging.info(f"🎯 已設定自定義起始保存幀: {start_frame}")
    
    def clear_custom_start_frame(self):
        """清除自定義起始幀，恢復使用比例計算"""
        self.custom_start_frame = None
        logging.info("🔄 已清除自定義起始幀，恢復使用比例計算")
    
    def cleanup_early_debug_images(self, before_frame: int = None):
        """清理指定幀數之前的調試圖片"""
        try:
            import os
            import glob
            from pathlib import Path
            
            if before_frame is None:
                before_frame = self.custom_start_frame or 2500
                
            if not os.path.exists(self.debug_save_dir):
                logging.info(f"📁 調試目錄不存在: {self.debug_save_dir}")
                return 0
            
            # 找到所有調試圖片
            pattern = os.path.join(self.debug_save_dir, "**", "composite_debug_*.jpg")
            all_debug_files = glob.glob(pattern, recursive=True)
            
            deleted_count = 0
            for file_path in all_debug_files:
                try:
                    # 從文件名提取幀號 (composite_debug_XXXX_timestamp.jpg)
                    filename = os.path.basename(file_path)
                    if filename.startswith("composite_debug_"):
                        # 提取幀號
                        frame_part = filename.split("_")[2]  # composite_debug_XXXX_timestamp.jpg
                        frame_number = int(frame_part)
                        
                        if frame_number < before_frame:
                            os.remove(file_path)
                            deleted_count += 1
                            
                except (ValueError, IndexError, OSError) as e:
                    logging.debug(f"跳過文件 {file_path}: {str(e)}")
                    continue
            
            logging.info(f"🗑️ 已清理 {deleted_count} 個第{before_frame}幀之前的調試圖片")
            return deleted_count
            
        except Exception as e:
            logging.error(f"清理早期調試圖片錯誤: {str(e)}")
            return 0

    @property
    def name(self) -> str:
        return "BackgroundSubtractionDetection"


