"""
錄影控制組件
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox,
    QPushButton, QLabel
)
from PyQt6.QtCore import pyqtSignal


class RecordingControlWidget(QWidget):
    """錄影控制組件"""

    # 信號
    start_recording = pyqtSignal()
    stop_recording = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_recording = False
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)

        # 創建分組框
        group_box = QGroupBox("🎥 錄影控制")
        group_layout = QVBoxLayout()

        # 錄影按鈕
        self.record_btn = QPushButton("⏺️ 開始錄製")
        self.record_btn.setEnabled(False)
        self.record_btn.clicked.connect(self.on_record_clicked)
        group_layout.addWidget(self.record_btn)

        # 錄影狀態
        self.status_label = QLabel("狀態: 未錄製")
        group_layout.addWidget(self.status_label)

        # 幀計數
        self.frame_count_label = QLabel("已錄製: 0 幀")
        group_layout.addWidget(self.frame_count_label)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

    def on_record_clicked(self):
        """錄影按鈕點擊"""
        if self.is_recording:
            self.stop_recording.emit()
            self.is_recording = False
            self.record_btn.setText("⏺️ 開始錄製")
            self.record_btn.setStyleSheet("")
            self.status_label.setText("狀態: 未錄製")
        else:
            self.start_recording.emit()
            self.is_recording = True
            self.record_btn.setText("⏹️ 停止錄製")
            self.record_btn.setStyleSheet("background-color: #f44336;")
            self.status_label.setText("狀態: 🔴 錄製中...")

    def set_enabled(self, enabled):
        """設置啟用狀態"""
        self.record_btn.setEnabled(enabled)

    def update_frame_count(self, count):
        """更新幀計數"""
        self.frame_count_label.setText(f"已錄製: {count} 幀")
