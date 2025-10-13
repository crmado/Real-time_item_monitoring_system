"""
小零件檢測控制組件
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QHBoxLayout,
    QPushButton, QLabel, QCheckBox, QSpinBox
)
from PyQt6.QtCore import pyqtSignal, Qt

# 導入圖示管理器
from basler_pyqt6.resources.icons import get_icon, get_pixmap, Icons


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
        layout.setSpacing(10)

        # 創建分組框
        group_box = QGroupBox("🔍 檢測控制")
        group_layout = QVBoxLayout()
        group_layout.setSpacing(12)

        # === 工業級大型數據卡片區 ===
        data_cards_container = QWidget()
        data_cards_layout = QHBoxLayout(data_cards_container)
        data_cards_layout.setSpacing(10)
        data_cards_layout.setContentsMargins(0, 0, 0, 0)

        # 卡片1: 檢測數量
        count_card = QWidget()
        count_card.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e3a5f, stop:1 #0d2544);
                border: 2px solid #00d4ff;
                border-radius: 12px;
            }
        """)
        count_card_layout = QVBoxLayout(count_card)
        count_card_layout.setContentsMargins(12, 10, 12, 10)
        count_card_layout.setSpacing(2)

        count_title = QLabel("即時檢測")
        count_title.setStyleSheet("color: #9ca3af; font-size: 9pt; background: transparent; border: none;")
        count_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_card_layout.addWidget(count_title)

        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 28pt; background: transparent; border: none;")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_card_layout.addWidget(self.count_label)

        count_unit = QLabel("物件/幀")
        count_unit.setStyleSheet("color: #6b7280; font-size: 8pt; background: transparent; border: none;")
        count_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_card_layout.addWidget(count_unit)

        data_cards_layout.addWidget(count_card)

        # 卡片2: 穿越計數
        crossing_card = QWidget()
        crossing_card.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e5a3a, stop:1 #0d4425);
                border: 2px solid #10b981;
                border-radius: 12px;
            }
        """)
        crossing_card_layout = QVBoxLayout(crossing_card)
        crossing_card_layout.setContentsMargins(12, 10, 12, 10)
        crossing_card_layout.setSpacing(2)

        crossing_title = QLabel("累計穿越")
        crossing_title.setStyleSheet("color: #9ca3af; font-size: 9pt; background: transparent; border: none;")
        crossing_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        crossing_card_layout.addWidget(crossing_title)

        self.crossing_label = QLabel("0")
        self.crossing_label.setStyleSheet("color: #10b981; font-weight: bold; font-size: 28pt; background: transparent; border: none;")
        self.crossing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        crossing_card_layout.addWidget(self.crossing_label)

        crossing_unit = QLabel("總計數")
        crossing_unit.setStyleSheet("color: #6b7280; font-size: 8pt; background: transparent; border: none;")
        crossing_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        crossing_card_layout.addWidget(crossing_unit)

        data_cards_layout.addWidget(crossing_card)

        group_layout.addWidget(data_cards_container)

        # === 狀態指示器（大型視覺化，使用圖示）===
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(10)

        # 狀態圖示
        self.status_icon = QLabel()
        self.status_icon.setPixmap(get_pixmap(Icons.TOGGLE_OFF, 32))
        self.status_icon.setStyleSheet("background: transparent; border: none;")
        status_layout.addWidget(self.status_icon)

        # 狀態文字
        self.status_label = QLabel("待機中")
        self.status_label.setStyleSheet("""
            color: #9ca3af;
            font-size: 13pt;
            font-weight: bold;
            background-color: transparent;
            border: none;
        """)
        status_layout.addWidget(self.status_label)

        # 包裝容器
        status_wrapper = QWidget()
        status_wrapper.setStyleSheet("""
            QWidget {
                background-color: #1f2a3d;
                border: 2px solid #4a5568;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        status_wrapper_layout = QHBoxLayout(status_wrapper)
        status_wrapper_layout.setContentsMargins(10, 10, 10, 10)
        status_wrapper_layout.addWidget(status_container)

        group_layout.addWidget(status_wrapper)

        # === 追蹤資訊（次要資訊）===
        self.tracking_label = QLabel("追蹤緩存: 0 筆記錄")
        self.tracking_label.setStyleSheet("color: #6b7280; font-size: 10pt; background: transparent; border: none;")
        self.tracking_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group_layout.addWidget(self.tracking_label)

        # === 選項控制區 ===
        options_container = QWidget()
        options_layout = QVBoxLayout(options_container)
        options_layout.setContentsMargins(8, 5, 8, 5)
        options_layout.setSpacing(8)

        # 啟用/禁用檢測
        self.enable_checkbox = QCheckBox("啟用檢測")
        self.enable_checkbox.setStyleSheet("font-size: 10pt; font-weight: bold; background: transparent; border: none;")
        self.enable_checkbox.stateChanged.connect(
            lambda state: self.enable_changed.emit(state == 2)
        )
        options_layout.addWidget(self.enable_checkbox)

        # ROI 區域檢測
        self.roi_checkbox = QCheckBox("ROI 區域檢測（性能優化）")
        self.roi_checkbox.setStyleSheet("font-size: 9pt; background: transparent; border: none;")
        self.roi_checkbox.setToolTip("只檢測畫面特定區域，提升處理速度")
        self.roi_checkbox.setChecked(True)  # 預設啟用
        self.roi_checkbox.stateChanged.connect(
            lambda state: self.roi_enabled_changed.emit(state == 2)
        )
        options_layout.addWidget(self.roi_checkbox)

        # 超高速模式
        self.high_speed_checkbox = QCheckBox("🚀 超高速模式 (280+ FPS)")
        self.high_speed_checkbox.setStyleSheet("font-size: 9pt; color: #f59e0b; font-weight: bold; background: transparent; border: none;")
        self.high_speed_checkbox.setToolTip("簡化處理流程，適合高速工業相機")
        self.high_speed_checkbox.stateChanged.connect(
            lambda state: self.high_speed_changed.emit(state == 2)
        )
        options_layout.addWidget(self.high_speed_checkbox)

        group_layout.addWidget(options_container)

        # === 重置按鈕（工業級警告樣式）===
        self.reset_btn = QPushButton("🔄 重置計數器")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc2626, stop:1 #991b1b);
                color: white;
                border: 2px solid #ef4444;
                padding: 10px;
                border-radius: 8px;
                font-size: 11pt;
                font-weight: bold;
                min-height: 40px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef4444, stop:1 #dc2626);
                border: 2px solid #fca5a5;
            }
            QPushButton:pressed {
                background: #991b1b;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_requested.emit)
        group_layout.addWidget(self.reset_btn)

        # === 參數說明（收縮，背景資訊）===
        self.params_text = QLabel(
            "📊 極小零件檢測 | 最小: 2px | 閾值: 3 | 學習率: 0.001"
        )
        self.params_text.setStyleSheet("""
            color: #4a5568;
            font-size: 8pt;
            padding: 8px;
            background-color: #0a0e27;
            border-radius: 6px;
            border: 1px solid #1f3a5f;
        """)
        self.params_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.params_text.setWordWrap(True)
        group_layout.addWidget(self.params_text)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)
        layout.addStretch()

    def update_status(self, enabled: bool, det_count: int = 0, cross_count: int = 0, track_count: int = 0):
        """更新狀態顯示 - 工業級視覺化（使用圖示）"""
        # 更新大型數據卡片
        self.count_label.setText(f"{det_count}")
        self.crossing_label.setText(f"{cross_count:,}")  # 使用千分位格式化
        self.tracking_label.setText(f"追蹤緩存: {track_count} 筆記錄")

        # 更新狀態指示器（使用 toggle 圖示）
        if enabled:
            # 運行中 - 使用 toggle_on 綠色圖示
            self.status_icon.setPixmap(get_pixmap(Icons.TOGGLE_ON, 32))
            self.status_label.setText("運行中")
            self.status_label.setStyleSheet("""
                color: #10b981;
                font-size: 13pt;
                font-weight: bold;
                background-color: transparent;
                border: none;
            """)
        else:
            # 待機中 - 使用 toggle_off 灰色圖示
            self.status_icon.setPixmap(get_pixmap(Icons.TOGGLE_OFF, 32))
            self.status_label.setText("待機中")
            self.status_label.setStyleSheet("""
                color: #9ca3af;
                font-size: 13pt;
                font-weight: bold;
                background-color: transparent;
                border: none;
            """)

    def set_high_speed_mode(self, enabled: bool):
        """設置高速模式顯示"""
        if enabled:
            self.params_text.setText(
                "🚀 超高速模式 | 目標: 280+ FPS | 簡化處理 | 追蹤: 禁用"
            )
            self.params_text.setStyleSheet("""
                color: #f59e0b;
                font-size: 8pt;
                padding: 8px;
                background-color: #2d1f0a;
                border-radius: 6px;
                border: 1px solid #f59e0b;
                font-weight: bold;
            """)
        else:
            self.params_text.setText(
                "📊 極小零件檢測 | 最小: 2px | 閾值: 3 | 學習率: 0.001"
            )
            self.params_text.setStyleSheet("""
                color: #4a5568;
                font-size: 8pt;
                padding: 8px;
                background-color: #0a0e27;
                border-radius: 6px;
                border: 1px solid #1f3a5f;
            """)
