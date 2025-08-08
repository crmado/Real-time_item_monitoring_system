"""
Basler 相機 Model - MVC 架構核心
專注於 Basler acA640-300gm 相機的數據管理和業務邏輯
"""

import logging
import threading
import time
import queue
import numpy as np
import cv2
from typing import Optional, Dict, Any, Callable
from collections import deque

try:
    from pypylon import pylon
    PYLON_AVAILABLE = True
    logging.info("pypylon 模塊加載成功")
except ImportError:
    PYLON_AVAILABLE = False
    logging.error("pypylon 未安裝")


class BaslerCameraModel:
    """Basler 相機數據模型 - 高性能版本"""
    
    def __init__(self):
        """初始化相機模型"""
        if not PYLON_AVAILABLE:
            raise RuntimeError("pypylon 未安裝，請執行: pip install pypylon")
            
        # 相機核心
        self.camera = None
        self.is_connected = False
        self.is_grabbing = False
        
        # 高性能多線程架構
        self.stop_event = threading.Event()
        self.frame_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        
        # 數據緩衝
        self.latest_frame = None
        self.frame_queue = queue.Queue(maxsize=3)  # 減少緩存以降低記憶體使用
        
        # 性能統計 - 🎯 優化FPS計算準確性
        self.total_frames = 0
        self.start_time = None
        self.current_fps = 0.0
        # 🎯 減少窗口大小，使用最近60幀計算更準確的實時FPS（約2秒窗口@280fps）
        self.frame_times = deque(maxlen=60)
        
        # 相機資訊
        self.camera_info = {}
        
        # 視頻錄製功能
        self.video_recorder = None  # 外部注入的錄製器
        self.recording_enabled = False
        
        # 觀察者模式 - 通知 View 更新
        self.observers = []
        
        logging.info("Basler 相機模型初始化完成")
        
    def set_exposure_time(self, exposure_us: float) -> bool:
        """動態設置曝光時間（微秒）"""
        try:
            if not self.camera or not self.is_connected:
                logging.error("相機未連接，無法設置曝光時間")
                return False
            
            # 設置曝光時間
            if hasattr(self.camera, 'ExposureTimeAbs'):
                # 檢查範圍
                min_exposure = self.camera.ExposureTimeAbs.GetMin()
                max_exposure = self.camera.ExposureTimeAbs.GetMax()
                
                if exposure_us < min_exposure or exposure_us > max_exposure:
                    logging.warning(f"曝光時間 {exposure_us}us 超出範圍 [{min_exposure}, {max_exposure}]")
                    exposure_us = max(min_exposure, min(exposure_us, max_exposure))
                
                self.camera.ExposureTimeAbs.SetValue(exposure_us)
                logging.info(f"✅ 曝光時間已調整為: {exposure_us}us")
                
                # 通知觀察者
                self.notify_observers('exposure_changed', {'exposure_time': exposure_us})
                return True
                
            elif hasattr(self.camera, 'ExposureTime'):
                self.camera.ExposureTime.SetValue(exposure_us)
                logging.info(f"✅ 曝光時間已調整為: {exposure_us}us (ExposureTime)")
                self.notify_observers('exposure_changed', {'exposure_time': exposure_us})
                return True
            else:
                logging.error("相機不支持曝光時間調整")
                return False
                
        except Exception as e:
            logging.error(f"設置曝光時間失敗: {str(e)}")
            return False
    
    def get_exposure_time(self) -> float:
        """獲取當前曝光時間（微秒）"""
        try:
            if not self.camera or not self.is_connected:
                return 0.0
            
            if hasattr(self.camera, 'ExposureTimeAbs'):
                return self.camera.ExposureTimeAbs.GetValue()
            elif hasattr(self.camera, 'ExposureTime'):
                return self.camera.ExposureTime.GetValue()
            else:
                return 0.0
        except Exception as e:
            logging.error(f"獲取曝光時間失敗: {str(e)}")
            return 0.0
    
    def get_exposure_range(self) -> tuple:
        """獲取曝光時間範圍（最小值，最大值）"""
        try:
            if not self.camera or not self.is_connected:
                return (0.0, 0.0)
            
            if hasattr(self.camera, 'ExposureTimeAbs'):
                min_exp = self.camera.ExposureTimeAbs.GetMin()
                max_exp = self.camera.ExposureTimeAbs.GetMax()
                return (min_exp, max_exp)
            elif hasattr(self.camera, 'ExposureTime'):
                min_exp = self.camera.ExposureTime.GetMin()
                max_exp = self.camera.ExposureTime.GetMax()
                return (min_exp, max_exp)
            else:
                return (0.0, 0.0)
        except Exception as e:
            logging.error(f"獲取曝光範圍失敗: {str(e)}")
            return (0.0, 0.0)
    
    def get_configured_fps(self) -> float:
        """獲取相機當前配置的幀率（不是實際測量FPS）"""
        try:
            if not self.camera or not self.is_connected:
                return 0.0
            
            # 嘗試不同的FPS屬性
            for fps_attr in ['AcquisitionFrameRateAbs', 'AcquisitionFrameRate']:
                if hasattr(self.camera, fps_attr):
                    fps_node = getattr(self.camera, fps_attr)
                    if hasattr(fps_node, 'GetValue'):
                        configured_fps = fps_node.GetValue()
                        logging.debug(f"從 {fps_attr} 獲取到配置FPS: {configured_fps:.1f}")
                        return configured_fps
            
            # 如果無法獲取，返回0
            logging.warning("無法獲取相機配置的幀率")
            return 0.0
            
        except Exception as e:
            logging.error(f"獲取配置幀率失敗: {str(e)}")
            return 0.0
    
    def get_fps_range(self) -> tuple:
        """獲取相機幀率範圍（最小值，最大值）"""
        try:
            if not self.camera or not self.is_connected:
                return (0.0, 0.0)
            
            for fps_attr in ['AcquisitionFrameRateAbs', 'AcquisitionFrameRate']:
                if hasattr(self.camera, fps_attr):
                    fps_node = getattr(self.camera, fps_attr)
                    if hasattr(fps_node, 'GetMin') and hasattr(fps_node, 'GetMax'):
                        min_fps = fps_node.GetMin()
                        max_fps = fps_node.GetMax()
                        return (min_fps, max_fps)
            
            return (0.0, 376.0)  # 預設範圍
            
        except Exception as e:
            logging.error(f"獲取幀率範圍失敗: {str(e)}")
            return (0.0, 376.0)
        
    def add_observer(self, observer: Callable):
        """添加觀察者（View）"""
        self.observers.append(observer)
        
    def notify_observers(self, event_type: str, data: Any = None):
        """通知所有觀察者"""
        for observer in self.observers:
            try:
                observer(event_type, data)
            except Exception as e:
                logging.error(f"通知觀察者時出錯: {str(e)}")
                
    def detect_cameras(self) -> list:
        """檢測可用的 Basler 相機"""
        try:
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            
            camera_list = []
            for device in devices:
                camera_info = {
                    'model': device.GetModelName(),
                    'serial': device.GetSerialNumber(),
                    'user_id': device.GetUserDefinedName() if hasattr(device, 'GetUserDefinedName') else '',
                    'is_target': "640-300" in device.GetModelName()
                }
                camera_list.append(camera_info)
                
            self.notify_observers('cameras_detected', camera_list)
            return camera_list
            
        except Exception as e:
            logging.error(f"檢測相機失敗: {str(e)}")
            self.notify_observers('detection_error', str(e))
            return []
            
    def connect(self, device_index: int = 0) -> bool:
        """連接指定相機 - 線程安全版本"""
        try:
            if self.is_connected:
                logging.info("斷開現有連接...")
                self.disconnect()
                # 等待確保舊連接完全斷開
                time.sleep(1.0)
                
            tl_factory = pylon.TlFactory.GetInstance()
            devices = tl_factory.EnumerateDevices()
            
            if not devices or device_index >= len(devices):
                raise ValueError("相機索引無效")
                
            self.camera = pylon.InstantCamera(tl_factory.CreateDevice(devices[device_index]))
            self.camera.Open()
            
            # 基本配置
            self._configure_camera()
            
            # 更新相機資訊
            self._update_camera_info()
            
            self.is_connected = True
            logging.info(f"成功連接相機: {self.camera_info.get('model', 'Unknown')}")
            
            self.notify_observers('camera_connected', self.camera_info)
            return True
            
        except Exception as e:
            logging.error(f"連接相機失敗: {str(e)}")
            self.notify_observers('connection_error', str(e))
            return False
            
    def _configure_camera(self):
        """配置相機為最佳性能 - acA640-300gm專用"""
        try:
            logging.info("開始配置 acA640-300gm 相機...")
            
            # 基本設置 - 只使用確定存在的節點
            basic_configs = [
                ('AcquisitionMode', 'Continuous'),
                ('PixelFormat', 'Mono8'),
                ('Width', 640),
                ('Height', 480),
            ]
            
            for param, value in basic_configs:
                try:
                    if hasattr(self.camera, param):
                        node = getattr(self.camera, param)
                        if hasattr(node, 'SetValue'):
                            node.SetValue(value)
                            logging.info(f"✅ 設置 {param} = {value}")
                        else:
                            logging.warning(f"⚠️ {param} 節點無SetValue方法")
                    else:
                        logging.warning(f"⚠️ {param} 節點不存在")
                except Exception as e:
                    logging.warning(f"❌ 設置 {param} 失敗: {str(e)}")
            
            # 曝光設置 - acA640-300gm使用ExposureTimeAbs
            try:
                if hasattr(self.camera, 'ExposureAuto'):
                    self.camera.ExposureAuto.SetValue('Off')
                    logging.info("✅ 關閉自動曝光")
                
                # 根據診斷結果，這個相機使用ExposureTimeAbs
                if hasattr(self.camera, 'ExposureTimeAbs'):
                    # 設置1ms曝光時間，追求280fps高性能
                    self.camera.ExposureTimeAbs.SetValue(1000.0)
                    logging.info("✅ 設置曝光時間: 1ms (ExposureTimeAbs) - 高速模式")
                elif hasattr(self.camera, 'ExposureTime'):
                    self.camera.ExposureTime.SetValue(1000.0)
                    logging.info("✅ 設置曝光時間: 1ms (ExposureTime) - 高速模式")
                    
            except Exception as e:
                logging.warning(f"設置曝光失敗: {str(e)}")
            
            # 增益設置 - acA640-300gm的GainRaw最小值是136
            try:
                if hasattr(self.camera, 'GainAuto'):
                    self.camera.GainAuto.SetValue('Off')
                    logging.info("✅ 關閉自動增益")
                    
                # 根據診斷結果，GainRaw最小值是136
                if hasattr(self.camera, 'GainRaw'):
                    try:
                        min_gain = self.camera.GainRaw.GetMin()
                        self.camera.GainRaw.SetValue(min_gain)
                        logging.info(f"✅ 設置增益為最小值: {min_gain}")
                    except:
                        # 如果無法獲取最小值，直接設置136
                        self.camera.GainRaw.SetValue(136)
                        logging.info("✅ 設置增益: 136 (最小值)")
                elif hasattr(self.camera, 'Gain'):
                    self.camera.Gain.SetValue(0.0)
                    logging.info("✅ 設置增益: 0")
                    
            except Exception as e:
                logging.warning(f"設置增益失敗: {str(e)}")
            
            # 幀率設置 - 保守設置以確保穩定
            try:
                if hasattr(self.camera, 'AcquisitionFrameRateEnable'):
                    self.camera.AcquisitionFrameRateEnable.SetValue(True)
                    logging.info("✅ 啟用幀率控制")
                    
                    # 嘗試不同的幀率API
                    frame_rate_set = False
                    for fps_attr in ['AcquisitionFrameRateAbs', 'AcquisitionFrameRate']:
                        try:
                            if hasattr(self.camera, fps_attr):
                                fps_node = getattr(self.camera, fps_attr)
                                # 高性能設置280fps
                                fps_node.SetValue(280.0)
                                logging.info(f"✅ 設置幀率: 280fps ({fps_attr})")
                                frame_rate_set = True
                                break
                        except Exception as e:
                            logging.debug(f"嘗試 {fps_attr} 失敗: {str(e)}")
                    
                    if not frame_rate_set:
                        logging.warning("無法設置幀率，使用默認值")
                        
            except Exception as e:
                logging.warning(f"設置幀率失敗: {str(e)}")
            
            # 觸發模式 - 確保關閉
            try:
                if hasattr(self.camera, 'TriggerMode'):
                    self.camera.TriggerMode.SetValue('Off')
                    logging.info("✅ 關閉觸發模式")
            except Exception as e:
                logging.warning(f"設置觸發模式失敗: {str(e)}")
                
            logging.info("✅ acA640-300gm 相機配置完成")
            
        except Exception as e:
            logging.error(f"相機配置失敗: {str(e)}")
            
    def _update_camera_info(self):
        """更新相機資訊"""
        try:
            if not self.camera:
                return
                
            info = self.camera.GetDeviceInfo()
            
            # 基本資訊
            self.camera_info = {
                'model': info.GetModelName(),
                'serial': info.GetSerialNumber(),
                'user_id': info.GetUserDefinedName() if hasattr(info, 'GetUserDefinedName') else '',
                'vendor': info.GetVendorName(),
                'version': info.GetDeviceVersion(),
            }
            
            # 當前設置
            try:
                self.camera_info.update({
                    'width': self.camera.Width.GetValue() if hasattr(self.camera, 'Width') else 640,
                    'height': self.camera.Height.GetValue() if hasattr(self.camera, 'Height') else 480,
                    'pixel_format': str(self.camera.PixelFormat.GetValue()) if hasattr(self.camera, 'PixelFormat') else 'Mono8',
                    'max_fps': self.camera.AcquisitionFrameRate.GetMax() if hasattr(self.camera, 'AcquisitionFrameRate') else 376.0,
                    'exposure_time': self.camera.ExposureTime.GetValue() if hasattr(self.camera, 'ExposureTime') else 1000.0
                })
            except:
                pass
                
        except Exception as e:
            logging.error(f"更新相機資訊失敗: {str(e)}")
            
    def start_capture(self) -> bool:
        """開始高速捕獲 - 線程安全版本"""
        if not self.is_connected:
            logging.error("相機未連接，無法開始捕獲")
            return False
            
        # 🔒 線程安全檢查：先停止現有捕獲
        if self.is_grabbing:
            logging.info("檢測到現有捕獲進程，先停止...")
            self.stop_capture()
            time.sleep(1.0)  # 確保完全停止
            
        try:
            # 雙重檢查相機狀態
            if not self.camera or not self.camera.IsOpen():
                logging.error("相機未開啟或已斷開")
                return False
            
            # 🔒 原子性設置狀態
            with self.frame_lock:
                if self.is_grabbing:  # 再次檢查
                    logging.warning("在鎖內檢測到捕獲已啟動，取消本次啟動")
                    return True
                
                # 清除停止事件和重置狀態
                self.stop_event.clear()
                self.is_grabbing = True
                
                # 重置統計
                self.total_frames = 0
                self.start_time = time.time()
                self.frame_times.clear()
                self.latest_frame = None
            
            # 🚀 安全啟動相機抓取（重要：使用最穩定的策略）
            try:
                self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
                logging.info("✅ 相機抓取已啟動，使用 OneByOne 策略")
            except Exception as grab_error:
                logging.error(f"❌ 相機抓取啟動失敗: {str(grab_error)}")
                self.is_grabbing = False
                return False
            
            # 等待相機穩定
            time.sleep(0.5)  # 縮短等待時間，但仍確保穩定
            
            # 🧵 啟動單一抓取線程
            self.capture_thread = threading.Thread(
                target=self._capture_loop, 
                name="BaslerCaptureThread",
                daemon=True
            )
            self.capture_thread.start()
            
            # 驗證線程啟動
            time.sleep(0.1)
            if not self.capture_thread.is_alive():
                logging.error("❌ 捕獲線程啟動失敗")
                self.is_grabbing = False
                if self.camera.IsGrabbing():
                    self.camera.StopGrabbing()
                return False
            
            logging.info("✅ 高速捕獲系統已啟動")
            self.notify_observers('capture_started')
            return True
            
        except Exception as e:
            logging.error(f"❌ 啟動捕獲失敗: {str(e)}")
            # 清理狀態
            self.is_grabbing = False
            if hasattr(self, 'camera') and self.camera and self.camera.IsGrabbing():
                try:
                    self.camera.StopGrabbing()
                except:
                    pass
            self.notify_observers('capture_error', str(e))
            return False
            
    def _capture_loop(self):
        """高性能捕獲循環 - 強化錯誤處理版本"""
        thread_name = threading.current_thread().name
        logging.info(f"[{thread_name}] 🚀 進入相機捕獲循環")
        
        consecutive_errors = 0
        max_consecutive_errors = 50  # 連續錯誤上限
        error_delay = 0.001  # 初始錯誤延遲（毫秒）
        
        while not self.stop_event.is_set() and self.is_grabbing:
            try:
                # 🔒 線程安全檢查相機狀態
                if not self.camera or not self.camera.IsGrabbing():
                    logging.warning(f"[{thread_name}] 相機已停止抓取，安全退出循環")
                    break
                
                # 🎯 關鍵修復：添加線程檢查，防止多線程衝突
                if hasattr(self, '_active_capture_thread') and self._active_capture_thread != threading.current_thread():
                    logging.warning(f"[{thread_name}] 檢測到其他活動捕獲線程，退出當前線程")
                    break
                
                # 設置當前線程為活動線程
                self._active_capture_thread = threading.current_thread()
                
                # 🛡️ 使用更短的超時時間，提高響應性
                grab_result = None
                try:
                    grab_result = self.camera.RetrieveResult(500, pylon.TimeoutHandling_Return)
                except Exception as retrieve_error:
                    # 🔥 關鍵修復：特別處理 "already a thread waiting" 錯誤
                    error_str = str(retrieve_error)
                    if "already a thread waiting" in error_str:
                        logging.error(f"[{thread_name}] ❌ 檢測到線程衝突，強制退出捕獲循環")
                        self.is_grabbing = False  # 強制停止
                        break
                    else:
                        raise retrieve_error  # 其他錯誤繼續往外拋
                
                if grab_result and grab_result.GrabSucceeded():
                    frame = grab_result.Array.copy()
                    grab_result.Release()
                    
                    # 🔒 線程安全更新最新幀
                    with self.frame_lock:
                        self.latest_frame = frame
                        
                    # 非阻塞更新隊列 - 優化版本
                    try:
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        try:
                            self.frame_queue.get_nowait()  # 丟棄舊幀
                            self.frame_queue.put_nowait(frame)
                        except queue.Empty:
                            pass
                    
                    # 🎬 優化錄製功能 - 降頻錄製減少性能影響
                    if self.recording_enabled and self.video_recorder and self.total_frames % 3 == 0:
                        try:
                            # 每3幀錄製一次，減少性能影響
                            # 確保幀是BGR格式（OpenCV格式）
                            if len(frame.shape) == 2:  # 灰度圖
                                recording_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                            else:
                                recording_frame = frame
                            
                            self.video_recorder.write_frame(recording_frame)
                        except Exception as record_error:
                            logging.error(f"錄製幀失敗: {str(record_error)}")
                    
                    # 更新統計
                    self._update_stats()
                    
                    # 🔄 重置錯誤計數（成功時）
                    consecutive_errors = 0
                    error_delay = 0.001
                    
                    # 第一幀的特殊日誌
                    if self.total_frames == 1:
                        logging.info(f"[{thread_name}] ✅ 成功獲取第一幀，尺寸: {frame.shape}")
                    
                elif grab_result:
                    grab_result.Release()
                    # 超時不算錯誤，繼續循環
                    
            except Exception as e:
                consecutive_errors += 1
                error_str = str(e)
                
                # 🚨 特殊處理致命錯誤
                if "already a thread waiting" in error_str:
                    logging.error(f"[{thread_name}] 💥 致命錯誤：線程衝突，立即停止捕獲")
                    self.is_grabbing = False
                    break
                
                # 記錄錯誤，但不要過度記錄
                if consecutive_errors <= 5:  # 只記錄前5個錯誤
                    logging.error(f"[{thread_name}] 抓取循環錯誤 #{consecutive_errors}: {error_str}")
                elif consecutive_errors == 6:
                    logging.error(f"[{thread_name}] 後續錯誤將被抑制...")
                
                # 🛑 達到錯誤上限時強制退出
                if consecutive_errors >= max_consecutive_errors:
                    logging.error(f"[{thread_name}] 💥 連續錯誤過多({consecutive_errors})，強制退出")
                    self.is_grabbing = False
                    break
                
                # 🕐 漸進式錯誤延遲
                error_delay = min(error_delay * 1.5, 0.1)  # 最大延遲100ms
                time.sleep(error_delay)
        
        # 🧹 清理工作
        if hasattr(self, '_active_capture_thread'):
            self._active_capture_thread = None
            
        logging.info(f"[{thread_name}] 🏁 相機捕獲循環已退出")
                
    def _update_stats(self):
        """更新性能統計"""
        current_time = time.time()
        
        with self.stats_lock:
            self.total_frames += 1
            self.frame_times.append(current_time)
            
            # 🎯 優化FPS計算 - 使用較短的時間窗口獲得更準確的實時FPS
            if len(self.frame_times) >= 10:  # 最少10幀才開始計算
                # 使用最近30幀計算更準確的短期FPS（約0.1秒窗口@280fps）
                recent_count = min(30, len(self.frame_times))
                time_span = self.frame_times[-1] - self.frame_times[-recent_count]
                if time_span > 0:
                    self.current_fps = (recent_count - 1) / time_span
                    
                    # 🎯 限制FPS範圍以確保合理性（acA640-300gm理論最大約300fps）
                    if self.current_fps > 320:  # 超過理論最大值，可能是計算誤差
                        # 使用更大的窗口重新計算
                        full_span = self.frame_times[-1] - self.frame_times[0]
                        if full_span > 0:
                            self.current_fps = (len(self.frame_times) - 1) / full_span
                    
        # 定期通知觀察者（優化頻率以提高性能）
        if self.total_frames % 50 == 0:  # 每50幀通知一次以減少開銷
            stats = self.get_stats()
            self.notify_observers('stats_updated', stats)
            
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """獲取最新幀 - 零延遲"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
            
    def get_frame_from_queue(self, timeout: float = 0.01) -> Optional[np.ndarray]:
        """從隊列獲取幀"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def get_stats(self) -> Dict[str, Any]:
        """獲取當前統計信息"""
        with self.stats_lock:
            elapsed_time = time.time() - self.start_time if self.start_time else 0
            avg_fps = self.total_frames / elapsed_time if elapsed_time > 0 else 0
            
            return {
                'total_frames': self.total_frames,
                'current_fps': self.current_fps,
                'average_fps': avg_fps,
                'elapsed_time': elapsed_time,
                'is_grabbing': self.is_grabbing,
                'is_connected': self.is_connected,
                'queue_size': self.frame_queue.qsize()
            }
            
    def get_camera_info(self) -> Dict[str, Any]:
        """獲取相機資訊"""
        return self.camera_info.copy()
        
    def stop_capture(self):
        """停止捕獲 - 強化線程安全版本"""
        try:
            # 🔒 使用鎖確保停止操作的原子性
            with self.frame_lock:
                if not self.is_grabbing:
                    logging.info("捕獲已經停止")
                    return
                    
                logging.info("🛑 正在停止捕獲...")
                self.is_grabbing = False
                self.stop_event.set()
                
                # 清理活動線程標記
                if hasattr(self, '_active_capture_thread'):
                    self._active_capture_thread = None
            
            # 🎯 第一步：停止相機抓取（重要：在線程外操作）
            if self.camera and hasattr(self.camera, 'IsGrabbing'):
                try:
                    if self.camera.IsGrabbing():
                        self.camera.StopGrabbing()
                        logging.info("✅ 相機停止抓取")
                except Exception as e:
                    logging.error(f"❌ 停止相機抓取失敗: {str(e)}")
            
            # 🧵 第二步：安全等待線程停止
            if hasattr(self, 'capture_thread') and self.capture_thread:
                if self.capture_thread.is_alive():
                    thread_name = getattr(self.capture_thread, 'name', 'Unknown')
                    logging.info(f"⏳ 等待捕獲線程停止... [{thread_name}]")
                    
                    # 使用較短的超時時間，避免長時間阻塞
                    self.capture_thread.join(timeout=2.0)
                    
                    if self.capture_thread.is_alive():
                        logging.warning(f"⚠️ 捕獲線程未能在2秒內停止 [{thread_name}]")
                        # 不強制終止，讓它自然結束
                    else:
                        logging.info(f"✅ 捕獲線程已停止 [{thread_name}]")
                        
                # 清理線程引用
                self.capture_thread = None
                
            # 🧹 第三步：安全清空幀隊列
            self._safe_clear_frame_queue()
            
            # 🔄 第四步：重置狀態
            with self.frame_lock:
                self.latest_frame = None
                
            logging.info("✅ 停止高速捕獲完成")
            self.notify_observers('capture_stopped')
            
        except Exception as e:
            logging.error(f"❌ 停止捕獲時出錯: {str(e)}")
            # 即使出錯也要確保狀態正確
            self.is_grabbing = False
            if hasattr(self, '_active_capture_thread'):
                self._active_capture_thread = None
    
    def _safe_clear_frame_queue(self):
        """安全清空幀隊列"""
        try:
            cleared_count = 0
            start_time = time.time()
            max_clear_time = 0.5  # 最大清理時間500ms
            
            while not self.frame_queue.empty() and (time.time() - start_time) < max_clear_time:
                try:
                    self.frame_queue.get_nowait()
                    cleared_count += 1
                    
                    # 避免清理過多造成阻塞
                    if cleared_count > 100:  # 最多清理100幀
                        logging.warning("幀隊列過大，停止清理以避免阻塞")
                        break
                        
                except queue.Empty:
                    break
                except Exception as e:
                    logging.warning(f"清理幀隊列項目時出錯: {str(e)}")
                    break
                    
            if cleared_count > 0:
                logging.info(f"🧹 清空了 {cleared_count} 個幀")
                
        except Exception as e:
            logging.warning(f"⚠️ 清空幀隊列時發生錯誤: {str(e)}")
            # 如果普通清理失敗，嘗試重建隊列
            try:
                self.frame_queue = queue.Queue(maxsize=3)
                logging.info("🔄 重建幀隊列")
            except Exception as rebuild_error:
                logging.error(f"❌ 重建幀隊列失敗: {str(rebuild_error)}")
    
    # ==================== 視頻錄製控制 ====================
    
    def set_video_recorder(self, video_recorder):
        """設置視頻錄製器並同步相機FPS配置（依賴注入）"""
        self.video_recorder = video_recorder
        
        # 🎯 同步相機配置的FPS到錄製器
        if self.is_connected:
            configured_fps = self.get_configured_fps()
            if configured_fps > 0:
                self.video_recorder.set_camera_fps(configured_fps)
                logging.info(f"✅ 已同步相機配置FPS到錄製器: {configured_fps:.1f}")
            else:
                logging.warning("⚠️ 無法獲取相機配置FPS，錄製器將使用預設值")
        
        logging.info("視頻錄製器已設置")
    
    def start_recording(self, filename: str = None) -> bool:
        """開始錄製（需要先設置錄製器）"""
        if not self.video_recorder:
            logging.error("未設置視頻錄製器，無法開始錄製")
            return False
            
        if not self.is_connected or self.latest_frame is None:
            logging.error("相機未連接或無可用幀，無法開始錄製")
            return False
            
        # 獲取當前幀尺寸
        frame_size = None
        if self.latest_frame is not None:
            if len(self.latest_frame.shape) == 2:  # 灰度圖
                height, width = self.latest_frame.shape
            else:  # 彩色圖
                height, width = self.latest_frame.shape[:2]
            frame_size = (width, height)
        
        # 🎯 智能FPS選擇：實際測量 → 相機配置 → 預設值
        if self.current_fps > 0:
            # 優先使用實際測量的FPS
            camera_fps = self.current_fps
            fps_source = "實際測量"
        else:
            # 如果沒有實際測量值，使用相機配置的FPS
            configured_fps = self.get_configured_fps()
            if configured_fps > 0:
                camera_fps = configured_fps
                fps_source = "相機配置"
            else:
                # 最後使用安全預設值
                camera_fps = 30.0
                fps_source = "安全預設"
                logging.warning("⚠️ 無法獲取相機實際或配置FPS，使用安全預設值")
        
        logging.info(f"📷 相機錄製使用幀率: {camera_fps:.1f} fps (來源: {fps_source})")
        
        # 開始錄製（傳遞實際幀率）
        success = self.video_recorder.start_recording(filename, frame_size, camera_fps)
        if success:
            self.recording_enabled = True
            
            # 🔧 工業相機錄製狀態檢查
            actual_fps_info = f"設定值: {camera_fps:.1f} fps"
            if self.current_fps > 0:
                fps_diff = abs(self.current_fps - camera_fps)
                if fps_diff > 10:  # 如果差異超過10fps
                    logging.warning(f"⚠️ FPS不匹配: 實際{self.current_fps:.1f} vs 錄製{camera_fps:.1f}")
                actual_fps_info += f", 實際: {self.current_fps:.1f} fps"
            
            self.notify_observers('recording_started', {
                'filename': filename,
                'frame_size': frame_size,
                'fps': camera_fps,  # 🎯 錄製使用的幀率
                'actual_fps': self.current_fps,  # 🎯 相機實際幀率
                'fps_match': abs(self.current_fps - camera_fps) <= 10 if self.current_fps > 0 else True
            })
            logging.info(f"🎬 工業相機錄製已開始: {filename} ({actual_fps_info})")
        
        return success
    
    def stop_recording(self) -> dict:
        """停止錄製"""
        if not self.recording_enabled or not self.video_recorder:
            return {}
            
        self.recording_enabled = False
        recording_info = self.video_recorder.stop_recording()
        
        self.notify_observers('recording_stopped', recording_info)
        logging.info("相機錄製已停止")
        
        return recording_info
    
    def is_recording(self) -> bool:
        """檢查是否正在錄製"""
        return self.recording_enabled and self.video_recorder and self.video_recorder.is_recording
            
    def disconnect(self):
        """斷開相機連接"""
        try:
            self.stop_capture()
            
            if self.camera and self.camera.IsOpen():
                self.camera.Close()
                
            self.camera = None
            self.is_connected = False
            
            with self.frame_lock:
                self.latest_frame = None
                
            logging.info("相機已斷開連接")
            self.notify_observers('camera_disconnected')
            
        except Exception as e:
            logging.error(f"斷開連接時出錯: {str(e)}")
            
    def get_system_diagnostics(self) -> Dict[str, Any]:
        """獲取系統診斷信息 - 幫助排查問題"""
        try:
            diagnostics = {
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'camera_status': {
                    'is_connected': self.is_connected,
                    'is_grabbing': self.is_grabbing,
                    'camera_exists': self.camera is not None,
                    'camera_open': self.camera.IsOpen() if self.camera else False,
                    'camera_grabbing': self.camera.IsGrabbing() if self.camera else False,
                },
                'thread_status': {
                    'stop_event_set': self.stop_event.is_set(),
                    'capture_thread_exists': hasattr(self, 'capture_thread') and self.capture_thread is not None,
                    'capture_thread_alive': (hasattr(self, 'capture_thread') and 
                                           self.capture_thread and 
                                           self.capture_thread.is_alive()),
                    'active_capture_thread': hasattr(self, '_active_capture_thread') and self._active_capture_thread is not None,
                },
                'performance': {
                    'total_frames': self.total_frames,
                    'current_fps': self.current_fps,
                    'frame_queue_size': self.frame_queue.qsize(),
                    'latest_frame_available': self.latest_frame is not None,
                },
                'memory': {
                    'frame_times_count': len(self.frame_times),
                    'observers_count': len(self.observers),
                }
            }
            
            # 相機詳細信息
            if self.camera_info:
                diagnostics['camera_info'] = self.camera_info.copy()
            
            return diagnostics
            
        except Exception as e:
            return {
                'error': f"診斷失敗: {str(e)}",
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def __del__(self):
        """析構函數 - 安全版本"""
        try:
            # 安全斷開連接
            if hasattr(self, 'is_connected') and self.is_connected:
                self.disconnect()
        except:
            # 忽略析構時的所有異常，避免程序崩潰
            pass