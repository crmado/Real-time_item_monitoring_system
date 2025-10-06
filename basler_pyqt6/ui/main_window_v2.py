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
from basler_pyqt6.ui.widgets.detection_control import DetectionControlWidget
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

logger = logging.getLogger(__name__)


class MainWindowV2(QMainWindow):
    """主窗口 V2 - 完整版"""

    def __init__(self):
        super().__init__()
        self.source_manager = SourceManager()
        self.detection_controller = DetectionController()
        self.video_recorder = VideoRecorder()

        # 調試模式變量
        if DEBUG_MODE:
            self.debug_detection_count_history = []  # 檢測數量歷史
            self.debug_frame_times = []  # 幀處理時間歷史
            self.debug_total_detection_count = 0  # 累計檢測總數

            # 性能優化變量
            self.perf_fps_limit = 30  # FPS限制（預設30）
            self.perf_image_scale = 0.5  # 圖像縮放比例（預設50%）
            self.perf_skip_frames = 0  # 跳幀數（預設不跳幀）
            self.perf_frame_counter = 0  # 幀計數器（用於跳幀）
            self.perf_last_process_time = 0  # 上次處理時間（用於FPS限制）

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
        monitoring_layout.setContentsMargins(10, 10, 10, 10)

        # 原始畫面預覽（小）
        self.camera_preview = VideoDisplayWidget()
        self.camera_preview.setFixedHeight(200)
        self.camera_preview.setMinimumWidth(320)
        self.camera_preview.setStyleSheet("""
            QWidget {
                border: 2px solid #00d4ff;
                border-radius: 8px;
                background-color: #0a0e27;
            }
        """)
        preview_label = QLabel("📹 原始畫面預覽")
        preview_label.setStyleSheet("""
            font-weight: bold;
            color: #00d4ff;
            font-size: 13pt;
            padding: 5px 0px;
            border-bottom: 2px solid #00d4ff;
        """)
        monitoring_layout.addWidget(preview_label)
        monitoring_layout.addWidget(self.camera_preview)

        # 主要控制按鈕（一鍵啟動）
        self.main_start_btn = QPushButton("🚀 開始檢測")
        self.main_start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00d4ff, stop:1 #0099cc);
                border: 2px solid #00ffff;
                border-radius: 8px;
                padding: 16px 24px;
                color: #0a0e27;
                font-weight: bold;
                font-size: 14pt;
                min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00ffff, stop:1 #00d4ff);
            }
            QPushButton:pressed {
                background: #0099cc;
            }
        """)
        self.main_start_btn.clicked.connect(self.on_main_start_clicked)
        monitoring_layout.addWidget(self.main_start_btn)

        self.main_stop_btn = QPushButton("⏹️ 停止檢測")
        self.main_stop_btn.setEnabled(False)
        self.main_stop_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ef4444, stop:1 #dc2626);
                border: 2px solid #fca5a5;
                border-radius: 8px;
                padding: 16px 24px;
                color: #ffffff;
                font-weight: bold;
                font-size: 14pt;
                min-height: 50px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff5555, stop:1 #ef4444);
            }
        """)
        self.main_stop_btn.clicked.connect(self.on_main_stop_clicked)
        monitoring_layout.addWidget(self.main_stop_btn)

        # 檢測控制
        self.detection_control = DetectionControlWidget()
        monitoring_layout.addWidget(self.detection_control)

        # 錄影控制
        self.recording_control = RecordingControlWidget()
        monitoring_layout.addWidget(self.recording_control)

        # 系統監控
        self.system_monitor = SystemMonitorWidget()
        monitoring_layout.addWidget(self.system_monitor)

        monitoring_layout.addStretch()

        # ========== Tab 3: 調試工具（僅開發模式） ==========
        if DEBUG_MODE:
            self.debug_panel = DebugPanelWidget()
            # 稍後連接調試面板信號
            logger.info("🛠️ 開發模式已啟用 - 調試工具可用")

        # 添加分頁到 TabWidget
        tab_widget.addTab(camera_settings_tab, "⚙️ 相機設定")
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
        """創建菜單欄"""
        menubar = self.menuBar()

        # 文件菜單
        file_menu = menubar.addMenu("文件(&F)")

        load_video_action = QAction("📂 加載視頻文件...", self)
        load_video_action.setShortcut("Ctrl+O")
        load_video_action.triggered.connect(self.load_video_file)
        file_menu.addAction(load_video_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 模式菜單
        mode_menu = menubar.addMenu("模式(&M)")

        camera_mode_action = QAction("📷 相機模式", self)
        camera_mode_action.triggered.connect(self.switch_to_camera_mode)
        mode_menu.addAction(camera_mode_action)

        video_mode_action = QAction("🎬 視頻模式", self)
        video_mode_action.triggered.connect(self.load_video_file)
        mode_menu.addAction(video_mode_action)

        # 幫助菜單
        help_menu = menubar.addMenu("幫助(&H)")

        check_update_action = QAction("🔄 檢查更新", self)
        check_update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(check_update_action)

        help_menu.addSeparator()

        about_action = QAction("關於(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_status_bar(self):
        """創建狀態欄"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label = QLabel("就緒")
        self.status_bar.addWidget(self.status_label)

        self.source_label = QLabel("源: 無")
        self.status_bar.addPermanentWidget(self.source_label)

        self.fps_label = QLabel("FPS: 0")
        self.status_bar.addPermanentWidget(self.fps_label)

        self.detection_label = QLabel("檢測: 0")
        self.status_bar.addPermanentWidget(self.detection_label)

    def connect_signals(self):
        """連接信號"""
        # 相機控制
        self.camera_control.detect_clicked.connect(self.on_detect_cameras)
        self.camera_control.connect_clicked.connect(self.on_connect_camera)
        self.camera_control.disconnect_clicked.connect(self.on_disconnect_camera)
        self.camera_control.start_clicked.connect(self.on_start_source)
        self.camera_control.stop_clicked.connect(self.on_stop_source)
        self.camera_control.exposure_changed.connect(self.on_exposure_changed)

        # 檢測控制
        self.detection_control.method_changed.connect(self.on_detection_method_changed)
        self.detection_control.enable_changed.connect(self.on_detection_enable_changed)

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
            self.source_manager.video_player.start_playing(loop=True)
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

    def on_detection_method_changed(self, method):
        """檢測方法改變"""
        from basler_pyqt6.core.detection import DetectionMethod
        method_map = {
            "circle": DetectionMethod.CIRCLE,
            "contour": DetectionMethod.CONTOUR,
            "background": DetectionMethod.BACKGROUND
        }
        if method in method_map:
            self.detection_controller.set_method(method_map[method])
            self.status_label.setText(f"檢測方法: {method}")

    def on_detection_enable_changed(self, enabled):
        """檢測啟用改變"""
        if enabled:
            self.detection_controller.enable()
            self.status_label.setText("檢測已啟用")
        else:
            self.detection_controller.disable()
            self.status_label.setText("檢測已禁用")

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

    def on_main_start_clicked(self):
        """主要啟動按鈕 - 一鍵啟動檢測（合併開始抓取 + 啟用檢測）"""
        # 1. 開始視頻源（相機抓取或視頻播放）
        if self.source_manager.source_type == SourceType.CAMERA:
            # 檢查相機是否已連接
            if not self.source_manager.camera_controller.camera:
                QMessageBox.warning(self, "錯誤", "請先在「相機設定」頁面連接相機！")
                return

            self.source_manager.camera_controller.start_grabbing()
            self.status_label.setText("🚀 開始檢測（相機模式）")
            logger.info("啟動相機抓取")

        elif self.source_manager.source_type == SourceType.VIDEO:
            self.source_manager.video_player.start_playing(loop=True)
            self.status_label.setText("🚀 開始檢測（視頻模式）")
            logger.info("啟動視頻播放")
        else:
            QMessageBox.warning(self, "錯誤", "未選擇視頻源")
            return

        # 2. 自動啟用檢測
        self.detection_controller.enable()
        self.detection_control.enable_checkbox.setChecked(True)

        # 3. 更新按鈕狀態
        self.main_start_btn.setEnabled(False)
        self.main_stop_btn.setEnabled(True)

        # 4. 啟用錄製功能
        self.recording_control.set_enabled(True)

        logger.info("✅ 一鍵啟動完成：視頻源已啟動 + 檢測已啟用")

    def on_main_stop_clicked(self):
        """主要停止按鈕 - 停止所有檢測活動"""
        # 1. 如果正在錄製，先停止錄製
        if self.video_recorder.is_recording:
            self.on_stop_recording()

        # 2. 停止檢測
        self.detection_controller.disable()
        self.detection_control.enable_checkbox.setChecked(False)

        # 3. 停止視頻源
        if self.source_manager.source_type == SourceType.CAMERA:
            self.source_manager.camera_controller.stop_grabbing()
            logger.info("停止相機抓取")
        elif self.source_manager.source_type == SourceType.VIDEO:
            self.source_manager.video_player.stop_playing()
            logger.info("停止視頻播放")

        # 4. 更新按鈕狀態
        self.main_start_btn.setEnabled(True)
        self.main_stop_btn.setEnabled(False)

        # 5. 禁用錄製功能
        self.recording_control.set_enabled(False)

        self.status_label.setText("⏹️ 已停止檢測")
        logger.info("✅ 已停止所有檢測活動")

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
            self.source_manager.video_player.start_playing(loop=True)
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
        if param_name == 'fps_limit':
            if DEBUG_MODE:
                self.perf_fps_limit = value
                logger.info(f"⚡ FPS 限制已設為: {value}")
        elif param_name == 'image_scale':
            if DEBUG_MODE:
                self.perf_image_scale = value
                logger.info(f"⚡ 圖像縮放已設為: {value*100:.0f}%")
        elif param_name == 'skip_frames':
            if DEBUG_MODE:
                self.perf_skip_frames = value
                logger.info(f"⚡ 跳幀處理已設為: {value}")
        # 更新檢測控制器參數
        elif param_name == 'min_area':
            self.detection_controller.params['min_area'] = value
        elif param_name == 'max_area':
            self.detection_controller.params['max_area'] = value
        elif param_name == 'circle_param2':
            self.detection_controller.params['circle']['param2'] = value
        elif param_name == 'circle_param1':
            self.detection_controller.params['circle']['param1'] = value
        elif param_name == 'min_radius':
            self.detection_controller.params['circle']['min_radius'] = value
        elif param_name == 'max_radius':
            self.detection_controller.params['circle']['max_radius'] = value
        elif param_name == 'min_dist':
            self.detection_controller.params['circle']['min_dist'] = value
        elif param_name == 'threshold':
            self.detection_controller.params['contour']['threshold'] = value
        elif param_name == 'kernel_size':
            self.detection_controller.params['contour']['kernel_size'] = value

        logger.debug(f"參數調整: {param_name} = {value}")

    def on_debug_reset_params(self):
        """調試：重置參數為預設值（平衡版本）"""
        # 重置為平衡的預設參數
        self.detection_controller.params = {
            'min_area': 100,
            'max_area': 10000,
            'circle': {
                'dp': 1.2,
                'min_dist': 25,
                'param1': 100,
                'param2': 40,
                'min_radius': 5,
                'max_radius': 80
            },
            'contour': {
                'threshold': 127,
                'kernel_size': 3
            }
        }

        # 更新調試面板UI（重置滑桿）
        if DEBUG_MODE:
            self.debug_panel.min_area_slider['slider'].setValue(100)
            self.debug_panel.max_area_slider['slider'].setValue(10000)
            self.debug_panel.circle_param2_slider['slider'].setValue(40)
            self.debug_panel.circle_param1_slider['slider'].setValue(100)
            self.debug_panel.min_radius_slider['slider'].setValue(5)
            self.debug_panel.max_radius_slider['slider'].setValue(80)
            self.debug_panel.min_dist_slider['slider'].setValue(25)
            self.debug_panel.threshold_slider['slider'].setValue(127)
            self.debug_panel.kernel_size_slider['slider'].setValue(3)

        self.status_label.setText("✅ 參數已重置為預設值")
        logger.info("調試模式：參數已重置為平衡值")

    def on_debug_save_config(self):
        """調試：儲存參數配置"""
        import json
        from pathlib import Path

        # 創建配置目錄
        config_dir = Path("basler_pyqt6/configs")
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / "detection_config.json"

        # 儲存參數
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.detection_controller.params, f, indent=4, ensure_ascii=False)

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

            self.detection_controller.params = params

            # 更新調試面板UI
            if DEBUG_MODE:
                self.debug_panel.min_area_slider['slider'].setValue(params.get('min_area', 100))
                self.debug_panel.max_area_slider['slider'].setValue(params.get('max_area', 5000))
                self.debug_panel.circle_param2_slider['slider'].setValue(params['circle']['param2'])
                self.debug_panel.circle_param1_slider['slider'].setValue(params['circle']['param1'])
                self.debug_panel.min_radius_slider['slider'].setValue(params['circle']['min_radius'])
                self.debug_panel.max_radius_slider['slider'].setValue(params['circle']['max_radius'])
                self.debug_panel.min_dist_slider['slider'].setValue(params['circle']['min_dist'])
                self.debug_panel.threshold_slider['slider'].setValue(params['contour']['threshold'])
                self.debug_panel.kernel_size_slider['slider'].setValue(params['contour']['kernel_size'])

            self.status_label.setText("✅ 參數配置已載入")
            logger.info("調試模式：參數配置已載入")
            QMessageBox.information(self, "載入成功", "參數配置已載入")

        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"載入配置失敗:\n{str(e)}")
            logger.error(f"載入配置失敗: {e}")

    def on_debug_reset_total_count(self):
        """調試：重置累計檢測計數"""
        if DEBUG_MODE:
            self.debug_total_detection_count = 0
            self.status_label.setText("🔄 累計檢測計數已重置")
            logger.info("調試模式：累計檢測計數已重置")

    def update_display(self):
        """更新顯示"""
        import time

        # 調試模式：開始計時
        if DEBUG_MODE:
            total_start = time.perf_counter()

            # === 性能優化 1: FPS 限制 ===
            current_time = time.perf_counter()
            min_frame_interval = 1.0 / self.perf_fps_limit  # 計算最小幀間隔
            elapsed = current_time - self.perf_last_process_time

            if elapsed < min_frame_interval:
                # 時間未到，跳過本幀處理，節省CPU
                time.sleep(min_frame_interval - elapsed)  # 休眠剩餘時間
                return

            self.perf_last_process_time = current_time

            # === 性能優化 2: 跳幀處理 ===
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
                self.detection_label.setText(f"檢測: {count}")
                self.detection_control.update_status(True, count)

                # 如果圖像有縮放，檢測結果需要縮放回原始尺寸顯示
                if DEBUG_MODE and self.perf_image_scale < 1.0:
                    h_orig, w_orig = original_frame.shape[:2]
                    detected_frame = cv2.resize(detected_frame, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)
            else:
                detected_frame = original_frame  # 使用原始幀
                count = 0
                self.detection_control.update_status(False, 0)

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

                # 累加檢測總數（只在有檢測到物體時累加）
                if count > 0:
                    self.debug_total_detection_count += count

                avg_count = sum(self.debug_detection_count_history) / len(self.debug_detection_count_history)
                max_count = max(self.debug_detection_count_history) if self.debug_detection_count_history else 0
                min_count = min(self.debug_detection_count_history) if self.debug_detection_count_history else 0

                self.debug_panel.update_statistics(
                    count, avg_count, max_count, min_count, self.debug_total_detection_count
                )

                # 更新幀數資訊
                if self.source_manager.source_type == SourceType.VIDEO:
                    player = self.source_manager.video_player
                    if player.video_capture:
                        current_frame = int(player.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
                        total_frames = int(player.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                        self.debug_panel.update_frame_info(current_frame, total_frames)

        # 更新 FPS
        fps = self.source_manager.get_fps()
        self.fps_label.setText(f"FPS: {fps:.1f}")

        # 更新系統監控
        if self.source_manager.source_type == SourceType.CAMERA:
            total_frames = self.source_manager.camera_controller.total_frames
            self.system_monitor.update_camera_stats(fps, total_frames)
        elif self.source_manager.source_type == SourceType.VIDEO:
            total_frames = self.source_manager.video_player.total_frames
            self.system_monitor.update_camera_stats(fps, total_frames)

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
