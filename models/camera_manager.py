"""
攝影機管理模型
負責管理所有視訊輸入源相關的功能
"""
import os
import threading

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
                stderr=subprocess.PIPE,
                timeout=2  # 添加超時限制
            )
            if result.returncode == 0:
                sources.append("libcamera")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logging.warning("libcamera Not Installed or not responding")

        # 修改：更穩健的USB攝像頭檢測
        for i in range(5):
            try:
                # 使用更安全的方式開啟攝像頭
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # 使用超時機制讀取幀
                    start_time = time.time()
                    ret = False
                    while time.time() - start_time < 0.5:  # 最多等待0.5秒
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            break
                        time.sleep(0.05)

                    if ret:
                        # 只有成功讀取到有效幀時才添加來源
                        sources.append(f"USB Camera {i}")
                        logging.info(f"發現可用攝像頭: USB Camera {i}")
                cap.release()
            except Exception as e:
                logging.warning(f"檢查攝像頭 {i} 時發生錯誤：{str(e)}")
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
            # 記錄要開啟的相機
            logging.info(f"嘗試開啟相機: {source}")

            # 如果已有開啟的相機，先釋放它
            if self.camera is not None:
                try:
                    if self.camera.isOpened():
                        self.camera.release()
                except Exception as e:
                    logging.warning(f"釋放相機時發生錯誤: {str(e)}")
                finally:
                    self.camera = None
                    time.sleep(0.3)  # 確保資源釋放

            # 如果有活躍的 Pylon 相機，釋放它
            if hasattr(self, 'pylon_camera') and self.pylon_camera:
                self.release_pylon_camera()
                time.sleep(0.3)

            # 根據來源類型開啟相機
            if source == "Test video":
                # 測試視頻處理邏輯
                video_path = r"testDate/colorConversion_output_2024-10-26_14-28-56_video_V6_200_206fps.mp4"
                if not os.path.exists(video_path):
                    backup_paths = ["testDate/test_video.mp4", "video/sample.mp4"]
                    for path in backup_paths:
                        if os.path.exists(path):
                            video_path = path
                            break
                    else:
                        logging.error(f"未找到測試影片: {video_path}")
                        return False

                logging.info(f"使用測試視頻: {video_path}")
                self.camera = cv2.VideoCapture(video_path)

            elif source == "libcamera":
                logging.info("初始化 libcamera")
                return self.setup_libcamera()

            else:
                # 處理 USB 相機或其他相機索引
                camera_index = -1

                # 嘗試從來源名稱中獲取索引
                if "USB Camera" in source:
                    try:
                        camera_index = int(source.split()[-1])
                        logging.info(f"從來源名稱解析相機索引: {camera_index}")
                    except ValueError:
                        logging.warning(f"無法從 '{source}' 解析相機索引")
                        camera_index = 0
                else:
                    # 嘗試將整個字符串解析為索引
                    try:
                        camera_index = int(source)
                        logging.info(f"將來源直接解析為索引: {camera_index}")
                    except ValueError:
                        logging.warning(f"無法將 '{source}' 解析為相機索引，使用預設索引 0")
                        camera_index = 0

                # 嘗試開啟相機，增加重試機制
                max_tries = 3
                success = False

                for attempt in range(max_tries):
                    try:
                        logging.info(f"嘗試開啟相機 {camera_index} (嘗試 {attempt + 1}/{max_tries})")

                        # 使用 OpenCV 開啟相機
                        self.camera = cv2.VideoCapture(camera_index)

                        if self.camera.isOpened():
                            # 設定相機屬性
                            self.camera.set(cv2.CAP_PROP_FOURCC, 0x4D4A5047)  # MJPEG 的四字節編碼
                            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 3)

                            # 測試讀取，確保相機可用
                            read_success, test_frame = self.camera.read()
                            if read_success and test_frame is not None:
                                logging.info(f"成功讀取相機 {camera_index} 的測試幀")
                                success = True
                                break
                            else:
                                logging.warning(f"相機 {camera_index} 已開啟但無法讀取幀")
                                self.camera.release()
                                self.camera = None
                        else:
                            logging.warning(f"無法開啟相機 {camera_index}")

                    except Exception as e:
                        logging.warning(f"開啟相機 {camera_index} 時發生錯誤: {str(e)}")
                        if self.camera:
                            try:
                                self.camera.release()
                            except:
                                pass
                            self.camera = None

                    # 如果失敗但還有更多嘗試，等待一下再試
                    if not success and attempt < max_tries - 1:
                        time.sleep(0.5)

                # 如果所有嘗試都失敗
                if not success:
                    logging.error(f"所有嘗試開啟相機 {camera_index} 的嘗試都失敗了")
                    return False

            # 驗證相機是否開啟並能讀取幀
            if not self.camera or not self.camera.isOpened():
                logging.error("無法開啟視訊來源")
                return False

            # 讀取多個幀以確認相機穩定性
            success_reads = 0
            for _ in range(3):
                try:
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
                        success_reads += 1
                except Exception as e:
                    logging.warning(f"讀取相機測試幀時出錯: {str(e)}")
                time.sleep(0.1)

            if success_reads < 2:  # 至少要有 2/3 的成功讀取
                logging.error(f"相機連接不穩定，僅成功讀取 {success_reads}/3 幀")
                if self.camera:
                    self.camera.release()
                    self.camera = None
                return False

            # 更新當前來源並返回成功
            self.current_source = source
            logging.info(f"成功開啟相機: {source}")
            return True

        except Exception as e:
            logging.error(f"開啟視訊來源時發生錯誤: {str(e)}")
            if self.camera:
                try:
                    self.camera.release()
                except:
                    pass
                self.camera = None
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
        讀取一幀影像，包含錯誤處理

        Returns:
            tuple: (是否成功, 影像幀)
        """
        global ret
        if not self.camera or not self.camera.isOpened():
            return False, None

        try:
            # 添加嘗試次數機制
            max_attempts = 3
            for attempt in range(max_attempts):
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    return ret, frame
                elif attempt < max_attempts - 1:
                    # 不是最後一次嘗試，等待一小段時間後重試
                    time.sleep(0.05)

            # 如果所有嘗試都失敗了
            if ret is False:
                logging.warning(f"讀取攝影機幀失敗，嘗試 {max_attempts} 次後放棄")
            return False, None

        except Exception as e:
            logging.error(f"讀取攝影機幀時發生異常: {str(e)}")
            return False, None

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

    # ==========================================================================
    # 第六部分：錯誤處理與自動恢復機制
    # ==========================================================================
    def monitor_camera_health(self):
        """監控攝影機健康狀態並在必要時重啟"""
        if not hasattr(self, 'health_monitor_running') or not self.health_monitor_running:
            self.health_monitor_running = True
            self.health_check_thread = threading.Thread(
                target=self._run_health_monitor,
                daemon=True
            )
            self.health_check_thread.start()
            logging.info("攝影機健康監控已啟動")

    def _run_health_monitor(self):
        """執行攝影機健康監控線程"""
        consecutive_failures = 0
        max_failures = 5
        check_interval = 2.0  # 每2秒檢查一次

        while self.health_monitor_running:
            if self.camera and self.camera.isOpened():
                try:
                    # 嘗試讀取幀來檢查攝影機健康狀況
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
                        # 攝影機運作正常
                        consecutive_failures = 0
                    else:
                        consecutive_failures += 1
                        logging.warning(f"攝影機讀取失敗 ({consecutive_failures}/{max_failures})")
                except Exception as e:
                    consecutive_failures += 1
                    logging.warning(f"攝影機檢查錯誤: {str(e)} ({consecutive_failures}/{max_failures})")

                # 如果連續失敗次數超過閾值，嘗試重新連接
                if consecutive_failures >= max_failures:
                    logging.warning("攝影機連續讀取失敗，嘗試重新連接...")

                    # 保存當前來源然後重新連接
                    current_source = self.current_source
                    self.release_camera()
                    time.sleep(1.0)  # 等待資源完全釋放

                    # 嘗試重新連接
                    if current_source and self.open_camera(current_source):
                        logging.info(f"攝影機已成功重新連接: {current_source}")
                        consecutive_failures = 0
                    else:
                        logging.error("攝影機重新連接失敗")

            # 等待一段時間再進行下一次檢查
            time.sleep(check_interval)

    def stop_health_monitor(self):
        """停止攝影機健康監控"""
        self.health_monitor_running = False
        if hasattr(self, 'health_check_thread') and self.health_check_thread:
            self.health_check_thread.join(timeout=1.0)
            logging.info("攝影機健康監控已停止")