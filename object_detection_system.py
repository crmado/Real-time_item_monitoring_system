import os

# Get the directory containing the script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Add OpenCV binary and library paths
cv2_bin_path = os.path.join(script_dir, 'bin')
cv2_lib_path = os.path.join(script_dir, 'lib')

if os.path.exists(cv2_bin_path):
    os.environ['PATH'] = cv2_bin_path + os.pathsep + os.environ['PATH']
if os.path.exists(cv2_lib_path):
    os.environ['PATH'] = cv2_lib_path + os.pathsep + os.environ['PATH']

import cv2

import signal
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import scrolledtext
import threading
import datetime
import logging
import time
from PIL import Image, ImageTk
import numpy as np
import sys
import locale

# 設定系統編碼
sys.setdefaultencoding('utf-8') if hasattr(sys, 'setdefaultencoding') else None
locale.setlocale(locale.LC_ALL, 'zh_TW.UTF-8')

# 設定 logging 的編碼
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("detection.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)



class ObjectDetectionSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("物件監測系統")
        self.version = "1.0.1"  # 版本號

        # 設置界面樣式
        self.setup_styles()

        # 設定日誌
        self.setup_logging()

        # 初始化變數
        self.is_monitoring = False
        self.current_count = 0
        self.camera = None
        self.detection_thread = None
        self.TEST_MODE = False  # 測試模式

        # 建立使用者介面
        self.create_ui()

        # 初始化背景減除器
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=20000,
            varThreshold=16,
            detectShadows=True
        )

        # 載入可用的視訊來源
        self.available_sources = self.get_available_sources()
        self.camera_combo['values'] = self.available_sources

        # 新增影片檢測相關的變數
        self.roi_height = 16
        self.roi_lines = None
        self.object_tracks = {}
        self.total_counter = 0
        self.frame_index = 1
        self.total_frames = 0
        self.camera_fps = 0

        self.target_count = 1000  # 預設預計數量
        self.buffer_point = 950  # 預設緩衝點
        self.alert_shown = False  # 用於追蹤是否已顯示警告

        # 初始化 ROI 相關變數
        self.dragging_roi = False
        self.roi_lines = [240]  # 預設在畫面中間偏上的位置
        self.saved_roi_percentage = 0.2  # 預設值為 20%

        # 啟動時檢查更新
        self.check_for_updates()


    def setup_logging(self):
        """設定日誌系統"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = os.path.join(
            log_dir,
            f"detection_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # 設定 logging 處理中文
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def create_ui(self):
        """創建使用者介面"""
        # 主要框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 設定主視窗最小大小
        self.root.minsize(800, 600)

        # 設定框架的權重，使其能夠隨視窗調整大小
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)  # 影像區域可以擴展
        main_frame.grid_columnconfigure(0, weight=1)

        # 上方控制區域
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.W)

        # 攝像頭選擇和按鈕並排
        ttk.Label(control_frame, text="Select Video Source:").grid(row=0, column=0, padx=5)
        self.camera_combo = ttk.Combobox(control_frame, width=30)
        self.camera_combo.grid(row=0, column=1, padx=5)

        self.test_button = ttk.Button(
            control_frame,
            text="Test Lenses",
            command=self.test_camera,
            style='Accent.TButton'
        )
        self.test_button.grid(row=0, column=2, padx=5)

        self.start_button = ttk.Button(
            control_frame,
            text="Start monitoring",
            command=self.toggle_monitoring,
            style='Accent.TButton'
        )
        self.start_button.grid(row=0, column=3, padx=5)

        # 中間影像顯示區域
        video_frame = ttk.Frame(main_frame, style='Video.TFrame')
        video_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 使用一個固定大小的框架來容納影像
        image_container = ttk.Frame(video_frame, width=640, height=480)
        image_container.grid(row=0, column=0, padx=2, pady=2)
        image_container.grid_propagate(False)  # 防止框架大小被內容影響

        # 影像標籤
        self.image_label = ttk.Label(
            image_container,
            style='Video.TLabel',
            text="Please select a camera"
        )
        self.image_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 綁定滑鼠事件
        self.image_label.bind('<Button-1>', self.start_roi_drag)
        self.image_label.bind('<B1-Motion>', self.drag_roi)
        self.image_label.bind('<ButtonRelease-1>', self.stop_roi_drag)

        # 右側設定區域
        settings_frame = ttk.Frame(video_frame)
        settings_frame.grid(row=0, column=1, padx=10, sticky=tk.N)

        # 當前計數顯示
        count_frame = ttk.Frame(settings_frame)
        count_frame.grid(row=0, column=0, pady=5, sticky=tk.EW)
        ttk.Label(count_frame, text="Current count：", style='Counter.TLabel').grid(row=0, column=0)
        self.count_label = ttk.Label(count_frame, text="0", style='CounterNum.TLabel')
        self.count_label.grid(row=0, column=1)

        # 預計數量設定
        target_frame = ttk.Frame(settings_frame)
        target_frame.grid(row=1, column=0, pady=5, sticky=tk.EW)
        ttk.Label(target_frame, text="Estimated quantity：").grid(row=0, column=0)
        self.target_entry = ttk.Entry(target_frame, width=10)
        self.target_entry.grid(row=0, column=1, padx=5)
        self.target_entry.insert(0, "1000")  # 預設值

        # 緩衝點設定
        buffer_frame = ttk.Frame(settings_frame)
        buffer_frame.grid(row=2, column=0, pady=5, sticky=tk.EW)
        ttk.Label(buffer_frame, text="Buffer Point：").grid(row=0, column=0)
        self.buffer_entry = ttk.Entry(buffer_frame, width=10)
        self.buffer_entry.grid(row=0, column=1, padx=5)
        self.buffer_entry.insert(0, "950")  # 預設值

        # 設定按鈕
        self.apply_settings_button = ttk.Button(
            settings_frame,
            text="Application Settings",
            command=self.apply_settings,
            style='Accent.TButton'
        )
        self.apply_settings_button.grid(row=3, column=0, pady=10)

        # 下方日誌區域
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        ttk.Label(log_frame, text="System log：").grid(row=0, column=0, sticky=tk.W)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=70,
            height=8,
            wrap=tk.WORD
        )
        self.log_text.grid(row=1, column=0, pady=5, sticky=(tk.W, tk.E))

        # 右下角資訊區域
        info_frame = ttk.Frame(main_frame)
        info_frame.grid(row=2, column=1, padx=30, pady=10, sticky=(tk.E, tk.S))

        ttk.Label(info_frame, text="Current time:").grid(row=0, column=0, sticky=tk.W)
        self.time_label = ttk.Label(info_frame, text="")
        self.time_label.grid(row=1, column=0, sticky=tk.W)

        ttk.Label(info_frame, text="Version:").grid(row=2, column=0, sticky=tk.W)
        self.version_label = ttk.Label(info_frame, text=self.version)
        self.version_label.grid(row=2, column=1, sticky=tk.W)

        # Start updating the time
        self.update_time()

    def update_time(self):
        """Update the current time display"""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.configure(text=current_time)
        self.root.after(1000, self.update_time)

    def apply_settings(self):
        """應用新的設定值"""
        try:
            new_target = int(self.target_entry.get())
            new_buffer = int(self.buffer_entry.get())

            if new_buffer >= new_target:
                self.log_message("Error: Buffer points must be less than the expected number")
                return

            if new_buffer < 0 or new_target < 0:
                self.log_message("Error: Value cannot be negative")
                return

            self.target_count = new_target
            self.buffer_point = new_buffer
            self.alert_shown = False  # 重設警告狀態
            self.log_message(f"Updated settings - Estimated quantity: {new_target}, Buffer point: {new_buffer}")

        except ValueError:
            self.log_message("Error: Please enter a valid number")

    def get_available_sources(self):
        """獲取可用的視訊來源"""
        sources = ["Test video"] if self.TEST_MODE else []

        # 檢查 libcamera 是否可用
        try:
            result = subprocess.run(['libcamera-vid', '--help'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            if result.returncode == 0:
                sources.append("libcamera")
        except FileNotFoundError:
            pass

        # 尋找可用的 USB 攝像頭
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # 讀取一幀來確認攝像頭是否真的可用
                ret, _ = cap.read()
                if ret:
                    sources.append(f"USB Camera {i}")
                cap.release()

        return sources

    def toggle_monitoring(self):
        """切換監測狀態"""
        if not self.is_monitoring:
            selected_source = self.camera_combo.get()
            if not selected_source:
                self.log_message("Error: Please select a video source")
                return

            self.start_monitoring(selected_source)
        else:
            self.stop_monitoring()

    def test_camera(self):
        """測試選擇的攝像頭"""
        selected_source = self.camera_combo.get()
        if not selected_source:
            self.log_message("Error: Please select a video source")
            return

        # 如果已經在測試中，則停止測試
        if hasattr(self, 'is_testing') and self.is_testing:
            self.stop_camera_test()
            return

        try:
            if selected_source == "libcamera":
                # 設定 libcamera 測試參數
                test_video_file = '/tmp/camera_test.h264'
                width = 640
                height = 480
                fps = 30

                # 建立 libcamera 測試命令
                command = f"libcamera-vid -o {test_video_file} --width {width} --height {height} " \
                          f"--framerate {fps} --codec h264 --denoise cdn_off --awb auto --level 4.2 -n --timeout 0"

                # 創建停止事件和執行緒
                self.test_stop_event = threading.Event()
                self.test_libcamera_thread = threading.Thread(
                    target=self.run_libcamera_test,
                    args=(command, self.test_stop_event, test_video_file)
                )
                self.test_libcamera_thread.start()

                # 等待檔案建立
                time.sleep(1)

                # 開啟影片串流
                self.test_camera_obj = cv2.VideoCapture(test_video_file)

                if not self.test_camera_obj.isOpened():
                    self.log_message("Error: Unable to open libcamera test stream")
                    return

                # 設定測試狀態和按鈕文字
                self.is_testing = True
                self.test_button.configure(text="Stop Test")

                # 啟動影像顯示執行緒
                self.test_display_thread = threading.Thread(
                    target=self.run_camera_test,
                    daemon=True
                )
                self.test_display_thread.start()

                # 設定測試狀態和按鈕文字
                self.is_testing = True
                self.test_button.configure(text="Stop Test")

                return

            # USB 攝像頭的處理邏輯
            camera_index = int(selected_source.split()[-1])
            self.test_camera_obj = cv2.VideoCapture(camera_index)

            if not self.test_camera_obj.isOpened():
                self.log_message("Error: Unable to open camera")
                return

            # 讀取一幀來初始化 ROI 線位置
            ret, frame = self.test_camera_obj.read()
            if ret:
                height = frame.shape[0]
                if not hasattr(self, 'roi_lines') or self.roi_lines is None:
                    self.roi_lines = [int(height * 0.2)]

                # 確保 ROI 線在有效範圍內
                self.roi_lines = [max(0, min(self.roi_lines[0], height))]

                # 顯示攝像頭資訊
                width = self.test_camera_obj.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = self.test_camera_obj.get(cv2.CAP_PROP_FRAME_HEIGHT)
                fps = self.test_camera_obj.get(cv2.CAP_PROP_FPS)
                self.log_message(f"Camera Information - Resolution: {width}x{height}, FPS: {fps}")

                roi_percentage = (self.roi_lines[0] / height) * 100
                self.log_message(f"Current ROI line position: {roi_percentage:.1f}%")

            # 設置測試狀態和按鈕文字
            self.is_testing = True
            self.test_button.configure(text="Stop Test")

            # 在新的執行緒中執行攝像頭測試
            self.test_thread = threading.Thread(target=self.run_camera_test, daemon=True)
            self.test_thread.start()

        except Exception as e:
            self.log_message(f"Camera test error: {str(e)}")
            self.stop_camera_test()

    def run_camera_test(self):
        """執行攝像頭測試的執行緒函數"""
        try:
            while self.is_testing:
                ret, frame = self.test_camera_obj.read()
                if ret:
                    frame_with_roi = frame.copy()
                    height, width = frame.shape[:2]

                    if self.roi_lines is not None:
                        line_y = self.roi_lines[0]

                        # 畫主要的 ROI 線
                        cv2.line(frame_with_roi,
                                 (0, line_y),
                                 (width, line_y),
                                 (0, 255, 0), 2)

                        # 畫檢測區域
                        cv2.rectangle(frame_with_roi,
                                      (0, line_y),
                                      (width, line_y + self.roi_height),
                                      (255, 0, 0), 1)

                        # 顯示 ROI 位置百分比
                        percentage = (line_y / height) * 100
                        text = f"ROI: {percentage:.1f}%"
                        cv2.putText(frame_with_roi,
                                    text,
                                    (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX,
                                    1,
                                    (0, 255, 0),
                                    2)

                        # 使用自定義函數顯示中文提示訊息
                        frame_with_roi = self.draw_chinese_text(
                            frame_with_roi,
                            "Drag the green line to adjust the ROI position",
                            (10, 60)
                        )

                    self.update_image_display(frame_with_roi)
                time.sleep(1 / 30)
        except Exception as e:
            self.log_message(f"Camera test execution error：{str(e)}")
        finally:
            self.stop_camera_test()

    def stop_camera_test(self):
        """停止攝像頭測試並保存設定"""
        try:
            # 停止 libcamera 進程
            if hasattr(self, 'test_stop_event'):
                self.test_stop_event.set()
                if hasattr(self, 'test_libcamera_thread'):
                    self.test_libcamera_thread.join()

            # 停止並清理一般攝像頭資源
            self.is_testing = False

            # 保存最後的 ROI 位置設定
            if hasattr(self, 'test_camera_obj') and self.test_camera_obj is not None:
                ret, frame = self.test_camera_obj.read()
                if ret and self.roi_lines is not None and len(self.roi_lines) > 0:
                    height = frame.shape[0]
                    self.saved_roi_percentage = self.roi_lines[0] / height
                    self.log_message(f"ROI line position settings saved: {self.saved_roi_percentage * 100:.1f}%")
        except Exception as e:
            self.log_message(f"An error occurred while saving ROI settings.：{str(e)}")
        finally:
            self.is_testing = False
            if hasattr(self, 'test_camera_obj') and self.test_camera_obj is not None:
                self.test_camera_obj.release()
                self.test_camera_obj = None
            self.test_button.configure(text="Test Lenses")
            self.log_message("Stop camera test")


    def start_monitoring(self, source):
        """開始監測"""
        try:
            # 檢查是否正在測試中
            if hasattr(self, 'is_testing') and self.is_testing:
                self.log_message("Please stop the test before starting it again")
                return

            if source == "Test video":
                # 使用指定的測試影片路徑
                video_path = r"testDate/colorConversion_output_2024-10-26_14-28-56_video_V6_200_206fps.mp4"
                if not os.path.exists(video_path):
                    self.log_message(f"No test video found: {video_path}")
                    return
                self.camera = cv2.VideoCapture(video_path)

                # 初始化 ROI 線位置
                if self.camera.isOpened():
                    _, first_frame = self.camera.read()
                    if first_frame is not None:
                        height = first_frame.shape[0]
                        self.roi_lines = [int(height * self.saved_roi_percentage)]
                        self.total_frames = int(self.camera.get(cv2.CAP_PROP_FRAME_COUNT))
                        self.camera.set(cv2.CAP_PROP_POS_FRAMES, 0)  # 重置影片位置
            elif source == "libcamera":
                # 設定 libcamera 參數
                raw_video_file = '/tmp/raw_output.h264'
                width = 640
                height = 480
                fps = 206

                command = f"libcamera-vid -o {raw_video_file} --width {width} --height {height} --framerate {fps} --codec h264 --denoise cdn_off --awb auto --level 4.2 -n --timeout 0"

                # 創建停止事件和執行緒
                self.stop_event = threading.Event()
                self.libcamera_thread = threading.Thread(
                    target=self.run_libcamera,
                    args=(command, self.stop_event)
                )
                self.libcamera_thread.start()

                # 設定相機為讀取 raw_video_file
                self.camera = cv2.VideoCapture(raw_video_file)
            else:
                camera_index = int(source.split()[-1])
                self.camera = cv2.VideoCapture(camera_index)
                if self.camera.isOpened():
                    _, first_frame = self.camera.read()
                    if first_frame is not None:
                        height = first_frame.shape[0]
                        self.roi_lines = [int(height * self.saved_roi_percentage)]
                        self.log_message(f"Use saved ROI line position: {self.saved_roi_percentage * 100:.1f}%")

            if not self.camera.isOpened():
                raise Exception("Unable to open video source")

            self.is_monitoring = True
            self.start_button.configure(text="Stop monitoring")
            self.log_message(f"Start monitoring - {source}")
            self.object_tracks = {}  # 重置軌跡追蹤
            self.total_counter = 0  # 重置計數器
            self.frame_index = 1  # 重置幀計數
            self.camera_fps = self.camera.get(cv2.CAP_PROP_FPS)

            # 在新執行緒中開始處理
            self.detection_thread = threading.Thread(
                target=self.process_video,
                daemon=True
            )
            self.detection_thread.start()

        except Exception as e:
            self.log_message(f"Error：{str(e)}")
            self.is_monitoring = False

    def stop_monitoring(self):
        if hasattr(self, 'stop_event'):
            self.stop_event.set()
            self.libcamera_thread.join()
        self.is_monitoring = False
        if self.camera:
            self.camera.release()
        self.camera = None
        self.start_button.configure(text="Start monitoring")
        self.log_message("Stop monitoring")

    def process_video(self):
        """處理視訊流"""
        while self.is_monitoring:
            try:
                ret, frame = self.camera.read()
                if not ret:
                    self.log_message("Video reading completed or unable to read the image")
                    break

                frame_with_detections = frame.copy()

                # 處理每個 ROI 線
                for line_y in self.roi_lines:
                    # 擷取 ROI 區域
                    roi = frame[line_y:line_y + self.roi_height, :]
                    processed = self.process_frame(roi)
                    objects = self.detect_objects(processed)

                    # 追蹤物件
                    new_tracks = {}
                    for (x, y, w, h, centroid) in objects:
                        cx, cy = map(int, centroid)
                        matched = False
                        for track_id, track in self.object_tracks.items():
                            # 物件匹配條件
                            if abs(cx - track['x']) < 64 and abs(line_y - track['y']) < 48:
                                new_tracks[track_id] = {'x': cx, 'y': line_y, 'count': track['count']}
                                matched = True
                                break

                        if not matched:
                            new_track_id = max(self.object_tracks.keys()) + 1 if self.object_tracks else 0
                            new_tracks[new_track_id] = {'x': cx, 'y': line_y, 'count': 0}

                    # 更新計數
                    for track_id, track in new_tracks.items():
                        if track['count'] == 0 and track['y'] == self.roi_lines[-1]:
                            self.total_counter += 1
                            track['count'] = 1
                            self.update_count(self.total_counter)

                    self.object_tracks = new_tracks

                    # 繪製檢測結果
                    height, width = frame.shape[:2]
                    cv2.line(frame_with_detections, (0, line_y), (width, line_y), (0, 255, 0), 2)

                    for (x, y, w, h, _) in objects:
                        cv2.rectangle(
                            frame_with_detections[line_y:line_y + self.roi_height, :],
                            (x, y), (x + w, y + h),
                            (0, 0, 255),
                            2
                        )

                # 添加資訊文字 - 顯示相機幀數
                cv2.putText(
                    frame_with_detections,
                    f"FPS: {self.camera_fps:.2f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

                # 更新顯示
                self.update_image_display(frame_with_detections)
                self.frame_index += 1

                # 控制處理速率，根據影片 FPS 調整
                time.sleep(1 / self.camera_fps)


            except Exception as e:
                self.log_message(f"Handling Errors：{str(e)}")
                break

        self.stop_monitoring()

    def process_frame(self, frame):
        """處理單幀影像"""
        # 使用背景減除器
        fg_mask = self.bg_subtractor.apply(frame)

        # 影像模糊化
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)

        # 邊緣檢測
        edges = cv2.Canny(blurred, 50, 110)

        # 使用遮罩
        result = cv2.bitwise_and(edges, edges, mask=fg_mask)

        # 二值化
        _, thresh = cv2.threshold(result, 30, 255, cv2.THRESH_BINARY)

        # 膨脹操作
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=1)

        # 閉合操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        closed = cv2.morphologyEx(dilated, cv2.MORPH_CLOSE, kernel)

        return closed

    def detect_objects(self, processed, min_area=10, max_area=150):
        """檢測物件"""
        # 使用您原有的detect_objects函數邏輯
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            processed,
            connectivity=4
        )
        valid_objects = []
        for i in range(1, num_labels):
            area = stats[i, cv2.CC_STAT_AREA]
            if min_area < area < max_area:
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP]
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                centroid = centroids[i]
                valid_objects.append((x, y, w, h, centroid))
        return valid_objects

    def draw_detection_results(self, frame, objects):
        """在影像上繪製檢測結果"""
        for x, y, w, h, _ in objects:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    def update_image_display(self, frame):
        """更新影像顯示"""
        try:
            # 使用固定的顯示大小
            display_width = 640
            display_height = 480

            # 轉換 OpenCV 的 BGR 格式為 RGB 格式
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 調整影像大小，保持比例
            frame_height, frame_width = frame.shape[:2]
            aspect_ratio = frame_width / frame_height

            if display_width / display_height > aspect_ratio:
                new_height = display_height
                new_width = int(display_height * aspect_ratio)
            else:
                new_width = display_width
                new_height = int(display_width / aspect_ratio)

            # 調整影像大小
            img = Image.fromarray(rgb_frame)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 轉換為 Tkinter 可用的格式
            img_tk = ImageTk.PhotoImage(image=img)

            # 更新顯示
            self.image_label.configure(image=img_tk)
            self.image_label.image = img_tk

        except Exception as e:
            self.log_message(f"An error occurred while updating the image display：{str(e)}")

    def update_count(self, count):
        """更新計數顯示並檢查閾值"""
        if count != self.current_count:
            self.current_count = count
            self.count_label.configure(text=str(count))
            # self.log_message(f"檢測到 {count} 個物件")

            # 檢查是否達到緩衝點
            if count >= self.buffer_point and not self.alert_shown:
                self.show_buffer_alert()
                self.alert_shown = True

            # 檢查是否達到預計數量
            if count >= self.target_count:
                self.show_target_reached()
                self.stop_monitoring()

    def run_libcamera(self, command, stop_event):
        try:
            pipe = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                preexec_fn=os.setsid
            )
            while not stop_event.is_set():
                time.sleep(0.1)
            os.killpg(os.getpgid(pipe.pid), signal.SIGTERM)
        except Exception as e:
            self.log_message(f"libcamera Execution Error：{e}")

    def run_libcamera_test(self, command, stop_event, video_file):
        """執行 libcamera 測試"""
        try:
            # 啟動 libcamera-vid 進程
            process = subprocess.Popen(
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )

            while not stop_event.is_set():
                time.sleep(0.1)

            # 清理資源
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            if os.path.exists(video_file):
                os.remove(video_file)

        except Exception as e:
            self.log_message(f"libcamera test error: {str(e)}")
        finally:
            self.stop_camera_test()

    def show_buffer_alert(self):
        """顯示緩衝點警告"""
        import tkinter.messagebox as messagebox
        messagebox.showwarning(
            "Buffer point warning",
            f"The buffer point ({self.buffer_point}) has been reached and the expected number is about to be reached!"
        )

    def show_target_reached(self):
        """顯示達到預計數量通知"""
        import tkinter.messagebox as messagebox
        messagebox.showinfo(
            "Completion Notification",
            f"The expected number ({self.target_count}) has been reached!"
        )

    def setup_styles(self):
        """設置界面樣式"""
        style = ttk.Style()

        # 設置影像顯示區域的樣式
        style.configure(
            'Video.TFrame',
            background='#f0f0f0',
            borderwidth=2,
            relief='solid'
        )

        style.configure(
            'Video.TLabel',
            background='#e0e0e0',
            font=('Arial', 12)
        )

        # 設置計數器樣式
        style.configure(
            'Counter.TLabel',
            font=('Arial', 12, 'bold')
        )

        style.configure(
            'CounterNum.TLabel',
            font=('Arial', 14, 'bold'),
            foreground='#2E8B57'
        )

        # 設置按鈕樣式
        style.configure(
            'Accent.TButton',
            font=('Arial', 10, 'bold'),
            background='#2E8B57'
        )

        style.configure(
            'Settings.TFrame',
            padding=5,
            relief='groove'
        )

        style.configure(
            'Settings.TLabel',
            font=('Arial', 10),
            padding=2
        )

        style.configure(
            'Settings.TEntry',
            padding=2
        )

    def log_message(self, message):
        """記錄訊息到日誌"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"

            # 更新UI日誌
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)

            # 寫入系統日誌
            logging.info(message.encode('utf-8').decode('utf-8'))
        except Exception as e:
            print(f"An error occurred while logging：{str(e)}")

    def check_for_updates(self):
        """檢查更新"""
        try:
            # 檢查是否為 Git 倉庫
            if not os.path.exists('.git'):
                self.log_message("Version control not set, skipping update check")
                return

            # 檢查遠端倉庫更新
            result = subprocess.run(
                ['git', 'remote', '-v'],
                capture_output=True,
                text=True
            )

            if 'origin' not in result.stdout:
                self.log_message("Remote repository not set, skipping update check")
                return

            subprocess.run(['git', 'fetch', 'origin'], check=True)
            result = subprocess.run(
                ['git', 'status', '-uno'],
                capture_output=True,
                text=True
            )

            if "Your branch is behind" in result.stdout:
                self.prompt_update()
        except Exception as e:
            self.log_message(f"An error occurred while checking for updates: {e}")

    def prompt_update(self):
        if messagebox.askyesno("Update Tips", "A new version has been found. Do you want to update?"):
            self.perform_update()

    def perform_update(self):
        try:
            subprocess.run(['git', 'pull'], check=True)
            messagebox.showinfo("Update Complete", "The program has been updated, please restart")
            self.root.quit()
        except Exception as e:
            messagebox.showerror("Update failed", f"An error occurred during the update process: {e}")

    def start_roi_drag(self, event):
        """開始拖動 ROI 線"""
        if hasattr(self, 'test_camera_obj') and self.test_camera_obj is not None:
            self.dragging_roi = True
            self.update_roi_from_mouse(event.y)

    def drag_roi(self, event):
        """拖動 ROI 線"""
        if self.dragging_roi:
            self.update_roi_from_mouse(event.y)

    def stop_roi_drag(self, event):
        """停止拖動 ROI 線"""
        self.dragging_roi = False

    def update_roi_from_mouse(self, mouse_y):
        """根據滑鼠位置更新 ROI 線"""
        try:
            if hasattr(self, 'test_camera_obj') and self.test_camera_obj is not None:
                # 獲取顯示區域的實際大小
                display_height = self.image_label.winfo_height()

                # 防止超出範圍
                mouse_y = max(0, min(mouse_y, display_height))

                # 計算實際影像中的位置
                ret, frame = self.test_camera_obj.read()
                if ret:
                    actual_height = frame.shape[0]
                    roi_y = int((mouse_y / display_height) * actual_height)

                    # 更新 ROI 線位置
                    self.roi_lines = [roi_y]

                    # 暫存位置百分比
                    percentage = roi_y / actual_height
                    self.saved_roi_percentage = percentage  # 即時更新暫存值

                    # 記錄位置到日誌
                    self.log_message(f"ROI Line position updated: {percentage * 100:.1f}%")

        except Exception as e:
            self.log_message(f"An error occurred while updating the ROI position：{str(e)}")

    def draw_chinese_text(self, img, text, position, font_size=0.6, color=(0, 255, 0), thickness=2):
        """在圖片上繪製中文文字"""
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np

        # 將 OpenCV 的 BGR 圖片轉換為 PIL 的 RGB 圖片
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)

        # 字體路徑優先順序
        font_paths = [
            "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # Linux WQY微米黑
            "/usr/share/fonts/wqy-microhei/wqy-microhei.ttc",  # 另一個可能的路徑
            "/usr/share/fonts/chinese/TrueType/wqy-microhei.ttc",
            "c:/windows/fonts/msjh.ttc"  # Windows 微軟正黑體
        ]

        # 嘗試載入字體
        font = None
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, int(font_size * 40))
                break
            except:
                continue

        # 如果沒有找到任何中文字體，使用默認字體
        if font is None:
            try:
                # 嘗試使用系統默認字體
                font = ImageFont.load_default()
                self.log_message("Warning: Chinese font not found, using system default font")
            except:
                self.log_message("Error: Unable to load any fonts")
                return img

        # 計算文字大小來調整位置
        try:
            text_width, text_height = draw.textsize(text, font=font)
        except:
            text_width, text_height = font.getbbox(text)[2:]

        # 繪製文字
        try:
            draw.text(position, text, font=font, fill=color[::-1])  # 注意：PIL 使用 RGB，而 OpenCV 使用 BGR
        except Exception as e:
            self.log_message(f"An error occurred while drawing text：{str(e)}")
            return img

        # 將 PIL 圖片轉回 OpenCV 格式
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def main():
    root = tk.Tk()
    app = ObjectDetectionSystem(root)
    root.mainloop()


if __name__ == "__main__":
    main()