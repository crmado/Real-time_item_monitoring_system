"""
物体检测控制器
负责协调图像处理和物体检测的核心逻辑
"""

import logging
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from models.image_processor import ImageProcessor


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
        
        # ROI设置
        self.roi_y = None
        self.saved_roi_percentage = 0.5  # 默认在中间位置
        self.roi_height = 16  # ROI 檢測區域高度
        
        # 计数相关
        self.current_count = 0
        self.target_count = 1000
        self.buffer_point = 950
        
        # 物體追蹤相關
        self.last_detected_objects = []
        self.tracked_objects = []
        self.object_count = 0
        
        # 當前照片
        self.current_photo = None
        
        # 回调函数字典
        self.callbacks = {}
        
        # 初始化 ROI 位置（確保有一個初始值）
        logging.info("初始化 ROI 位置")
        self._initialize_roi()
        
    def _initialize_roi(self):
        """初始化 ROI 位置"""
        try:
            # 如果相機已經打開並有幀，使用幀高度計算 ROI 位置
            if hasattr(self.camera_manager, 'current_frame') and self.camera_manager.current_frame is not None:
                height = self.camera_manager.current_frame.shape[0]
                self.roi_y = int(height * self.saved_roi_percentage)
                logging.info(f"根據當前幀初始化 ROI 位置: {self.roi_y}, 幀高度: {height}")
            else:
                # 否則設置一個默認值（例如 240），後續會在有幀時更新
                self.roi_y = 240
                logging.info(f"設置默認 ROI 位置: {self.roi_y}")
                
                # 在第一次處理幀時更新 ROI 位置
                self.roi_needs_update = True
        except Exception as e:
            logging.error(f"初始化 ROI 位置時出錯: {str(e)}")
            self.roi_y = 240  # 設置一個安全的默認值
            self.roi_needs_update = True
            
    def put_chinese_text(self, img, text, position, font_size=30, color=(0, 255, 0)):
        """
        在圖像上添加中文文字
        
        Args:
            img: OpenCV 圖像
            text: 要添加的文字
            position: 文字位置 (x, y)
            font_size: 字體大小
            color: 文字顏色 (B, G, R)
            
        Returns:
            添加文字後的圖像
        """
        try:
            # 將 OpenCV 圖像轉換為 PIL 圖像
            img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            
            # 創建繪圖對象
            draw = ImageDraw.Draw(img_pil)
            
            # 嘗試加載字體
            try:
                # 嘗試加載系統字體
                font_paths = [
                    "/System/Library/Fonts/PingFang.ttc",  # macOS
                    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux
                    "C:/Windows/Fonts/msyh.ttc",  # Windows
                    "fonts/NotoSansCJK-Regular.ttc"  # 自帶字體
                ]
                
                font = None
                for path in font_paths:
                    try:
                        font = ImageFont.truetype(path, font_size)
                        break
                    except:
                        continue
                        
                if font is None:
                    # 如果無法加載任何字體，使用默認字體
                    font = ImageFont.load_default()
                    logging.warning("無法加載中文字體，使用默認字體")
            except:
                # 如果加載字體失敗，使用默認字體
                font = ImageFont.load_default()
                logging.warning("加載字體失敗，使用默認字體")
            
            # 繪製文字
            draw.text(position, text, font=font, fill=(color[2], color[1], color[0]))  # PIL 使用 RGB 順序
            
            # 將 PIL 圖像轉回 OpenCV 圖像
            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            logging.error(f"添加中文文字時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return img
            
    def start_detection(self):
        """啟動物體檢測"""
        logging.info("啟動物體檢測")
        print("啟動物體檢測")
        self.is_detecting = True
        
        # 重置計數
        self.current_count = 0
        self.object_count = 0
        self.tracked_objects = []
        
        # 觸發監控開始回調
        if 'monitoring_started' in self.callbacks and self.callbacks['monitoring_started']:
            self.callbacks['monitoring_started']()
            
        logging.info("物體檢測已啟動")
        print("物體檢測已啟動")
        
    def stop_detection(self):
        """停止物體檢測"""
        logging.info("停止物體檢測")
        print("停止物體檢測")
        self.is_detecting = False
        
        # 觸發監控停止回調
        if 'monitoring_stopped' in self.callbacks and self.callbacks['monitoring_stopped']:
            self.callbacks['monitoring_stopped']()
            
        logging.info("物體檢測已停止")
        print("物體檢測已停止")
        
    def draw_detection_line(self, frame):
        """
        在幀上繪製檢測線和計數信息
        
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
                
                # 在檢測線右側添加中文標籤
                status_text = "啟用" if self.is_detecting else "未啟用"
                result_frame = self.put_chinese_text(
                    result_frame,
                    f"檢測線 ({status_text})",
                    (width - 200, self.roi_y - 25),
                    font_size=20,
                    color=line_color
                )
                
                # 如果在測試模式，顯示提示
                if self.is_testing:
                    result_frame = self.put_chinese_text(
                        result_frame,
                        "測試模式",
                        (width - 150, 30),
                        font_size=24,
                        color=(0, 165, 255)
                    )
                    
            return result_frame
            
        except Exception as e:
            logging.error(f"繪製檢測線時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return frame

    def process_frame(self, frame):
        """
        處理視頻幀

        Args:
            frame: 要處理的視頻幀

        Returns:
            處理後的視頻幀
        """
        if frame is None:
            logging.warning("處理幀為空")
            return None
            
        # 如果 ROI 位置為空或需要更新，則初始化或更新 ROI 位置
        if self.roi_y is None or (hasattr(self, 'roi_needs_update') and self.roi_needs_update):
            logging.info("更新 ROI 位置")
            height = frame.shape[0]
            self.roi_y = int(height * self.saved_roi_percentage)
            logging.info(f"已更新 ROI 位置: {self.roi_y}, 幀高度: {height}")
            if hasattr(self, 'roi_needs_update'):
                self.roi_needs_update = False
            
        # 複製一份幀進行處理
        processed_frame = frame.copy()
        
        # 如果没有启动检测，直接返回带有未激活 ROI 線的幀
        if not self.is_detecting:
            return self.draw_detection_line(processed_frame)
            
        try:
            # 定義 ROI 區域
            roi_top = max(0, self.roi_y - self.roi_height // 2)
            roi_bottom = min(frame.shape[0], self.roi_y + self.roi_height // 2)
            roi = frame[roi_top:roi_bottom, :]
            
            # 使用圖像處理器處理 ROI 區域
            processed_roi = self.image_processor.process_frame(roi)
            
            # 檢測物體
            if processed_roi is not None:
                detected_objects = self.image_processor.detect_objects(processed_roi)
                
                # 更新物體追蹤和計數
                self.update_object_tracking(detected_objects, self.roi_y)
                
                # 在幀上繪製檢測結果
                if detected_objects:
                    # 調整物體座標到原始幀
                    for i, obj in enumerate(detected_objects):
                        x, y, w, h, center = obj
                        # 調整 y 座標
                        y += roi_top
                        center = (center[0], center[1] + roi_top)
                        # 繪製物體框
                        cv2.rectangle(processed_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        # 繪製物體 ID
                        cv2.putText(
                            processed_frame,
                            f"ID: {i}",
                            (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 255, 0),
                            1
                        )
            
            # 繪製檢測線並添加計數信息
            processed_frame = self.draw_detection_line(processed_frame)
                
            return processed_frame

        except Exception as e:
            logging.error(f"處理視頻幀時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
        return frame
        
    def update_object_tracking(self, detected_objects, roi_y):
        """
        更新物體追蹤和計數
        
        Args:
            detected_objects: 檢測到的物體列表
            roi_y: ROI 線的 y 座標
        """
        try:
            # 如果沒有檢測到物體，直接返回
            if not detected_objects:
                self.last_detected_objects = []
                return
                
            # 如果是第一次檢測，初始化追蹤列表
            if not self.last_detected_objects:
                self.last_detected_objects = detected_objects
                return
                
            # 比較當前檢測到的物體和上一次檢測到的物體
            # 檢查是否有新物體穿過 ROI 線
            for obj in detected_objects:
                x, y, w, h, center = obj
                
                # 檢查物體中心是否在 ROI 線附近
                if abs(center[1] - roi_y) < 5:
                    # 檢查是否是新物體（不在已追蹤列表中）
                    is_new_object = True
                    for tracked_obj in self.tracked_objects:
                        tracked_x, tracked_y, tracked_w, tracked_h, _ = tracked_obj
                        # 如果物體位置相近，認為是同一個物體
                        if (abs(x - tracked_x) < 50 and abs(y - tracked_y) < 50):
                            is_new_object = False
                            break
                            
                    if is_new_object:
                        # 添加到已追蹤列表
                        self.tracked_objects.append(obj)
                        # 增加計數
                        self.object_count += 1
                        self.current_count = self.object_count
                        logging.info(f"檢測到新物體，當前計數: {self.current_count}")
                        print(f"檢測到新物體，當前計數: {self.current_count}")
                        
                        # 觸發計數更新回調
                        if 'count_updated' in self.callbacks and self.callbacks['count_updated']:
                            self.callbacks['count_updated'](self.current_count)
                            
                        # 檢查是否達到緩衝點
                        if self.current_count == self.buffer_point:
                            logging.info(f"達到緩衝點: {self.buffer_point}")
                            print(f"達到緩衝點: {self.buffer_point}")
                            # 觸發緩衝點回調
                            if 'buffer_reached' in self.callbacks and self.callbacks['buffer_reached']:
                                self.callbacks['buffer_reached'](self.buffer_point)
                                
                        # 檢查是否達到目標計數
                        if self.current_count == self.target_count:
                            logging.info(f"達到目標計數: {self.target_count}")
                            print(f"達到目標計數: {self.target_count}")
                            # 觸發目標計數回調
                            if 'target_reached' in self.callbacks and self.callbacks['target_reached']:
                                self.callbacks['target_reached'](self.target_count)
                                
            # 更新上一次檢測到的物體
            self.last_detected_objects = detected_objects
            
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
            y_pos = y_pos.y
            
        if self.is_dragging_roi:
            self.roi_y = y_pos
            logging.debug(f"更新ROI位置: {y_pos}")
            print(f"更新ROI位置: {y_pos}")
            
    def stop_roi_drag(self):
        """停止ROI拖拽"""
        if not self.is_dragging_roi:
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