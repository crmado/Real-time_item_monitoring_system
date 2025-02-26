"""
物件偵測控制器
負責協調影像處理和物件偵測的核心邏輯
"""

import threading
import time
import logging
from tkinter import messagebox

import cv2
from queue import Queue, Empty
import concurrent.futures
from utils.language import get_text


class DetectionController:
    """物件偵測控制器類別"""

    def __init__(self, camera_manager, image_processor):
        """
        初始化物件偵測控制器

        Args:
            camera_manager: 攝影機管理器實例
            image_processor: 影像處理器實例
        """
        self._run_libcamera_test = None
        self.camera_manager = camera_manager
        self.image_processor = image_processor

        # 狀態變數
        self.is_monitoring = False
        self.is_testing = False
        self.current_count = 0
        self.total_counter = 0

        # 設定值
        self.target_count = 1000
        self.buffer_point = 950
        self.alert_shown = False

        # ROI 相關設定
        self.dragging_roi = False
        self.roi_height = 16
        self.roi_lines = [240]  # 預設值
        self.saved_roi_percentage = 0.2

        # 物件追蹤資料
        self.object_tracks = {}
        self.frame_index = 1

        # 效能追蹤相關變數
        self.frame_stats = {
            'captured': 0,  # 擷取的幀數
            'processed': 0,  # 處理的幀數
            'displayed': 0,  # 顯示的幀數
            'dropped': 0  # 丟棄的幀數
        }
        self.last_time = time.time()
        self.performance_lock = threading.Lock()

        self.frame_queue = Queue(maxsize=30)  # 原始影像佇列
        self.result_queue = Queue(maxsize=30)  # 處理結果佇列
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)

        # 測試相關變數
        self.is_testing = False
        self.test_camera_obj = None
        self.test_stop_event = None
        self.test_libcamera_thread = None

        # 註冊回調函數的字典
        self.callbacks = {
            'test_started': None,
            'test_stopped': None,
            'frame_processed': None,
            'monitoring_started': None,
            'monitoring_stopped': None,
            'count_updated': None
        }

    def start_roi_drag(self, mouse_y):
        """
        開始拖動 ROI 線

        Args:
            mouse_y: 滑鼠 Y 座標
        """
        self.dragging_roi = True
        self.update_roi_position(mouse_y)

    def update_roi_position(self, mouse_y):
        """更新 ROI 線位置"""
        try:
            if not self.dragging_roi:
                return

            frame = None
            if self.is_testing and self.test_camera_obj:
                ret, frame = self.test_camera_obj.read()
            elif self.is_monitoring and self.camera_manager.camera:
                ret, frame = self.camera_manager.read_frame()

            if frame is not None:
                height = frame.shape[0]

                # 確保 ROI 線在有效範圍內
                roi_y = min(max(0, mouse_y), height)

                # 更新 ROI 線位置
                self.roi_lines = [roi_y]

                # 更新儲存的百分比位置
                self.saved_roi_percentage = roi_y / height

                logging.info(f"ROI Line position update:: {self.saved_roi_percentage * 100:.1f}%")

        except Exception as e:
            logging.error(f"An error occurred while updating the ROI position：{str(e)}")

    def stop_roi_drag(self):
        """停止拖動 ROI 線"""
        try:
            if not self.dragging_roi:
                return

            self.dragging_roi = False

            # 記錄最後的 ROI 位置設定
            frame = None
            if self.is_testing and self.test_camera_obj:
                ret, frame = self.test_camera_obj.read()
            elif self.is_monitoring and self.camera_manager.camera:
                ret, frame = self.camera_manager.read_frame()

            if frame is not None and self.roi_lines:
                height = frame.shape[0]
                self.saved_roi_percentage = self.roi_lines[0] / height
                logging.info(f"ROI Line position settings saved: {self.saved_roi_percentage * 100:.1f}%")

        except Exception as e:
            logging.error(f"An error occurred while saving ROI settings.：{str(e)}")
        finally:
            self.dragging_roi = False

    def start_monitoring(self, source):
        """
        開始監測

        Args:
            source: 視訊來源名稱
        """
        try:
            if self.is_testing:
                logging.warning("Please stop the test before starting it again")
                return False

            if not self.camera_manager.open_camera(source):
                return False

            self.is_monitoring = True
            self.object_tracks = {}
            self.total_counter = 0
            self.frame_index = 1

            # 啟動處理執行緒
            self.detection_thread = threading.Thread(
                target=self._process_video,
                daemon=True
            )
            self.detection_thread.start()

            self._notify('monitoring_started')
            return True

        except Exception as e:
            logging.error(f"An error occurred while starting the check：{str(e)}")
            return False

    def stop_monitoring(self):
        """停止監測"""
        self.is_monitoring = False
        self.camera_manager.release_camera()
        self.object_tracks = {}  # 重置物件追蹤資料
        self._notify('monitoring_stopped')

    def _process_video(self):
        """改進的視訊處理主函數"""
        # 啟動影像擷取線程
        capture_thread = threading.Thread(
            target=self._capture_frames,
            daemon=True
        )
        capture_thread.start()

        # 啟動結果處理線程
        display_thread = threading.Thread(
            target=self._display_results,
            daemon=True
        )
        display_thread.start()

        # 主處理循環
        while self.is_monitoring:
            try:
                frame = self.frame_queue.get(timeout=0.1)
                if frame is None:
                    break

                # 提交處理任務到線程池
                self.thread_pool.submit(self._process_single_frame, frame)

            except Empty:
                continue

    def _capture_frames(self):
        """專門的影像擷取線程"""
        while self.is_monitoring:
            ret, frame = self.camera_manager.read_frame()
            if not ret or frame is None:
                self.frame_queue.put(None)
                break

            self._update_frame_stats('captured')

            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                    self._update_frame_stats('dropped')
                except Empty:
                    pass

            self.frame_queue.put(frame)

    def _process_single_frame(self, frame):
        """處理單一影像幀並監控效能"""
        try:
            # 記錄開始時間
            start_process_time = time.time()

            frame_with_detections = frame.copy()

            # 處理每個 ROI 線
            for line_y in self.roi_lines:
                roi = frame[line_y:line_y + self.roi_height, :]
                processed = self.image_processor.process_frame(roi)
                objects = self.image_processor.detect_objects(processed)
                self._update_object_tracking(objects, line_y)
                self._draw_detection_results(frame_with_detections, objects, line_y)

            # 計算處理時間
            process_time = (time.time() - start_process_time) * 1000  # 轉換為毫秒

            # 記錄處理時間
            with self.performance_lock:
                self.current_frame_time = process_time

            self._update_frame_stats('processed')
            self.result_queue.put(frame_with_detections)

            # 記錄到日誌
            logging.debug(f"Frame processing time: {process_time:.2f}ms")

        except Exception as e:
            logging.error(f"處理影像時發生錯誤：{str(e)}")

    def _update_performance_stats(self):
        """更新效能統計資訊"""
        self.frame_count += 1
        self.total_frames += 1
        current_time = time.time()
        time_diff = current_time - self.last_time

        # 每秒更新一次統計資訊
        if time_diff >= 1.0:
            # 計算 FPS
            current_fps = self.frame_count / time_diff
            self.fps = current_fps
            self.fps_history.append(current_fps)

            # 保持 FPS 歷史記錄在合理範圍內
            if len(self.fps_history) > 60:  # 保留最近一分鐘的數據
                self.fps_history.pop(0)

            # 計算平均處理時間
            avg_process_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0

            # 記錄統計資訊
            logging.info(
                f"Performance Stats:\n"
                f"Current FPS: {current_fps:.2f}\n"
                f"Average FPS: {sum(self.fps_history) / len(self.fps_history):.2f}\n"
                f"Average Processing Time: {avg_process_time * 1000:.2f}ms\n"
                f"Total Frames: {self.total_frames}"
            )

            # 重置計數器
            self.frame_count = 0
            self.last_time = current_time

    def _display_results(self):
        """顯示處理結果的專門線程"""
        while self.is_monitoring:
            try:
                frame_with_detections = self.result_queue.get(timeout=0.1)
                if frame_with_detections is None:
                    break

                self._notify('frame_processed', frame_with_detections)
                self._update_frame_stats('displayed')

            except Empty:
                continue


    def _update_object_tracking(self, objects, line_y):
        """
        更新物件追蹤狀態

        Args:
            objects: 檢測到的物件列表
            line_y: ROI 線的 y 座標
        """
        new_tracks = {}
        for (x, y, w, h, centroid) in objects:
            cx, cy = map(int, centroid)
            matched = False

            # 尋找匹配的追蹤物件
            for track_id, track in self.object_tracks.items():
                if abs(cx - track['x']) < 64 and abs(line_y - track['y']) < 48:
                    new_tracks[track_id] = {
                        'x': cx,
                        'y': line_y,
                        'count': track['count']
                    }
                    matched = True
                    break

            # 如果沒有匹配，建立新的追蹤
            if not matched:
                new_track_id = max(self.object_tracks.keys()) + 1 if self.object_tracks else 0
                new_tracks[new_track_id] = {'x': cx, 'y': line_y, 'count': 0}

        # 更新計數
        for track_id, track in new_tracks.items():
            if track['count'] == 0 and track['y'] == self.roi_lines[-1]:
                self.total_counter += 1
                track['count'] = 1
                self._update_count(self.total_counter)

        self.object_tracks = new_tracks

    def _draw_detection_results(self, frame, objects, line_y):
        """在影像上繪製檢測結果和效能資訊"""
        # 繪製檢測結果
        height, width = frame.shape[:2]
        cv2.line(frame, (0, line_y), (width, line_y), (0, 255, 0), 2)

        for (x, y, w, h, _) in objects:
            cv2.rectangle(
                frame[line_y:line_y + self.roi_height, :],
                (x, y), (x + w, y + h),
                (0, 0, 255),
                2
            )

        # 顯示效能資訊
        with self.performance_lock:
            # 計算每秒的 FPS
            current_time = time.time()
            time_diff = current_time - self.last_time

            if time_diff >= 1.0:
                self.current_fps = {
                    'capture': self.frame_stats['captured'] / time_diff,
                    'process': self.frame_stats['processed'] / time_diff,
                    'display': self.frame_stats['displayed'] / time_diff
                }
                self.frame_stats = {k: 0 for k in self.frame_stats}  # 重置計數器
                self.last_time = current_time

            # 使用多行顯示效能資訊
            line_height = 30  # 行高
            stats_texts = [
                f"Capture FPS: {getattr(self, 'current_fps', {}).get('capture', 0):.1f}",
                f"Process FPS: {getattr(self, 'current_fps', {}).get('process', 0):.1f}",
                f"Display FPS: {getattr(self, 'current_fps', {}).get('display', 0):.1f}",
                f"Dropped Frames: {self.frame_stats['dropped']}"
            ]

            for i, text in enumerate(stats_texts):
                cv2.putText(
                    frame,
                    text,
                    (10, 30 + i * line_height),  # 每行向下移動 line_height 像素
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

        return frame


    def _update_count(self, count):
        """
        更新計數並檢查閾值

        Args:
            count: 新的計數值
        """
        if count != self.current_count:
            self.current_count = count
            self._notify('count_updated', count)

            # 檢查是否達到緩衝點
            if count >= self.buffer_point and not self.alert_shown:
                self._show_buffer_alert()
                self.alert_shown = True

            # 檢查是否達到目標數量
            if count >= self.target_count:
                self._show_target_reached()
                self.stop_monitoring()

    def _show_buffer_alert(self):
        """顯示緩衝點警告"""
        messagebox.showwarning(
            get_text("buffer_warning", "緩衝點警告"),
            get_text("buffer_warning_msg", "緩衝點已達 ({})，即將達到預計數量！").format(self.buffer_point)
        )

    def _show_target_reached(self):
        """顯示達到目標數量通知"""
        messagebox.showinfo(
            get_text("target_reached", "完成通知"),
            get_text("target_reached_msg", "已達到預計數量 ({})！").format(self.target_count)
        )

    def set_callback(self, button_name, callback):
        """
        設置按鈕回調函數

        Args:
            button_name: 按鈕名稱
            callback: 回調函數
        """
        # 保存回調函數供下拉選單事件使用
        self.callbacks[button_name] = callback

        # 只為存在的按鈕設置命令
        if button_name == 'start':
            self.start_button.configure(command=callback)

    def _notify(self, event_name, *args):
        """
        通知註冊的回調函數

        Args:
            event_name: 事件名稱
            *args: 傳遞給回調函數的參數
        """
        if event_name in self.callbacks and self.callbacks[event_name]:
            self.callbacks[event_name](*args)

    def update_settings(self, target_count, buffer_point):
        """
        更新設定值

        Args:
            target_count: 目標數量
            buffer_point: 緩衝點
        """
        if buffer_point >= target_count:
            logging.error(get_text("error_buffer_target", "緩衝點必須小於預計數量"))
            return False

        if buffer_point < 0 or target_count < 0:
            logging.error(get_text("error_negative", "數值不能為負數"))
            return False

        self.target_count = target_count
        self.buffer_point = buffer_point
        self.alert_shown = False
        return True

    def test_camera(self, source):
        """
        測試選擇的攝像頭

        Args:
            source: 視訊來源名稱
        """
        if not source:
            logging.error("Error: Please select a video source")
            return False

        # 如果已經在測試中，則停止測試
        if self.is_testing:
            self.stop_camera_test()
            return True

        try:
            # self._notify('test_started')  # 通知開始測試

            if source == "libcamera":
                return self._test_libcamera()
            else:
                return self._test_usb_camera(source)

        except Exception as e:
            logging.error(f"Camera test error:{str(e)}")
            self.stop_camera_test()
            return False

    def _test_libcamera(self):
        """測試 libcamera"""
        test_video_file = '/tmp/camera_test.h264'
        width = 640
        height = 480
        fps = 30

        command = (
            f"libcamera-vid -o {test_video_file} "
            f"--width {width} --height {height} "
            f"--framerate {fps} --codec h264 "
            f"--denoise cdn_off --awb auto --level 4.2 -n --timeout 0"
        )

        self.test_stop_event = threading.Event()
        self.test_libcamera_thread = threading.Thread(
            target=self._run_libcamera_test,
            args=(command, self.test_stop_event, test_video_file)
        )
        self.test_libcamera_thread.start()

        # 等待檔案建立
        time.sleep(1)

        self.test_camera_obj = cv2.VideoCapture(test_video_file)
        if not self.test_camera_obj.isOpened():
            logging.error("Unable to open libcamera test stream")
            return False

        self.is_testing = True
        self._start_camera_test()
        return True

    def _test_usb_camera(self, source):
        """測試 USB 攝像頭"""
        camera_index = int(source.split()[-1])
        self.test_camera_obj = cv2.VideoCapture(camera_index)

        if not self.test_camera_obj.isOpened():
            logging.error("Unable to turn on camera")
            return False

        # 讀取一幀來初始化 ROI 線位置
        ret, frame = self.test_camera_obj.read()
        if ret:
            height = frame.shape[0]
            if not self.roi_lines:
                self.roi_lines = [int(height * self.saved_roi_percentage)]
            self.roi_lines = [max(0, min(self.roi_lines[0], height))]

        self.is_testing = True
        self._start_camera_test()
        return True

    def _start_camera_test(self):
        """開始攝像頭測試"""
        self.test_thread = threading.Thread(
            target=self._run_camera_test,
            daemon=True
        )
        self.test_thread.start()
        self._notify('test_started')  # 通知 UI 測試已開始

    def _run_camera_test(self):
        """執行攝像頭測試"""
        try:
            while self.is_testing:
                ret, frame = self.test_camera_obj.read()
                if ret:
                    frame_with_roi = self._draw_roi_on_frame_test(frame.copy())
                    self._notify('frame_processed', frame_with_roi)
                # time.sleep(0.01)
        except Exception as e:
            logging.error(f"Camera test execution error：{str(e)}")
        finally:
            self.stop_camera_test()

    def _draw_roi_on_frame_test(self, frame):
        """在影像上繪製 ROI 線和相關資訊"""
        height, width = frame.shape[:2]

        if self.roi_lines is not None and len(self.roi_lines) > 0:
            line_y = self.roi_lines[0]

            # 畫主要的 ROI 線
            cv2.line(frame, (0, line_y), (width, line_y), (0, 255, 0), 2)

            # 畫檢測區域
            cv2.rectangle(
                frame,
                (0, line_y),
                (width, line_y + self.roi_height),
                (255, 0, 0),
                1
            )

            # 顯示 ROI 位置百分比
            percentage = (line_y / height) * 100
            text = f"ROI: {percentage:.1f}%"
            cv2.putText(
                frame,
                text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

        return frame

    def _draw_roi_on_frame(self, frame):
        """在影像上繪製 ROI 線和檢測區域，並顯示相關資訊"""
        height, width = frame.shape[:2]

        if self.roi_lines is not None and len(self.roi_lines) > 0:
            line_y = self.roi_lines[0]

            # 畫主要的 ROI 線
            cv2.line(frame, (0, line_y), (width, line_y), (0, 255, 0), 2)

            # 畫檢測區域
            cv2.rectangle(
                frame,
                (0, line_y),
                (width, line_y + self.roi_height),
                (255, 0, 0),
                1
            )

            # 顯示 ROI 位置百分比
            roi_percentage = (line_y / height) * 100
            text = f"ROI: {roi_percentage:.1f}%"
            cv2.putText(
                frame,
                text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )

            # # 顯示攝像頭資訊
            # if hasattr(self, 'test_camera_obj') and self.test_camera_obj is not None:
            #     cam_width = self.test_camera_obj.get(cv2.CAP_PROP_FRAME_WIDTH)
            #     cam_height = self.test_camera_obj.get(cv2.CAP_PROP_FRAME_HEIGHT)
            #     cam_fps = self.test_camera_obj.get(cv2.CAP_PROP_FPS)
            #     cam_info = f"Resolution: {int(cam_width)}x{int(cam_height)}, FPS: {int(cam_fps)}"
            #     cv2.putText(
            #         frame,
            #         cam_info,
            #         (10, 60),
            #         cv2.FONT_HERSHEY_SIMPLEX,
            #         0.7,
            #         (0, 255, 0),
            #         2
            #     )

        return frame

    def stop_camera_test(self):
        """停止攝像頭測試"""
        try:
            if self.test_stop_event is not None:
                self.test_stop_event.set()
                if self.test_libcamera_thread is not None:
                    self.test_libcamera_thread.join()

            self.is_testing = False

            if self.test_camera_obj is not None:
                self.test_camera_obj.release()
                self.test_camera_obj = None

            self._notify('test_stopped')

        except Exception as e:
            logging.error(f"An error occurred while stopping the camera test：{str(e)}")
        finally:
            self.is_testing = False

    def _update_frame_stats(self, stat_type):
        """統一更新幀統計"""
        with self.performance_lock:
            self.frame_stats[stat_type] += 1
            current_time = time.time()
            time_diff = current_time - self.last_time

            if time_diff >= 1.0:
                # 計算真實的 FPS（考慮時間差）
                capture_fps = self.frame_stats['captured'] / time_diff
                process_fps = self.frame_stats['processed'] / time_diff
                display_fps = self.frame_stats['displayed'] / time_diff
                drop_rate = self.frame_stats['dropped'] / max(1, self.frame_stats['captured'])

                # 確保 FPS 不超過相機設定
                camera_fps = self.camera_manager.get_camera_info()['fps']
                capture_fps = min(capture_fps, camera_fps)

                logging.info(
                    f"Performance Stats:\n"
                    f"Capture FPS: {capture_fps:.2f}\n"
                    f"Process FPS: {process_fps:.2f}\n"
                    f"Display FPS: {display_fps:.2f}\n"
                    f"Drop Rate: {drop_rate * 100:.1f}%\n"
                    f"Frame Process Time: {getattr(self, 'current_frame_time', 0):.2f}ms"
                )

                # 重置計數器
                self.frame_stats = {k: 0 for k in self.frame_stats}
                self.last_time = current_time