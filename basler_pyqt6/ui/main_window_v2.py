"""
主窗口 V2 - 完整功能版本
支持相機/視頻雙模式 + 檢測 + 錄影
"""

import logging
import cv2
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStatusBar, QLabel, QFileDialog, QMessageBox, QScrollArea, QTabWidget, QPushButton
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from basler_pyqt6.ui.widgets.camera_control import CameraControlWidget
from basler_pyqt6.ui.widgets.video_display import VideoDisplayWidget
# DetectionControlWidget 已移除，功能整合到 PackagingControlWidget
from basler_pyqt6.ui.widgets.recording_control import RecordingControlWidget
from basler_pyqt6.ui.widgets.system_monitor import SystemMonitorWidget
from basler_pyqt6.ui.widgets.debug_panel import DebugPanelWidget
from basler_pyqt6.ui.dialogs.update_dialog import UpdateDialog

# 導入核心模塊
from basler_pyqt6.core.source_manager import SourceManager, SourceType
from basler_pyqt6.core.detection import DetectionController
from basler_pyqt6.core.video_recorder import VideoRecorder
from basler_pyqt6.core.updater import AutoUpdater
from basler_pyqt6.version import DEBUG_MODE

# 導入圖示管理器
from basler_pyqt6.resources.icons import get_icon, Icons

logger = logging.getLogger(__name__)


