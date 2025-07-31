"""
修復版 Basler 主程序
解決顯示和檢測問題
"""

import sys
from pathlib import Path
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
import threading
import time

# 添加 MVC 路徑
sys.path.insert(0, str(Path.cwd()))

from basler_mvc.models.basler_camera_model import BaslerCameraModel
from basler_mvc.models.detection_model import DetectionModel


class FixedBaslerApp:
    """修復版 Basler 應用程序"""
    
    def __init__(self):
        """初始化應用程序"""
        self.root = tk.Tk()
        self.root.title("🔧 修復版 Basler acA640-300gm 系統")
        self.root.geometry("1000x700")
        
        # 模型
        self.camera_model = BaslerCameraModel()
        self.detection_model = DetectionModel()
        
        # 狀態
        self.is_running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # UI 變量
        self.status_var = tk.StringVar(value="狀態: 就緒")
        self.camera_fps_var = tk.StringVar(value="相機: 0 FPS")
        self.object_count_var = tk.StringVar(value="物件: 0")
        
        # 創建UI
        self.create_ui()
        
        # 啟動更新循環
        self.update_display()
        
        logging.info("修復版應用程序初始化完成")
    
    def create_ui(self):
        """創建用戶界面"""
        # 控制面板
        control_frame = ttk.LabelFrame(self.root, text="🎮 控制", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="🔍 檢測相機", 
                  command=self.detect_cameras).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="🔗 連接相機", 
                  command=self.connect_camera).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="🚀 開始", 
                  command=self.start_capture).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="⏹️ 停止", 
                  command=self.stop_capture).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="🧪 測試檢測", 
                  command=self.test_detection).pack(side=tk.LEFT, padx=10)
        
        # 狀態面板
        status_frame = ttk.LabelFrame(self.root, text="📊 狀態", padding=5)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(status_frame, textvariable=self.status_var, 
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Label(status_frame, textvariable=self.camera_fps_var, 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=20)
        ttk.Label(status_frame, textvariable=self.object_count_var, 
                 font=('Arial', 10)).pack(side=tk.LEFT, padx=20)
        
        # 視頻顯示
        video_frame = ttk.LabelFrame(self.root, text="📺 實時視頻", padding=10)
        video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.video_label = ttk.Label(video_frame, text="點擊「連接相機」開始", 
                                    font=('Arial', 14))
        self.video_label.pack(expand=True)
    
    def detect_cameras(self):
        """檢測相機"""
        try:
            cameras = self.camera_model.detect_cameras()
            if cameras:
                info = f"檢測到 {len(cameras)} 台相機:\n\n"
                for i, camera in enumerate(cameras):
                    info += f"相機 {i+1}: {camera['model']}\n"
                    info += f"序列號: {camera['serial']}\n\n"
                messagebox.showinfo("檢測結果", info)
                self.status_var.set(f"狀態: 檢測到 {len(cameras)} 台相機")
            else:
                messagebox.showwarning("檢測結果", "未檢測到 Basler 相機")
                self.status_var.set("狀態: 未檢測到相機")
        except Exception as e:
            messagebox.showerror("錯誤", f"檢測失敗: {str(e)}")
    
    def connect_camera(self):
        """連接相機"""
        try:
            if self.camera_model.connect():
                info = self.camera_model.get_camera_info()
                self.status_var.set(f"狀態: 已連接 {info.get('model', 'Unknown')}")
                messagebox.showinfo("成功", f"相機連接成功!\n型號: {info.get('model')}")
            else:
                messagebox.showerror("錯誤", "相機連接失敗")
        except Exception as e:
            messagebox.showerror("錯誤", f"連接失敗: {str(e)}")
    
    def start_capture(self):
        """開始捕獲"""
        try:
            if not self.camera_model.is_connected:
                messagebox.showwarning("警告", "請先連接相機")
                return
            
            if self.camera_model.start_capture():
                self.is_running = True
                self.status_var.set("狀態: 🚀 捕獲中")
                logging.info("開始修復版捕獲")
            else:
                messagebox.showerror("錯誤", "無法開始捕獲")
        except Exception as e:
            messagebox.showerror("錯誤", f"啟動失敗: {str(e)}")
    
    def stop_capture(self):
        """停止捕獲"""
        try:
            self.is_running = False
            self.camera_model.stop_capture()
            self.status_var.set("狀態: 已停止")
            self.camera_fps_var.set("相機: 0 FPS")
            self.object_count_var.set("物件: 0")
        except Exception as e:
            logging.error(f"停止失敗: {str(e)}")
    
    def test_detection(self):
        """測試檢測功能"""
        try:
            # 創建測試圖像
            test_image = np.zeros((480, 640), dtype=np.uint8)
            
            # 繪製多個圓形
            cv2.circle(test_image, (200, 200), 30, 255, -1)
            cv2.circle(test_image, (400, 300), 25, 255, -1)
            cv2.circle(test_image, (500, 150), 35, 255, -1)
            
            # 調整檢測參數
            self.detection_model.update_parameters({
                'min_area': 500,   # 降低最小面積
                'max_area': 10000  # 提高最大面積
            })
            
            # 執行檢測
            objects, result_frame = self.detection_model.detect_frame(test_image)
            
            if len(objects) > 0:
                messagebox.showinfo("測試結果", f"檢測成功！\n檢測到 {len(objects)} 個圓形物件")
                
                # 顯示結果
                with self.frame_lock:
                    self.current_frame = result_frame
                self.object_count_var.set(f"物件: {len(objects)} (測試)")
            else:
                messagebox.showwarning("測試結果", "檢測失敗，未找到圓形物件")
                
        except Exception as e:
            messagebox.showerror("測試失敗", f"檢測測試失敗: {str(e)}")
    
    def update_display(self):
        """更新顯示循環"""
        try:
            if self.is_running and self.camera_model.is_grabbing:
                # 獲取最新幀
                frame = self.camera_model.get_latest_frame()
                if frame is not None:
                    # 執行檢測
                    objects, result_frame = self.detection_model.detect_frame(frame)
                    
                    # 更新幀和統計
                    with self.frame_lock:
                        self.current_frame = result_frame
                    
                    # 更新UI
                    stats = self.camera_model.get_stats()
                    self.camera_fps_var.set(f"相機: {stats['current_fps']:.1f} FPS")
                    self.object_count_var.set(f"物件: {len(objects)}")
            
            # 更新視頻顯示
            self.update_video_display()
            
        except Exception as e:
            logging.error(f"更新顯示錯誤: {str(e)}")
        
        # 30 FPS 更新率
        self.root.after(33, self.update_display)
    
    def update_video_display(self):
        """更新視頻顯示"""
        try:
            with self.frame_lock:
                if self.current_frame is None:
                    return
                frame = self.current_frame.copy()
            
            # 調整大小
            h, w = frame.shape[:2]
            max_size = 600
            
            if w > max_size or h > max_size:
                scale = min(max_size/w, max_size/h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h))
            
            # 轉換格式
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            elif len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 轉換為 Tkinter 格式
            pil_image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(pil_image)
            
            # 更新顯示
            if self.video_label.winfo_exists():
                self.video_label.configure(image=photo)
                self.video_label.image = photo
                
        except Exception as e:
            logging.error(f"視頻顯示錯誤: {str(e)}")
    
    def on_closing(self):
        """關閉處理"""
        try:
            self.stop_capture()
            self.camera_model.disconnect()
            self.root.destroy()
        except Exception as e:
            logging.error(f"關閉錯誤: {str(e)}")
            self.root.destroy()
    
    def run(self):
        """運行應用程序"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """主函數"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🔧 修復版 Basler acA640-300gm 系統")
    print("=" * 50)
    print("修復問題:")
    print("1. 相機FPS顯示問題")
    print("2. 檢測參數問題")
    print("3. 視頻顯示問題")
    print("=" * 50)
    
    try:
        app = FixedBaslerApp()
        app.run()
    except Exception as e:
        print(f"應用程序錯誤: {str(e)}")
        logging.error(f"應用程序錯誤: {str(e)}")


if __name__ == "__main__":
    main()