import logging
import time
import threading
import cv2
import numpy as np

class DetectionController:
    """檢測控制器類"""
    
    def __init__(self, camera_manager):
        """
        初始化檢測控制器
        
        Args:
            camera_manager: 相機管理器實例
        """
        self.camera_manager = camera_manager
        self.is_monitoring = False
        self.monitoring_thread = None
        self.stop_event = threading.Event()
        
        # 回調函數字典
        self.callbacks = {
            'monitoring_started': [],
            'monitoring_stopped': [],
            'frame_processed': [],
            'count_updated': [],
            'camera_preview_updated': [],
            'photo_captured': [],
            'performance_updated': []
        }
        
        # 性能統計
        self.frame_count = 0
        self.fps = 0
        self.last_time = time.time()
        
    def set_callback(self, event_name, callback_function):
        """
        設置回調函數
        
        Args:
            event_name: 事件名稱
            callback_function: 回調函數
        """
        if event_name in self.callbacks:
            self.callbacks[event_name].append(callback_function)
        else:
            logging.warning(f"未知的事件名稱: {event_name}")
            
    def trigger_callback(self, event_name, *args, **kwargs):
        """
        觸發回調函數
        
        Args:
            event_name: 事件名稱
            *args, **kwargs: 傳遞給回調函數的參數
        """
        if event_name in self.callbacks:
            for callback in self.callbacks[event_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logging.error(f"執行回調函數時發生錯誤: {str(e)}")
        else:
            logging.warning(f"未知的事件名稱: {event_name}")
            
    def start_monitoring(self):
        """開始監控"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.stop_event.clear()
        
        # 創建並啟動監控線程
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        # 觸發監控開始回調
        self.trigger_callback('monitoring_started')
        logging.info("監控已開始")
        
    def stop_monitoring(self):
        """停止監控"""
        if not self.is_monitoring:
            return
            
        self.stop_event.set()
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=1.0)
            
        self.is_monitoring = False
        
        # 觸發監控停止回調
        self.trigger_callback('monitoring_stopped')
        logging.info("監控已停止")
        
    def _monitoring_loop(self):
        """監控循環"""
        self.frame_count = 0
        self.last_time = time.time()
        
        while not self.stop_event.is_set():
            start_time = time.time()
            
            # 讀取幀
            ret, frame = self.camera_manager.read_frame()
            
            if not ret or frame is None:
                logging.warning("無法讀取幀")
                time.sleep(0.1)
                continue
                
            # 處理幀（這裡可以添加實際的檢測邏輯）
            processed_frame = self._process_frame(frame)
            
            # 更新幀計數和 FPS
            self.frame_count += 1
            current_time = time.time()
            elapsed = current_time - self.last_time
            
            if elapsed >= 1.0:  # 每秒更新一次 FPS
                self.fps = self.frame_count / elapsed
                self.frame_count = 0
                self.last_time = current_time
                
                # 觸發性能更新回調
                self.trigger_callback('performance_updated', {
                    'fps': self.fps,
                    'frame_time': (current_time - start_time) * 1000  # 毫秒
                })
                
            # 觸發幀處理回調
            self.trigger_callback('frame_processed', processed_frame)
            
            # 控制循環速度
            time.sleep(max(0.01, 0.033 - (time.time() - start_time)))
            
    def _process_frame(self, frame):
        """
        處理幀
        
        Args:
            frame: 輸入幀
            
        Returns:
            處理後的幀
        """
        try:
            # 添加一些基本的處理（這裡只是示例）
            processed_frame = frame.copy()
            
            # 添加時間戳
            cv2.putText(
                processed_frame,
                time.strftime("%Y-%m-%d %H:%M:%S"),
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            # 添加 FPS 信息
            cv2.putText(
                processed_frame,
                f"FPS: {self.fps:.1f}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
            
            return processed_frame
            
        except Exception as e:
            logging.error(f"處理幀時發生錯誤: {str(e)}")
            return frame  # 返回原始幀
            
    def capture_photo(self):
        """
        拍照
        
        Returns:
            拍攝的照片
        """
        try:
            ret, frame = self.camera_manager.read_frame()
            
            if not ret or frame is None:
                logging.error("拍照失敗：無法讀取幀")
                return None
                
            # 觸發照片拍攝回調
            self.trigger_callback('photo_captured', frame)
            
            return frame
            
        except Exception as e:
            logging.error(f"拍照時發生錯誤: {str(e)}")
            return None 