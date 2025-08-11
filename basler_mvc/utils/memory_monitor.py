"""
記憶體監控工具 - 預防記憶體洩漏
監控系統記憶體使用情況並提供清理建議
"""

import logging
import time
import threading
import gc
from typing import Dict, Any, Optional, List
from collections import deque
import psutil
import os


class MemoryMonitor:
    """記憶體監控器 - 預防記憶體洩漏"""
    
    def __init__(self, check_interval: float = 30.0, memory_limit_mb: float = 1024.0):
        """
        初始化記憶體監控器
        
        Args:
            check_interval: 檢查間隔（秒）
            memory_limit_mb: 記憶體使用警告閾值（MB）
        """
        self.check_interval = check_interval
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        
        # 監控狀態
        self.is_monitoring = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        # 記憶體歷史記錄
        self.memory_history = deque(maxlen=100)  # 保留最近100次記錄
        self.gc_history = deque(maxlen=50)  # GC歷史
        
        # 統計數據
        self.max_memory_used = 0
        self.total_gc_collections = 0
        self.last_warning_time = 0
        
        # 回調函數
        self.memory_warning_callback = None
        self.memory_critical_callback = None
        
        # 獲取進程對象
        self.process = psutil.Process(os.getpid())
        
        logging.info(f"記憶體監控器初始化完成 - 警告閾值: {memory_limit_mb:.1f}MB")
    
    def start_monitoring(self):
        """開始監控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.stop_event.clear()
        
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop, 
            name="MemoryMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        
        logging.info("🔍 記憶體監控已啟動")
    
    def stop_monitoring(self):
        """停止監控"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
            if self.monitor_thread.is_alive():
                logging.warning("記憶體監控線程未能及時停止")
        
        logging.info("🔍 記憶體監控已停止")
    
    def _monitoring_loop(self):
        """監控循環"""
        logging.info("記憶體監控循環啟動")
        
        while not self.stop_event.is_set():
            try:
                # 獲取記憶體使用情況
                memory_info = self._get_memory_info()
                current_memory = memory_info['rss_bytes']
                
                # 記錄歷史
                self.memory_history.append({
                    'timestamp': time.time(),
                    'memory_mb': current_memory / (1024 * 1024),
                    'memory_percent': memory_info['percent']
                })
                
                # 更新統計
                if current_memory > self.max_memory_used:
                    self.max_memory_used = current_memory
                
                # 檢查記憶體使用情況
                self._check_memory_usage(memory_info)
                
                # 自動垃圾回收（如果記憶體使用過高）
                if current_memory > self.memory_limit_bytes * 0.8:  # 80%閾值
                    self._perform_gc()
                
            except Exception as e:
                logging.error(f"記憶體監控錯誤: {str(e)}")
            
            # 等待下次檢查
            self.stop_event.wait(self.check_interval)
        
        logging.info("記憶體監控循環結束")
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """獲取記憶體信息"""
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            return {
                'rss_bytes': memory_info.rss,  # 常駐記憶體
                'vms_bytes': memory_info.vms,  # 虛擬記憶體
                'percent': memory_percent,     # 記憶體使用百分比
                'available_mb': psutil.virtual_memory().available / (1024 * 1024)
            }
        except Exception as e:
            logging.error(f"獲取記憶體信息失敗: {str(e)}")
            return {
                'rss_bytes': 0,
                'vms_bytes': 0,
                'percent': 0,
                'available_mb': 0
            }
    
    def _check_memory_usage(self, memory_info: Dict[str, Any]):
        """檢查記憶體使用情況"""
        current_memory = memory_info['rss_bytes']
        current_time = time.time()
        
        # 避免頻繁警告
        if current_time - self.last_warning_time < 60:  # 1分鐘內不重複警告
            return
        
        if current_memory > self.memory_limit_bytes:
            # 記憶體使用超過閾值
            memory_mb = current_memory / (1024 * 1024)
            limit_mb = self.memory_limit_bytes / (1024 * 1024)
            
            logging.warning(f"⚠️ 記憶體使用警告: {memory_mb:.1f}MB (限制: {limit_mb:.1f}MB)")
            
            if self.memory_warning_callback:
                try:
                    self.memory_warning_callback(memory_info)
                except Exception as e:
                    logging.error(f"記憶體警告回調執行失敗: {str(e)}")
            
            self.last_warning_time = current_time
            
            # 如果記憶體使用極高，觸發緊急回調
            if current_memory > self.memory_limit_bytes * 1.5:  # 150%閾值
                logging.error(f"🚨 記憶體使用嚴重警告: {memory_mb:.1f}MB")
                
                if self.memory_critical_callback:
                    try:
                        self.memory_critical_callback(memory_info)
                    except Exception as e:
                        logging.error(f"記憶體緊急回調執行失敗: {str(e)}")
    
    def _perform_gc(self):
        """執行垃圾回收"""
        try:
            before_memory = self.process.memory_info().rss
            
            # 執行所有層級的垃圾回收
            collected = 0
            for generation in range(3):
                collected += gc.collect(generation)
            
            after_memory = self.process.memory_info().rss
            freed_mb = (before_memory - after_memory) / (1024 * 1024)
            
            # 記錄GC結果
            gc_info = {
                'timestamp': time.time(),
                'objects_collected': collected,
                'memory_freed_mb': freed_mb,
                'before_memory_mb': before_memory / (1024 * 1024),
                'after_memory_mb': after_memory / (1024 * 1024)
            }
            
            self.gc_history.append(gc_info)
            self.total_gc_collections += 1
            
            if freed_mb > 1.0:  # 如果釋放了超過1MB記憶體
                logging.info(f"🧹 垃圾回收釋放了 {freed_mb:.1f}MB 記憶體")
            
        except Exception as e:
            logging.error(f"垃圾回收執行失敗: {str(e)}")
    
    def force_gc(self) -> Dict[str, Any]:
        """手動執行垃圾回收"""
        before_memory = self.process.memory_info().rss
        
        collected = 0
        for generation in range(3):
            collected += gc.collect(generation)
        
        after_memory = self.process.memory_info().rss
        freed_mb = (before_memory - after_memory) / (1024 * 1024)
        
        result = {
            'objects_collected': collected,
            'memory_freed_mb': freed_mb,
            'before_memory_mb': before_memory / (1024 * 1024),
            'after_memory_mb': after_memory / (1024 * 1024)
        }
        
        logging.info(f"🧹 手動垃圾回收完成: 釋放 {freed_mb:.1f}MB, 回收 {collected} 個物件")
        return result
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """獲取記憶體統計信息"""
        current_memory_info = self._get_memory_info()
        
        # 計算平均記憶體使用
        if self.memory_history:
            recent_memory = [record['memory_mb'] for record in list(self.memory_history)[-10:]]
            avg_memory_mb = sum(recent_memory) / len(recent_memory)
        else:
            avg_memory_mb = 0
        
        return {
            'current_memory_mb': current_memory_info['rss_bytes'] / (1024 * 1024),
            'max_memory_mb': self.max_memory_used / (1024 * 1024),
            'avg_memory_mb': avg_memory_mb,
            'memory_limit_mb': self.memory_limit_bytes / (1024 * 1024),
            'memory_percent': current_memory_info['percent'],
            'available_memory_mb': current_memory_info['available_mb'],
            'total_gc_collections': self.total_gc_collections,
            'memory_history_count': len(self.memory_history),
            'gc_history_count': len(self.gc_history),
            'is_monitoring': self.is_monitoring
        }
    
    def get_memory_trend(self) -> List[Dict[str, Any]]:
        """獲取記憶體使用趨勢"""
        return list(self.memory_history)
    
    def set_warning_callback(self, callback: callable):
        """設置記憶體警告回調"""
        self.memory_warning_callback = callback
    
    def set_critical_callback(self, callback: callable):
        """設置記憶體緊急回調"""
        self.memory_critical_callback = callback
    
    def cleanup(self):
        """清理記憶體監控器"""
        self.stop_monitoring()
        
        # 清理歷史記錄
        self.memory_history.clear()
        self.gc_history.clear()
        
        logging.info("🧹 記憶體監控器清理完成")


