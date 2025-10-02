"""
主窗口 V2 - 完整功能版本
支持相機/視頻雙模式 + 檢測 + 錄影
"""

import logging
import cv2
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from basler_pyqt6.ui.widgets.camera_control import CameraControlWidget
from basler_pyqt6.ui.widgets.video_display import VideoDisplayWidget
from basler_pyqt6.ui.widgets.detection_control import DetectionControlWidget
from basler_pyqt6.ui.widgets.recording_control import RecordingControlWidget
from basler_pyqt6.ui.widgets.system_monitor import SystemMonitorWidget

# 導入核心模塊
from basler_pyqt6.core.source_manager import SourceManager, SourceType
from basler_pyqt6.core.detection import DetectionController
from basler_pyqt6.core.video_recorder import VideoRecorder

logger = logging.getLogger(__name__)


class MainWindowV2(QMainWindow):
    """主窗口 V2 - 完整版"""

    def __init__(self):
        super().__init__()
        self.source_manager = SourceManager()
        self.detection_controller = DetectionController()
        self.video_recorder = VideoRecorder()
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("🏭 Basler 工業視覺系統 - 專業版")
        self.setMinimumSize(1500, 900)

        # 創建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主佈局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 創建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ===== 左側控制面板 =====
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        self.camera_control = CameraControlWidget()
        left_layout.addWidget(self.camera_control)

        self.detection_control = DetectionControlWidget()
        left_layout.addWidget(self.detection_control)

        self.recording_control = RecordingControlWidget()
        left_layout.addWidget(self.recording_control)

        left_layout.addStretch()

        # ===== 中間視頻顯示區 =====
        self.video_display = VideoDisplayWidget()

        # ===== 右側監控面板 =====
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.system_monitor = SystemMonitorWidget()
        right_layout.addWidget(self.system_monitor)
        right_layout.addStretch()

        # 添加到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(self.video_display)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 2)

        main_layout.addWidget(splitter)

        # 創建菜單欄
        self.create_menu_bar()

        # 創建狀態欄
        self.create_status_bar()

        # 連接信號
        self.connect_signals()

        # 定時器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(33)  # 30 FPS 更新

        # 應用樣式
        self.apply_styles()

        logger.info("✅ UI 初始化完成")

    def create_menu_bar(self):
        """創建菜單欄"""
        menubar = self.menuBar()

        # 文件菜單
        file_menu = menubar.addMenu("文件(&F)")

        load_video_action = QAction("📂 加載視頻文件...", self)
        load_video_action.setShortcut("Ctrl+O")
        load_video_action.triggered.connect(self.load_video_file)
        file_menu.addAction(load_video_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 模式菜單
        mode_menu = menubar.addMenu("模式(&M)")

        camera_mode_action = QAction("📷 相機模式", self)
        camera_mode_action.triggered.connect(self.switch_to_camera_mode)
        mode_menu.addAction(camera_mode_action)

        video_mode_action = QAction("🎬 視頻模式", self)
        video_mode_action.triggered.connect(self.load_video_file)
        mode_menu.addAction(video_mode_action)

        # 幫助菜單
        help_menu = menubar.addMenu("幫助(&H)")

        about_action = QAction("關於(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_status_bar(self):
        """創建狀態欄"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("就緒")
        self.status_bar.addWidget(self.status_label)

        self.source_label = QLabel("源: 無")
        self.status_bar.addPermanentWidget(self.source_label)

        self.fps_label = QLabel("FPS: 0")
        self.status_bar.addPermanentWidget(self.fps_label)

        self.detection_label = QLabel("檢測: 0")
        self.status_bar.addPermanentWidget(self.detection_label)

    def connect_signals(self):
        """連接信號"""
        # 相機控制
        self.camera_control.detect_clicked.connect(self.on_detect_cameras)
        self.camera_control.connect_clicked.connect(self.on_connect_camera)
        self.camera_control.disconnect_clicked.connect(self.on_disconnect_camera)
        self.camera_control.start_clicked.connect(self.on_start_source)
        self.camera_control.stop_clicked.connect(self.on_stop_source)
        self.camera_control.exposure_changed.connect(self.on_exposure_changed)

        # 檢測控制
        self.detection_control.method_changed.connect(self.on_detection_method_changed)
        self.detection_control.enable_changed.connect(self.on_detection_enable_changed)

        # 錄影控制
        self.recording_control.start_recording.connect(self.on_start_recording)
        self.recording_control.stop_recording.connect(self.on_stop_recording)

    def load_video_file(self):
        """加載視頻文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇視頻文件",
            str(Path.home()),
            "視頻文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*.*)"
        )

        if file_path:
            if self.source_manager.use_video(file_path):
                self.source_label.setText(f"源: 視頻 - {Path(file_path).name}")
                self.status_label.setText(f"視頻已加載: {Path(file_path).name}")
                self.camera_control.set_video_mode(True)
            else:
                QMessageBox.warning(self, "錯誤", "無法加載視頻文件")

    def switch_to_camera_mode(self):
        """切換到相機模式"""
        self.source_manager.use_camera()
        self.source_label.setText("源: 相機")
        self.camera_control.set_video_mode(False)
        self.status_label.setText("已切換到相機模式")

    def on_detect_cameras(self):
        """檢測相機"""
        camera = self.source_manager.use_camera()
        cameras = camera.detect_cameras()
        self.camera_control.update_camera_list(cameras)
        self.status_label.setText(f"檢測到 {len(cameras)} 台相機")

    def on_connect_camera(self, camera_index):
        """連接相機"""
        if self.source_manager.source_type == SourceType.CAMERA:
            success = self.source_manager.camera_controller.connect(camera_index)
            if success:
                self.status_label.setText("相機連接成功")
            else:
                self.status_label.setText("相機連接失敗")

    def on_disconnect_camera(self):
        """斷開相機"""
        if self.source_manager.source_type == SourceType.CAMERA:
            self.source_manager.camera_controller.disconnect()
            self.status_label.setText("相機已斷開")

    def on_start_source(self):
        """開始源（相機抓取或視頻播放）"""
        if self.source_manager.source_type == SourceType.CAMERA:
            self.source_manager.camera_controller.start_grabbing()
            self.status_label.setText("開始抓取圖像")
            self.recording_control.set_enabled(True)  # 啟用錄製按鈕
        elif self.source_manager.source_type == SourceType.VIDEO:
            self.source_manager.video_player.start_playing(loop=True)
            self.status_label.setText("開始播放視頻")
            self.recording_control.set_enabled(True)  # 啟用錄製按鈕

    def on_stop_source(self):
        """停止源"""
        # 如果正在錄製，先停止錄製
        if self.video_recorder.is_recording:
            self.on_stop_recording()

        if self.source_manager.source_type == SourceType.CAMERA:
            self.source_manager.camera_controller.stop_grabbing()
            self.status_label.setText("停止抓取圖像")
            self.recording_control.set_enabled(False)  # 禁用錄製按鈕
        elif self.source_manager.source_type == SourceType.VIDEO:
            self.source_manager.video_player.stop_playing()
            self.status_label.setText("停止播放視頻")
            self.recording_control.set_enabled(False)  # 禁用錄製按鈕

    def on_exposure_changed(self, value):
        """曝光改變"""
        if self.source_manager.source_type == SourceType.CAMERA:
            self.source_manager.camera_controller.set_exposure(value)

    def on_detection_method_changed(self, method):
        """檢測方法改變"""
        from basler_pyqt6.core.detection import DetectionMethod
        method_map = {
            "circle": DetectionMethod.CIRCLE,
            "contour": DetectionMethod.CONTOUR,
            "background": DetectionMethod.BACKGROUND
        }
        if method in method_map:
            self.detection_controller.set_method(method_map[method])
            self.status_label.setText(f"檢測方法: {method}")

    def on_detection_enable_changed(self, enabled):
        """檢測啟用改變"""
        if enabled:
            self.detection_controller.enable()
            self.status_label.setText("檢測已啟用")
        else:
            self.detection_controller.disable()
            self.status_label.setText("檢測已禁用")

    def on_start_recording(self):
        """開始錄影"""
        # 獲取當前幀以確定錄製參數
        frame = self.source_manager.get_frame()
        if frame is None:
            QMessageBox.warning(self, "錯誤", "無法獲取視頻源，請先啟動相機或播放視頻")
            self.recording_control.set_enabled(True)
            return

        # 獲取幀尺寸
        height, width = frame.shape[:2]
        frame_size = (width, height)

        # 獲取當前FPS
        fps = self.source_manager.get_fps()
        if fps <= 0:
            fps = 30.0  # 預設值

        # 開始錄製
        if self.video_recorder.start_recording(frame_size=frame_size, fps=fps):
            self.status_label.setText("🔴 錄製中...")
            logger.info(f"開始錄製: {frame_size} @ {fps:.1f}fps")
        else:
            QMessageBox.warning(self, "錯誤", "無法啟動視頻錄製")
            self.recording_control.set_enabled(True)

    def on_stop_recording(self):
        """停止錄影"""
        recording_info = self.video_recorder.stop_recording()

        if recording_info:
            self.status_label.setText("✅ 錄製完成")

            # 顯示錄製信息
            info_msg = (
                f"錄製完成！\n\n"
                f"文件名: {recording_info['filename']}\n"
                f"總幀數: {recording_info['frames_recorded']} 幀\n"
                f"時長: {recording_info['duration']:.2f} 秒\n"
                f"平均幀率: {recording_info['average_fps']:.1f} fps\n"
                f"編碼器: {recording_info['codec']}"
            )
            QMessageBox.information(self, "錄製完成", info_msg)

            logger.info(f"錄製完成: {recording_info}")
        else:
            self.status_label.setText("錄製停止")

    def update_display(self):
        """更新顯示"""
        # 獲取當前幀
        frame = self.source_manager.get_frame()

        if frame is not None:
            # 保存原始幀用於錄製
            original_frame = frame.copy()

            # 執行檢測
            if self.detection_controller.enabled:
                frame, objects = self.detection_controller.process_frame(frame)
                count = len(objects)
                self.detection_label.setText(f"檢測: {count}")
                self.detection_control.update_status(True, count)
            else:
                self.detection_control.update_status(False, 0)

            # 錄製視頻（使用檢測後的幀，如果啟用檢測的話）
            if self.video_recorder.is_recording:
                # 確保幀是BGR格式（OpenCV標準）
                if len(frame.shape) == 2:  # 灰度圖
                    recording_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                else:
                    recording_frame = frame

                self.video_recorder.write_frame(recording_frame)

                # 更新錄製狀態
                status = self.video_recorder.get_recording_status()
                self.recording_control.update_frame_count(status['frames_recorded'])

            # 更新顯示
            self.video_display.update_frame(frame)

        # 更新 FPS
        fps = self.source_manager.get_fps()
        self.fps_label.setText(f"FPS: {fps:.1f}")

        # 更新系統監控
        if self.source_manager.source_type == SourceType.CAMERA:
            total_frames = self.source_manager.camera_controller.total_frames
            self.system_monitor.update_camera_stats(fps, total_frames)
        elif self.source_manager.source_type == SourceType.VIDEO:
            total_frames = self.source_manager.video_player.total_frames
            self.system_monitor.update_camera_stats(fps, total_frames)

    def apply_styles(self):
        """應用樣式"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
                font-size: 10pt;
            }
            QGroupBox {
                border: 2px solid #3d3d3d;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: bold;
                color: #4CAF50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #0d7377;
                border: none;
                border-radius: 4px;
                padding: 10px 18px;
                color: white;
                font-weight: bold;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #14ffec;
                color: #000000;
            }
            QPushButton:pressed {
                background-color: #0a5f63;
            }
            QPushButton:disabled {
                background-color: #3d3d3d;
                color: #777777;
            }
            QStatusBar {
                background-color: #1a1a1a;
                color: #ffffff;
                border-top: 1px solid #3d3d3d;
            }
            QMenuBar {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QMenuBar::item:selected {
                background-color: #0d7377;
            }
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QMenu::item:selected {
                background-color: #0d7377;
            }
        """)

    def show_about(self):
        """顯示關於"""
        QMessageBox.about(
            self,
            "關於",
            "<h2>Basler 工業視覺系統 - 專業版</h2>"
            "<p>版本: 2.0 (PyQt6)</p>"
            "<p>高性能工業相機視覺檢測系統</p>"
            "<p>支持 Basler acA640-300gm (280+ FPS)</p>"
            "<hr>"
            "<p><b>功能特點:</b></p>"
            "<ul>"
            "<li>✅ 雙模式支持（相機/視頻）</li>"
            "<li>✅ 多種檢測算法</li>"
            "<li>✅ 實時性能監控</li>"
            "<li>✅ 專業化界面設計</li>"
            "</ul>"
            "<hr>"
            "<p>© 2024 Industrial Vision</p>"
        )

    def closeEvent(self, event):
        """窗口關閉事件"""
        # 停止錄製
        if self.video_recorder.is_recording:
            self.video_recorder.stop_recording()

        # 清理資源
        self.source_manager.cleanup()
        self.video_recorder.cleanup()

        logger.info("✅ 資源清理完成")
        event.accept()