class MainWindowV2(QMainWindow):
    """主窗口 V2 - 完整版"""

    def __init__(self):
        super().__init__()
        self.source_manager = SourceManager()
        self.detection_controller = DetectionController()
        self.video_recorder = VideoRecorder()

        # UI 狀態變量
        self.ui_scale_factor = 1.0  # UI 縮放因子

        # 調試模式變量
        if DEBUG_MODE:
            self.debug_detection_count_history = []  # 檢測數量歷史
            self.debug_frame_times = []  # 幀處理時間歷史

            # 性能優化變量
            self.perf_image_scale = 1  # 圖像縮放比例（預設100%）
            self.perf_skip_frames = 0  # 跳幀數（預設不跳幀）
            self.perf_frame_counter = 0  # 幀計數器（用於跳幀）

        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("🏭 Basler 工業視覺系統 - 專業版")
        self.setMinimumSize(1400, 800)  # 調整最小尺寸
        self.resize(1600, 900)  # 設置默認尺寸

        # 創建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主佈局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 創建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # ===== 左側/中間：檢測結果主畫面（大） =====
        self.video_display = VideoDisplayWidget()
        self.video_display.setMinimumSize(800, 600)

        # ===== 右側控制面板（分頁式設計） =====
        # 創建分頁容器
        tab_widget = QTabWidget()
        tab_widget.setMinimumWidth(400)

        # ========== Tab 1: 相機設定 ==========
        camera_settings_tab = QWidget()
        camera_settings_layout = QVBoxLayout(camera_settings_tab)
        camera_settings_layout.setSpacing(15)
        camera_settings_layout.setContentsMargins(10, 10, 10, 10)

        # 相機控制組件
        self.camera_control = CameraControlWidget()
        camera_settings_layout.addWidget(self.camera_control)
        camera_settings_layout.addStretch()

        # ========== Tab 2: 檢測監控 ==========
        monitoring_tab = QWidget()
        monitoring_layout = QVBoxLayout(monitoring_tab)
        monitoring_layout.setSpacing(15)
        monitoring_layout.setContentsMargins(15, 15, 15, 15)

        # === 原始畫面預覽（上方，放大顯示） ===
        preview_container = QWidget()
        preview_container.setStyleSheet("""
            QWidget {
                background-color: #0a0e27;
                border: 2px solid #1f3a5f;
                border-radius: 10px;
            }
        """)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(10, 10, 10, 10)
        preview_layout.setSpacing(8)

        preview_label = QLabel("📹 原始畫面")
        preview_label.setStyleSheet("""
            font-weight: bold;
            color: #00d4ff;
            font-size: 12pt;
            background-color: transparent;
            border: none;
        """)
        preview_layout.addWidget(preview_label)

        self.camera_preview = VideoDisplayWidget()
        self.camera_preview.setFixedHeight(300)  # 放大顯示
        self.camera_preview.setMinimumWidth(400)
        self.camera_preview.setStyleSheet("""
            QWidget {
                border: 1px solid #00d4ff;
                border-radius: 6px;
                background-color: #000000;
            }
        """)
        preview_layout.addWidget(self.camera_preview, 0, Qt.AlignmentFlag.AlignCenter)

        monitoring_layout.addWidget(preview_container)

        # === 包裝控制中心（下方） ===
        from basler_pyqt6.ui.widgets.packaging_control import PackagingControlWidget
        self.packaging_control = PackagingControlWidget()
        monitoring_layout.addWidget(self.packaging_control)

        monitoring_layout.addStretch()

        # === 錄影控制和系統監控已移到狀態欄 ===
        # 保留變數引用用於更新
        self.recording_control = RecordingControlWidget()
        self.system_monitor = SystemMonitorWidget()

        # ========== Tab 3: 調試工具（僅開發模式） ==========
        if DEBUG_MODE:
            self.debug_panel = DebugPanelWidget()
            # 稍後連接調試面板信號
            logger.info("🛠️ 開發模式已啟用 - 調試工具可用")

        # 添加分頁到 TabWidget
        tab_widget.addTab(camera_settings_tab, "⚙️ 設定")
        tab_widget.addTab(monitoring_tab, "📊 檢測監控")

        if DEBUG_MODE:
            tab_widget.addTab(self.debug_panel, "🛠️ 調試工具")

        # 預設顯示「檢測監控」頁面
        tab_widget.setCurrentIndex(1)

        # 包裝在滾動區域中
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(tab_widget)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 添加到分割器
        splitter.addWidget(self.video_display)
        splitter.addWidget(scroll_area)  # 使用滾動區域而非直接使用面板

        # 設置分割器比例：主畫面(大) : 右側控制面板
        splitter.setStretchFactor(0, 7)  # 主畫面占 70%
        splitter.setStretchFactor(1, 3)  # 右側面板占 30%

        # 設置分割器最小尺寸
        splitter.setCollapsible(0, False)  # 主畫面不可摺疊
        splitter.setCollapsible(1, False)  # 右側面板不可摺疊

        main_layout.addWidget(splitter)

        # 創建菜單欄
        self.create_menu_bar()

        # 創建狀態欄
        self.create_status_bar()

        # 連接信號
        self.connect_signals()

        # 定時器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(33)  # 30 FPS 更新

        # 應用樣式
        self.apply_styles()

        logger.info("✅ UI 初始化完成")

    def create_menu_bar(self):
        """創建跨平台工業級菜單欄"""
        menubar = self.menuBar()

        # 設置菜單欄樣式（跨平台一致性）
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #0a0e27;
                color: #e0e6f1;
                border-bottom: 2px solid #1f3a5f;
                padding: 4px;
                font-size: 11pt;
            }
            QMenuBar::item {
                padding: 8px 16px;
                background-color: transparent;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #1e5a8e;
            }
            QMenuBar::item:pressed {
                background-color: #0d4a7a;
            }
        """)

        # ========== 1. 檔案菜單 ==========
        file_menu = menubar.addMenu("檔案(&F)")

        # 開啟測試影片
        load_video_action = QAction("開啟測試影片...", self)
        load_video_action.setShortcut("Ctrl+O")
        load_video_action.setStatusTip("載入 MP4/AVI 影片進行測試")
        load_video_action.triggered.connect(self.load_video_file)
        file_menu.addAction(load_video_action)

        # 最近使用的檔案
        recent_menu = file_menu.addMenu("最近使用")
        recent_menu.setEnabled(False)  # 未來功能

        file_menu.addSeparator()

        # 匯出功能
        export_menu = file_menu.addMenu("匯出")

        export_config_action = QAction("匯出配置...", self)
        export_config_action.setStatusTip("將當前檢測參數匯出為 JSON")
        export_config_action.triggered.connect(self.on_export_config)
        export_menu.addAction(export_config_action)

        export_log_action = QAction("匯出運行日誌...", self)
        export_log_action.setStatusTip("匯出系統運行日誌")
        export_log_action.setEnabled(False)  # 未來功能
        export_menu.addAction(export_log_action)

        file_menu.addSeparator()

        # 退出（macOS 會自動處理）
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("關閉應用程式")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ========== 2. 編輯菜單 ==========
        edit_menu = menubar.addMenu("編輯(&E)")

        # 設定選項
        preferences_action = QAction("偏好設定...", self)
        preferences_action.setShortcut("Ctrl+,")
        preferences_action.setStatusTip("開啟系統設定")
        preferences_action.triggered.connect(self.show_preferences)
        edit_menu.addAction(preferences_action)

        edit_menu.addSeparator()

        # 重置配置
        reset_config_action = QAction("重置所有設定", self)
        reset_config_action.setStatusTip("將所有參數重置為預設值")
        reset_config_action.triggered.connect(self.on_reset_config)
        edit_menu.addAction(reset_config_action)

        # ========== 3. 視圖菜單 ==========
        view_menu = menubar.addMenu("視圖(&V)")

        # 全螢幕模式
        fullscreen_action = QAction("全螢幕模式", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.setCheckable(True)
        fullscreen_action.setStatusTip("切換全螢幕顯示")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        self.fullscreen_action = fullscreen_action  # 保存引用

        view_menu.addSeparator()

        # 介面縮放
        zoom_menu = view_menu.addMenu("介面縮放")

        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(lambda: self.adjust_ui_scale(1.1))
        zoom_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("縮小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(lambda: self.adjust_ui_scale(0.9))
        zoom_menu.addAction(zoom_out_action)

        zoom_reset_action = QAction("重置縮放", self)
        zoom_reset_action.setShortcut("Ctrl+0")
        zoom_reset_action.triggered.connect(lambda: self.adjust_ui_scale(1.0, reset=True))
        zoom_menu.addAction(zoom_reset_action)

        # ========== 4. 相機菜單 ==========
        camera_menu = menubar.addMenu("相機(&C)")

        # 偵測相機
        detect_camera_action = QAction("偵測相機", self)
        detect_camera_action.setShortcut("Ctrl+D")
        detect_camera_action.setStatusTip("搜尋可用的 Basler 相機")
        detect_camera_action.triggered.connect(self.on_detect_cameras)
        camera_menu.addAction(detect_camera_action)

        camera_menu.addSeparator()

        # 相機模式切換
        camera_mode_action = QAction("切換到相機模式", self)
        camera_mode_action.setShortcut("Ctrl+Shift+C")
        camera_mode_action.triggered.connect(self.switch_to_camera_mode)
        camera_menu.addAction(camera_mode_action)

        video_mode_action = QAction("切換到影片模式", self)
        video_mode_action.setShortcut("Ctrl+Shift+V")
        video_mode_action.triggered.connect(self.load_video_file)
        camera_menu.addAction(video_mode_action)

        # ========== 5. 工具菜單 ==========
        tools_menu = menubar.addMenu("工具(&T)")

        # 性能測試
        benchmark_action = QAction("性能基準測試", self)
        benchmark_action.setStatusTip("測試系統處理速度")
        benchmark_action.setEnabled(False)  # 未來功能
        tools_menu.addAction(benchmark_action)

        tools_menu.addSeparator()

        # 清理快取
        clear_cache_action = QAction("清理快取", self)
        clear_cache_action.setStatusTip("清除暫存檔案和快取")
        clear_cache_action.triggered.connect(self.clear_cache)
        tools_menu.addAction(clear_cache_action)

        # ========== 6. 幫助菜單 ==========
        help_menu = menubar.addMenu("幫助(&H)")

        # 檢查更新（重要功能）
        check_update_action = QAction("檢查更新...", self)
        check_update_action.setShortcut("Ctrl+U")
        check_update_action.setStatusTip("檢查是否有新版本可用")
        check_update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_update_action)

        help_menu.addSeparator()

        # 使用說明
        documentation_action = QAction("使用說明", self)
        documentation_action.setShortcut("F1")
        documentation_action.setStatusTip("開啟線上說明文件")
        documentation_action.triggered.connect(self.show_documentation)
        help_menu.addAction(documentation_action)

        # 鍵盤快捷鍵
        shortcuts_action = QAction("鍵盤快捷鍵", self)
        shortcuts_action.setStatusTip("顯示所有可用的快捷鍵")
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        # 回報問題
        report_issue_action = QAction("回報問題", self)
        report_issue_action.setStatusTip("在 GitHub 上回報 Bug")
        report_issue_action.triggered.connect(self.report_issue)
        help_menu.addAction(report_issue_action)

        help_menu.addSeparator()

        # 關於
        about_action = QAction("關於 Basler 視覺系統(&A)", self)
        about_action.setStatusTip("顯示版本資訊")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    """ 底部狀態欄  """
    def create_status_bar(self):
        """創建狀態欄 - 工業級狀態指示"""
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #0a0e27;
                color: #00d4ff;
                border-top: 2px solid #1f3a5f;
                font-size: 11pt;
                min-height: 30px;
            }
            QStatusBar QLabel {
                background-color: transparent;
                color: #e0e6f1;
                padding: 5px 15px;
                font-weight: 500;
            }
        """)
        self.setStatusBar(self.status_bar)

        # 主要狀態指示器（左側）
        self.status_label = QLabel("● 系統就緒")
        self.status_label.setStyleSheet("""
            background-color: transparent;
            color: #10b981;
            padding: 5px 15px;
            font-weight: bold;
            font-size: 11pt;
        """)
        self.status_bar.addWidget(self.status_label)

        # 添加分隔符
        separator1 = QLabel("│")
        separator1.setStyleSheet("color: #4a5568; padding: 0px 5px;")
        self.status_bar.addWidget(separator1)

        # 視頻源指示器
        self.source_label = QLabel("源: 無")
        self.source_label.setStyleSheet("""
            background-color: transparent;
            color: #00d4ff;
            padding: 5px 10px;
            font-size: 10pt;
        """)
        self.status_bar.addPermanentWidget(self.source_label)

        # FPS 指示器（關鍵指標，使用醒目顏色）
        self.fps_label = QLabel("FPS: 0")
        self.fps_label.setStyleSheet("""
            background-color: #1e3a5f;
            color: #00d4ff;
            padding: 5px 15px;
            font-weight: bold;
            font-size: 10pt;
            border-radius: 4px;
            margin: 0px 5px;
        """)
        self.status_bar.addPermanentWidget(self.fps_label)

        # 檢測計數指示器
        self.detection_label = QLabel("檢測: 0")
        self.detection_label.setStyleSheet("""
            background-color: #1e5a3a;
            color: #10b981;
            padding: 5px 15px;
            font-weight: bold;
            font-size: 10pt;
            border-radius: 4px;
            margin: 0px 5px;
        """)
        self.status_bar.addPermanentWidget(self.detection_label)

        # 錄影狀態指示器（精簡版）
        self.recording_status_label = QLabel("⏺️ 錄影: 停止")
        self.recording_status_label.setStyleSheet("""
            background-color: #4b5563;
            color: #9ca3af;
            padding: 5px 15px;
            font-size: 10pt;
            border-radius: 4px;
            margin: 0px 5px;
        """)
        self.recording_status_label.setVisible(False)  # 預設隱藏，錄影時顯示
        self.status_bar.addPermanentWidget(self.recording_status_label)

        # 系統資源監控（精簡版）
        self.system_status_label = QLabel("💻 CPU: 0% | RAM: 0%")
        self.system_status_label.setStyleSheet("""
            background-color: #1e293b;
            color: #cbd5e1;
            padding: 5px 15px;
            font-size: 9pt;
            border-radius: 4px;
            margin: 0px 5px;
        """)
        self.status_bar.addPermanentWidget(self.system_status_label)

    def connect_signals(self):
        """連接信號"""
        # 相機控制
        self.camera_control.detect_clicked.connect(self.on_detect_cameras)
        self.camera_control.connect_clicked.connect(self.on_connect_camera)
        self.camera_control.disconnect_clicked.connect(self.on_disconnect_camera)
        self.camera_control.start_clicked.connect(self.on_start_source)
        self.camera_control.stop_clicked.connect(self.on_stop_source)
        self.camera_control.exposure_changed.connect(self.on_exposure_changed)

        # 檢測控制信號已移除（功能已整合到包裝控制）

        # 定量包裝控制（計數方法）
        self.packaging_control.start_packaging_requested.connect(self.on_start_packaging)
        self.packaging_control.pause_packaging_requested.connect(self.on_pause_packaging)
        self.packaging_control.reset_count_requested.connect(self.on_reset_packaging)
        self.packaging_control.target_count_changed.connect(self.on_target_count_changed)
        self.packaging_control.threshold_changed.connect(self.on_threshold_changed)

        # 瑕疵檢測控制（瑕疵檢測方法）
        self.packaging_control.start_defect_detection_requested.connect(self.on_start_defect_detection)
        self.packaging_control.stop_defect_detection_requested.connect(self.on_stop_defect_detection)
        self.packaging_control.clear_defect_stats_requested.connect(self.on_clear_defect_stats)
        self.packaging_control.defect_sensitivity_changed.connect(self.on_defect_sensitivity_changed)

        # 零件類型和檢測方法變更
        self.packaging_control.part_type_changed.connect(self.on_part_type_changed)
        self.packaging_control.detection_method_changed.connect(self.on_detection_method_changed)

        # 錄影控制
        self.recording_control.start_recording.connect(self.on_start_recording)
        self.recording_control.stop_recording.connect(self.on_stop_recording)

        # 調試工具（僅開發模式）
        if DEBUG_MODE:
            self.debug_panel.load_test_video.connect(self.on_debug_load_video)
            self.debug_panel.param_changed.connect(self.on_debug_param_changed)
            self.debug_panel.reset_params.connect(self.on_debug_reset_params)
            self.debug_panel.save_config.connect(self.on_debug_save_config)
            self.debug_panel.load_config.connect(self.on_debug_load_config)
            self.debug_panel.reset_total_count.connect(self.on_debug_reset_total_count)
            # 播放控制
            self.debug_panel.play_video.connect(self.on_debug_play)
            self.debug_panel.pause_video.connect(self.on_debug_pause)
            self.debug_panel.prev_frame.connect(self.on_debug_prev_frame)
            self.debug_panel.next_frame.connect(self.on_debug_next_frame)
            self.debug_panel.jump_to_frame.connect(self.on_debug_jump_frame)
            self.debug_panel.screenshot.connect(self.on_debug_screenshot)

    def load_video_file(self):
        """加載視頻文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇視頻文件",
            str(Path.home()),
            "視頻文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*.*)"
        )

        if file_path:
            if self.source_manager.use_video(file_path):
                self.source_label.setText(f"源: 視頻 - {Path(file_path).name}")
                self.status_label.setText(f"視頻已加載: {Path(file_path).name}")
                self.camera_control.set_video_mode(True)
            else:
                QMessageBox.warning(self, "錯誤", "無法加載視頻文件")

    def switch_to_camera_mode(self):
        """切換到相機模式"""
        self.source_manager.use_camera()
        self.source_label.setText("源: 相機")
        self.camera_control.set_video_mode(False)
        self.status_label.setText("已切換到相機模式")

    def on_detect_cameras(self):
        """檢測相機"""
        camera = self.source_manager.use_camera()
        cameras = camera.detect_cameras()
        self.camera_control.update_camera_list(cameras)
        self.status_label.setText(f"檢測到 {len(cameras)} 台相機")

    def on_connect_camera(self, camera_index):
        """連接相機"""
        if self.source_manager.source_type == SourceType.CAMERA:
            success = self.source_manager.camera_controller.connect(camera_index)
            if success:
                self.status_label.setText("相機連接成功")
            else:
                self.status_label.setText("相機連接失敗")

    def on_disconnect_camera(self):
        """斷開相機"""
        if self.source_manager.source_type == SourceType.CAMERA:
            self.source_manager.camera_controller.disconnect()
            self.status_label.setText("相機已斷開")

    def on_start_source(self):
        """開始源（相機抓取或視頻播放）"""
        if self.source_manager.source_type == SourceType.CAMERA:
            self.source_manager.camera_controller.start_grabbing()
            self.status_label.setText("開始抓取圖像")
            self.recording_control.set_enabled(True)  # 啟用錄製按鈕
        elif self.source_manager.source_type == SourceType.VIDEO:
            self.source_manager.video_player.start_playing(loop=False)
            self.status_label.setText("開始播放視頻")
            self.recording_control.set_enabled(True)  # 啟用錄製按鈕

    def on_stop_source(self):
        """停止源"""
        # 如果正在錄製，先停止錄製
        if self.video_recorder.is_recording:
            self.on_stop_recording()

        if self.source_manager.source_type == SourceType.CAMERA:
            self.source_manager.camera_controller.stop_grabbing()
            self.status_label.setText("停止抓取圖像")
            self.recording_control.set_enabled(False)  # 禁用錄製按鈕
        elif self.source_manager.source_type == SourceType.VIDEO:
            self.source_manager.video_player.stop_playing()
            self.status_label.setText("停止播放視頻")
            self.recording_control.set_enabled(False)  # 禁用錄製按鈕

    def on_exposure_changed(self, value):
        """曝光改變"""
        if self.source_manager.source_type == SourceType.CAMERA:
            self.source_manager.camera_controller.set_exposure(value)

    def on_detection_enable_changed(self, enabled):
        """檢測啟用改變"""
        if enabled:
            self.detection_controller.enable()
            self.status_label.setText("小零件檢測已啟用")
        else:
            self.detection_controller.disable()
            self.status_label.setText("檢測已禁用")

    def on_roi_enabled_changed(self, enabled):
        """ROI 區域檢測啟用改變"""
        self.detection_controller.set_roi_enabled(enabled)
        self.status_label.setText(f"ROI 檢測: {'啟用' if enabled else '禁用'}")

    def on_high_speed_changed(self, enabled):
        """超高速模式改變"""
        self.detection_controller.set_ultra_high_speed_mode(enabled)
        self.detection_control.set_high_speed_mode(enabled)
        self.status_label.setText(f"超高速模式: {'啟用' if enabled else '禁用'}")

    def on_detection_reset(self):
        """重置檢測計數器"""
        self.detection_controller.reset()
        self.status_label.setText("檢測計數器已重置")
        logger.info("✅ 檢測計數器已重置")

    # ==================== 定量包裝控制處理 ====================

    def on_start_packaging(self):
        """開始包裝 - 一鍵啟動檢測和震動機"""
        logger.info("📦 開始定量包裝")

        # 1. 啟用檢測（如果尚未啟用）
        if not self.detection_controller.enabled:
            self.detection_controller.enable()
            logger.info("✅ 自動啟用檢測")

        # 2. 啟用包裝模式（自動控制震動機）
        self.detection_controller.enable_packaging_mode(True)

        # 3. 更新狀態
        target = self.packaging_control.get_target_count()
        self.status_label.setText(f"📦 包裝中... (目標: {target}顆)")
        logger.info(f"🎯 目標數量: {target}顆")

    def on_pause_packaging(self):
        """暫停包裝"""
        logger.info("⏸ 暫停包裝")
        self.detection_controller.enable_packaging_mode(False)
        self.status_label.setText("包裝已暫停")

    def on_reset_packaging(self):
        """重置包裝計數"""
        logger.info("🔄 重置包裝計數")
        self.detection_controller.reset_packaging()
        self.packaging_control.update_count(0)
        self.status_label.setText("包裝計數已重置")

    def on_target_count_changed(self, count: int):
        """目標數量變更"""
        logger.info(f"🎯 目標數量變更: {count}顆")
        self.detection_controller.set_target_count(count)

    def on_threshold_changed(self, threshold_name: str, value: float):
        """速度閾值變更"""
        logger.info(f"⚙️  閾值變更: {threshold_name} = {value:.2%}")
        # 更新 DetectionController 的閾值
        if threshold_name == "speed_medium":
            self.detection_controller.speed_medium_threshold = value
        elif threshold_name == "speed_slow":
            self.detection_controller.speed_slow_threshold = value
        elif threshold_name == "speed_creep":
            self.detection_controller.speed_slow_threshold = value

    # ==================== 瑕疵檢測控制處理 ====================

    def on_start_defect_detection(self):
        """開始瑕疵檢測"""
        logger.info("🔍 開始瑕疵檢測")

        # 啟用檢測（如果尚未啟用）
        if not self.detection_controller.enabled:
            self.detection_controller.enable()
            logger.info("✅ 自動啟用檢測")

        self.status_label.setText("🔍 瑕疵檢測運行中...")

    def on_stop_defect_detection(self):
        """停止瑕疵檢測"""
        logger.info("⏹ 停止瑕疵檢測")
        self.detection_controller.disable()
        self.status_label.setText("瑕疵檢測已停止")

    def on_clear_defect_stats(self):
        """清除瑕疵統計數據"""
        logger.info("🔄 清除瑕疵統計")
        # TODO: 重置瑕疵檢測相關的統計數據
        self.status_label.setText("瑕疵統計已清除")

    def on_defect_sensitivity_changed(self, value: float):
        """瑕疵檢測靈敏度變更"""
        logger.info(f"⚙️  瑕疵檢測靈敏度變更: {value:.2f}")
        # TODO: 更新瑕疵檢測參數
        # self.detection_controller.set_defect_sensitivity(value)

    # ==================== 零件類型和方法變更處理 ====================

    def on_part_type_changed(self, part_id: str):
        """
        零件類型變更處理

        注意：新架構下，零件切換只是第一步
        還需要等待用戶選擇檢測方法後才會真正切換參數

        Args:
            part_id: 選擇的零件類型 ID
        """
        from config.settings import get_config

        logger.info(f"🔧 零件類型切換: {part_id}")

        # 獲取配置
        config = get_config()
        profile = config.part_library.get_part_profile(part_id)

        if not profile:
            logger.error(f"❌ 找不到零件類型: {part_id}")
            return

        # 更新配置庫的當前選擇
        config.part_library.current_part_id = part_id

        # 顯示狀態訊息
        part_name = profile["part_name"]
        self.status_label.setText(f"✅ 已選擇零件: [{part_name}]，請選擇檢測方法")
        logger.info(f"✅ 已選擇零件: [{part_name}]")
        logger.info(f"   可用方法: {len(profile.get('available_methods', []))} 種")

    def on_detection_method_changed(self, part_id: str, method_id: str):
        """
        檢測方法變更處理 - 根據方法類型切換檢測參數

        Args:
            part_id: 零件 ID
            method_id: 檢測方法 ID
        """
        from config.settings import get_config

        logger.info(f"🎯 檢測方法切換: {part_id} -> {method_id}")

        # 獲取配置
        config = get_config()
        method_config = config.part_library.get_detection_method(part_id, method_id)

        if not method_config:
            logger.error(f"❌ 找不到檢測方法: {part_id}/{method_id}")
            return

        method_name = method_config.get("method_name", "Unknown")
        method_params = method_config.get("config", {})

        # 根據方法類型切換參數
        if method_id == "counting":
            # ===== 計數檢測方法 =====
            logger.info(f"📊 切換到計數模式: {method_name}")

            # 更新檢測參數
            self.detection_controller.min_area = method_params.get("min_area", 2)
            self.detection_controller.max_area = method_params.get("max_area", 3000)
            self.detection_controller.bg_var_threshold = method_params.get("bg_var_threshold", 3)
            self.detection_controller.bg_learning_rate = method_params.get("bg_learning_rate", 0.001)
            self.detection_controller.current_learning_rate = method_params.get("bg_learning_rate", 0.001)

            # 更新虛擬光柵參數
            self.detection_controller.gate_trigger_radius = method_params.get("gate_trigger_radius", 20)
            self.detection_controller.gate_history_frames = method_params.get("gate_history_frames", 8)

            # 重置背景減除器以應用新參數
            self.detection_controller._reset_background_subtractor()

            # 顯示包裝控制面板（計數模式特有）
            # TODO: 實作動態顯示/隱藏包裝參數設定區塊

            # 顯示狀態訊息
            self.status_label.setText(f"✅ 已切換至 [{method_name}] 模式")
            logger.info(f"✅ 已切換至 [{method_name}] 模式")
            logger.info(f"   • 面積範圍: {method_params.get('min_area')} - {method_params.get('max_area')} px")
            logger.info(f"   • 背景敏感度: {method_params.get('bg_var_threshold')}")
            logger.info(f"   • 學習率: {method_params.get('bg_learning_rate')}")
            logger.info(f"   • 光柵去重半徑: {method_params.get('gate_trigger_radius')} px")

        elif method_id == "defect_detection":
            # ===== 瑕疵檢測方法 =====
            logger.info(f"🔍 切換到瑕疵檢測模式: {method_name}")

            # TODO: 實作瑕疵檢測參數更新
            # TODO: 隱藏包裝控制面板
            # TODO: 顯示瑕疵檢測控制面板

            # 暫時顯示提示訊息
            self.status_label.setText(f"⚠️ [{method_name}] 功能開發中")
            logger.warning(f"⚠️ [{method_name}] 功能尚未實作")

            QMessageBox.information(
                self,
                "功能開發中",
                f"🔍 {method_name}\n\n"
                "此功能正在開發中，敬請期待！\n\n"
                "目前可用的檢測方法：\n"
                "• 📊 定量計數 - 已完成"
            )

        else:
            logger.warning(f"⚠️ 未知的檢測方法: {method_id}")
            self.status_label.setText(f"❌ 未知的檢測方法: {method_id}")

        # 更新配置庫的當前方法選擇
        profile = config.part_library.get_part_profile(part_id)
        if profile:
            profile["current_method_id"] = method_id
            config.save()

    # ==================== 錄影控制處理 ====================

    def on_start_recording(self):
        """開始錄影"""
        # 獲取當前幀以確定錄製參數
        frame = self.source_manager.get_frame()
        if frame is None:
            QMessageBox.warning(self, "錯誤", "無法獲取視頻源，請先啟動相機或播放視頻")
            self.recording_control.set_enabled(True)
            return

        # 獲取幀尺寸
        height, width = frame.shape[:2]
        frame_size = (width, height)

        # 獲取當前FPS
        fps = self.source_manager.get_fps()
        if fps <= 0:
            fps = 30.0  # 預設值

        # 開始錄製
        if self.video_recorder.start_recording(frame_size=frame_size, fps=fps):
            self.status_label.setText("🔴 錄製中...")
            logger.info(f"開始錄製: {frame_size} @ {fps:.1f}fps")
        else:
            QMessageBox.warning(self, "錯誤", "無法啟動視頻錄製")
            self.recording_control.set_enabled(True)

    def on_stop_recording(self):
        """停止錄影"""
        recording_info = self.video_recorder.stop_recording()

        # 隱藏狀態欄錄影指示器
        self.recording_status_label.setVisible(False)

        if recording_info:
            self.status_label.setText("✅ 錄製完成")

            # 顯示錄製信息
            info_msg = (
                f"錄製完成！\n\n"
                f"文件名: {recording_info['filename']}\n"
                f"總幀數: {recording_info['frames_recorded']} 幀\n"
                f"時長: {recording_info['duration']:.2f} 秒\n"
                f"平均幀率: {recording_info['average_fps']:.1f} fps\n"
                f"編碼器: {recording_info['codec']}"
            )
            QMessageBox.information(self, "錄製完成", info_msg)

            logger.info(f"錄製完成: {recording_info}")
        else:
            self.status_label.setText("錄製停止")

    # ========== 調試工具方法（僅開發模式） ==========

    def on_debug_load_video(self, file_path: str):
        """調試：載入測試影片（不自動播放）"""
        if self.source_manager.use_video(file_path):
            self.source_label.setText(f"源: 測試影片 - {Path(file_path).name}")
            self.status_label.setText(f"✅ 測試影片已載入，請點擊播放按鈕開始")
            self.camera_control.set_video_mode(True)

            # 啟用檢測但不自動播放，等待用戶手動點擊播放
            self.detection_controller.enable()

            logger.info(f"調試模式：已載入測試影片 {file_path}（等待手動播放）")
        else:
            QMessageBox.warning(self, "錯誤", "無法載入測試影片")

    def on_debug_play(self):
        """調試：播放視頻"""
        if self.source_manager.source_type == SourceType.VIDEO:
            self.source_manager.video_player.start_playing(loop=False)
            self.status_label.setText("▶️ 播放中...")

            # 鎖定參數面板防止誤觸
            if DEBUG_MODE:
                self.debug_panel.lock_params()

            logger.debug("調試：播放視頻")

    def on_debug_pause(self):
        """調試：暫停視頻"""
        if self.source_manager.source_type == SourceType.VIDEO:
            self.source_manager.video_player.stop_playing()
            self.status_label.setText("⏸️ 已暫停")

            # 解鎖參數面板允許調整
            if DEBUG_MODE:
                self.debug_panel.unlock_params()

            logger.debug("調試：暫停視頻")

    def on_debug_prev_frame(self):
        """調試：前一幀"""
        if self.source_manager.source_type == SourceType.VIDEO:
            player = self.source_manager.video_player
            if player.video_capture:
                # 暫停播放
                player.stop_playing()
                # 回退一幀（當前-2，因為get_frame會+1）
                current_pos = int(player.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
                new_pos = max(0, current_pos - 2)
                player.video_capture.set(cv2.CAP_PROP_POS_FRAMES, new_pos)
                logger.debug(f"調試：跳轉到幀 {new_pos}")

    def on_debug_next_frame(self):
        """調試：下一幀"""
        if self.source_manager.source_type == SourceType.VIDEO:
            player = self.source_manager.video_player
            if player.video_capture:
                # 暫停播放
                player.stop_playing()
                # 自動前進一幀（get_frame會自動讀取下一幀）
                logger.debug("調試：前進一幀")

    def on_debug_jump_frame(self, frame_num: int):
        """調試：跳轉到指定幀"""
        if self.source_manager.source_type == SourceType.VIDEO:
            player = self.source_manager.video_player
            if player.video_capture:
                player.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                self.status_label.setText(f"⏭️ 跳轉到幀 {frame_num}")
                logger.debug(f"調試：跳轉到幀 {frame_num}")

    def on_debug_screenshot(self):
        """調試：截圖當前幀"""
        import datetime

        # 獲取當前幀
        frame = self.source_manager.get_frame()
        if frame is None:
            QMessageBox.warning(self, "錯誤", "無法獲取當前幀")
            return

        # 執行檢測
        if self.detection_controller.enabled:
            detected_frame, objects = self.detection_controller.process_frame(frame.copy())
        else:
            detected_frame = frame

        # 創建截圖目錄
        screenshot_dir = Path("basler_pyqt6/screenshots")
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        original_path = screenshot_dir / f"original_{timestamp}.png"
        detected_path = screenshot_dir / f"detected_{timestamp}.png"

        # 保存截圖
        cv2.imwrite(str(original_path), frame)
        cv2.imwrite(str(detected_path), detected_frame)

        self.status_label.setText(f"📸 截圖已儲存")
        logger.info(f"調試：截圖已儲存 {original_path} 和 {detected_path}")
        QMessageBox.information(
            self, "截圖成功",
            f"截圖已儲存至:\n• {original_path.name}\n• {detected_path.name}"
        )

    def on_debug_param_changed(self, param_name: str, value):
        """調試：參數即時調整"""
        # 性能優化參數
        if param_name == 'image_scale':
            if DEBUG_MODE:
                self.perf_image_scale = value
                logger.info(f"⚡ 圖像縮放已設為: {value*100:.0f}%")
        elif param_name == 'skip_frames':
            if DEBUG_MODE:
                self.perf_skip_frames = value
                logger.info(f"⚡ 跳幀處理已設為: {value}")
        # 更新檢測控制器參數 (新版小零件檢測專用)
        elif param_name == 'min_area':
            self.detection_controller.min_area = value
            logger.info(f"📏 最小面積已設為: {value} 像素")
        elif param_name == 'max_area':
            self.detection_controller.max_area = value
            logger.info(f"📏 最大面積已設為: {value} 像素")
        elif param_name == 'bg_var_threshold':
            self.detection_controller.bg_var_threshold = value
            # 重置背景減除器以應用新參數
            self.detection_controller._reset_background_subtractor()
            logger.info(f"🎯 背景敏感度已設為: {value}")
        elif param_name == 'bg_learning_rate':
            self.detection_controller.bg_learning_rate = value
            self.detection_controller.current_learning_rate = value
            logger.info(f"📚 背景學習率已設為: {value}")
        elif param_name == 'duplicate_distance':
            # 虛擬光柵：映射到去重半徑
            self.detection_controller.gate_trigger_radius = value
            logger.info(f"🔄 光柵去重半徑已設為: {value} 像素")
        elif param_name == 'min_track_frames':
            # 虛擬光柵：映射到歷史幀數
            self.detection_controller.gate_history_frames = value
            logger.info(f"📌 光柵歷史幀數已設為: {value}")
        # 忽略舊版參數 (圓形、輪廓檢測等)
        elif param_name in ['circle_param2', 'circle_param1', 'min_radius',
                           'max_radius', 'min_dist', 'threshold', 'kernel_size']:
            logger.debug(f"⚠️ 忽略舊版參數: {param_name} (新版本不使用)")

        logger.debug(f"參數調整: {param_name} = {value}")

    def on_debug_reset_params(self):
        """調試：重置參數為預設值（basler_mvc 驗證參數）"""
        # 重置檢測參數（使用 basler_mvc 驗證過的參數）
        self.detection_controller.min_area = 2
        self.detection_controller.max_area = 3000
        self.detection_controller.bg_var_threshold = 3
        self.detection_controller.bg_learning_rate = 0.001

        # 重置虛擬光柵參數
        self.detection_controller.gate_trigger_radius = 20
        self.detection_controller.gate_history_frames = 8

        # 重置背景減除器
        self.detection_controller._reset_background_subtractor()

        # 更新調試面板UI（重置滑桿）
        if DEBUG_MODE and hasattr(self, 'debug_panel'):
            if hasattr(self.debug_panel, 'min_area_slider'):
                self.debug_panel.min_area_slider['slider'].setValue(2)
            if hasattr(self.debug_panel, 'max_area_slider'):
                self.debug_panel.max_area_slider['slider'].setValue(3000)
            if hasattr(self.debug_panel, 'bg_var_slider'):
                self.debug_panel.bg_var_slider['slider'].setValue(3)
            if hasattr(self.debug_panel, 'min_track_slider'):
                self.debug_panel.min_track_slider['slider'].setValue(3)
            if hasattr(self.debug_panel, 'duplicate_dist_slider'):
                self.debug_panel.duplicate_dist_slider['slider'].setValue(30)

        self.status_label.setText("✅ 參數已重置為 basler_mvc 預設值")
        logger.info("✅ 參數已重置為 basler_mvc 預設值")

    def on_debug_save_config(self):
        """調試：儲存參數配置"""
        import json
        from pathlib import Path

        # 創建配置目錄
        config_dir = Path("basler_pyqt6/configs")
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / "detection_config.json"

        # 儲存參數（虛擬光柵系統）
        params = {
            'min_area': self.detection_controller.min_area,
            'max_area': self.detection_controller.max_area,
            'bg_var_threshold': self.detection_controller.bg_var_threshold,
            'bg_learning_rate': self.detection_controller.bg_learning_rate,
            'gate_trigger_radius': self.detection_controller.gate_trigger_radius,
            'gate_history_frames': self.detection_controller.gate_history_frames
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(params, f, indent=4, ensure_ascii=False)

        self.status_label.setText(f"✅ 參數已儲存至 {config_file}")
        logger.info(f"調試模式：參數已儲存 {config_file}")
        QMessageBox.information(self, "儲存成功", f"參數配置已儲存至:\n{config_file}")

    def on_debug_load_config(self):
        """調試：載入參數配置"""
        import json
        from pathlib import Path

        config_file = Path("basler_pyqt6/configs/detection_config.json")

        if not config_file.exists():
            QMessageBox.warning(self, "錯誤", "找不到配置文件")
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                params = json.load(f)

            # 載入參數到檢測控制器（使用 basler_mvc 驗證參數作為預設值）
            self.detection_controller.min_area = params.get('min_area', 2)
            self.detection_controller.max_area = params.get('max_area', 3000)
            self.detection_controller.bg_var_threshold = params.get('bg_var_threshold', 3)
            self.detection_controller.bg_learning_rate = params.get('bg_learning_rate', 0.001)

            # 虛擬光柵參數（向後兼容舊配置）
            if 'gate_trigger_radius' in params:
                self.detection_controller.gate_trigger_radius = params['gate_trigger_radius']
            elif 'duplicate_distance_threshold' in params:
                # 舊配置：映射到新參數
                self.detection_controller.gate_trigger_radius = params['duplicate_distance_threshold']

            if 'gate_history_frames' in params:
                self.detection_controller.gate_history_frames = params['gate_history_frames']
            elif 'min_track_frames' in params:
                # 舊配置：映射到新參數
                self.detection_controller.gate_history_frames = params['min_track_frames']

            # 重置背景減除器
            self.detection_controller._reset_background_subtractor()

            # 更新調試面板UI
            if DEBUG_MODE and hasattr(self, 'debug_panel'):
                if hasattr(self.debug_panel, 'min_area_slider'):
                    self.debug_panel.min_area_slider['slider'].setValue(params.get('min_area', 2))
                if hasattr(self.debug_panel, 'max_area_slider'):
                    self.debug_panel.max_area_slider['slider'].setValue(params.get('max_area', 3000))
                if hasattr(self.debug_panel, 'bg_var_slider'):
                    self.debug_panel.bg_var_slider['slider'].setValue(params.get('bg_var_threshold', 3))
                if hasattr(self.debug_panel, 'min_track_slider'):
                    # 虛擬光柵：映射到歷史幀數
                    gate_history = params.get('gate_history_frames', params.get('min_track_frames', 8))
                    self.debug_panel.min_track_slider['slider'].setValue(gate_history)
                if hasattr(self.debug_panel, 'duplicate_dist_slider'):
                    # 虛擬光柵：映射到去重半徑
                    gate_radius = params.get('gate_trigger_radius', params.get('duplicate_distance_threshold', 20))
                    self.debug_panel.duplicate_dist_slider['slider'].setValue(gate_radius)

            self.status_label.setText("✅ 參數配置已載入")
            logger.info("調試模式：參數配置已載入")
            QMessageBox.information(self, "載入成功", "參數配置已載入")

        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"載入配置失敗:\n{str(e)}")
            logger.error(f"載入配置失敗: {e}")

    def on_debug_reset_total_count(self):
        """調試：重置累計檢測計數"""
        if DEBUG_MODE:
            self.detection_controller.reset()
            self.status_label.setText("🔄 累計檢測計數已重置")
            logger.info("調試模式：累計檢測計數已重置")

    def update_display(self):
        """更新顯示"""
        import time

        # 調試模式：開始計時
        if DEBUG_MODE:
            total_start = time.perf_counter()

            # === 性能優化: 跳幀處理 ===
            self.perf_frame_counter += 1
            if self.perf_skip_frames > 0:
                if self.perf_frame_counter % (self.perf_skip_frames + 1) != 0:
                    # 跳過此幀，不進行檢測
                    return

        # 獲取當前幀
        frame = self.source_manager.get_frame()

        if frame is not None:
            # 保存原始幀
            original_frame = frame.copy()

            # 1. 右上小預覽窗口 - 顯示原始相機畫面
            self.camera_preview.update_frame(original_frame)

            # === 性能優化 3: 圖像縮放 ===
            if DEBUG_MODE and self.perf_image_scale < 1.0:
                # 縮放圖像以減少計算量
                h, w = frame.shape[:2]
                new_h = int(h * self.perf_image_scale)
                new_w = int(w * self.perf_image_scale)
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # 調試模式：灰度轉換計時
            if DEBUG_MODE:
                gray_start = time.perf_counter()

            # 2. 執行檢測（如果啟用）
            if DEBUG_MODE:
                detect_start = time.perf_counter()

            if self.detection_controller.enabled:
                detected_frame, objects = self.detection_controller.process_frame(frame)
                count = len(objects)
                crossing_count = self.detection_controller.get_count()

                self.detection_label.setText(f"檢測: {count} | 穿越: {crossing_count}")

                # 🎯 更新包裝控制狀態
                self.packaging_control.update_count(crossing_count)
                pkg_status = self.detection_controller.get_packaging_status()
                self.packaging_control.update_vibrator_status(
                    pkg_status['vibrator1'],
                    pkg_status['vibrator2']
                )

                # 如果圖像有縮放，檢測結果需要縮放回原始尺寸顯示
                if DEBUG_MODE and self.perf_image_scale < 1.0:
                    h_orig, w_orig = original_frame.shape[:2]
                    detected_frame = cv2.resize(detected_frame, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)
            else:
                detected_frame = original_frame  # 使用原始幀
                count = 0

            if DEBUG_MODE:
                detect_time = (time.perf_counter() - detect_start) * 1000

            # 3. 主畫面 - 顯示檢測結果（包含檢測框標註）
            self.video_display.update_frame(detected_frame)

            # 調試模式：繪製計時
            if DEBUG_MODE:
                draw_start = time.perf_counter()

            # 調試模式：更新調試面板的原始畫面
            if DEBUG_MODE:
                self.debug_panel.original_display.update_frame(original_frame)

                draw_time = (time.perf_counter() - draw_start) * 1000

            # 錄製視頻（使用檢測後的幀）
            if self.video_recorder.is_recording:
                # 確保幀是BGR格式（OpenCV標準）
                if len(detected_frame.shape) == 2:  # 灰度圖
                    recording_frame = cv2.cvtColor(detected_frame, cv2.COLOR_GRAY2BGR)
                else:
                    recording_frame = detected_frame

                self.video_recorder.write_frame(recording_frame)

                # 更新錄製狀態
                status = self.video_recorder.get_recording_status()
                self.recording_control.update_frame_count(status['frames_recorded'])

                # 更新狀態欄錄影指示器
                self.recording_status_label.setText(f"⏺️ 錄影: {status['frames_recorded']} 幀")
                self.recording_status_label.setStyleSheet("""
                    background-color: #dc2626;
                    color: #ffffff;
                    padding: 5px 15px;
                    font-size: 10pt;
                    font-weight: bold;
                    border-radius: 4px;
                    margin: 0px 5px;
                """)
                self.recording_status_label.setVisible(True)

            # 調試模式：更新性能指標和統計
            if DEBUG_MODE:
                total_time = (time.perf_counter() - total_start) * 1000
                gray_time = 2.0  # 簡化估計

                # 更新性能指標
                fps = self.source_manager.get_fps()
                self.debug_panel.update_performance(
                    total_time, gray_time, detect_time, draw_time, fps
                )

                # 更新檢測統計
                self.debug_detection_count_history.append(count)
                if len(self.debug_detection_count_history) > 100:  # 保留最近100幀
                    self.debug_detection_count_history.pop(0)

                # 使用穿越計數作為累計總數（與舊 MVC 系統一致）
                total_count = self.detection_controller.get_count()

                avg_count = sum(self.debug_detection_count_history) / len(self.debug_detection_count_history)
                max_count = max(self.debug_detection_count_history) if self.debug_detection_count_history else 0
                min_count = min(self.debug_detection_count_history) if self.debug_detection_count_history else 0

                self.debug_panel.update_statistics(
                    count, avg_count, max_count, min_count, total_count
                )

                # 更新幀數資訊
                if self.source_manager.source_type == SourceType.VIDEO:
                    player = self.source_manager.video_player
                    if player.video_capture:
                        current_frame = int(player.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
                        total_frames = int(player.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                        self.debug_panel.update_frame_info(current_frame, total_frames)

        # 更新 FPS（工業級狀態欄格式）
        fps = self.source_manager.get_fps()
        self.fps_label.setText(f"FPS: {fps:.0f}")

        # 更新系統監控
        if self.source_manager.source_type == SourceType.CAMERA:
            total_frames = self.source_manager.camera_controller.total_frames
            self.system_monitor.update_camera_stats(fps, total_frames)
        elif self.source_manager.source_type == SourceType.VIDEO:
            total_frames = self.source_manager.video_player.total_frames
            self.system_monitor.update_camera_stats(fps, total_frames)

        # 更新狀態欄系統資源監控（每秒更新一次）
        import psutil
        if not hasattr(self, '_last_sys_update_time'):
            self._last_sys_update_time = 0
        import time
        current_time = time.time()
        if current_time - self._last_sys_update_time >= 1.0:  # 每秒更新
            try:
                cpu_percent = psutil.cpu_percent(interval=0)
                ram_percent = psutil.virtual_memory().percent
                self.system_status_label.setText(f"💻 CPU: {cpu_percent:.0f}% | RAM: {ram_percent:.0f}%")

                # 根據負載調整顏色
                if cpu_percent > 80 or ram_percent > 80:
                    bg_color = "#7f1d1d"  # 紅色 - 高負載
                elif cpu_percent > 60 or ram_percent > 60:
                    bg_color = "#78350f"  # 橙色 - 中負載
                else:
                    bg_color = "#1e293b"  # 正常

                self.system_status_label.setStyleSheet(f"""
                    background-color: {bg_color};
                    color: #cbd5e1;
                    padding: 5px 15px;
                    font-size: 9pt;
                    border-radius: 4px;
                    margin: 0px 5px;
                """)
                self._last_sys_update_time = current_time
            except:
                pass  # 忽略錯誤

    def apply_styles(self):
        """應用專業監控系統樣式"""
        self.setStyleSheet("""
            /* ===== 主窗口 ===== */
            QMainWindow {
                background-color: #0a0e27;
            }

            /* ===== 通用組件 ===== */
            QWidget {
                background-color: #141b2d;
                color: #e0e6f1;
                font-family: "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif;
                font-size: 11pt;
            }

            /* ===== 群組框 ===== */
            QGroupBox {
                border: 2px solid #1f3a5f;
                border-radius: 8px;
                margin-top: 16px;
                padding-top: 16px;
                font-weight: 600;
                font-size: 12pt;
                color: #00d4ff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                background-color: #141b2d;
            }

            /* ===== 按鈕 ===== */
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e5a8e, stop:1 #0d4a7a);
                border: 1px solid #00d4ff;
                border-radius: 6px;
                padding: 12px 20px;
                color: #ffffff;
                font-weight: 600;
                font-size: 11pt;
                min-height: 36px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00d4ff, stop:1 #0099cc);
                color: #0a0e27;
                border: 1px solid #00ffff;
            }
            QPushButton:pressed {
                background: #0d4a7a;
                border: 1px solid #0099cc;
            }
            QPushButton:disabled {
                background-color: #1f2a3d;
                color: #4a5568;
                border: 1px solid #2d3748;
            }

            /* ===== 狀態欄 ===== */
            QStatusBar {
                background-color: #0a0e27;
                color: #00d4ff;
                border-top: 2px solid #1f3a5f;
                font-size: 10pt;
            }
            QStatusBar QLabel {
                background-color: transparent;
                color: #00d4ff;
                padding: 3px 10px;
            }

            /* ===== 菜單欄 ===== */
            QMenuBar {
                background-color: #0a0e27;
                color: #e0e6f1;
                border-bottom: 2px solid #1f3a5f;
                padding: 2px;
            }
            QMenuBar::item {
                padding: 8px 12px;
                background-color: transparent;
            }
            QMenuBar::item:selected {
                background-color: #1e5a8e;
                border-radius: 4px;
            }

            /* ===== 下拉菜單 ===== */
            QMenu {
                background-color: #141b2d;
                color: #e0e6f1;
                border: 2px solid #1f3a5f;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 25px 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1e5a8e;
                color: #ffffff;
            }

            /* ===== 下拉框 ===== */
            QComboBox {
                background-color: #1f2a3d;
                border: 2px solid #1f3a5f;
                border-radius: 6px;
                padding: 8px 12px;
                color: #e0e6f1;
                font-size: 11pt;
                min-height: 32px;
            }
            QComboBox:hover {
                border: 2px solid #00d4ff;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid #00d4ff;
                margin-right: 8px;
            }

            /* ===== 滾動條 ===== */
            QScrollBar:vertical {
                background-color: #141b2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #1e5a8e;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #00d4ff;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }

            /* ===== 分割器 ===== */
            QSplitter::handle {
                background-color: #1f3a5f;
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: #00d4ff;
            }

            /* ===== 標籤 ===== */
            QLabel {
                background-color: transparent;
                color: #e0e6f1;
            }

            /* ===== 滾動區域 ===== */
            QScrollArea {
                border: none;
                background-color: #141b2d;
            }

            /* ===== 分頁控制 ===== */
            QTabWidget::pane {
                border: 2px solid #1f3a5f;
                border-radius: 8px;
                background-color: #141b2d;
                top: -2px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f2a3d, stop:1 #141b2d);
                border: 2px solid #1f3a5f;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 10px 20px;
                margin-right: 2px;
                color: #e0e6f1;
                font-size: 11pt;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e5a8e, stop:1 #0d4a7a);
                border-color: #00d4ff;
                color: #00d4ff;
            }
            QTabBar::tab:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a4a6a, stop:1 #1f3a5f);
            }
        """)

    def check_for_updates(self):
        """檢查軟件更新"""
        self.status_label.setText("🔍 正在檢查更新...")

        try:
            updater = AutoUpdater()
            update_info = updater.check_for_updates(timeout=10)

            if update_info:
                # 有更新，顯示更新對話框
                dialog = UpdateDialog(update_info, self)
                dialog.exec()
            else:
                # 無更新
                QMessageBox.information(
                    self,
                    "軟件更新",
                    "✅ 當前已是最新版本！"
                )

            self.status_label.setText("就緒")

        except Exception as e:
            logger.error(f"檢查更新失敗: {str(e)}")
            QMessageBox.warning(
                self,
                "更新檢查失敗",
                f"無法檢查更新，請稍後再試。\n\n錯誤: {str(e)}"
            )
            self.status_label.setText("就緒")

    def show_about(self):
        """顯示關於"""
        from basler_pyqt6.version import __version__
        QMessageBox.about(
            self,
            "關於",
            f"<h2>Basler 工業視覺系統 - 專業版</h2>"
            f"<p>版本: {__version__} (PyQt6)</p>"
            "<p>高性能工業相機視覺檢測系統</p>"
            "<p>支持 Basler acA640-300gm (280+ FPS)</p>"
            "<hr>"
            "<p><b>功能特點:</b></p>"
            "<ul>"
            "<li>✅ 雙模式支持（相機/視頻）</li>"
            "<li>✅ 多種檢測算法</li>"
            "<li>✅ 實時性能監控</li>"
            "<li>✅ 專業化界面設計</li>"
            "<li>✅ 自動更新功能</li>"
            "</ul>"
            "<hr>"
            "<p>© 2024 Industrial Vision</p>"
        )

    # ========== 新增菜單功能實現 ==========

    def show_preferences(self):
        """顯示偏好設定對話框"""
        QMessageBox.information(
            self,
            "偏好設定",
            "⚙️ 偏好設定功能\n\n"
            "此功能將開啟系統設定面板，讓您可以自訂：\n"
            "• 預設檢測參數\n"
            "• UI 主題和外觀\n"
            "• 快捷鍵設定\n"
            "• 自動儲存選項\n\n"
            "此功能規劃中，敬請期待！"
        )
        logger.info("偏好設定功能被觸發")

    def on_export_config(self):
        """匯出當前配置到 JSON 檔案"""
        from config.settings import get_config
        from pathlib import Path
        import json
        from datetime import datetime

        # 開啟儲存對話框
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出配置",
            f"basler_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON 檔案 (*.json)"
        )

        if file_path:
            try:
                # 獲取當前配置
                config = get_config()
                config_dict = config.to_dict()

                # 寫入檔案
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, ensure_ascii=False, indent=2)

                self.status_label.setText(f"✅ 配置已匯出至: {Path(file_path).name}")
                QMessageBox.information(
                    self,
                    "匯出成功",
                    f"配置已成功匯出至:\n{file_path}"
                )
                logger.info(f"配置已匯出至: {file_path}")

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "匯出失敗",
                    f"無法匯出配置檔案。\n\n錯誤: {str(e)}"
                )
                logger.error(f"配置匯出失敗: {str(e)}")

    def on_reset_config(self):
        """重置所有設定為預設值"""
        from config.settings import get_config

        # 二次確認
        reply = QMessageBox.question(
            self,
            "確認重置",
            "⚠️ 確定要重置所有設定為預設值嗎？\n\n"
            "這將會：\n"
            "• 重置所有檢測參數\n"
            "• 清除自訂設定\n"
            "• 恢復預設 UI 配置\n\n"
            "此操作無法復原！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                config = get_config()
                config.reset_to_default()
                config.save()

                self.status_label.setText("✅ 設定已重置為預設值")
                QMessageBox.information(
                    self,
                    "重置完成",
                    "所有設定已成功重置為預設值。\n請重新啟動應用程式以套用變更。"
                )
                logger.info("設定已重置為預設值")

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "重置失敗",
                    f"無法重置設定。\n\n錯誤: {str(e)}"
                )
                logger.error(f"設定重置失敗: {str(e)}")

    def toggle_fullscreen(self, checked):
        """切換全螢幕模式"""
        if checked:
            self.showFullScreen()
            self.status_label.setText("🖥️ 已進入全螢幕模式（按 F11 或 ESC 退出）")
            logger.info("進入全螢幕模式")
        else:
            self.showNormal()
            self.status_label.setText("🖥️ 已退出全螢幕模式")
            logger.info("退出全螢幕模式")

    def adjust_ui_scale(self, factor, reset=False):
        """調整 UI 縮放比例"""
        if reset:
            # 重置到 100%
            self.status_label.setText("🔍 UI 縮放已重置為 100%")
            logger.info("UI 縮放重置為 100%")
        else:
            # 應用縮放（未來實現）
            scale_percent = int(factor * 100)
            self.status_label.setText(f"🔍 UI 縮放: {scale_percent}%")
            logger.info(f"UI 縮放調整為: {scale_percent}%")

        # 提示：功能開發中
        if not reset:
            QMessageBox.information(
                self,
                "功能開發中",
                "🔍 UI 縮放功能正在開發中。\n\n"
                "未來將支援：\n"
                "• 介面整體縮放\n"
                "• 字體大小調整\n"
                "• 自訂顯示密度"
            )

    def clear_cache(self):
        """清理快取和暫存檔案"""
        from pathlib import Path

        reply = QMessageBox.question(
            self,
            "確認清理",
            "🗑️ 確定要清理快取嗎？\n\n"
            "這將刪除：\n"
            "• 暫存的影片檔案\n"
            "• Debug 截圖\n"
            "• 日誌快取\n\n"
            "此操作無法復原！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                cleaned_size = 0

                # 清理 screenshots 目錄
                screenshots_dir = Path("basler_pyqt6/screenshots")
                if screenshots_dir.exists():
                    for file in screenshots_dir.glob("*.png"):
                        cleaned_size += file.stat().st_size
                        file.unlink()

                # 清理 debug 目錄
                debug_dir = Path("basler_pyqt6/recordings/debug")
                if debug_dir.exists():
                    for file in debug_dir.glob("*"):
                        if file.is_file():
                            cleaned_size += file.stat().st_size
                            file.unlink()

                # 轉換為 MB
                cleaned_mb = cleaned_size / (1024 * 1024)

                self.status_label.setText(f"✅ 快取已清理（釋放 {cleaned_mb:.2f} MB）")
                QMessageBox.information(
                    self,
                    "清理完成",
                    f"快取清理成功！\n\n釋放空間: {cleaned_mb:.2f} MB"
                )
                logger.info(f"快取已清理，釋放 {cleaned_mb:.2f} MB")

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "清理失敗",
                    f"無法清理快取。\n\n錯誤: {str(e)}"
                )
                logger.error(f"快取清理失敗: {str(e)}")

    def show_documentation(self):
        """開啟線上使用說明"""
        import webbrowser

        # GitHub README 連結
        doc_url = "https://github.com/crmado/Real-time_item_monitoring_system/blob/master/README.md"

        try:
            webbrowser.open(doc_url)
            self.status_label.setText("📖 已開啟線上說明文件")
            logger.info("開啟線上說明文件")
        except Exception as e:
            QMessageBox.warning(
                self,
                "無法開啟",
                f"無法開啟瀏覽器。\n\n請手動訪問:\n{doc_url}"
            )
            logger.error(f"開啟說明文件失敗: {str(e)}")

    def show_shortcuts(self):
        """顯示鍵盤快捷鍵列表"""
        shortcuts_text = """
        <h3>⌨️ 鍵盤快捷鍵</h3>
        <table style="width:100%; border-spacing: 10px;">
        <tr><td><b>檔案操作</b></td><td></td></tr>
        <tr><td>開啟影片</td><td><code>Ctrl+O</code></td></tr>
        <tr><td>退出程式</td><td><code>Ctrl+Q</code></td></tr>

        <tr><td><b>編輯</b></td><td></td></tr>
        <tr><td>偏好設定</td><td><code>Ctrl+,</code></td></tr>

        <tr><td><b>視圖</b></td><td></td></tr>
        <tr><td>全螢幕</td><td><code>F11</code></td></tr>
        <tr><td>放大介面</td><td><code>Ctrl++</code></td></tr>
        <tr><td>縮小介面</td><td><code>Ctrl+-</code></td></tr>
        <tr><td>重置縮放</td><td><code>Ctrl+0</code></td></tr>

        <tr><td><b>相機</b></td><td></td></tr>
        <tr><td>偵測相機</td><td><code>Ctrl+D</code></td></tr>
        <tr><td>相機模式</td><td><code>Ctrl+Shift+C</code></td></tr>
        <tr><td>影片模式</td><td><code>Ctrl+Shift+V</code></td></tr>

        <tr><td><b>幫助</b></td><td></td></tr>
        <tr><td>檢查更新</td><td><code>Ctrl+U</code></td></tr>
        <tr><td>使用說明</td><td><code>F1</code></td></tr>
        </table>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("鍵盤快捷鍵")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(shortcuts_text)
        msg.exec()
        logger.info("顯示快捷鍵列表")

    def report_issue(self):
        """開啟 GitHub Issues 頁面回報問題"""
        import webbrowser

        # GitHub Issues 連結
        issues_url = "https://github.com/yourusername/Real-time_item_monitoring_system/issues/new"

        try:
            webbrowser.open(issues_url)
            self.status_label.setText("🐛 已開啟 GitHub Issues")
            logger.info("開啟 GitHub Issues 頁面")
        except Exception as e:
            QMessageBox.warning(
                self,
                "無法開啟",
                f"無法開啟瀏覽器。\n\n請手動訪問:\n{issues_url}"
            )
            logger.error(f"開啟 Issues 頁面失敗: {str(e)}")

    def closeEvent(self, event):
        """窗口關閉事件"""
        # 停止錄製
        if self.video_recorder.is_recording:
            self.video_recorder.stop_recording()

        # 清理資源
        self.source_manager.cleanup()
        self.video_recorder.cleanup()

        logger.info("✅ 資源清理完成")
        event.accept()
