"""
系統診斷工具
幫助快速識別和排查線程同步問題和系統隱患
"""

import logging
import threading
import time
import traceback
from typing import Dict, Any, List
import json


class SystemDiagnostics:
    """系統診斷工具 - 專門解決線程同步問題"""
    
    def __init__(self, controller=None):
        """初始化診斷工具"""
        self.controller = controller
        self.last_diagnostic = None
        
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """運行完整的系統診斷"""
        try:
            diagnostic_report = {
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'system_info': self._get_system_info(),
                'thread_analysis': self._analyze_threads(),
                'camera_status': self._get_camera_status(),
                'controller_status': self._get_controller_status(),
                'potential_issues': self._identify_potential_issues(),
                'recommendations': self._generate_recommendations(),
            }
            
            self.last_diagnostic = diagnostic_report
            return diagnostic_report
            
        except Exception as e:
            logging.error(f"系統診斷失敗: {str(e)}")
            return {
                'error': f"診斷失敗: {str(e)}",
                'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
                'traceback': traceback.format_exc()
            }
    
    def _get_system_info(self) -> Dict[str, Any]:
        """獲取系統基本信息"""
        try:
            active_threads = threading.active_count()
            thread_list = []
            
            for thread in threading.enumerate():
                thread_info = {
                    'name': thread.name,
                    'alive': thread.is_alive(),
                    'daemon': thread.daemon,
                    'ident': thread.ident,
                }
                thread_list.append(thread_info)
            
            return {
                'active_thread_count': active_threads,
                'threads': thread_list,
                'main_thread_alive': threading.main_thread().is_alive(),
            }
        except Exception as e:
            return {'error': f"系統信息獲取失敗: {str(e)}"}
    
    def _analyze_threads(self) -> Dict[str, Any]:
        """分析線程狀態"""
        try:
            issues = []
            basler_threads = []
            
            for thread in threading.enumerate():
                thread_name = thread.name.lower()
                
                # 檢查 Basler 相關線程
                if 'basler' in thread_name or 'capture' in thread_name:
                    basler_threads.append({
                        'name': thread.name,
                        'alive': thread.is_alive(),
                        'daemon': thread.daemon,
                    })
            
            # 檢查是否有多個捕獲線程
            capture_threads = [t for t in basler_threads if 'capture' in t['name'].lower()]
            if len(capture_threads) > 1:
                issues.append({
                    'severity': 'high',
                    'type': 'multiple_capture_threads',
                    'description': f"檢測到多個捕獲線程({len(capture_threads)})，可能導致 'already a thread waiting' 錯誤",
                    'threads': capture_threads
                })
            
            return {
                'basler_threads': basler_threads,
                'capture_thread_count': len(capture_threads),
                'issues': issues
            }
            
        except Exception as e:
            return {'error': f"線程分析失敗: {str(e)}"}
    
    def _get_camera_status(self) -> Dict[str, Any]:
        """獲取相機狀態"""
        try:
            if not self.controller or not hasattr(self.controller, 'camera_model'):
                return {'error': '控制器或相機模型不可用'}
            
            camera_model = self.controller.camera_model
            if hasattr(camera_model, 'get_system_diagnostics'):
                return camera_model.get_system_diagnostics()
            else:
                # 基本狀態檢查
                return {
                    'is_connected': getattr(camera_model, 'is_connected', False),
                    'is_grabbing': getattr(camera_model, 'is_grabbing', False),
                    'camera_exists': getattr(camera_model, 'camera', None) is not None,
                }
                
        except Exception as e:
            return {'error': f"相機狀態獲取失敗: {str(e)}"}
    
    def _get_controller_status(self) -> Dict[str, Any]:
        """獲取控制器狀態"""
        try:
            if not self.controller:
                return {'error': '控制器不可用'}
            
            status = {
                'is_running': getattr(self.controller, 'is_running', False),
                'is_processing': getattr(self.controller, 'is_processing', False),
            }
            
            # 檢查處理線程
            if hasattr(self.controller, 'processing_thread'):
                processing_thread = self.controller.processing_thread
                status['processing_thread'] = {
                    'exists': processing_thread is not None,
                    'alive': processing_thread.is_alive() if processing_thread else False,
                    'name': processing_thread.name if processing_thread else None,
                }
            
            return status
            
        except Exception as e:
            return {'error': f"控制器狀態獲取失敗: {str(e)}"}
    
    def _identify_potential_issues(self) -> List[Dict[str, Any]]:
        """識別潛在問題"""
        issues = []
        
        try:
            # 檢查線程問題
            thread_analysis = self._analyze_threads()
            if 'issues' in thread_analysis:
                issues.extend(thread_analysis['issues'])
            
            # 檢查相機狀態不一致
            camera_status = self._get_camera_status()
            if 'camera_status' in camera_status:
                cam_stat = camera_status['camera_status']
                if (cam_stat.get('is_connected', False) and 
                    not cam_stat.get('camera_open', False)):
                    issues.append({
                        'severity': 'medium',
                        'type': 'camera_state_mismatch',
                        'description': '相機標記為已連接但實際未開啟',
                    })
                
                if (cam_stat.get('is_grabbing', False) and 
                    not cam_stat.get('camera_grabbing', False)):
                    issues.append({
                        'severity': 'high',
                        'type': 'grabbing_state_mismatch',
                        'description': '捕獲狀態不一致，可能導致線程衝突',
                    })
            
            # 檢查線程洩漏
            if thread_analysis.get('capture_thread_count', 0) > 1:
                issues.append({
                    'severity': 'critical',
                    'type': 'thread_leak',
                    'description': '檢測到線程洩漏，必須重啟系統',
                })
            
        except Exception as e:
            issues.append({
                'severity': 'critical',
                'type': 'diagnostic_error',
                'description': f'診斷過程中發生錯誤: {str(e)}',
            })
        
        return issues
    
    def _generate_recommendations(self) -> List[str]:
        """生成修復建議"""
        recommendations = []
        
        if not self.last_diagnostic:
            return ['請先運行完整診斷']
        
        try:
            issues = self.last_diagnostic.get('potential_issues', [])
            
            for issue in issues:
                issue_type = issue.get('type', '')
                severity = issue.get('severity', 'unknown')
                
                if issue_type == 'multiple_capture_threads':
                    recommendations.append('⚠️ 立即停止所有捕獲操作，重啟相機連接')
                    recommendations.append('🔧 檢查代碼中是否有重複的 start_capture() 調用')
                
                elif issue_type == 'camera_state_mismatch':
                    recommendations.append('🔄 重新建立相機連接')
                    recommendations.append('📝 檢查相機初始化邏輯')
                
                elif issue_type == 'grabbing_state_mismatch':
                    recommendations.append('🛑 立即停止捕獲，清理線程狀態')
                    recommendations.append('🔧 使用 force_stop_all() 方法')
                
                elif issue_type == 'thread_leak':
                    recommendations.append('🚨 嚴重：必須重啟應用程序')
                    recommendations.append('🔍 檢查線程停止邏輯')
                
                if severity == 'critical':
                    recommendations.insert(0, '🚨 發現嚴重問題，建議立即重啟系統')
            
            if not issues:
                recommendations.append('✅ 系統狀態良好，無發現問題')
            
        except Exception as e:
            recommendations.append(f'❌ 生成建議時出錯: {str(e)}')
        
        return recommendations
    
    def print_diagnostic_report(self, report: Dict[str, Any] = None):
        """打印診斷報告"""
        if report is None:
            report = self.last_diagnostic
        
        if not report:
            print("❌ 無可用的診斷報告")
            return
        
        print("\n" + "="*60)
        print("🔍 BASLER 相機系統診斷報告")
        print("="*60)
        print(f"時間: {report.get('timestamp', 'Unknown')}")
        print()
        
        # 系統信息
        sys_info = report.get('system_info', {})
        print(f"📊 系統狀態:")
        print(f"   活動線程數: {sys_info.get('active_thread_count', 'Unknown')}")
        print(f"   主線程狀態: {'正常' if sys_info.get('main_thread_alive', False) else '異常'}")
        print()
        
        # 線程分析
        thread_analysis = report.get('thread_analysis', {})
        basler_threads = thread_analysis.get('basler_threads', [])
        print(f"🧵 Basler 線程分析:")
        if basler_threads:
            for thread in basler_threads:
                status = "🟢 運行中" if thread['alive'] else "🔴 已停止"
                print(f"   {thread['name']}: {status}")
        else:
            print("   未檢測到 Basler 相關線程")
        print()
        
        # 潛在問題
        issues = report.get('potential_issues', [])
        print(f"⚠️ 發現 {len(issues)} 個潛在問題:")
        if issues:
            for i, issue in enumerate(issues, 1):
                severity_emoji = {
                    'critical': '🚨',
                    'high': '⚠️',
                    'medium': '🟡',
                    'low': '🔵'
                }.get(issue.get('severity', 'unknown'), '❓')
                
                print(f"   {i}. {severity_emoji} {issue.get('description', 'Unknown issue')}")
        else:
            print("   ✅ 無發現問題")
        print()
        
        # 建議
        recommendations = report.get('recommendations', [])
        print(f"💡 修復建議:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        print("\n" + "="*60)
    
    def save_diagnostic_report(self, filename: str = None):
        """保存診斷報告到文件"""
        if not self.last_diagnostic:
            logging.error("無可用的診斷報告")
            return False
        
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"basler_diagnostic_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.last_diagnostic, f, ensure_ascii=False, indent=2)
            
            logging.info(f"診斷報告已保存到: {filename}")
            return True
            
        except Exception as e:
            logging.error(f"保存診斷報告失敗: {str(e)}")
            return False


def quick_diagnostic(controller) -> Dict[str, Any]:
    """快速診斷函數 - 便捷接口"""
    diagnostics = SystemDiagnostics(controller)
    return diagnostics.run_full_diagnostic()


def print_quick_diagnostic(controller):
    """快速診斷並打印報告"""
    diagnostics = SystemDiagnostics(controller)
    report = diagnostics.run_full_diagnostic()
    diagnostics.print_diagnostic_report(report)
    return report