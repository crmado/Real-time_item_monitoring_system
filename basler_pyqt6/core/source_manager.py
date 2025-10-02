"""
源管理器 - 統一管理相機和視頻輸入
"""

import logging
from typing import Optional
import numpy as np
from enum import Enum

from basler_pyqt6.core.camera import CameraController
from basler_pyqt6.core.video_player import VideoPlayer

logger = logging.getLogger(__name__)


class SourceType(str, Enum):
    """源類型"""
    CAMERA = "camera"
    VIDEO = "video"
    NONE = "none"


class SourceManager:
    """統一的源管理器"""

    def __init__(self):
        self.source_type = SourceType.NONE
        self.camera_controller: Optional[CameraController] = None
        self.video_player: Optional[VideoPlayer] = None

        logger.info("✅ 源管理器初始化完成")

    def use_camera(self) -> CameraController:
        """切換到相機模式"""
        self._cleanup_current_source()

        self.camera_controller = CameraController()
        self.source_type = SourceType.CAMERA

        logger.info("📷 切換到相機模式")
        return self.camera_controller

    def use_video(self, video_path: str) -> bool:
        """切換到視頻模式"""
        self._cleanup_current_source()

        self.video_player = VideoPlayer()
        if self.video_player.load_video(video_path):
            self.source_type = SourceType.VIDEO
            logger.info(f"🎬 切換到視頻模式: {video_path}")
            return True
        else:
            self.video_player = None
            self.source_type = SourceType.NONE
            return False

    def get_frame(self) -> Optional[np.ndarray]:
        """獲取當前幀"""
        if self.source_type == SourceType.CAMERA and self.camera_controller:
            return self.camera_controller.get_frame()
        elif self.source_type == SourceType.VIDEO and self.video_player:
            return self.video_player.get_frame()
        return None

    def get_fps(self) -> float:
        """獲取 FPS"""
        if self.source_type == SourceType.CAMERA and self.camera_controller:
            return self.camera_controller.current_fps
        elif self.source_type == SourceType.VIDEO and self.video_player:
            return self.video_player.fps
        return 0.0

    def is_active(self) -> bool:
        """檢查源是否活躍"""
        if self.source_type == SourceType.CAMERA and self.camera_controller:
            return self.camera_controller.is_grabbing
        elif self.source_type == SourceType.VIDEO and self.video_player:
            return self.video_player.is_playing
        return False

    def _cleanup_current_source(self):
        """清理當前源"""
        if self.camera_controller:
            self.camera_controller.cleanup()
            self.camera_controller = None

        if self.video_player:
            self.video_player.release()
            self.video_player = None

        self.source_type = SourceType.NONE

    def cleanup(self):
        """清理所有資源"""
        self._cleanup_current_source()
        logger.info("✅ 源管理器資源已清理")
