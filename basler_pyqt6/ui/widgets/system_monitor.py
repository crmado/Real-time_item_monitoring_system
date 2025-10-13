"""
系統監控組件 - 工業級監控面板
"""

import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QLabel, QProgressBar, QHBoxLayout
)
from PyQt6.QtCore import QTimer, Qt


class SystemMonitorWidget(QWidget):
    """系統監控組件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.init_timer()

    def init_ui(self):
        """初始化 UI - 工業級監控面板"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 創建分組框
        group_box = QGroupBox("📊 系統資源")
        group_layout = QVBoxLayout()
        group_layout.setSpacing(12)

        # === FPS 指標（最重要，放最上面）===
        fps_container = QWidget()
        fps_container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1e3a5f, stop:1 #0d2544);
                border: 2px solid #00d4ff;
                border-radius: 10px;
            }
        """)
        fps_layout = QVBoxLayout(fps_container)
        fps_layout.setContentsMargins(10, 8, 10, 8)
        fps_layout.setSpacing(3)

        fps_title = QLabel("⚡ 相機 FPS")
        fps_title.setStyleSheet("color: #9ca3af; font-size: 9pt; background: transparent; border: none;")
        fps_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fps_layout.addWidget(fps_title)

        self.camera_fps_label = QLabel("0")
        self.camera_fps_label.setStyleSheet("color: #00d4ff; font-weight: bold; font-size: 24pt; background: transparent; border: none;")
        self.camera_fps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fps_layout.addWidget(self.camera_fps_label)

        fps_unit = QLabel("幀/秒")
        fps_unit.setStyleSheet("color: #6b7280; font-size: 8pt; background: transparent; border: none;")
        fps_unit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fps_layout.addWidget(fps_unit)

        group_layout.addWidget(fps_container)

        # === CPU 使用率（帶進度條）===
        cpu_container = QWidget()
        cpu_container.setStyleSheet("background: transparent; border: none;")
        cpu_layout = QVBoxLayout(cpu_container)
        cpu_layout.setContentsMargins(5, 5, 5, 5)
        cpu_layout.setSpacing(5)

        self.cpu_label = QLabel("CPU: 0%")
        self.cpu_label.setStyleSheet("color: #e0e6f1; font-size: 10pt; font-weight: bold; background: transparent; border: none;")
        cpu_layout.addWidget(self.cpu_label)

        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        self.cpu_bar.setTextVisible(False)
        self.cpu_bar.setFixedHeight(8)
        self.cpu_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1f3a5f;
                border-radius: 4px;
                background-color: #0a0e27;
            }
            QProgressBar::chunk {
                background-color: #00d4ff;
                border-radius: 3px;
            }
        """)
        cpu_layout.addWidget(self.cpu_bar)

        group_layout.addWidget(cpu_container)

        # === 記憶體使用率（帶進度條）===
        memory_container = QWidget()
        memory_container.setStyleSheet("background: transparent; border: none;")
        memory_layout = QVBoxLayout(memory_container)
        memory_layout.setContentsMargins(5, 5, 5, 5)
        memory_layout.setSpacing(5)

        self.memory_label = QLabel("記憶體: 0%")
        self.memory_label.setStyleSheet("color: #e0e6f1; font-size: 10pt; font-weight: bold; background: transparent; border: none;")
        memory_layout.addWidget(self.memory_label)

        self.memory_bar = QProgressBar()
        self.memory_bar.setRange(0, 100)
        self.memory_bar.setValue(0)
        self.memory_bar.setTextVisible(False)
        self.memory_bar.setFixedHeight(8)
        self.memory_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #1f3a5f;
                border-radius: 4px;
                background-color: #0a0e27;
            }
            QProgressBar::chunk {
                background-color: #8b5cf6;
                border-radius: 3px;
            }
        """)
        memory_layout.addWidget(self.memory_bar)

        group_layout.addWidget(memory_container)

        # === 次要指標（較小字體）===
        # 進程記憶體
        self.process_memory_label = QLabel("進程記憶體: 0 MB")
        self.process_memory_label.setStyleSheet("color: #6b7280; font-size: 9pt; background: transparent; border: none;")
        group_layout.addWidget(self.process_memory_label)

        # 檢測 FPS（次要指標）
        self.detection_fps_label = QLabel("處理 FPS: 0")
        self.detection_fps_label.setStyleSheet("color: #6b7280; font-size: 9pt; background: transparent; border: none;")
        group_layout.addWidget(self.detection_fps_label)

        # 總幀數
        self.total_frames_label = QLabel("總幀數: 0")
        self.total_frames_label.setStyleSheet("color: #6b7280; font-size: 9pt; background: transparent; border: none;")
        group_layout.addWidget(self.total_frames_label)

        group_box.setLayout(group_layout)
        layout.addWidget(group_box)

    def init_timer(self):
        """初始化定時器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_metrics)
        self.timer.start(1000)  # 每秒更新一次

    def update_metrics(self):
        """更新性能指標 - 工業級視覺警報"""
        try:
            # CPU 使用率（帶顏色警報）
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
            self.cpu_bar.setValue(int(cpu_percent))

            # CPU 警報邏輯（工業級閾值）
            if cpu_percent > 80:
                # 高負載警告（紅色）
                self.cpu_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #ef4444;
                        border-radius: 4px;
                        background-color: #0a0e27;
                    }
                    QProgressBar::chunk {
                        background-color: #ef4444;
                        border-radius: 3px;
                    }
                """)
                self.cpu_label.setStyleSheet("color: #ef4444; font-size: 10pt; font-weight: bold; background: transparent; border: none;")
            elif cpu_percent > 60:
                # 中負載提示（橙色）
                self.cpu_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #f59e0b;
                        border-radius: 4px;
                        background-color: #0a0e27;
                    }
                    QProgressBar::chunk {
                        background-color: #f59e0b;
                        border-radius: 3px;
                    }
                """)
                self.cpu_label.setStyleSheet("color: #f59e0b; font-size: 10pt; font-weight: bold; background: transparent; border: none;")
            else:
                # 正常負載（青色）
                self.cpu_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #1f3a5f;
                        border-radius: 4px;
                        background-color: #0a0e27;
                    }
                    QProgressBar::chunk {
                        background-color: #00d4ff;
                        border-radius: 3px;
                    }
                """)
                self.cpu_label.setStyleSheet("color: #e0e6f1; font-size: 10pt; font-weight: bold; background: transparent; border: none;")

            # 記憶體使用率（帶顏色警報）
            memory = psutil.virtual_memory()
            self.memory_label.setText(f"記憶體: {memory.percent:.1f}%")
            self.memory_bar.setValue(int(memory.percent))

            # 記憶體警報邏輯
            if memory.percent > 85:
                # 高使用率警告（紅色）
                self.memory_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #ef4444;
                        border-radius: 4px;
                        background-color: #0a0e27;
                    }
                    QProgressBar::chunk {
                        background-color: #ef4444;
                        border-radius: 3px;
                    }
                """)
                self.memory_label.setStyleSheet("color: #ef4444; font-size: 10pt; font-weight: bold; background: transparent; border: none;")
            elif memory.percent > 70:
                # 中使用率提示（橙色）
                self.memory_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #f59e0b;
                        border-radius: 4px;
                        background-color: #0a0e27;
                    }
                    QProgressBar::chunk {
                        background-color: #f59e0b;
                        border-radius: 3px;
                    }
                """)
                self.memory_label.setStyleSheet("color: #f59e0b; font-size: 10pt; font-weight: bold; background: transparent; border: none;")
            else:
                # 正常使用率（紫色）
                self.memory_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #1f3a5f;
                        border-radius: 4px;
                        background-color: #0a0e27;
                    }
                    QProgressBar::chunk {
                        background-color: #8b5cf6;
                        border-radius: 3px;
                    }
                """)
                self.memory_label.setStyleSheet("color: #e0e6f1; font-size: 10pt; font-weight: bold; background: transparent; border: none;")

            # 進程記憶體
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024 * 1024)
            self.process_memory_label.setText(f"進程記憶體: {process_memory:.0f} MB")

        except Exception as e:
            print(f"❌ 更新監控指標錯誤: {str(e)}")

    def update_camera_stats(self, fps, total_frames):
        """更新相機統計 - 大型 FPS 卡片"""
        # 更新大型 FPS 顯示（只顯示數字）
        self.camera_fps_label.setText(f"{fps:.0f}")

        # 更新總幀數（格式化為千分位）
        self.total_frames_label.setText(f"總幀數: {total_frames:,}")

    def update_detection_fps(self, fps):
        """更新檢測 FPS"""
        self.detection_fps_label.setText(f"檢測 FPS: {fps:.1f}")
