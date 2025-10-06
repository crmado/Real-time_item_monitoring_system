"""
相機控制組件
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QListWidget, QLabel, QSlider, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal


class CameraControlWidget(QWidget):
    """相機控制組件"""

    # 信號
    detect_clicked = pyqtSignal()
    connect_clicked = pyqtSignal(int)
    disconnect_clicked = pyqtSignal()
    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    exposure_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_camera_index = None
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)

        # 創建分組框
        group_box = QGroupBox("📷 相機控制")
        group_layout = QVBoxLayout()

        # 檢測按鈕
        self.detect_btn = QPushButton("🔍 檢測相機")
        self.detect_btn.clicked.connect(self.detect_clicked.emit)
        group_layout.addWidget(self.detect_btn)

        # 相機列表
        self.camera_list = QListWidget()
        self.camera_list.setMaximumHeight(150)
        self.camera_list.itemClicked.connect(self.on_camera_selected)
        group_layout.addWidget(QLabel("可用相機:"))
        group_layout.addWidget(self.camera_list)

        # 連接/斷開按鈕
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("連接")
        self.connect_btn.setEnabled(False)
        self.connect_btn.clicked.connect(self.on_connect_clicked)

        self.disconnect_btn = QPushButton("斷開")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.clicked.connect(self.disconnect_clicked.emit)

        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.disconnect_btn)
        group_layout.addLayout(btn_layout)

        # 開始/停止抓取
        grab_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶️ 開始抓取")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start_clicked.emit)

        self.stop_btn = QPushButton("⏸️ 停止抓取")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_clicked.emit)

        grab_layout.addWidget(self.start_btn)
        grab_layout.addWidget(self.stop_btn)
        group_layout.addLayout(grab_layout)

        # 曝光控制
        group_layout.addWidget(QLabel("曝光時間 (μs):"))
        exposure_layout = QHBoxLayout()

        self.exposure_slider = QSlider(Qt.Orientation.Horizontal)
        self.exposure_slider.setMinimum(100)
        self.exposure_slider.setMaximum(10000)
        self.exposure_slider.setValue(1000)
        self.exposure_slider.setEnabled(False)
        self.exposure_slider.valueChanged.connect(self.on_exposure_changed)

        self.exposure_label = QLabel("1000")
        exposure_layout.addWidget(self.exposure_slider)
        exposure_layout.addWidget(self.exposure_label)
        group_layout.addLayout(exposure_layout)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

    def update_camera_list(self, cameras):
        """更新相機列表"""
        self.camera_list.clear()

        for camera in cameras:
            item_text = f"{camera['model']} ({camera['serial']})"
            if camera.get('is_target', False):
                item_text += " ✓"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, camera['index'])
            self.camera_list.addItem(item)

    def on_camera_selected(self, item):
        """相機選中"""
        self.selected_camera_index = item.data(Qt.ItemDataRole.UserRole)
        self.connect_btn.setEnabled(True)

    def on_connect_clicked(self):
        """連接按鈕點擊"""
        if self.selected_camera_index is not None:
            self.connect_clicked.emit(self.selected_camera_index)
            self.disconnect_btn.setEnabled(True)
            self.start_btn.setEnabled(True)
            self.exposure_slider.setEnabled(True)

    def on_exposure_changed(self, value):
        """曝光值改變"""
        self.exposure_label.setText(str(value))
        self.exposure_changed.emit(float(value))

    def set_grabbing_state(self, grabbing):
        """設置抓取狀態"""
        if grabbing:
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def set_video_mode(self, is_video: bool):
        """設置為視頻模式"""
        if is_video:
            # 視頻模式：隱藏相機相關控件
            self.detect_btn.setEnabled(False)
            self.camera_list.setEnabled(False)
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(False)
            self.exposure_slider.setEnabled(False)
            self.start_btn.setEnabled(True)
            self.start_btn.setText("▶️ 播放")
            self.stop_btn.setText("⏸️ 暫停")
        else:
            # 相機模式：恢復相機控件
            self.detect_btn.setEnabled(True)
            self.camera_list.setEnabled(True)
            self.start_btn.setText("▶️ 開始抓取")
            self.stop_btn.setText("⏸️ 停止抓取")