# 全局記憶體監控器實例
_global_memory_monitor: Optional[MemoryMonitor] = None


def get_global_memory_monitor() -> MemoryMonitor:
    """獲取全局記憶體監控器實例"""
    global _global_memory_monitor
    if _global_memory_monitor is None:
        _global_memory_monitor = MemoryMonitor()
    return _global_memory_monitor


def start_global_monitoring():
    """啟動全局記憶體監控"""
    monitor = get_global_memory_monitor()
    monitor.start_monitoring()


def stop_global_monitoring():
    """停止全局記憶體監控"""
    global _global_memory_monitor
    if _global_memory_monitor:
        _global_memory_monitor.stop_monitoring()
        _global_memory_monitor = None


def get_memory_summary() -> str:
    """獲取記憶體使用摘要"""
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        system_memory = psutil.virtual_memory()
        
        summary = f"""
📊 記憶體使用摘要:
  當前進程: {memory_info.rss / (1024*1024):.1f}MB ({memory_percent:.1f}%)
  系統總計: {system_memory.total / (1024*1024*1024):.1f}GB
  系統可用: {system_memory.available / (1024*1024*1024):.1f}GB ({system_memory.percent:.1f}% used)
        """.strip()
        
        return summary
        
    except Exception as e:
        return f"獲取記憶體摘要失敗: {str(e)}"
