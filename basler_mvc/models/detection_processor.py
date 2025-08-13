"""
檢測處理器 - 專用於高性能檢測處理
針對rack 5b設備和GPU加速優化
"""

import cv2
import numpy as np
import threading
import queue
import time
import logging
from typing import Optional, Dict, Any, Callable, List, Tuple
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

class DetectionProcessor:
    """
    高性能檢測處理器
    - 專門處理視頻回放檢測
    - GPU優化
    - 多線程並行處理
    - UI與檢測完全分離
    """
    
    def __init__(self, detection_model, max_workers=None):
        """初始化檢測處理器"""
        self.detection_model = detection_model
        
        # 自動設定線程數量（優化記憶體使用）
        if max_workers is None:
            cpu_count = multiprocessing.cpu_count()
            # 減少線程數量以降低記憶體消耗
            self.max_workers = max(1, cpu_count // 2)
        else:
            self.max_workers = max_workers
            
        # 線程池
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # 🎯 記憶體優化：進一步減少隊列大小以降低記憶體占用
        self.frame_queue = queue.Queue(maxsize=3)     # 最小化隊列大小
        
        # 結果隊列（UI消費）
        self.result_queue = queue.Queue(maxsize=5)    # 最小化結果隊列
        
        # 同步控制 - 記憶體優化
        self.sync_mode = False  # 🎯 預設使用非同步模式，減少阻塞
        self.processing_semaphore = threading.Semaphore(self.max_workers)      # 進一步減少並發許可數
        
        # 統計資料
        self.total_frames_processed = 0
        self.total_objects_detected = 0
        self.processing_times = deque(maxlen=20)  # 進一步減少記憶體占用
        self.detection_fps = 0.0
        
        # 控制標誌
        self.is_processing = False
        self.stop_event = threading.Event()
        
        # 工作線程
        self.processing_threads = []
        
        # 觀察者
        self.observers = []
        
        logging.info(f"檢測處理器初始化完成 - {self.max_workers} 工作線程")
    
    def add_observer(self, observer: Callable):
        """添加觀察者"""
        self.observers.append(observer)
    
    def notify_observers(self, event_type: str, data: Any = None):
        """通知觀察者"""
        for observer in self.observers:
            try:
                observer(event_type, data)
            except Exception as e:
                logging.error(f"通知觀察者錯誤: {str(e)}")
    
    def start_processing(self):
        """開始處理"""
        if self.is_processing:
            return
            
        self.is_processing = True
        self.stop_event.clear()
        
        # 啟動工作線程
        for i in range(self.max_workers):
            thread = threading.Thread(
                target=self._processing_worker, 
                name=f"DetectionWorker-{i}",
                daemon=True
            )
            thread.start()
            self.processing_threads.append(thread)
        
        # 啟動結果處理線程
        result_thread = threading.Thread(
            target=self._result_handler,
            name="DetectionResultHandler",
            daemon=True
        )
        result_thread.start()
        self.processing_threads.append(result_thread)
        
        logging.info("檢測處理器已啟動")
    
    def stop_processing(self):
        """停止處理 - 資源安全版本"""
        if not self.is_processing:
            return
            
        self.is_processing = False
        self.stop_event.set()
        
        # 🎯 確保線程池正確關閉（修正資源洩漏）
        if hasattr(self, 'executor') and self.executor:
            try:
                # 停止接受新任務並等待完成
                self.executor.shutdown(wait=True)
                logging.info("✅ 線程池已正確關閉")
                
            except Exception as e:
                logging.error(f"❌ 線程池關閉異常: {str(e)}")
                
                # 🆘 緊急措施：強制清理
                try:
                    if hasattr(self.executor, '_threads'):
                        for thread in self.executor._threads:
                            if thread.is_alive():
                                logging.warning(f"強制等待線程 {thread.name} 停止")
                                thread.join(timeout=1.0)
                except Exception as force_error:
                    logging.error(f"強制清理失敗: {str(force_error)}")
            
            finally:
                # 🧹 確保引用被清除
                self.executor = None
        
        # 🔧 改善線程停止機制：先清空隊列再等待線程
        self._clear_queues()
        
        # 等待工作線程結束，使用更長的超時時間
        for thread in self.processing_threads:
            if thread.is_alive():
                # 🔧 針對結果處理線程的特殊處理
                if "ResultHandler" in thread.name:
                    # 結果處理線程需要更多時間清理隊列
                    thread.join(timeout=5.0)
                else:
                    thread.join(timeout=3.0)
                    
                if thread.is_alive():
                    logging.warning(f"檢測工作線程 {thread.name} 未能及時停止，嘗試強制中斷")
                    # 🔧 最後手段：強制設置停止標誌
                    if hasattr(thread, '_target') and hasattr(thread._target, '__self__'):
                        try:
                            thread_obj = thread._target.__self__
                            if hasattr(thread_obj, 'stop_event'):
                                thread_obj.stop_event.set()
                        except:
                            pass
        
        self.processing_threads.clear()
        
        # 清空隊列
        self._clear_queues()
        
        # 🎯 重置統計數據以防記憶體累積
        self.processing_times.clear()
        
        # 🧹 強制記憶體清理
        import gc
        gc.collect()
        logging.debug("🧹 執行記憶體垃圾回收")
        
        logging.info("✅ 檢測處理器已安全停止")
    
    def submit_frame(self, frame: np.ndarray, frame_info: Dict[str, Any]) -> bool:
        """提交幀進行檢測 - 算法調整模式同步版本"""
        if not self.is_processing:
            return False
        
        frame_number = frame_info.get('frame_number', 0)
        
        if self.sync_mode:
            # 🎯 同步模式：等待直到可以提交
            try:
                # 🎯 優化視頻回放：非阻塞提交
                acquired = self.processing_semaphore.acquire(blocking=False)  # 非阻塞獲取信號量
                if not acquired:
                    # 使用非阻塞模式，直接跳過該幀
                    return False
                
                # 非阻塞提交（視頻回放模式優化）
                try:
                    self.frame_queue.put_nowait({
                        'frame': frame.copy(),  # 複製幀避免併發問題
                        'frame_info': frame_info,
                        'submit_time': time.time(),
                        'semaphore': self.processing_semaphore  # 傳遞信號量用於釋放
                    })
                except queue.Full:
                    self.processing_semaphore.release()  # 隊列滿時釋放信號量
                    return False
                
                return True
                
            except queue.Full:
                # 🎯 靜默處理：同步模式下隊列滿也是正常的
                self.processing_semaphore.release()  # 釋放信號量
                return False
            except Exception as e:
                logging.error(f"幀 {frame_number}: 提交錯誤 - {str(e)}")
                self.processing_semaphore.release()  # 釋放信號量
                return False
        else:
            # 非同步模式（原有遟度模式）
            try:
                self.frame_queue.put_nowait({
                    'frame': frame.copy(),
                    'frame_info': frame_info,
                    'submit_time': time.time(),
                    'semaphore': None
                })
                return True
            except queue.Full:
                # 🎯 完全靜默處理：視頻回放時跳過部分幀是正常的
                return False
    
    def _processing_worker(self):
        """檢測工作線程"""
        thread_name = threading.current_thread().name
        logging.info(f"[{thread_name}] 檢測工作線程啟動")
        
        while not self.stop_event.is_set():
            try:
                # 獲取幀（阻塞等待）
                try:
                    frame_data = self.frame_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                frame = frame_data['frame']
                frame_info = frame_data['frame_info']
                submit_time = frame_data['submit_time']
                
                # 執行檢測
                start_time = time.time()
                objects, result_frame = self.detection_model.detect_frame(frame)
                detection_time = time.time() - start_time
                
                # 更新統計
                self.total_frames_processed += 1
                if len(objects) > 0:
                    self.total_objects_detected += len(objects)
                
                self.processing_times.append(detection_time)
                
                # 🎯 改進：更頻繁更新FPS，使用滿意的滑動平均
                if len(self.processing_times) >= 3:  # 更快開始計算平均值
                    avg_time = sum(self.processing_times) / len(self.processing_times)
                    self.detection_fps = 1.0 / avg_time if avg_time > 0 else 0
                    
                    # 記錄詳細資訊用於調試
                    if self.total_frames_processed % 30 == 0:  # 每30幀記錄一次
                        logging.debug(f"🚀 處理平均速度: {self.detection_fps:.1f} fps (樣本數: {len(self.processing_times)})")
                
                # 提交結果
                result = {
                    'frame': result_frame,
                    'objects': objects,
                    'object_count': len(objects),
                    'frame_info': frame_info,
                    'detection_time': detection_time,
                    'queue_delay': start_time - submit_time,
                    'total_processed': self.total_frames_processed,
                    'detection_fps': self.detection_fps,
                    'thread_name': thread_name
                }
                
                # 非阻塞提交結果
                try:
                    self.result_queue.put_nowait(result)
                except queue.Full:
                    # 如果結果隊列滿了，移除最舊的結果
                    try:
                        self.result_queue.get_nowait()
                        self.result_queue.put_nowait(result)
                    except queue.Empty:
                        pass
                
                # 釋放信號量（如果是同步模式）
                semaphore = frame_data.get('semaphore')
                if semaphore:
                    semaphore.release()
                
                # 標記任務完成
                self.frame_queue.task_done()
                
            except Exception as e:
                logging.error(f"[{thread_name}] 檢測處理錯誤: {str(e)}")
                try:
                    # 錯誤時也要釋放信號量
                    if 'frame_data' in locals():
                        semaphore = frame_data.get('semaphore')
                        if semaphore:
                            semaphore.release()
                    self.frame_queue.task_done()
                except:
                    pass
        
        logging.info(f"[{thread_name}] 檢測工作線程結束")
    
    def _result_handler(self):
        """結果處理線程"""
        logging.info("結果處理線程啟動")
        
        ui_update_counter = 0
        last_ui_update = 0
        
        while not self.stop_event.is_set():
            try:
                # 🔧 關鍵修復：檢查停止狀態和處理狀態
                if not self.is_processing:
                    break
                    
                # 獲取檢測結果
                try:
                    result = self.result_queue.get(timeout=0.1)
                except queue.Empty:
                    # 🔧 在隊列為空時檢查停止狀態，避免無限等待
                    if self.stop_event.is_set() or not self.is_processing:
                        break
                    continue
                
                frame_number = result['frame_info'].get('frame_number', 0)
                object_count = result['object_count']
                
                # 🚀 優化UI更新策略：確保重要檢測結果都能顯示
                current_time = time.time()
                should_update_ui = (
                    frame_number == 1 or  # 第一幀
                    object_count > 0 or  # 🎯 有檢測結果時總是更新（重要！）
                    ui_update_counter % 5 == 0 or  # 每5個結果更新一次（提高頻率）
                    (current_time - last_ui_update) > 0.3  # 至少0.3秒更新一次（提高頻率）
                )
                
                if should_update_ui:
                    # 通知UI更新
                    self.notify_observers('detection_result', {
                        'frame': result['frame'],
                        'object_count': object_count,
                        'frame_number': frame_number,
                        'progress': result['frame_info'].get('progress', 0),
                        'timestamp': result['frame_info'].get('timestamp', 0),
                        'source': 'video',
                        'total_processed': result['total_processed'],
                        'detection_fps': result['detection_fps'],
                        'queue_delay': result['queue_delay'],
                        'detection_time': result['detection_time']
                    })
                    last_ui_update = current_time
                
                # 🎯 始終記錄檢測結果（用於統計分析）
                if object_count > 0:
                    logging.debug(f"幀 {frame_number}: 檢測到 {object_count} 個物件 "
                                f"(檢測時間: {result['detection_time']*1000:.1f}ms)")
                
                ui_update_counter += 1
                
            except Exception as e:
                logging.error(f"結果處理錯誤: {str(e)}")
        
        logging.info("結果處理線程結束")
    
    def _clear_queues(self):
        """🔧 快速清空隊列，幫助線程更快停止"""
        # 清空幀隊列
        cleared_frames = 0
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
                cleared_frames += 1
                # 避免無限循環
                if cleared_frames > 1000:
                    logging.warning("⚠️ 幀隊列清理超過1000個項目，強制停止清理")
                    break
            except queue.Empty:
                break
        
        # 清空結果隊列
        cleared_results = 0
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
                cleared_results += 1
                # 避免無限循環
                if cleared_results > 1000:
                    logging.warning("⚠️ 結果隊列清理超過1000個項目，強制停止清理")
                    break
            except queue.Empty:
                break
                
        if cleared_frames > 0 or cleared_results > 0:
            logging.debug(f"🧹 清理隊列: 幀={cleared_frames}, 結果={cleared_results}")
    
    def set_sync_mode(self, sync_mode: bool):
        """設置同步模式"""
        self.sync_mode = sync_mode
        mode_name = "同步模式" if sync_mode else "異步模式"
        logging.info(f"檢測處理器切換為: {mode_name}")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """獲取隊列狀態"""
        return {
            'frame_queue_size': self.frame_queue.qsize(),
            'result_queue_size': self.result_queue.qsize(),
            'frame_queue_maxsize': self.frame_queue.maxsize,
            'result_queue_maxsize': self.result_queue.maxsize,
            'semaphore_value': self.processing_semaphore._value if hasattr(self.processing_semaphore, '_value') else 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取處理統計 - 強調平均處理速度"""
        # 🎯 計算實時平均處理速度
        if len(self.processing_times) > 0:
            avg_time = sum(self.processing_times) / len(self.processing_times)
            current_avg_fps = 1.0 / avg_time if avg_time > 0 else 0
        else:
            current_avg_fps = 0
            
        return {
            'total_frames_processed': self.total_frames_processed,
            'total_objects_detected': self.total_objects_detected,
            'detection_fps': current_avg_fps,  # 🎯 返回最新的平均值
            'avg_processing_time': sum(self.processing_times) / len(self.processing_times) if len(self.processing_times) > 0 else 0,
            'frame_queue_size': self.frame_queue.qsize(),
            'result_queue_size': self.result_queue.qsize(),
            'max_workers': self.max_workers,
            'is_processing': self.is_processing,
            'sync_mode': self.sync_mode,
            'samples_count': len(self.processing_times)  # 用於調試
        }
    
    def cleanup(self):
        """手動清理資源 - 推薦使用此方法而非依賴析構函數"""
        try:
            self.stop_processing()
            logging.info("🧹 DetectionProcessor 資源清理完成")
        except Exception as e:
            logging.error(f"❌ DetectionProcessor 清理失敗: {str(e)}")
    
    def __del__(self):
        """析構函數 - 最後防線"""
        try:
            # 🎯 只做最基本的清理，避免在析構時出錯
            if hasattr(self, 'executor') and self.executor:
                self.executor.shutdown(wait=False)  # 不等待，避免阻塞
        except:
            pass  # 析構函數中不記錄錯誤