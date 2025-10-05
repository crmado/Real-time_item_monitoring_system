"""
更新對話框
顯示更新信息並處理更新下載與安裝
"""

import logging
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTextEdit, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from basler_pyqt6.core.updater import AutoUpdater, UpdateInfo

logger = logging.getLogger(__name__)


class DownloadThread(QThread):
    """下載線程"""
    progress_updated = pyqtSignal(int, int)  # current, total
    download_finished = pyqtSignal(str)  # download_path
    download_failed = pyqtSignal(str)  # error_message

    def __init__(self, updater: AutoUpdater, update_info: UpdateInfo):
        super().__init__()
        self.updater = updater
        self.update_info = update_info

    def run(self):
        """執行下載"""
        try:
            def progress_callback(current, total):
                self.progress_updated.emit(current, total)

            download_path = self.updater.download_update(
                self.update_info,
                progress_callback=progress_callback
            )

            if download_path:
                self.download_finished.emit(str(download_path))
            else:
                self.download_failed.emit("下載失敗")

        except Exception as e:
            self.download_failed.emit(str(e))


class UpdateDialog(QDialog):
    """更新對話框"""

    def __init__(self, update_info: UpdateInfo, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.updater = AutoUpdater()
        self.download_thread: Optional[DownloadThread] = None
        self.downloaded_path: Optional[str] = None

        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("軟件更新")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 標題
        title_label = QLabel("🆕 發現新版本！")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # 版本信息
        version_widget = QWidget()
        version_layout = QVBoxLayout(version_widget)
        version_layout.setContentsMargins(0, 0, 0, 0)

        current_version_label = QLabel(f"當前版本: {self.updater.current_version}")
        new_version_label = QLabel(f"最新版本: {self.update_info.version}")

        new_version_font = QFont()
        new_version_font.setBold(True)
        new_version_label.setFont(new_version_font)
        new_version_label.setStyleSheet("color: #4CAF50;")

        version_layout.addWidget(current_version_label)
        version_layout.addWidget(new_version_label)

        if self.update_info.release_date:
            release_date_label = QLabel(f"發布日期: {self.update_info.release_date}")
            version_layout.addWidget(release_date_label)

        if self.update_info.file_size > 0:
            size_mb = self.update_info.file_size / (1024 * 1024)
            size_label = QLabel(f"文件大小: {size_mb:.2f} MB")
            version_layout.addWidget(size_label)

        layout.addWidget(version_widget)

        # 更新日誌
        changelog_label = QLabel("更新內容:")
        changelog_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(changelog_label)

        self.changelog_text = QTextEdit()
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setPlainText(
            self.update_info.changelog or "暫無更新說明"
        )
        self.changelog_text.setMaximumHeight(150)
        layout.addWidget(self.changelog_text)

        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 狀態標籤
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # 按鈕
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.skip_button = QPushButton("跳過")
        self.skip_button.clicked.connect(self.reject)
        button_layout.addWidget(self.skip_button)

        self.download_button = QPushButton("立即更新")
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.download_button.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_button)

        layout.addLayout(button_layout)

        # 如果是強制更新，禁用跳過按鈕
        if self.update_info.mandatory:
            self.skip_button.setEnabled(False)
            self.skip_button.setText("強制更新")

    def start_download(self):
        """開始下載更新"""
        self.download_button.setEnabled(False)
        self.skip_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("⬇️ 正在下載更新...")

        # 創建並啟動下載線程
        self.download_thread = DownloadThread(self.updater, self.update_info)
        self.download_thread.progress_updated.connect(self.on_progress_updated)
        self.download_thread.download_finished.connect(self.on_download_finished)
        self.download_thread.download_failed.connect(self.on_download_failed)
        self.download_thread.start()

    def on_progress_updated(self, current: int, total: int):
        """更新下載進度"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)

            current_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.status_label.setText(
                f"⬇️ 正在下載: {current_mb:.1f} MB / {total_mb:.1f} MB ({percentage}%)"
            )

    def on_download_finished(self, download_path: str):
        """下載完成"""
        self.downloaded_path = download_path
        self.progress_bar.setValue(100)
        self.status_label.setText("✅ 下載完成！")

        # 修改按鈕
        self.skip_button.setEnabled(True)
        self.skip_button.setText("稍後安裝")

        self.download_button.setText("立即安裝")
        self.download_button.setEnabled(True)
        self.download_button.clicked.disconnect()
        self.download_button.clicked.connect(self.install_update)

    def on_download_failed(self, error_msg: str):
        """下載失敗"""
        self.status_label.setText(f"❌ 下載失敗: {error_msg}")
        self.download_button.setEnabled(True)
        self.skip_button.setEnabled(True)

    def install_update(self):
        """安裝更新"""
        if self.downloaded_path:
            from pathlib import Path
            if self.updater.install_update(Path(self.downloaded_path)):
                # 安裝程序已啟動，退出應用
                import sys
                sys.exit(0)
            else:
                self.status_label.setText("❌ 啟動安裝程序失敗")

    def closeEvent(self, event):
        """關閉事件"""
        if self.download_thread and self.download_thread.isRunning():
            # 如果正在下載，提示用戶
            event.ignore()
        else:
            event.accept()
