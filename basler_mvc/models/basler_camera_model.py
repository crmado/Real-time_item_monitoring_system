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
        self.frame_queue = queue.Queue(maxsize=3)  # 減少緩存以降低記憶體使用
        
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
        """開始高速捕獲"""
        if not self.is_connected:
            logging.error("相機未連接，無法開始捕獲")
            return False
            
        if self.is_grabbing:
            logging.warning("捕獲已經在進行中")
            return True
            
        try:
            # 確保相機是開啟狀態
            if not self.camera.IsOpen():
                logging.error("相機未開啟")
                return False
            
            # 使用OneByOne策略，更穩定
            self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne)
            self.is_grabbing = True
            self.stop_event.clear()
            
            # 重置統計
            self.total_frames = 0
            self.start_time = time.time()
            self.frame_times.clear()
            
            logging.info("相機開始抓取，等待2秒讓相機穩定...")
            time.sleep(2)  # 讓相機穩定
            
            # 啟動高速抓取線程
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logging.info("開始高速捕獲，抓取線程已啟動")
            self.notify_observers('capture_started')
            return True
            
        except Exception as e:
            logging.error(f"啟動捕獲失敗: {str(e)}")
            self.is_grabbing = False
            self.notify_observers('capture_error', str(e))
            return False
            
    def _capture_loop(self):
        """高性能捕獲循環"""
        logging.info("進入相機捕獲循環")
        
        while not self.stop_event.is_set() and self.is_grabbing:
            try:
                # 檢查相機狀態
                if not self.camera.IsGrabbing():
                    logging.warning("相機已停止抓取，退出循環")
                    break
                
                # 使用穩定的超時設置
                grab_result = self.camera.RetrieveResult(1000, pylon.TimeoutHandling_Return)
                
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
                    
                    # 第一幀的特殊日誌
                    if self.total_frames == 1:
                        logging.info(f"成功獲取第一幀，尺寸: {frame.shape}")
                    
                elif grab_result:
                    grab_result.Release()
                    # 移除過多的警告日誌
                    # logging.warning("抓取失敗但有結果")
                    
            except Exception as e:
                logging.error(f"抓取循環錯誤: {str(e)}")
                time.sleep(0.1)  # 出錯時稍作等待
                
        logging.info("退出相機捕獲循環")
                
    def _update_stats(self):
        """更新性能統計"""
        current_time = time.time()
        
        with self.stats_lock:
            self.total_frames += 1
            self.frame_times.append(current_time)
            
            # 限制列表大小，防止記憶體洩漏
            if len(self.frame_times) > 200:  # 保持最新200個時間戳
                self.frame_times.pop(0)
            
            # 計算實時 FPS
            if len(self.frame_times) >= 2:
                time_span = self.frame_times[-1] - self.frame_times[0]
                if time_span > 0:
                    self.current_fps = (len(self.frame_times) - 1) / time_span
                    
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
        """停止捕獲 - 改進版，確保線程安全停止"""
        try:
            if not self.is_grabbing:
                logging.info("捕獲已經停止")
                return
                
            logging.info("正在停止捕獲...")
            self.is_grabbing = False
            self.stop_event.set()
            
            # 先停止相機抓取
            if self.camera and self.camera.IsGrabbing():
                try:
                    self.camera.StopGrabbing()
                    logging.info("相機停止抓取")
                except Exception as e:
                    logging.error(f"停止相機抓取失敗: {str(e)}")
            
            # 等待線程停止
            if hasattr(self, 'capture_thread') and self.capture_thread:
                if self.capture_thread.is_alive():
                    logging.info("等待捕獲線程停止...")
                    self.capture_thread.join(timeout=3.0)
                    if self.capture_thread.is_alive():
                        logging.warning("捕獲線程未能在3秒內停止")
                    else:
                        logging.info("捕獲線程已停止")
                
            # 安全清空隊列 - 防止死鎖
            try:
                # 設定清理超時，避免無限等待
                start_time = time.time()
                cleared_count = 0
                while not self.frame_queue.empty() and (time.time() - start_time) < 1.0:
                    try:
                        self.frame_queue.get_nowait()
                        cleared_count += 1
                    except queue.Empty:
                        break
                if cleared_count > 0:
                    logging.info(f"清空了 {cleared_count} 個幀")
            except Exception as e:
                logging.warning(f"清空幀隊列時發生錯誤: {str(e)}")
                    
            logging.info("停止高速捕獲完成")
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