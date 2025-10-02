"""
主窗口 - PyQt6 實現
"""

import logging
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from basler_pyqt6.ui.widgets.camera_control import CameraControlWidget
from basler_pyqt6.ui.widgets.video_display import VideoDisplayWidget
from basler_pyqt6.ui.widgets.detection_control import DetectionControlWidget
from basler_pyqt6.ui.widgets.recording_control import RecordingControlWidget
from basler_pyqt6.ui.widgets.system_monitor import SystemMonitorWidget

# 導入簡化的相機控制器
from basler_pyqt6.core.camera import CameraController

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口類"""

    def __init__(self):
        super().__init__()
        self.controller = None
        self.init_ui()
        self.init_controller()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("🏭 Basler acA640-300gm 工業視覺系統")
        self.setMinimumSize(1400, 900)

        # 創建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主佈局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 創建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ===== 左側控制面板 =====
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 相機控制
        self.camera_control = CameraControlWidget()
        left_layout.addWidget(self.camera_control)

        # 檢測控制
        self.detection_control = DetectionControlWidget()
        left_layout.addWidget(self.detection_control)

        # 錄影控制
        self.recording_control = RecordingControlWidget()
        left_layout.addWidget(self.recording_control)

        left_layout.addStretch()

        # ===== 中間視頻顯示區 =====
        self.video_display = VideoDisplayWidget()

        # ===== 右側監控面板 =====
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.system_monitor = SystemMonitorWidget()
        right_layout.addWidget(self.system_monitor)
        right_layout.addStretch()

        # 添加到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(self.video_display)
        splitter.addWidget(right_panel)

        # 設置分割器比例
        splitter.setStretchFactor(0, 2)  # 左側
        splitter.setStretchFactor(1, 5)  # 中間
        splitter.setStretchFactor(2, 2)  # 右側

        main_layout.addWidget(splitter)

        # 創建菜單欄
        self.create_menu_bar()

        # 創建狀態欄
        self.create_status_bar()

        # 應用樣式
        self.apply_styles()

        logger.info("✅ UI 初始化完成")

    def create_menu_bar(self):
        """創建菜單欄"""
        menubar = self.menuBar()

        # 文件菜單
        file_menu = menubar.addMenu("文件(&F)")

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 視圖菜單
        view_menu = menubar.addMenu("視圖(&V)")

        # 幫助菜單
        help_menu = menubar.addMenu("幫助(&H)")

        about_action = QAction("關於(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_status_bar(self):
        """創建狀態欄"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 狀態標籤
        self.status_label = QLabel("就緒")
        self.status_bar.addWidget(self.status_label)

        # FPS 標籤
        self.fps_label = QLabel("FPS: 0")
        self.status_bar.addPermanentWidget(self.fps_label)

        # 連接狀態
        self.connection_label = QLabel("相機: 未連接")
        self.status_bar.addPermanentWidget(self.connection_label)

    def init_controller(self):
        """初始化控制器（使用簡化版）"""
        try:
            self.controller = CameraController()

            # 連接信號
            self.connect_signals()

            logger.info("✅ 控制器初始化完成")

        except Exception as e:
            logger.error(f"❌ 控制器初始化失敗: {str(e)}")

    def connect_signals(self):
        """連接信號和槽"""
        # 相機控制信號
        self.camera_control.detect_clicked.connect(self.on_detect_cameras)
        self.camera_control.connect_clicked.connect(self.on_connect_camera)
        self.camera_control.disconnect_clicked.connect(self.on_disconnect_camera)
        self.camera_control.start_clicked.connect(self.on_start_grabbing)
        self.camera_control.stop_clicked.connect(self.on_stop_grabbing)

        # 檢測控制信號
        self.detection_control.method_changed.connect(self.on_detection_method_changed)
        self.detection_control.enable_changed.connect(self.on_detection_enable_changed)

        # 錄影控制信號
        self.recording_control.start_recording.connect(self.on_start_recording)
        self.recording_control.stop_recording.connect(self.on_stop_recording)

        # 設置定時器更新狀態
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(100)  # 每 100ms 更新一次

    def on_detect_cameras(self):
        """檢測相機"""
        if self.controller:
            cameras = self.controller.detect_cameras()
            self.camera_control.update_camera_list(cameras)
            self.status_label.setText(f"檢測到 {len(cameras)} 台相機")

    def on_connect_camera(self, camera_index):
        """連接相機"""
        if self.controller:
            success = self.controller.connect(camera_index)
            if success:
                self.connection_label.setText("相機: 已連接")
                self.status_label.setText("相機連接成功")
            else:
                self.status_label.setText("相機連接失敗")

    def on_disconnect_camera(self):
        """斷開相機"""
        if self.controller:
            self.controller.disconnect()
            self.connection_label.setText("相機: 未連接")
            self.status_label.setText("相機已斷開")

    def on_start_grabbing(self):
        """開始抓取"""
        if self.controller:
            self.controller.start_grabbing()
            self.status_label.setText("開始抓取圖像")

    def on_stop_grabbing(self):
        """停止抓取"""
        if self.controller:
            self.controller.stop_grabbing()
            self.status_label.setText("停止抓取圖像")

    def on_detection_method_changed(self, method):
        """檢測方法改變"""
        # TODO: 實現檢測功能
        self.status_label.setText(f"檢測方法: {method}")

    def on_detection_enable_changed(self, enabled):
        """檢測啟用狀態改變"""
        # TODO: 實現檢測功能
        if enabled:
            self.status_label.setText("檢測已啟用")
        else:
            self.status_label.setText("檢測已禁用")

    def on_start_recording(self):
        """開始錄影"""
        # TODO: 實現錄影功能
        self.status_label.setText("開始錄製視頻")

    def on_stop_recording(self):
        """停止錄影"""
        # TODO: 實現錄影功能
        self.status_label.setText("停止錄製視頻")

    def update_status(self):
        """更新狀態顯示"""
        if not self.controller:
            return

        # 更新 FPS
        fps = self.controller.current_fps
        self.fps_label.setText(f"FPS: {fps:.1f}")

        # 更新視頻顯示
        frame = self.controller.get_frame()
        if frame is not None:
            self.video_display.update_frame(frame)

        # 更新系統監控
        self.system_monitor.update_camera_stats(fps, self.controller.total_frames)

    def apply_styles(self):
        """應用樣式表"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 10pt;
            }
            QGroupBox {
                border: 2px solid #3d3d3d;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
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
                padding: 8px 16px;
                color: white;
                font-weight: bold;
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
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)

    def show_about(self):
        """顯示關於對話框"""
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "關於",
            "<h2>Basler 工業視覺系統</h2>"
            "<p>版本: 2.0 (PyQt6)</p>"
            "<p>高性能工業相機視覺檢測系統</p>"
            "<p>支持 Basler acA640-300gm (280+ FPS)</p>"
            "<hr>"
            "<p>架構: PyQt6 桌面應用</p>"
            "<p>© 2024 Industrial Vision</p>"
        )

    def closeEvent(self, event):
        """窗口關閉事件"""
        # 清理資源
        if self.controller:
            try:
                self.controller.cleanup()
                logger.info("✅ 資源清理完成")
            except Exception as e:
                logger.error(f"❌ 資源清理失敗: {str(e)}")

        event.accept()
