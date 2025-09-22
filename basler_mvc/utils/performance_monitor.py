#!/usr/bin/env python3
"""
性能監控器 - 全面的系統性能監控和優化建議
專為高速工業檢測系統設計，提供實時性能分析和自動優化
"""

import time
import threading
import logging
import psutil
import gc
from typing import Dict, Any, List, Optional, Callable
from collections import deque
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np

class PerformanceLevel(Enum):
    """性能等級"""
    EXCELLENT = "excellent"    # > 95%
    GOOD = "good"             # 85-95%
    MODERATE = "moderate"     # 70-85%
    POOR = "poor"            # 50-70%
    CRITICAL = "critical"    # < 50%

@dataclass
class PerformanceMetrics:
    """性能指標"""
    timestamp: float
    fps: float
    cpu_percent: float
    memory_mb: float
    gpu_usage: float
    detection_latency_ms: float
    frame_processing_time_ms: float
    queue_size: int
    thread_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class PerformanceMonitor:
    """性能監控器 - 實時性能分析和優化"""
    
    def __init__(self, target_fps: float = 280.0, monitoring_interval: float = 1.0):
        """
        初始化性能監控器
        
        Args:
            target_fps: 目標FPS
            monitoring_interval: 監控間隔（秒）
        """
        self.target_fps = target_fps
        self.monitoring_interval = monitoring_interval
        
        # 監控狀態
        self.is_monitoring = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        # 性能歷史
        self.metrics_history = deque(maxlen=300)  # 保留5分鐘歷史（1秒間隔）
        self.fps_history = deque(maxlen=100)      # FPS歷史
        self.latency_history = deque(maxlen=100)  # 延遲歷史
        
        # 統計數據
        self.total_frames_processed = 0
        self.total_detections = 0
        self.performance_warnings = 0
        self.auto_optimizations = 0
        
        # 性能閾值
        self.fps_warning_threshold = target_fps * 0.85  # 85%
        self.fps_critical_threshold = target_fps * 0.70  # 70%
        self.latency_warning_threshold = 50.0  # ms
        self.latency_critical_threshold = 100.0  # ms
        self.memory_warning_threshold = 1024.0  # MB
        self.cpu_warning_threshold = 80.0  # %
        
        # 回調函數
        self.performance_callbacks: Dict[str, List[Callable]] = {
            'warning': [],
            'critical': [],
            'optimization': []
        }
        
        # 自動優化配置
        self.auto_optimization_enabled = True
        self.optimization_cooldown = 30.0  # 優化冷卻時間（秒）
        self.last_optimization_time = 0
        
        # 獲取系統信息
        self.cpu_count = psutil.cpu_count()
        self.total_memory_gb = psutil.virtual_memory().total / (1024**3)
        
        logging.info(f"性能監控器初始化完成 - 目標FPS: {target_fps}, 系統: {self.cpu_count}核/{self.total_memory_gb:.1f}GB")
    
    def start_monitoring(self):
        """開始性能監控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.stop_event.clear()
        
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="PerformanceMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        
        logging.info("🚀 性能監控已啟動")
    
    def stop_monitoring(self):
        """停止性能監控"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        logging.info("🛑 性能監控已停止")
    
    def record_frame_processed(self, processing_time_ms: float = 0):
        """記錄幀處理完成"""
        self.total_frames_processed += 1
        
        if processing_time_ms > 0:
            self.latency_history.append(processing_time_ms)
    
    def record_detection_completed(self, detection_count: int = 1):
        """記錄檢測完成"""
        self.total_detections += detection_count
    
    def record_fps(self, fps: float):
        """記錄FPS"""
        self.fps_history.append(fps)
        
        # 檢查性能警告
        if fps < self.fps_critical_threshold:
            self._trigger_performance_alert('critical', 'fps', fps)
        elif fps < self.fps_warning_threshold:
            self._trigger_performance_alert('warning', 'fps', fps)
    
    def _monitoring_loop(self):
        """監控循環"""
        logging.info("性能監控循環啟動")
        
        while not self.stop_event.is_set():
            try:
                # 收集性能指標
                metrics = self._collect_metrics()
                
                if metrics:
                    self.metrics_history.append(metrics)
                    
                    # 分析性能
                    self._analyze_performance(metrics)
                    
                    # 自動優化（如果啟用）
                    if self.auto_optimization_enabled:
                        self._auto_optimize(metrics)
                
            except Exception as e:
                logging.error(f"性能監控錯誤: {str(e)}")
            
            # 等待下次檢查
            self.stop_event.wait(self.monitoring_interval)
        
        logging.info("性能監控循環結束")
    
    def _collect_metrics(self) -> Optional[PerformanceMetrics]:
        """收集性能指標"""
        try:
            # CPU和記憶體
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()
            memory_mb = memory_info.used / (1024 * 1024)
            
            # FPS
            current_fps = self.fps_history[-1] if self.fps_history else 0.0
            
            # 延遲
            avg_latency = np.mean(list(self.latency_history)[-10:]) if self.latency_history else 0.0
            
            # GPU使用率（如果可用）
            gpu_usage = self._get_gpu_usage()
            
            # 線程計數
            thread_count = threading.active_count()
            
            # 處理時間
            processing_time = avg_latency
            
            return PerformanceMetrics(
                timestamp=time.time(),
                fps=current_fps,
                cpu_percent=cpu_percent,
                memory_mb=memory_mb,
                gpu_usage=gpu_usage,
                detection_latency_ms=avg_latency,
                frame_processing_time_ms=processing_time,
                queue_size=0,  # 需要從外部傳入
                thread_count=thread_count
            )
            
        except Exception as e:
            logging.error(f"收集性能指標失敗: {str(e)}")
            return None
    
    def _get_gpu_usage(self) -> float:
        """獲取GPU使用率"""
        try:
            # 嘗試使用nvidia-ml-py或其他GPU監控庫
            # 這裡返回0作為預設值
            return 0.0
        except:
            return 0.0
    
    def _analyze_performance(self, metrics: PerformanceMetrics):
        """分析性能"""
        # FPS性能檢查
        if metrics.fps < self.fps_critical_threshold:
            self.performance_warnings += 1
            self._trigger_performance_alert('critical', 'fps', metrics.fps)
        elif metrics.fps < self.fps_warning_threshold:
            self.performance_warnings += 1
            self._trigger_performance_alert('warning', 'fps', metrics.fps)
        
        # 延遲檢查
        if metrics.detection_latency_ms > self.latency_critical_threshold:
            self._trigger_performance_alert('critical', 'latency', metrics.detection_latency_ms)
        elif metrics.detection_latency_ms > self.latency_warning_threshold:
            self._trigger_performance_alert('warning', 'latency', metrics.detection_latency_ms)
        
        # 記憶體檢查
        if metrics.memory_mb > self.memory_warning_threshold:
            self._trigger_performance_alert('warning', 'memory', metrics.memory_mb)
        
        # CPU檢查
        if metrics.cpu_percent > self.cpu_warning_threshold:
            self._trigger_performance_alert('warning', 'cpu', metrics.cpu_percent)
    
    def _auto_optimize(self, metrics: PerformanceMetrics):
        """自動優化"""
        current_time = time.time()
        
        # 檢查冷卻時間
        if current_time - self.last_optimization_time < self.optimization_cooldown:
            return
        
        optimizations_applied = []
        
        # FPS過低優化
        if metrics.fps < self.fps_warning_threshold:
            # 建議降低UI更新頻率
            optimizations_applied.append("reduce_ui_frequency")
            
            # 建議啟用跳幀
            if metrics.fps < self.fps_critical_threshold:
                optimizations_applied.append("enable_frame_skip")
        
        # 記憶體過高優化
        if metrics.memory_mb > self.memory_warning_threshold:
            # 觸發垃圾回收
            gc.collect()
            optimizations_applied.append("garbage_collection")
        
        # CPU過高優化
        if metrics.cpu_percent > self.cpu_warning_threshold:
            optimizations_applied.append("reduce_cpu_load")
        
        if optimizations_applied:
            self.auto_optimizations += 1
            self.last_optimization_time = current_time
            
            self._trigger_optimization_callback(optimizations_applied, metrics)
            
            logging.info(f"🔧 自動優化已應用: {', '.join(optimizations_applied)}")
    
    def _trigger_performance_alert(self, level: str, metric_type: str, value: float):
        """觸發性能警告"""
        alert_data = {
            'level': level,
            'metric_type': metric_type,
            'value': value,
            'timestamp': time.time()
        }
        
        # 觸發相應的回調
        if level in self.performance_callbacks:
            for callback in self.performance_callbacks[level]:
                try:
                    callback(alert_data)
                except Exception as e:
                    logging.error(f"性能警告回調執行失敗: {str(e)}")
        
        # 記錄日誌
        if level == 'critical':
            logging.error(f"🚨 性能嚴重警告: {metric_type} = {value}")
        else:
            logging.warning(f"⚠️ 性能警告: {metric_type} = {value}")
    
    def _trigger_optimization_callback(self, optimizations: List[str], metrics: PerformanceMetrics):
        """觸發優化回調"""
        optimization_data = {
            'optimizations': optimizations,
            'metrics': metrics.to_dict(),
            'timestamp': time.time()
        }
        
        for callback in self.performance_callbacks.get('optimization', []):
            try:
                callback(optimization_data)
            except Exception as e:
                logging.error(f"優化回調執行失敗: {str(e)}")
    
    def register_callback(self, event_type: str, callback: Callable):
        """
        註冊性能回調
        
        Args:
            event_type: 事件類型 ('warning', 'critical', 'optimization')
            callback: 回調函數
        """
        if event_type in self.performance_callbacks:
            self.performance_callbacks[event_type].append(callback)
            logging.info(f"已註冊性能回調: {event_type}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """獲取性能摘要"""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        recent_metrics = list(self.metrics_history)[-10:]  # 最近10次記錄
        
        avg_fps = np.mean([m.fps for m in recent_metrics])
        avg_cpu = np.mean([m.cpu_percent for m in recent_metrics])
        avg_memory = np.mean([m.memory_mb for m in recent_metrics])
        avg_latency = np.mean([m.detection_latency_ms for m in recent_metrics])
        
        # 計算性能等級
        fps_ratio = avg_fps / self.target_fps
        performance_level = self._calculate_performance_level(fps_ratio)
        
        return {
            'performance_level': performance_level.value,
            'fps': {
                'current': avg_fps,
                'target': self.target_fps,
                'ratio': fps_ratio,
                'status': 'good' if avg_fps >= self.fps_warning_threshold else 'warning'
            },
            'cpu': {
                'percent': avg_cpu,
                'status': 'good' if avg_cpu < self.cpu_warning_threshold else 'warning'
            },
            'memory': {
                'usage_mb': avg_memory,
                'status': 'good' if avg_memory < self.memory_warning_threshold else 'warning'
            },
            'latency': {
                'avg_ms': avg_latency,
                'status': 'good' if avg_latency < self.latency_warning_threshold else 'warning'
            },
            'statistics': {
                'total_frames': self.total_frames_processed,
                'total_detections': self.total_detections,
                'warnings': self.performance_warnings,
                'optimizations': self.auto_optimizations
            }
        }
    
    def _calculate_performance_level(self, fps_ratio: float) -> PerformanceLevel:
        """計算性能等級"""
        if fps_ratio >= 0.95:
            return PerformanceLevel.EXCELLENT
        elif fps_ratio >= 0.85:
            return PerformanceLevel.GOOD
        elif fps_ratio >= 0.70:
            return PerformanceLevel.MODERATE
        elif fps_ratio >= 0.50:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
    
    def get_optimization_recommendations(self) -> List[str]:
        """獲取性能優化建議"""
        if not self.metrics_history:
            return []
        
        recommendations = []
        latest_metrics = self.metrics_history[-1]
        
        # FPS優化建議
        if latest_metrics.fps < self.fps_warning_threshold:
            recommendations.append("考慮降低檢測解析度或啟用跳幀")
            recommendations.append("檢查是否有不必要的UI更新")
            
        # CPU優化建議
        if latest_metrics.cpu_percent > self.cpu_warning_threshold:
            recommendations.append("考慮減少並行處理線程數量")
            recommendations.append("檢查是否有CPU密集型操作可以優化")
            
        # 記憶體優化建議
        if latest_metrics.memory_mb > self.memory_warning_threshold:
            recommendations.append("執行記憶體清理和垃圾回收")
            recommendations.append("檢查是否有記憶體洩漏")
            
        # 延遲優化建議
        if latest_metrics.detection_latency_ms > self.latency_warning_threshold:
            recommendations.append("考慮啟用GPU加速")
            recommendations.append("優化檢測算法參數")
        
        return recommendations
    
    def export_performance_data(self, filename: str = None) -> str:
        """導出性能數據"""
        if filename is None:
            filename = f"performance_data_{int(time.time())}.json"
        
        try:
            import json
            
            data = {
                'summary': self.get_performance_summary(),
                'recommendations': self.get_optimization_recommendations(),
                'history': [m.to_dict() for m in list(self.metrics_history)],
                'config': {
                    'target_fps': self.target_fps,
                    'monitoring_interval': self.monitoring_interval,
                    'thresholds': {
                        'fps_warning': self.fps_warning_threshold,
                        'fps_critical': self.fps_critical_threshold,
                        'latency_warning': self.latency_warning_threshold,
                        'latency_critical': self.latency_critical_threshold
                    }
                }
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logging.info(f"性能數據已導出到: {filename}")
            return filename
            
        except Exception as e:
            logging.error(f"導出性能數據失敗: {str(e)}")
            return ""


# 全局性能監控器實例
_global_performance_monitor: Optional[PerformanceMonitor] = None


def get_global_performance_monitor() -> PerformanceMonitor:
    """獲取全局性能監控器實例"""
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
    return _global_performance_monitor


def init_performance_monitoring(target_fps: float = 280.0):
    """初始化性能監控"""
    global _global_performance_monitor
    _global_performance_monitor = PerformanceMonitor(target_fps)
    _global_performance_monitor.start_monitoring()


def get_performance_summary() -> Dict[str, Any]:
    """獲取性能摘要的便捷函數"""
    monitor = get_global_performance_monitor()
    return monitor.get_performance_summary()