"""
攝影機管理模型
負責管理所有視訊輸入源相關的功能
"""
import os
import threading

import cv2 # type: ignore
import signal
import subprocess
import time
import logging
from threading import Event
# 引入pylon庫
from pypylon import pylon # type: ignore
import numpy as np # type: ignore

class CameraManager:
    """攝影機管理類別"""

    # ==========================================================================
    # 第一部分：基本屬性和初始化
    # ==========================================================================
    def __init__(self, config=None):
        """
        初始化相機管理器
        
        Args:
            config: 配置對象
        """
        self.config = config or {}
        self.camera = None
        self.basler_camera = None
        self.pylon_camera = None
        self.preview_timer = None
        self.is_virtual = False
        self.virtual_frame = None
        self.TEST_MODE = True  # 始終啟用測試模式
        self.current_frame = None
        
        # 測試視頻相關變數
        self.is_test_video = False
        self.video_fps = 30.0  # 默認幀率
        self.frame_interval_ms = 33  # 默認幀間隔（毫秒）
        self.last_frame_time = 0  # 上一幀的時間戳
        
        # 直接存取的測試相機物件
        self.test_camera_obj = None
        
        # 初始化虛擬相機
        self._init_virtual_camera()
        
    def _init_virtual_camera(self):
        """初始化虛擬相機"""
        try:
            # 創建一個黑色背景
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # 添加一些文字
            cv2.putText(frame, "Virtual Camera", (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            self.virtual_frame = frame
            logging.info("成功初始化虛擬相機")
        except Exception as e:
            logging.error(f"初始化虛擬相機時發生錯誤: {str(e)}")
            # 創建一個備用幀
            self.virtual_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
    def get_available_sources(self):
        """
        獲取可用的視訊來源

        Returns:
            sources: 可用視訊來源列表
        """
        sources = []
        
        logging.info("[資訊] 開始檢測可用的視訊來源...")
        
        # 添加測試視頻選項
        sources.append("Test video")
        logging.info("[資訊] 已添加測試視頻選項")
        
        # 檢測內置攝像頭 - 不再使用安全模式限制
        # 在 macOS 上，檢查內建相機（索引 0）
        if os.name == 'posix' and 'darwin' in os.uname().sysname.lower():
            logging.info("[資訊] 檢測到 macOS 系統")
            try:
                cap = cv2.VideoCapture(0)
                if cap.isOpened():
                    logging.info("[資訊] 使用內建相機，索引: 0")
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        sources.append("Built-in Camera")
                        logging.info("[資訊] 成功讀取第一幀，尺寸: {}".format(frame.shape))
                    else:
                        logging.warning("[警告] 內建相機開啟成功但無法讀取幀")
                else:
                    logging.warning("[警告] 無法開啟內建相機")
                cap.release()
            except Exception as e:
                logging.warning(f"[警告] 檢查內建相機時發生錯誤: {str(e)}")
        else:
            # 在其他系統上檢查USB攝像頭
            logging.info("[資訊] 非 macOS 系統，嘗試檢測 USB 相機...")
            for i in range(2):  # 只檢查前兩個攝像頭索引，避免過多檢查導致的問題
                try:
                    logging.info(f"[資訊] 嘗試開啟 USB 相機 {i}...")
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        logging.info(f"[資訊] 成功開啟 USB 相機 {i}")
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            sources.append(f"USB Camera {i}")
                            logging.info(f"[資訊] 已檢測到 USB 相機 {i} 並成功讀取幀，尺寸: {frame.shape}")
                        else:
                            logging.warning(f"[警告] USB 相機 {i} 開啟成功但無法讀取幀")
                    else:
                        logging.warning(f"[警告] 無法開啟 USB 相機 {i}")
                    cap.release()
                except Exception as e:
                    logging.warning(f"[警告] 檢查 USB 相機 {i} 時發生錯誤: {str(e)}")

        # 檢查 Basler 相機
        logging.info("[資訊] 嘗試檢測 Basler 相機...")
        try:
            tlf = pylon.TlFactory.GetInstance()
            devices = tlf.EnumerateDevices()
            if devices:
                logging.info(f"[資訊] 檢測到 {len(devices)} 個 Basler 相機")
                for i, device in enumerate(devices):
                    sources.append(f"Basler Camera {i}")
                    logging.info(f"[資訊] 已檢測到 Basler 相機 {i}: {device.GetModelName()}")
            else:
                logging.info("[資訊] 未檢測到 Basler 相機")
        except Exception as e:
            logging.warning(f"[警告] Basler 相機檢測失敗: {str(e)}")

        # 如果沒有檢測到任何相機，添加一個提示選項
        if len(sources) == 1:  # 只有測試視頻
            sources.append("未檢測到可用相機")
            logging.info("[資訊] 未檢測到任何相機")
            
        logging.info(f"[資訊] 可用視訊來源檢測完成，共找到 {len(sources)} 個來源: {sources}")

        return sources
        
    def open_camera(self, source):
        """
        開啟相機
        
        Args:
            source: 相機來源
        
        Returns:
            bool: 是否成功開啟相機
        """
        try:
            # 首先釋放所有現有相機資源
            self.release_all_cameras()
            
            logging.info(f"[資訊] 嘗試開啟相機源: {source}")
            
            # 處理「未檢測到可用相機」的情況
            if source == "未檢測到可用相機":
                logging.warning("[警告] 未檢測到可用相機，使用虛擬相機替代")
                return self._open_virtual_camera()
            elif source == "Test video":
                return self._open_test_video()
            elif source == "Virtual Camera":
                return self._open_virtual_camera()
            elif "Basler" in source:
                return self._open_basler_camera(source)
            else:
                return self._open_usb_camera(source)
                
        except Exception as e:
            logging.error(f"[錯誤] 開啟相機時發生錯誤: {str(e)}")
            self.release_all_cameras()
            # 默認使用虛擬相機
            self.is_virtual = True
            return True
            
    def _open_virtual_camera(self):
        """開啟虛擬相機"""
        try:
            # 創建一個黑色背景
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # 添加一些文字
            cv2.putText(frame, "Virtual Camera", (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            self.virtual_frame = frame
            self.is_virtual = True
            logging.info("[資訊] 成功開啟虛擬相機")
            return True
            
        except Exception as e:
            logging.error(f"[錯誤] 開啟虛擬相機時發生錯誤: {str(e)}")
            return False
            
    def read_frame(self):
        """
        讀取一幀圖像，對於測試視頻以最大速度讀取
        
        Returns:
            tuple: (成功標誌, 幀數據)
        """
        try:
            # 如果是虛擬相機，直接返回虛擬幀
            if self.is_virtual:
                if self.virtual_frame is None:
                    self._init_virtual_camera()
                self.current_frame = self.virtual_frame.copy()
                return True, self.current_frame
            
            # 如果是測試視頻，以最大速度讀取，不限制幀率
            if self.is_test_video and hasattr(self, 'camera') and self.camera is not None:
                # 直接讀取新幀，不考慮幀率限制
                ret, frame = self.camera.read()
                
                # 處理循環播放
                if not ret or frame is None:
                    # 檢查是否到達視頻結尾
                    current_pos = self.camera.get(cv2.CAP_PROP_POS_FRAMES)
                    total_frames = self.camera.get(cv2.CAP_PROP_FRAME_COUNT)
                    
                    if total_frames > 0 and current_pos >= total_frames - 1:
                        logging.info("[資訊] 測試視頻播放完畢，重新從頭開始")
                        self.camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = self.camera.read()
                        
                        if not ret or frame is None:
                            logging.error("[錯誤] 重置測試視頻後仍無法讀取幀")
                            self.is_virtual = True
                            self.current_frame = self.virtual_frame.copy()
                            return True, self.current_frame
                    else:
                        logging.error("讀取幀失敗")
                        self.is_virtual = True
                        self.current_frame = self.virtual_frame.copy()
                        return True, self.current_frame
                
                self.current_frame = frame
                return True, frame
            
            # 检查是否有 Basler 相机
            if hasattr(self, 'pylon_camera') and self.pylon_camera is not None and self.pylon_camera.IsGrabbing():
                try:
                    # 尝试从 Basler 相机获取图像
                    grab_result = self.pylon_camera.RetrieveResult(1000, pylon.TimeoutHandling_Return)
                    if grab_result and grab_result.GrabSucceeded():
                        image = grab_result.Array
                        grab_result.Release()
                        self.current_frame = image
                        return True, image
                    if grab_result:
                        grab_result.Release()
                except Exception as e:
                    logging.error(f"从 Basler 相机读取帧时出错: {str(e)}")
                
            # 检查普通相机
            if self.camera is None:
                logging.error("相機未初始化")
                self.is_virtual = True
                self.current_frame = self.virtual_frame.copy()
                return True, self.current_frame
                
            if not self.camera.isOpened():
                logging.error("相機未打開")
                self.is_virtual = True
                self.current_frame = self.virtual_frame.copy()
                return True, self.current_frame
                
            ret, frame = self.camera.read()
            
            # 特殊處理測試視頻的循環播放
            if not ret or frame is None:
                # 檢查是否是測試視頻並且已經播放到結尾
                current_pos = self.camera.get(cv2.CAP_PROP_POS_FRAMES)
                total_frames = self.camera.get(cv2.CAP_PROP_FRAME_COUNT)
                
                # 如果是測試視頻並且到達了結尾，重置到開頭
                if total_frames > 0 and current_pos >= total_frames - 1:
                    logging.info("[資訊] 測試視頻播放完畢，重新從頭開始")
                    self.camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.camera.read()
                    
                    # 如果重置後仍然無法讀取，則切換到虛擬相機
                    if not ret or frame is None:
                        logging.error("[錯誤] 重置測試視頻後仍無法讀取幀")
                        self.is_virtual = True
                        self.current_frame = self.virtual_frame.copy()
                        return True, self.current_frame
                else:
                    # 其他情況下的讀取失敗，使用虛擬相機
                    logging.error("讀取幀失敗")
                    self.is_virtual = True
                    self.current_frame = self.virtual_frame.copy()
                    return True, self.current_frame
            
            self.current_frame = frame
            return True, frame
            
        except Exception as e:
            logging.error(f"讀取幀時發生錯誤: {str(e)}")
            self.is_virtual = True
            self.current_frame = self.virtual_frame.copy()
            return True, self.current_frame
            
    def release_all_cameras(self):
        """釋放所有相機資源"""
        try:
            self.is_virtual = False
            self.virtual_frame = None
            
            if self.camera is not None:
                if hasattr(self.camera, 'isOpened') and self.camera.isOpened():
                    self.camera.release()
                self.camera = None
                
            if hasattr(self, 'basler_camera') and self.basler_camera is not None:
                self.basler_camera.Close()
                self.basler_camera = None
                
        except Exception as e:
            logging.error(f"釋放相機資源時發生錯誤: {str(e)}")
            
        finally:
            self.camera = None
            self.basler_camera = None
            self.is_virtual = False
            self.virtual_frame = None

    def _open_test_video(self):
        """開啟測試視頻"""
        try:
            # 預設測試視頻路徑
            video_path = "testDate/colorConversion_output_2024-10-26_14-28-56_video_V6_200_206fps.mp4"
            
            # 檢查測試視頻是否存在
            if not os.path.exists(video_path):
                logging.warning(f"[警告] 預設測試視頻不存在: {video_path}")
                # 嘗試查找測試目錄中的其他視頻文件
                test_dir = "testDate"
                if os.path.exists(test_dir) and os.path.isdir(test_dir):
                    for file in os.listdir(test_dir):
                        if file.endswith(('.mp4', '.avi', '.mov')):
                            video_path = os.path.join(test_dir, file)
                            logging.info(f"[資訊] 找到其他測試視頻: {video_path}")
                            break
                
                # 如果仍然找不到，嘗試備用位置
                if not os.path.exists(video_path):
                    backup_paths = ["video/sample.mp4", "resources/test_video.mp4"]
                    for path in backup_paths:
                        if os.path.exists(path):
                            video_path = path
                            logging.info(f"[資訊] 使用備用測試視頻: {video_path}")
                            break
                    else:
                        logging.error("[錯誤] 找不到任何測試視頻")
                        # 如果所有嘗試都失敗，使用虛擬相機
                        return self._open_virtual_camera()

            logging.info(f"[資訊] 使用測試視頻: {video_path}")
            self.camera = cv2.VideoCapture(video_path)
            
            # 確認視頻是否成功打開
            if not self.camera.isOpened():
                logging.error(f"[錯誤] 無法打開測試視頻: {video_path}")
                return self._open_virtual_camera()
                
            # 獲取視頻的fps
            self.video_fps = self.camera.get(cv2.CAP_PROP_FPS)
            if self.video_fps <= 0 or self.video_fps > 1000:  # 無效的fps值
                self.video_fps = 30.0  # 使用默認值
            
            # 計算幀間隔時間（毫秒）
            self.frame_interval_ms = int(1000 / self.video_fps)
            
            logging.info(f"[資訊] 測試視頻幀率: {self.video_fps} FPS，幀間隔: {self.frame_interval_ms} ms")
                
            # 測試讀取第一幀
            ret, frame = self.camera.read()
            if not ret or frame is None:
                logging.error("[錯誤] 無法從測試視頻讀取幀")
                return self._open_virtual_camera()
                
            # 設定循環播放
            total_frames = int(self.camera.get(cv2.CAP_PROP_FRAME_COUNT))
            logging.info(f"[資訊] 測試視頻總幀數: {total_frames}")
            
            # 標記為測試視頻
            self.is_test_video = True
            
            logging.info("[資訊] 成功打開測試視頻")
            return True
            
        except Exception as e:
            logging.error(f"[錯誤] 開啟測試視頻時發生錯誤: {str(e)}")
            import traceback
            traceback.print_exc()
            # 如果發生任何錯誤，回退到虛擬相機
            return self._open_virtual_camera()

    def _open_usb_camera(self, source):
        """開啟 USB 相機"""
        try:
            logging.info(f"[資訊] 嘗試開啟相機源: {source}")
            # 在 macOS 上，我們只使用內建相機（索引 0）
            camera_index = 0
            if os.name == 'posix' and 'darwin' in os.uname().sysname.lower():
                logging.info("[資訊] 檢測到 macOS 系統")
                if source == "Built-in Camera":
                    # 使用內建相機
                    camera_index = 0
                    logging.info(f"[資訊] 使用內建相機，索引: {camera_index}")
                else:
                    # 嘗試解析其他相機索引
                    try:
                        if "USB Camera" in source:
                            camera_index = int(source.split()[-1])
                        else:
                            camera_index = int(source)
                    except ValueError:
                        logging.warning(f"[警告] 無法從 '{source}' 解析相機索引，使用預設值 0")
                        camera_index = 0
                    logging.info(f"[資訊] 使用其他相機，索引: {camera_index}")
                
                logging.info(f"[資訊] 在 macOS 上使用相機索引: {camera_index}")
                
                # 嘗試開啟相機
                logging.info(f"[資訊] 嘗試開啟相機，索引: {camera_index}")
                self.camera = cv2.VideoCapture(camera_index)
                if self.camera.isOpened():
                    logging.info(f"[資訊] 成功開啟相機，索引: {camera_index}")
                    # 設置相機屬性
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    self.camera.set(cv2.CAP_PROP_FPS, 30)
                    
                    # 測試讀取幾幀，確保相機穩定
                    for i in range(3):  # 減少測試幀數，避免長時間阻塞
                        logging.info(f"[資訊] 測試讀取第 {i+1} 幀...")
                        ret, frame = self.camera.read()
                        if not ret:
                            logging.warning(f"[警告] 無法讀取第 {i+1} 幀")
                            break
                        logging.info(f"[資訊] 成功讀取第 {i+1} 幀，尺寸: {frame.shape if frame is not None else 'None'}")
                        time.sleep(0.1)
                    
                    if not ret or frame is None:
                        logging.error("[錯誤] 無法從相機讀取穩定的幀")
                        self.release_all_cameras()
                        return False
                        
                    logging.info("[資訊] 成功初始化 macOS 相機")
                    return True
                else:
                    logging.error("[錯誤] 無法開啟 macOS 相機")
                    return False
            else:
                # 在其他系統上解析相機索引
                logging.info("非 macOS 系统")
                if "USB Camera" in source:
                    try:
                        camera_index = int(source.split()[-1])
                    except ValueError:
                        logging.warning(f"[警告] 無法從 '{source}' 解析相機索引，使用預設值 0")
                else:
                    try:
                        camera_index = int(source)
                    except ValueError:
                        logging.warning(f"[警告] 無法將 '{source}' 解析為相機索引，使用預設值 0")

            # 嘗試開啟相機
            logging.info(f"[資訊] 嘗試開啟相機，索引: {camera_index}")
            logging.info(f"[資訊] 嘗試開啟相機 {camera_index}")
            self.camera = cv2.VideoCapture(camera_index)

            if not self.camera.isOpened():
                logging.error(f"[錯誤] 無法開啟相機 {camera_index}")
                return False

            # 設定相機屬性
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # 測試讀取
            logging.info("[資訊] 測試讀取幀...")
            ret, frame = self.camera.read()
            if not ret or frame is None:
                logging.error(f"[錯誤] 無法從相機 {camera_index} 讀取幀")
                self.release_all_cameras()
                return False

            logging.info(f"[資訊] 成功開啟相機 {camera_index}")
            return True

        except Exception as e:
            logging.error(f"[錯誤] 開啟相機時發生錯誤: {str(e)}")
            self.release_all_cameras()
            return False

    def _open_basler_camera(self, source):
        """開啟 Basler 相機"""
        try:
            # 解析相機索引
            camera_index = int(source.split()[-1])
            
            # 獲取相機列表
            tlf = pylon.TlFactory.GetInstance()
            devices = tlf.EnumerateDevices()
            
            if not devices or camera_index >= len(devices):
                logging.error(f"找不到指定的 Basler 相機 {camera_index}")
                return False
            
            # 創建相機實例
            self.pylon_camera = pylon.InstantCamera(tlf.CreateDevice(devices[camera_index]))
            self.pylon_camera.Open()
            
            if not self.pylon_camera.IsOpen():
                logging.error(f"無法開啟 Basler 相機 {camera_index}")
                return False
            
            # 配置相機
            self.pylon_camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
            logging.info(f"成功開啟 Basler 相機 {camera_index}")
            return True
            
        except Exception as e:
            logging.error(f"開啟 Basler 相機時發生錯誤: {str(e)}")
            if self.pylon_camera:
                try:
                    self.pylon_camera.Close()
                except:
                    pass
                self.pylon_camera = None
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
            dict: 攝影機資訊，如果無法獲取則返回默認值
        """
        default_info = {
            'width': 640,
            'height': 480,
            'fps': 30,
            'frame_count': 0
        }

        try:
            if not self.camera or not self.camera.isOpened():
                if hasattr(self, 'pylon_camera') and self.pylon_camera:
                    # 獲取 Basler 相機資訊
                    try:
                        width = self.pylon_camera.Width.GetValue()
                        height = self.pylon_camera.Height.GetValue()
                        fps = self.pylon_camera.ResultingFrameRate.GetValue() if hasattr(self.pylon_camera, 'ResultingFrameRate') else 30
                        return {
                            'width': width,
                            'height': height,
                            'fps': fps,
                            'frame_count': 0  # Basler相機不提供總幀數
                        }
                    except Exception as e:
                        logging.warning(f"獲取Basler相機資訊失敗: {str(e)}")
                        return default_info
                else:
                    return default_info

            # 獲取OpenCV相機資訊
            info = {
                'width': int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': self.camera.get(cv2.CAP_PROP_FPS),
                'frame_count': int(self.camera.get(cv2.CAP_PROP_FRAME_COUNT))
            }

            # 驗證並修正資訊
            if info['width'] <= 0 or info['width'] > 4096:
                info['width'] = default_info['width']
            if info['height'] <= 0 or info['height'] > 4096:
                info['height'] = default_info['height']
            if info['fps'] <= 0 or info['fps'] > 240:
                info['fps'] = default_info['fps']
            if info['frame_count'] < 0:
                info['frame_count'] = default_info['frame_count']

            return info

        except Exception as e:
            logging.error(f"獲取攝影機資訊時發生錯誤: {str(e)}")
            return default_info

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
            import cv2 # type: ignore

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