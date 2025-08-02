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
            logging.info("收到相機捕獲開始事件，啟動處理循環")
            self._start_processing()
        elif event_type == 'capture_stopped':
            logging.info("收到相機捕獲停止事件，停止處理循環")
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
        """連接相機 - 線程安全版本"""
        try:
            # 先完全停止任何現有的系統
            self.force_stop_all()
            
            # 等待線程完全停止
            time.sleep(0.5)
            
            success = self.camera_model.connect(device_index)
            if success:
                self.notify_views('system_status', '相機已連接')
            return success
        except Exception as e:
            logging.error(f"連接相機錯誤: {str(e)}")
            return False
    
    def force_stop_all(self):
        """強制停止所有線程和連接 - 用於防止線程競爭"""
        try:
            # 停止處理循環
            self._stop_processing()
            
            # 停止相機捕獲
            if hasattr(self, 'camera_model') and self.camera_model:
                self.camera_model.stop_capture()
                
            # 等待線程停止
            if hasattr(self, 'processing_thread') and self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=2.0)
                
            logging.info("強制停止所有線程完成")
            
        except Exception as e:
            logging.error(f"強制停止錯誤: {str(e)}")
    
    def disconnect_camera(self):
        """斷開相機"""
        self.force_stop_all()
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
    
    def set_exposure_time(self, exposure_us: float) -> bool:
        """設置相機曝光時間"""
        return self.camera_model.set_exposure_time(exposure_us)
    
    def get_exposure_time(self) -> float:
        """獲取當前曝光時間"""
        return self.camera_model.get_exposure_time()
    
    def get_exposure_range(self) -> tuple:
        """獲取曝光時間範圍"""
        return self.camera_model.get_exposure_range()
    
    # ==================== 批次檢測控制 ====================
    
    def start_batch_detection(self):
        """開始批次檢測模式"""
        try:
            # 批次檢測模式不需要特殊處理，檢測邏輯在視圖層處理
            # 這裡確保檢測正在運行
            if not self.is_processing:
                self._start_processing()
            
            logging.info("✅ 批次檢測模式已啟動")
            return True
            
        except Exception as e:
            logging.error(f"啟動批次檢測錯誤: {str(e)}")
            return False
    
    def stop_batch_detection(self):
        """停止批次檢測模式"""
        try:
            # 批次檢測停止不影響視頻流，只是邏輯上的停止
            # 實際的檢測控制在視圖層處理
            logging.info("⏹️ 批次檢測模式已停止")
            return True
            
        except Exception as e:
            logging.error(f"停止批次檢測錯誤: {str(e)}")
            return False
    
    # ==================== 主處理循環 ====================
    
    def _start_processing(self):
        """開始處理循環"""
        if self.is_processing:
            logging.info("處理循環已經在運行")
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
        
        logging.info("✅ 開始主處理循環，線程已啟動")
        
        # 等待一小段時間確保線程啟動
        time.sleep(0.1)
    
    def _stop_processing(self):
        """停止處理循環"""
        self.is_processing = False
        self.stop_event.set()
        
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        logging.info("停止主處理循環")
    
    def _processing_loop(self):
        """主處理循環 - 極致性能優化版本"""
        logging.info("🚀 啟動高性能處理循環")
        
        while not self.stop_event.is_set() and self.is_processing:
            try:
                frame_start_time = time.time()
                
                # 獲取最新幀
                frame = self.camera_model.get_latest_frame()
                if frame is None:
                    # 第一次獲取失敗時的診斷日誌
                    if self.total_processed_frames == 0:
                        logging.warning("處理循環：等待第一幀")
                    time.sleep(0.005)  # 🚀 減少延遲50%
                    continue
                
                # 執行檢測
                objects, result_frame = self.detection_model.detect_frame(frame)
                
                # 更新統計
                self.total_processed_frames += 1
                frame_time = time.time() - frame_start_time
                self.frame_times.append(frame_time)
                
                # 🚀 優化FPS計算頻率（每30幀計算一次）
                if len(self.frame_times) >= 30:
                    # 確保使用正確的列表操作
                    recent_times = list(self.frame_times)[-30:]
                    avg_time = sum(recent_times) / len(recent_times)
                    self.processing_fps = 1.0 / avg_time if avg_time > 0 else 0
                    # 保持最新100幀數據
                    if len(self.frame_times) > 100:
                        # 保留最新的100個時間記錄
                        while len(self.frame_times) > 100:
                            self.frame_times.pop(0)
                
                # 🚀 優化視圖通知策略（高頻率通知提升流暢度）
                should_notify = (
                    self.total_processed_frames == 1 or  # 第一幀
                    self.total_processed_frames % 2 == 0  # 每2幀通知一次（比原來更頻繁）
                )
                
                if should_notify:
                    self.notify_views('frame_processed', {
                        'frame': result_frame,
                        'objects': objects,
                        'object_count': len(objects),
                        'processing_fps': self.processing_fps,
                        'detection_fps': getattr(self.detection_model, 'detection_fps', 0)
                    })
                    
                    # 第一幀日誌
                    if self.total_processed_frames == 1:
                        logging.info(f"✅ 處理第一幀成功，高性能模式啟動")
                
                # 🚀 完全移除延遲，追求極致性能
                # 不添加任何sleep以達到最高FPS
                
            except Exception as e:
                logging.error(f"處理循環錯誤: {str(e)}")
                time.sleep(0.001)  # 🚀 錯誤時最小延遲
    
    # ==================== 系統控制 ====================
    
    def auto_start_camera_system(self) -> bool:
        """自動檢測並啟動相機系統 - 防止重複連接版本"""
        try:
            # 檢查是否已經連接
            if self.camera_model.is_connected and self.camera_model.is_grabbing:
                print("   ⚠️ 相機已連接並正在捕獲，跳過重複啟動")
                return True
            
            print("   🔍 檢測可用相機...")
            cameras = self.detect_cameras()
            if not cameras:
                print("   ❌ 未檢測到Basler相機")
                return False
            
            # 尋找目標相機 acA640-300gm
            target_camera_index = 0
            for i, camera in enumerate(cameras):
                if camera.get('is_target', False):
                    target_camera_index = i
                    print(f"   ✅ 找到目標相機: {camera['model']} (索引: {i})")
                    break
            else:
                print(f"   ⚠️ 使用第一台相機: {cameras[0]['model']}")
            
            print("   🔗 連接相機...")
            if not self.connect_camera(target_camera_index):
                print("   ❌ 相機連接失敗")
                return False
            
            print("   🚀 啟動捕獲...")
            if not self.start_capture():
                print("   ❌ 啟動捕獲失敗")
                return False
            
            # 手動啟動處理循環，因為觀察者可能沒有正確觸發
            print("   🔄 手動啟動處理循環...")
            self._start_processing()
            
            print("   ✅ 系統完全啟動，開始高速捕獲")
            return True
            
        except Exception as e:
            error_msg = f"自動啟動失敗: {str(e)}"
            logging.error(error_msg)
            print(f"   ❌ {error_msg}")
            return False
    
    def _configure_high_performance(self):
        """配置相機以達到最高性能 - 280fps目標"""
        try:
            # 獲取相機實例進行進階配置
            camera = self.camera_model.camera
            if not camera:
                return
            
            # 設置最高性能參數
            high_perf_configs = [
                # 幀率設置 - 目標280fps
                ('AcquisitionFrameRateEnable', True),
                ('AcquisitionFrameRate', 285.0),  # 設置略高於目標值
                
                # 最小曝光時間以達到高速
                ('ExposureTime', 800.0),  # 0.8ms
                
                # 固定增益避免自動調整
                ('Gain', 1.0),
                
                # 網路優化
                ('GevSCPSPacketSize', 9000),  # Jumbo frames
                ('GevSCPD', 1000),  # 幀間延遲最小化
                
                # 緩衝區優化
                ('DeviceStreamChannelCount', 1),
                ('DeviceStreamChannelSelector', 0),
                ('DeviceStreamChannelType', 'Stream'),
            ]
            
            for param, value in high_perf_configs:
                try:
                    if hasattr(camera, param):
                        node = getattr(camera, param)
                        if hasattr(node, 'SetValue'):
                            node.SetValue(value)
                            logging.info(f"高性能配置 {param} = {value}")
                except Exception as e:
                    logging.debug(f"配置 {param} 失敗: {str(e)}")
            
            # 設置檢測參數為高速模式
            self.detection_model.update_parameters({
                'min_area': 50,    # 降低最小面積以減少計算
                'max_area': 3000,  # 限制最大面積
                'enable_detection': True
            })
            
            logging.info("高性能配置完成 - 目標280fps")
            
        except Exception as e:
            logging.warning(f"高性能配置警告: {str(e)}")
    
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
    
    def system_health_check(self) -> Dict[str, Any]:
        """系統健康檢查"""
        health_status = {
            'camera_connected': False,
            'camera_grabbing': False,
            'processing_active': False,
            'memory_usage': 'unknown',
            'thread_status': 'unknown',
            'error_count': 0,
            'overall_status': 'unhealthy'
        }
        
        try:
            # 檢查相機狀態
            if self.camera_model:
                camera_info = self.camera_model.get_camera_info()
                health_status['camera_connected'] = camera_info.get('is_connected', False)
                health_status['camera_grabbing'] = camera_info.get('is_grabbing', False)
            
            # 檢查處理狀態
            health_status['processing_active'] = self.is_processing
            
            # 檢查線程狀態
            thread_alive = (hasattr(self, 'processing_thread') and 
                          self.processing_thread and 
                          self.processing_thread.is_alive())
            health_status['thread_status'] = 'alive' if thread_alive else 'stopped'
            
            # 計算總體健康狀態
            if (health_status['camera_connected'] and 
                health_status['processing_active'] and
                thread_alive):
                health_status['overall_status'] = 'healthy'
            elif health_status['camera_connected']:
                health_status['overall_status'] = 'warning'
            else:
                health_status['overall_status'] = 'critical'
                
        except Exception as e:
            logging.error(f"系統健康檢查錯誤: {str(e)}")
            health_status['error_count'] += 1
        
        return health_status
    
    def cleanup(self):
        """清理資源 - 增強版本"""
        try:
            logging.info("開始清理控制器資源...")
            
            # 停止系統
            self.stop_system()
            
            # 斷開相機
            self.disconnect_camera()
            
            # 清理觀察者列表
            if hasattr(self, 'view_observers'):
                self.view_observers.clear()
            
            logging.info("控制器資源清理完成")
        except Exception as e:
            logging.error(f"清理資源錯誤: {str(e)}")
    
    def __del__(self):
        """析構函數 - 安全版本"""
        try:
            self.cleanup()
        except:
            # 忽略析構時的所有異常，避免程序崩潰
            pass