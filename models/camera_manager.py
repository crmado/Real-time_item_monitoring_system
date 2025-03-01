"""
攝影機管理模型
負責管理所有視訊輸入源相關的功能
"""
import datetime
import os
import cv2
import signal
import subprocess
import time
import logging
from threading import Event
# 引入pylon庫
from pypylon import pylon

class CameraManager:
    """攝影機管理類別"""

    # ==========================================================================
    # 第一部分：基本屬性和初始化
    # ==========================================================================
    def __init__(self):
        """初始化攝影機管理器"""
        self.camera = None
        self.test_camera_obj = None
        self.test_stop_event = None
        self.test_libcamera_thread = None
        self.current_source = None
        self.is_recording = False
        self.TEST_MODE = False  # 測試模式，移到這裡

        self.pylon_camera = None
        self.preview_timer = None

    # ==========================================================================
    # 第二部分：攝影機操作
    # ==========================================================================
    def get_available_sources(self):
        """
        獲取可用的視訊來源

        Returns:
            sources: 可用視訊來源列表
        """
        sources = ["Test video"] if self.TEST_MODE else []

        # 檢查 libcamera 是否可用
        try:
            result = subprocess.run(
                ['libcamera-vid', '--help'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            if result.returncode == 0:
                sources.append("libcamera")
        except FileNotFoundError:
            logging.warning("libcamera Not Installed")

        # 尋找可用的 USB 攝像頭
        for i in range(5):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        sources.append(f"USB Camera {i}")
                cap.release()
            except Exception as e:
                logging.warning(f"Check the camera {i} An error occurred：{str(e)}")
                continue

        return sources

    def open_camera(self, source):
        """
        開啟指定的視訊來源

        Args:
            source: 視訊來源名稱

        Returns:
            bool: 是否成功開啟
        """
        try:
            if source == "Test video":
                video_path = r"testDate/colorConversion_output_2024-10-26_14-28-56_video_V6_200_206fps.mp4"
                if not os.path.exists(video_path):
                    logging.error(f"No test video found：{video_path}")
                    return False
                self.camera = cv2.VideoCapture(video_path)
            elif source == "libcamera":
                self.setup_libcamera()
            else:
                camera_index = int(source.split()[-1])
                self.camera = cv2.VideoCapture(camera_index)

            if not self.camera.isOpened():  # 檢查攝影機是否成功開啟
                logging.error("Unable to open video source")
                return False

            self.current_source = source
            return True

        except Exception as e:
            logging.error(f"An error occurred while opening the video source：{str(e)}")
            return False

    def setup_libcamera(self):
        """設定 libcamera"""
        raw_video_file = '/tmp/raw_output.h264'
        width = 640
        height = 480
        fps = 206

        command = (
            f"libcamera-vid -o {raw_video_file} "
            f"--width {width} --height {height} "
            f"--framerate {fps} --codec h264 "
            f"--denoise cdn_off --awb auto "
            f"--brightness 0.5 --contrast 1.0 "  # 調整影像參數
            f"--sharpness 0.5 "
            f"--level 4.2 -n --timeout 0"
        )

        self.stop_event = Event()
        try:
            self.run_libcamera(command, self.stop_event)
            self.camera = cv2.VideoCapture(raw_video_file)
        except Exception as e:
            logging.error(f"Error occurred while setting up libcamera：{str(e)}")
            raise

    def run_libcamera(self, command, stop_event):
        """
        執行 libcamera

        Args:
            command: libcamera 命令
            stop_event: 停止事件
        """
        try:
            pipe = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                preexec_fn=os.setsid
            )

            def monitor_process():
                while not stop_event.is_set():
                    time.sleep(0.1)
                os.killpg(os.getpgid(pipe.pid), signal.SIGTERM)

            from threading import Thread
            monitor_thread = Thread(target=monitor_process, daemon=True)
            monitor_thread.start()

        except Exception as e:
            logging.error(f"An error occurred while executing libcamera：{str(e)}")
            raise

    def release_camera(self):
        """釋放攝影機資源"""
        # 原有程式碼
        if hasattr(self, 'stop_event'):
            self.stop_event.set()

        if self.camera:
            self.camera.release()
            self.camera = None

        # 新增的Basler相機釋放
        self.release_pylon_camera()

        self.current_source = None
        self.is_recording = False

    def get_camera_info(self):
        """
        獲取攝影機資訊

        Returns:
            dict: 攝影機資訊
        """
        if not self.camera or not self.camera.isOpened():
            return None

        return {
            'width': int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': self.camera.get(cv2.CAP_PROP_FPS),
            'frame_count': int(self.camera.get(cv2.CAP_PROP_FRAME_COUNT))
        }

    def read_frame(self):
        """
        讀取一幀影像

        Returns:
            tuple: (是否成功, 影像幀)
        """
        if not self.camera or not self.camera.isOpened():
            return False, None

        return self.camera.read()

    def initialize_pylon_camera(self):
        """初始化Basler相機"""
        try:
            # 如果已經有初始化的相機，先使用它
            if self.camera and self.camera.isOpened():
                logging.info("使用已初始化的相機，跳過 Pylon 相機初始化")
                return True

            # 確保已安裝pypylon
            try:
                from pypylon import pylon
            except ImportError:
                logging.warning("未安裝pypylon庫，將使用普通相機")
                # 如果沒有 pypylon，嘗試使用 OpenCV 相機
                for i in range(5):
                    try:
                        cap = cv2.VideoCapture(i)
                        if cap.isOpened():
                            self.camera = cap
                            return True
                    except Exception:
                        continue
                return False

            # 嘗試獲取 Basler 相機設備
            tlf = pylon.TlFactory.GetInstance()
            devices = tlf.EnumerateDevices()

            if not devices:
                logging.warning("未檢測到Basler相機，嘗試使用普通相機")
                # 嘗試使用 OpenCV 相機
                for i in range(5):
                    try:
                        cap = cv2.VideoCapture(i)
                        if cap.isOpened():
                            self.camera = cap
                            return True
                    except Exception:
                        continue
                return False

            # 初始化 Pylon 相機
            try:
                self.pylon_camera = pylon.InstantCamera(tlf.CreateFirstDevice())
                self.pylon_camera.Open()

                # 配置相機參數
                device_info = self.pylon_camera.GetDeviceInfo()
                logging.info(f"相機類型: {device_info.GetDeviceClass()}")
                logging.info(f"型號: {device_info.GetModelName()}")

                # 根據相機類型設置參數
                if device_info.GetDeviceClass() == "BaslerGigE":
                    if hasattr(self.pylon_camera, 'GainRaw') and self.pylon_camera.GainRaw.IsWritable():
                        self.pylon_camera.GainRaw.SetValue(0)
                    if hasattr(self.pylon_camera, 'ExposureTimeRaw') and self.pylon_camera.ExposureTimeRaw.IsWritable():
                        self.pylon_camera.ExposureTimeRaw.SetValue(10000)
                else:
                    if hasattr(self.pylon_camera, 'Gain') and self.pylon_camera.Gain.IsWritable():
                        self.pylon_camera.Gain.SetValue(0)
                    if hasattr(self.pylon_camera, 'ExposureTime') and self.pylon_camera.ExposureTime.IsWritable():
                        self.pylon_camera.ExposureTime.SetValue(10000)

                if hasattr(self.pylon_camera, 'PixelFormat') and self.pylon_camera.PixelFormat.IsWritable():
                    self.pylon_camera.PixelFormat.SetValue('Mono8')

                # 開始抓取圖像
                self.pylon_camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

                return True
            except Exception as e:
                logging.error(f"初始化Basler相機失敗: {str(e)}")
                self.pylon_camera = None

                # 失敗後嘗試使用普通相機
                for i in range(5):
                    try:
                        cap = cv2.VideoCapture(i)
                        if cap.isOpened():
                            self.camera = cap
                            return True
                    except Exception:
                        continue
                return False

        except Exception as e:
            logging.error(f"初始化相機失敗: {str(e)}")
            return False

    def capture_pylon_image(self):
        """從Basler相機拍攝圖像"""
        try:
            if not self.pylon_camera or not self.pylon_camera.IsGrabbing():
                return False, None

            grab_result = self.pylon_camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grab_result.GrabSucceeded():
                image = grab_result.Array
                grab_result.Release()
                return True, image

            grab_result.Release()
            return False, None
        except Exception as e:
            logging.error(f"Basler相機拍攝失敗: {str(e)}")
            return False, None

    def capture_photo(self):
        """
        拍攝一張照片 - 支援多種相機類型，優先使用已開啟的相機

        Returns:
            tuple: (成功與否, 圖像數據)
        """
        try:
            # 優先使用已開啟的 OpenCV 相機
            if self.camera and self.camera.isOpened():
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    return True, frame

            # 嘗試使用 Basler 相機
            if hasattr(self, 'pylon_camera') and self.pylon_camera:
                try:
                    return self.capture_pylon_image()
                except Exception as e:
                    logging.warning(f"使用 Pylon 相機拍攝失敗: {str(e)}")

            # 嘗試使用測試相機
            if self.test_camera_obj and self.test_camera_obj.isOpened():
                ret, frame = self.test_camera_obj.read()
                if ret and frame is not None:
                    return True, frame

            # 如果所有方法都失敗，嘗試臨時打開一個相機
            for i in range(5):
                try:
                    temp_camera = cv2.VideoCapture(i)
                    if temp_camera.isOpened():
                        ret, frame = temp_camera.read()
                        temp_camera.release()
                        if ret and frame is not None:
                            return True, frame
                except Exception:
                    continue

            logging.error("無法拍攝：沒有可用的相機")
            return False, None

        except Exception as e:
            logging.error(f"拍攝照片時發生錯誤：{str(e)}")
            return False, None

    def save_photo(self, frame, directory="captured_images"):
        """
        保存照片到指定目錄

        Args:
            frame: 圖像幀
            directory: 保存目錄

        Returns:
            str: 保存的文件路徑，失敗時返回None
        """
        try:
            import os
            import datetime
            import cv2

            # 確保目錄存在
            if not os.path.exists(directory):
                os.makedirs(directory)

            # 生成文件名：時間戳
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{directory}/captured_{timestamp}.jpg"

            # 保存圖像
            cv2.imwrite(filename, frame)
            logging.info(f"照片已保存：{filename}")
            return filename

        except Exception as e:
            logging.error(f"保存照片時發生錯誤：{str(e)}")
            return None

    def release_pylon_camera(self):
        """釋放Basler相機資源"""
        try:
            if hasattr(self, 'pylon_camera') and self.pylon_camera:
                if self.pylon_camera.IsGrabbing():
                    self.pylon_camera.StopGrabbing()
                self.pylon_camera.Close()
                self.pylon_camera = None
        except Exception as e:
            logging.error(f"釋放Basler相機資源時發生錯誤: {str(e)}")