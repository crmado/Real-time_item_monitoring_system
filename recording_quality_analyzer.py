#!/usr/bin/env python3
"""
錄製品質分析器
專門用於檢測280 fps錄製的檔案品質和規格
"""

import cv2
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import statistics

class RecordingQualityAnalyzer:
    """錄製品質分析器"""
    
    def __init__(self):
        self.recordings_dir = Path("basler_mvc/recordings")
        self.expected_fps = 280
        self.tolerance_percent = 5  # 5% 容差
        
    def analyze_all_recordings(self):
        """分析所有錄製檔案的品質"""
        print("🎬 錄製品質分析器")
        print("=" * 60)
        print(f"🎯 目標FPS: {self.expected_fps}")
        print(f"📊 容許誤差: ±{self.tolerance_percent}%")
        print()
        
        video_files = self._get_video_files()
        if not video_files:
            print("❌ 沒有找到視頻檔案")
            return
            
        analysis_results = []
        print(f"🔍 分析 {len(video_files)} 個檔案...")
        print("=" * 60)
        
        for i, video_file in enumerate(video_files, 1):
            print(f"\n📹 [{i}/{len(video_files)}] {video_file.name}")
            result = self._analyze_single_file(video_file)
            if result:
                analysis_results.append(result)
                self._print_file_analysis(result)
            print("-" * 60)
        
        # 總體分析
        if analysis_results:
            self._print_summary_analysis(analysis_results)
            self._generate_recommendations(analysis_results)
            
    def _get_video_files(self):
        """獲取所有視頻檔案"""
        if not self.recordings_dir.exists():
            return []
            
        video_files = []
        for ext in ['*.avi', '*.mp4', '*.mov']:
            video_files.extend(self.recordings_dir.glob(ext))
            
        return sorted(video_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def _analyze_single_file(self, video_path):
        """分析單個檔案"""
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                print(f"❌ 無法開啟檔案: {video_path}")
                return None
                
            # 基本資訊
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            
            # 檔案資訊
            file_size = video_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            creation_time = datetime.fromtimestamp(video_path.stat().st_ctime)
            
            # 計算品質指標
            duration = frame_count / fps if fps > 0 else 0
            fourcc_str = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
            
            # FPS 偏差分析
            fps_error = abs(fps - self.expected_fps) / self.expected_fps * 100
            fps_status = self._evaluate_fps_status(fps, fps_error)
            
            # 檔案效率（每秒檔案大小）
            file_efficiency = file_size_mb / duration if duration > 0 else 0
            
            cap.release()
            
            return {
                'file_name': video_path.name,
                'file_path': str(video_path),
                'file_size_mb': file_size_mb,
                'file_size_bytes': file_size,
                'creation_time': creation_time,
                'fps': fps,
                'fps_error_percent': fps_error,
                'fps_status': fps_status,
                'frame_count': frame_count,
                'duration_sec': duration,
                'width': width,
                'height': height,
                'codec': fourcc_str,
                'file_efficiency_mb_per_sec': file_efficiency
            }
            
        except Exception as e:
            print(f"❌ 分析檔案時發生錯誤: {str(e)}")
            return None
    
    def _evaluate_fps_status(self, actual_fps, error_percent):
        """評估FPS狀態"""
        if error_percent <= 1:
            return "excellent"  # 優秀
        elif error_percent <= self.tolerance_percent:
            return "good"       # 良好
        elif error_percent <= 10:
            return "acceptable" # 可接受
        else:
            return "poor"       # 不良
    
    def _print_file_analysis(self, result):
        """列印單個檔案分析結果"""
        # 基本資訊
        print(f"📊 檔案資訊:")
        print(f"   大小: {result['file_size_mb']:.2f} MB")
        print(f"   解析度: {result['width']} x {result['height']}")
        print(f"   編碼: {result['codec']}")
        print(f"   時長: {result['duration_sec']:.2f} 秒")
        print(f"   建立時間: {result['creation_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        # FPS 分析
        print(f"\n🎯 FPS 分析:")
        print(f"   實際 FPS: {result['fps']:.2f}")
        print(f"   誤差: {result['fps_error_percent']:.2f}%")
        
        # FPS 狀態圖示
        status_icons = {
            "excellent": "🟢 優秀",
            "good": "🟡 良好", 
            "acceptable": "🟠 可接受",
            "poor": "🔴 不良"
        }
        print(f"   狀態: {status_icons.get(result['fps_status'], '❓ 未知')}")
        
        # 效率分析
        print(f"\n📈 效率分析:")
        print(f"   檔案效率: {result['file_efficiency_mb_per_sec']:.2f} MB/秒")
        
        # 品質評估
        if result['fps_status'] == "poor":
            print(f"   ⚠️ 警告: FPS偏差過大，可能影響監控品質")
        
        if result['file_efficiency_mb_per_sec'] > 10:
            print(f"   📝 注意: 檔案較大，考慮優化編碼設定")
    
    def _print_summary_analysis(self, results):
        """列印總體分析結果"""
        print("\n" + "=" * 60)
        print("📊 總體分析結果")
        print("=" * 60)
        
        # 統計各狀態的檔案數量
        status_counts = {}
        fps_values = []
        file_sizes = []
        
        for result in results:
            status = result['fps_status']
            status_counts[status] = status_counts.get(status, 0) + 1
            fps_values.append(result['fps'])
            file_sizes.append(result['file_size_mb'])
        
        # FPS 統計
        if fps_values:
            avg_fps = statistics.mean(fps_values)
            min_fps = min(fps_values)
            max_fps = max(fps_values)
            
            print(f"🎯 FPS 統計:")
            print(f"   平均 FPS: {avg_fps:.2f}")
            print(f"   最低 FPS: {min_fps:.2f}")
            print(f"   最高 FPS: {max_fps:.2f}")
            print(f"   標準差: {statistics.stdev(fps_values) if len(fps_values) > 1 else 0:.2f}")
        
        # 檔案大小統計
        if file_sizes:
            total_size = sum(file_sizes)
            avg_size = statistics.mean(file_sizes)
            
            print(f"\n💾 檔案大小統計:")
            print(f"   總大小: {total_size:.2f} MB")
            print(f"   平均大小: {avg_size:.2f} MB")
            print(f"   最大檔案: {max(file_sizes):.2f} MB")
            print(f"   最小檔案: {min(file_sizes):.2f} MB")
        
        # 品質狀態統計
        print(f"\n📈 品質狀態分佈:")
        status_names = {
            "excellent": "🟢 優秀",
            "good": "🟡 良好",
            "acceptable": "🟠 可接受", 
            "poor": "🔴 不良"
        }
        
        for status, count in status_counts.items():
            percentage = count / len(results) * 100
            print(f"   {status_names.get(status, status)}: {count} 個檔案 ({percentage:.1f}%)")
    
    def _generate_recommendations(self, results):
        """產生改進建議"""
        print("\n" + "=" * 60)
        print("💡 改進建議")
        print("=" * 60)
        
        poor_files = [r for r in results if r['fps_status'] == 'poor']
        large_files = [r for r in results if r['file_efficiency_mb_per_sec'] > 5]
        
        recommendations = []
        
        # FPS 相關建議
        if poor_files:
            recommendations.append(
                f"🔴 發現 {len(poor_files)} 個FPS不符合要求的檔案，建議：\n"
                f"   - 檢查攝影機設定是否正確設定為280 FPS\n"
                f"   - 確認系統效能是否足夠支援高幀率錄製\n"
                f"   - 檢查是否有其他程式占用系統資源"
            )
        
        # 檔案大小相關建議
        if large_files:
            recommendations.append(
                f"📁 發現 {len(large_files)} 個檔案較大，建議：\n"
                f"   - 考慮使用更高效的編碼格式（如H.264）\n"
                f"   - 調整畫質設定以平衡檔案大小和品質\n"
                f"   - 定期清理舊的錄製檔案"
            )
        
        # 編碼一致性建議
        codecs = set(r['codec'] for r in results)
        if len(codecs) > 1:
            recommendations.append(
                f"🔧 發現使用了多種編碼格式 {list(codecs)}，建議：\n"
                f"   - 統一使用同一種編碼格式以確保一致性\n"
                f"   - 建議使用H.264編碼以獲得更好的壓縮效率"
            )
        
        # 一般性建議
        if not poor_files and not large_files:
            recommendations.append(
                "✅ 所有檔案品質良好！建議：\n"
                "   - 繼續保持當前的錄製設定\n"
                "   - 定期監控錄製品質\n"
                "   - 考慮建立自動化的品質檢查流程"
            )
        
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec}")
    
    def export_analysis_report(self, output_file="recording_analysis_report.json"):
        """匯出分析報告"""
        video_files = self._get_video_files()
        if not video_files:
            return
            
        analysis_results = []
        for video_file in video_files:
            result = self._analyze_single_file(video_file)
            if result:
                # 轉換datetime為字串以便JSON序列化
                result['creation_time'] = result['creation_time'].isoformat()
                analysis_results.append(result)
        
        report = {
            'analysis_date': datetime.now().isoformat(),
            'expected_fps': self.expected_fps,
            'tolerance_percent': self.tolerance_percent,
            'total_files': len(analysis_results),
            'results': analysis_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 分析報告已匯出至: {output_file}")

def main():
    """主函式"""
    analyzer = RecordingQualityAnalyzer()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "export":
            analyzer.export_analysis_report()
        elif sys.argv[1] == "analyze":
            analyzer.analyze_all_recordings()
        else:
            print("用法:")
            print("  python recording_quality_analyzer.py analyze  # 分析所有檔案")
            print("  python recording_quality_analyzer.py export   # 匯出分析報告")
    else:
        # 預設執行完整分析
        analyzer.analyze_all_recordings()

if __name__ == "__main__":
    main()
