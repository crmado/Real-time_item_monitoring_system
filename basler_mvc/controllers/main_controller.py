"""
主控制器 - MVC 架構核心
協調相機模型和檢測模型的業務邏輯
"""

import logging
import threading
import time
import numpy as np
from typing import Optional, Dict, Any, Callable
from collections import deque

from ..models.basler_camera_model import BaslerCameraModel
from ..models.detection_model import DetectionModel


class MainController:
    """主控制器 - 協調所有業務邏輯"""
    
    def __init__(self):
        """初始化主控制器"""
        # 模型實例
        self.camera_model = BaslerCameraModel()
        self.detection_model = DetectionModel()
        
        # 控制器狀態
        self.is_running = False
        self.is_processing = False
        
        # 處理線程
        self.processing_thread = None
        self.stop_event = threading.Event()
        
        # 性能統計
        self.processing_fps = 0.0
        self.total_processed_frames = 0
        self.processing_start_time = None
        self.frame_times = deque(maxlen=100)
        
        # 觀察者（Views）
        self.view_observers = []
        
        # 設置模型觀察者
        self.camera_model.add_observer(self._on_camera_event)
        self.detection_model.add_observer(self._on_detection_event)
        
        logging.info("主控制器初始化完成")
    
    def add_view_observer(self, observer: Callable):
        """添加視圖觀察者"""
        self.view_observers.append(observer)
    
    def notify_views(self, event_type: str, data: Any = None):
        """通知所有視圖"""
        for observer in self.view_observers:
            try:
                observer(event_type, data)
            except Exception as e:
                logging.error(f"通知視圖錯誤: {str(e)}")
    
    def _on_camera_event(self, event_type: str, data: Any = None):
        """處理相機事件"""
        # 轉發到視圖
        self.notify_views(f"camera_{event_type}", data)
        
        # 特殊處理
        if event_type == 'capture_started':
            self._start_processing()
        elif event_type == 'capture_stopped':
            self._stop_processing()
    
    def _on_detection_event(self, event_type: str, data: Any = None):
        """處理檢測事件"""
        # 轉發到視圖
        self.notify_views(f"detection_{event_type}", data)
    
    # ==================== 相機控制 ====================
    
    def detect_cameras(self) -> list:
        """檢測相機"""
        return self.camera_model.detect_cameras()
    
    def connect_camera(self, device_index: int = 0) -> bool:
        """連接相機"""
        success = self.camera_model.connect(device_index)
        if success:
            self.notify_views('system_status', '相機已連接')
        return success
    
    def disconnect_camera(self):
        """斷開相機"""
        self.stop_system()
        self.camera_model.disconnect()
        self.notify_views('system_status', '相機已斷開')
    
    def start_capture(self) -> bool:
        """開始捕獲"""
        if not self.camera_model.is_connected:
            self.notify_views('system_error', '請先連接相機')
            return False
        
        success = self.camera_model.start_capture()
        if success:
            self.is_running = True
            self.notify_views('system_status', '開始捕獲')
        return success
    
    def stop_capture(self):
        """停止捕獲"""
        self.camera_model.stop_capture()
        self.is_running = False
        self.notify_views('system_status', '停止捕獲')
    
    # ==================== 檢測控制 ====================
    
    def set_detection_method(self, method_name: str) -> bool:
        """設置檢測方法"""
        return self.detection_model.set_detection_method(method_name)
    
    def update_detection_parameters(self, params: Dict[str, Any]) -> bool:
        """更新檢測參數"""
        return self.detection_model.update_parameters(params)
    
    def toggle_detection(self, enabled: bool):
        """開啟/關閉檢測"""
        self.detection_model.update_parameters({'enable_detection': enabled})
        status = '檢測已開啟' if enabled else '檢測已關閉'
        self.notify_views('system_status', status)
    
    # ==================== 主處理循環 ====================
    
    def _start_processing(self):
        """開始處理循環"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.stop_event.clear()
        
        # 重置統計
        self.total_processed_frames = 0
        self.processing_start_time = time.time()
        self.frame_times.clear()
        
        # 啟動處理線程
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        logging.info("開始主處理循環")
    
    def _stop_processing(self):
        """停止處理循環"""
        self.is_processing = False
        self.stop_event.set()
        
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        logging.info("停止主處理循環")
    
    def _processing_loop(self):
        """主處理循環 - 高性能版本"""
        while not self.stop_event.is_set() and self.is_processing:
            try:
                frame_start_time = time.time()
                
                # 獲取最新幀
                frame = self.camera_model.get_latest_frame()
                if frame is None:
                    time.sleep(0.001)  # 微小延遲
                    continue
                
                # 執行檢測
                objects, result_frame = self.detection_model.detect_frame(frame)
                
                # 更新統計
                self.total_processed_frames += 1
                frame_time = time.time() - frame_start_time
                self.frame_times.append(frame_time)
                
                # 計算處理FPS
                if len(self.frame_times) >= 10:
                    avg_time = sum(self.frame_times) / len(self.frame_times)
                    self.processing_fps = 1.0 / avg_time if avg_time > 0 else 0
                
                # 通知視圖（減少頻率）
                if self.total_processed_frames % 15 == 0:  # 每15幀通知一次
                    self.notify_views('frame_processed', {
                        'frame': result_frame,
                        'objects': objects,
                        'object_count': len(objects),
                        'processing_fps': self.processing_fps
                    })
                
                # 極小延遲以防CPU過載
                time.sleep(0.001)
                
            except Exception as e:
                logging.error(f"處理循環錯誤: {str(e)}")
                time.sleep(0.01)
    
    # ==================== 系統控制 ====================
    
    def start_system(self) -> bool:
        """啟動整個系統"""
        try:
            # 檢測相機
            cameras = self.detect_cameras()
            if not cameras:
                self.notify_views('system_error', '未檢測到相機')
                return False
            
            # 連接第一台相機
            if not self.connect_camera(0):
                self.notify_views('system_error', '相機連接失敗')
                return False
            
            # 開始捕獲
            if not self.start_capture():
                self.notify_views('system_error', '啟動捕獲失敗')
                return False
            
            self.notify_views('system_status', '系統已啟動')
            return True
            
        except Exception as e:
            error_msg = f"系統啟動失敗: {str(e)}"
            logging.error(error_msg)
            self.notify_views('system_error', error_msg)
            return False
    
    def stop_system(self):
        """停止整個系統"""
        try:
            self._stop_processing()
            self.stop_capture()
            self.notify_views('system_status', '系統已停止')
            
        except Exception as e:
            logging.error(f"系統停止錯誤: {str(e)}")
    
    def restart_system(self) -> bool:
        """重啟系統"""
        self.stop_system()
        time.sleep(1)  # 等待完全停止
        return self.start_system()
    
    # ==================== 狀態查詢 ====================
    
    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        camera_stats = self.camera_model.get_stats()
        detection_stats = self.detection_model.get_stats()
        camera_info = self.camera_model.get_camera_info()
        
        elapsed_time = time.time() - self.processing_start_time if self.processing_start_time else 0
        avg_processing_fps = self.total_processed_frames / elapsed_time if elapsed_time > 0 else 0
        
        return {
            # 系統狀態
            'is_running': self.is_running,
            'is_processing': self.is_processing,
            'is_connected': self.camera_model.is_connected,
            'is_grabbing': self.camera_model.is_grabbing,
            
            # 相機統計
            'camera_fps': camera_stats.get('current_fps', 0),
            'camera_avg_fps': camera_stats.get('average_fps', 0),
            'camera_total_frames': camera_stats.get('total_frames', 0),
            
            # 處理統計
            'processing_fps': self.processing_fps,
            'processing_avg_fps': avg_processing_fps,
            'processing_total_frames': self.total_processed_frames,
            
            # 檢測統計
            'detection_fps': detection_stats.get('detection_fps', 0),
            'object_count': detection_stats.get('object_count', 0),
            'detection_method': detection_stats.get('current_method', 'unknown'),
            
            # 相機資訊
            'camera_info': camera_info,
            
            # 時間
            'elapsed_time': elapsed_time
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """獲取性能報告"""
        status = self.get_system_status()
        
        # 性能評級
        camera_fps = status['camera_fps']
        processing_fps = status['processing_fps']
        
        if camera_fps >= 250:
            camera_grade = "🏆 卓越"
        elif camera_fps >= 200:
            camera_grade = "🎉 優秀"
        elif camera_fps >= 150:
            camera_grade = "✅ 良好"
        else:
            camera_grade = "⚠️ 需要優化"
        
        if processing_fps >= 200:
            processing_grade = "🏆 卓越"
        elif processing_fps >= 150:
            processing_grade = "🎉 優秀"
        elif processing_fps >= 100:
            processing_grade = "✅ 良好"
        else:
            processing_grade = "⚠️ 需要優化"
        
        return {
            'camera_performance': {
                'fps': camera_fps,
                'grade': camera_grade,
                'total_frames': status['camera_total_frames']
            },
            'processing_performance': {
                'fps': processing_fps,
                'grade': processing_grade,
                'total_frames': status['processing_total_frames']
            },
            'detection_performance': {
                'fps': status['detection_fps'],
                'object_count': status['object_count'],
                'method': status['detection_method']
            },
            'system_efficiency': {
                'fps_ratio': processing_fps / camera_fps if camera_fps > 0 else 0,
                'elapsed_time': status['elapsed_time']
            }
        }
    
    # ==================== 清理 ====================
    
    def cleanup(self):
        """清理資源"""
        try:
            self.stop_system()
            self.disconnect_camera()
            logging.info("控制器資源清理完成")
        except Exception as e:
            logging.error(f"清理資源錯誤: {str(e)}")
    
    def __del__(self):
        """析構函數"""
        try:
            self.cleanup()
        except:
            pass