"""
零件類型選擇器組件
用於切換不同零件的檢測方法
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPixmap

from basler_pyqt6.config.settings import get_config
from basler_pyqt6.resources.icons import get_icon, Icons


class PartTypeCard(QFrame):
    """零件類型卡片（單個零件選項）"""

    clicked = pyqtSignal(str)  # 發射零件 ID

    def __init__(self, part_id: str, part_name: str, part_image: str,
                 description: str, parent=None):
        super().__init__(parent)
        self.part_id = part_id
        self.part_name = part_name
        self.part_image = part_image
        self.description = description
        self.is_selected = False

        self.init_ui()

    def init_ui(self):
        """初始化卡片 UI"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(160, 200)  # 固定卡片大小
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # === 零件照片/圖示 ===
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(120, 100)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #0f1419;
                border: 2px solid #374151;
                border-radius: 8px;
            }
        """)

        # 嘗試載入零件圖片
        pixmap = self._load_part_image()
        if pixmap:
            # 縮放圖片以適應標籤
            scaled_pixmap = pixmap.scaled(
                100, 80,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        else:
            # 使用預設圖示
            self.image_label.setText("📦")
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: #0f1419;
                    border: 2px solid #374151;
                    border-radius: 8px;
                    font-size: 48pt;
                    color: #4b5563;
                }
            """)

        layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # === 零件名稱 ===
        name_label = QLabel(self.part_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setStyleSheet("""
            QLabel {
                color: #e5e7eb;
                font-size: 11pt;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(name_label)

        # === 零件描述（縮小字體） ===
        desc_label = QLabel(self.description)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("""
            QLabel {
                color: #9ca3af;
                font-size: 8pt;
                background: transparent;
                border: none;
            }
        """)
        layout.addWidget(desc_label)

        layout.addStretch()

        # 設定初始樣式（未選中）
        self._update_style()

    def _load_part_image(self) -> QPixmap:
        """
        載入零件圖片（支援開發和打包環境）

        Returns:
            QPixmap: 圖片物件，載入失敗返回 None
        """
        if not self.part_image:
            return None

        # 獲取正確的資源路徑（支援開發和打包環境）
        import sys
        if getattr(sys, 'frozen', False):
            # 打包環境：從 _MEIPASS 載入
            base_path = Path(sys._MEIPASS)
            image_path = base_path / self.part_image
        else:
            # 開發環境：從專案根目錄載入
            # 當前文件位於 basler_pyqt6/ui/widgets/part_selector.py
            project_root = Path(__file__).parent.parent.parent.parent
            image_path = project_root / "basler_pyqt6" / self.part_image

        if image_path.exists():
            return QPixmap(str(image_path))
        else:
            # 圖片不存在時優雅降級（不顯示圖片）
            return None

    def mousePressEvent(self, event):
        """滑鼠點擊事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.part_id)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool):
        """設定選中狀態"""
        self.is_selected = selected
        self._update_style()

    def _update_style(self):
        """更新卡片樣式（根據選中狀態）"""
        if self.is_selected:
            # 選中狀態 - 高亮邊框
            self.setStyleSheet("""
                PartTypeCard {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1e3a5f, stop:1 #0d2544);
                    border: 3px solid #00d4ff;
                    border-radius: 12px;
                }
                PartTypeCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2a4a6f, stop:1 #1a3554);
                }
            """)
        else:
            # 未選中狀態 - 普通邊框
            self.setStyleSheet("""
                PartTypeCard {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #1f2937, stop:1 #111827);
                    border: 2px solid #374151;
                    border-radius: 12px;
                }
                PartTypeCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #2d3748, stop:1 #1a202c);
                    border: 2px solid #4b5563;
                }
            """)


class PartSelectorWidget(QWidget):
    """零件類型選擇器（包含多個零件卡片）"""

    # 信號：當選擇零件類型時發射 (part_id)
    part_type_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = {}  # 存儲所有卡片 {part_id: PartTypeCard}
        self.current_part_id = None

        self.init_ui()
        self.load_part_types()

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

        title_label = QLabel("零件檢測種類選擇")
        title_label.setStyleSheet("""
            QLabel {
                color: #00d4ff;
                font-size: 12pt;
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
                font-size: 10pt;
                font-weight: bold;
                background-color: #1e3a2f;
                border: 1px solid #10b981;
                border-radius: 6px;
                padding: 5px 15px;
            }
        """)
        title_layout.addWidget(self.selected_indicator)
        title_layout.addStretch()

        main_layout.addWidget(title_container)

        # === 卡片滾動區域 ===
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFixedHeight(240)  # 固定高度適應卡片
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 2px solid #374151;
                border-radius: 10px;
                background-color: #0f1419;
            }
            QScrollBar:horizontal {
                height: 10px;
                background-color: #1f2937;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4b5563;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #6b7280;
            }
        """)

        # 卡片容器（橫向佈局）
        self.cards_container = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(15)
        self.cards_layout.setContentsMargins(15, 15, 15, 15)
        self.cards_layout.addStretch()  # 左側彈簧

        scroll_area.setWidget(self.cards_container)
        main_layout.addWidget(scroll_area)

    def load_part_types(self):
        """從配置載入所有零件類型"""
        config = get_config()
        part_library = config.part_library

        # 清空現有卡片
        self.cards.clear()

        # 創建卡片（使用新的 part_profiles 結構）
        for profile in part_library.part_profiles:
            card = PartTypeCard(
                part_id=profile["part_id"],
                part_name=profile["part_name"],
                part_image=profile.get("part_image", ""),
                description=profile.get("description", "")
            )
            card.clicked.connect(self._on_card_clicked)

            # 插入到最後一個 stretch 之前
            self.cards_layout.insertWidget(
                self.cards_layout.count() - 1,
                card
            )
            self.cards[profile["part_id"]] = card

        # 設定預設選擇（配置中的當前零件）
        default_part_id = part_library.current_part_id
        if default_part_id in self.cards:
            self.select_part_type(default_part_id)
            # 🔧 自動觸發信號，讓檢測方法選擇器同步載入
            self.part_type_changed.emit(default_part_id)

    def _on_card_clicked(self, part_id: str):
        """卡片點擊處理"""
        self.select_part_type(part_id)
        self.part_type_changed.emit(part_id)

    def select_part_type(self, part_id: str):
        """選擇零件類型"""
        # 取消所有卡片的選中狀態
        for card in self.cards.values():
            card.set_selected(False)

        # 設定新的選中卡片
        if part_id in self.cards:
            self.cards[part_id].set_selected(True)
            self.current_part_id = part_id

            # 更新指示器
            part_name = self.cards[part_id].part_name
            self.selected_indicator.setText(f"當前: {part_name}")

    def get_current_part_id(self) -> str:
        """獲取當前選擇的零件 ID"""
        return self.current_part_id
