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
from models.api_client import APIClient


class DetectionController:
    """物件偵測控制器類別"""

    def __init__(self, camera_manager, image_processor):
        """
        初始化物件偵測控制器

        Args:
            camera_manager: 攝影機管理器實例
            image_processor: 影像處理器實例
        """
        self.processing_times = None
        self.fps_history = None
        self.total_frames = None
        self.frame_count = None
        self._run_libcamera_test = None
        self.camera_manager = camera_manager
        self.image_processor = image_processor

        # 狀態變數
        self.is_monitoring = False
        self.is_testing = False
        self.current_count = 0
        self.total_counter = 0

        # 拍照相關變數
        self.is_photo_mode = False
        self.captured_photo = None
        self.current_image_path = None
        self.preview_timer = None  # 添加這一行以初始化 preview_timer

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

        # API客戶端
        self.api_client = APIClient()

        # 註冊回調函數的字典
        self.callbacks = {
            'test_started': None,
            'test_stopped': None,
            'frame_processed': None,
            'monitoring_started': None,
            'monitoring_stopped': None,
            'count_updated': None,
            'photo_captured': None,  # 新增：拍照回調
            'photo_analyzed': None,  # 新增：分析回調
            'camera_preview_updated': None,  # 新增：相機預覽更新回調
            'analysis_error': None  # 新增：分析錯誤回調
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
        """停止監測並恢復到測試狀態"""
        self.is_monitoring = False

        # 保存目前的視訊來源
        current_source = None
        if self.camera_manager and self.camera_manager.current_source:
            current_source = self.camera_manager.current_source

        # 釋放相機資源
        self.camera_manager.release_camera()
        self.object_tracks = {}  # 重置物件追蹤資料

        # 通知監測已停止
        self._notify('monitoring_stopped')

        # 如果有來源，自動重新開始測試
        if current_source:
            # 短暫延遲確保資源完全釋放
            import time
            time.sleep(0.2)
            self.test_camera(current_source)

    def _process_video(self):
        """改進的視訊處理主函數，增強錯誤處理"""
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
        error_count = 0
        max_errors = 10

        while self.is_monitoring:
            try:
                frame = self.frame_queue.get(timeout=0.1)
                if frame is None:
                    error_count += 1
                    if error_count > max_errors:
                        logging.error(f"連續 {max_errors} 次未能獲取有效影像，停止監測")
                        self.stop_monitoring()
                        break
                    continue

                # 成功獲取影像，重置錯誤計數
                error_count = 0

                # 提交處理任務到線程池
                self.thread_pool.submit(self._process_single_frame, frame)

            except Empty:
                # 佇列超時是正常情況，繼續嘗試
                continue
            except Exception as e:
                error_count += 1
                logging.error(f"處理視訊時發生錯誤: {str(e)}")
                if error_count > max_errors:
                    logging.error(f"連續 {max_errors} 次處理錯誤，停止監測")
                    self.stop_monitoring()
                    break

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

    # ==========================================================================
    # 第七部分：回調管理增強
    # ==========================================================================

    def set_callback(self, callback_name, callback_function):
        """
        設置回調函數

        Args:
            callback_name: 回調名稱
            callback_function: 回調函數
        """
        if not hasattr(self, 'callbacks'):
            self.callbacks = {}

        self.callbacks[callback_name] = callback_function

        # 保留向下兼容性
        if callback_name == 'start' and hasattr(self, 'start_button'):
            self.start_button.configure(command=callback_function)

    def _notify(self, event_name, *args):
        """
        通知註冊的回調函數

        Args:
            event_name: 事件名稱
            *args: 傳遞給回調函數的參數
        """
        if hasattr(self, 'callbacks') and event_name in self.callbacks and self.callbacks[event_name]:
            try:
                return self.callbacks[event_name](*args)
            except Exception as e:
                logging.error(f"執行回調 {event_name} 時發生錯誤: {str(e)}")
        return None

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
            logging.error("錯誤：請選擇視訊來源")
            return False

        # 如果已經在測試中，則停止測試
        if self.is_testing:
            self.stop_camera_test()
            # 短暫延遲確保資源完全釋放
            import time
            time.sleep(0.2)

        try:
            if source == "libcamera":
                return self._test_libcamera()
            else:
                return self._test_usb_camera(source)

        except Exception as e:
            logging.error(f"相機測試錯誤：{str(e)}")
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

    # ==========================================================================
    # 添加新部分：拍照和分析功能
    # ==========================================================================

    def capture_photo(self):
        """拍攝照片"""
        try:
            # 獲取圖像
            success, frame = self.camera_manager.capture_photo()
            if not success or frame is None:
                logging.error("拍攝失敗")
                return False

            # 保存圖像
            self.captured_photo = frame

            # 保存為臨時文件
            self.current_image_path = self.api_client.save_temp_image(frame)

            # 通知UI更新預覽
            self._notify('photo_captured', frame)

            return True

        except Exception as e:
            logging.error(f"拍攝照片時發生錯誤：{str(e)}")
            return False

    def analyze_photo(self):
        """分析照片"""
        try:
            if self.captured_photo is None or self.current_image_path is None:
                logging.error("沒有可分析的照片")
                return False

            # 定義成功和失敗回調
            def on_success(result):
                # 通知UI更新分析結果
                self._notify('photo_analyzed', result)

            def on_error(error_msg):
                logging.error(f"分析失敗：{error_msg}")
                # 通知UI顯示錯誤
                self._notify('analysis_error', error_msg)

            # 調用API進行分析
            self.api_client.inspect_image(
                self.current_image_path,
                success_callback=on_success,
                error_callback=on_error
            )

            return True

        except Exception as e:
            logging.error(f"分析照片時發生錯誤：{str(e)}")
            return False

    def cleanup_photo_resources(self):
        """清理拍照相關資源"""
        try:
            # 停止預覽
            self.stop_camera_preview()

            # 清理臨時文件
            if self.current_image_path:
                self.api_client.cleanup_temp_file(self.current_image_path)
                self.current_image_path = None

            # 清理相機資源
            if self.camera_manager:
                self.camera_manager.release_pylon_camera()

        except Exception as e:
            logging.error(f"清理拍照資源時發生錯誤：{str(e)}")

    def preview_camera_for_photo(self):
        """為拍照模式提供相機預覽"""
        try:
            if not self.camera_manager.camera or not self.camera_manager.camera.isOpened():
                return False

            ret, frame = self.camera_manager.read_frame()
            if not ret or frame is None:
                return False

            # 通知預覽幀
            self._notify('frame_processed', frame)

            return True

        except Exception as e:
            logging.error(f"提供拍照預覽時發生錯誤：{str(e)}")
            return False

    # ==========================================================================
    # 第三部分：拍照模式相關方法
    # ==========================================================================

    def start_camera_preview(self):
        """啟動相機預覽"""
        try:
            # 停止任何可能在運行的預覽
            self.stop_camera_preview()

            # 釋放任何已存在的相機資源，確保乾淨的開始
            self.cleanup_photo_resources()

            # 重新設置狀態
            self.is_photo_mode = True
            self.preview_active = True

            # 嘗試獲取選定的相機源
            selected_source = None
            if hasattr(self, 'callbacks') and 'get_selected_source' in self.callbacks:
                selected_source = self.callbacks['get_selected_source']()

            # 嘗試打開選擇的相機
            if selected_source:
                success = self.camera_manager.open_camera(selected_source)
                if success:
                    logging.info(f"成功開啟相機: {selected_source}")
                else:
                    logging.warning(f"無法開啟選擇的相機: {selected_source}，嘗試自動尋找可用相機")
                    # 嘗試尋找任何可用的相機
                    for i in range(5):
                        try:
                            self.camera_manager.camera = cv2.VideoCapture(i)
                            if self.camera_manager.camera.isOpened():
                                ret, _ = self.camera_manager.camera.read()
                                if ret:
                                    logging.info(f"自動找到可用相機: {i}")
                                    break
                        except Exception:
                            pass

            # 如果常規相機初始化失敗，嘗試使用 Pylon 相機
            if not self.camera_manager.camera or not self.camera_manager.camera.isOpened():
                logging.info("嘗試初始化 Pylon 相機")
                if not self.camera_manager.initialize_pylon_camera():
                    logging.error("無法初始化任何相機，預覽無法啟動")
                    return False

            # 確認 root 對象可用
            if not hasattr(self, 'root') and hasattr(self, 'callbacks') and 'get_root' in self.callbacks:
                self.root = self.callbacks['get_root']()

            # 如果沒有有效的 root 對象，返回失敗
            if not hasattr(self, 'root'):
                logging.error("無法獲取有效的 root 對象，預覽無法啟動")
                return False

            # 初始化預覽更新 ID
            self.preview_update_id = None

            # 啟動第一次預覽更新
            self._update_photo_preview()

            logging.info("相機預覽系統已啟動")
            return True
        except Exception as e:
            logging.error(f"啟動相機預覽時發生錯誤: {str(e)}")
            # 重置狀態
            self.is_photo_mode = False
            self.preview_active = False
            return False

    def _update_photo_preview(self):
        """更新相機預覽的新方法"""
        try:
            # 檢查是否仍處於預覽狀態
            if not hasattr(self, 'preview_active') or not self.preview_active:
                return

            # 嘗試獲取一幀圖像
            success = False
            frame = None

            # 首先嘗試從標準相機獲取圖像
            if self.camera_manager.camera and self.camera_manager.camera.isOpened():
                ret, frame = self.camera_manager.camera.read()
                if ret and frame is not None:
                    success = True

            # 如果標準相機失敗，嘗試 Pylon 相機
            if not success and hasattr(self.camera_manager, 'pylon_camera') and self.camera_manager.pylon_camera:
                ret, frame = self.camera_manager.capture_pylon_image()
                if ret and frame is not None:
                    success = True

            # 如果獲取到圖像，通知 UI 更新
            if success and frame is not None:
                self._notify('camera_preview_updated', frame)
            else:
                # 如果無法獲取圖像，記錄錯誤但繼續嘗試
                logging.warning("無法從相機讀取圖像，但將繼續嘗試")

            # 如果預覽仍然活躍，排程下一次更新
            if hasattr(self, 'preview_active') and self.preview_active and hasattr(self, 'root'):
                try:
                    # 取消任何先前的排程
                    if hasattr(self, 'preview_update_id') and self.preview_update_id:
                        self.root.after_cancel(self.preview_update_id)

                    # 排程下一次更新
                    self.preview_update_id = self.root.after(50, self._update_photo_preview)
                except Exception as e:
                    logging.error(f"排程相機預覽更新時發生錯誤: {str(e)}")
        except Exception as e:
            logging.error(f"更新相機預覽時發生錯誤: {str(e)}")
            # 報告錯誤但不中斷預覽循環
            if hasattr(self, 'preview_active') and self.preview_active and hasattr(self, 'root'):
                self.preview_update_id = self.root.after(1000, self._update_photo_preview)  # 遇到錯誤後延長間隔

    def _schedule_preview_update(self):
        """排程預覽更新"""
        if not hasattr(self, 'root'):
            # 從回調函數中獲取 root 對象
            if hasattr(self, 'callbacks') and 'get_root' in self.callbacks:
                self.root = self.callbacks['get_root']()
            else:
                logging.error("無法獲取 root 對象，無法排程預覽更新")
                return

        # 使用 Tkinter 的 after 方法定期更新
        if self.is_photo_mode:
            self._update_camera_preview()
            self.preview_update_id = self.root.after(50, self._schedule_preview_update)  # 約 20 FPS

    def _update_camera_preview(self):
        """更新相機預覽"""
        try:
            if not self.is_photo_mode:
                return

            # 獲取圖像，優先使用已有的相機
            ret, frame = False, None
            if self.camera_manager.camera and self.camera_manager.camera.isOpened():
                ret, frame = self.camera_manager.camera.read()

            # 如果普通相機失敗，嘗試使用 Pylon 相機
            if not ret or frame is None:
                ret, frame = self.camera_manager.capture_photo()

            if ret and frame is not None:
                # 通知UI更新預覽
                self._notify('camera_preview_updated', frame)

        except Exception as e:
            logging.error(f"更新相機預覽時發生錯誤：{str(e)}")

    def stop_camera_preview(self):
        """停止相機預覽"""
        try:
            # 標記預覽為非活躍
            self.preview_active = False
            self.is_photo_mode = False

            # 取消任何排程的更新
            if hasattr(self, 'root') and hasattr(self, 'preview_update_id') and self.preview_update_id:
                try:
                    self.root.after_cancel(self.preview_update_id)
                    self.preview_update_id = None
                except Exception as e:
                    logging.warning(f"取消預覽排程時發生錯誤: {str(e)}")

            # 為了向下兼容 - 清理舊計時器
            if hasattr(self, 'preview_timer') and self.preview_timer:
                try:
                    self.preview_timer.cancel()
                    self.preview_timer = None
                except Exception:
                    pass

            logging.info("相機預覽已停止")
        except Exception as e:
            logging.error(f"停止相機預覽時發生錯誤: {str(e)}")