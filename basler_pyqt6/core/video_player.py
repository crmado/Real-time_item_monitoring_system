"""
視頻播放器 - 用於測試模式（無需實體相機）
"""

import cv2
import logging
import threading
import time
from pathlib import Path
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class VideoPlayer:
    """視頻文件播放器 - 模擬相機輸入"""

    def __init__(self):
        self.video_capture: Optional[cv2.VideoCapture] = None
        self.is_playing = False
        self.video_path: Optional[str] = None

        # 線程控制
        self.play_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        # 幀數據
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()

        # 視頻信息
        self.total_frames = 0
        self.current_frame_index = 0
        self.fps = 30.0
        self.frame_count = 0

        logger.info("✅ 視頻播放器初始化完成")

    def load_video(self, video_path: str) -> bool:
        """加載視頻文件"""
        try:
            if not Path(video_path).exists():
                logger.error(f"❌ 視頻文件不存在: {video_path}")
                return False

            self.video_path = video_path
            self.video_capture = cv2.VideoCapture(video_path)

            if not self.video_capture.isOpened():
                logger.error("❌ 無法打開視頻文件")
                return False

            # 獲取視頻信息
            self.frame_count = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.video_capture.get(cv2.CAP_PROP_FPS)

            logger.info(f"✅ 視頻加載成功: {Path(video_path).name}")
            logger.info(f"   總幀數: {self.frame_count}, FPS: {self.fps}")
            return True

        except Exception as e:
            logger.error(f"❌ 加載視頻失敗: {str(e)}")
            return False

    def start_playing(self, loop: bool = True) -> bool:
        """開始播放"""
        if not self.video_capture:
            logger.error("❌ 未加載視頻文件")
            return False

        if self.is_playing:
            logger.warning("⚠️ 已在播放中")
            return True

        try:
            self.is_playing = True
            self.current_frame_index = 0
            self.total_frames = 0

            # 啟動播放線程
            self.stop_event.clear()
            self.play_thread = threading.Thread(
                target=self._play_loop,
                args=(loop,),
                daemon=True
            )
            self.play_thread.start()

            logger.info("✅ 開始視頻播放")
            return True

        except Exception as e:
            logger.error(f"❌ 開始播放失敗: {str(e)}")
            return False

    def _play_loop(self, loop: bool):
        """播放循環"""
        while not self.stop_event.is_set() and self.is_playing:
            try:
                ret, frame = self.video_capture.read()

                if not ret:
                    if loop:
                        # 循環播放
                        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        self.current_frame_index = 0
                        logger.info("🔄 視頻循環播放")
                        continue
                    else:
                        # 停止播放
                        logger.info("⏹️ 視頻播放完畢")
                        self.is_playing = False
                        break

                with self.frame_lock:
                    self.latest_frame = frame.copy()

                self.current_frame_index += 1
                self.total_frames += 1

                # 控制播放速度
                time.sleep(1.0 / self.fps)

            except Exception as e:
                if not self.stop_event.is_set():
                    logger.error(f"❌ 播放錯誤: {str(e)}")
                time.sleep(0.01)

    def stop_playing(self):
        """停止播放"""
        if not self.is_playing:
            return

        self.stop_event.set()
        self.is_playing = False

        if self.play_thread:
            self.play_thread.join(timeout=2)

        logger.info("✅ 停止視頻播放")

    def get_frame(self) -> Optional[np.ndarray]:
        """獲取當前幀"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def release(self):
        """釋放資源"""
        self.stop_playing()

        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None

        logger.info("✅ 視頻資源已釋放")

    def get_progress(self) -> float:
        """獲取播放進度（0-1）"""
        if self.frame_count == 0:
            return 0.0
        return self.current_frame_index / self.frame_count

    def seek(self, frame_index: int):
        """跳轉到指定幀"""
        if self.video_capture and 0 <= frame_index < self.frame_count:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            self.current_frame_index = frame_index
