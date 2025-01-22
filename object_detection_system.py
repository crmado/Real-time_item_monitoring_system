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


class ObjectDetectionSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("物件監測系統")
        self.version = "1.0.0"  # 版本號

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

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
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
        ttk.Label(control_frame, text="選擇視訊來源：").grid(row=0, column=0, padx=5)
        self.camera_combo = ttk.Combobox(control_frame, width=30)
        self.camera_combo.grid(row=0, column=1, padx=5)

        self.start_button = ttk.Button(
            control_frame,
            text="開始監測",
            command=self.toggle_monitoring,
            style='Accent.TButton'
        )
        self.start_button.grid(row=0, column=2, padx=5)

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
            text="請選擇攝像頭"
        )
        self.image_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 右側設定區域
        settings_frame = ttk.Frame(video_frame)
        settings_frame.grid(row=0, column=1, padx=10, sticky=tk.N)

        # 當前計數顯示
        count_frame = ttk.Frame(settings_frame)
        count_frame.grid(row=0, column=0, pady=5, sticky=tk.EW)
        ttk.Label(count_frame, text="當前計數：", style='Counter.TLabel').grid(row=0, column=0)
        self.count_label = ttk.Label(count_frame, text="0", style='CounterNum.TLabel')
        self.count_label.grid(row=0, column=1)

        # 預計數量設定
        target_frame = ttk.Frame(settings_frame)
        target_frame.grid(row=1, column=0, pady=5, sticky=tk.EW)
        ttk.Label(target_frame, text="預計數量：").grid(row=0, column=0)
        self.target_entry = ttk.Entry(target_frame, width=10)
        self.target_entry.grid(row=0, column=1, padx=5)
        self.target_entry.insert(0, "1000")  # 預設值

        # 緩衝點設定
        buffer_frame = ttk.Frame(settings_frame)
        buffer_frame.grid(row=2, column=0, pady=5, sticky=tk.EW)
        ttk.Label(buffer_frame, text="緩衝點：").grid(row=0, column=0)
        self.buffer_entry = ttk.Entry(buffer_frame, width=10)
        self.buffer_entry.grid(row=0, column=1, padx=5)
        self.buffer_entry.insert(0, "950")  # 預設值

        # 設定按鈕
        self.apply_settings_button = ttk.Button(
            settings_frame,
            text="應用設定",
            command=self.apply_settings,
            style='Accent.TButton'
        )
        self.apply_settings_button.grid(row=3, column=0, pady=10)

        # 下方日誌區域
        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=2, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        ttk.Label(log_frame, text="系統日誌：").grid(row=0, column=0, sticky=tk.W)

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

        ttk.Label(info_frame, text="當前時間:").grid(row=0, column=0, sticky=tk.W)
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
                self.log_message("錯誤：緩衝點必須小於預計數量")
                return

            if new_buffer < 0 or new_target < 0:
                self.log_message("錯誤：數值不能為負數")
                return

            self.target_count = new_target
            self.buffer_point = new_buffer
            self.alert_shown = False  # 重設警告狀態
            self.log_message(f"已更新設定 - 預計數量：{new_target}，緩衝點：{new_buffer}")

        except ValueError:
            self.log_message("錯誤：請輸入有效的數字")

    def get_available_sources(self):
        """獲取可用的視訊來源"""
        sources = ["測試影片"] if self.TEST_MODE else []

        # 檢查 libcamera 是否可用
        try:
            result = subprocess.run(['libcamera-vid', '--help'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            if result.returncode == 0:
                sources.append("libcamera")
        except FileNotFoundError:
            pass

        # 尋找可用的攝像頭
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                sources.append(f"攝像頭 {i}")
                cap.release()

        return sources

    def toggle_monitoring(self):
        """切換監測狀態"""
        if not self.is_monitoring:
            selected_source = self.camera_combo.get()
            if not selected_source:
                self.log_message("錯誤：請選擇視訊來源")
                return

            self.start_monitoring(selected_source)
        else:
            self.stop_monitoring()

    def start_monitoring(self, source):
        """開始監測"""
        try:
            if source == "測試影片":
                # 使用指定的測試影片路徑
                video_path = r"testDate/colorConversion_output_2024-10-26_14-28-56_video_V6_200_206fps.mp4"
                if not os.path.exists(video_path):
                    self.log_message(f"找不到測試影片: {video_path}")
                    return
                self.camera = cv2.VideoCapture(video_path)

                # 初始化 ROI 線位置
                _, first_frame = self.camera.read()
                if first_frame is not None:
                    height, _ = first_frame.shape[:2]
                    self.roi_lines = [int(height * 0.2)]
                    self.total_frames = int(self.camera.get(cv2.CAP_PROP_FRAME_COUNT))
                    # 重置視訊位置
                    self.camera.set(cv2.CAP_PROP_POS_FRAMES, 0)
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
                    height, _ = first_frame.shape[:2]
                    self.roi_lines = [int(height * 0.2)]

            if not self.camera.isOpened():
                raise Exception("無法開啟視訊來源")

            self.is_monitoring = True
            self.start_button.configure(text="停止監測")
            self.log_message(f"開始監測 - {source}")
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
            self.log_message(f"錯誤：{str(e)}")
            self.is_monitoring = False

    def stop_monitoring(self):
        if hasattr(self, 'stop_event'):
            self.stop_event.set()
            self.libcamera_thread.join()
        self.is_monitoring = False
        if self.camera:
            self.camera.release()
        self.camera = None
        self.start_button.configure(text="開始監測")
        self.log_message("停止監測")

    def process_video(self):
        """處理視訊流"""
        while self.is_monitoring:
            try:
                ret, frame = self.camera.read()
                if not ret:
                    self.log_message("視訊讀取完畢或無法讀取影像")
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
                self.log_message(f"處理錯誤：{str(e)}")
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
            self.log_message(f"更新影像顯示時發生錯誤：{str(e)}")

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
            self.log_message(f"libcamera 執行錯誤：{e}")

    def show_buffer_alert(self):
        """顯示緩衝點警告"""
        import tkinter.messagebox as messagebox
        messagebox.showwarning(
            "緩衝點警告",
            f"已達到緩衝點（{self.buffer_point}個），即將達到預計數量！"
        )

    def show_target_reached(self):
        """顯示達到預計數量通知"""
        import tkinter.messagebox as messagebox
        messagebox.showinfo(
            "完成通知",
            f"已達到預計數量（{self.target_count}個）！"
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
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        # 更新UI日誌
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)

        # 寫入系統日誌
        logging.info(message)

    def check_for_updates(self):
        try:
            # 檢查遠端倉庫更新
            subprocess.run(['git', 'fetch', 'origin'], check=True)
            result = subprocess.run(['git', 'status', '-uno'],
                                    capture_output=True,
                                    text=True)
            if "Your branch is behind" in result.stdout:
                self.prompt_update()
        except Exception as e:
            self.log_message(f"檢查更新失敗: {e}")

    def prompt_update(self):
        if messagebox.askyesno("更新提示", "發現新版本，是否更新？"):
            self.perform_update()

    def perform_update(self):
        try:
            subprocess.run(['git', 'pull'], check=True)
            messagebox.showinfo("更新完成", "程式已更新，請重新啟動")
            self.root.quit()
        except Exception as e:
            messagebox.showerror("更新失敗", f"更新過程發生錯誤: {e}")


def main():
    root = tk.Tk()
    app = ObjectDetectionSystem(root)
    root.mainloop()


if __name__ == "__main__":
    main()