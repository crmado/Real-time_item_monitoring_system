"""
相機控制模塊 - 簡化版
直接整合 Basler 相機控制邏輯
"""

import logging
import threading
import time
from collections import deque
from typing import Optional, List, Dict, Any
import numpy as np

try:
    from pypylon import pylon
    PYLON_AVAILABLE = True
except ImportError:
    PYLON_AVAILABLE = False
    pylon = None

logger = logging.getLogger(__name__)


class CameraController:
    """Basler 相機控制器 - 簡化版"""

    def __init__(self):
        if not PYLON_AVAILABLE:
            raise RuntimeError("pypylon 未安裝，請執行: pip install pypylon")

        self.camera: Optional[pylon.InstantCamera] = None
        self.is_connected = False
        self.is_grabbing = False

        # 線程控制
        self.grab_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 幀數據
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()

        # 性能統計
        self.total_frames = 0
        self.current_fps = 0.0
        self.frame_times = deque(maxlen=60)

        # 配置
        self.target_fps = 350.0
        self.exposure_time = 1000.0

        logger.info("✅ 相機控制器初始化完成")

    def detect_cameras(self) -> List[Dict[str, Any]]:
        """檢測所有可用相機"""
        try:
            tlFactory = pylon.TlFactory.GetInstance()
            devices = tlFactory.EnumerateDevices()

            cameras = []
            for i, device in enumerate(devices):
                info = {
                    'index': i,
                    'model': device.GetModelName(),
                    'serial': device.GetSerialNumber(),
                    'friendly_name': device.GetFriendlyName(),
                    'is_target': 'acA640-300gm' in device.GetModelName()
                }
                cameras.append(info)
                logger.info(f"📷 發現相機: {info['model']}")

            return cameras

        except Exception as e:
            logger.error(f"❌ 檢測相機失敗: {str(e)}")
            return []

    def connect(self, camera_index: int = 0) -> bool:
        """連接到指定相機"""
        try:
            if self.is_connected:
                logger.warning("⚠️ 相機已連接")
                return True

            tlFactory = pylon.TlFactory.GetInstance()
            devices = tlFactory.EnumerateDevices()

            if camera_index >= len(devices):
                raise ValueError(f"相機索引 {camera_index} 超出範圍")

            # 創建相機實例
            self.camera = pylon.InstantCamera(
                tlFactory.CreateDevice(devices[camera_index])
            )

            # 打開相機
            self.camera.Open()

            # 配置相機
            self._configure_camera()

            self.is_connected = True
            logger.info(f"✅ 相機連接成功: {self.camera.GetDeviceInfo().GetModelName()}")
            return True

        except Exception as e:
            logger.error(f"❌ 相機連接失敗: {str(e)}")
            return False

    def _configure_camera(self):
        """配置相機參數"""
        try:
            # 設置圖像格式
            if hasattr(self.camera, 'Width'):
                self.camera.Width.SetValue(640)
                self.camera.Height.SetValue(480)

            # 設置像素格式
            if hasattr(self.camera, 'PixelFormat'):
                self.camera.PixelFormat.SetValue('Mono8')

            # 設置曝光時間
            if hasattr(self.camera, 'ExposureTime'):
                self.camera.ExposureTime.SetValue(self.exposure_time)
            elif hasattr(self.camera, 'ExposureTimeAbs'):
                self.camera.ExposureTimeAbs.SetValue(self.exposure_time)

            # 優化性能設置
            if hasattr(self.camera, 'AcquisitionFrameRateEnable'):
                self.camera.AcquisitionFrameRateEnable.SetValue(True)

            if hasattr(self.camera, 'AcquisitionFrameRate'):
                self.camera.AcquisitionFrameRate.SetValue(self.target_fps)

            # GigE 優化
            if hasattr(self.camera, 'GevSCPSPacketSize'):
                self.camera.GevSCPSPacketSize.SetValue(9000)

            logger.info("✅ 相機參數配置完成")

        except Exception as e:
            logger.warning(f"⚠️ 相機配置警告: {str(e)}")

    def start_grabbing(self) -> bool:
        """開始抓取圖像"""
        if not self.is_connected:
            logger.error("❌ 相機未連接")
            return False

        if self.is_grabbing:
            logger.warning("⚠️ 已在抓取中")
            return True

        try:
            self.camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            self.is_grabbing = True
            self.total_frames = 0

            # 啟動抓取線程
            self.stop_event.clear()
            self.grab_thread = threading.Thread(target=self._grab_loop, daemon=True)
            self.grab_thread.start()

            logger.info("✅ 開始圖像抓取")
            return True

        except Exception as e:
            logger.error(f"❌ 開始抓取失敗: {str(e)}")
            return False

    def _grab_loop(self):
        """抓取循環"""
        while not self.stop_event.is_set() and self.is_grabbing:
            try:
                grab_result = self.camera.RetrieveResult(100, pylon.TimeoutHandling_ThrowException)

                if grab_result.GrabSucceeded():
                    frame = grab_result.Array.copy()

                    with self.frame_lock:
                        self.latest_frame = frame

                    # 更新統計
                    self.total_frames += 1
                    current_time = time.time()
                    self.frame_times.append(current_time)

                    # 計算 FPS
                    if len(self.frame_times) >= 2:
                        time_diff = self.frame_times[-1] - self.frame_times[0]
                        if time_diff > 0:
                            self.current_fps = (len(self.frame_times) - 1) / time_diff

                grab_result.Release()

            except Exception as e:
                if not self.stop_event.is_set():
                    logger.error(f"❌ 抓取錯誤: {str(e)}")
                time.sleep(0.01)

    def stop_grabbing(self):
        """停止抓取圖像"""
        if not self.is_grabbing:
            return

        self.stop_event.set()
        self.is_grabbing = False

        if self.grab_thread:
            self.grab_thread.join(timeout=2)

        if self.camera and self.camera.IsGrabbing():
            self.camera.StopGrabbing()

        logger.info("✅ 停止圖像抓取")

    def disconnect(self):
        """斷開相機連接"""
        if not self.is_connected:
            return

        self.stop_grabbing()

        if self.camera and self.camera.IsOpen():
            self.camera.Close()

        self.is_connected = False
        self.camera = None
        logger.info("✅ 相機已斷開")

    def set_exposure(self, exposure_us: float) -> bool:
        """設置曝光時間"""
        try:
            if not self.is_connected:
                return False

            self.exposure_time = exposure_us

            if hasattr(self.camera, 'ExposureTime'):
                self.camera.ExposureTime.SetValue(exposure_us)
            elif hasattr(self.camera, 'ExposureTimeAbs'):
                self.camera.ExposureTimeAbs.SetValue(exposure_us)

            logger.info(f"✅ 曝光時間設置為: {exposure_us}us")
            return True

        except Exception as e:
            logger.error(f"❌ 設置曝光失敗: {str(e)}")
            return False

    def get_frame(self) -> Optional[np.ndarray]:
        """獲取最新幀"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def cleanup(self):
        """清理資源"""
        self.disconnect()
        logger.info("✅ 相機資源已清理")
