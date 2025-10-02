"""
視頻錄製器 - PyQt6 版本
簡化版本的工業相機錄製功能
"""

import cv2
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class VideoRecorder:
    """視頻錄製器"""

    def __init__(self, output_dir: str = "recordings"):
        """初始化錄製器

        Args:
            output_dir: 錄製文件輸出目錄
        """
        self.output_path = Path(output_dir)
        self.output_path.mkdir(exist_ok=True)

        self.is_recording = False
        self.video_writer: Optional[cv2.VideoWriter] = None
        self.current_filename = None
        self.frames_recorded = 0
        self.recording_start_time = None

        # 錄製參數
        self.fps = 30.0  # 預設FPS
        self.codec_name = None

        logger.info(f"✅ 視頻錄製器初始化完成，輸出目錄: {self.output_path}")

    def start_recording(
        self,
        frame_size: tuple = (640, 480),
        fps: float = 30.0,
        filename: str = None
    ) -> bool:
        """開始錄製

        Args:
            frame_size: 幀尺寸 (width, height)
            fps: 錄製幀率
            filename: 自定義文件名（不含副檔名）

        Returns:
            bool: 是否成功開始錄製
        """
        if self.is_recording:
            logger.warning("錄製已在進行中")
            return False

        try:
            # 生成文件名
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recording_{timestamp}"

            self.current_filename = filename
            self.fps = fps

            # 嘗試不同的編碼器
            codecs_to_try = [
                ('mp4v', cv2.VideoWriter_fourcc(*'mp4v'), '.mp4'),  # 高品質
                ('MJPG', cv2.VideoWriter_fourcc(*'MJPG'), '.avi'),  # 穩定
                ('XVID', cv2.VideoWriter_fourcc(*'XVID'), '.avi')   # 備用
            ]

            for codec_name, codec_fourcc, extension in codecs_to_try:
                try:
                    filepath = self.output_path / f"{filename}{extension}"

                    self.video_writer = cv2.VideoWriter(
                        str(filepath),
                        codec_fourcc,
                        fps,
                        frame_size
                    )

                    if self.video_writer.isOpened():
                        self.codec_name = codec_name
                        logger.info(f"✅ 使用 {codec_name} 編碼器")
                        logger.info(f"📊 錄製參數: {frame_size[0]}x{frame_size[1]} @ {fps:.1f}fps")
                        logger.info(f"📁 錄製文件: {filepath}")
                        break
                    else:
                        self.video_writer = None

                except Exception as e:
                    logger.warning(f"⚠️ {codec_name} 編碼器失敗: {str(e)}")
                    self.video_writer = None

            if not self.video_writer or not self.video_writer.isOpened():
                logger.error("❌ 所有編碼器都失敗")
                return False

            self.is_recording = True
            self.frames_recorded = 0
            self.recording_start_time = datetime.now()

            logger.info(f"🎬 開始錄製: {filename}")
            return True

        except Exception as e:
            logger.error(f"錄製啟動失敗: {str(e)}")
            return False

    def write_frame(self, frame: np.ndarray) -> bool:
        """寫入一幀

        Args:
            frame: 要寫入的幀

        Returns:
            bool: 是否成功寫入
        """
        if not self.is_recording or self.video_writer is None:
            return False

        try:
            self.video_writer.write(frame)
            self.frames_recorded += 1
            return True

        except Exception as e:
            logger.error(f"寫入幀失敗: {str(e)}")
            return False

    def stop_recording(self) -> dict:
        """停止錄製

        Returns:
            dict: 錄製信息
        """
        if not self.is_recording:
            return {}

        try:
            self.is_recording = False

            # 計算錄製時長
            if self.recording_start_time:
                duration = (datetime.now() - self.recording_start_time).total_seconds()
            else:
                duration = 0.0

            # 釋放寫入器
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None

            # 計算平均FPS
            average_fps = self.frames_recorded / duration if duration > 0 else 0

            recording_info = {
                'filename': self.current_filename,
                'frames_recorded': self.frames_recorded,
                'duration': duration,
                'average_fps': average_fps,
                'codec': self.codec_name
            }

            logger.info(f"✅ 錄製完成: {self.current_filename}")
            logger.info(f"📊 錄製統計: {self.frames_recorded} 幀, {duration:.2f} 秒")
            logger.info(f"🎯 平均幀率: {average_fps:.1f} fps")

            return recording_info

        except Exception as e:
            logger.error(f"停止錄製失敗: {str(e)}")
            return {}

    def get_recording_status(self) -> dict:
        """獲取錄製狀態

        Returns:
            dict: 狀態信息
        """
        duration = 0.0
        if self.is_recording and self.recording_start_time:
            duration = (datetime.now() - self.recording_start_time).total_seconds()

        return {
            'is_recording': self.is_recording,
            'filename': self.current_filename,
            'frames_recorded': self.frames_recorded,
            'duration': duration,
            'fps': self.fps
        }

    def cleanup(self):
        """清理資源"""
        if self.is_recording:
            self.stop_recording()

        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None

        logger.info("✅ 錄製器資源已清理")
