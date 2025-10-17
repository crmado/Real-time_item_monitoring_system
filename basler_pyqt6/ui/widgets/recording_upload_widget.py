"""
問題回報錄製與上傳組件
用於開發測試期間錄製影像並上傳回報問題
"""

import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Set

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QProgressBar, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor

# 導入錄製器
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.video_recorder import VideoRecorder

logger = logging.getLogger(__name__)


class UploadWorker(QThread):
    """上傳工作執行緒（模擬上傳過程）"""

    progress_updated = pyqtSignal(int)  # 進度更新 (0-100)
    upload_finished = pyqtSignal(bool, str)  # (是否成功, 訊息)

    def __init__(self, file_path: Path, upload_url: str = ""):
        super().__init__()
        self.file_path = file_path
        self.upload_url = upload_url
        self._is_cancelled = False

    def run(self):
        """執行上傳（這裡是模擬，實際需要實作真正的上傳邏輯）"""
        try:
            import time

            # 模擬上傳過程
            file_size = self.file_path.stat().st_size
            chunk_size = file_size // 10  # 分成10個chunk

            for i in range(10):
                if self._is_cancelled:
                    self.upload_finished.emit(False, "上傳已取消")
                    return

                time.sleep(0.3)  # 模擬網路延遲
                progress = (i + 1) * 10
                self.progress_updated.emit(progress)

            # TODO: 這裡應該實作真正的上傳邏輯
            # 例如使用 requests 上傳到指定伺服器
            # response = requests.post(self.upload_url, files={'video': open(self.file_path, 'rb')})

            self.upload_finished.emit(True, "上傳成功")

        except Exception as e:
            logger.error(f"上傳失敗: {str(e)}")
            self.upload_finished.emit(False, f"上傳失敗: {str(e)}")

    def cancel(self):
        """取消上傳"""
        self._is_cancelled = True


