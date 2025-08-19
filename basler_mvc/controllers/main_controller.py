"""
主控制器 - MVC 架構核心
協調相機模型和檢測模型的業務邏輯
"""

import logging
import threading
import time
import numpy as np
from typing import Optional, Dict, Any, Callable, List, Tuple
from collections import deque

from ..models.basler_camera_model import BaslerCameraModel
from ..models.detection_model import DetectionModel
from ..models.video_recorder_model import VideoRecorderModel
from ..models.video_player_model import VideoPlayerModel
from ..models.detection_processor import DetectionProcessor
from ..utils.recording_validator import RecordingValidator
from ..utils.memory_monitor import MemoryMonitor


class MainController:
    """主控制器 - 協調所有業務邏輯"""
    
    def __init__(self):
        """初始化主控制器"""
        # 模型實例
        self.camera_model = BaslerCameraModel()
        self.detection_model = DetectionModel()
        
        # 視頻相關模型
        self.video_recorder = VideoRecorderModel()
        self.video_player = VideoPlayerModel()
        
        # 🔧 設置錄製器到相機模型（依賴注入）
        self.camera_model.set_video_recorder(self.video_recorder)
        
        # 🚀 高性能檢測處理器（專用於視頻回放）
        self.detection_processor = DetectionProcessor(self.detection_model)
        
        # 🎯 錄製驗證器（280 FPS品質檢查）
        self.recording_validator = RecordingValidator(expected_fps=280, tolerance_percent=5.0)
        
        # 🔍 記憶體監控器 - 提高限制以減少警告
        self.memory_monitor = MemoryMonitor(check_interval=30.0, memory_limit_mb=768.0)
        
        # 設置記憶體警告回調
        self.memory_monitor.set_warning_callback(self._on_memory_warning)
        self.memory_monitor.set_critical_callback(self._on_memory_critical)
        
        # 系統模式：live, recording, playback
        self.current_mode = 'live'
        
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
        self.frame_times = deque(maxlen=50)  # 優化記憶體使用
        
        # 🎯 包裝計數系統
        self.total_detected_count = 0     # 當前計數：該影像啟動檢測後的所有檢測到的總合
        self.current_segment_count = 0    # 目前計數：每一段的數量
        self.package_count = 0            # 包裝數：每滿100就+1
        self.segment_target = 100         # 每段目標數量
        
        # 觀察者（Views）
        self.view_observers = []
        
        # 設置模型觀察者
        self.camera_model.add_observer(self._on_camera_event)
        self.detection_model.add_observer(self._on_detection_event)
        self.video_recorder.add_observer(self._on_video_recorder_event)
        self.video_player.add_observer(self._on_video_player_event)
        self.detection_processor.add_observer(self._on_detection_processor_event)
        
        # 注入錄製器到相機模型
        self.camera_model.set_video_recorder(self.video_recorder)
        
        # 啟動記憶體監控
        self.memory_monitor.start_monitoring()
        
        logging.info("主控制器初始化完成")
    
    def _update_package_counting(self, crossing_count: int):
        """更新包裝計數系統"""
        try:
            # 🎯 修正邏輯：當前計數(總累計) = 目前計數(當前段) = 實際檢測數量
            self.total_detected_count = crossing_count      # 當前計數(總累計)
            self.current_segment_count = crossing_count     # 目前計數(當前段) - 應該一樣
            
            # 計算包裝數（每滿100包裝數+1）
            new_package_count = crossing_count // self.segment_target
            
            # 檢查是否需要增加包裝數
            if new_package_count > self.package_count:
                self.package_count = new_package_count
                # 🚀🚀 206fps模式：最小化日誌輸出
                if self.package_count % 10 == 1:  # 極少數日誌，只在關鍵里程碑
                    logging.info(f"📦 包裝數: {self.package_count}")
                
        except Exception as e:
            logging.error(f"包裝計數更新錯誤: {str(e)}")
    
    def reset_package_counting(self):
        """重置包裝計數系統"""
        self.total_detected_count = 0
        self.current_segment_count = 0
        self.package_count = 0
        logging.info("🔄 包裝計數系統已重置")
    
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
        # 🔧 修復：避免重複添加 camera_ 前綴
        if event_type.startswith('camera_'):
            # 如果已經有前綴，直接轉發
            self.notify_views(event_type, data)
        else:
            # 如果沒有前綴，添加前綴
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
    
    def _on_video_recorder_event(self, event_type: str, data: Any = None):
        """處理視頻錄製事件"""
        # 轉發到視圖
        self.notify_views(f"recorder_{event_type}", data)
        
        if event_type == 'recording_started':
            logging.info(f"錄製開始: {data.get('filename', 'unknown')}")
        elif event_type == 'recording_stopped':
            logging.info(f"錄製完成: {data.get('frames_recorded', 0)} 幀")
            # 🎯 自動驗證剛完成的錄製檔案
            self._auto_validate_latest_recording(data)
    
    def _on_video_player_event(self, event_type: str, data: Any = None):
        """處理視頻播放事件"""
        # 轉發到視圖
        self.notify_views(f"player_{event_type}", data)
        
        if event_type == 'frame_ready':
            # 🚀 視頻回放模式：使用高性能檢測處理器
            if self.current_mode == 'playback':
                self._submit_frame_for_detection(data)
        elif event_type == 'video_loaded':
            logging.info(f"視頻加載完成: {data.get('filename', 'unknown')}")
            
            # 🎯 新功能：根據實際視頻數據優化檢測參數
            if self.current_mode == 'playback':
                self.detection_model.set_source_type('video', data)
                logging.info(f"🚀 視頻檢測參數已根據實際規格優化")
            
            # 啟動檢測處理器
            self.detection_processor.start_processing()
        elif event_type == 'playback_finished':
            logging.info("視頻播放完成")
            # 停止檢測處理器
            self.detection_processor.stop_processing()
    
    def _on_detection_processor_event(self, event_type: str, data: Any = None):
        """處理檢測處理器事件"""
        if event_type == 'detection_result':
            # 直接轉發檢測結果到視圖
            self.notify_views('frame_processed', data)
        else:
            # 轉發其他事件
            self.notify_views(f"processor_{event_type}", data)
    
    def _submit_frame_for_detection(self, frame_data):
        """提交幀到檢測處理器 - 高性能並行檢測"""
        frame = frame_data.get('frame')
        if frame is None:
            return
            
        try:
            # 🚀 關鍵：提交到檢測處理器進行並行處理
            frame_info = {
                'frame_number': frame_data.get('frame_number', 0),
                'progress': frame_data.get('progress', 0),
                'timestamp': frame_data.get('timestamp', 0),
                'source': 'video'
            }
            
            # 🎯 非阻塞提交（視頻回放模式優化）
            success = self.detection_processor.submit_frame(frame, frame_info)
            
            # 🎯 靜默處理：視頻回放時跳過部分幀是正常的，不記錄警告
            if not success and frame_info['frame_number'] % 100 == 0:  # 只有每100幀記錄一次調試信息
                logging.debug(f"幀 {frame_info['frame_number']} 跳過（處理器忙碌）")
            
        except Exception as e:
            logging.error(f"提交檢測幀失敗: {str(e)}")
    
    def _process_playback_frame(self, frame_data):
        """處理回放幀 - 保留舊接口（備用）"""
        # 重定向到新的處理方式
        self._submit_frame_for_detection(frame_data)
    
    # ==================== 相機控制 ====================
    
    def detect_cameras(self) -> list:
        """檢測相機"""
        return self.camera_model.detect_cameras()
    
    # ==================== 🎯 設備監控功能 ====================
    
    def start_device_monitor(self) -> bool:
        """啟動設備監控"""
        return self.camera_model.start_device_monitor()
    
    def stop_device_monitor(self):
        """停止設備監控"""
        self.camera_model.stop_device_monitor()
    
    def force_refresh_device_list(self) -> list:
        """手動刷新設備列表"""
        return self.camera_model.force_refresh_device_list()
    
    def set_device_monitor_interval(self, interval: float):
        """設置設備監控間隔"""
        self.camera_model.set_device_monitor_interval(interval)
    
    def connect_camera(self, device_index: int = 0) -> bool:
        """連接相機 - 強化線程安全版本"""
        try:
            # 🔒 防止重複連接
            if self.camera_model.is_connected:
                logging.info("相機已連接，先斷開現有連接...")
                self.force_stop_all()
                time.sleep(1.0)  # 確保完全斷開
            
            # 🛡️ 連接前狀態檢查
            if hasattr(self.camera_model, '_active_capture_thread') and self.camera_model._active_capture_thread:
                logging.warning("檢測到活動捕獲線程，強制清理...")
                self.camera_model._active_capture_thread = None
            
            logging.info(f"🔗 正在連接相機 (設備索引: {device_index})...")
            success = self.camera_model.connect(device_index)
            
            if success:
                logging.info("✅ 相機連接成功")
                self.notify_views('system_status', '相機已連接')
            else:
                logging.error("❌ 相機連接失敗")
                self.notify_views('system_error', '相機連接失敗')
                
            return success
            
        except Exception as e:
            logging.error(f"❌ 連接相機錯誤: {str(e)}")
            self.notify_views('system_error', f'連接相機錯誤: {str(e)}')
            return False
    
    def force_stop_all(self):
        """強制停止所有線程和連接 - 強化版本，防止線程競爭，保護錄製數據"""
        try:
            logging.info("🛑 開始強制停止所有系統組件...")
            
            # 🎯 錄製獨立化：強制停止不再影響錄製
            if (hasattr(self, 'camera_model') and self.camera_model and 
                hasattr(self.camera_model, 'recording_enabled') and 
                self.camera_model.recording_enabled):
                logging.info("🎬 檢測到正在錄製，錄製功能已獨立化")
                logging.info("📝 錄製將獨立繼續，不受系統強制停止影響")
            
            # 🔄 第一步：停止處理循環
            if self.is_processing:
                logging.info("🔄 停止主處理循環...")
                self._stop_processing()
            
            # 🎥 第二步：停止相機捕獲
            if hasattr(self, 'camera_model') and self.camera_model:
                if self.camera_model.is_grabbing:
                    logging.info("🎥 停止相機捕獲...")
                    self.camera_model.stop_capture()
            
            # 🧵 第三步：安全等待所有線程停止
            threads_to_wait = []
            
            # 檢查處理線程
            if hasattr(self, 'processing_thread') and self.processing_thread and self.processing_thread.is_alive():
                threads_to_wait.append(('處理線程', self.processing_thread))
            
            # 檢查相機捕獲線程
            if (hasattr(self.camera_model, 'capture_thread') and 
                self.camera_model.capture_thread and 
                self.camera_model.capture_thread.is_alive()):
                threads_to_wait.append(('相機捕獲線程', self.camera_model.capture_thread))
            
                            # 🎯 等待所有線程停止 - 錄製模式需更長時間
            for thread_name, thread in threads_to_wait:
                # 檢查是否在錄製中，需要更長等待時間
                is_recording = (hasattr(self, 'camera_model') and 
                              self.camera_model and 
                              hasattr(self.camera_model, 'recording_enabled') and
                              self.camera_model.recording_enabled)
                              
                timeout = 5.0 if is_recording else 1.5
                
                logging.info(f"⏳ 等待 {thread_name} 停止... (錄製中: {is_recording})")
                thread.join(timeout=timeout)
                
                if thread.is_alive():
                    logging.warning(f"⚠️ {thread_name} 未能在{timeout}秒內停止")
                else:
                    logging.info(f"✅ {thread_name} 已停止")
            
            # 🧹 第四步：清理狀態標誌
            self.is_processing = False
            self.is_running = False
            
            # 清理活動線程標記
            if hasattr(self.camera_model, '_active_capture_thread'):
                self.camera_model._active_capture_thread = None
                
            logging.info("✅ 強制停止所有線程完成")
            
        except Exception as e:
            logging.error(f"❌ 強制停止錯誤: {str(e)}")
            # 即使出錯也要確保狀態正確
            self.is_processing = False
            self.is_running = False
    
    def disconnect_camera(self):
        """斷開相機"""
        self.force_stop_all()
        self.camera_model.disconnect()
        self.notify_views('system_status', '相機已斷開')
    
    def start_capture(self) -> bool:
        """開始捕獲/處理 - 根據當前模式"""
        try:
            logging.info(f"🚀 開始處理 - 模式: {self.current_mode}")
            
            if self.current_mode == 'live':
                # 實時模式：只啟動相機
                if not self.camera_model.is_connected:
                    self.notify_views('system_error', '請先連接相機')
                    return False
                
                success = self.camera_model.start_capture()
                if success:
                    self.is_running = True
                    self._start_processing()  # 啟動處理循環
                    self.notify_views('system_status', '實時處理已啟動')
                    logging.info("✅ 實時模式處理已啟動")
                else:
                    logging.error("❌ 實時模式相機啟動失敗")
                return success
                
            elif self.current_mode == 'recording':
                # 錄製模式：相機+錄製同時啟動
                if not self.camera_model.is_connected:
                    self.notify_views('system_error', '請先連接相機')
                    return False
                
                # 第一步：啟動相機
                camera_success = self.camera_model.start_capture()
                if not camera_success:
                    logging.error("❌ 錄製模式相機啟動失敗")
                    self.notify_views('system_error', '相機啟動失敗')
                    return False
                    
                # 第二步：啟動錄製（使用預設檔名）
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                default_filename = f"recording_{timestamp}"
                recording_success = self.camera_model.start_recording(default_filename)
                
                if recording_success:
                    self.is_running = True
                    self._start_processing()  # 啟動處理循環
                    self.notify_views('system_status', '錄製處理已啟動')
                    logging.info("✅ 錄製模式已啟動 - 相機+錄製+處理")
                    return True
                else:
                    # 錄製失敗，回滾相機
                    logging.error("❌ 錄製啟動失敗，停止相機")
                    self.camera_model.stop_capture()
                    self.notify_views('system_error', '錄製啟動失敗')
                    return False
                    
            elif self.current_mode == 'playback':
                # 回放模式：啟動視頻播放
                success = self.video_player.start_playback()
                if success:
                    self.is_running = True
                    self._start_processing()  # 啟動處理循環
                    self.notify_views('system_status', '回放處理已啟動')
                    logging.info("✅ 回放模式處理已啟動")
                else:
                    logging.error("❌ 回放模式啟動失敗")
                    self.notify_views('system_error', '視頻播放啟動失敗')
                return success
                
            else:
                logging.error(f"未知的模式: {self.current_mode}")
                self.notify_views('system_error', f'未知模式: {self.current_mode}')
                return False
                
        except Exception as e:
            logging.error(f"開始捕獲錯誤: {str(e)}")
            self.notify_views('system_error', f'處理啟動失敗: {str(e)}')
            return False
    
    def stop_capture(self):
        """停止捕獲/處理 - 根據當前模式"""
        try:
            logging.info(f"🛑 停止處理 - 模式: {self.current_mode}")
            
            # 首先停止處理循環
            if self.is_processing:
                self._stop_processing()
            
            if self.current_mode == 'live':
                # 實時模式：停止相機捕獲
                self.camera_model.stop_capture()
                self.notify_views('system_status', '實時處理已停止')
                logging.info("✅ 實時模式處理已停止")
                
            elif self.current_mode == 'recording':
                # 錄製模式：停止錄製+相機
                # 先停止錄製
                if self.camera_model.is_recording():
                    recording_info = self.camera_model.stop_recording()
                    if recording_info:
                        logging.info(f"✅ 錄製已完成: {recording_info.get('filename', 'unknown')}")
                
                # 再停止相機
                self.camera_model.stop_capture()
                self.notify_views('system_status', '錄製處理已停止')
                logging.info("✅ 錄製模式處理已停止")
                
            elif self.current_mode == 'playback':
                # 回放模式：停止視頻播放
                self.video_player.stop_playback()
                self.notify_views('system_status', '回放處理已停止')
                logging.info("✅ 回放模式處理已停止")
            
            # 重置運行狀態
            self.is_running = False
            
        except Exception as e:
            logging.error(f"停止捕獲錯誤: {str(e)}")
            self.notify_views('system_error', f'處理停止失敗: {str(e)}')
    
    # ==================== 檢測控制 ====================
    
    def set_detection_method(self, method_name: str) -> bool:
        """設置檢測方法"""
        return self.detection_model.set_detection_method(method_name)
    
    def update_detection_parameters(self, params: Dict[str, Any]) -> bool:
        """更新檢測參數"""
        return self.detection_model.update_parameters(params)
    
    def toggle_detection(self, enabled: bool):
        """開啟/關閉檢測"""
        try:
            success = self.detection_model.update_parameters({'enable_detection': enabled})
            if success:
                status = '檢測已開啟' if enabled else '檢測已關閉'
                self.notify_views('system_status', status)
                logging.info(f"✅ 檢測開關已設置為: {enabled}")
            else:
                logging.error(f"❌ 檢測參數更新失敗")
                self.notify_views('system_error', '檢測開關設置失敗')
        except Exception as e:
            logging.error(f"❌ 切換檢測開關時出錯: {str(e)}")
            self.notify_views('system_error', f'檢測開關錯誤: {str(e)}')
    
    def set_exposure_time(self, exposure_us: float) -> bool:
        """設置相機曝光時間"""
        return self.camera_model.set_exposure_time(exposure_us)
    
    def get_exposure_time(self) -> float:
        """獲取當前曝光時間"""
        return self.camera_model.get_exposure_time()
    
    def get_exposure_range(self) -> tuple:
        """獲取曝光時間範圍"""
        return self.camera_model.get_exposure_range()
    
    # ==================== 視頻錄製和回放控制 ====================
    
    def switch_mode(self, mode: str) -> bool:
        """切換系統模式：live, recording, playback - 改進版，避免過度清理"""
        try:
            if mode not in ['live', 'recording', 'playback']:
                logging.error(f"不支持的模式: {mode}")
                return False
            
            # 🔧 智能模式切換：只停止必要的組件
            if self.current_mode != mode:
                logging.info(f"🔄 從 {self.current_mode} 模式切換到 {mode} 模式")
                
                # 根據切換類型決定停止範圍
                if mode == 'playback':
                    # 切換到回放模式：只停止相機相關，保留視頻播放能力
                    if self.current_mode in ['live', 'recording']:
                        self._stop_camera_operations()
                    # 不調用 force_stop_all()，避免影響視頻播放器
                    
                elif mode in ['live', 'recording']:
                    # 切換到相機模式：可以安全停止所有操作
                    if self.current_mode == 'playback':
                        # 從回放模式切換，只需停止檢測處理器
                        if self.detection_processor.is_processing:
                            self.detection_processor.stop_processing()
                    else:
                        # 相機模式間切換，停止當前相機操作
                        self._stop_camera_operations()
                
                # 切換數據源類型
                if mode == 'playback':
                    # 🎯 視頻模式：先設置為基本視頻模式，實際參數將在video_loaded事件中優化
                    self.detection_model.set_source_type('video')
                    logging.info("🎬 已切換至視頻檢測模式，等待視頻加載後優化參數")
                else:
                    self.detection_model.set_source_type('camera')
                    logging.info("📷 已切換至相機檢測模式")
                
                self.current_mode = mode
                
                self.notify_views('mode_changed', {
                    'mode': mode,
                    'description': {
                        'live': '實時檢測模式',
                        'recording': '錄製模式',
                        'playback': '回放測試模式'
                    }.get(mode, mode)
                })
                
                logging.info(f"✅ 系統模式已切換為: {mode}")
            else:
                logging.info(f"💭 已在 {mode} 模式，無需切換")
            
            return True
            
        except Exception as e:
            logging.error(f"切換模式失敗: {str(e)}")
            return False
    
    def _stop_camera_operations(self):
        """只停止相機相關操作，保留其他功能"""
        try:
            logging.info("🎥 停止相機相關操作...")
            
            # 停止主處理循環
            if self.is_processing:
                self._stop_processing()
            
            # 停止相機捕獲
            if hasattr(self, 'camera_model') and self.camera_model:
                if self.camera_model.is_grabbing:
                    self.camera_model.stop_capture()
            
            # 停止錄製（如果在進行）
            if hasattr(self, 'video_recorder') and self.video_recorder:
                if self.video_recorder.is_recording:
                    self.video_recorder.stop_recording()
            
            logging.info("✅ 相機操作已停止")
            
        except Exception as e:
            logging.error(f"停止相機操作錯誤: {str(e)}")
    
    def start_recording(self, filename: str = None) -> bool:
        """開始錄製"""
        if self.current_mode not in ['live', 'recording']:
            self.notify_views('system_error', '請先切換到實時或錄製模式')
            return False
            
        if not self.camera_model.is_connected:
            self.notify_views('system_error', '請先連接相機')
            return False
            
        return self.camera_model.start_recording(filename)
    
    def stop_recording(self) -> dict:
        """停止錄製"""
        return self.camera_model.stop_recording()
    
    def is_recording(self) -> bool:
        """檢查是否正在錄製"""
        return self.camera_model.is_recording()
    
    def load_video(self, video_path: str) -> bool:
        """加載視頻用於回放"""
        success = self.video_player.load_video(video_path)
        
        if success:
            # 🚀 啟用高速檢測模式：盡快處理所有幀，不等待時間同步
            self.video_player.set_high_speed_detection_mode(True)
            
            # 🎯 設定檢測模型的影片信息，用於中間段照片保存
            video_info = self.video_player.video_info
            total_frames = video_info.get('total_frames', 0)
            fps = video_info.get('fps', 206)
            
            # 🚀🚀 206fps模式：簡化載入日誌
            logging.info(f"🎥 {total_frames}幀, {fps}fps - 高速模式")
            
            # 如果使用background檢測方法，設定影片信息
            if (hasattr(self.detection_model, 'method_name') and 
                self.detection_model.method_name == 'background'):
                try:
                    current_method = self.detection_model.current_method
                    if hasattr(current_method, 'set_video_info'):
                        current_method.set_video_info(total_frames, fps)
                        logging.info(f"📸 已設定影片信息用於中間段保存: {total_frames}幀, {fps:.1f}FPS")
                except Exception as e:
                    logging.warning(f"設定檢測模型影片信息失敗: {str(e)}")
        
        return success
    
    def set_playback_file(self, file_path: str) -> bool:
        """設置回放檔案路徑"""
        try:
            # 🎯 修復：確保切換到回放模式並加載視頻
            if self.current_mode != 'playback':
                success = self.switch_mode('playback')
                if not success:
                    logging.error("無法切換到回放模式")
                    return False
            
            # 加載視頻檔案
            success = self.load_video(file_path)
            if success:
                logging.info(f"✅ 視頻檔案已加載: {file_path}")
            else:
                logging.error(f"❌ 視頻檔案加載失敗: {file_path}")
            
            return success
            
        except Exception as e:
            logging.error(f"設置回放檔案失敗: {str(e)}")
            return False
    
    def start_video_playback(self) -> bool:
        """開始視頻回放"""
        # 🔧 診斷：檢查模式和視頻狀態
        if self.current_mode != 'playback':
            logging.error(f"❌ 視頻播放啟動失敗: 當前模式為 {self.current_mode}，需要切換到回放模式")
            self.notify_views('system_error', f'當前模式: {self.current_mode}，需要切換到回放模式')
            return False
        
        # 檢查視頻是否已加載
        if not hasattr(self.video_player, 'video_capture') or not self.video_player.video_capture:
            logging.error("❌ 視頻播放啟動失敗: 沒有視頻檔案已加載")
            self.notify_views('system_error', '請先選擇視頻檔案')
            return False
            
        success = self.video_player.start_playback()
        if not success:
            logging.error("❌ 視頻播放器啟動失敗")
            self.notify_views('system_error', '視頻播放器啟動失敗')
        else:
            logging.info("✅ 視頻播放已啟動")
        
        return success
    
    def pause_video_playback(self):
        """暫停/恢復視頻回放"""
        self.video_player.pause_playback()
    
    def stop_video_playback(self):
        """停止視頻回放"""
        self.video_player.stop_playback()
    
    def get_video_playback_status(self) -> dict:
        """獲取視頻播放狀態"""
        return self.video_player.get_playback_status()
    
    def seek_video_to_frame(self, frame_number: int) -> bool:
        """跳轉到指定幀"""
        return self.video_player.seek_to_frame(frame_number)
    
    def seek_video_to_progress(self, progress: float) -> bool:
        """根據進度跳轉（0.0-1.0）"""
        return self.video_player.seek_to_progress(progress)
    
    def set_playback_speed(self, speed: float):
        """設置播放速度"""
        self.video_player.set_playback_speed(speed)
    
    def get_current_video_info(self) -> Dict[str, Any]:
        """獲取當前視頻的實際規格信息"""
        if self.current_mode == 'playback' and hasattr(self.video_player, 'video_info'):
            return self.video_player.video_info.copy()
        return {}
    
    def refresh_video_detection_params(self) -> bool:
        """刷新視頻檢測參數（手動調用）"""
        if self.current_mode == 'playback':
            video_info = self.get_current_video_info()
            if video_info:
                success = self.detection_model.set_source_type('video', video_info)
                logging.info(f"🔄 手動刷新視頻檢測參數: {'success' if success else 'failed'}")
                return success
        return False
    
    def get_recorded_files(self) -> list:
        """獲取已錄製的文件列表"""
        return self.video_recorder.get_recorded_files()
    
    # ==================== 錄製品質驗證 ====================
    
    def _auto_validate_latest_recording(self, recording_data: Dict[str, Any]):
        """自動驗證最新完成的錄製檔案"""
        try:
            filename = recording_data.get('filename', '')
            file_path = recording_data.get('file_path', '')
            
            if not file_path:
                logging.warning("無法驗證錄製檔案：缺少檔案路徑")
                return
            
            logging.info(f"🔍 開始驗證錄製檔案: {filename}")
            
            # 使用錄製驗證器檢查檔案
            from pathlib import Path
            validation_result = self.recording_validator.validate_recording(Path(file_path))
            
            if validation_result:
                # 通知視圖驗證結果
                self.notify_views('recording_validated', {
                    'filename': filename,
                    'file_path': file_path,
                    'validation_result': validation_result,
                    'is_valid_fps': validation_result.is_valid_fps,
                    'actual_fps': validation_result.fps,
                    'expected_fps': self.recording_validator.expected_fps,
                    'fps_error': validation_result.fps_error_percent
                })
                
                # 記錄驗證結果
                if validation_result.is_valid_fps:
                    logging.info(f"✅ 錄製驗證通過: {filename} - {validation_result.fps:.1f} fps (誤差: {validation_result.fps_error_percent:.1f}%)")
                else:
                    logging.warning(f"⚠️ 錄製驗證警告: {filename} - {validation_result.fps:.1f} fps (誤差: {validation_result.fps_error_percent:.1f}%)")
            else:
                logging.error(f"❌ 錄製驗證失敗: {filename}")
                self.notify_views('recording_validation_failed', {
                    'filename': filename,
                    'file_path': file_path,
                    'error': '無法讀取檔案資訊'
                })
                
        except Exception as e:
            logging.error(f"錄製驗證過程中發生錯誤: {str(e)}")
    
    def validate_recording_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """手動驗證指定的錄製檔案"""
        try:
            from pathlib import Path
            validation_result = self.recording_validator.validate_recording(Path(file_path))
            
            if validation_result:
                return {
                    'file_name': validation_result.file_name,
                    'file_path': validation_result.file_path,
                    'fps': validation_result.fps,
                    'is_valid_fps': validation_result.is_valid_fps,
                    'fps_error_percent': validation_result.fps_error_percent,
                    'frame_count': validation_result.frame_count,
                    'duration': validation_result.duration,
                    'resolution': f"{validation_result.width}x{validation_result.height}",
                    'codec': validation_result.codec,
                    'file_size_mb': validation_result.file_size_mb
                }
            return None
            
        except Exception as e:
            logging.error(f"驗證檔案時發生錯誤: {str(e)}")
            return None
    
    def validate_all_recordings(self) -> List[Dict[str, Any]]:
        """驗證所有錄製檔案"""
        try:
            from pathlib import Path
            recordings_dir = Path("basler_mvc/recordings")
            
            all_recordings = self.recording_validator.validate_all_recordings(recordings_dir)
            
            # 轉換為字典格式供UI使用
            results = []
            for recording in all_recordings:
                results.append({
                    'file_name': recording.file_name,
                    'file_path': recording.file_path,
                    'fps': recording.fps,
                    'is_valid_fps': recording.is_valid_fps,
                    'fps_error_percent': recording.fps_error_percent,
                    'frame_count': recording.frame_count,
                    'duration': recording.duration,
                    'resolution': f"{recording.width}x{recording.height}",
                    'codec': recording.codec,
                    'file_size_mb': recording.file_size_mb,
                    'status': 'valid' if recording.is_valid_fps else 'invalid'
                })
            
            return results
            
        except Exception as e:
            logging.error(f"批量驗證錄製檔案時發生錯誤: {str(e)}")
            return []
    
    def get_recording_quality_summary(self) -> Dict[str, Any]:
        """獲取錄製品質總結"""
        try:
            from pathlib import Path
            recordings_dir = Path("basler_mvc/recordings")
            
            all_recordings = self.recording_validator.validate_all_recordings(recordings_dir)
            summary = self.recording_validator.get_quality_summary(all_recordings)
            
            # 添加詳細分析
            summary['recommendations'] = []
            
            if summary['invalid_fps_files'] > 0:
                summary['recommendations'].append({
                    'type': 'warning',
                    'message': f"發現 {summary['invalid_fps_files']} 個FPS不符合280目標的檔案",
                    'action': '檢查攝影機設定和系統效能'
                })
            
            if summary['validity_rate'] < 80:
                summary['recommendations'].append({
                    'type': 'critical',
                    'message': f"錄製品質較低 ({summary['validity_rate']:.1f}%)",
                    'action': '建議檢查整體系統配置'
                })
            elif summary['validity_rate'] == 100:
                summary['recommendations'].append({
                    'type': 'success',
                    'message': '所有錄製檔案品質優良',
                    'action': '繼續保持當前設定'
                })
            
            return summary
            
        except Exception as e:
            logging.error(f"獲取錄製品質總結時發生錯誤: {str(e)}")
            return {
                'total_files': 0,
                'valid_fps_files': 0,
                'invalid_fps_files': 0,
                'validity_rate': 0.0,
                'avg_fps': 0.0,
                'fps_range': (0.0, 0.0),
                'recommendations': [{
                    'type': 'error',
                    'message': '無法獲取錄製品質資訊',
                    'action': '檢查錄製目錄是否存在'
                }]
            }
    
    def quick_fps_check(self, file_path: str) -> Tuple[bool, float]:
        """快速檢查檔案FPS是否符合280目標"""
        try:
            from pathlib import Path
            return self.recording_validator.quick_fps_check(Path(file_path))
        except Exception as e:
            logging.error(f"快速FPS檢查失敗: {str(e)}")
            return False, 0.0
    
    def get_video_player_status(self) -> dict:
        """獲取視頻播放狀態"""
        return self.video_player.get_playback_status()
    
    def get_current_mode(self) -> str:
        """獲取當前系統模式"""
        return self.current_mode
    
    # ==================== 批次檢測控制 ====================
    
    def start_batch_detection(self):
        """開始批次檢測模式 - 支持視頻回放模式"""
        try:
            # 🎯 優化：根據模式啟動不同的檢測處理器
            if self.current_mode == 'playback':
                # 🎯 視頻回放模式：使用非同步模式避免提交失敗
                if not self.detection_processor.is_processing:
                    # 🎯 修復：使用非同步模式，提高視頻回放流暢度
                    self.detection_processor.set_sync_mode(False)
                    self.detection_processor.start_processing()
                    logging.info("✅ 視頻回放非同步檢測已啟動（避免幀提交失敗）")
                else:
                    # 確保已在運行的處理器也是非同步模式
                    self.detection_processor.set_sync_mode(False)
                    logging.info("🔄 視頻回放檢測處理器已在運行（切換為非同步模式）")
                return True
                
            elif self.current_mode == 'live':
                # 📹 實時相機模式：啟動高速相機處理
                # 設置檢測處理器為異步模式（相機實時性能）
                self.detection_processor.set_sync_mode(False)
                
                if not self.is_processing:
                    self._start_processing()
                    logging.info("✅ 相機批次檢測已啟動（異步模式）")
                else:
                    logging.info("🔄 相機檢測處理已在運行")
                return True
                
            else:
                logging.warning(f"不支持的模式: {self.current_mode}")
                return False
            
        except Exception as e:
            logging.error(f"啟動批次檢測錯誤: {str(e)}")
            return False
    
    def stop_batch_detection(self):
        """停止批次檢測模式 - 正確的線程清理版本"""
        try:
            logging.info(f"🛑 開始停止批次檢測 (模式: {self.current_mode})")
            
            # 🎯 關鍵修復：根據模式停止不同的檢測處理器
            if self.current_mode == 'playback':
                # 視頻回放模式：只停止檢測處理器，保持視頻播放繼續
                if self.detection_processor.is_processing:
                    self.detection_processor.stop_processing()
                    logging.info("⏹️ 視頻回放批次檢測已停止 - 視頻播放繼續")
                else:
                    logging.info("💭 視頻回放檢測處理器未運行")
                # 🔧 重要：不要停止視頻播放器，讓用戶繼續控制視頻
                return True
                
            elif self.current_mode == 'live':
                # 🔧 實時相機模式：必須停止相機捕獲線程
                success = True
                
                # 停止相機捕獲
                if self.camera_model and self.camera_model.is_grabbing:
                    logging.info("🎥 停止相機捕獲線程...")
                    self.camera_model.stop_capture()
                    
                    # 🔧 確認捕獲是否真正停止
                    import time
                    time.sleep(0.5)  # 給線程時間清理
                    
                    if self.camera_model.is_grabbing:
                        logging.warning("⚠️ 相機捕獲未完全停止")
                        success = False
                    else:
                        logging.info("✅ 相機捕獲已完全停止")
                else:
                    logging.info("💭 相機捕獲未在運行")
                
                # 停止主處理循環
                if self.is_processing:
                    logging.info("🔄 停止主處理循環...")
                    self._stop_processing()
                
                if success:
                    logging.info("✅ 實時模式批次檢測已完全停止")
                else:
                    logging.error("❌ 實時模式停止存在問題")
                
                return success
                
            else:
                logging.warning(f"不支持的模式: {self.current_mode}")
                return False
            
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
                    pass  # 🚀🚀 206fps模式：移除所有延遲
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
                
                # 🚀🚀 真實206fps模式：移除所有人工限制
                should_notify = True  # 每幀都通知，不限制更新頻率
                
                if should_notify:
                    # 🎯 包裝計數系統：檢測物件數量 + ROI穿越計數 + 包裝邏輯
                    frame_object_count = len(objects)  # 每幀檢測物件數
                    total_crossing_count = 0  # 累加穿越計數
                    
                    # 如果使用background方法，獲取ROI穿越計數
                    if (hasattr(self.detection_model, 'method_name') and 
                        self.detection_model.method_name == 'background'):
                        try:
                            current_method = self.detection_model.current_method
                            if hasattr(current_method, 'get_crossing_count'):
                                total_crossing_count = current_method.get_crossing_count()
                                
                                # 🔍 調試：每20幀記錄一次穿越計數
                                if self.total_processed_frames % 20 == 0:
                                    logging.debug(f"🎯 穿越計數: {total_crossing_count}, 檢測物件: {frame_object_count}")
                                
                                # 🎯 更新包裝計數系統
                                self._update_package_counting(total_crossing_count)
                                
                        except Exception as count_error:
                            logging.debug(f"獲取穿越計數錯誤: {str(count_error)}")
                    
                    self.notify_views('frame_processed', {
                        'frame': result_frame,
                        'objects': objects,
                        'object_count': frame_object_count,  # 右側面板顯示每幀物件數
                        'crossing_count': total_crossing_count,  # 影像中顯示累加計數
                        'total_detected_count': self.total_detected_count,  # 當前計數：總累計
                        'current_segment_count': self.current_segment_count,  # 目前計數：當前段數量
                        'package_count': self.package_count,  # 包裝數
                        'processing_fps': self.processing_fps,
                        'detection_fps': getattr(self.detection_model, 'detection_fps', 0),
                        'method_name': getattr(self.detection_model, 'method_name', 'unknown')
                    })
                    
                    # 第一幀日誌
                    if self.total_processed_frames == 1:
                        logging.info(f"✅ 處理第一幀成功，高性能模式啟動")
                
                # 🚀 完全移除延遲，追求極致性能
                # 不添加任何sleep以達到最高FPS
                
            except Exception as e:
                logging.error(f"處理循環錯誤: {str(e)}")
                pass  # 🚀🚀 206fps模式：移除錯誤延遲
    
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
        """獲取系統狀態 - 根據模式返回不同狀態"""
        detection_stats = self.detection_model.get_stats()
        elapsed_time = time.time() - self.processing_start_time if self.processing_start_time else 0
        avg_processing_fps = self.total_processed_frames / elapsed_time if elapsed_time > 0 else 0
        
        # 基本系統狀態
        base_status = {
            # 系統狀態
            'current_mode': self.current_mode,  # 🎯 關鍵添加：當前模式
            'is_running': self.is_running,
            'is_processing': self.is_processing,
            
            # 處理統計
            'processing_fps': self.processing_fps,
            'processing_avg_fps': avg_processing_fps,
            'processing_total_frames': self.total_processed_frames,
            
            # 檢測統計
            'detection_fps': detection_stats.get('detection_fps', 0),
            'object_count': detection_stats.get('object_count', 0),
            'detection_method': detection_stats.get('current_method', 'unknown'),
            
            # 時間
            'elapsed_time': elapsed_time
        }
        
        # 🎯 根據模式添加專用狀態
        if self.current_mode == 'playback':
            # 視頻回放模式：添加視頻狀態
            video_status = self.video_player.get_playback_status()
            processor_stats = self.detection_processor.get_stats()
            
            base_status.update({
                # 視頻相關狀態
                'video_fps': video_status.get('fps', 0),
                'playback_fps': video_status.get('playback_fps', 0),
                'video_progress': video_status.get('progress', 0),
                'current_frame': video_status.get('current_frame', 0),
                'total_frames': video_status.get('total_frames', 0),
                # 🎯 新增時間軸信息用於狀態顯示
                'video_duration': video_status.get('video_duration', 0),
                'current_time': video_status.get('current_time', 0),
                'time_format': video_status.get('time_format', '00:00 / 00:00'),
                'is_playing': video_status.get('is_playing', False),
                'is_paused': video_status.get('is_paused', False),
                # 🎬 新增視頻規格信息用於參考
                'video_info': video_status.get('video_info', {}),
                
                # 視頻檢測處理器狀態
                'video_processing_fps': processor_stats.get('detection_fps', 0),
                'frame_queue_size': processor_stats.get('frame_queue_size', 0),
                'result_queue_size': processor_stats.get('result_queue_size', 0),
                'total_frames_processed': processor_stats.get('total_frames_processed', 0),
                
                # 相機狀態設為0（回放模式不使用相機）
                'camera_fps': 0,
                'camera_avg_fps': 0,
                'camera_total_frames': 0,
                'is_connected': False,
                'is_grabbing': False,
                'camera_info': {}
            })
        else:
            # 實時相機模式：添加相機狀態
            camera_stats = self.camera_model.get_stats()
            camera_info = self.camera_model.get_camera_info()
            
            base_status.update({
                # 相機相關狀態
                'is_connected': self.camera_model.is_connected,
                'is_grabbing': self.camera_model.is_grabbing,
                'camera_fps': camera_stats.get('current_fps', 0),
                'camera_avg_fps': camera_stats.get('average_fps', 0),
                'camera_total_frames': camera_stats.get('total_frames', 0),
                'camera_info': camera_info,
                
                # 視頻狀態設為0（相機模式不使用視頻）
                'video_fps': 0,
                'playback_fps': 0,
                'video_progress': 0,
                'current_frame': 0,
                'total_frames': 0,
                'is_playing': False,
                'is_paused': False
            })
        
        return base_status
    
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
    
    def _on_memory_warning(self, memory_info: Dict[str, Any]):
        """記憶體警告回調"""
        memory_mb = memory_info['rss_bytes'] / (1024 * 1024)
        logging.warning(f"⚠️ 記憶體使用警告: {memory_mb:.1f}MB")
        
        # 通知UI
        self.notify_views('memory_warning', {
            'memory_mb': memory_mb,
            'memory_percent': memory_info['percent'],
            'available_mb': memory_info['available_mb']
        })
        
        # 自動清理建議
        if hasattr(self, 'detection_processor'):
            queue_status = self.detection_processor.get_queue_status()
            if queue_status['frame_queue_size'] > 10:
                logging.info("🧹 建議：清理檢測處理器隊列")
        
        # 強制垃圾回收
        if hasattr(self, 'memory_monitor'):
            gc_result = self.memory_monitor.force_gc()
            if gc_result['memory_freed_mb'] > 1.0:
                logging.info(f"🧹 垃圾回收釋放了 {gc_result['memory_freed_mb']:.1f}MB")
    
    def _on_memory_critical(self, memory_info: Dict[str, Any]):
        """記憶體緊急警告回調"""
        memory_mb = memory_info['rss_bytes'] / (1024 * 1024)
        logging.error(f"🚨 記憶體使用緊急警告: {memory_mb:.1f}MB")
        
        # 通知UI緊急狀況
        self.notify_views('memory_critical', {
            'memory_mb': memory_mb,
            'memory_percent': memory_info['percent'],
            'available_mb': memory_info['available_mb']
        })
        
        # 緊急措施：暫停處理
        if self.is_processing:
            logging.warning("🛑 記憶體不足，暫停處理")
            self.stop_capture()
            
        # 強制清理
        if hasattr(self, 'detection_processor'):
            self.detection_processor._clear_queues()
            logging.info("🧹 緊急清理檢測處理器隊列")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """獲取記憶體統計信息"""
        if hasattr(self, 'memory_monitor'):
            return self.memory_monitor.get_memory_stats()
        else:
            return {'error': '記憶體監控器未初始化'}
    
    def cleanup(self):
        """清理資源 - 增強版本"""
        try:
            logging.info("開始清理控制器資源...")
            
            # 停止系統
            self.stop_system()
            
            # 斷開相機
            self.disconnect_camera()
            
            # 🔍 停止記憶體監控
            if hasattr(self, 'memory_monitor'):
                self.memory_monitor.cleanup()
            
            # 🧹 清理檢測處理器
            if hasattr(self, 'detection_processor'):
                self.detection_processor.cleanup()
            
            # 清理觀察者列表
            if hasattr(self, 'view_observers'):
                self.view_observers.clear()
            
            logging.info("控制器資源清理完成")
        except Exception as e:
            logging.error(f"清理資源錯誤: {str(e)}")
    
    # ==================== 調試分析功能 ====================
    
    def enable_debug_image_save(self, enabled: bool = True):
        """啟用或禁用調試圖片保存功能"""
        try:
            detection_method = self.detection_model.get_detection_method()
            if hasattr(detection_method, 'enable_debug_save'):
                detection_method.enable_debug_save(enabled)
                
                action = "啟用" if enabled else "禁用"
                self.notify_views('debug_save_status', {
                    'enabled': enabled,
                    'message': f"調試圖片保存已{action}"
                })
                
                logging.info(f"📸 調試圖片保存已{action}")
                return True
            else:
                logging.warning("當前檢測方法不支援調試圖片保存")
                return False
                
        except Exception as e:
            logging.error(f"設置調試圖片保存錯誤: {str(e)}")
            return False
    
    def get_debug_status(self) -> Dict[str, Any]:
        """獲取調試狀態信息"""
        try:
            detection_method = self.detection_model.get_detection_method()
            if hasattr(detection_method, 'get_debug_info'):
                return detection_method.get_debug_info()
            else:
                return {
                    'debug_enabled': False,
                    'frames_saved': 0,
                    'max_frames': 0,
                    'save_directory': '',
                    'error': '當前檢測方法不支援調試功能'
                }
        except Exception as e:
            logging.error(f"獲取調試狀態錯誤: {str(e)}")
            return {'error': str(e)}
    
    def clear_debug_images(self):
        """清理調試圖片"""
        try:
            detection_method = self.detection_model.get_detection_method()
            if hasattr(detection_method, '_cleanup_debug_folder'):
                detection_method._cleanup_debug_folder()
                logging.info("🗑️ 調試圖片已清理")
                return True
            else:
                logging.warning("當前檢測方法不支援調試圖片清理")
                return False
        except Exception as e:
            logging.error(f"清理調試圖片錯誤: {str(e)}")
            return False
    
    def trigger_manual_debug_save(self):
        """手動觸發調試圖片保存 - 用於捕捉特定畫面"""
        try:
            detection_method = self.detection_model.get_detection_method()
            if hasattr(detection_method, 'trigger_manual_save'):
                detection_method.trigger_manual_save()
                logging.info("🔧 手動觸發調試保存")
                return True
            else:
                logging.warning("當前檢測方法不支援手動觸發保存")
                return False
        except Exception as e:
            logging.error(f"手動觸發調試保存錯誤: {str(e)}")
            return False
    
    def set_debug_start_frame(self, start_frame: int = 2500):
        """設定調試圖片保存的起始幀"""
        try:
            detection_method = self.detection_model.get_detection_method()
            if hasattr(detection_method, 'set_custom_start_frame'):
                detection_method.set_custom_start_frame(start_frame)
                
                self.notify_views('debug_start_frame_set', {
                    'start_frame': start_frame,
                    'message': f"調試圖片將從第{start_frame}幀開始保存"
                })
                
                logging.info(f"🎯 調試保存起始幀已設定: {start_frame}")
                return True
            else:
                logging.warning("當前檢測方法不支援設定起始幀")
                return False
        except Exception as e:
            logging.error(f"設定調試起始幀錯誤: {str(e)}")
            return False
    
    def cleanup_early_debug_images(self, before_frame: int = None):
        """清理指定幀數之前的調試圖片"""
        try:
            detection_method = self.detection_model.get_detection_method()
            if hasattr(detection_method, 'cleanup_early_debug_images'):
                deleted_count = detection_method.cleanup_early_debug_images(before_frame)
                
                self.notify_views('early_debug_cleaned', {
                    'deleted_count': deleted_count,
                    'before_frame': before_frame or 2500,
                    'message': f"已清理{deleted_count}個早期調試圖片"
                })
                
                logging.info(f"🗑️ 已清理{deleted_count}個早期調試圖片")
                return deleted_count
            else:
                logging.warning("當前檢測方法不支援清理調試圖片")
                return 0
        except Exception as e:
            logging.error(f"清理早期調試圖片錯誤: {str(e)}")
            return 0
    
    def apply_small_component_optimization(self, start_frame: int = 2500, cleanup_early_images: bool = True):
        """應用小零件檢測優化設置
        
        Args:
            start_frame: 調試圖片保存起始幀數 (預設2500)
            cleanup_early_images: 是否清理早期調試圖片 (預設True)
        """
        try:
            logging.info(f"🎯 開始應用小零件檢測優化...")
            
            # 1. 設定調試圖片起始幀
            success = self.set_debug_start_frame(start_frame)
            if success:
                logging.info(f"✅ 已設定調試圖片從第{start_frame}幀開始保存")
            
            # 2. 清理早期調試圖片 (如果需要)
            if cleanup_early_images:
                deleted_count = self.cleanup_early_debug_images(start_frame)
                if deleted_count > 0:
                    logging.info(f"✅ 已清理{deleted_count}個第{start_frame}幀之前的調試圖片")
            
            # 3. 通知UI優化已完成
            self.notify_views('small_component_optimization_applied', {
                'start_frame': start_frame,
                'cleanup_performed': cleanup_early_images,
                'deleted_count': deleted_count if cleanup_early_images else 0,
                'message': f"小零件檢測優化已應用 - 從第{start_frame}幀開始保存調試圖片"
            })
            
            logging.info("✅ 小零件檢測優化設置完成")
            logging.info("📋 優化內容:")
            logging.info("   - 增大追蹤容差適應小零件移動")
            logging.info("   - 降低最小追蹤幀數要求 (3→2)")
            logging.info("   - 降低移動像素要求 (10→3)")
            logging.info("   - 降低穿越和置信度閾值")
            logging.info(f"   - 調試圖片從第{start_frame}幀開始保存")
            
            return True
            
        except Exception as e:
            logging.error(f"應用小零件檢測優化錯誤: {str(e)}")
            self.notify_views('system_error', f'小零件檢測優化失敗: {str(e)}')
            return False
    
    # ==================== 🚀 超高速檢測模式 ====================
    
    def enable_ultra_high_speed_detection(self, enabled: bool = True, target_fps: int = None):
        """啟用超高速檢測模式 - 專為206-376fps設計"""
        # 🚀 根據相機規格自動設定目標FPS
        if target_fps is None:
            # 根據相機模型推斷最適FPS
            if hasattr(self.camera_model, 'current_fps') and self.camera_model.current_fps > 0:
                # 使用當前相機FPS作為目標，檢測速度比相機快15%
                target_fps = int(self.camera_model.current_fps * 1.15)
            else:
                # 預設使用280fps (中等規格)
                target_fps = 280
        
        # 🔧 確保檢測FPS高於影像FPS
        if target_fps < 200:
            target_fps = 280  # 最低280fps以確保性能
        
        self.detection_model.enable_ultra_high_speed_mode(enabled, target_fps)
        
        if enabled:
            logging.info(f"🚀 主控制器啟用超高速檢測 - 目標: {target_fps}fps")
            # 🔧 自動關閉不必要的功能以提升性能
            self._optimize_for_high_speed()
        else:
            logging.info("🔧 主控制器禁用超高速檢測，恢復標準模式")
            self._restore_standard_mode()
    
    def _optimize_for_high_speed(self):
        """為高速模式優化系統設置"""
        try:
            # 🚀 減少記憶體監控頻率以節省性能
            if hasattr(self.memory_monitor, 'check_interval'):
                self.memory_monitor.check_interval = 60.0  # 從30秒改為60秒
            
            # 🚀 暫停不必要的設備監控
            if hasattr(self.camera_model, 'device_monitor_enabled'):
                self.camera_model.device_monitor_enabled = False
                
            logging.info("🚀 系統已優化以支援超高速檢測")
        except Exception as e:
            logging.warning(f"高速優化設置部分失敗: {str(e)}")
    
    def _restore_standard_mode(self):
        """恢復標準模式設置"""
        try:
            # 🔧 恢復記憶體監控頻率
            if hasattr(self.memory_monitor, 'check_interval'):
                self.memory_monitor.check_interval = 30.0
            
            # 🔧 恢復設備監控
            if hasattr(self.camera_model, 'device_monitor_enabled'):
                self.camera_model.device_monitor_enabled = True
                
            logging.info("🔧 系統已恢復標準模式設置")
        except Exception as e:
            logging.warning(f"標準模式恢復部分失敗: {str(e)}")
    
    def is_ultra_high_speed_enabled(self) -> bool:
        """檢查是否啟用超高速模式"""
        return self.detection_model.is_ultra_high_speed_enabled()
    
    def auto_configure_detection_speed(self):
        """根據相機規格自動配置檢測速度"""
        try:
            if hasattr(self.camera_model, 'current_fps') and self.camera_model.current_fps > 0:
                camera_fps = self.camera_model.current_fps
                
                # 🚀 自動判斷是否需要高速模式
                if camera_fps >= 200:  # 高速相機
                    # 檢測FPS應該比相機FPS高15%以確保每幀都被處理
                    target_detection_fps = int(camera_fps * 1.15)
                    self.enable_ultra_high_speed_detection(True, target_detection_fps)
                    logging.info(f"🚀 檢測到高速相機({camera_fps:.1f}fps)，自動啟用超高速檢測模式")
                else:
                    # 低速相機使用標準模式
                    self.enable_ultra_high_speed_detection(False)
                    logging.info(f"🎯 檢測到標準相機({camera_fps:.1f}fps)，使用標準檢測模式")
            else:
                logging.warning("⚠️ 無法獲取相機FPS，使用預設檢測模式")
        except Exception as e:
            logging.error(f"自動配置檢測速度失敗: {str(e)}")
    
    def get_detection_speed_info(self) -> Dict[str, Any]:
        """獲取檢測速度相關信息"""
        try:
            detection_stats = self.detection_model.get_stats()
            is_high_speed = self.is_ultra_high_speed_enabled()
            
            camera_fps = getattr(self.camera_model, 'current_fps', 0)
            detection_fps = detection_stats.get('detection_fps', 0)
            
            # 計算性能比率
            speed_ratio = detection_fps / camera_fps if camera_fps > 0 else 0
            
            return {
                'ultra_high_speed_enabled': is_high_speed,
                'camera_fps': camera_fps,
                'detection_fps': detection_fps,
                'speed_ratio': speed_ratio,
                'performance_grade': self._get_speed_grade(speed_ratio, camera_fps),
                'ultra_high_speed_status': detection_stats.get('ultra_high_speed', {}),
                'recommendations': self._get_speed_recommendations(camera_fps, detection_fps, is_high_speed)
            }
        except Exception as e:
            logging.error(f"獲取檢測速度信息錯誤: {str(e)}")
            return {'error': str(e)}
    
    def _get_speed_grade(self, ratio: float, camera_fps: float) -> str:
        """獲取速度等級評分"""
        if camera_fps >= 300:  # 超高速相機
            if ratio >= 1.1:
                return "🏆 卓越 (適用376fps)"
            elif ratio >= 1.05:
                return "🎉 優秀"
            else:
                return "⚠️ 需要啟用超高速模式"
        elif camera_fps >= 200:  # 高速相機
            if ratio >= 1.1:
                return "🏆 卓越 (適用280fps)"
            elif ratio >= 1.0:
                return "✅ 良好"
            else:
                return "⚠️ 建議啟用高速模式"
        else:  # 標準相機
            if ratio >= 1.0:
                return "✅ 良好 (適用206fps)"
            else:
                return "🔧 標準模式即可"
    
    def _get_speed_recommendations(self, camera_fps: float, detection_fps: float, is_high_speed: bool) -> List[str]:
        """獲取速度優化建議"""
        recommendations = []
        
        if camera_fps >= 300 and not is_high_speed:
            recommendations.append("🚀 建議啟用376fps超高速模式")
        elif camera_fps >= 250 and not is_high_speed:
            recommendations.append("🚀 建議啟用280fps高速模式")
        elif camera_fps >= 200 and not is_high_speed:
            recommendations.append("🚀 建議啟用206fps模式")
        
        if detection_fps < camera_fps:
            recommendations.append("⚠️ 檢測速度低於相機速度，可能丟幀")
        
        if is_high_speed and camera_fps < 150:
            recommendations.append("🔧 相機速度較低，可考慮使用標準模式")
            
        return recommendations

    def __del__(self):
        """析構函數 - 安全版本"""
        try:
            self.cleanup()
        except:
            # 忽略析構時的所有異常，避免程序崩潰
            pass