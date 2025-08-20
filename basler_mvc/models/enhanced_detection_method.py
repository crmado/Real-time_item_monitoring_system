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
        self.min_area = 2    # 🔧 進一步降低以捕獲極小零件 (3→2)  
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
        self.high_speed_min_area = 1          # 高速模式下最極限降低最小面積 (2→1)
        self.high_speed_max_area = 2000       # 高速模式下降低最大面積
        self.high_speed_binary_threshold = 3  # 高速模式下的二值化閾值
        
        # 🎯 極高敏感度邊緣檢測 - 專為小零件檢測優化
        self.gaussian_blur_kernel = (1, 1)  # 最小模糊保留最多細節 (3→1)
        self.canny_low_threshold = 3         # 🔧 極低闾值提高敏感度 (8→3)
        self.canny_high_threshold = 10       # 🔧 極低闾值提高敏感度 (25→10) 
        self.binary_threshold = 1            # 🔧 極低闾值提高敏感度 (8→1)
        
        # 🔍 分離優化的形態學處理 - 避免粘連同時保留小零件
        self.dilate_kernel_size = (1, 1)    # 🔧 最小核避免過度膨脹
        self.dilate_iterations = 0           # 🔧 禁用膨脹以保留小零件
        self.close_kernel_size = (1, 1)     # 🔧 禁用閉合避免零件粘連
        self.enable_watershed_separation = True  # 🆕 啟用分水嶺分離算法
        
        # 🎯 最小化雜訊過濾 - 最大化保留小零件
        self.opening_kernel_size = (1, 1)   # 🆕 最小開運算核 (2→1)
        self.opening_iterations = 0          # 🆕 禁用開運算以保留小零件 (1→0)
        
        # 連通組件參數
        self.connectivity = 4  # 4-連通或8-連通
        
        # 🎯 ROI 檢測區域參數 (根據影像分析結果優化)
        self.roi_enabled = True
        self.roi_height = 120  # 🔧 擴大ROI區域高度 (80→120以增加檢測面積)
        self.roi_position_ratio = 0.12  # 🔧 調整位置比例 (0.15→0.12，稍微上移以配合擴大高度)
        self.current_roi_y = 0  # 當前ROI的Y座標
        
        # 🎯 物件追蹤和計數參數 - 為小零件優化
        self.enable_crossing_count = True
        self.crossing_tolerance_x = 40  # 🔧 適度收緊x方向容差 (50→40，改善多物件分離)
        self.crossing_tolerance_y = 80  # 🔧 適度收緊y方向容差 (120→80，避免多物件沖突)
        
        # 🎯 提升追蹤穩定性 - 減少誤檢同時保持小零件檢測能力
        self.track_lifetime = 20  # 🔧 延長追蹤週期避免中斷 (8→20)
        self.min_track_frames = 4 # 🔧 提高穩定性要求，減少誤判 (2→4)
        self.crossing_threshold = 0.15   # 🔧 提高穿越閾值，減少誤檢 (0.05→0.15)
        self.confidence_threshold = 0.12  # 🔧 適度提高置信度要求 (0.05→0.12)
        
        # 🛡️ 增強防重複機制 - 避免追蹤中斷造成的重複計算
        self.counted_objects_history = []  # 已計數物件的歷史記錄 [(position, frame_number), ...]
        self.history_length = 30  # 🔧 增加歷史長度以增強重複檢測 (10→30)
        self.duplicate_distance_threshold = 15  # 🔧 收緊重複檢測距離減少誤檢 (25→15)
        self.temporal_tolerance = 5  # 🔧 降低時間容忍度提高檢測精度 (10→5)
        
        # 🧠 智能大小統計模型 - 用於判斷粘連情況
        self.component_sizes = []  # 記錄所有檢測到的零件大小
        self.size_statistics = {
            'mean_size': 0,
            'std_size': 0,
            'median_size': 0,
            'size_range': (0, 0),
            'sample_count': 0
        }
        self.min_samples_for_stats = 50  # 需要多少樣本才開始統計分析
        self.clustering_threshold_ratio = 2.5  # 超過平均大小多少倍視為可能的粘連
        
        # 🎯 空間網格追蹤系統 - 基於XY位置的精確追蹤
        self.grid_cell_size = 30  # 網格單元大小 (pixels)
        self.position_based_tracking = True  # 啟用位置基礎追蹤
        self.spatial_grid = {}  # 空間網格：{(grid_x, grid_y): track_id}
        
        # 🧠 推斷式追蹤系統 - 處理檢測中斷
        self.enable_predictive_tracking = True  # 啟用推斷追蹤
        self.prediction_tolerance = 15  # 推斷位置的容忍範圍
        self.max_prediction_frames = 5  # 最大連續推斷幀數
        
        # 追蹤狀態
        self.object_tracks = {}
        self.lost_tracks = {}  # 🆕 失去的追蹤（暫時消失但可能恢復的物件）
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
            
            # 🔧 方法1: 增強前景遮罩濾波 - 減少噪點干擾同時保留小零件
            # Step 1: 中值濾波去除椒鹽噪點
            fg_median = cv2.medianBlur(fg_mask, 5)
            
            # Step 2: 增強形態學開運算去除獨立噪點
            enhanced_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))  # 從(2,2)增加到(5,5)
            fg_step1 = cv2.morphologyEx(fg_median, cv2.MORPH_OPEN, enhanced_kernel, iterations=1)
            
            # Step 3: 閉運算填補物件內部空洞
            close_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            fg_step2 = cv2.morphologyEx(fg_step1, cv2.MORPH_CLOSE, close_kernel, iterations=1)
            
            # Step 4: 最終微調開運算，移除剩餘小噪點但保留真實小零件
            final_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            fg_cleaned = cv2.morphologyEx(fg_step2, cv2.MORPH_OPEN, final_kernel, iterations=1)
            
            # 🔧 方法2: 多敏感度邊緣檢測
            # 使用兩種不同敏感度的邊緣檢測
            strong_edges = cv2.Canny(blurred, self.canny_low_threshold, self.canny_high_threshold)
            sensitive_edges = cv2.Canny(blurred, self.canny_low_threshold//2, self.canny_high_threshold//2)
            
            # 🔧 方法3: 自適應閾值檢測 - 補強小零件檢測
            gray_roi = cv2.cvtColor(process_region, cv2.COLOR_BGR2GRAY) if len(process_region.shape) == 3 else process_region
            adaptive_thresh = cv2.adaptiveThreshold(gray_roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # 🚀 智能化檢測策略 - 前景遮罩 + 輕微邊緣增強
            # 背景減除作為主要檢測，邊緣檢測作為補強
            
            # 5. 輕微邊緣增強處理
            binary_thresh = self.high_speed_binary_threshold if self.ultra_high_speed_mode else self.binary_threshold
            
            # 為前景遮罩中的小點進行多重增強
            # 方法A: 邊緣增強
            edge_enhanced = cv2.bitwise_and(sensitive_edges, sensitive_edges, mask=fg_cleaned)
            _, edge_thresh = cv2.threshold(edge_enhanced, 1, 255, cv2.THRESH_BINARY)
            
            # 方法B: 自適應閾值增強
            adaptive_enhanced = cv2.bitwise_and(adaptive_thresh, adaptive_thresh, mask=fg_cleaned)
            _, adaptive_thresh_clean = cv2.threshold(adaptive_enhanced, 127, 255, cv2.THRESH_BINARY)
            
            # 6. 🚀 三重聯合檢測 - 前景遮罩 + 邊緣增強 + 自適應閾值
            temp_combined = cv2.bitwise_or(fg_cleaned, edge_thresh)
            combined = cv2.bitwise_or(temp_combined, adaptive_thresh_clean)
            
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
                    'fg_cleaned': combined.copy(),  # 使用增強後的combined結果
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
            
            # 🔧 小零件專用增強預處理
            enhanced_frame = processed_frame.copy()
            
            # 對於極小零件，進行輕微膨脹使其更容易被檢測
            if not self.ultra_high_speed_mode:
                # 使用極小的膨脹核來輕微增強小零件
                tiny_kernel = np.ones((2, 2), np.uint8)
                enhanced_frame = cv2.dilate(enhanced_frame, tiny_kernel, iterations=1)
            
            # 連通組件標記 (Connected Component Labeling)
            # 參考 partsCounts_v1.py 的實現
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                enhanced_frame, connectivity=self.connectivity
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
                
                # 🔧 增強面積篩選 - 加入物件大小驗證減少噪點誤檢
                area_valid = self._validate_object_size(area, min_a, max_a)
                if area_valid:
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
                        
                        # 🧠 更新大小統計模型
                        self._update_size_statistics(area)
                        
                        # 🔧 智能粘連檢測與分離
                        should_separate = False
                        separation_reason = ""
                        
                        # 方法1: 基於統計大小的智能判斷
                        if self._is_clustered_component(area):
                            should_separate = True
                            estimated_count = self._estimate_component_count(area)
                            separation_reason = f"統計分析(估算{estimated_count}個零件)"
                            
                        # 方法2: 傳統方法作為後備 (面積超過合理閾值)
                        elif (self.enable_watershed_separation and 
                              self.size_statistics['sample_count'] < self.min_samples_for_stats and 
                              area > 500):  # 🔧 調整為更合理的閾值，只在統計不足時使用
                            should_separate = True
                            separation_reason = f"統計不足時的保守分離(面積>{500})"
                        
                        if should_separate:
                            logging.info(f"🔧 嘗試分離粘連零件: 面積={area:.0f}, 原因={separation_reason}")
                            separated_objects = self._separate_clustered_components(
                                enhanced_frame, labels, i, x, y, w, h, area
                            )
                            
                            if separated_objects:  # 如果成功分離
                                logging.info(f"✅ 成功分離出{len(separated_objects)}個零件")
                                for sep_obj in separated_objects:
                                    sep_x, sep_y, sep_w, sep_h, sep_area, sep_radius = sep_obj
                                    # 轉換為全圖座標
                                    global_sep_y = sep_y + self.current_roi_y
                                    global_sep_centroid = (sep_x + sep_w//2, global_sep_y + sep_h//2)
                                    current_objects.append((sep_x, global_sep_y, sep_w, sep_h, global_sep_centroid, sep_area, sep_radius))
                                    # 為分離出的零件也更新統計
                                    self._update_size_statistics(sep_area)
                                continue  # 跳過原始大物件，使用分離後的結果
                            else:
                                logging.warning(f"❌ 分離失敗，保留原始物件: 面積={area:.0f}")
                        
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
            
            # 🔧 改進的追蹤匹配邏輯：實現一對一匹配，避免多物件沖突
            new_tracks = {}
            used_track_ids = set()  # 記錄已經匹配的追蹤ID
            
            # 🎯 清理空間網格並重建 (每幀重新計算網格佔用)
            self.spatial_grid.clear()
            
            # 🧠 推斷式追蹤：為可能失去檢測的物件生成虛擬檢測
            virtual_objects = []
            if self.enable_predictive_tracking:
                # 當檢測較少或有失去的追蹤時，嘗試推斷
                virtual_objects = self._generate_predictive_objects()
                if virtual_objects:
                    logging.debug(f"🔮 生成{len(virtual_objects)}個推斷物件（檢測到{len(current_objects)}個真實物件）")
            
            # 合併實際檢測和推斷物件
            all_objects = current_objects + virtual_objects
            
            # 🎯 第一階段：為每個檢測物件找到最佳匹配
            object_track_matches = []  # [(object_index, track_id, distance, is_virtual), ...]
            
            for obj_idx, obj in enumerate(all_objects):
                x, y, w, h, centroid, area, radius = obj
                cx, cy = centroid
                is_virtual = obj_idx >= len(current_objects)  # 判斷是否為虛擬物件
                
                best_match_id = None
                best_match_distance = float('inf')
                
                # 與現有追蹤進行匹配 (找最佳匹配)
                for track_id, track in self.object_tracks.items():
                    if track_id in used_track_ids:  # 跳過已經被匹配的追蹤
                        continue
                        
                    # 計算距離
                    distance = np.sqrt((cx - track['x'])**2 + (cy - track['y'])**2)
                    
                    # 🧠 對虛擬物件使用更寬鬆的容差
                    tolerance_x = self.crossing_tolerance_x * (2 if is_virtual else 1)
                    tolerance_y = self.crossing_tolerance_y * (2 if is_virtual else 1)
                    
                    # 檢查是否在容差範圍內
                    if (abs(cx - track['x']) < tolerance_x and 
                        abs(cy - track['y']) < tolerance_y and
                        distance < best_match_distance):
                        
                        best_match_distance = distance
                        best_match_id = track_id
                
                # 記錄匹配結果
                if best_match_id is not None:
                    object_track_matches.append((obj_idx, best_match_id, best_match_distance, is_virtual))
            
            # 🎯 第二階段：按距離排序，確保最佳匹配優先
            object_track_matches.sort(key=lambda x: x[2])  # 按距離排序
            
            # 🎯 第三階段：執行一對一匹配（含網格驗證）
            # grid_conflicted_objects = set()  # 🔧 記錄因網格衝突被跳過的物件
            
            for match_data in object_track_matches:
                if len(match_data) == 4:
                    obj_idx, track_id, distance, is_virtual = match_data
                else:
                    obj_idx, track_id, distance = match_data
                    is_virtual = False
                    
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
                            # 🧠 為推斷式追蹤添加尺寸信息
                            'avg_w': int((old_track.get('avg_w', w) + w) / 2),
                            'avg_h': int((old_track.get('avg_h', h) + h) / 2),
                            'avg_area': (old_track.get('avg_area', area) + area) / 2
                        }
                        used_track_ids.add(track_id)
                        
                        # 佔用網格
                        if self.position_based_tracking:
                            self.spatial_grid[grid_pos] = track_id
                            
                        logging.debug(f"🔗 物件{obj_idx}匹配到追蹤{track_id}, 距離={distance:.1f}px, 網格={grid_pos}")
                    else:
                        # 有網格衝突，記錄並跳過，防止重複創建
                        conflicted_track = self.spatial_grid[grid_pos]
                        # grid_conflicted_objects.add(obj_idx)  # 🔧 記錄衝突物件
                        logging.warning(f"⚠️ 網格衝突: 物件{obj_idx}與追蹤{conflicted_track}在網格{grid_pos}衝突，跳過匹配")
            
            # 🎯 第四階段：為未匹配的物件（包括虛擬物件）創建新追蹤或嘗試恢復
            matched_objects = {match[0] for match in object_track_matches if match[1] in used_track_ids}
            
            for obj_idx, obj in enumerate(all_objects):
                if obj_idx not in matched_objects:
                    x, y, w, h, centroid, area, radius = obj
                    cx, cy = centroid
                    is_virtual = obj_idx >= len(current_objects)  # 判斷是否為虛擬物件
                    
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
                        
                        # 恢復條件：空間距離稍微寬鬆，時間間隔在容忍範圍內
                        recovery_tolerance_x = self.crossing_tolerance_x * 1.5
                        recovery_tolerance_y = self.crossing_tolerance_y * 1.5
                        
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
                            # 恢復追蹤到new_tracks
                            new_tracks[recovered_track_id] = {
                                'x': cx,
                                'y': cy,
                                'first_frame': recovered_track.get('first_frame', self.current_frame_count),
                                'last_frame': self.current_frame_count,
                                'positions': recovered_track.get('positions', []) + [(cx, cy)],
                                'counted': recovered_track.get('counted', False),
                                'in_roi_frames': recovered_track.get('in_roi_frames', 0) + 1,
                                'max_y': max(recovered_track.get('max_y', cy), cy),
                                'min_y': min(recovered_track.get('min_y', cy), cy),
                                'grid_position': recovery_grid_pos,
                                # 🧠 為推斷式追蹤添加尺寸信息
                                'avg_w': int((recovered_track.get('avg_w', w) + w) / 2),
                                'avg_h': int((recovered_track.get('avg_h', h) + h) / 2),
                                'avg_area': (recovered_track.get('avg_area', area) + area) / 2
                            }
                            
                            # 佔用網格
                            if self.position_based_tracking:
                                self.spatial_grid[recovery_grid_pos] = recovered_track_id
                        else:
                            # 恢復位置有網格衝突，放棄恢復
                            recovered_track_id = None
                            logging.warning(f"⚠️ 追蹤恢復失敗: 網格{recovery_grid_pos}已被佔用")
                        
                        # 從lost_tracks中移除已恢復的追蹤
                        del self.lost_tracks[recovered_track_id]
                        
                        logging.info(f"🔄 成功恢復追蹤{recovered_track_id}: 距離={best_recovery_distance:.1f}px, 時間間隔={self.current_frame_count - recovered_track['last_frame']}幀")
                    
                    if not recovered_track_id:
                        # 🧠 對於虛擬物件：優先恢復而非創建新追蹤
                        if is_virtual:
                            logging.debug(f"🔮 虛擬物件{obj_idx}未找到恢復目標，跳過創建新追蹤")
                            continue
                        
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
                                'grid_position': new_grid_pos,
                                # 🧠 為推斷式追蹤添加尺寸信息
                                'avg_w': w,
                                'avg_h': h,
                                'avg_area': area
                            }
                            
                            # 佔用網格
                            if self.position_based_tracking:
                                self.spatial_grid[new_grid_pos] = new_track_id
                                
                            logging.debug(f"🆕 物件{obj_idx}創建新追蹤{new_track_id}, 網格={new_grid_pos}")
                        else:
                            # 新位置有網格衝突，跳過創建
                            conflicted_track = self.spatial_grid[new_grid_pos]
                            logging.warning(f"⚠️ 新追蹤創建失敗: 物件{obj_idx}在網格{new_grid_pos}與追蹤{conflicted_track}衝突")
                    else:
                        logging.debug(f"🔄 物件{obj_idx}恢復追蹤{recovered_track_id}")
            
            # 🔍 調試：記錄軌跡狀態和網格衝突統計 (每20幀記錄一次)
            if self.current_frame_count % 20 == 0:
                logging.debug(f"🎯 軌跡狀態: 總軌跡數={len(new_tracks)}, 當前穿越計數={self.crossing_counter}")
            
            # 🎯 簡化高效穿越計數邏輯 - 提升檢測速度
            for track_id, track in new_tracks.items():
                if not track['counted'] and track['in_roi_frames'] >= self.min_track_frames:
                    # 簡化檢查：只要物件在ROI中出現就計數
                    y_travel = track['max_y'] - track['min_y']
                    
                    # 檢查是否為重複計數（簡化版）
                    is_duplicate = self._check_duplicate_detection_simple(track)
                    
                    # 🎯 提升追蹤穩定性：適度提高移動要求減少誤檢
                    valid_crossing = (
                        y_travel >= 8 and           # 🔧 提高移動要求減少誤檢 (3→8像素)
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
            
            # 🔧 改進的追蹤生命週期管理：移動失去的追蹤到lost_tracks
            current_time = self.current_frame_count
            
            # 將當前未匹配的追蹤移動到lost_tracks
            for track_id, track in self.object_tracks.items():
                if track_id not in new_tracks:
                    # 追蹤失去匹配，移動到lost_tracks
                    self.lost_tracks[track_id] = track
                    logging.debug(f"🔄 追蹤{track_id}失去匹配，移動到lost_tracks")
            
            # 清理過期的lost_tracks
            for track_id in list(self.lost_tracks.keys()):
                track = self.lost_tracks[track_id]
                if current_time - track['last_frame'] > self.temporal_tolerance:
                    del self.lost_tracks[track_id]
                    logging.debug(f"🗑️ 清理過期lost_track {track_id}")
            
            # 更新追蹤狀態
            self.object_tracks = new_tracks
            
        except Exception as e:
            logging.error(f"物件追蹤更新錯誤: {str(e)}")
    
    def _check_duplicate_detection_simple(self, track: Dict) -> bool:
        """🔧 增強版重複檢測 - 加入時間與空間雙重考量"""
        try:
            current_pos = (track['x'], track['y'])
            current_frame = self.current_frame_count
            
            # 🆕 檢查歷史記錄中的時空重複
            for hist_entry in self.counted_objects_history:
                if isinstance(hist_entry, tuple) and len(hist_entry) == 2:
                    # 新格式：(position, frame_number)
                    hist_pos, hist_frame = hist_entry
                    
                    # 🎯 時空距離檢測：同時考慮空間距離和時間間隔
                    spatial_distance = abs(current_pos[0] - hist_pos[0]) + abs(current_pos[1] - hist_pos[1])
                    temporal_distance = current_frame - hist_frame
                    
                    # 🛡️ 如果空間距離小且時間間隔在容忍範圍內，視為重複
                    if (spatial_distance < self.duplicate_distance_threshold and 
                        temporal_distance <= self.temporal_tolerance):
                        logging.debug(f"🚫 檢測到重複: 空間距離={spatial_distance}, 時間間隔={temporal_distance}幀")
                        return True
                        
                elif isinstance(hist_entry, tuple) and len(hist_entry) == 2 and isinstance(hist_entry[0], (int, float)):
                    # 舊格式：(x, y) - 向後相容
                    hist_pos = hist_entry
                    spatial_distance = abs(current_pos[0] - hist_pos[0]) + abs(current_pos[1] - hist_pos[1])
                    
                    if spatial_distance < self.duplicate_distance_threshold:
                        return True
            
            return False
            
        except Exception as e:
            logging.debug(f"重複檢測錯誤: {str(e)}")
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
                
            logging.debug(f"📝 添加到歷史: 位置={position}, 幀號={frame_number}")
                
        except Exception as e:
            logging.error(f"添加歷史記錄錯誤: {str(e)}")
    
    def get_crossing_count(self) -> int:
        """獲取穿越計數"""
        return self.crossing_counter
    
    def get_tracking_stats(self) -> Dict[str, Any]:
        """獲取追蹤統計信息 (用於調試)"""
        active_tracks = len(self.object_tracks)
        lost_tracks_count = len(self.lost_tracks)  # 🔧 新增失去追蹤統計
        counted_tracks = sum(1 for track in self.object_tracks.values() if track.get('counted', False))
        
        return {
            'crossing_count': self.crossing_counter,
            'active_tracks': active_tracks,
            'lost_tracks': lost_tracks_count,  # 🔧 新增lost_tracks統計
            'counted_tracks': counted_tracks,
            'frame_count': self.current_frame_count,
            'roi_height': self.roi_height,
            'roi_position': self.roi_position_ratio,
            'history_length': len(self.counted_objects_history),
            'accuracy_features': {
                'min_track_frames': self.min_track_frames,
                'confidence_threshold': self.confidence_threshold,
                'duplicate_prevention': True,
                'track_recovery_enabled': True,  # 🔧 新增追蹤恢復功能標記
                'temporal_tolerance': self.temporal_tolerance
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
        self.lost_tracks = {}  # 🔧 重置失去的追蹤
        self.spatial_grid = {}  # 🔧 重置空間網格
        self.current_frame_count = 0
        self.total_processed_frames = 0  # 🎯 重置總幀數計數器
        self.debug_frame_counter = 0     # 🎯 重置調試圖片計數器
        self.counted_objects_history = []  # 清理歷史記錄
        # 🧠 保留大小統計模型（不重置，繼續學習）
        logging.info("🔄 穿越計數、追蹤、失去追蹤、網格、歷史記錄和調試計數器已重置")
    
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
    
    def _validate_object_size(self, area: int, min_area: int, max_area: int) -> bool:
        """🔧 物件大小驗證 - 減少噪點誤檢同時保留真實小零件"""
        try:
            # 基本面積檢查
            if area < min_area:
                return False
                
            # 動態上限檢查：允許合理範圍內的大物件
            # 對於小零件系統，設定較為寬鬆但有界的上限
            reasonable_max_area = max_area if max_area and max_area > 0 else 500
            
            # 如果物件過大，可能是粘連或背景噪點
            if area > reasonable_max_area:
                logging.debug(f"🚫 物件面積過大: {area} > {reasonable_max_area}")
                return False
                
            # 過小物件可能是噪點
            if area < 10:  # 極小噪點過濾
                logging.debug(f"🚫 物件面積過小: {area} < 10")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"物件大小驗證錯誤: {str(e)}")
            return True  # 發生錯誤時預設接受，避免系統中斷
    
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

    def _separate_clustered_components(self, frame, labels, component_id, x, y, w, h, area):
        """
        分水嶺算法分離粘連的小零件
        
        Args:
            frame: 處理後的二值圖像
            labels: 連通組件標籤圖像
            component_id: 當前組件ID
            x, y, w, h: 組件的邊界框
            area: 組件面積
            
        Returns:
            List of separated objects: [(x, y, w, h, area, radius), ...]
        """
        try:
            # 提取當前組件的區域
            component_mask = (labels == component_id).astype(np.uint8) * 255
            
            # 提取組件區域
            roi = component_mask[y:y+h, x:x+w]
            if roi.size == 0:
                return []
            
            # 🔧 智能估算預期零件數量
            if self.size_statistics['sample_count'] >= self.min_samples_for_stats:
                # 使用統計模型估算
                expected_components = self._estimate_component_count(area)
            else:
                # 統計不足時的保守估算
                expected_components = max(2, min(4, int(area / 200)))  # 限制在2-4個之間
            
            # 🔧 改進的距離變換和種子點檢測
            dist_transform = cv2.distanceTransform(roi, cv2.DIST_L2, 3)  # 使用較小的mask
            
            # 🔧 自適應峰值檢測
            # 對於小零件，使用較小的形態學核心
            kernel_size = 2 if area < 400 else 3
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            local_maxima = cv2.morphologyEx(dist_transform, cv2.MORPH_OPEN, kernel)
            
            # 🔧 自適應閾值設定
            # 對於小零件使用較低的閾值
            threshold_ratio = 0.4 if area < 400 else 0.3
            sure_fg = np.uint8(local_maxima > threshold_ratio * dist_transform.max())
            
            # 🔧 進一步過濾：移除過小的種子點
            if area < 400:
                # 對小零件，確保種子點有最小大小
                seed_kernel = np.ones((2, 2), np.uint8)
                sure_fg = cv2.morphologyEx(sure_fg, cv2.MORPH_OPEN, seed_kernel)
            
            # 標記種子點
            _, markers = cv2.connectedComponents(sure_fg)
            
            # 🔧 改進的種子點驗證邏輯
            num_seeds = markers.max()
            seeds_reasonable = (num_seeds >= 2 and num_seeds <= expected_components + 1)
            
            logging.debug(f"🔧 分離分析: 面積={area}, 種子點={num_seeds}, 期望組件={expected_components}, 合理={seeds_reasonable}")
            
            if seeds_reasonable:
                # 為分水嶺算法準備圖像
                if len(roi.shape) == 2:
                    roi_3ch = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
                else:
                    roi_3ch = roi
                
                # 執行分水嶺算法
                markers = cv2.watershed(roi_3ch, markers)
                
                # 提取分離後的組件
                separated_objects = []
                for label_id in range(2, markers.max() + 1):  # 跳過背景(0)和邊界(-1,1)
                    mask = (markers == label_id).astype(np.uint8)
                    
                    # 找到輪廓
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if contours:
                        cnt = max(contours, key=cv2.contourArea)
                        sep_area = cv2.contourArea(cnt)
                        
                        # 🔧 改進的分離組件驗證
                        # 設定合理的最小面積（比檢測最小面積稍大）
                        min_separated_area = max(self.min_area, 20)
                        if sep_area >= min_separated_area:
                            sep_x, sep_y, sep_w, sep_h = cv2.boundingRect(cnt)
                            # 轉換回原圖坐標
                            sep_x += x
                            sep_y += y
                            sep_radius = np.sqrt(sep_area / np.pi)
                            
                            separated_objects.append((sep_x, sep_y, sep_w, sep_h, sep_area, sep_radius))
                
                # 🔧 改進的分離成功驗證
                total_separated_area = sum(obj[4] for obj in separated_objects)
                area_conservation = 0.7 <= (total_separated_area / area) <= 1.3  # 允許30%的面積變化
                
                success_criteria = (
                    len(separated_objects) >= 2 and 
                    len(separated_objects) <= expected_components and
                    area_conservation
                )
                
                if success_criteria:
                    logging.info(f"✅ 成功分離: 原面積={area} -> {len(separated_objects)}個組件")
                    logging.debug(f"   分離面積: {[f'{obj[4]:.0f}' for obj in separated_objects]}, 總面積比例={total_separated_area/area:.2f}")
                    return separated_objects
                else:
                    logging.debug(f"❌ 分離驗證失敗: 組件數={len(separated_objects)}, 面積比例={total_separated_area/area:.2f}")
            else:
                logging.debug(f"❌ 種子點不合理，跳過分離")
            
            # 分離失敗，返回空列表
            return []
            
        except Exception as e:
            logging.debug(f"分離算法錯誤: {str(e)}")
            return []

    def _get_grid_position(self, x: int, y: int) -> Tuple[int, int]:
        """將像素座標轉換為網格座標"""
        grid_x = x // self.grid_cell_size
        grid_y = y // self.grid_cell_size
        return (grid_x, grid_y)
    
    def _update_size_statistics(self, area: float):
        """更新零件大小統計模型"""
        self.component_sizes.append(area)
        
        # 保持合理的樣本數量（最多1000個樣本）
        if len(self.component_sizes) > 1000:
            self.component_sizes = self.component_sizes[-1000:]
        
        # 如果有足夠的樣本，計算統計數據
        if len(self.component_sizes) >= self.min_samples_for_stats:
            import numpy as np
            sizes = np.array(self.component_sizes)
            
            self.size_statistics.update({
                'mean_size': float(np.mean(sizes)),
                'std_size': float(np.std(sizes)),
                'median_size': float(np.median(sizes)),
                'size_range': (float(np.min(sizes)), float(np.max(sizes))),
                'sample_count': len(sizes)
            })
            
            logging.debug(f"📊 大小統計更新: 平均={self.size_statistics['mean_size']:.1f}, 標準差={self.size_statistics['std_size']:.1f}")
    
    def _is_clustered_component(self, area: float) -> bool:
        """判斷是否為粘連的零件（基於大小統計）"""
        if self.size_statistics['sample_count'] < self.min_samples_for_stats:
            return False  # 樣本不足，不進行判斷
            
        mean_size = self.size_statistics['mean_size']
        threshold = mean_size * self.clustering_threshold_ratio
        
        is_clustered = area > threshold
        if is_clustered:
            logging.info(f"🔗 檢測到可能的粘連零件: 面積={area:.0f} > 閾值={threshold:.0f} (平均大小={mean_size:.0f})")
        
        return is_clustered
    
    def _estimate_component_count(self, area: float) -> int:
        """根據面積估算粘連零件的數量"""
        if self.size_statistics['sample_count'] < self.min_samples_for_stats:
            return 1
            
        mean_size = self.size_statistics['mean_size']
        estimated_count = max(1, round(area / mean_size))
        
        logging.debug(f"📏 面積={area:.0f}, 平均大小={mean_size:.0f}, 估算數量={estimated_count}")
        return estimated_count
    
    def get_size_statistics(self) -> Dict[str, Any]:
        """獲取大小統計信息"""
        return {
            'statistics': self.size_statistics.copy(),
            'clustering_threshold_ratio': self.clustering_threshold_ratio,
            'grid_cell_size': self.grid_cell_size,
            'position_based_tracking': self.position_based_tracking
        }

    def _generate_predictive_objects(self) -> List[Tuple]:
        """🧠 推斷式追蹤：根據現有追蹤軌跡預測物件位置"""
        virtual_objects = []
        
        try:
            current_frame = self.current_frame_count
            
            # 分析活躍追蹤和最近失去的追蹤
            all_tracks = {**self.object_tracks, **self.lost_tracks}
            
            for track_id, track in all_tracks.items():
                # 檢查追蹤是否需要預測
                frames_since_last = current_frame - track['last_frame']
                
                if (1 <= frames_since_last <= self.max_prediction_frames and 
                    len(track.get('positions', [])) >= 2):
                    
                    # 🔮 基於歷史位置預測下一個位置
                    positions = track['positions'][-3:]  # 使用最近3個位置
                    
                    if len(positions) >= 2:
                        # 簡單線性預測
                        last_pos = positions[-1]
                        prev_pos = positions[-2]
                        
                        # 計算移動向量
                        dx = last_pos[0] - prev_pos[0]
                        dy = last_pos[1] - prev_pos[1]
                        
                        # 預測新位置
                        predicted_x = int(last_pos[0] + dx * frames_since_last)
                        predicted_y = int(last_pos[1] + dy * frames_since_last)
                        
                        # 檢查預測位置是否在合理範圍內
                        if (0 <= predicted_x < self.frame_width and 
                            0 <= predicted_y < self.frame_height):
                            
                            # 使用平均尺寸創建虛擬物件
                            avg_w = track.get('avg_w', 20)
                            avg_h = track.get('avg_h', 20) 
                            avg_area = track.get('avg_area', 300)
                            avg_radius = max(5, int(np.sqrt(avg_area / np.pi)))
                            
                            # 創建虛擬物件 (格式與真實檢測一致)
                            virtual_obj = (
                                max(0, predicted_x - avg_w//2),  # x
                                max(0, predicted_y - avg_h//2),  # y  
                                avg_w,                           # w
                                avg_h,                           # h
                                (predicted_x, predicted_y),     # centroid
                                avg_area,                        # area
                                avg_radius                       # radius
                            )
                            
                            virtual_objects.append(virtual_obj)
                            
                            logging.debug(f"🔮 生成虛擬物件 track_{track_id}: 位置({predicted_x},{predicted_y}), "
                                        f"移動向量({dx},{dy}), 預測幀數={frames_since_last}")
            
            if virtual_objects:
                logging.info(f"🧠 推斷式追蹤: 生成了 {len(virtual_objects)} 個虛擬物件用於追蹤連續性")
                
        except Exception as e:
            logging.error(f"生成預測物件錯誤: {str(e)}")
        
        return virtual_objects

    @property
    def name(self) -> str:
        return "BackgroundSubtractionDetection"


