"""
錄影控制組件
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox,
    QPushButton, QLabel, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal, Qt

# 導入圖示管理器
from basler_pyqt6.resources.icons import get_icon, get_pixmap, Icons


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
        group_box = QGroupBox("錄影控制")
        group_layout = QVBoxLayout()

        # 錄影按鈕（使用圖示）
        self.record_btn = QPushButton(" 開始錄製")
        self.record_btn.setIcon(get_icon(Icons.PLAY, 24))
        self.record_btn.setStyleSheet("padding-left: 10px;")
        self.record_btn.setEnabled(False)
        self.record_btn.clicked.connect(self.on_record_clicked)
        group_layout.addWidget(self.record_btn)

        # 錄影狀態（帶圖示指示器）
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 5, 0, 5)
        status_layout.setSpacing(8)

        self.status_icon = QLabel()
        self.status_icon.setPixmap(get_pixmap(Icons.TOGGLE_OFF, 16))
        status_layout.addWidget(self.status_icon)

        self.status_label = QLabel("狀態: 未錄製")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        group_layout.addWidget(status_container)

        # 幀計數
        self.frame_count_label = QLabel("已錄製: 0 幀")
        group_layout.addWidget(self.frame_count_label)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

    def on_record_clicked(self):
        """錄影按鈕點擊"""
        if self.is_recording:
            # 停止錄製
            self.stop_recording.emit()
            self.is_recording = False
            self.record_btn.setText(" 開始錄製")
            self.record_btn.setIcon(get_icon(Icons.PLAY, 24))
            self.record_btn.setStyleSheet("padding-left: 10px;")
            self.status_icon.setPixmap(get_pixmap(Icons.TOGGLE_OFF, 16))
            self.status_label.setText("狀態: 未錄製")
        else:
            # 開始錄製
            self.start_recording.emit()
            self.is_recording = True
            self.record_btn.setText(" 停止錄製")
            self.record_btn.setIcon(get_icon(Icons.STOP, 24))
            self.record_btn.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef4444, stop:1 #dc2626);
                border: 1px solid #fca5a5;
                color: #ffffff;
                padding-left: 10px;
            """)
            self.status_icon.setPixmap(get_pixmap(Icons.TOGGLE_ON, 16))
            self.status_label.setText("狀態: 錄製中...")
            self.status_label.setStyleSheet("color: #ef4444; font-weight: bold;")

    def set_enabled(self, enabled):
        """設置啟用狀態"""
        self.record_btn.setEnabled(enabled)

    def update_frame_count(self, count):
        """更新幀計數"""
        self.frame_count_label.setText(f"已錄製: {count} 幀")
