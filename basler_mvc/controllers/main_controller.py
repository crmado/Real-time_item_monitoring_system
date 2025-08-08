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
from ..models.video_recorder_model import VideoRecorderModel
from ..models.video_player_model import VideoPlayerModel
from ..models.detection_processor import DetectionProcessor


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
        
        # 🚀 高性能檢測處理器（專用於視頻回放）
        self.detection_processor = DetectionProcessor(self.detection_model)
        
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
        self.frame_times = deque(maxlen=100)
        
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
    
    def _on_video_recorder_event(self, event_type: str, data: Any = None):
        """處理視頻錄製事件"""
        # 轉發到視圖
        self.notify_views(f"recorder_{event_type}", data)
        
        if event_type == 'recording_started':
            logging.info(f"錄製開始: {data.get('filename', 'unknown')}")
        elif event_type == 'recording_stopped':
            logging.info(f"錄製完成: {data.get('frames_recorded', 0)} 幀")
    
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
            
            # 非阻塞提交（確保不丟幀）
            success = self.detection_processor.submit_frame(frame, frame_info)
            
            if not success:
                logging.warning(f"幀 {frame_info['frame_number']} 提交失敗")
            
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
        """強制停止所有線程和連接 - 強化版本，防止線程競爭"""
        try:
            logging.info("🛑 開始強制停止所有系統組件...")
            
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
            
            # 等待所有線程停止
            for thread_name, thread in threads_to_wait:
                logging.info(f"⏳ 等待 {thread_name} 停止...")
                thread.join(timeout=1.5)  # 每個線程最多等1.5秒
                
                if thread.is_alive():
                    logging.warning(f"⚠️ {thread_name} 未能及時停止")
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
    
    # ==================== 視頻錄製和回放控制 ====================
    
    def switch_mode(self, mode: str) -> bool:
        """切換系統模式：live, recording, playback"""
        try:
            if mode not in ['live', 'recording', 'playback']:
                logging.error(f"不支持的模式: {mode}")
                return False
            
            # 停止當前操作
            self.force_stop_all()
            
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
            
            logging.info(f"系統模式已切換為: {mode}")
            return True
            
        except Exception as e:
            logging.error(f"切換模式失敗: {str(e)}")
            return False
    
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
        return self.video_player.load_video(video_path)
    
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
        if self.current_mode != 'playback':
            self.notify_views('system_error', '請先切換到回放模式')
            return False
            
        return self.video_player.start_playback()
    
    def pause_video_playback(self):
        """暫停/恢復視頻回放"""
        self.video_player.pause_playback()
    
    def stop_video_playback(self):
        """停止視頻回放"""
        self.video_player.stop_playback()
    
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
        """停止批次檢測模式 - 支持視頻回放模式"""
        try:
            # 🎯 關鍵修復：根據模式停止不同的檢測處理器
            if self.current_mode == 'playback':
                # 視頻回放模式：停止檢測處理器
                if self.detection_processor.is_processing:
                    self.detection_processor.stop_processing()
                    logging.info("⏹️ 視頻回放批次檢測已停止")
                else:
                    logging.info("💭 視頻回放檢測處理器未運行")
                return True
                
            elif self.current_mode == 'live':
                # 實時相機模式：無需特殊處理（相機持續運行）
                logging.info("⏹️ 相機批次檢測模式已停止")
                return True
                
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
                
                # 🚀 極速模式：降低通知頻率提升性能
                should_notify = (
                    self.total_processed_frames == 1 or  # 第一幀
                    self.total_processed_frames % 5 == 0  # 每5幀通知一次（大幅減少UI更新）
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