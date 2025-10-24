"""
瑕疵檢測方法控制面板
用於表面瑕疵檢測與品質控制
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QProgressBar, QDoubleSpinBox, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from basler_pyqt6.resources.icons import get_icon, Icons


class DefectDetectionMethodPanel(QWidget):
    """瑕疵檢測方法控制面板 - 品質控制專用"""

    # 信號定義
    start_detection_requested = pyqtSignal()         # 開始檢測請求
    stop_detection_requested = pyqtSignal()          # 停止檢測請求
    clear_stats_requested = pyqtSignal()             # 清除統計請求
    sensitivity_changed = pyqtSignal(float)          # 靈敏度變更

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_detecting = False
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ========== 區塊 1: 檢測參數設定 ==========
        params_group = QGroupBox("🔍 瑕疵檢測設定")
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
        params_layout.setContentsMargins(10, 10, 10, 10)

        # 檢測靈敏度設定
        sensitivity_container = QWidget()
        sensitivity_layout = QHBoxLayout(sensitivity_container)
        sensitivity_layout.setContentsMargins(0, 0, 0, 0)

        sensitivity_label = QLabel("檢測靈敏度:")
        sensitivity_label.setStyleSheet("color: #e5e7eb; font-size: 10pt; font-weight: normal;")
        sensitivity_layout.addWidget(sensitivity_label)

        self.sensitivity_spinbox = QDoubleSpinBox()
        self.sensitivity_spinbox.setRange(0.0, 1.0)
        self.sensitivity_spinbox.setSingleStep(0.05)
        self.sensitivity_spinbox.setValue(0.5)
        self.sensitivity_spinbox.setDecimals(2)
        self.sensitivity_spinbox.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.sensitivity_spinbox.setToolTip("瑕疵判定閾值（0.0-1.0，值越低越嚴格）")
        self.sensitivity_spinbox.setStyleSheet("""
            QDoubleSpinBox {
                background-color: #0f1419;
                border: 2px solid #374151;
                border-radius: 6px;
                padding: 8px 12px;
                color: #f59e0b;
                font-size: 13pt;
                font-weight: bold;
                min-width: 120px;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #f59e0b;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 24px;
                background-color: #374151;
                border-radius: 4px;
            }
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #4b5563;
            }
        """)
        self.sensitivity_spinbox.valueChanged.connect(self._on_sensitivity_changed)
        sensitivity_layout.addWidget(self.sensitivity_spinbox)
        sensitivity_layout.addStretch()

        params_layout.addWidget(sensitivity_container)

        # 說明文字
        desc_label = QLabel("💡 說明：靈敏度值越低，瑕疵判定越嚴格。建議從 0.5 開始調整。")
        desc_label.setStyleSheet("color: #9ca3af; font-size: 8pt; padding: 5px;")
        desc_label.setWordWrap(True)
        params_layout.addWidget(desc_label)

        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)

        # ========== 區塊 2: 檢測統計顯示 ==========
        stats_group = QGroupBox("品質統計")
        stats_group.setStyleSheet("""
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
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(12)
        stats_layout.setContentsMargins(15, 15, 15, 15)

        # === 合格率大卡片 ===
        pass_rate_card = QWidget()
        pass_rate_card.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e5a3a, stop:1 #0d4425);
                border: 3px solid #10b981;
                border-radius: 12px;
            }
        """)
        pass_rate_layout = QVBoxLayout(pass_rate_card)
        pass_rate_layout.setContentsMargins(15, 12, 15, 12)
        pass_rate_layout.setSpacing(5)

        pass_rate_title = QLabel("合格率")
        pass_rate_title.setStyleSheet("color: #9ca3af; font-size: 10pt; background: transparent; border: none;")
        pass_rate_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pass_rate_layout.addWidget(pass_rate_title)

        self.pass_rate_label = QLabel("100.0%")
        self.pass_rate_label.setStyleSheet("color: #10b981; font-weight: bold; font-size: 36pt; background: transparent; border: none;")
        self.pass_rate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pass_rate_layout.addWidget(self.pass_rate_label)

        stats_layout.addWidget(pass_rate_card)

        # === 統計數據卡片（並排） ===
        stats_cards_container = QWidget()
        stats_cards_layout = QHBoxLayout(stats_cards_container)
        stats_cards_layout.setSpacing(10)
        stats_cards_layout.setContentsMargins(0, 0, 0, 0)

        # 總檢測數卡片
        self.total_card = self._create_stat_card("總檢測數", "0", "#3b82f6")
        stats_cards_layout.addWidget(self.total_card['widget'])

        # 合格數卡片
        self.pass_card = self._create_stat_card("合格數", "0", "#10b981")
        stats_cards_layout.addWidget(self.pass_card['widget'])

        # 不合格數卡片
        self.fail_card = self._create_stat_card("不合格數", "0", "#ef4444")
        stats_cards_layout.addWidget(self.fail_card['widget'])

        stats_layout.addWidget(stats_cards_container)

        # === 瑕疵類型統計 ===
        defect_types_container = QWidget()
        defect_types_layout = QVBoxLayout(defect_types_container)
        defect_types_layout.setSpacing(8)
        defect_types_layout.setContentsMargins(0, 5, 0, 0)

        defect_title = QLabel("📋 瑕疵類型分佈")
        defect_title.setStyleSheet("color: #9ca3af; font-size: 10pt; font-weight: bold;")
        defect_types_layout.addWidget(defect_title)

        # 瑕疵類型卡片容器（帶邊框）
        defect_cards_frame = QFrame()
        defect_cards_frame.setStyleSheet("""
            QFrame {
                background-color: #0f1419;
                border: 2px solid #374151;
                border-radius: 8px;
            }
        """)
        defect_cards_layout = QVBoxLayout(defect_cards_frame)
        defect_cards_layout.setSpacing(8)
        defect_cards_layout.setContentsMargins(12, 12, 12, 12)

        # 瑕疵類型：刮痕
        self.scratch_row = self._create_defect_type_row("刮痕", "#f59e0b")
        defect_cards_layout.addWidget(self.scratch_row['widget'])

        # 瑕疵類型：凹陷
        self.dent_row = self._create_defect_type_row("凹陷", "#8b5cf6")
        defect_cards_layout.addWidget(self.dent_row['widget'])

        # 瑕疵類型：變色
        self.discoloration_row = self._create_defect_type_row("變色", "#ec4899")
        defect_cards_layout.addWidget(self.discoloration_row['widget'])

        defect_types_layout.addWidget(defect_cards_frame)
        stats_layout.addWidget(defect_types_container)

        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)

        # ========== 區塊 3: 控制按鈕 ==========
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(12)
        buttons_layout.setContentsMargins(0, 5, 0, 0)

        # 開始檢測按鈕
        self.start_btn = QPushButton(" 開始檢測")
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

        # 停止檢測按鈕
        self.stop_btn = QPushButton(" 停止")
        self.stop_btn.setIcon(get_icon(Icons.STOP, 24))
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef4444, stop:1 #dc2626);
                border: 3px solid #f87171;
                border-radius: 10px;
                padding: 15px 20px;
                color: #ffffff;
                font-weight: bold;
                font-size: 12pt;
                min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f87171, stop:1 #ef4444);
            }
            QPushButton:pressed {
                background: #dc2626;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
                border: 2px solid #4b5563;
            }
        """)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        buttons_layout.addWidget(self.stop_btn, 1)

        # 清除統計按鈕
        self.clear_btn = QPushButton(" 清除統計")
        self.clear_btn.setIcon(get_icon(Icons.RESET, 24))
        self.clear_btn.setStyleSheet("""
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
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        buttons_layout.addWidget(self.clear_btn, 1)

        main_layout.addWidget(buttons_container)
        main_layout.addStretch()

    def _create_stat_card(self, title: str, value: str, color: str) -> dict:
        """創建統計卡片"""
        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {color}40, stop:1 #1a1f2e);
                border: 2px solid {color};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #9ca3af; font-size: 9pt; background: transparent; border: none;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 24pt; background: transparent; border: none;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        return {
            'widget': card,
            'value_label': value_label
        }

    def _create_defect_type_row(self, defect_name: str, color: str) -> dict:
        """創建瑕疵類型行"""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)

        # 類型圖示和名稱
        type_container = QWidget()
        type_layout = QHBoxLayout(type_container)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(8)

        indicator = QLabel("●")
        indicator.setStyleSheet(f"color: {color}; font-size: 14pt;")
        type_layout.addWidget(indicator)

        name_label = QLabel(defect_name)
        name_label.setStyleSheet("color: #e5e7eb; font-size: 10pt; font-weight: bold;")
        name_label.setFixedWidth(80)
        type_layout.addWidget(name_label)

        row_layout.addWidget(type_container)

        # 進度條
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(18)
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #374151;
                border-radius: 8px;
                background-color: #0f1419;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 6px;
            }}
        """)
        row_layout.addWidget(progress_bar, 3)

        # 數量標籤
        count_label = QLabel("0")
        count_label.setStyleSheet(f"color: {color}; font-size: 11pt; font-weight: bold;")
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        count_label.setFixedWidth(60)
        row_layout.addWidget(count_label)

        return {
            'widget': row,
            'progress_bar': progress_bar,
            'count_label': count_label,
            'color': color
        }

    def _on_start_clicked(self):
        """開始檢測按鈕點擊"""
        self.is_detecting = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.sensitivity_spinbox.setEnabled(False)  # 鎖定靈敏度
        self.start_detection_requested.emit()

    def _on_stop_clicked(self):
        """停止檢測按鈕點擊"""
        self.is_detecting = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.sensitivity_spinbox.setEnabled(True)
        self.stop_detection_requested.emit()

    def _on_clear_clicked(self):
        """清除統計按鈕點擊"""
        self.clear_stats_requested.emit()
        # 重置 UI 顯示
        self.update_statistics(0, 0, 0, {})

    def _on_sensitivity_changed(self, value: float):
        """靈敏度改變時的處理"""
        self.sensitivity_changed.emit(value)

    def update_statistics(
        self,
        total_count: int,
        pass_count: int,
        fail_count: int,
        defect_counts: dict
    ):
        """
        更新統計數據

        Args:
            total_count: 總檢測數
            pass_count: 合格數
            fail_count: 不合格數（總數）
            defect_counts: 瑕疵類型計數字典 {'scratch': int, 'dent': int, 'discoloration': int}
        """
        # 更新總數卡片
        self.total_card['value_label'].setText(str(total_count))
        self.pass_card['value_label'].setText(str(pass_count))
        self.fail_card['value_label'].setText(str(fail_count))

        # 計算合格率
        if total_count > 0:
            pass_rate = (pass_count / total_count) * 100
            self.pass_rate_label.setText(f"{pass_rate:.1f}%")

            # 根據合格率調整顏色
            if pass_rate >= 95:
                color = "#10b981"  # 綠色 - 優秀
            elif pass_rate >= 85:
                color = "#3b82f6"  # 藍色 - 良好
            elif pass_rate >= 70:
                color = "#f59e0b"  # 橙色 - 警告
            else:
                color = "#ef4444"  # 紅色 - 不佳

            self.pass_rate_label.setStyleSheet(
                f"color: {color}; font-weight: bold; font-size: 36pt; background: transparent; border: none;"
            )
        else:
            self.pass_rate_label.setText("100.0%")
            self.pass_rate_label.setStyleSheet(
                "color: #10b981; font-weight: bold; font-size: 36pt; background: transparent; border: none;"
            )

        # 更新瑕疵類型統計
        scratch_count = defect_counts.get('scratch', 0)
        dent_count = defect_counts.get('dent', 0)
        discoloration_count = defect_counts.get('discoloration', 0)

        # 計算各類型的百分比（相對於總不合格數）
        if fail_count > 0:
            scratch_percent = (scratch_count / fail_count) * 100
            dent_percent = (dent_count / fail_count) * 100
            discoloration_percent = (discoloration_count / fail_count) * 100
        else:
            scratch_percent = 0
            dent_percent = 0
            discoloration_percent = 0

        # 更新刮痕
        self.scratch_row['count_label'].setText(str(scratch_count))
        self.scratch_row['progress_bar'].setValue(int(scratch_percent))

        # 更新凹陷
        self.dent_row['count_label'].setText(str(dent_count))
        self.dent_row['progress_bar'].setValue(int(dent_percent))

        # 更新變色
        self.discoloration_row['count_label'].setText(str(discoloration_count))
        self.discoloration_row['progress_bar'].setValue(int(discoloration_percent))

    def get_sensitivity(self) -> float:
        """獲取當前靈敏度"""
        return self.sensitivity_spinbox.value()

    def set_sensitivity(self, value: float):
        """設定靈敏度"""
        self.sensitivity_spinbox.setValue(value)
