"""
包裝控制組件（重構版）- 動態方法面板容器
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget
)
from PyQt6.QtCore import pyqtSignal

# 導入零件選擇器和方法選擇器
from basler_pyqt6.ui.widgets.part_selector import PartSelectorWidget
from basler_pyqt6.ui.widgets.method_selector import MethodSelectorWidget

# 導入方法面板
from basler_pyqt6.ui.widgets.method_panels import (
    CountingMethodPanel,
    DefectDetectionMethodPanel
)

from basler_pyqt6.config.settings import get_config


class PackagingControlWidget(QWidget):
    """
    包裝控制組件（重構版）

    使用 QStackedWidget 動態切換不同檢測方法的控制面板
    """

    # ========== 零件和方法選擇信號 ==========
    part_type_changed = pyqtSignal(str)                 # 零件類型變更 (part_id)
    detection_method_changed = pyqtSignal(str, str)     # 檢測方法變更 (part_id, method_id)

    # ========== 計數方法信號（轉發自 CountingMethodPanel）==========
    start_packaging_requested = pyqtSignal()            # 開始包裝請求
    pause_packaging_requested = pyqtSignal()            # 暫停包裝請求
    reset_count_requested = pyqtSignal()                # 重置計數請求
    target_count_changed = pyqtSignal(int)              # 目標數量變更
    threshold_changed = pyqtSignal(str, float)          # 閾值變更 (threshold_name, value)

    # ========== 瑕疵檢測方法信號（轉發自 DefectDetectionMethodPanel）==========
    start_defect_detection_requested = pyqtSignal()     # 開始瑕疵檢測請求
    stop_defect_detection_requested = pyqtSignal()      # 停止瑕疵檢測請求
    clear_defect_stats_requested = pyqtSignal()         # 清除瑕疵統計請求
    defect_sensitivity_changed = pyqtSignal(float)      # 瑕疵靈敏度變更

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_method_id = None
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ========== 區塊 1: 零件檢測種類選擇 ==========
        self.part_selector = PartSelectorWidget()
        self.part_selector.part_type_changed.connect(self._on_part_type_changed)
        main_layout.addWidget(self.part_selector)

        # ========== 區塊 2: 檢測方法選擇 ==========
        self.method_selector = MethodSelectorWidget()
        self.method_selector.method_changed.connect(self._on_method_changed)
        main_layout.addWidget(self.method_selector)

        # ========== 區塊 3: 動態方法控制面板（QStackedWidget）==========
        self.method_panels_stack = QStackedWidget()
        self.method_panels_stack.setStyleSheet("""
            QStackedWidget {
                background-color: transparent;
                border: none;
            }
        """)

        # 創建各方法面板並添加到 Stack
        self.panels = {}

        # 3.1 計數方法面板
        self.counting_panel = CountingMethodPanel()
        self.panels["counting"] = {
            "widget": self.counting_panel,
            "index": self.method_panels_stack.addWidget(self.counting_panel)
        }
        # 連接計數方法面板的信號
        self.counting_panel.start_packaging_requested.connect(
            self.start_packaging_requested.emit
        )
        self.counting_panel.pause_packaging_requested.connect(
            self.pause_packaging_requested.emit
        )
        self.counting_panel.reset_count_requested.connect(
            self.reset_count_requested.emit
        )
        self.counting_panel.target_count_changed.connect(
            self.target_count_changed.emit
        )
        self.counting_panel.threshold_changed.connect(
            self.threshold_changed.emit
        )

        # 3.2 瑕疵檢測方法面板
        self.defect_panel = DefectDetectionMethodPanel()
        self.panels["defect_detection"] = {
            "widget": self.defect_panel,
            "index": self.method_panels_stack.addWidget(self.defect_panel)
        }
        # 連接瑕疵檢測面板的信號
        self.defect_panel.start_detection_requested.connect(
            self.start_defect_detection_requested.emit
        )
        self.defect_panel.stop_detection_requested.connect(
            self.stop_defect_detection_requested.emit
        )
        self.defect_panel.clear_stats_requested.connect(
            self.clear_defect_stats_requested.emit
        )
        self.defect_panel.sensitivity_changed.connect(
            self.defect_sensitivity_changed.emit
        )

        main_layout.addWidget(self.method_panels_stack)

        # 🔧 設定預設顯示計數方法面板（索引 0）
        # 即使信號還未觸發，也確保有面板顯示
        self.method_panels_stack.setCurrentIndex(0)
        self.current_method_id = "counting"

        # 🔧 手動觸發一次零件類型變更，載入檢測方法
        # 因為 PartSelectorWidget 在 __init__ 中已經選擇了預設零件並發射信號
        # 但此時信號連接還沒建立，所以需要手動觸發一次
        current_part_id = self.part_selector.get_current_part_id()
        if current_part_id:
            self._on_part_type_changed(current_part_id)

    def _on_part_type_changed(self, part_id: str):
        """
        零件類型變更處理

        當零件被選擇時：
        1. 載入該零件的可用檢測方法
        2. 發射零件變更信號

        Args:
            part_id: 新選擇的零件類型 ID
        """
        # 獲取配置
        config = get_config()
        profile = config.part_library.get_part_profile(part_id)

        if profile:
            # 載入可用的檢測方法
            available_methods = profile.get("available_methods", [])
            current_method_id = profile.get("current_method_id", "counting")

            self.method_selector.load_methods(part_id, available_methods, current_method_id)

        # 發射信號給主視窗
        self.part_type_changed.emit(part_id)

    def _on_method_changed(self, part_id: str, method_id: str):
        """
        檢測方法變更處理

        當檢測方法被選擇時：
        1. 切換 QStackedWidget 顯示對應的方法面板
        2. 發射方法變更信號

        Args:
            part_id: 零件 ID
            method_id: 檢測方法 ID
        """
        # 切換到對應的方法面板
        if method_id in self.panels:
            panel_index = self.panels[method_id]["index"]
            self.method_panels_stack.setCurrentIndex(panel_index)
            self.current_method_id = method_id

        # 發射信號給主視窗
        self.detection_method_changed.emit(part_id, method_id)

    # ========== 計數方法專用公開介面 ==========

    def get_target_count(self) -> int:
        """獲取目標數量（計數方法專用）"""
        return self.counting_panel.get_target_count()

    def set_target_count(self, count: int):
        """設定目標數量（計數方法專用）"""
        self.counting_panel.set_target_count(count)

    def update_count(self, current: int):
        """
        更新當前計數（計數方法專用）

        Args:
            current: 當前計數
        """
        self.counting_panel.update_count(current)

    def update_vibrator_status(
        self,
        vibrator1_status: dict,
        vibrator2_status: dict
    ):
        """
        更新震動機狀態（計數方法專用）

        Args:
            vibrator1_status: 震動機A狀態字典
            vibrator2_status: 震動機B狀態字典
        """
        self.counting_panel.update_vibrator_status(vibrator1_status, vibrator2_status)

    # ========== 瑕疵檢測方法專用公開介面 ==========

    def get_defect_sensitivity(self) -> float:
        """獲取瑕疵檢測靈敏度"""
        return self.defect_panel.get_sensitivity()

    def set_defect_sensitivity(self, value: float):
        """設定瑕疵檢測靈敏度"""
        self.defect_panel.set_sensitivity(value)

    def update_defect_statistics(
        self,
        total_count: int,
        pass_count: int,
        fail_count: int,
        defect_counts: dict
    ):
        """
        更新瑕疵檢測統計數據

        Args:
            total_count: 總檢測數
            pass_count: 合格數
            fail_count: 不合格數
            defect_counts: 瑕疵類型計數字典 {'scratch': int, 'dent': int, 'discoloration': int}
        """
        self.defect_panel.update_statistics(total_count, pass_count, fail_count, defect_counts)

    # ========== 通用介面 ==========

    def get_current_method_id(self) -> str:
        """獲取當前選擇的方法 ID"""
        return self.current_method_id
