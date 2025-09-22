#!/usr/bin/env python3
"""
錄製驗證器
簡化的280 FPS錄製檔案驗證工具，整合到MVC架構中
"""

import cv2
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class RecordingInfo:
    """錄製檔案資訊"""
    file_path: str
    file_name: str
    fps: float
    frame_count: int
    duration: float
    width: int
    height: int
    codec: str
    file_size_mb: float
    is_valid_fps: bool
    fps_error_percent: float

class RecordingValidator:
    """錄製驗證器 - 專門檢查280 FPS錄製品質"""
    
    def __init__(self, expected_fps: int = 280, tolerance_percent: float = 5.0):
        """
        初始化錄製驗證器
        
        Args:
            expected_fps: 預期的FPS值 (預設280)
            tolerance_percent: 容許誤差百分比 (預設5%)
        """
        self.expected_fps = expected_fps
        self.tolerance_percent = tolerance_percent
        self.logger = logging.getLogger(__name__)
        
    def validate_recording(self, video_path: Path) -> Optional[RecordingInfo]:
        """
        驗證單個錄製檔案
        
        Args:
            video_path: 視頻檔案路徑
            
        Returns:
            RecordingInfo: 錄製檔案資訊，如果驗證失敗則返回None
        """
        try:
            if not video_path.exists():
                self.logger.error(f"檔案不存在: {video_path}")
                return None
                
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                self.logger.error(f"無法開啟視頻檔案: {video_path}")
                return None
                
            # 獲取視頻資訊
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            
            cap.release()
            
            # 計算其他資訊
            duration = frame_count / fps if fps > 0 else 0
            fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
            file_size_mb = video_path.stat().st_size / (1024 * 1024)
            
            # 計算FPS誤差
            fps_error_percent = abs(fps - self.expected_fps) / self.expected_fps * 100
            is_valid_fps = fps_error_percent <= self.tolerance_percent
            
            return RecordingInfo(
                file_path=str(video_path),
                file_name=video_path.name,
                fps=fps,
                frame_count=frame_count,
                duration=duration,
                width=width,
                height=height,
                codec=fourcc_str,
                file_size_mb=file_size_mb,
                is_valid_fps=is_valid_fps,
                fps_error_percent=fps_error_percent
            )
            
        except Exception as e:
            self.logger.error(f"驗證錄製檔案時發生錯誤: {str(e)}")
            return None
    
    def validate_latest_recording(self, recordings_dir: Path) -> Optional[RecordingInfo]:
        """
        驗證最新的錄製檔案
        
        Args:
            recordings_dir: 錄製目錄路徑
            
        Returns:
            RecordingInfo: 最新錄製檔案資訊
        """
        video_files = self._get_video_files(recordings_dir)
        if not video_files:
            self.logger.warning("錄製目錄中沒有找到視頻檔案")
            return None
            
        latest_file = video_files[0]  # 已按修改時間排序
        return self.validate_recording(latest_file)
    
    def validate_all_recordings(self, recordings_dir: Path) -> List[RecordingInfo]:
        """
        驗證所有錄製檔案
        
        Args:
            recordings_dir: 錄製目錄路徑
            
        Returns:
            List[RecordingInfo]: 所有有效錄製檔案的資訊列表
        """
        video_files = self._get_video_files(recordings_dir)
        valid_recordings = []
        
        for video_file in video_files:
            info = self.validate_recording(video_file)
            if info:
                valid_recordings.append(info)
                
        return valid_recordings
    
    def quick_fps_check(self, video_path: Path) -> Tuple[bool, float]:
        """
        快速FPS檢查
        
        Args:
            video_path: 視頻檔案路徑
            
        Returns:
            Tuple[bool, float]: (是否符合預期FPS, 實際FPS值)
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return False, 0.0
                
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            
            fps_error_percent = abs(fps - self.expected_fps) / self.expected_fps * 100
            is_valid = fps_error_percent <= self.tolerance_percent
            
            return is_valid, fps
            
        except Exception as e:
            self.logger.error(f"快速FPS檢查失敗: {str(e)}")
            return False, 0.0
    
    def get_quality_summary(self, recordings: List[RecordingInfo]) -> Dict:
        """
        獲取品質總結
        
        Args:
            recordings: 錄製檔案資訊列表
            
        Returns:
            Dict: 品質總結資訊
        """
        if not recordings:
            return {
                'total_files': 0,
                'valid_fps_files': 0,
                'invalid_fps_files': 0,
                'validity_rate': 0.0,
                'avg_fps': 0.0,
                'fps_range': (0.0, 0.0)
            }
        
        valid_fps_count = sum(1 for r in recordings if r.is_valid_fps)
        invalid_fps_count = len(recordings) - valid_fps_count
        validity_rate = valid_fps_count / len(recordings) * 100
        
        fps_values = [r.fps for r in recordings]
        avg_fps = sum(fps_values) / len(fps_values)
        fps_range = (min(fps_values), max(fps_values))
        
        return {
            'total_files': len(recordings),
            'valid_fps_files': valid_fps_count,
            'invalid_fps_files': invalid_fps_count,
            'validity_rate': validity_rate,
            'avg_fps': avg_fps,
            'fps_range': fps_range
        }
    
    def _get_video_files(self, recordings_dir: Path) -> List[Path]:
        """獲取視頻檔案列表，按修改時間排序"""
        if not recordings_dir.exists():
            return []
            
        video_files = []
        for ext in ['*.avi', '*.mp4', '*.mov']:
            video_files.extend(recordings_dir.glob(ext))
            
        # 按修改時間排序（最新的在前）
        return sorted(video_files, key=lambda x: x.stat().st_mtime, reverse=True)

# 便利函數
def quick_validate_fps(video_path: str, expected_fps: int = 280) -> bool:
    """
    快速驗證檔案FPS是否符合預期
    
    Args:
        video_path: 視頻檔案路徑
        expected_fps: 預期FPS值
        
    Returns:
        bool: 是否符合預期FPS
    """
    validator = RecordingValidator(expected_fps=expected_fps)
    is_valid, _ = validator.quick_fps_check(Path(video_path))
    return is_valid

def validate_latest_280fps_recording(recordings_dir: str = "recordings") -> Optional[RecordingInfo]:
    """
    驗證最新的280fps錄製檔案
    
    Args:
        recordings_dir: 錄製目錄路徑
        
    Returns:
        RecordingInfo: 最新錄製檔案資訊
    """
    validator = RecordingValidator(expected_fps=280)
    return validator.validate_latest_recording(Path(recordings_dir))
