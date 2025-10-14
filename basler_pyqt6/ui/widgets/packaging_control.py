"""
定量包裝控制組件 - 工業級震動機自動控制
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QSpinBox, QProgressBar, QDoubleSpinBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont

# 導入圖示管理器
from basler_pyqt6.resources.icons import get_icon, Icons


class PackagingControlWidget(QWidget):
    """定量包裝控制組件 - 工業級操作面板"""

    # 信號定義
    start_packaging_requested = pyqtSignal()      # 開始包裝請求
    pause_packaging_requested = pyqtSignal()      # 暫停包裝請求
    reset_count_requested = pyqtSignal()          # 重置計數請求
    target_count_changed = pyqtSignal(int)        # 目標數量變更
    threshold_changed = pyqtSignal(str, float)    # 閾值變更 (threshold_name, value)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_packaging_active = False
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ========== 區塊 1: 包裝參數設定 ==========
        params_group = QGroupBox("📦 定量包裝設定")
        params_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                color: #e5e7eb;
                border: 2px solid #374151;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #1a1f2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
        """)
        params_layout = QVBoxLayout()
        params_layout.setSpacing(12)

        # 目標數量設定
        target_container = QWidget()
        target_layout = QHBoxLayout(target_container)
        target_layout.setContentsMargins(10, 5, 10, 5)

        target_label = QLabel("🎯 目標數量:")
        target_label.setStyleSheet("color: #e5e7eb; font-size: 10pt; font-weight: normal;")
        target_layout.addWidget(target_label)

        self.target_count_spinbox = QSpinBox()
        self.target_count_spinbox.setRange(1, 99999)
        self.target_count_spinbox.setValue(150)
        self.target_count_spinbox.setSuffix(" 顆")
        self.target_count_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.target_count_spinbox.setStyleSheet("""
            QSpinBox {
                background-color: #0f1419;
                border: 2px solid #374151;
                border-radius: 6px;
                padding: 8px 12px;
                color: #10b981;
                font-size: 13pt;
                font-weight: bold;
                min-width: 150px;
            }
            QSpinBox:focus {
                border: 2px solid #10b981;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 24px;
                background-color: #374151;
                border-radius: 4px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #4b5563;
            }
        """)
        self.target_count_spinbox.valueChanged.connect(self._on_target_count_changed)
        target_layout.addWidget(self.target_count_spinbox)
        target_layout.addStretch()

        params_layout.addWidget(target_container)

        # 速度控制閾值設定（折疊式專業控制）
        threshold_container = QWidget()
        threshold_layout = QVBoxLayout(threshold_container)
        threshold_layout.setSpacing(8)
        threshold_layout.setContentsMargins(10, 5, 10, 10)

        # 閾值標題
        threshold_title = QLabel("⚙️ 自動速度控制閾值（進階設定）")
        threshold_title.setStyleSheet("color: #9ca3af; font-size: 9pt; font-weight: bold;")
        threshold_layout.addWidget(threshold_title)

        # 中速閾值
        medium_row = self._create_threshold_row(
            "中速啟動",
            "speed_medium",
            0.85,
            "達到此百分比時降為中速"
        )
        threshold_layout.addWidget(medium_row)

        # 慢速閾值
        slow_row = self._create_threshold_row(
            "慢速啟動",
            "speed_slow",
            0.93,
            "達到此百分比時降為慢速"
        )
        threshold_layout.addWidget(slow_row)

        # 極慢速閾值
        creep_row = self._create_threshold_row(
            "極慢速啟動",
            "speed_creep",
            0.97,
            "達到此百分比時降為極慢速"
        )
        threshold_layout.addWidget(creep_row)

        params_layout.addWidget(threshold_container)
        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)

        # ========== 區塊 2: 包裝進度顯示 ==========
        status_group = QGroupBox("📊 包裝進度")
        status_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                color: #e5e7eb;
                border: 2px solid #374151;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #1a1f2e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
        """)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(12)
        status_layout.setContentsMargins(15, 15, 15, 15)

        # === 當前計數顯示（大字體） ===
        count_display = QWidget()
        count_layout = QHBoxLayout(count_display)
        count_layout.setContentsMargins(0, 0, 0, 0)
        count_layout.setSpacing(10)

        count_label_text = QLabel("當前計數:")
        count_label_text.setStyleSheet("color: #d1d5db; font-size: 12pt; font-weight: bold;")
        count_layout.addWidget(count_label_text)

        self.current_count_label = QLabel("0")
        self.current_count_label.setStyleSheet("color: #3b82f6; font-size: 32pt; font-weight: bold;")
        count_layout.addWidget(self.current_count_label)

        self.target_count_label = QLabel("/ 150")
        self.target_count_label.setStyleSheet("color: #9ca3af; font-size: 18pt; font-weight: bold;")
        count_layout.addWidget(self.target_count_label)

        count_layout.addStretch()

        self.progress_percent_label = QLabel("0%")
        self.progress_percent_label.setStyleSheet("color: #f59e0b; font-size: 24pt; font-weight: bold;")
        count_layout.addWidget(self.progress_percent_label)

        status_layout.addWidget(count_display)

        # === 進度條 ===
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setSpacing(5)

        progress_title = QLabel("包裝進度")
        progress_title.setStyleSheet("color: #9ca3af; font-size: 9pt;")
        progress_layout.addWidget(progress_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #374151;
                border-radius: 8px;
                background-color: #0f1419;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
                font-size: 11pt;
                min-height: 32px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:0.5 #8b5cf6, stop:1 #ec4899);
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        status_layout.addWidget(progress_container)

        # === 雙震動機狀態指示（並排顯示） ===
        vibrators_row = QWidget()
        vibrators_row_layout = QHBoxLayout(vibrators_row)
        vibrators_row_layout.setSpacing(10)
        vibrators_row_layout.setContentsMargins(0, 0, 0, 0)

        # 震動機A
        self.vibrator1_card = self._create_vibrator_status_card("震動機A")
        vibrators_row_layout.addWidget(self.vibrator1_card['container'])

        # 震動機B
        self.vibrator2_card = self._create_vibrator_status_card("震動機B")
        vibrators_row_layout.addWidget(self.vibrator2_card['container'])

        status_layout.addWidget(vibrators_row)

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # ========== 區塊 3: 控制按鈕 ==========
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(12)
        buttons_layout.setContentsMargins(0, 5, 0, 0)

        # 開始包裝按鈕
        self.start_btn = QPushButton(" 開始包裝")
        self.start_btn.setIcon(get_icon(Icons.PLAY, 24))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #10b981, stop:1 #059669);
                border: 3px solid #34d399;
                border-radius: 10px;
                padding: 15px 20px;
                color: #ffffff;
                font-weight: bold;
                font-size: 12pt;
                min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34d399, stop:1 #10b981);
            }
            QPushButton:pressed {
                background: #059669;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
                border: 2px solid #4b5563;
            }
        """)
        self.start_btn.clicked.connect(self._on_start_clicked)
        buttons_layout.addWidget(self.start_btn, 2)

        # 暫停按鈕
        self.pause_btn = QPushButton(" 暫停")
        self.pause_btn.setIcon(get_icon(Icons.PAUSE, 24))
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f59e0b, stop:1 #d97706);
                border: 3px solid #fbbf24;
                border-radius: 10px;
                padding: 15px 20px;
                color: #ffffff;
                font-weight: bold;
                font-size: 12pt;
                min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fbbf24, stop:1 #f59e0b);
            }
            QPushButton:pressed {
                background: #d97706;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
                border: 2px solid #4b5563;
            }
        """)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        buttons_layout.addWidget(self.pause_btn, 1)

        # 重置計數按鈕
        self.reset_btn = QPushButton(" 重置")
        self.reset_btn.setIcon(get_icon(Icons.RESET, 24))
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6b7280, stop:1 #4b5563);
                border: 2px solid #9ca3af;
                border-radius: 10px;
                padding: 15px 20px;
                color: #ffffff;
                font-weight: bold;
                font-size: 12pt;
                min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9ca3af, stop:1 #6b7280);
            }
            QPushButton:pressed {
                background: #4b5563;
            }
        """)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        buttons_layout.addWidget(self.reset_btn, 1)

        main_layout.addWidget(buttons_container)
        main_layout.addStretch()

    def _create_threshold_row(self, label_text: str, threshold_name: str,
                               default_value: float, tooltip: str) -> QWidget:
        """創建閾值設定行"""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        label = QLabel(f"  {label_text}:")
        label.setStyleSheet("color: #d1d5db; font-size: 9pt;")
        label.setFixedWidth(100)
        layout.addWidget(label)

        spinbox = QDoubleSpinBox()
        spinbox.setRange(0.0, 1.0)
        spinbox.setSingleStep(0.01)
        spinbox.setValue(default_value)
        spinbox.setDecimals(2)
        spinbox.setSuffix(" %")
        spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        spinbox.setToolTip(tooltip)
        spinbox.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #1f2937;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 4px 8px;
                color: #e5e7eb;
                font-size: 9pt;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #3b82f6;
            }
        """)
        spinbox.valueChanged.connect(
            lambda val: self.threshold_changed.emit(threshold_name, val)
        )
        layout.addWidget(spinbox)

        # 存儲 spinbox 引用
        setattr(self, f"{threshold_name}_spinbox", spinbox)

        layout.addStretch()
        return row

    def _create_status_card(self, title: str, color: str, bg_color: str,
                            unit: str = "") -> dict:
        """創建狀態卡片"""
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color}40, stop:1 {bg_color});
                border: 2px solid {color};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: #d1d5db; font-size: 9pt; background: transparent; border: none;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        value_label = QLabel("0")
        value_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 26pt; background: transparent; border: none;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        if unit:
            unit_label = QLabel(unit)
            unit_label.setStyleSheet("color: #9ca3af; font-size: 9pt; background: transparent; border: none;")
            unit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(unit_label)

        return {
            'widget': card,
            'value_label': value_label
        }

    def _create_vibrator_status_card(self, vibrator_name: str) -> dict:
        """
        創建震動機狀態卡片

        Args:
            vibrator_name: 震動機名稱（如 "震動機A", "震動機B"）

        Returns:
            包含卡片元件和控制元件的字典
        """
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e293b, stop:1 #0f172a);
                border: 2px solid #475569;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 標題行
        title_row = QHBoxLayout()
        title_label = QLabel(vibrator_name)
        title_label.setStyleSheet("color: #cbd5e1; font-size: 9pt; font-weight: bold; background: transparent; border: none;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        layout.addLayout(title_row)

        # 狀態指示器 + 狀態文字
        status_row = QHBoxLayout()
        status_row.setSpacing(8)

        indicator = QLabel("●")
        indicator.setStyleSheet("color: #6b7280; font-size: 16pt; background: transparent; border: none;")
        status_row.addWidget(indicator)

        status_label = QLabel("停止")
        status_label.setStyleSheet("color: #9ca3af; font-size: 10pt; font-weight: bold; background: transparent; border: none;")
        status_row.addWidget(status_label)

        status_row.addStretch()

        speed_label = QLabel("0%")
        speed_label.setStyleSheet("color: #60a5fa; font-size: 12pt; font-weight: bold; background: transparent; border: none;")
        status_row.addWidget(speed_label)

        layout.addLayout(status_row)

        return {
            'container': container,
            'indicator': indicator,
            'status_label': status_label,
            'speed_label': speed_label
        }

    def _on_start_clicked(self):
        """開始包裝按鈕點擊"""
        self.is_packaging_active = True
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.target_count_spinbox.setEnabled(False)  # 鎖定目標數量
        self.start_packaging_requested.emit()

    def _on_pause_clicked(self):
        """暫停按鈕點擊"""
        self.is_packaging_active = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_packaging_requested.emit()

    def _on_reset_clicked(self):
        """重置按鈕點擊"""
        self.reset_count_requested.emit()
        self.update_count(0)
        if not self.is_packaging_active:
            self.target_count_spinbox.setEnabled(True)

    def _on_target_count_changed(self, value: int):
        """目標數量改變時的處理"""
        # 1. 即時更新包裝進度區的目標數量顯示
        self.target_count_label.setText(f"/ {value}")

        # 2. 發射信號通知主窗口
        self.target_count_changed.emit(value)

        # 3. 重新計算並更新進度百分比
        current = int(self.current_count_label.text())
        if value > 0:
            progress = min(100, int((current / value) * 100))
        else:
            progress = 0
        self.progress_percent_label.setText(f"{progress}%")
        self.progress_bar.setValue(progress)

    def update_count(self, current: int):
        """
        更新當前計數和進度

        Args:
            current: 當前計數
        """
        target = self.target_count_spinbox.value()

        # 更新當前計數
        self.current_count_label.setText(str(current))

        # 更新目標顯示（格式："/ 150"）
        self.target_count_label.setText(f"/ {target}")

        # 計算進度百分比
        if target > 0:
            progress = min(100, int((current / target) * 100))
        else:
            progress = 0

        self.progress_percent_label.setText(f"{progress}%")
        self.progress_bar.setValue(progress)

        # 檢查是否完成
        if current >= target and self.is_packaging_active:
            self._on_packaging_complete()

    def update_vibrator_status(
        self,
        vibrator1_status: dict,
        vibrator2_status: dict
    ):
        """
        更新兩台震動機的狀態顯示

        Args:
            vibrator1_status: 震動機A狀態字典 {'speed': str, 'speed_percent': int, 'is_running': bool}
            vibrator2_status: 震動機B狀態字典 {'speed': str, 'speed_percent': int, 'is_running': bool}
        """
        self._update_single_vibrator_card(self.vibrator1_card, vibrator1_status)
        self._update_single_vibrator_card(self.vibrator2_card, vibrator2_status)

    def _update_single_vibrator_card(self, card: dict, status: dict):
        """
        更新單一震動機卡片

        Args:
            card: 震動機卡片字典
            status: 狀態字典 {'speed': str, 'speed_percent': int, 'is_running': bool}
        """
        speed_name = status.get('speed', '停止')
        speed_percent = status.get('speed_percent', 0)
        is_running = status.get('is_running', False)

        # 更新指示燈顏色
        if is_running:
            if speed_percent >= 80:
                color = "#10b981"  # 綠色 - 全速
            elif speed_percent >= 50:
                color = "#3b82f6"  # 藍色 - 中速
            elif speed_percent >= 20:
                color = "#f59e0b"  # 橙色 - 慢速
            else:
                color = "#fbbf24"  # 黃色 - 極慢速
        else:
            color = "#6b7280"  # 灰色 - 停止

        card['indicator'].setStyleSheet(f"color: {color}; font-size: 16pt; background: transparent; border: none;")

        # 更新狀態文字
        card['status_label'].setText(speed_name)

        # 更新速度百分比
        card['speed_label'].setText(f"{speed_percent}%")

    def _on_packaging_complete(self):
        """包裝完成處理"""
        self.is_packaging_active = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.target_count_spinbox.setEnabled(True)

        # TODO: 播放提示音（如果啟用）
        print("🎉 包裝完成！")

    def get_target_count(self) -> int:
        """獲取目標數量"""
        return self.target_count_spinbox.value()

    def set_target_count(self, count: int):
        """設定目標數量"""
        self.target_count_spinbox.setValue(count)