class RecordingUploadWidget(QWidget):
    """問題回報錄製與上傳組件"""

    # 信號
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(dict)  # 錄製資訊

    def __init__(self, parent=None):
        super().__init__(parent)

        # 錄製目錄（問題回報專用）
        self.recordings_dir = Path(__file__).parent.parent.parent / "testData" / "issue_recordings"
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

        # 上傳狀態記錄檔案
        self.upload_status_file = self.recordings_dir / "upload_status.json"
        self.uploaded_files: Set[str] = self.load_upload_status()

        # 錄製器
        self.recorder = VideoRecorder(str(self.recordings_dir))
        self.is_recording = False

        # 上傳工作執行緒
        self.upload_worker: Optional[UploadWorker] = None

        # 當前幀（從主視窗傳入）
        self.current_frame = None
        self.frame_size = (640, 480)  # 預設值，會從實際幀更新
        self.fps = 30.0  # 預設值，會從實際幀更新

        self.init_ui()
        self.refresh_video_list()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # === 錄製控制 ===
        record_group = QGroupBox("🎥 錄製控制")
        record_layout = QVBoxLayout()

        # 名稱輸入
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("錄製名稱:"))

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("輸入錄製名稱（可選，自動加時間戳）")
        name_layout.addWidget(self.name_input)
        record_layout.addLayout(name_layout)

        # 狀態顯示
        self.record_status_label = QLabel("⚪ 未錄製")
        self.record_status_label.setStyleSheet("""
            color: #888;
            font-weight: bold;
            font-size: 11pt;
            padding: 5px;
            background-color: rgba(136, 136, 136, 0.1);
            border-radius: 3px;
        """)
        record_layout.addWidget(self.record_status_label)

        # 錄製資訊
        self.record_info_label = QLabel("幀數: 0 | 時長: 0.0s")
        self.record_info_label.setStyleSheet("color: #00d4ff; font-size: 10pt;")
        record_layout.addWidget(self.record_info_label)

        # 錄製按鈕
        btn_layout = QHBoxLayout()
        self.start_record_btn = QPushButton("⏺️ 開始錄製")
        self.start_record_btn.clicked.connect(self.start_recording)
        self.start_record_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:disabled {
                background-color: #6b7280;
            }
        """)

        self.stop_record_btn = QPushButton("⏹️ 停止錄製")
        self.stop_record_btn.clicked.connect(self.stop_recording)
        self.stop_record_btn.setEnabled(False)
        self.stop_record_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: #6b7280;
            }
        """)

        btn_layout.addWidget(self.start_record_btn)
        btn_layout.addWidget(self.stop_record_btn)
        record_layout.addLayout(btn_layout)

        record_group.setLayout(record_layout)
        layout.addWidget(record_group)

        # === 影像列表 ===
        list_group = QGroupBox("📁 已錄製影像")
        list_layout = QVBoxLayout()

        # 列表控制按鈕
        list_control_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 重新整理")
        refresh_btn.clicked.connect(self.refresh_video_list)

        open_folder_btn = QPushButton("📂 開啟資料夾")
        open_folder_btn.clicked.connect(self.open_recordings_folder)

        list_control_layout.addWidget(refresh_btn)
        list_control_layout.addWidget(open_folder_btn)
        list_layout.addLayout(list_control_layout)

        # 影像列表
        self.video_list_widget = QListWidget()
        self.video_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1a1a2e;
                border: 1px solid #00d4ff;
                border-radius: 4px;
                color: #fff;
                font-size: 10pt;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #333;
            }
            QListWidget::item:selected {
                background-color: #00d4ff;
                color: #000;
            }
        """)
        list_layout.addWidget(self.video_list_widget)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        # === 上傳控制 ===
        upload_group = QGroupBox("☁️ 上傳回報")
        upload_layout = QVBoxLayout()

        # 上傳按鈕
        upload_btn_layout = QHBoxLayout()
        self.upload_btn = QPushButton("📤 上傳選取的影像")
        self.upload_btn.clicked.connect(self.upload_selected_video)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:disabled {
                background-color: #6b7280;
            }
        """)
        upload_btn_layout.addWidget(self.upload_btn)
        upload_layout.addLayout(upload_btn_layout)

        # 上傳進度
        progress_layout = QVBoxLayout()
        self.upload_status_label = QLabel("等待上傳...")
        self.upload_status_label.setStyleSheet("color: #888; font-size: 10pt;")
        progress_layout.addWidget(self.upload_status_label)

        self.upload_progress = QProgressBar()
        self.upload_progress.setVisible(False)
        self.upload_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #00d4ff;
                border-radius: 4px;
                text-align: center;
                color: white;
                background-color: #1a1a2e;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.upload_progress)
        upload_layout.addLayout(progress_layout)

        # 上傳說明
        upload_hint = QLabel(
            "💡 上傳說明:\n"
            "• 選擇影像後點擊上傳按鈕\n"
            "• 已上傳的影像會標記為綠色\n"
            "• 重複上傳會提示確認"
        )
        upload_hint.setStyleSheet("""
            color: #9ca3af;
            font-size: 9pt;
            padding: 10px;
            background-color: rgba(74, 85, 104, 0.3);
            border-radius: 4px;
        """)
        upload_hint.setWordWrap(True)
        upload_layout.addWidget(upload_hint)

        upload_group.setLayout(upload_layout)
        layout.addWidget(upload_group)

        layout.addStretch()

    def start_recording(self):
        """開始錄製"""
        if self.is_recording:
            logger.warning("錄製已在進行中")
            return

        # 檢查是否有當前幀（用於獲取實際參數）
        if self.current_frame is not None:
            # 從當前幀更新實際的 frame_size
            height, width = self.current_frame.shape[:2]
            self.frame_size = (width, height)
            logger.info(f"從當前幀更新錄製參數: {self.frame_size}")
        else:
            logger.warning(f"無當前幀，使用預設參數: {self.frame_size}")

        # 生成檔案名
        custom_name = self.name_input.text().strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if custom_name:
            filename = f"{custom_name}_{timestamp}"
        else:
            filename = f"test_recording_{timestamp}"

        # 開始錄製
        success = self.recorder.start_recording(
            frame_size=self.frame_size,
            fps=self.fps,
            filename=filename
        )

        if success:
            self.is_recording = True
            self.start_record_btn.setEnabled(False)
            self.stop_record_btn.setEnabled(True)
            self.name_input.setEnabled(False)

            self.record_status_label.setText("🔴 錄製中...")
            self.record_status_label.setStyleSheet("""
                color: #ef4444;
                font-weight: bold;
                font-size: 11pt;
                padding: 5px;
                background-color: rgba(239, 68, 68, 0.1);
                border-radius: 3px;
            """)

            self.recording_started.emit()
            logger.info(f"✅ 開始錄製: {filename}")
        else:
            QMessageBox.warning(self, "錄製失敗", "無法啟動錄製，請檢查設定")

    def stop_recording(self):
        """停止錄製"""
        if not self.is_recording:
            return

        # 停止錄製
        recording_info = self.recorder.stop_recording()

        self.is_recording = False
        self.start_record_btn.setEnabled(True)
        self.stop_record_btn.setEnabled(False)
        self.name_input.setEnabled(True)
        self.name_input.clear()

        self.record_status_label.setText("⚪ 未錄製")
        self.record_status_label.setStyleSheet("""
            color: #888;
            font-weight: bold;
            font-size: 11pt;
            padding: 5px;
            background-color: rgba(136, 136, 136, 0.1);
            border-radius: 3px;
        """)
        self.record_info_label.setText("幀數: 0 | 時長: 0.0s")

        self.recording_stopped.emit(recording_info)

        # 重新整理列表
        self.refresh_video_list()

        logger.info(f"✅ 錄製完成: {recording_info}")

    def write_frame(self, frame):
        """寫入錄製幀（從主視窗調用）"""
        import cv2

        # 保存當前幀（用於開始錄製時獲取參數）
        if frame is not None:
            self.current_frame = frame

        # 如果正在錄製，寫入幀
        if self.is_recording and frame is not None:
            # 確保幀是BGR格式（OpenCV標準，與主視窗一致）
            if len(frame.shape) == 2:  # 灰度圖
                recording_frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            else:
                recording_frame = frame

            self.recorder.write_frame(recording_frame)

            # 更新狀態
            status = self.recorder.get_recording_status()
            self.record_info_label.setText(
                f"幀數: {status['frames_recorded']} | 時長: {status['duration']:.1f}s"
            )

    def refresh_video_list(self):
        """重新整理影像列表"""
        self.video_list_widget.clear()

        # 列出所有 MP4 檔案
        video_files = sorted(
            self.recordings_dir.glob("*.mp4"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        for video_path in video_files:
            # 檔案資訊
            file_size = video_path.stat().st_size / (1024 * 1024)  # MB
            file_hash = self.get_file_hash(video_path)
            is_uploaded = file_hash in self.uploaded_files

            # 建立列表項目
            item_text = f"{video_path.name} ({file_size:.1f} MB)"
            if is_uploaded:
                item_text += " ✅ 已上傳"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, str(video_path))

            # 設定顏色
            if is_uploaded:
                item.setForeground(QColor("#10b981"))  # 綠色
            else:
                item.setForeground(QColor("#00d4ff"))  # 藍色

            self.video_list_widget.addItem(item)

        logger.info(f"已載入 {len(video_files)} 個影像檔案")

    def upload_selected_video(self):
        """上傳選取的影像"""
        current_item = self.video_list_widget.currentItem()

        if not current_item:
            QMessageBox.warning(self, "未選擇", "請先選擇要上傳的影像")
            return

        video_path = Path(current_item.data(Qt.ItemDataRole.UserRole))
        file_hash = self.get_file_hash(video_path)

        # 檢查是否重複上傳
        if file_hash in self.uploaded_files:
            reply = QMessageBox.question(
                self,
                "重複上傳確認",
                f"影像 {video_path.name} 已經上傳過，確定要再次上傳嗎？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

        # 開始上傳
        self.start_upload(video_path, file_hash)

    def start_upload(self, video_path: Path, file_hash: str):
        """開始上傳"""
        # TODO: 設定實際的上傳 URL
        upload_url = "http://your-upload-server.com/upload"

        # 禁用上傳按鈕
        self.upload_btn.setEnabled(False)

        # 顯示進度條
        self.upload_progress.setVisible(True)
        self.upload_progress.setValue(0)
        self.upload_status_label.setText(f"正在上傳: {video_path.name}")

        # 建立上傳執行緒
        self.upload_worker = UploadWorker(video_path, upload_url)
        self.upload_worker.progress_updated.connect(self.on_upload_progress)
        self.upload_worker.upload_finished.connect(
            lambda success, msg: self.on_upload_finished(success, msg, file_hash)
        )
        self.upload_worker.start()

        logger.info(f"開始上傳: {video_path.name}")

    def on_upload_progress(self, progress: int):
        """上傳進度更新"""
        self.upload_progress.setValue(progress)

    def on_upload_finished(self, success: bool, message: str, file_hash: str):
        """上傳完成"""
        self.upload_btn.setEnabled(True)
        self.upload_progress.setVisible(False)

        if success:
            self.upload_status_label.setText(f"✅ {message}")
            self.upload_status_label.setStyleSheet("color: #10b981; font-size: 10pt;")

            # 記錄為已上傳
            self.uploaded_files.add(file_hash)
            self.save_upload_status()

            # 重新整理列表
            self.refresh_video_list()

            QMessageBox.information(self, "上傳成功", message)
        else:
            self.upload_status_label.setText(f"❌ {message}")
            self.upload_status_label.setStyleSheet("color: #ef4444; font-size: 10pt;")

            QMessageBox.critical(self, "上傳失敗", message)

        logger.info(f"上傳結果: {message}")

    def open_recordings_folder(self):
        """開啟錄製資料夾"""
        import subprocess
        import platform

        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(self.recordings_dir)])
            elif platform.system() == "Windows":
                subprocess.run(["explorer", str(self.recordings_dir)])
            else:  # Linux
                subprocess.run(["xdg-open", str(self.recordings_dir)])
        except Exception as e:
            logger.error(f"無法開啟資料夾: {str(e)}")

    def get_file_hash(self, file_path: Path) -> str:
        """計算檔案 MD5 雜湊值"""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def load_upload_status(self) -> Set[str]:
        """載入上傳狀態"""
        if self.upload_status_file.exists():
            try:
                with open(self.upload_status_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('uploaded_files', []))
            except Exception as e:
                logger.error(f"載入上傳狀態失敗: {str(e)}")
        return set()

    def save_upload_status(self):
        """儲存上傳狀態"""
        try:
            with open(self.upload_status_file, 'w') as f:
                json.dump({
                    'uploaded_files': list(self.uploaded_files),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"儲存上傳狀態失敗: {str(e)}")

    def cleanup(self):
        """清理資源"""
        if self.is_recording:
            self.stop_recording()

        if self.upload_worker and self.upload_worker.isRunning():
            self.upload_worker.cancel()
            self.upload_worker.wait()
