"""
檢測控制組件
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QCheckBox
)
from PyQt6.QtCore import pyqtSignal


class DetectionControlWidget(QWidget):
    """檢測控制組件"""

    # 信號
    method_changed = pyqtSignal(str)
    enable_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)

        # 創建分組框
        group_box = QGroupBox("🔍 檢測控制")
        group_layout = QVBoxLayout()

        # 檢測方法選擇
        group_layout.addWidget(QLabel("檢測方法:"))
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "圓形檢測 (Circle)",
            "輪廓檢測 (Contour)",
            "增強檢測 (Enhanced)",
            "背景減除 (Background)"
        ])
        self.method_combo.currentTextChanged.connect(self.on_method_changed)
        group_layout.addWidget(self.method_combo)

        # 啟用/禁用檢測
        self.enable_checkbox = QCheckBox("啟用檢測")
        self.enable_checkbox.stateChanged.connect(
            lambda state: self.enable_changed.emit(state == 2)
        )
        group_layout.addWidget(self.enable_checkbox)

        # 檢測狀態顯示
        self.status_label = QLabel("狀態: 未啟用")
        self.status_label.setStyleSheet("color: #ff9800;")
        group_layout.addWidget(self.status_label)

        # 檢測計數顯示
        self.count_label = QLabel("檢測數量: 0")
        self.count_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        group_layout.addWidget(self.count_label)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

    def on_method_changed(self, text):
        """檢測方法改變"""
        # 提取方法名稱
        method_map = {
            "圓形檢測 (Circle)": "circle",
            "輪廓檢測 (Contour)": "contour",
            "增強檢測 (Enhanced)": "enhanced",
            "背景減除 (Background)": "background"
        }
        method = method_map.get(text, "circle")
        self.method_changed.emit(method)

    def update_status(self, enabled, count=0):
        """更新狀態顯示"""
        if enabled:
            self.status_label.setText("狀態: ✅ 已啟用")
            self.status_label.setStyleSheet("color: #4caf50;")
        else:
            self.status_label.setText("狀態: ❌ 未啟用")
            self.status_label.setStyleSheet("color: #ff9800;")

        self.count_label.setText(f"檢測數量: {count}")
