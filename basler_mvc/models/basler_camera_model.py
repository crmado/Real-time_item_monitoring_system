"""
Basler 相機 Model - MVC 架構核心
專注於 Basler acA640-300gm 相機的數據管理和業務邏輯
"""

import logging
import threading
import time
import queue
import numpy as np
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
        self.frame_queue = queue.Queue(maxsize=10)
        
        # 性能統計
        self.total_frames = 0
        self.start_time = None
        self.current_fps = 0.0
        self.frame_times = deque(maxlen=100)
        
        # 相機資訊
        self.camera_info = {}
        
        # 觀察者模式 - 通知 View 更新
        self.observers = []
        
        logging.info("Basler 相機模型初始化完成")
        
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
        """連接指定相機"""
        try:
            if self.is_connected:
                self.disconnect()
                
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
        """配置相機為最佳性能"""
        try:
            # acA640-300gm 最佳設置
            configs = [
                ('AcquisitionMode', 'Continuous'),
                ('PixelFormat', 'Mono8'),
                ('Width', 640),
                ('Height', 480),
                ('ExposureAuto', 'Off'),
                ('ExposureTime', 1000.0),  # 1ms
                ('GainAuto', 'Off'),
                ('Gain', 0.0),
                ('AcquisitionFrameRateEnable', True),
                ('AcquisitionFrameRate', 350.0),  # 接近理論最大值
            ]
            
            for param, value in configs:
                try:
                    if hasattr(self.camera, param):
                        node = getattr(self.camera, param)
                        if hasattr(node, 'SetValue'):
                            node.SetValue(value)
                except Exception as e:
                    logging.debug(f"設置 {param} 失敗: {str(e)}")
                    
            # 網路優化 (GigE)
            try:
                if hasattr(self.camera, 'GevSCPSPacketSize'):
                    self.camera.GevSCPSPacketSize.SetValue(9000)  # Jumbo frames
            except:
                pass
                
            logging.info("相機配置完成")
            
        except Exception as e:
            logging.warning(f"相機配置警告: {str(e)}")
            
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
        """開始高速捕獲"""
        if not self.is_connected or self.is_grabbing:
            return False
            
        try:
            # 使用最新圖像策略
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            self.is_grabbing = True
            self.stop_event.clear()
            
            # 重置統計
            self.total_frames = 0
            self.start_time = time.time()
            self.frame_times.clear()
            
            # 啟動高速抓取線程
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logging.info("開始高速捕獲")
            self.notify_observers('capture_started')
            return True
            
        except Exception as e:
            logging.error(f"啟動捕獲失敗: {str(e)}")
            self.notify_observers('capture_error', str(e))
            return False
            
    def _capture_loop(self):
        """高性能捕獲循環"""
        while not self.stop_event.is_set() and self.is_grabbing:
            try:
                # 直接抓取最新幀
                grab_result = self.camera.RetrieveResult(1, pylon.TimeoutHandling_Return)
                
                if grab_result and grab_result.GrabSucceeded():
                    frame = grab_result.Array.copy()
                    grab_result.Release()
                    
                    # 更新最新幀
                    with self.frame_lock:
                        self.latest_frame = frame
                        
                    # 非阻塞更新隊列
                    try:
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        try:
                            self.frame_queue.get_nowait()  # 丟棄舊幀
                            self.frame_queue.put_nowait(frame)
                        except queue.Empty:
                            pass
                    
                    # 更新統計
                    self._update_stats()
                    
                elif grab_result:
                    grab_result.Release()
                    
            except Exception as e:
                logging.debug(f"抓取循環錯誤: {str(e)}")
                time.sleep(0.001)
                
    def _update_stats(self):
        """更新性能統計"""
        current_time = time.time()
        
        with self.stats_lock:
            self.total_frames += 1
            self.frame_times.append(current_time)
            
            # 計算實時 FPS
            if len(self.frame_times) >= 2:
                time_span = self.frame_times[-1] - self.frame_times[0]
                if time_span > 0:
                    self.current_fps = (len(self.frame_times) - 1) / time_span
                    
        # 定期通知觀察者
        if self.total_frames % 30 == 0:  # 每30幀通知一次
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
        """停止捕獲"""
        try:
            self.is_grabbing = False
            self.stop_event.set()
            
            if hasattr(self, 'capture_thread'):
                self.capture_thread.join(timeout=2.0)
                
            if self.camera and self.camera.IsGrabbing():
                self.camera.StopGrabbing()
                
            # 清空隊列
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break
                    
            logging.info("停止高速捕獲")
            self.notify_observers('capture_stopped')
            
        except Exception as e:
            logging.error(f"停止捕獲時出錯: {str(e)}")
            
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
            
    def __del__(self):
        """析構函數"""
        try:
            self.disconnect()
        except:
            pass