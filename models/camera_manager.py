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
        if hasattr(self, 'stop_event'):
            self.stop_event.set()

        if self.camera:
            self.camera.release()
            self.camera = None

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

    def capture_photo(self):
        """
        拍攝一張照片

        Returns:
            tuple: (成功與否, 圖像數據)
        """
        try:
            if not self.camera or not self.camera.isOpened():
                logging.error("無法拍攝：相機未開啟")
                return False, None

            # 拍攝照片（實際上是獲取一幀）
            ret, frame = self.camera.read()
            if not ret or frame is None:
                logging.error("拍攝失敗：無法讀取圖像")
                return False, None

            # 這裡可以添加圖像處理，例如調整大小、提高清晰度等

            return True, frame

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