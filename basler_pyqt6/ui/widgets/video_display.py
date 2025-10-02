"""
視頻顯示組件 - 實時顯示相機圖像
"""

import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap


class VideoDisplayWidget(QWidget):
    """視頻顯示組件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 創建圖像顯示標籤
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 2px solid #3d3d3d;
                border-radius: 5px;
            }
        """)
        self.image_label.setText("等待相機連接...")
        self.image_label.setMinimumSize(640, 480)

        layout.addWidget(self.image_label)

    def update_frame(self, frame: np.ndarray):
        """
        更新顯示幀

        Args:
            frame: OpenCV 格式的圖像（numpy array）
        """
        if frame is None:
            return

        try:
            # 轉換顏色空間
            if len(frame.shape) == 2:
                # 灰度圖
                height, width = frame.shape
                bytes_per_line = width
                q_image = QImage(
                    frame.data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format.Format_Grayscale8
                )
            else:
                # 彩色圖（BGR -> RGB）
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channel = frame_rgb.shape
                bytes_per_line = 3 * width
                q_image = QImage(
                    frame_rgb.data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format.Format_RGB888
                )

            # 縮放以適應窗口大小（保持寬高比）
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.image_label.setPixmap(scaled_pixmap)

        except Exception as e:
            print(f"❌ 更新幀錯誤: {str(e)}")

    def clear(self):
        """清空顯示"""
        self.image_label.clear()
        self.image_label.setText("等待相機連接...")
