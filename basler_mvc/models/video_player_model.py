"""
視頻播放模型 - MVC 架構核心
專注於錄製視頻回放的數據管理
"""

import cv2
import numpy as np
import threading
import time
import logging
from typing import Optional, Callable
from pathlib import Path

class VideoPlayerModel:
    """視頻播放數據模型"""
    
    def __init__(self):
        """初始化播放模型"""
        self.video_capture = None
        self.is_playing = False
        self.is_paused = False
        self.playback_thread = None
        self.stop_event = threading.Event()
        
        # 播放控制
        self.current_frame_number = 0
        self.total_frames = 0
        self.fps = None  # 🔧 修正：不設預設值，完全依賴視頻實際FPS
        self.original_fps = None  # 🎯 新增：保存原始視頻FPS
        self.playback_speed = 1.0  # 播放速度倍數
        self.high_speed_detection_mode = True  # 🚀 高速檢測模式：跳過時間同步，盡快處理所有幀
        
        # 當前加載的視頻
        self.current_video_path = None
        self.video_info = {}
        
        # 播放模式
        self.loop_playback = False
        
        # 觀察者模式
        self.observers = []
        
        logging.info("視頻播放模型初始化完成")
        
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
        
    def load_video(self, video_path: str) -> bool:
        """加載視頻"""
        try:
            # 🔧 確保完全重置播放狀態
            if self.is_playing:
                self.stop_playback()
                # 等待播放線程完全停止
                if hasattr(self, 'playback_thread') and self.playback_thread:
                    self.playback_thread.join(timeout=2.0)
            
            # 強制重置所有狀態變量
            self.is_playing = False
            self.is_paused = False
            self.current_frame_number = 0
            
            # 釋放舊的視頻捕獲
            if self.video_capture:
                self.video_capture.release()
                
            # 🔧 針對AVI等格式的兼容性改進
            self.video_capture = cv2.VideoCapture(video_path)
            
            # 嘗試多種後端以提高AVI兼容性
            if not self.video_capture.isOpened():
                logging.warning(f"使用預設後端無法打開視頻，嘗試其他後端: {video_path}")
                self.video_capture.release()
                
                # 嘗試使用FFMPEG後端
                self.video_capture = cv2.VideoCapture(video_path, cv2.CAP_FFMPEG)
                if not self.video_capture.isOpened():
                    logging.error(f"無法打開視頻檔案: {video_path}")
                    logging.error("請確認視頻檔案格式受支援（推薦使用MP4格式）")
                    return False
                else:
                    logging.info("✅ 使用FFMPEG後端成功開啟視頻")
            else:
                logging.info("✅ 使用預設後端成功開啟視頻")
                
            # 獲取視頻信息並進行驗證
            self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            detected_fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 🔧 驗證視頻參數的有效性
            if self.total_frames <= 0:
                logging.error(f"❌ 無效的幀數: {self.total_frames}")
                return False
            
            # 🎯 增強FPS驗證和自動修正
            if detected_fps <= 0 or detected_fps > 300:  # 合理的FPS範圍
                logging.warning(f"⚠️ 檢測到異常FPS: {detected_fps}")
                # 嘗試通過檔案特性推測FPS
                if 'fps' in str(video_path).lower():
                    # 從檔名中提取FPS信息 (例如: video_30fps.mp4)
                    import re
                    fps_match = re.search(r'(\d+)fps', str(video_path).lower())
                    if fps_match:
                        self.fps = float(fps_match.group(1))
                        logging.info(f"🔍 從檔名推測FPS: {self.fps}")
                    else:
                        self.fps = 206.0  # 🚀 高速預設值
                        logging.warning(f"⚠️ 使用高速預設FPS: {self.fps}")
                else:
                    self.fps = 206.0  # 🚀 高速預設值
                    logging.warning(f"⚠️ 使用高速預設FPS: {self.fps}")
            else:
                self.fps = detected_fps
                logging.info(f"✅ 使用視頻實際FPS: {self.fps:.2f}")
            
            # 🎯 保存原始FPS用於檢測參數優化
            self.original_fps = self.fps
            
            if width <= 0 or height <= 0:
                logging.error(f"❌ 無效的解析度: {width}x{height}")
                return False
            
            self.current_frame_number = 0
            self.current_video_path = video_path
            
            # 🎯 獲取視頻編碼信息
            fourcc = self.video_capture.get(cv2.CAP_PROP_FOURCC)
            codec = ''.join([chr((int(fourcc) >> 8 * i) & 0xFF) for i in range(4)]).rstrip('\x00') if fourcc else 'unknown'
            
            self.video_info = {
                'path': video_path,
                'filename': Path(video_path).name,
                'total_frames': self.total_frames,
                'fps': self.fps,
                'width': width,
                'height': height,
                'duration': self.total_frames / self.fps if self.fps > 0 else 0,
                'codec': codec  # 🎯 新增編碼信息用於優化
            }
            
            self.notify_observers('video_loaded', self.video_info)
            
            logging.info(f"視頻已加載: {Path(video_path).name}")
            logging.info(f"總幀數: {self.total_frames}, FPS: {self.fps:.2f}")
            logging.info(f"解析度: {width}x{height}")
            
            # 讀取並顯示第一幀
            self.seek_to_frame(0)
            
            return True
            
        except Exception as e:
            logging.error(f"加載視頻失敗: {str(e)}")
            return False
    
    def start_playback(self) -> bool:
        """開始播放"""
        # 🔧 診斷：詳細的錯誤日誌
        if not self.video_capture:
            logging.error("❌ 視頻播放啟動失敗: 沒有視頻捕獲對象")
            return False
        
        if not self.video_capture.isOpened():
            logging.error("❌ 視頻播放啟動失敗: 視頻檔案未正確開啟")
            return False
            
        if self.is_playing:
            logging.warning("⚠️ 視頻播放啟動失敗: 視頻已在播放中")
            return False
            
        self.is_playing = True
        self.is_paused = False
        self.stop_event.clear()
        
        # 啟動播放線程
        self.playback_thread = threading.Thread(target=self._playback_loop)
        self.playback_thread.daemon = True
        self.playback_thread.start()
        
        self.notify_observers('playback_started', {
            'current_frame': self.current_frame_number,
            'total_frames': self.total_frames
        })
        
        duration = self.total_frames / self.fps if self.fps > 0 else 0
        logging.info(f"🎬 視頻播放開始 - {self.video_info.get('filename', 'unknown')}")
        logging.info(f"🎯 視頻參數: FPS={self.fps:.2f}, 總幀數={self.total_frames}, 總時長={duration:.2f}秒")
        logging.info(f"🚀 時間軸模式: 嚴格按{duration:.2f}秒播放，每幀都處理")
        return True
    
    def pause_playback(self):
        """暫停播放"""
        if self.is_playing:
            self.is_paused = not self.is_paused
            status = "暫停" if self.is_paused else "繼續"
            logging.info(f"視頻播放{status}")
            
            self.notify_observers('playback_paused' if self.is_paused else 'playback_resumed', {
                'current_frame': self.current_frame_number
            })
    
    def stop_playback(self):
        """停止播放"""
        if self.is_playing:
            self.is_playing = False
            self.is_paused = False
            self.stop_event.set()
            
            # 🔧 確保播放線程完全停止
            if hasattr(self, 'playback_thread') and self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=2.0)
                if self.playback_thread.is_alive():
                    logging.warning("⚠️ 播放線程停止超時")
            
            # 🔧 重置播放線程引用
            self.playback_thread = None
            
            # 🔧 修復：停止播放時重置到開頭
            self.current_frame_number = 0
            if self.video_capture:
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
            self.notify_observers('playback_stopped', {
                'current_frame': self.current_frame_number
            })
            
            logging.info("✅ 視頻播放已完全停止")
    
    def _playback_loop(self):
        """播放循環 - 嚴格按秒數時間軸播放"""
        # 🎯 關鍵修復：嚴格按視頻的實際秒數播放
        playback_start_time = time.time()
        video_duration = self.total_frames / self.fps if self.fps > 0 else 0
        
        logging.info(f"🎬 開始按時間軸播放")
        logging.info(f"🕰️ 視頻時長: {video_duration:.2f}秒 (FPS: {self.fps:.2f}, 總幀數: {self.total_frames})")
        logging.info(f"🎯 模式: 嚴格按秒數播放，確保每幀都被處理")
        
        while self.is_playing and not self.stop_event.is_set():
            if self.is_paused:
                time.sleep(0.1)
                # 暂停時重置時間基準
                playback_start_time = time.time() - (self.current_frame_number / self.fps)
                continue
            
            # 🚀 高速檢測模式：跳過時間同步，盡快處理所有幀
            if not self.high_speed_detection_mode:
                # 正常播放模式：按影片時間線播放
                current_video_time = self.current_frame_number / self.fps if self.fps > 0 else 0
                target_real_time = playback_start_time + (current_video_time / self.playback_speed)
                current_real_time = time.time()
                
                # 等待直到實際時間達到視頻時間點
                if current_real_time < target_real_time:
                    wait_time = target_real_time - current_real_time
                    if wait_time > 0:
                        time.sleep(wait_time)
            # 高速檢測模式：不等待，直接處理下一幀
            
            # 讀取下一幀
            ret, frame = self.video_capture.read()
            if not ret:
                # 播放結束
                if self.loop_playback:
                    # 循環播放
                    self.seek_to_frame(0)
                    playback_start_time = time.time()  # 重置時間基準
                    continue
                else:
                    # 播放完成 - 記錄實際時間
                    self.is_playing = False
                    actual_duration = time.time() - playback_start_time
                    
                    logging.info(f"🏁 播放完成")
                    logging.info(f"🕰️ 視頻時長: {video_duration:.2f}秒, 實際播放: {actual_duration:.2f}秒")
                    logging.info(f"🎯 時間誤差: {abs(actual_duration - video_duration):.3f}秒")
                    
                    self.notify_observers('playback_finished', {
                        'total_frames_played': self.current_frame_number,
                        'video_duration': video_duration,
                        'actual_duration': actual_duration,
                        'time_accuracy': abs(actual_duration - video_duration)
                    })
                    break
            
            # 更新幀計數器
            self.current_frame_number += 1
            progress = self.current_frame_number / self.total_frames if self.total_frames > 0 else 0
            
            # 計算精確的時間戳
            video_timestamp = self.current_frame_number / self.fps if self.fps > 0 else 0
            real_elapsed = time.time() - playback_start_time
            
            # 準備幀數據
            frame_data = {
                'frame': frame,
                'frame_number': self.current_frame_number,
                'total_frames': self.total_frames,
                'progress': progress,
                'video_timestamp': video_timestamp,  # 視頻中的時間點
                'real_elapsed': real_elapsed,        # 實際經過時間
                'time_sync_error': abs(real_elapsed - video_timestamp),  # 時間同步誤差
                'fps': self.fps  # 🎯 新增：實際視頻FPS規格
            }
            
            # 🎯 發送幀給檢測處理器（同步模式下會等待處理完成）
            self.notify_observers('frame_ready', frame_data)
            
            # 🚀🚀 206fps模式：大幅減少時間同步日誌
            if self.current_frame_number % 1000 == 0:  # 每1000幀才記錄一次
                sync_error_ms = frame_data['time_sync_error'] * 1000
                # 只在高速檢測模式下且誤差極大時才警告
                if self.high_speed_detection_mode and sync_error_ms > 50000:  # 50秒才警告
                    logging.debug(f"幀{self.current_frame_number}: {sync_error_ms:.0f}ms")
    
    def _wait_for_processor_ready(self):
        """等待檢測處理器準備好 - 簡化版本"""
        # 🎯 在新的時間軸模式下，由submit_frame的同步機制確保不丟幀
        # 這裡不需要特殊等待，只需要檢查狀態
        if self.is_paused or not self.is_playing:
            return
        
        # 無需額外延遲，時間控制由主迴圈負責
        pass
    
    def seek_to_frame(self, frame_number: int) -> bool:
        """跳轉到指定幀"""
        if not self.video_capture:
            return False
            
        frame_number = max(0, min(frame_number, self.total_frames - 1))
        
        try:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            self.current_frame_number = frame_number
            
            # 讀取並發送當前幀
            ret, frame = self.video_capture.read()
            if ret:
                progress = self.current_frame_number / self.total_frames if self.total_frames > 0 else 0
                
                self.notify_observers('frame_ready', {
                    'frame': frame,
                    'frame_number': self.current_frame_number,
                    'total_frames': self.total_frames,
                    'progress': progress,
                    'timestamp': self.current_frame_number / self.fps if self.fps > 0 else 0
                })
                
                self.notify_observers('seek_completed', {
                    'frame_number': self.current_frame_number,
                    'progress': progress
                })
                
                logging.debug(f"跳轉到幀: {frame_number}")
                return True
            else:
                logging.error(f"無法讀取幀: {frame_number}")
                return False
                
        except Exception as e:
            logging.error(f"跳轉失敗: {str(e)}")
            return False
    
    def seek_to_progress(self, progress: float) -> bool:
        """根據進度跳轉（0.0-1.0）"""
        if not self.video_capture or self.total_frames == 0:
            return False
            
        progress = max(0.0, min(progress, 1.0))
        frame_number = int(progress * (self.total_frames - 1))
        return self.seek_to_frame(frame_number)
    
    def set_playback_speed(self, speed: float):
        """設置播放速度"""
        self.playback_speed = max(0.1, min(speed, 5.0))
        logging.info(f"播放速度設置為: {self.playback_speed}x")
        
        self.notify_observers('speed_changed', {
            'playback_speed': self.playback_speed
        })
    
    def set_high_speed_detection_mode(self, enable: bool):
        """🚀 設置高速檢測模式 - 盡快處理所有幀，不等待時間同步"""
        self.high_speed_detection_mode = enable
        mode_text = "高速檢測" if enable else "正常播放"
        logging.info(f"🎯 播放模式切換為: {mode_text}模式")
        
        self.notify_observers('detection_mode_changed', {
            'high_speed_detection_mode': self.high_speed_detection_mode,
            'mode_description': mode_text
        })
    
    def set_loop_playback(self, enable: bool):
        """設置循環播放"""
        self.loop_playback = enable
        logging.info(f"循環播放: {'開啟' if enable else '關閉'}")
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """獲取當前幀"""
        if not self.video_capture:
            return None
            
        # 保存當前位置
        current_pos = self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)
        
        # 讀取當前幀
        ret, frame = self.video_capture.read()
        
        # 恢復位置
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, current_pos)
        
        return frame if ret else None
    
    def get_playback_status(self) -> dict:
        """獲取播放狀態 - 時間軸版本"""
        progress = self.current_frame_number / self.total_frames if self.total_frames > 0 else 0
        
        # 🚀 修正FPS限制問題 - 使用高速預設值
        effective_fps = self.fps if (self.fps and self.fps > 0) else 206.0  # 預設206fps (acA640-300gm典型值)
        video_duration = self.total_frames / effective_fps if self.total_frames > 0 else 0
        current_time = self.current_frame_number / effective_fps if self.current_frame_number > 0 else 0
        
        return {
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'current_frame': self.current_frame_number,
            'total_frames': self.total_frames,
            'progress': progress,
            'fps': self.fps,
            'playback_fps': self.fps,  # 為 UI 相容性保留
            'playback_speed': self.playback_speed,
            'loop_playback': self.loop_playback,
            'video_info': self.video_info,
            # 🚀 高速檢測模式信息
            'high_speed_detection_mode': self.high_speed_detection_mode,
            'mode_description': "高速檢測" if self.high_speed_detection_mode else "正常播放",
            # 🎯 時間軸相關信息
            'video_duration': video_duration,      # 視頻總時長（秒）
            'current_time': current_time,          # 當前播放時間（秒）
            'remaining_time': max(0, video_duration - current_time),  # 剩餘時間（秒）
            'time_format': f"{int(current_time)//60:02d}:{int(current_time)%60:02d} / {int(video_duration)//60:02d}:{int(video_duration)%60:02d}"
        }
    
    def release(self):
        """釋放資源"""
        self.stop_playback()
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
        logging.info("視頻播放器資源已釋放")