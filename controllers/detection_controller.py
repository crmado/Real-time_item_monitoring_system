"""
物件偵測控制器
負責協調影像處理和物件偵測的核心邏輯
"""

import threading
import time
import logging
from tkinter import messagebox

import cv2


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

                logging.info(f"ROI 線位置更新: {self.saved_roi_percentage * 100:.1f}%")

        except Exception as e:
            logging.error(f"更新 ROI 位置時發生錯誤：{str(e)}")

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
                logging.info(f"ROI 線位置設定已儲存: {self.saved_roi_percentage * 100:.1f}%")

        except Exception as e:
            logging.error(f"儲存 ROI 設定時發生錯誤：{str(e)}")
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
                logging.warning("請先停止測試再開始監測")
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
            logging.error(f"啟動監測時發生錯誤：{str(e)}")
            return False

    def stop_monitoring(self):
        """停止監測"""
        self.is_monitoring = False
        self.camera_manager.release_camera()
        self.object_tracks = {}  # 重置物件追蹤資料
        self._notify('monitoring_stopped')

    def _process_video(self):
        """處理視訊流"""
        while self.is_monitoring:
            try:
                ret, frame = self.camera_manager.read_frame()
                if not ret or frame is None:
                    logging.warning("無法讀取影像或影片已結束")
                    break

                frame_with_detections = frame.copy()

                # 處理每個 ROI 線
                for line_y in self.roi_lines:
                    # 確保 frame 不為 None
                    if frame is not None:
                        # 繪製 ROI 線和檢測區域
                        # frame_with_detections = self._draw_roi_on_frame(frame_with_detections)

                        # 擷取 ROI 區域
                        roi = frame[line_y:line_y + self.roi_height, :]
                        processed = self.image_processor.process_frame(roi)
                        objects = self.image_processor.detect_objects(processed)

                        # 更新物件追蹤
                        self._update_object_tracking(objects, line_y)

                        # 更新影像顯示
                        self._draw_detection_results(frame_with_detections, objects, line_y)

                # 通知更新顯示
                self._notify('frame_processed', frame_with_detections)
                self.frame_index += 1

                # 控制處理速率
                time.sleep(1 / self.camera_manager.get_camera_info()['fps'])

            except Exception as e:
                logging.error(f"處理影像時發生錯誤：{str(e)}")
                break

        self.stop_monitoring()

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
        """
        在影像上繪製檢測結果

        Args:
            frame: 原始影像幀
            objects: 檢測到的物件列表
            line_y: ROI 線的 y 座標
        """
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
        # 添加資訊文字 - 顯示相機幀數
        cv2.putText(
            frame,
            f"FPS: {self.camera_manager.get_camera_info()['fps']}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
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
            "緩衝點警告",
            f"已達到緩衝點 ({self.buffer_point})，即將達到預計數量！"
        )

    def _show_target_reached(self):
        """顯示達到目標數量通知"""
        messagebox.showinfo(
            "完成通知",
            f"已達到預計數量 ({self.target_count})！"
        )

    def set_callback(self, event_name, callback):
        """
        註冊回調函數

        Args:
            event_name: 事件名稱
            callback: 回調函數
        """
        self.callbacks[event_name] = callback

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
            logging.error("緩衝點必須小於預計數量")
            return False

        if buffer_point < 0 or target_count < 0:
            logging.error("數值不能為負數")
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
            return True

        try:
            # self._notify('test_started')  # 通知開始測試

            if source == "libcamera":
                return self._test_libcamera()
            else:
                return self._test_usb_camera(source)

        except Exception as e:
            logging.error(f"攝像頭測試錯誤：{str(e)}")
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
            logging.error("無法開啟 libcamera 測試串流")
            return False

        self.is_testing = True
        self._start_camera_test()
        return True

    def _test_usb_camera(self, source):
        """測試 USB 攝像頭"""
        camera_index = int(source.split()[-1])
        self.test_camera_obj = cv2.VideoCapture(camera_index)

        if not self.test_camera_obj.isOpened():
            logging.error("無法開啟攝像頭")
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
                time.sleep(1 / 30)
        except Exception as e:
            logging.error(f"攝像頭測試執行錯誤：{str(e)}")
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

            # 顯示攝像頭資訊
            if hasattr(self, 'test_camera_obj') and self.test_camera_obj is not None:
                cam_width = self.test_camera_obj.get(cv2.CAP_PROP_FRAME_WIDTH)
                cam_height = self.test_camera_obj.get(cv2.CAP_PROP_FRAME_HEIGHT)
                cam_fps = self.test_camera_obj.get(cv2.CAP_PROP_FPS)
                cam_info = f"Resolution: {int(cam_width)}x{int(cam_height)}, FPS: {int(cam_fps)}"
                cv2.putText(
                    frame,
                    cam_info,
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )

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
            logging.error(f"停止攝像頭測試時發生錯誤：{str(e)}")
        finally:
            self.is_testing = False