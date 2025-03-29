"""
物体检测控制器
负责协调图像处理和物体检测的核心逻辑
"""

import logging
import cv2
import numpy as np
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from models.image_processor import ImageProcessor
import time
import threading


class DetectionController:
    """物体检测控制器类"""

    def __init__(self, camera_manager):
        """
        初始化检测控制器

        Args:
            camera_manager: 相机管理器实例
        """
        self.camera_manager = camera_manager
        
        # 初始化圖像處理器
        self.image_processor = ImageProcessor()
        
        # 状态标志
        self.is_detecting = False
        self.is_dragging_roi = False
        self.is_testing = False  # 添加测试模式标志
        
        # ROI设置 - 按照參考代碼設置默認ROI位置
        self.roi_y = None
        self.saved_roi_percentage = 0.2  # 默認在高度20%位置，與參考代碼一致
        self.roi_height = 16  # ROI 檢測區域高度，與參考代碼一致
        
        # 計數相關
        self.current_count = 0
        self.target_count = 1000
        self.buffer_point = 950
        
        # 物體追蹤相關 - 使用字典而非列表
        self.last_detected_objects = []
        self.tracked_objects = {}  # 使用字典形式儲存追蹤對象，格式 {id: {'x': x, 'y': y, 'count': count}}
        self.object_count = 0
        
        # 當前照片
        self.current_photo = None
        
        # 回调函数字典
        self.callbacks = {}
        
        # 檢測日誌
        self.detection_log_file = None
        self.detection_logger = None
        
        # 初始化 ROI 位置（確保有一個初始值）
        logging.info("初始化 ROI 位置")
        self._initialize_roi()
        
        # 新增計數物體ID集合，避免重複計數
        self.counted_ids = set()
        
    def _initialize_roi(self):
        """初始化 ROI 位置 - 按照參考代碼設為高度的20%"""
        try:
            # 如果相機已經打開並有幀，使用幀高度計算 ROI 位置
            if hasattr(self.camera_manager, 'current_frame') and self.camera_manager.current_frame is not None:
                height = self.camera_manager.current_frame.shape[0]
                # 設置ROI為高度的20%，與參考代碼一致
                self.saved_roi_percentage = 0.2
                self.roi_y = int(height * self.saved_roi_percentage)
                logging.info(f"根據當前幀初始化 ROI 位置: {self.roi_y}, 幀高度: {height}")
            else:
                # 預設值也設為一個合理的20%估計值
                self.saved_roi_percentage = 0.2
                self.roi_y = 120  # 假設高度為600的20%
                logging.info(f"設置默認 ROI 位置: {self.roi_y} (預設畫面高度20%)")
                
                # 在第一次處理幀時更新 ROI 位置
                self.roi_needs_update = True
        except Exception as e:
            logging.error(f"初始化 ROI 位置時出錯: {str(e)}")
            self.saved_roi_percentage = 0.2
            self.roi_y = 120  # 設置一個安全的默認值
            self.roi_needs_update = True
            
    def put_chinese_text(self, img, text, position, font_size=30, color=(0, 255, 0)):
        """
        簡化版本的文字繪製 - 不使用PIL庫來提高效率
        
        Args:
            img: OpenCV 圖像
            text: 要添加的文字
            position: 文字位置 (x, y)
            font_size: 字體大小
            color: 文字顏色 (B, G, R)
            
        Returns:
            添加文字後的圖像
        """
        # 直接使用OpenCV的putText繪製文字，避免轉換開銷
        font_scale = font_size / 30.0  # 根據字體大小計算縮放比例
        thickness = max(1, int(font_size / 15))  # 根據字體大小計算線條粗細
        
        # 避免修改原始圖像
        result = img.copy()
        cv2.putText(
            result, 
            text, 
            position, 
            cv2.FONT_HERSHEY_SIMPLEX, 
            font_scale, 
            color, 
            thickness
        )
        
        return result
            
    def start_detection(self):
        """啟動物體檢測"""
        logging.info("[資訊] 啟動物體檢測")
        print("啟動物體檢測")
        self.is_detecting = True
        
        # 重置計數
        self.current_count = 0
        self.object_count = 0
        self.tracked_objects = {}
        
        # 創建檢測日誌文件
        self._setup_detection_log()
        
        # 觸發監控開始回調
        if 'monitoring_started' in self.callbacks and self.callbacks['monitoring_started']:
            self.callbacks['monitoring_started']()
            
        logging.info("[資訊] 物體檢測已啟動")
        print("物體檢測已啟動")
        
    def _setup_detection_log(self):
        """設置檢測日誌"""
        try:
            # 確保日誌目錄存在
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
                
            # 創建檢測日誌文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.detection_log_file = os.path.join(logs_dir, f"detection_{timestamp}.log")
            
            # 配置檢測日誌
            detection_logger = logging.getLogger('detection_logger')
            detection_logger.setLevel(logging.INFO)
            
            # 清除現有處理器
            for handler in detection_logger.handlers[:]:
                detection_logger.removeHandler(handler)
                
            # 添加文件處理器
            file_handler = logging.FileHandler(self.detection_log_file, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s %(levelname_cn)s %(message)s', 
                                         datefmt='%Y-%m-%d %H:%M:%S')
            file_handler.setFormatter(formatter)
            detection_logger.addHandler(file_handler)
            
            # 保存日誌器引用
            self.detection_logger = detection_logger
            
            # 記錄初始信息
            self._log_detection("[資訊]", "檢測日誌已創建")
            self._log_detection("[資訊]", f"ROI 位置百分比: {self.saved_roi_percentage}")
            self._log_detection("[資訊]", f"目標計數: {self.target_count}")
            
            logging.info(f"[資訊] 檢測日誌已創建: {self.detection_log_file}")
            
        except Exception as e:
            logging.error(f"[錯誤] 創建檢測日誌失敗: {str(e)}")
            
    def _log_detection(self, level_cn, message):
        """記錄檢測日誌
        
        Args:
            level_cn: 中文日誌級別
            message: 日誌消息
        """
        if self.detection_logger:
            extra = {'levelname_cn': level_cn}
            if level_cn == "[資訊]":
                self.detection_logger.info(message, extra=extra)
            elif level_cn == "[警告]":
                self.detection_logger.warning(message, extra=extra)
            elif level_cn == "[錯誤]":
                self.detection_logger.error(message, extra=extra)
            elif level_cn == "[嚴重]":
                self.detection_logger.critical(message, extra=extra)
        
    def stop_detection(self):
        """停止物體檢測"""
        logging.info("[資訊] 停止物體檢測")
        print("停止物體檢測")
        self.is_detecting = False
        
        # 記錄檢測結束信息
        if self.detection_logger:
            self._log_detection("[資訊]", f"檢測結束，總計數: {self.current_count}")
            self._log_detection("[資訊]", f"檢測到的物體數量: {self.object_count}")
        
        # 觸發監控停止回調
        if 'monitoring_stopped' in self.callbacks and self.callbacks['monitoring_stopped']:
            self.callbacks['monitoring_stopped']()
            
        logging.info("[資訊] 物體檢測已停止")
        print("物體檢測已停止")
        
    def draw_detection_line(self, frame):
        """
        在幀上繪製檢測線和計數信息 - 使用英文顯示
        
        Args:
            frame: 要繪製的視頻幀
            
        Returns:
            處理後的視頻幀
        """
        if frame is None:
            return None
            
        try:
            # 複製一份幀進行繪製
            result_frame = frame.copy()
            
            if self.roi_y is not None:
                # 獲取幀的寬度
                width = frame.shape[1]
                
                # 繪製檢測線
                line_color = (0, 255, 0) if self.is_detecting else (0, 0, 255)  # 綠色表示啟用，紅色表示未啟用
                cv2.line(result_frame, (0, self.roi_y), (width, self.roi_y), line_color, 2)
                
                # 在檢測線右側添加英文標籤
                status_text = "Active" if self.is_detecting else "Inactive"
                cv2.putText(
                    result_frame,
                    f"Detection Line ({status_text})",
                    (width - 260, self.roi_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    line_color,
                    1
                )
                
                # 如果在測試模式，顯示提示
                if self.is_testing:
                    cv2.putText(
                        result_frame,
                        "Test Mode",
                        (width - 150, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 165, 255),
                        2
                    )
                    
            return result_frame
            
        except Exception as e:
            logging.error(f"繪製檢測線時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return frame

    def process_frame(self, frame):
        """
        完全按照參考代碼處理一個幀的圖像
        
        Args:
            frame: 輸入幀
            
        Returns:
            processed_frame: 處理後的幀
        """
        if frame is None:
            logging.error("傳入的幀為空")
            return None
            
        try:
            # 創建一個幀的副本
            frame_with_detections = frame.copy()
            
            # 檢查是否需要更新ROI位置
            if hasattr(self, 'roi_needs_update') and self.roi_needs_update and self.saved_roi_percentage is not None:
                height = frame.shape[0]
                self.roi_y = int(height * self.saved_roi_percentage)
                self.roi_needs_update = False
                logging.info(f"已更新ROI位置: {self.roi_y}")
            
            # 如果 ROI 為空，按照參考代碼設置為幀高度的20%
            if self.roi_y is None:
                height = frame.shape[0]
                self.roi_y = int(height * 0.2)  # 參考代碼使用0.2
            
            height, width = frame.shape[:2]
            
            # 如果啟用了檢測
            if self.is_detecting:
                # 按照參考代碼設置ROI高度為16像素
                roi_height = 16  # 完全按照參考代碼
                roi_top = self.roi_y
                roi = frame[roi_top:roi_top+roi_height, :]
                
                # 處理ROI區域
                processed_roi = self.image_processor.process_frame(roi)
                
                if processed_roi is not None:
                    detected_objects = self.image_processor.detect_objects(processed_roi)
                    
                    # 如果檢測到物體，更新追蹤
                    if detected_objects:
                        logging.info(f"檢測到 {len(detected_objects)} 個物體")
                        self.update_object_tracking(detected_objects, self.roi_y)
                        
                        # 繪製物體框 - 按照參考代碼中相同的方式
                        for (x, y, w, h, _) in detected_objects:
                            # 繪製在ROI區域內的物體框
                            cv2.rectangle(
                                frame_with_detections[roi_top:roi_top+roi_height, :], 
                                (x, y), 
                                (x + w, y + h), 
                                (0, 0, 255), 
                                2
                            )
            
            # 繪製ROI線 - 按照參考代碼使用綠色
            cv2.line(frame_with_detections, (0, self.roi_y), (width, self.roi_y), (0, 255, 0), 2)
            
            # 添加計數信息
            cv2.putText(
                frame_with_detections, 
                f"Count: {self.current_count}", 
                (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                (0, 255, 0), 
                2
            )
            
            return frame_with_detections
            
        except Exception as e:
            logging.error(f"處理幀時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return frame  # 返回原始幀

    def _draw_simple_roi_line(self, frame):
        """簡化的ROI線繪製，用於未啟動檢測時"""
        if frame is None or self.roi_y is None:
            return frame
            
        # 獲取幀的寬度
        height, width = frame.shape[:2]
        
        # 繪製紅色線表示未啟用
        cv2.line(frame, (0, self.roi_y), (width, self.roi_y), (0, 0, 255), 2)
        
        # 添加英文標籤
        cv2.putText(
            frame, 
            "ROI Line (Inactive)", 
            (width - 200, self.roi_y - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (0, 0, 255), 
            1
        )
            
        return frame

    def _draw_roi_line(self, frame, roi_y):
        """
        在影像上繪製ROI線 - 使用英文標籤
        
        Args:
            frame: 要繪製的影像幀
            roi_y: ROI線的y坐標
            
        Returns:
            繪製ROI線後的影像
        """
        if frame is None or roi_y is None:
            return frame
            
        try:
            # 取得影像寬度
            height, width = frame.shape[:2]
            
            # 繪製ROI線 - 使用綠色表示啟用狀態
            line_color = (0, 255, 0) if self.is_detecting else (0, 0, 255)
            cv2.line(frame, (0, roi_y), (width, roi_y), line_color, 2)
            
            # 添加英文標籤文字
            label_text = "ROI Line (Active)" if self.is_detecting else "ROI Line (Inactive)"
            cv2.putText(
                frame, 
                label_text, 
                (width - 200, roi_y - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.6, 
                line_color, 
                1
            )
            
            return frame
            
        except Exception as e:
            logging.error(f"繪製ROI線時出錯: {str(e)}")
            return frame

    def update_object_tracking(self, detected_objects, roi_y):
        """
        完全按照參考代碼更新物體追蹤和計數
        
        Args:
            detected_objects: 檢測到的物體列表
            roi_y: ROI 線的 y 座標
        """
        try:
            # 如果沒有檢測到物體，直接返回
            if not detected_objects:
                return
                
            # 初始化新的軌跡字典
            new_tracks = {}
            
            # 處理每個檢測到的物體 - 完全按照參考代碼
            for obj in detected_objects:
                x, y, w, h, centroid = obj
                cx, cy = int(centroid[0]), int(centroid[1])
                
                # 檢查是否匹配到現有軌跡
                matched = False
                
                # 遍歷所有現有軌跡尋找匹配 - 使用參考代碼的匹配邏輯
                for track_id, track in self.tracked_objects.items():
                    # 完全按照參考代碼: x座標相差不超過64像素，y座標相差不超過48像素
                    if abs(cx - track.get('x', 0)) < 64 and abs(roi_y - track.get('y', 0)) < 48:
                        # 更新現有軌跡
                        new_tracks[track_id] = {
                            'x': cx, 
                            'y': roi_y, 
                            'count': track.get('count', 0)
                        }
                        matched = True
                        break
                
                # 如果沒有匹配到軌跡，則建立新軌跡（視為新的物體）
                if not matched:
                    # 生成新的軌跡ID - 按照參考代碼的邏輯
                    new_track_id = max(self.tracked_objects.keys()) + 1 if self.tracked_objects else 0
                        
                    # 建立新的軌跡記錄
                    new_tracks[new_track_id] = {
                        'x': cx, 
                        'y': roi_y, 
                        'count': 0
                    }
            
            # 處理計數邏輯 - 完全按照參考代碼的嚴格條件
            for track_id, track in new_tracks.items():
                # 與參考代碼完全相同的判斷: 物體的y座標必須恰好等於ROI線的y座標
                if track['count'] == 0 and track['y'] == roi_y:
                    self.object_count += 1
                    self.current_count = self.object_count
                    track['count'] = 1
                    
                    # 記錄檢測日誌
                    logging.info(f"物體ID: {track_id} 已計數，當前總數: {self.current_count}")
                    
                    # 確保回調函數被調用
                    if 'count_updated' in self.callbacks and self.callbacks['count_updated']:
                        try:
                            self.callbacks['count_updated'](self.current_count)
                        except Exception as e:
                            logging.error(f"調用count_updated回調出錯: {str(e)}")
                            
                    # 檢查是否達到緩衝點或目標計數
                    if self.current_count == self.buffer_point and 'buffer_reached' in self.callbacks and self.callbacks['buffer_reached']:
                        try:
                            self.callbacks['buffer_reached'](self.buffer_point)
                        except Exception as e:
                            logging.error(f"調用buffer_reached回調出錯: {str(e)}")
                        
                    if self.current_count == self.target_count and 'target_reached' in self.callbacks and self.callbacks['target_reached']:
                        try:
                            self.callbacks['target_reached'](self.target_count)
                        except Exception as e:
                            logging.error(f"調用target_reached回調出錯: {str(e)}")
            
            # 完全按照參考代碼：直接用新軌跡替換舊軌跡，不保留歷史軌跡
            self.tracked_objects = new_tracks
            
        except Exception as e:
            logging.error(f"更新物體追蹤時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def start_roi_drag(self, y_pos):
        """
        開始ROI拖拽

        Args:
            y_pos: Y坐標位置
        """
        # 如果傳入的是事件對象，獲取 y 坐標
        if hasattr(y_pos, 'y'):
            logging.info(f"收到事件對象，y 坐標: {y_pos.y}")
            print(f"收到事件對象，y 坐標: {y_pos.y}")
            y_pos = y_pos.y
            
        self.roi_y = y_pos
        self.is_dragging_roi = True
        logging.info(f"開始ROI拖拽，位置: {y_pos}")
        print(f"開始ROI拖拽，位置: {y_pos}")
        
    def update_roi_position(self, y_pos):
        """
        更新ROI位置

        Args:
            y_pos: Y坐標位置
        """
        # 如果傳入的是事件對象，獲取 y 坐標
        if hasattr(y_pos, 'y'):
            logging.info(f"收到事件對象，y 坐標: {y_pos.y}")
            print(f"收到事件對象，y 坐標: {y_pos.y}")
            y_pos = y_pos.y
            
        if self.is_dragging_roi:
            self.roi_y = y_pos
            logging.info(f"更新ROI位置: {y_pos}")
            print(f"更新ROI位置: {y_pos}")
        else:
            logging.warning("嘗試更新 ROI 位置，但未處於拖拽狀態")
            print("嘗試更新 ROI 位置，但未處於拖拽狀態")
            
    def stop_roi_drag(self):
        """停止ROI拖拽"""
        logging.info("停止 ROI 拖拽")
        print("停止 ROI 拖拽")
        
        if not self.is_dragging_roi:
            logging.warning("嘗試停止 ROI 拖拽，但未處於拖拽狀態")
            print("嘗試停止 ROI 拖拽，但未處於拖拽狀態")
            return
            
        self.is_dragging_roi = False
        
        # 保存ROI位置百分比
        if self.roi_y is not None and hasattr(self.camera_manager, 'current_frame') and self.camera_manager.current_frame is not None:
            height = self.camera_manager.current_frame.shape[0]
            if height > 0:
                self.saved_roi_percentage = self.roi_y / height
                logging.info(f"保存ROI位置百分比: {self.saved_roi_percentage:.2f}")
                print(f"保存ROI位置百分比: {self.saved_roi_percentage:.2f}")
        
        logging.info(f"ROI設置完成，位置: {self.roi_y}")
        print(f"ROI設置完成，位置: {self.roi_y}")
        
    def handle_roi_selection(self, event):
        """
        處理ROI選擇事件

        Args:
            event: 事件對象
        """
        logging.info(f"處理ROI選擇事件，位置: {event.y}")
        print(f"處理ROI選擇事件，位置: {event.y}")
        
        # 開始拖拽
        self.start_roi_drag(event.y)
        # 更新位置
        self.update_roi_position(event.y)
        # 停止拖拽
        self.stop_roi_drag()
        
    def update_count(self, count):
        """
        更新计数

        Args:
            count: 新的计数值
        """
        self.current_count = count
        
        # 触发计数更新回调
        if 'count_updated' in self.callbacks and self.callbacks['count_updated']:
            self.callbacks['count_updated'](count)
            
    def set_target_count(self, target_count):
        """
        设置目标计数

        Args:
            target_count: 目标计数值
        """
        self.target_count = target_count
        
    def set_buffer_point(self, buffer_point):
        """
        设置缓冲点

        Args:
            buffer_point: 缓冲点值
        """
        self.buffer_point = buffer_point

    def set_callback(self, event_name, callback):
        """
        设置回调函数

        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        self.callbacks[event_name] = callback 