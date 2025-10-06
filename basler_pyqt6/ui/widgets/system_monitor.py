"""
系統監控組件
"""

import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel
)
from PyQt6.QtCore import QTimer


class SystemMonitorWidget(QWidget):
    """系統監控組件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.init_timer()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)

        # 創建分組框
        group_box = QGroupBox("📊 系統監控")
        group_layout = QVBoxLayout()

        # CPU 使用率
        self.cpu_label = QLabel("CPU: 0%")
        group_layout.addWidget(self.cpu_label)

        # 記憶體使用率
        self.memory_label = QLabel("記憶體: 0%")
        group_layout.addWidget(self.memory_label)

        # 進程記憶體
        self.process_memory_label = QLabel("進程記憶體: 0 MB")
        group_layout.addWidget(self.process_memory_label)

        # 相機 FPS
        self.camera_fps_label = QLabel("相機 FPS: 0")
        self.camera_fps_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 12pt;")
        group_layout.addWidget(self.camera_fps_label)

        # 檢測 FPS
        self.detection_fps_label = QLabel("檢測 FPS: 0")
        group_layout.addWidget(self.detection_fps_label)

        # 總幀數
        self.total_frames_label = QLabel("總幀數: 0")
        group_layout.addWidget(self.total_frames_label)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

    def init_timer(self):
        """初始化定時器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(1000)  # 每秒更新一次

    def update_metrics(self):
        """更新性能指標"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")

            # 記憶體使用率
            memory = psutil.virtual_memory()
            self.memory_label.setText(f"記憶體: {memory.percent:.1f}%")

            # 進程記憶體
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024 * 1024)
            self.process_memory_label.setText(f"進程記憶體: {process_memory:.1f} MB")

        except Exception as e:
            print(f"❌ 更新監控指標錯誤: {str(e)}")

    def update_camera_stats(self, fps, total_frames):
        """更新相機統計"""
        self.camera_fps_label.setText(f"相機 FPS: {fps:.1f}")
        self.total_frames_label.setText(f"總幀數: {total_frames}")

    def update_detection_fps(self, fps):
        """更新檢測 FPS"""
        self.detection_fps_label.setText(f"檢測 FPS: {fps:.1f}")
