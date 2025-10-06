"""
小零件檢測控制組件
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QHBoxLayout,
    QPushButton, QLabel, QCheckBox, QSpinBox
)
from PyQt6.QtCore import pyqtSignal


class DetectionControlWidget(QWidget):
    """小零件檢測控制組件"""

    # 信號
    enable_changed = pyqtSignal(bool)
    roi_enabled_changed = pyqtSignal(bool)
    high_speed_changed = pyqtSignal(bool)
    reset_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)

        # 創建分組框
        group_box = QGroupBox("🔍 小零件檢測控制")
        group_layout = QVBoxLayout()

        # 檢測算法說明
        algo_label = QLabel("算法: 背景減除 + 物件追蹤 (小零件專用)")
        algo_label.setStyleSheet("color: #00d4ff; font-size: 10pt; font-weight: bold;")
        group_layout.addWidget(algo_label)

        # 啟用/禁用檢測
        self.enable_checkbox = QCheckBox("✅ 啟用檢測")
        self.enable_checkbox.setStyleSheet("font-size: 11pt; font-weight: bold;")
        self.enable_checkbox.stateChanged.connect(
            lambda state: self.enable_changed.emit(state == 2)
        )
        group_layout.addWidget(self.enable_checkbox)

        # ROI 區域檢測
        self.roi_checkbox = QCheckBox("📍 啟用 ROI 區域檢測")
        self.roi_checkbox.setStyleSheet("font-size: 10pt;")
        self.roi_checkbox.setToolTip("只檢測畫面特定區域,提升性能")
        self.roi_checkbox.setChecked(True)  # 預設啟用
        self.roi_checkbox.stateChanged.connect(
            lambda state: self.roi_enabled_changed.emit(state == 2)
        )
        group_layout.addWidget(self.roi_checkbox)

        # 超高速模式
        self.high_speed_checkbox = QCheckBox("🚀 超高速模式 (280+ FPS)")
        self.high_speed_checkbox.setStyleSheet("font-size: 10pt;")
        self.high_speed_checkbox.setToolTip("簡化處理流程,適合高速相機")
        self.high_speed_checkbox.stateChanged.connect(
            lambda state: self.high_speed_changed.emit(state == 2)
        )
        group_layout.addWidget(self.high_speed_checkbox)

        # 分隔線
        separator = QLabel("─" * 40)
        separator.setStyleSheet("color: #4a5568;")
        group_layout.addWidget(separator)

        # 檢測狀態顯示
        self.status_label = QLabel("狀態: ❌ 未啟用")
        self.status_label.setStyleSheet("color: #fbbf24; font-size: 11pt;")
        group_layout.addWidget(self.status_label)

        # 檢測計數顯示
        self.count_label = QLabel("檢測數量: 0")
        self.count_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 12pt;")
        group_layout.addWidget(self.count_label)

        # 穿越計數顯示
        self.crossing_label = QLabel("穿越計數: 0")
        self.crossing_label.setStyleSheet("color: #10b981; font-weight: bold; font-size: 12pt;")
        group_layout.addWidget(self.crossing_label)

        # 追蹤數量顯示
        self.tracking_label = QLabel("追蹤中: 0")
        self.tracking_label.setStyleSheet("color: #8b5cf6; font-size: 11pt;")
        group_layout.addWidget(self.tracking_label)

        # 分隔線
        separator2 = QLabel("─" * 40)
        separator2.setStyleSheet("color: #4a5568;")
        group_layout.addWidget(separator2)

        # 重置按鈕
        self.reset_btn = QPushButton("🔄 重置計數器")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_requested.emit)
        group_layout.addWidget(self.reset_btn)

        # 參數說明
        params_label = QLabel("📊 當前參數:")
        params_label.setStyleSheet("color: #9ca3af; font-size: 10pt; margin-top: 10px;")
        group_layout.addWidget(params_label)

        self.params_text = QLabel(
            "• 最小面積: 2 像素\n"
            "• 背景歷史: 1000 幀\n"
            "• 靈敏度閾值: 3\n"
            "• 分水嶺分離: 啟用"
        )
        self.params_text.setStyleSheet("color: #6b7280; font-size: 9pt; padding-left: 10px;")
        group_layout.addWidget(self.params_text)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)
        layout.addStretch()

    def update_status(self, enabled: bool, det_count: int = 0, cross_count: int = 0, track_count: int = 0):
        """更新狀態顯示"""
        if enabled:
            self.status_label.setText("狀態: ✅ 運行中")
            self.status_label.setStyleSheet("color: #10b981; font-size: 11pt; font-weight: bold;")
        else:
            self.status_label.setText("狀態: ❌ 未啟用")
            self.status_label.setStyleSheet("color: #fbbf24; font-size: 11pt;")

        self.count_label.setText(f"檢測數量: {det_count}")
        self.crossing_label.setText(f"穿越計數: {cross_count}")
        self.tracking_label.setText(f"追蹤中: {track_count}")

    def set_high_speed_mode(self, enabled: bool):
        """設置高速模式顯示"""
        if enabled:
            self.params_text.setText(
                "🚀 高速模式啟用:\n"
                "• 簡化處理流程\n"
                "• 目標: 280+ FPS\n"
                "• 追蹤功能: 禁用"
            )
            self.params_text.setStyleSheet("color: #f59e0b; font-size: 9pt; padding-left: 10px; font-weight: bold;")
        else:
            self.params_text.setText(
                "• 最小面積: 2 像素\n"
                "• 背景歷史: 1000 幀\n"
                "• 靈敏度閾值: 3\n"
                "• 分水嶺分離: 啟用"
            )
            self.params_text.setStyleSheet("color: #6b7280; font-size: 9pt; padding-left: 10px;")
