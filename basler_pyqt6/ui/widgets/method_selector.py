"""
檢測方法選擇器組件
用於選擇特定零件的不同檢測意圖（計數、瑕疵檢測等）
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QButtonGroup, QRadioButton, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from basler_pyqt6.resources.icons import get_icon, get_pixmap, Icons


class MethodCard(QFrame):
    """檢測方法卡片（單選）"""

    clicked = pyqtSignal(str)  # 發射 method_id

    def __init__(self, method_id: str, method_name: str,
                 method_description: str, icon_name: str = Icons.CHART, parent=None):
        super().__init__(parent)
        self.method_id = method_id
        self.method_name = method_name
        self.method_description = method_description
        self.icon_name = icon_name  # SVG 圖示名稱
        self.is_selected = False

        self.init_ui()

    def init_ui(self):
        """初始化卡片 UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedHeight(100)
        self.setMinimumWidth(200)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # === 圖示 ===
        self.icon_label = QLabel()
        self.icon_label.setPixmap(get_pixmap(self.icon_name, 48))
        self.icon_label.setStyleSheet("""
            QLabel {
                background: transparent;
                border: none;
            }
        """)
        self.icon_label.setFixedSize(60, 60)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        # === 文字區域 ===
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setSpacing(5)
        text_layout.setContentsMargins(0, 0, 0, 0)

        # 方法名稱
        name_label = QLabel(self.method_name)
        name_label.setStyleSheet("""
            QLabel {
                color: #e5e7eb;
                font-size: 12pt;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        text_layout.addWidget(name_label)

        # 方法描述
        desc_label = QLabel(self.method_description)
        desc_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 9pt;
                background: transparent;
                border: none;
            }
        """)
        desc_label.setWordWrap(True)
        text_layout.addWidget(desc_label)

        text_layout.addStretch()
        layout.addWidget(text_container, 1)

        # 設定初始樣式
        self._update_style()

    def mousePressEvent(self, event):
        """滑鼠點擊事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.method_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        """設定選中狀態"""
        self.is_selected = selected
        self._update_style()

    def _update_style(self):
        """更新卡片樣式"""
        if self.is_selected:
            # 選中狀態 - 藍色高亮
            self.setStyleSheet("""
                MethodCard {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1e3a5f, stop:1 #0d2544);
                    border: 3px solid #00d4ff;
                    border-radius: 10px;
                }
                MethodCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2a4a6f, stop:1 #1a3554);
                }
            """)
        else:
            # 未選中狀態
            self.setStyleSheet("""
                MethodCard {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1f2937, stop:1 #111827);
                    border: 2px solid #374151;
                    border-radius: 10px;
                }
                MethodCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2d3748, stop:1 #1a202c);
                    border: 2px solid #4b5563;
                }
            """)


class MethodSelectorWidget(QWidget):
    """檢測方法選擇器（顯示某零件的所有可用方法）"""

    # 信號：方法變更 (part_id, method_id)
    method_changed = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_part_id = None
        self.current_method_id = None
        self.method_cards = {}  # {method_id: MethodCard}

        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # === 標題區 ===
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(15, 10, 15, 5)
        title_layout.setSpacing(10)

        title_label = QLabel("🎯 檢測方法選擇")
        title_label.setStyleSheet("""
            QLabel {
                color: #00d4ff;
                font-size: 11pt;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        title_layout.addWidget(title_label)

        # 當前選擇指示器
        self.selected_indicator = QLabel("當前: 未選擇")
        self.selected_indicator.setStyleSheet("""
            QLabel {
                color: #10b981;
                font-size: 9pt;
                font-weight: bold;
                background-color: #1e3a2f;
                border: 1px solid #10b981;
                border-radius: 6px;
                padding: 4px 12px;
            }
        """)
        title_layout.addWidget(self.selected_indicator)
        title_layout.addStretch()

        main_layout.addWidget(title_container)

        # === 方法卡片容器 ===
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(10)
        self.cards_layout.setContentsMargins(15, 10, 15, 10)

        # 包裝容器（帶邊框）
        cards_wrapper = QFrame()
        cards_wrapper.setStyleSheet("""
            QFrame {
                border: 2px solid #374151;
                border-radius: 10px;
                background-color: #0f1419;
            }
        """)
        wrapper_layout = QVBoxLayout(cards_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self.cards_container)

        main_layout.addWidget(cards_wrapper)

    def load_methods(self, part_id: str, available_methods: list, current_method_id: str = None):
        """
        載入某零件的可用檢測方法

        Args:
            part_id: 零件 ID
            available_methods: 可用方法列表
            current_method_id: 當前選擇的方法 ID（可選）
        """
        self.current_part_id = part_id

        # 清空現有卡片
        self.method_cards.clear()
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 方法圖示映射（使用專案 SVG 圖示）
        method_icons = {
            "counting": Icons.CHART,
            "defect_detection": Icons.SEARCH,
            "size_measurement": Icons.RULER,
            "classification": Icons.CHECKMARK
        }

        # 創建方法卡片
        for method_data in available_methods:
            method_id = method_data.get("method_id", "unknown")
            method_name = method_data.get("method_name", "Unknown")
            method_desc = method_data.get("method_description", "")
            icon_name = method_icons.get(method_id, Icons.CHART)

            card = MethodCard(method_id, method_name, method_desc, icon_name)
            card.clicked.connect(self._on_card_clicked)

            self.cards_layout.addWidget(card)
            self.method_cards[method_id] = card

        self.cards_layout.addStretch()

        # 設定預設選擇
        if current_method_id and current_method_id in self.method_cards:
            self.select_method(current_method_id)
            # 🔧 自動觸發信號，讓主視窗同步更新參數
            self.method_changed.emit(self.current_part_id, current_method_id)
        elif len(self.method_cards) > 0:
            # 自動選擇第一個方法
            first_method_id = list(self.method_cards.keys())[0]
            self.select_method(first_method_id)
            # 🔧 自動觸發信號
            self.method_changed.emit(self.current_part_id, first_method_id)

    def _on_card_clicked(self, method_id: str):
        """卡片點擊處理"""
        self.select_method(method_id)
        self.method_changed.emit(self.current_part_id, method_id)

    def select_method(self, method_id: str):
        """選擇檢測方法"""
        # 取消所有卡片的選中狀態
        for card in self.method_cards.values():
            card.set_selected(False)

        # 設定新的選中卡片
        if method_id in self.method_cards:
            self.method_cards[method_id].set_selected(True)
            self.current_method_id = method_id

            # 更新指示器
            method_name = self.method_cards[method_id].method_name
            self.selected_indicator.setText(f"當前: {method_name}")

    def get_current_method_id(self) -> str:
        """獲取當前選擇的方法 ID"""
        return self.current_method_id

    def clear(self):
        """清空方法列表"""
        self.method_cards.clear()
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.current_part_id = None
        self.current_method_id = None
        self.selected_indicator.setText("當前: 未選擇")
