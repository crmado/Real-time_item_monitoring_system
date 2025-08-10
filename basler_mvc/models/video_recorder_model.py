"""
視頻錄製模型 - MVC 架構核心
專注於工業相機視頻錄製的數據管理
"""

import cv2
import numpy as np
import threading
import time
import logging
from typing import Optional, Callable
from pathlib import Path
from datetime import datetime

class VideoRecorderModel:
    """視頻錄製數據模型"""
    
    def __init__(self):
        """初始化錄製模型"""
        self.is_recording = False
        self.video_writer = None
        self.recording_lock = threading.Lock()
        
        # 錄製參數
        self.output_path = Path("recordings")
        self.fps = 30  # 預設FPS（將從相機動態獲取實際配置）
        self.camera_configured_fps = None  # 儲存相機配置的FPS
        
        # 🔧 使用更可靠的編碼器 - MP4V 比 XVID 更通用
        self.codec = cv2.VideoWriter_fourcc(*'mp4v')
        self.current_filename = None
        self.frames_recorded = 0
        
        # 錄製統計
        self.recording_start_time = None
        self.recording_duration = 0.0
        
        # 觀察者模式
        self.observers = []
        
        # 確保錄製目錄存在
        self.output_path.mkdir(exist_ok=True)
        
        logging.info("視頻錄製模型初始化完成")
        
    def add_observer(self, observer: Callable):
        """添加觀察者"""
        self.observers.append(observer)
    
    def notify_observers(self, event_type: str, data=None):
        """通知觀察者"""
        for observer in self.observers:
            try:
                observer(event_type, data)
            except Exception as e:
                logging.error(f"通知觀察者錯誤: {str(e)}")
    
    def set_camera_fps(self, camera_fps: float):
        """設定來自相機的配置FPS"""
        if camera_fps > 0:
            self.camera_configured_fps = camera_fps
            logging.info(f"🎯 錄製器接收到相機配置FPS: {camera_fps:.1f}")
        else:
            logging.warning("⚠️ 接收到無效的相機FPS，使用預設值")
        
    def start_recording(self, filename: str = None, frame_size: tuple = None, fps: float = None) -> bool:
        """開始錄製 - 支持動態幀率"""
        with self.recording_lock:
            if self.is_recording:
                logging.warning("錄製已在進行中")
                return False
                
            try:
                # 生成檔名
                if filename is None:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"camera_recording_{timestamp}"
                
                self.current_filename = filename
                filepath = self.output_path / f"{filename}.avi"
                
                # 預設幀尺寸
                if frame_size is None:
                    frame_size = (640, 480)
                
                # 🎯 動態FPS選擇策略：優先相機配置 → 實際測量 → 預設值
                if fps is not None and fps > 0:
                    # 1. 優先使用傳入的實際測量FPS
                    actual_fps = fps
                    fps_source = f"實際測量: {fps:.1f}"
                elif self.camera_configured_fps is not None and self.camera_configured_fps > 0:
                    # 2. 使用相機配置的FPS
                    actual_fps = self.camera_configured_fps
                    fps_source = f"相機配置: {self.camera_configured_fps:.1f}"
                else:
                    # 3. 最後使用預設值
                    actual_fps = self.fps
                    fps_source = f"預設值: {self.fps:.1f}"
                
                # 🔧 工業相機幀率驗證與警告
                if actual_fps < 60:
                    logging.warning(f"⚠️  檢測到低幀率錄製: {actual_fps:.1f} fps - 可能不適合工業相機高速監控")
                elif actual_fps > 300:
                    logging.warning(f"⚠️  檢測到超高幀率: {actual_fps:.1f} fps - 可能導致檔案過大")
                
                self.fps = actual_fps  # 更新當前錄製幀率
                
                logging.info(f"🎬 開始工業相機錄製 - FPS: {actual_fps:.1f} ({fps_source}), 尺寸: {frame_size}")
                
                # 創建視頻寫入器 - 帶備用編碼器
                self.video_writer = cv2.VideoWriter(
                    str(filepath), self.codec, actual_fps, frame_size
                )
                
                if not self.video_writer.isOpened():
                    logging.warning(f"主要編碼器 mp4v 失敗，嘗試備用編碼器...")
                    
                    # 🔧 嘗試 XVID 編碼器
                    backup_codec = cv2.VideoWriter_fourcc(*'XVID')
                    self.video_writer = cv2.VideoWriter(
                        str(filepath), backup_codec, actual_fps, frame_size
                    )
                    
                    if not self.video_writer.isOpened():
                        logging.warning(f"XVID 編碼器也失敗，嘗試 MJPG...")
                        
                        # 🔧 嘗試 MJPG 編碼器（通常更可靠）
                        mjpg_codec = cv2.VideoWriter_fourcc(*'MJPG')
                        self.video_writer = cv2.VideoWriter(
                            str(filepath), mjpg_codec, actual_fps, frame_size
                        )
                        
                        if not self.video_writer.isOpened():
                            logging.error("所有編碼器都失敗，無法創建視頻寫入器")
                            logging.error(f"嘗試的編碼器: mp4v, XVID, MJPG")
                            logging.error(f"參數: FPS={actual_fps}, 尺寸={frame_size}")
                            return False
                        else:
                            logging.info("✅ 使用 MJPG 編碼器成功")
                            self.codec = mjpg_codec  # 記錄成功的編碼器
                    else:
                        logging.info("✅ 使用 XVID 編碼器成功")
                        self.codec = backup_codec  # 記錄成功的編碼器
                else:
                    logging.info("✅ 使用 mp4v 編碼器成功")
                
                self.is_recording = True
                self.frames_recorded = 0
                self.recording_start_time = time.time()
                
                self.notify_observers('recording_started', {
                    'filename': filename,
                    'filepath': str(filepath),
                    'frame_size': frame_size
                })
                
                logging.info(f"開始錄製: {filepath}")
                return True
                
            except Exception as e:
                logging.error(f"錄製啟動失敗: {str(e)}")
                return False
    
    def write_frame(self, frame: np.ndarray) -> bool:
        """寫入幀"""
        if not self.is_recording or self.video_writer is None:
            return False
            
        try:
            with self.recording_lock:
                self.video_writer.write(frame)
                self.frames_recorded += 1
                
                # 計算錄製時長
                if self.recording_start_time:
                    self.recording_duration = time.time() - self.recording_start_time
                
                # 定期通知錄製進度
                if self.frames_recorded % 100 == 0:
                    self.notify_observers('recording_progress', {
                        'frames_recorded': self.frames_recorded,
                        'duration': self.recording_duration,
                        'fps': self.frames_recorded / self.recording_duration if self.recording_duration > 0 else 0
                    })
                
            return True
            
        except Exception as e:
            logging.error(f"寫入幀失敗: {str(e)}")
            return False
    
    def stop_recording(self) -> dict:
        """停止錄製並返回錄製信息"""
        with self.recording_lock:
            if not self.is_recording:
                return {}
                
            try:
                self.is_recording = False
                final_duration = time.time() - self.recording_start_time if self.recording_start_time else 0
                
                if self.video_writer:
                    self.video_writer.release()
                    self.video_writer = None
                
                recording_info = {
                    'filename': self.current_filename,
                    'frames_recorded': self.frames_recorded,
                    'duration': final_duration,
                    'average_fps': self.frames_recorded / final_duration if final_duration > 0 else 0,
                    'filepath': str(self.output_path / f"{self.current_filename}.avi")
                }
                
                self.notify_observers('recording_stopped', recording_info)
                
                logging.info(f"錄製完成: {self.current_filename}, "
                           f"共 {self.frames_recorded} 幀, "
                           f"時長 {final_duration:.2f} 秒")
                
                return recording_info
                
            except Exception as e:
                logging.error(f"停止錄製失敗: {str(e)}")
                return {}
    
    def get_recording_status(self) -> dict:
        """獲取錄製狀態"""
        return {
            'is_recording': self.is_recording,
            'current_filename': self.current_filename,
            'frames_recorded': self.frames_recorded,
            'duration': self.recording_duration,
            'output_path': str(self.output_path)
        }
    
    def get_recorded_files(self) -> list:
        """獲取已錄製的文件列表"""
        try:
            files = []
            for file_path in self.output_path.glob("*.avi"):
                stat = file_path.stat()
                files.append({
                    'filename': file_path.stem,
                    'filepath': str(file_path),
                    'size': stat.st_size,
                    'created_time': datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # 按創建時間排序
            files.sort(key=lambda x: x['created_time'], reverse=True)
            return files
            
        except Exception as e:
            logging.error(f"獲取錄製文件列表失敗: {str(e)}")
            return []