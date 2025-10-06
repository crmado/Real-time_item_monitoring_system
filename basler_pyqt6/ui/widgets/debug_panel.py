"""
調試面板組件
用於開發測試和參數調優
"""

import json
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QSlider, QCheckBox, QFileDialog,
    QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

# 導入視頻顯示組件
import sys
sys.path.insert(0, str(Path(__file__).parent))
from video_display import VideoDisplayWidget

logger = logging.getLogger(__name__)


class DebugPanelWidget(QWidget):
    """調試面板組件"""

    # 信號
    load_test_video = pyqtSignal(str)  # 載入測試影片
    play_video = pyqtSignal()
    pause_video = pyqtSignal()
    prev_frame = pyqtSignal()
    next_frame = pyqtSignal()
    jump_to_frame = pyqtSignal(int)
    speed_changed = pyqtSignal(float)

    # 參數調整信號
    param_changed = pyqtSignal(str, object)  # (參數名, 值)

    # 調試選項信號
    debug_option_changed = pyqtSignal(str, bool)  # (選項名, 啟用狀態)

    # 功能信號
    save_config = pyqtSignal()
    load_config = pyqtSignal()
    reset_params = pyqtSignal()
    screenshot = pyqtSignal()
    reset_total_count = pyqtSignal()  # 重置累計計數

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_param_widgets = []  # 保存所有參數控件（用於鎖定）
        self.init_ui()

        # 發送初始性能優化參數（確保主窗口收到初始值）
        self.param_changed.emit('fps_limit', 30)
        self.param_changed.emit('image_scale', 0.5)
        self.param_changed.emit('skip_frames', 0)

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # === 原始畫面顯示 ===
        display_group = QGroupBox("📺 原始畫面預覽")
        display_layout = QVBoxLayout()

        original_label = QLabel("即時原始畫面（檢測結果請看左側大畫面）")
        original_label.setStyleSheet("""
            font-weight: bold;
            color: #00d4ff;
            font-size: 11pt;
            padding: 5px;
        """)
        display_layout.addWidget(original_label)

        self.original_display = VideoDisplayWidget()
        self.original_display.setMinimumSize(360, 270)  # 4:3 比例
        self.original_display.setFixedHeight(300)  # 固定高度確保一致性
        display_layout.addWidget(self.original_display)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        # === 測試影片載入 ===
        video_group = QGroupBox("📂 測試影片載入")
        video_layout = QVBoxLayout()

        self.video_path_label = QLabel("當前: 無")
        self.video_path_label.setStyleSheet("color: #00d4ff; font-size: 10pt;")
        video_layout.addWidget(self.video_path_label)

        btn_layout = QHBoxLayout()
        self.select_video_btn = QPushButton("選擇影片")
        self.select_video_btn.clicked.connect(self.on_select_video)

        self.quick_load_btn = QPushButton("快速載入測試目錄")
        self.quick_load_btn.clicked.connect(self.on_quick_load)

        btn_layout.addWidget(self.select_video_btn)
        btn_layout.addWidget(self.quick_load_btn)
        video_layout.addLayout(btn_layout)

        video_group.setLayout(video_layout)
        layout.addWidget(video_group)

        # === 播放控制 ===
        playback_group = QGroupBox("⏯️ 播放控制")
        playback_layout = QVBoxLayout()

        # 播放按鈕
        play_btn_layout = QHBoxLayout()
        self.prev_frame_btn = QPushButton("⏮️ 前一幀")
        self.prev_frame_btn.clicked.connect(self.prev_frame.emit)

        self.pause_btn = QPushButton("⏸️ 暫停")
        self.pause_btn.clicked.connect(self.pause_video.emit)

        self.play_btn = QPushButton("▶️ 播放")
        self.play_btn.clicked.connect(self.play_video.emit)

        self.next_frame_btn = QPushButton("⏭️ 下一幀")
        self.next_frame_btn.clicked.connect(self.next_frame.emit)

        play_btn_layout.addWidget(self.prev_frame_btn)
        play_btn_layout.addWidget(self.pause_btn)
        play_btn_layout.addWidget(self.play_btn)
        play_btn_layout.addWidget(self.next_frame_btn)
        playback_layout.addLayout(play_btn_layout)

        # 幀數控制
        frame_layout = QHBoxLayout()
        self.frame_label = QLabel("幀數: 0 / 0")
        frame_layout.addWidget(self.frame_label)

        frame_layout.addWidget(QLabel("跳轉:"))
        self.jump_input = QSpinBox()
        self.jump_input.setMinimum(0)
        self.jump_input.setMaximum(99999)
        frame_layout.addWidget(self.jump_input)

        jump_btn = QPushButton("Go")
        jump_btn.clicked.connect(lambda: self.jump_to_frame.emit(self.jump_input.value()))
        frame_layout.addWidget(jump_btn)
        playback_layout.addLayout(frame_layout)

        # 速度控制
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("速度:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "1.0x", "2.0x", "5.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.currentTextChanged.connect(self.on_speed_changed)
        speed_layout.addWidget(self.speed_combo)
        speed_layout.addStretch()
        playback_layout.addLayout(speed_layout)

        playback_group.setLayout(playback_layout)
        layout.addWidget(playback_group)

        # === 檢測參數調整 ===
        params_group = QGroupBox("🎚️ 檢測參數調整 (即時生效)")
        params_layout = QVBoxLayout()

        # 通用參數
        params_layout.addWidget(QLabel("通用參數:", parent=self))

        self.min_area_slider = self.create_param_slider(
            "最小面積", 10, 1000, 100,
            lambda v: self.param_changed.emit('min_area', v)
        )
        params_layout.addLayout(self.min_area_slider['layout'])

        self.max_area_slider = self.create_param_slider(
            "最大面積", 100, 20000, 10000,  # 增加上限和預設值
            lambda v: self.param_changed.emit('max_area', v)
        )
        params_layout.addLayout(self.max_area_slider['layout'])

        # 圓形檢測參數（平衡版本）
        params_layout.addWidget(QLabel("圓形檢測:", parent=self))

        self.circle_param2_slider = self.create_param_slider(
            "靈敏度(param2)", 1, 150, 40,  # 降低到40增加靈敏度
            lambda v: self.param_changed.emit('circle_param2', v)
        )
        params_layout.addLayout(self.circle_param2_slider['layout'])

        self.circle_param1_slider = self.create_param_slider(
            "邊緣閾值(param1)", 1, 200, 100,  # 降低到100
            lambda v: self.param_changed.emit('circle_param1', v)
        )
        params_layout.addLayout(self.circle_param1_slider['layout'])

        self.min_radius_slider = self.create_param_slider(
            "最小半徑", 1, 50, 5,  # 恢復到5
            lambda v: self.param_changed.emit('min_radius', v)
        )
        params_layout.addLayout(self.min_radius_slider['layout'])

        self.max_radius_slider = self.create_param_slider(
            "最大半徑", 10, 200, 80,  # 增加到80
            lambda v: self.param_changed.emit('max_radius', v)
        )
        params_layout.addLayout(self.max_radius_slider['layout'])

        self.min_dist_slider = self.create_param_slider(
            "最小距離", 1, 100, 25,  # 調整到25
            lambda v: self.param_changed.emit('min_dist', v)
        )
        params_layout.addLayout(self.min_dist_slider['layout'])

        # 輪廓檢測參數
        params_layout.addWidget(QLabel("輪廓檢測:", parent=self))

        self.threshold_slider = self.create_param_slider(
            "二值化閾值", 0, 255, 127,
            lambda v: self.param_changed.emit('threshold', v)
        )
        params_layout.addLayout(self.threshold_slider['layout'])

        self.kernel_size_slider = self.create_param_slider(
            "核大小", 1, 11, 3,
            lambda v: self.param_changed.emit('kernel_size', v if v % 2 == 1 else v + 1)
        )
        params_layout.addLayout(self.kernel_size_slider['layout'])

        # 配置管理按鈕
        config_btn_layout = QHBoxLayout()
        reset_btn = QPushButton("重置為預設值")
        reset_btn.clicked.connect(self.reset_params.emit)

        save_btn = QPushButton("儲存配置")
        save_btn.clicked.connect(self.save_config.emit)

        load_btn = QPushButton("載入配置")
        load_btn.clicked.connect(self.load_config.emit)

        config_btn_layout.addWidget(reset_btn)
        config_btn_layout.addWidget(save_btn)
        config_btn_layout.addWidget(load_btn)
        params_layout.addLayout(config_btn_layout)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # === 性能優化 ===
        perf_opt_group = QGroupBox("⚡ 性能優化（降低資源佔用）")
        perf_opt_layout = QVBoxLayout()

        # FPS 限制
        fps_limit_layout = QHBoxLayout()
        fps_limit_label = QLabel("FPS 限制:")
        fps_limit_label.setMinimumWidth(100)
        fps_limit_layout.addWidget(fps_limit_label)

        self.fps_limit_slider = QSlider(Qt.Orientation.Horizontal)
        self.fps_limit_slider.setMinimum(1)
        self.fps_limit_slider.setMaximum(60)
        self.fps_limit_slider.setValue(30)  # 預設30fps
        self.fps_limit_slider.valueChanged.connect(
            lambda v: self.param_changed.emit('fps_limit', v)
        )
        fps_limit_layout.addWidget(self.fps_limit_slider)

        self.fps_limit_spinbox = QSpinBox()
        self.fps_limit_spinbox.setMinimum(1)
        self.fps_limit_spinbox.setMaximum(60)
        self.fps_limit_spinbox.setValue(30)
        self.fps_limit_spinbox.setMinimumWidth(70)
        self.fps_limit_spinbox.setStyleSheet("""
            QSpinBox {
                color: #00d4ff;
                font-weight: bold;
                background-color: #1a1a2e;
                border: 1px solid #00d4ff;
                border-radius: 3px;
                padding: 2px;
            }
        """)
        self.fps_limit_slider.valueChanged.connect(self.fps_limit_spinbox.setValue)
        self.fps_limit_spinbox.valueChanged.connect(self.fps_limit_slider.setValue)
        fps_limit_layout.addWidget(self.fps_limit_spinbox)
        perf_opt_layout.addLayout(fps_limit_layout)

        # 圖像縮放比例
        scale_layout = QHBoxLayout()
        scale_label = QLabel("圖像縮放:")
        scale_label.setMinimumWidth(100)
        scale_layout.addWidget(scale_label)

        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["100% (原始)", "75%", "50%", "30%"])
        self.scale_combo.setCurrentText("50%")  # 預設50%降低計算量
        self.scale_combo.currentTextChanged.connect(
            lambda t: self.param_changed.emit('image_scale', float(t.replace('%', '').replace(' (原始)', '')) / 100)
        )
        self.scale_combo.setStyleSheet("color: #00d4ff;")
        scale_layout.addWidget(self.scale_combo)
        scale_layout.addStretch()
        perf_opt_layout.addLayout(scale_layout)

        # 跳幀處理
        skip_layout = QHBoxLayout()
        skip_label = QLabel("跳幀處理:")
        skip_label.setMinimumWidth(100)
        skip_layout.addWidget(skip_label)

        self.skip_frame_spinbox = QSpinBox()
        self.skip_frame_spinbox.setMinimum(0)
        self.skip_frame_spinbox.setMaximum(10)
        self.skip_frame_spinbox.setValue(0)
        self.skip_frame_spinbox.setMinimumWidth(70)
        self.skip_frame_spinbox.setSuffix(" 幀")
        self.skip_frame_spinbox.setStyleSheet("""
            QSpinBox {
                color: #00d4ff;
                font-weight: bold;
                background-color: #1a1a2e;
                border: 1px solid #00d4ff;
                border-radius: 3px;
                padding: 2px;
            }
        """)
        self.skip_frame_spinbox.valueChanged.connect(
            lambda v: self.param_changed.emit('skip_frames', v)
        )
        skip_layout.addWidget(self.skip_frame_spinbox)

        skip_hint = QLabel("(0=不跳幀, 1=每2幀處理1幀)")
        skip_hint.setStyleSheet("color: #888; font-size: 9pt;")
        skip_layout.addWidget(skip_hint)
        skip_layout.addStretch()
        perf_opt_layout.addLayout(skip_layout)

        perf_opt_group.setLayout(perf_opt_layout)
        layout.addWidget(perf_opt_group)

        # === 調試選項 ===
        debug_group = QGroupBox("🔬 調試選項")
        debug_layout = QVBoxLayout()

        self.show_gray_cb = QCheckBox("顯示灰度圖")
        self.show_gray_cb.stateChanged.connect(
            lambda s: self.debug_option_changed.emit('show_gray', s == 2)
        )
        debug_layout.addWidget(self.show_gray_cb)

        self.show_binary_cb = QCheckBox("顯示二值化結果")
        self.show_binary_cb.stateChanged.connect(
            lambda s: self.debug_option_changed.emit('show_binary', s == 2)
        )
        debug_layout.addWidget(self.show_binary_cb)

        self.show_edges_cb = QCheckBox("顯示邊緣檢測")
        self.show_edges_cb.stateChanged.connect(
            lambda s: self.debug_option_changed.emit('show_edges', s == 2)
        )
        debug_layout.addWidget(self.show_edges_cb)

        self.show_coords_cb = QCheckBox("顯示檢測框座標")
        self.show_coords_cb.stateChanged.connect(
            lambda s: self.debug_option_changed.emit('show_coords', s == 2)
        )
        debug_layout.addWidget(self.show_coords_cb)

        self.show_timing_cb = QCheckBox("顯示處理時間")
        self.show_timing_cb.setChecked(True)
        self.show_timing_cb.stateChanged.connect(
            lambda s: self.debug_option_changed.emit('show_timing', s == 2)
        )
        debug_layout.addWidget(self.show_timing_cb)

        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)

        # === 性能指標 ===
        perf_group = QGroupBox("⏱️ 性能指標")
        perf_layout = QVBoxLayout()

        self.total_time_label = QLabel("總處理時間: - ms")
        self.gray_time_label = QLabel("├─ 灰度轉換: - ms")
        self.detect_time_label = QLabel("├─ 檢測算法: - ms")
        self.draw_time_label = QLabel("└─ 繪製結果: - ms")
        self.fps_label = QLabel("當前 FPS: -")

        for label in [self.total_time_label, self.gray_time_label,
                     self.detect_time_label, self.draw_time_label, self.fps_label]:
            label.setStyleSheet("font-family: 'Courier New', monospace; color: #00d4ff;")
            perf_layout.addWidget(label)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        # === 檢測統計 ===
        stats_group = QGroupBox("📊 檢測統計")
        stats_layout = QVBoxLayout()

        self.total_count_label = QLabel("✨ 累計檢測總數: 0")
        self.total_count_label.setStyleSheet("""
            color: #00ff00;
            font-weight: bold;
            font-size: 13pt;
            padding: 5px;
            background-color: rgba(0, 255, 0, 0.1);
            border-radius: 3px;
        """)
        stats_layout.addWidget(self.total_count_label)

        self.current_count_label = QLabel("當前幀檢測數: 0")
        self.avg_count_label = QLabel("平均檢測數: 0.0")
        self.minmax_count_label = QLabel("最大/最小: 0 / 0")

        for label in [self.current_count_label, self.avg_count_label, self.minmax_count_label]:
            label.setStyleSheet("color: #00d4ff;")
            stats_layout.addWidget(label)

        # 重置計數按鈕
        reset_count_btn = QPushButton("🔄 重置累計計數")
        reset_count_btn.clicked.connect(self.reset_count)
        reset_count_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        stats_layout.addWidget(reset_count_btn)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # === 功能按鈕 ===
        action_layout = QHBoxLayout()

        screenshot_btn = QPushButton("📸 截圖當前幀")
        screenshot_btn.clicked.connect(self.screenshot.emit)

        export_btn = QPushButton("📝 匯出檢測報告")
        export_btn.setEnabled(False)  # 暫時禁用

        action_layout.addWidget(screenshot_btn)
        action_layout.addWidget(export_btn)
        layout.addLayout(action_layout)

        layout.addStretch()

    def create_param_slider(self, label: str, min_val: int, max_val: int,
                           default_val: int, callback) -> dict:
        """創建參數滑桿（含數值輸入框）"""
        layout = QHBoxLayout()

        label_widget = QLabel(f"{label}:")
        label_widget.setMinimumWidth(120)
        layout.addWidget(label_widget)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)
        slider.valueChanged.connect(callback)
        layout.addWidget(slider)

        # 數值輸入框（取代純顯示的 Label）
        spinbox = QSpinBox()
        spinbox.setMinimum(min_val)
        spinbox.setMaximum(max_val)
        spinbox.setValue(default_val)
        spinbox.setMinimumWidth(70)
        spinbox.setStyleSheet("""
            QSpinBox {
                color: #00d4ff;
                font-weight: bold;
                background-color: #1a1a2e;
                border: 1px solid #00d4ff;
                border-radius: 3px;
                padding: 2px;
            }
        """)

        # 雙向綁定：滑桿 ↔ 輸入框
        slider.valueChanged.connect(spinbox.setValue)
        spinbox.valueChanged.connect(slider.setValue)

        layout.addWidget(spinbox)

        # 保存控件到列表（用於鎖定功能）
        self.all_param_widgets.extend([slider, spinbox])

        return {
            'layout': layout,
            'slider': slider,
            'spinbox': spinbox
        }

    def on_select_video(self):
        """選擇測試影片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "選擇測試影片",
            str(Path.home()),
            "視頻文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*.*)"
        )

        if file_path:
            self.video_path_label.setText(f"當前: {Path(file_path).name}")
            self.load_test_video.emit(file_path)
            logger.info(f"載入測試影片: {file_path}")

    def on_quick_load(self):
        """快速載入測試目錄"""
        from basler_pyqt6.version import TEST_DATA_DIR

        test_dir = Path(TEST_DATA_DIR)
        if not test_dir.exists():
            logger.warning(f"測試目錄不存在: {test_dir}")
            return

        # 尋找第一個視頻文件
        video_files = list(test_dir.glob("*.mp4")) + list(test_dir.glob("*.avi"))

        if video_files:
            file_path = str(video_files[0])
            self.video_path_label.setText(f"當前: {Path(file_path).name}")
            self.load_test_video.emit(file_path)
            logger.info(f"快速載入: {file_path}")
        else:
            logger.warning(f"測試目錄中沒有視頻文件: {test_dir}")

    def on_speed_changed(self, text: str):
        """播放速度改變"""
        speed = float(text.replace('x', ''))
        self.speed_changed.emit(speed)

    def update_frame_info(self, current: int, total: int):
        """更新幀數資訊"""
        self.frame_label.setText(f"幀數: {current} / {total}")
        self.jump_input.setMaximum(total)

    def update_performance(self, total_ms: float, gray_ms: float,
                          detect_ms: float, draw_ms: float, fps: float):
        """更新性能指標"""
        self.total_time_label.setText(f"總處理時間: {total_ms:.1f} ms")
        self.gray_time_label.setText(f"├─ 灰度轉換: {gray_ms:.1f} ms")
        self.detect_time_label.setText(f"├─ 檢測算法: {detect_ms:.1f} ms")
        self.draw_time_label.setText(f"└─ 繪製結果: {draw_ms:.1f} ms")
        self.fps_label.setText(f"當前 FPS: {fps:.1f}")

    def update_statistics(self, current: int, average: float,
                         max_count: int, min_count: int, total_count: int = 0):
        """更新檢測統計"""
        self.total_count_label.setText(f"✨ 累計檢測總數: {total_count}")
        self.current_count_label.setText(f"當前幀檢測數: {current}")
        self.avg_count_label.setText(f"平均檢測數: {average:.1f}")
        self.minmax_count_label.setText(f"最大/最小: {max_count} / {min_count}")

    def reset_count(self):
        """重置累計計數"""
        self.reset_total_count.emit()
        self.total_count_label.setText("✨ 累計檢測總數: 0")
        logger.info("累計檢測計數已重置")

    def lock_params(self):
        """鎖定參數控件（播放時防止誤觸）"""
        for widget in self.all_param_widgets:
            widget.setEnabled(False)
        logger.debug("參數面板已鎖定（播放中）")

    def unlock_params(self):
        """解鎖參數控件（暫停時可調整）"""
        for widget in self.all_param_widgets:
            widget.setEnabled(True)
        logger.debug("參數面板已解鎖（已暫停）")
