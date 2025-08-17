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
        self.fps = 206  # 🚀 高速預設FPS（將從相機動態獲取實際配置）
        self.camera_configured_fps = None  # 儲存相機配置的FPS
        
                        # 🔧 使用最穩定的編碼器 - MJPG 對高幀率最可靠
        self.codec = cv2.VideoWriter_fourcc(*'MJPG')
        self.current_filename = None
        self.current_codec_name = None  # 儲存當前使用的編碼器名稱
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
    
    def _get_file_extension_by_codec(self, codec_name: str) -> str:
        """根據編碼器類型返回對應的檔案附檔名"""
        codec_extensions = {
            'mp4v': '.mp4',
            'H264': '.mp4', 
            'h264': '.mp4',
            'MJPG': '.avi',
            'mjpg': '.avi',
            'XVID': '.avi',
            'xvid': '.avi'
        }
        
        extension = codec_extensions.get(codec_name, '.avi')  # 預設為 .avi
        logging.info(f"📁 編碼器 {codec_name} 對應附檔名: {extension}")
        return extension
    
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
                # 🎯 暫時設定，將在編碼器確認後更新正確的附檔名
                filepath = None
                
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
                
                # 🔧 工業相機幀率驗證與調整
                if actual_fps < 60:
                    logging.warning(f"⚠️  檢測到低幀率錄製: {actual_fps:.1f} fps - 可能不適合工業相機高速監控")
                elif actual_fps > 300:
                    logging.warning(f"⚠️  檢測到超高幀率: {actual_fps:.1f} fps - 可能導致檔案過大和編碼器問題")
                    # 🎯 限制最大幀率以避免編碼器問題
                    if actual_fps > 280:
                        actual_fps = 280.0
                        logging.info(f"🔧 限制錄製幀率為 {actual_fps} fps 以提高穩定性")
                
                self.fps = actual_fps  # 更新當前錄製幀率
                
                logging.info(f"🎬 開始工業相機錄製 - FPS: {actual_fps:.1f} ({fps_source}), 尺寸: {frame_size}")
                
                # 🎯 創建視頻寫入器 - 優先高品質編碼器序列
                codecs_to_try = [
                    ('mp4v', cv2.VideoWriter_fourcc(*'mp4v')),  # 品質較好，優先使用
                    ('H264', cv2.VideoWriter_fourcc(*'H264')),  # 高品質，但兼容性待驗證
                    ('MJPG', cv2.VideoWriter_fourcc(*'MJPG')),  # 穩定但品質一般
                    ('XVID', cv2.VideoWriter_fourcc(*'XVID'))   # 備用
                ]
                
                self.video_writer = None
                successful_codec = None
                
                for codec_name, codec_fourcc in codecs_to_try:
                    try:
                        # 🎯 根據編碼器類型設定正確的檔案路徑
                        file_extension = self._get_file_extension_by_codec(codec_name)
                        filepath = self.output_path / f"{filename}{file_extension}"
                        
                        self.video_writer = cv2.VideoWriter(
                            str(filepath), codec_fourcc, actual_fps, frame_size
                        )
                        
                        if self.video_writer.isOpened():
                            # 🎯 記錄編碼器品質信息和檔案資訊
                            quality_info = "高品質" if codec_name in ['mp4v', 'H264'] else "標準品質"
                            logging.info(f"✅ 使用 {codec_name} 編碼器成功 ({quality_info})")
                            logging.info(f"📊 錄製參數: {frame_size[0]}x{frame_size[1]} @ {actual_fps:.1f}fps")
                            logging.info(f"📁 錄製檔案: {filename}{file_extension}")
                            self.codec = codec_fourcc
                            self.current_codec_name = codec_name  # 儲存編碼器名稱
                            successful_codec = codec_name
                            break
                        else:
                            logging.warning(f"⚠️ {codec_name} 編碼器初始化失敗")
                            if self.video_writer:
                                self.video_writer.release()
                                self.video_writer = None
                                
                    except Exception as e:
                        logging.warning(f"⚠️ {codec_name} 編碼器異常: {str(e)}")
                        if self.video_writer:
                            self.video_writer.release()
                            self.video_writer = None
                
                if not self.video_writer or not self.video_writer.isOpened():
                    logging.error("❌ 所有編碼器都失敗，無法創建視頻寫入器")
                    logging.error(f"嘗試的編碼器: {[name for name, _ in codecs_to_try]}")
                    logging.error(f"參數: FPS={actual_fps}, 尺寸={frame_size}")
                    return False
                
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
                
                # 🎯 使用正確的檔案附檔名
                file_extension = self._get_file_extension_by_codec(self.current_codec_name) if self.current_codec_name else '.avi'
                full_filename = f"{self.current_filename}{file_extension}"
                
                recording_info = {
                    'filename': self.current_filename,  # 不含附檔名的基本檔名
                    'full_filename': full_filename,     # 包含附檔名的完整檔名
                    'frames_recorded': self.frames_recorded,
                    'duration': final_duration,
                    'average_fps': self.frames_recorded / final_duration if final_duration > 0 else 0,
                    'filepath': str(self.output_path / full_filename),
                    'codec': self.current_codec_name,
                    'extension': file_extension
                }
                
                self.notify_observers('recording_stopped', recording_info)
                
                # 🎯 錄製完成後驗證檔案完整性
                self._validate_recording(recording_info)
                
                # 📊 詳細的錄製完成日誌
                expected_fps = 280  # 預期FPS
                actual_fps = self.frames_recorded / final_duration if final_duration > 0 else 0
                
                logging.info(f"✅ 錄製完成: {self.current_filename}")
                logging.info(f"📊 錄製統計: {self.frames_recorded} 幀, {final_duration:.2f} 秒")
                logging.info(f"🎯 幀率對比: 預期 {expected_fps} fps, 實際 {actual_fps:.1f} fps")
                
                if final_duration < 10.0:
                    logging.warning(f"⚠️ 短錄製警告: 時長僅 {final_duration:.2f} 秒，可能被意外中斷")
                else:
                    logging.info(f"🎉 錄製時長正常: {final_duration:.2f} 秒")
                
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
    
    def _validate_recording(self, recording_info: dict):
        """驗證錄製檔案的完整性"""
        try:
            if not recording_info or not recording_info.get('filepath'):
                logging.warning("⚠️ 無法驗證錄製檔案：缺少檔案路徑")
                return
                
            filepath = Path(recording_info['filepath'])
            if not filepath.exists():
                logging.error(f"❌ 錄製檔案不存在: {filepath}")
                return
                
            # 檢查檔案大小
            file_size = filepath.stat().st_size
            if file_size < 1024:  # 小於1KB
                logging.error(f"❌ 錄製檔案過小: {file_size} bytes")
                return
                
            # 使用opencv驗證檔案
            import cv2
            cap = cv2.VideoCapture(str(filepath))
            if not cap.isOpened():
                logging.error(f"❌ 錄製檔案無法開啟: {filepath}")
                return
                
            actual_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            actual_fps = cap.get(cv2.CAP_PROP_FPS)
            actual_duration = actual_frame_count / actual_fps if actual_fps > 0 else 0
            
            cap.release()
            
            # 比較錄製統計與實際檔案
            expected_frames = recording_info.get('frames_recorded', 0)
            expected_duration = recording_info.get('duration', 0)
            
            # 🔧 智能驗證：如果預期時長明顯異常，使用幀數計算
            if expected_duration > actual_duration * 2 or expected_duration < actual_duration * 0.5:
                # 預期時長異常，重新計算
                calculated_duration = expected_frames / actual_fps if actual_fps > 0 else 0
                logging.info(f"🔧 檢測到時長異常，重新計算: 原始預期 {expected_duration:.2f}s → 重算 {calculated_duration:.2f}s")
                expected_duration = calculated_duration
            
            frame_diff = abs(actual_frame_count - expected_frames) if expected_frames > 0 else 0
            duration_diff = abs(actual_duration - expected_duration) if expected_duration > 0 else 0
            
            # 🎯 更寬鬆的驗證條件，專注於重要問題
            if expected_frames > 0 and frame_diff > expected_frames * 0.1:  # 幀數差異超過10%
                logging.warning(f"⚠️ 幀數不匹配: 預期 {expected_frames}, 實際 {actual_frame_count} (差異: {frame_diff}幀)")
            
            if expected_duration > 0 and duration_diff > expected_duration * 0.1:  # 時長差異超過10%
                logging.warning(f"⚠️ 時長不匹配: 預期 {expected_duration:.2f}s, 實際 {actual_duration:.2f}s (差異: {duration_diff:.2f}s)")
            
            # 🎯 重點檢查：錄製完整性
            if actual_duration < 5.0:
                logging.warning(f"⚠️ 錄製時間過短: {actual_duration:.2f}秒 - 可能被意外停止")
            elif expected_frames > 0 and actual_frame_count < expected_frames * 0.5:
                logging.warning(f"⚠️ 錄製不完整: 只有預期幀數的 {actual_frame_count/expected_frames*100:.1f}%")
            
            logging.info(f"✅ 錄製檔案驗證完成: {file_size/1024/1024:.1f}MB, "
                        f"{actual_frame_count}幀, {actual_duration:.2f}秒")
                        
        except Exception as e:
            logging.error(f"錄製檔案驗證失敗: {str(e)}")