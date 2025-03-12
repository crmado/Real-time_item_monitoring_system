"""
系統控制器
負責協調整個系統的運作，包括 UI 和偵測系統的互動
"""

import logging
import os
import subprocess
import time
from tkinter import messagebox, ttk
import tkinter as tk
import json

from utils.language import get_text, change_language
from models.camera_manager import CameraManager
from controllers.detection_controller import DetectionController
from utils.ui_style_manager import UIStyleManager
from views.components.setting.settings_dialog import SettingsDialog
from utils.config import Config


class SystemController:
    """系統控制器類別"""

    def __init__(self, main_window=None):
        """
        初始化系统控制器

        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window
        
        # 初始化相机管理器
        self.camera_manager = CameraManager()
        
        # 初始化检测控制器
        self.detection_controller = DetectionController(self.camera_manager)
        
        # 状态标志
        self.is_running = False
        self.monitoring_active = False
        self.photo_mode_active = False
        self.current_mode = "monitoring"  # 默认为监控模式
        
        # 当前照片
        self.current_photo = None
        
        # 初始化設置
        self.settings = self.load_settings()
        
        # 绑定事件
        if main_window:
            self.bind_events()
        
        # 初始化 UI 樣式管理器
        self.ui_style_manager = UIStyleManager(main_window)
        
        # 初始化計時器
        self.update_timer = None
        self.fps_update_timer = None
        
        # 初始化性能統計
        self.frame_times = []
        self.last_fps_update = time.time()
        
        # 設置日誌
        logging.basicConfig(level=logging.INFO)

    def initialize(self, main_window):
        """
        初始化系統
        
        Args:
            main_window: 主窗口對象
        """
        self.main_window = main_window
        
        # 應用 UI 樣式
        self.ui_style_manager.apply_theme()
        
        # 綁定事件
        self.bind_events()

        # 注册检测控制器回调
        self.register_detection_callbacks()

        # 更新相機源列表
        self.update_camera_sources()
        
        # 默認選擇第一個相機
        sources = self.camera_manager.get_available_sources()
        if sources:
            self.main_window.control_panel.set_camera_source(sources[0])
            # 自動開啟第一個相機
            self.handle_camera_open(sources[0])
            
        # 開始更新 UI
        self.start_ui_update()

    def bind_events(self):
        """綁定事件處理函數"""
        # 綁定控制面板事件
        self.main_window.control_panel.callbacks = {
            'start': self.handle_start_button,
            'stop': self.handle_stop_button,
            'settings': self.handle_settings_button,
            'mode_changed': self.handle_mode_switch,
            'camera_selected': self.handle_camera_selection,
            'refresh_preview': self.handle_refresh_preview
        }
        
        # 如果控制面板有 set_callbacks 方法，使用它來設置回調
        if hasattr(self.main_window.control_panel, 'set_callbacks'):
            self.main_window.control_panel.set_callbacks({
                'start': self.handle_start_button,
                'stop': self.handle_stop_button,
                'settings': self.handle_settings_button,
                'mode_changed': self.handle_mode_switch,
                'camera_selected': self.handle_camera_selection,
                'refresh_preview': self.handle_refresh_preview
            })
        
        # 綁定視頻面板事件
        self.main_window.video_panel.set_callback('roi_drag_start', self.handle_roi_selection)
        self.main_window.video_panel.set_callback('roi_drag', self.handle_roi_selection)
        self.main_window.video_panel.set_callback('roi_drag_end', self.handle_roi_selection)
        
        # 绑定照片面板事件
        photo_panel = self.main_window.photo_panel
        photo_panel.set_callback('capture', self.handle_photo_capture)
        photo_panel.set_callback('analyze', self.handle_photo_analysis)

    def register_detection_callbacks(self):
        """註冊偵測控制器的回調函數"""
        # 保留原有回調註冊
        self.detection_controller.set_callback(
            'monitoring_started',
            lambda: self.main_window.control_panel.update_start_button_text(True)
        )

        self.detection_controller.set_callback(
            'monitoring_stopped',
            lambda: self.main_window.control_panel.update_start_button_text(False)
        )

        # 确保 settings_panel 已初始化
        if hasattr(self.main_window, 'settings_panel') and self.main_window.settings_panel is not None:
            self.detection_controller.set_callback(
                'count_updated',
                self.main_window.settings_panel.update_count
            )

        self.detection_controller.set_callback(
            'frame_processed',
            self.main_window.video_panel.update_image
        )

        self.detection_controller.set_callback(
            'test_started',
            lambda: self.main_window.control_panel.update_test_button_text(True)
        )

        self.detection_controller.set_callback(
            'test_stopped',
            lambda: self.main_window.control_panel.update_test_button_text(False)
        )

        # 新增拍照模式回調
        self.detection_controller.set_callback(
            'camera_preview_updated',
            lambda frame: self.main_window.photo_panel and self.main_window.photo_panel.update_camera_preview(
                frame)
        )

        self.detection_controller.set_callback(
            'photo_captured',
            lambda frame: self.main_window.photo_panel and self.main_window.photo_panel.update_photo_preview(
                frame)
        )

        self.detection_controller.set_callback(
            'photo_analyzed',
            self.handle_analysis_results
        )

        self.detection_controller.set_callback(
            'analysis_error',
            self.handle_analysis_error
        )

    def handle_test_camera(self):
        """處理測試攝影機"""
        selected_source = self.main_window.control_panel.get_selected_source()
        if not selected_source:
            self.main_window.log_message(get_text("error_source", "錯誤：請選擇視訊來源"))
            return

        # 輸出畫面到視窗
        self.detection_controller.test_camera(selected_source)

    def handle_start_button(self):
        """處理開始按鈕點擊事件"""
        try:
            # 獲取當前選擇的相機
            selected_source = self.main_window.control_panel.selected_camera.get()
            logging.info(f"點擊開始按鈕，選擇的相機源: {selected_source}")
            print(f"點擊開始按鈕，選擇的相機源: {selected_source}")
            
            if not selected_source:
                error_msg = "請選擇一個相機源"
                logging.error(error_msg)
                print(error_msg)
                self.show_error(error_msg)
                return

            # 更新UI狀態
            logging.info("更新UI狀態為運行中")
            print("更新UI狀態為運行中")
            self.main_window.control_panel.update_button_states(True)
            self.main_window.control_panel.set_status(get_text("status_running", "正在運行"))
            
            # 根據當前模式啟動相應功能
            logging.info(f"當前模式: {self.current_mode}")
            print(f"當前模式: {self.current_mode}")
            if self.current_mode == "monitoring":
                logging.info("啟動監控模式")
                print("啟動監控模式")
                self.start_monitoring(selected_source)
            else:
                logging.info("啟動拍照模式")
                print("啟動拍照模式")
                self.start_photo_mode(selected_source)
                
        except Exception as e:
            error_msg = f"啟動失敗: {str(e)}"
            logging.error(error_msg)
            print(error_msg)
            self.show_error(error_msg)
            self.main_window.control_panel.update_button_states(False)
            
    def handle_stop_button(self):
        """處理停止按鈕點擊事件"""
        try:
            logging.info("點擊停止按鈕")
            print("點擊停止按鈕")
            
            # 停止當前運行的功能
            if self.is_running:
                logging.info("停止當前運行的功能")
                print("停止當前運行的功能")
                self.stop_current_operation()
                
            # 更新UI狀態
            logging.info("更新UI狀態為已停止")
            print("更新UI狀態為已停止")
            self.main_window.control_panel.update_button_states(False)
            self.main_window.control_panel.set_status(get_text("status_stopped", "已停止"))
            
        except Exception as e:
            error_msg = f"停止失敗: {str(e)}"
            logging.error(error_msg)
            print(error_msg)
            self.show_error(error_msg)
            
    def handle_settings_button(self):
        """處理設置按鈕點擊事件"""
        # 打開設置對話框
        self._on_settings()
        
    def handle_mode_switch(self, mode):
        """
        處理模式切換事件
        
        Args:
            mode: 新的模式 ("monitoring" 或 "photo")
        """
        logging.info(f"切換模式: {mode}, 當前模式: {self.current_mode}")
        print(f"切換模式: {mode}, 當前模式: {self.current_mode}")
        
        if mode == self.current_mode:
            logging.info("模式未變更，不執行切換")
            print("模式未變更，不執行切換")
            return
            
        # 停止當前運行的功能
        if self.is_running:
            logging.info("停止當前運行的功能")
            print("停止當前運行的功能")
            self.stop_current_operation()
            self.main_window.control_panel.update_button_states(False)
            
        # 更新當前模式
        self.current_mode = mode
        logging.info(f"已更新當前模式為: {mode}")
        print(f"已更新當前模式為: {mode}")
        
        # 切換UI顯示
        if mode == "monitoring":
            logging.info("切換到監控模式UI")
            print("切換到監控模式UI")
            self.main_window.switch_mode("monitoring")
            self.main_window.control_panel.set_status(get_text("status_monitoring_mode", "監控模式"))
        else:
            logging.info("切換到拍照模式UI")
            print("切換到拍照模式UI")
            self.main_window.switch_mode("photo")
            self.main_window.control_panel.set_status(get_text("status_photo_mode", "拍照模式"))
            
    def start_monitoring(self, source):
        """
        啟動監控模式
        
        Args:
            source: 相機源
        """
        try:
            logging.info(f"開始啟動監控模式，相機源: {source}")
            
            # 打開相機
            logging.info("嘗試打開相機...")
            success = self.camera_manager.open_camera(source)
            if not success:
                error_msg = f"無法打開相機: {source}"
                logging.error(error_msg)
                self.show_error(error_msg)
                self.main_window.control_panel.update_button_states(False)
                return
                
            logging.info(f"成功打開相機: {source}")
            
            # 啟動視頻流
            self.is_running = True
            self.monitoring_active = True
            logging.info("開始更新視頻幀...")
            self.update_video_frame()
            
            # 啟動檢測
            if self.detection_controller:
                logging.info("啟動物體檢測...")
                self.detection_controller.start_detection()
                
            logging.info("監控模式啟動成功")
                
        except Exception as e:
            error_msg = f"啟動監控失敗: {str(e)}"
            logging.error(error_msg)
            self.show_error(error_msg)
            self.main_window.control_panel.update_button_states(False)
            self.is_running = False
            self.monitoring_active = False
            
    def start_photo_mode(self, source):
        """
        啟動拍照模式
        
        Args:
            source: 相機源
        """
        try:
            # 打開相機
            success = self.camera_manager.open_camera(source)
            if not success:
                self.show_error(f"無法打開相機: {source}")
                self.main_window.control_panel.update_button_states(False)
                return
                
            # 啟動視頻流預覽
            self.is_running = True
            self.photo_mode_active = True
            self.update_photo_preview()
            
        except Exception as e:
            self.show_error(f"啟動拍照模式失敗: {str(e)}")
            self.main_window.control_panel.update_button_states(False)
            self.is_running = False
            self.photo_mode_active = False
            
    def stop_current_operation(self):
        """停止當前運行的操作"""
        # 停止視頻流
        self.is_running = False
        self.monitoring_active = False
        self.photo_mode_active = False
        
        # 停止檢測
        if self.detection_controller:
            self.detection_controller.stop_detection()
            
        # 釋放相機資源
        self.camera_manager.release_all_cameras()
        
    def update_video_frame(self):
        """更新視頻幀"""
        if not self.is_running or not self.monitoring_active:
            return
            
        try:
            # 讀取一幀
            ret, frame = self.camera_manager.read_frame()
            if ret and frame is not None:
                print(f"成功讀取視頻幀，尺寸: {frame.shape}")
                logging.debug(f"成功讀取視頻幀，尺寸: {frame.shape}")
                
                # 如果有檢測控制器，進行物體檢測
                if self.detection_controller:
                    processed_frame = self.detection_controller.process_frame(frame)
                    if processed_frame is not None:
                        # 更新視頻面板
                        self.main_window.video_panel.update_image(processed_frame)
                        print("已更新視頻面板顯示")
                    else:
                        print("處理後的幀為空，無法更新視頻面板")
                        # 直接顯示原始幀
                        self.main_window.video_panel.update_image(frame)
                else:
                    # 直接顯示原始幀
                    self.main_window.video_panel.update_image(frame)
                    print("無檢測控制器，直接顯示原始幀")
                
                # 每 100 幀輸出一次日誌
                if hasattr(self, 'frame_count'):
                    self.frame_count += 1
                    if self.frame_count % 100 == 0:
                        logging.debug(f"已處理 {self.frame_count} 幀，幀尺寸: {frame.shape}")
                else:
                    self.frame_count = 1
                    logging.info(f"開始處理視頻幀，首幀尺寸: {frame.shape}")
            else:
                logging.warning("讀取幀失敗或幀為空")
                print("讀取幀失敗或幀為空")
                
            # 繼續更新
            self.main_window.root.after(15, self.update_video_frame)
            
        except Exception as e:
            logging.error(f"更新視頻幀時出錯: {str(e)}")
            print(f"更新視頻幀時出錯: {str(e)}")
            self.is_running = False
            self.monitoring_active = False
            
    def update_photo_preview(self):
        """更新照片預覽"""
        if not self.is_running or not self.photo_mode_active:
            return
            
        try:
            # 讀取一幀
            ret, frame = self.camera_manager.read_frame()
            if ret and frame is not None:
                # 更新照片面板的相機預覽
                self.main_window.photo_panel.update_camera_preview(frame)
                
            # 繼續更新
            self.main_window.root.after(15, self.update_photo_preview)
            
        except Exception as e:
            logging.error(f"更新照片預覽時出錯: {str(e)}")
            self.is_running = False
            self.photo_mode_active = False
            self.main_window.control_panel.update_button_states(False)
            
    def handle_photo_capture(self):
        """處理拍照事件"""
        if not self.is_running or not self.photo_mode_active:
            return
            
        try:
            # 讀取一幀作為照片
            ret, frame = self.camera_manager.read_frame()
            if ret and frame is not None:
                # 更新照片面板的照片預覽
                self.main_window.photo_panel.update_photo_preview(frame)
                # 保存照片
                self.current_photo = frame.copy()
                
        except Exception as e:
            self.show_error(f"拍照失敗: {str(e)}")
            
    def handle_photo_analysis(self):
        """處理照片分析事件"""
        if self.current_photo is None:
            self.show_error("沒有可分析的照片")
            return
            
        try:
            # 顯示進度條
            self.main_window.photo_panel.show_progress()
            
            # 使用檢測控制器分析照片
            if self.detection_controller:
                result_frame = self.detection_controller.process_frame(self.current_photo.copy())
                # 更新照片預覽
                self.main_window.photo_panel.update_photo_preview(result_frame)
                
            # 隱藏進度條
            self.main_window.photo_panel.hide_progress()
            
        except Exception as e:
            self.show_error(f"分析照片失敗: {str(e)}")
            # 隱藏進度條
            self.main_window.photo_panel.hide_progress()

    def handle_apply_settings(self):
        """處理應用設定"""
        settings = self.main_window.settings_panel.get_settings()
        if settings:
            # 檢查鍵名格式
            target_count = settings.get('detection.target_count',
                                        settings.get('target_count'))  # 嘗試兩種可能的鍵名
            buffer_point = settings.get('detection.buffer_point',
                                        settings.get('buffer_point'))  # 嘗試兩種可能的鍵名

            if target_count is not None and buffer_point is not None:
                if self.detection_controller.update_settings(
                        target_count,
                        buffer_point
                ):
                    # 更新配置
                    self.config.update(settings)

                    self.main_window.log_message(
                        get_text("settings_updated", "更新設定 - 預計數量：{0}，緩衝點：{1}").format(
                            target_count,
                            buffer_point
                        )
                    )
                else:
                    self.main_window.log_message(get_text("settings_update_failed", "設定更新失敗"))
            else:
                self.main_window.log_message("錯誤：無法獲取預計數量或緩衝點設定")

    def handle_language_change(self, language_code):
        """
        處理語言變更

        Args:
            language_code: 語言代碼
        """
        # 更新主視窗和所有組件的語言
        self.main_window.on_language_changed(language_code)

    def handle_roi_selection(self, event):
        """處理ROI選擇事件"""
        logging.info(f"系統控制器收到 ROI 選擇事件，位置: {event.y}")
        print(f"系統控制器收到 ROI 選擇事件，位置: {event.y}")
        
        if self.detection_controller:
            # 直接調用 detection_controller 的方法處理 ROI 選擇
            self.detection_controller.start_roi_drag(event)
            self.detection_controller.update_roi_position(event)
            self.detection_controller.stop_roi_drag()
        else:
            logging.error("檢測控制器未初始化，無法處理 ROI 選擇事件")
            print("檢測控制器未初始化，無法處理 ROI 選擇事件")

    def handle_theme_change(self, theme_name):
        """
        處理主題變更

        Args:
            theme_name: 主題名稱
        """
        try:
            logging.info(f"變更主題為: {theme_name}")
            print(f"變更主題為: {theme_name}")
            
            # 更新設置
            self.settings['theme'] = theme_name
            self.save_settings()
            
            # 應用主題
            if theme_name == "dark":
                self.apply_dark_theme()
            else:
                self.apply_light_theme()
                
            # 更新狀態欄
            if hasattr(self.main_window, 'status_bar'):
                self.main_window.status_bar.set_status(
                    get_text("theme_changed", "已切換至{}模式").format(
                        get_text(f"theme_{theme_name}", theme_name)
                    )
                )
                
            # 不再使用 log_message 方法，避免錯誤
            # 如果需要記錄日誌，使用 logging 模組
            logging.info(get_text("theme_changed", "已切換至{}模式").format(
                get_text(f"theme_{theme_name}", theme_name)
            ))
            
        except Exception as e:
            logging.error(f"變更主題時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def check_for_updates(self):
        """檢查系統更新"""
        try:
            if not os.path.exists('.git'):
                self.main_window.log_message(get_text("version_control_not_set", "版本控制未設定，跳過更新檢查"))
                return

            result = subprocess.run(
                ['git', 'remote', '-v'],
                capture_output=True,
                text=True
            )

            if 'origin' not in result.stdout:
                self.main_window.log_message(get_text("remote_not_set", "遠端儲存庫未設定，跳過更新檢查"))
                return

            subprocess.run(['git', 'fetch', 'origin'], check=True)

            result = subprocess.run(
                ['git', 'status', '-uno'],
                capture_output=True,
                text=True
            )

            if "Your branch is behind" in result.stdout:
                self.prompt_update()

        except Exception as e:
            self.main_window.log_message(get_text("update_check_error", "檢查更新時發生錯誤：{}").format(str(e)))

    def prompt_update(self):
        """提示更新"""
        if messagebox.askyesno(
            get_text("update_tips", "更新提示"),
            get_text("update_tips_msg", "發現新版本，是否更新？")
        ):
            self.perform_update()

    def perform_update(self):
        """執行更新"""
        try:
            subprocess.run(['git', 'pull'], check=True)
            messagebox.showinfo(
                get_text("update_complete", "更新完成"),
                get_text("update_complete_msg", "程式已更新，請重新啟動")
            )
            self.main_window.root.quit()
        except Exception as e:
            messagebox.showerror(
                get_text("update_failed", "更新失敗"),
                get_text("update_failed_msg", "更新過程中發生錯誤：{}").format(str(e))
            )

    def handle_camera_selection(self, source):
        """
        处理相机选择事件
        
        Args:
            source: 选择的相机源
        """
        logging.info(f"选择相机: {source}")
        # 如果有需要，可以在这里添加相机选择的处理逻辑

    def handle_camera_open(self, source):
        """
        處理開啟相機

        Args:
            source: 相機源
        """
        try:
            # 開啟相機
            print(f"嘗試打開相機源: {source}")
            logging.info(f"嘗試打開相機源: {source}")
            success = self.camera_manager.open_camera(source)
            
            if success:
                print(f"成功打開相機: {source}")
                logging.info(f"成功開啟相機: {source}")
                
                # 確保按鈕狀態正確 - 相機開啟後，開始按鈕應該是可點擊的
                self.main_window.control_panel.update_button_states(False)
                print("更新按鈕狀態：開始按鈕可點擊")
                logging.info("更新按鈕狀態：開始按鈕可點擊")
                
                # 顯示相機預覽 - 讀取一幀並顯示
                ret, frame = self.camera_manager.read_frame()
                if ret and frame is not None:
                    # 如果有檢測控制器，處理幀以顯示 ROI 線
                    if self.detection_controller:
                        processed_frame = self.detection_controller.process_frame(frame)
                        if processed_frame is not None:
                            self.main_window.video_panel.update_image(processed_frame)
                            print("已顯示相機預覽（帶 ROI 線）")
                            logging.info("已顯示相機預覽（帶 ROI 線）")
                        else:
                            self.main_window.video_panel.update_image(frame)
                            print("已顯示相機預覽（原始幀）")
                            logging.info("已顯示相機預覽（原始幀）")
                    else:
                        self.main_window.video_panel.update_image(frame)
                        print("已顯示相機預覽（原始幀）")
                        logging.info("已顯示相機預覽（原始幀）")
                else:
                    print("無法讀取相機幀進行預覽")
                    logging.warning("無法讀取相機幀進行預覽")
                
                # 如果在監控模式，不要自動開始監控，讓用戶手動點擊開始按鈕
                if self.current_mode == "monitoring":
                    print("相機已準備好，等待用戶點擊開始按鈕啟動監控")
                    logging.info("相機已準備好，等待用戶點擊開始按鈕啟動監控")
                    # 不要自動調用 self.start_monitoring(source)
                    
                # 如果在拍照模式，不要自動開始預覽，讓用戶手動點擊開始按鈕
                elif self.current_mode == "photo":
                    print("相機已準備好，等待用戶點擊開始按鈕啟動拍照模式")
                    logging.info("相機已準備好，等待用戶點擊開始按鈕啟動拍照模式")
                    # 不要自動調用 self.start_photo_mode(source)
            else:
                print(f"無法打開相機: {source}")
                logging.error(f"無法開啟相機: {source}")
                self.show_error(f"無法開啟相機: {source}")

        except Exception as e:
            print(f"打開相機時發生錯誤: {str(e)}")
            logging.error(f"開啟相機時發生錯誤: {str(e)}")
            self.show_error(f"開啟相機時發生錯誤: {str(e)}")
            
    def start_ui_update(self):
        """启动UI更新"""
        # 更新时间显示
        self._update_time()
        
    def _update_time(self):
        """更新時間顯示"""
        try:
            # 獲取當前時間
            import time
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 更新狀態欄時間顯示
            if hasattr(self.main_window, 'status_label'):
                self.main_window.status_label.config(text=current_time)
                
            # 每秒更新一次
            self.main_window.root.after(1000, self._update_time)

        except Exception as e:
            logging.error(f"更新時間顯示時出錯: {str(e)}")

    def show_error(self, message):
        """
        顯示錯誤訊息
        
        Args:
            message: 錯誤訊息
        """
        logging.error(message)
        
        # 在狀態欄顯示錯誤
        if hasattr(self.main_window, 'control_panel'):
            self.main_window.control_panel.set_status(f"錯誤: {message}")
            
        # 彈出錯誤對話框
        from tkinter import messagebox
        messagebox.showerror("錯誤", message)

    def _on_settings(self):
        """打開設置對話框"""
        try:
            logging.info("打開設置對話框")
            print("打開設置對話框")
            
            # 檢查設置是否已初始化
            if not hasattr(self, 'settings'):
                self.settings = {}
                logging.info("初始化設置字典")
                print("初始化設置字典")
            
            # 創建設置對話框
            config_manager = Config()
            
            # 將當前設置轉換為 Config 格式
            for key, value in self.settings.items():
                config_manager.set(key, value)
            
            # 創建並顯示設置對話框
            settings_dialog = SettingsDialog(self.main_window, config_manager)
            
            # 等待對話框關閉
            self.main_window.wait_window(settings_dialog)
            
            # 檢查結果
            if not settings_dialog.result:
                logging.info("用戶取消設置")
                print("用戶取消設置")
                return
                
            # 獲取新設置
            new_settings_dict = settings_dialog.get_settings()
            if not new_settings_dict:
                logging.warning("無法獲取設置")
                print("無法獲取設置")
                return
                
            # 將 Config 格式的設置轉換為我們的格式
            new_settings = {}
            for key, value in new_settings_dict.items():
                # 移除前綴，例如 'system.language' -> 'language'
                simple_key = key.split('.')[-1]
                new_settings[simple_key] = value
                
            # 更新設置
            old_language = self.settings.get('language', 'zh_TW')
            old_theme = self.settings.get('theme', 'light')
            
            # 獲取新設置
            new_language = new_settings.get('language', old_language)
            new_theme = new_settings.get('theme', old_theme)
            new_target_count = int(new_settings.get('target_count', 1000))
            new_buffer_point = int(new_settings.get('buffer_point', 950))
            
            # 更新設置
            self.settings = new_settings
            self.save_settings()
            
            # 更新檢測控制器設置
            if self.detection_controller:
                self.detection_controller.set_target_count(new_target_count)
                self.detection_controller.set_buffer_point(new_buffer_point)
                
                # 設置 ROI 位置
                roi_default_position = float(new_settings.get('roi_default_position', 0.5))
                if hasattr(self.camera_manager, 'current_frame') and self.camera_manager.current_frame is not None:
                    height = self.camera_manager.current_frame.shape[0]
                    self.detection_controller.roi_y = int(height * roi_default_position)
                    self.detection_controller.saved_roi_percentage = roi_default_position
                    logging.info(f"設置 ROI 位置: {self.detection_controller.roi_y}, 百分比: {roi_default_position}")
                    print(f"設置 ROI 位置: {self.detection_controller.roi_y}, 百分比: {roi_default_position}")
                else:
                    # 如果當前沒有幀，設置一個標誌，在下一幀處理時更新 ROI 位置
                    self.detection_controller.saved_roi_percentage = roi_default_position
                    self.detection_controller.roi_needs_update = True
                    logging.info(f"設置 ROI 百分比: {roi_default_position}，將在下一幀更新位置")
                    print(f"設置 ROI 百分比: {roi_default_position}，將在下一幀更新位置")
            
            # 更新語言
            if new_language != old_language:
                logging.info(f"變更語言為: {new_language}")
                print(f"變更語言為: {new_language}")
                self.handle_language_change(new_language)
                
            # 更新主題
            if new_theme != old_theme:
                logging.info(f"變更主題為: {new_theme}")
                print(f"變更主題為: {new_theme}")
                self.handle_theme_change(new_theme)
                
            # 更新狀態欄 - 檢查不同的可能性
            status_message = get_text("settings_updated", "設置已更新")
            logging.info(status_message)
            print(status_message)
            
            # 嘗試不同的方式更新狀態
            if hasattr(self.main_window, 'status_bar') and hasattr(self.main_window.status_bar, 'set_status'):
                # 如果有 status_bar 對象且有 set_status 方法
                self.main_window.status_bar.set_status(status_message)
            elif hasattr(self.main_window, 'control_panel') and hasattr(self.main_window.control_panel, 'set_status'):
                # 如果有 control_panel 對象且有 set_status 方法
                self.main_window.control_panel.set_status(status_message)
            elif hasattr(self.main_window, 'set_status'):
                # 如果 main_window 本身有 set_status 方法
                self.main_window.set_status(status_message)
                
            # 嘗試刷新預覽
            try:
                self.refresh_preview()
            except Exception as e:
                logging.error(f"刷新預覽時出錯: {str(e)}")
                print(f"刷新預覽時出錯: {str(e)}")
                
        except Exception as e:
            logging.error(f"打開設置對話框時出錯: {str(e)}")
            print(f"打開設置對話框時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            logging.error("無法打開設置對話框")
            
    def update_camera_sources(self):
        """更新相機源列表"""
        try:
            # 獲取可用的相機源
            sources = self.camera_manager.get_available_sources()
            
            # 更新控制面板的相機源列表
            if hasattr(self.main_window, 'control_panel'):
                self.main_window.control_panel.set_camera_sources(sources)
                
            logging.info(f"已更新相機源列表: {sources}")
            return sources
        except Exception as e:
            logging.error(f"更新相機源列表時出錯: {str(e)}")
            return []

    def refresh_preview(self):
        """刷新相機預覽畫面"""
        try:
            logging.info("刷新相機預覽畫面")
            print("刷新相機預覽畫面")
            
            # 檢查 main_window 和 video_panel 是否存在
            if not hasattr(self, 'main_window') or self.main_window is None:
                logging.error("無法刷新預覽：main_window 不存在")
                print("無法刷新預覽：main_window 不存在")
                return False
                
            if not hasattr(self.main_window, 'video_panel') or self.main_window.video_panel is None:
                logging.error("無法刷新預覽：video_panel 不存在")
                print("無法刷新預覽：video_panel 不存在")
                return False
                
            # 檢查當前模式
            if hasattr(self.main_window, 'current_mode') and self.main_window.current_mode != "monitoring":
                logging.warning(f"當前模式不是監控模式，而是 {self.main_window.current_mode}，切換到監控模式")
                print(f"當前模式不是監控模式，而是 {self.main_window.current_mode}，切換到監控模式")
                self.main_window.switch_mode("monitoring")
            
            # 檢查相機是否已打開
            if not hasattr(self.camera_manager, 'current_frame') or self.camera_manager.current_frame is None:
                logging.info("相機未打開或沒有當前幀，嘗試讀取一幀")
                print("相機未打開或沒有當前幀，嘗試讀取一幀")
                
                # 嘗試讀取一幀
                ret, frame = self.camera_manager.read_frame()
                if not ret or frame is None:
                    logging.warning("無法讀取相機幀進行預覽刷新")
                    print("無法讀取相機幀進行預覽刷新")
                    return False
                    
                logging.info(f"成功讀取一幀，尺寸: {frame.shape}")
                print(f"成功讀取一幀，尺寸: {frame.shape}")
            else:
                # 使用當前幀
                frame = self.camera_manager.current_frame.copy()
                logging.info(f"使用當前幀，尺寸: {frame.shape}")
                print(f"使用當前幀，尺寸: {frame.shape}")
                
            # 檢查 detection_controller 是否存在
            if not hasattr(self, 'detection_controller') or self.detection_controller is None:
                logging.warning("檢測控制器不存在，直接顯示原始幀")
                print("檢測控制器不存在，直接顯示原始幀")
                self.main_window.video_panel.update_image(frame)
                logging.info("已刷新相機預覽（原始幀）")
                print("已刷新相機預覽（原始幀）")
                return True
                
            # 如果有檢測控制器，處理幀以顯示 ROI 線
            processed_frame = self.detection_controller.process_frame(frame)
            if processed_frame is not None:
                logging.info(f"成功處理幀，尺寸: {processed_frame.shape}")
                print(f"成功處理幀，尺寸: {processed_frame.shape}")
                
                # 確保 video_panel 可見
                if hasattr(self.main_window, 'current_mode') and self.main_window.current_mode != "monitoring":
                    logging.info("切換到監控模式以顯示視頻面板")
                    print("切換到監控模式以顯示視頻面板")
                    self.main_window.switch_mode("monitoring")
                
                # 更新圖像
                self.main_window.video_panel.update_image(processed_frame)
                logging.info("已刷新相機預覽（帶 ROI 線）")
                print("已刷新相機預覽（帶 ROI 線）")
                
                # 強制更新 Tkinter
                self.main_window.root.update_idletasks()
                logging.info("已強制更新 Tkinter 界面")
                print("已強制更新 Tkinter 界面")
                
                return True
            else:
                logging.warning("處理幀失敗，顯示原始幀")
                print("處理幀失敗，顯示原始幀")
                self.main_window.video_panel.update_image(frame)
                
                # 強制更新 Tkinter
                self.main_window.root.update_idletasks()
                logging.info("已強制更新 Tkinter 界面")
                print("已強制更新 Tkinter 界面")
                
                logging.info("已刷新相機預覽（原始幀）")
                print("已刷新相機預覽（原始幀）")
                return True
                
        except Exception as e:
            logging.error(f"刷新相機預覽時出錯: {str(e)}")
            print(f"刷新相機預覽時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def handle_refresh_preview(self):
        """處理刷新預覽按鈕點擊事件"""
        logging.info("刷新預覽按鈕被點擊")
        print("刷新預覽按鈕被點擊")
        
        # 嘗試刷新預覽
        if not self.refresh_preview():
            # 如果刷新失敗，嘗試打開相機
            logging.info("刷新預覽失敗，嘗試打開相機...")
            print("刷新預覽失敗，嘗試打開相機...")
            selected_source = self.main_window.control_panel.selected_camera.get()
            if selected_source:
                self.handle_camera_open(selected_source)
            else:
                self.show_error("請先選擇一個相機源")
                logging.error("無法刷新預覽：未選擇相機源")
                print("無法刷新預覽：未選擇相機源")

    def apply_dark_theme(self):
        """應用暗色主題"""
        try:
            # 如果有主題管理器，使用它
            if hasattr(self.main_window, 'theme_manager'):
                self.main_window.theme_manager.apply_theme("dark")
            else:
                # 否則直接設置基本的暗色主題
                style = ttk.Style()
                style.theme_use('alt')  # 使用替代主題作為基礎
                
                # 設置暗色背景和淺色文字
                style.configure('TFrame', background='#2E2E2E')
                style.configure('TLabel', background='#2E2E2E', foreground='#FFFFFF')
                style.configure('TButton', background='#444444', foreground='#FFFFFF')
                style.configure('TEntry', fieldbackground='#444444', foreground='#FFFFFF')
                
                # 更新主窗口背景
                if hasattr(self.main_window, 'configure'):
                    self.main_window.configure(background='#2E2E2E')
                    
                # 更新所有子窗口
                for widget in self.main_window.winfo_children():
                    if hasattr(widget, 'configure'):
                        widget.configure(background='#2E2E2E')
                        
                        # 遞歸更新子窗口
                        for child in widget.winfo_children():
                            if hasattr(child, 'configure'):
                                child.configure(background='#2E2E2E')
                                
                                if isinstance(child, tk.Label) or isinstance(child, ttk.Label):
                                    child.configure(foreground='#FFFFFF')
                
            logging.info("已應用暗色主題")
            print("已應用暗色主題")
            
        except Exception as e:
            logging.error(f"應用暗色主題時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def apply_light_theme(self):
        """應用亮色主題"""
        try:
            # 如果有主題管理器，使用它
            if hasattr(self.main_window, 'theme_manager'):
                self.main_window.theme_manager.apply_theme("light")
            else:
                # 否則直接設置基本的亮色主題
                style = ttk.Style()
                style.theme_use('default')  # 使用默認主題
                
                # 設置亮色背景和深色文字
                style.configure('TFrame', background='#F0F0F0')
                style.configure('TLabel', background='#F0F0F0', foreground='#000000')
                style.configure('TButton', background='#E0E0E0', foreground='#000000')
                style.configure('TEntry', fieldbackground='#FFFFFF', foreground='#000000')
                
                # 更新主窗口背景
                if hasattr(self.main_window, 'configure'):
                    self.main_window.configure(background='#F0F0F0')
                    
                # 更新所有子窗口
                for widget in self.main_window.winfo_children():
                    if hasattr(widget, 'configure'):
                        widget.configure(background='#F0F0F0')
                        
                        # 遞歸更新子窗口
                        for child in widget.winfo_children():
                            if hasattr(child, 'configure'):
                                child.configure(background='#F0F0F0')
                                
                                if isinstance(child, tk.Label) or isinstance(child, ttk.Label):
                                    child.configure(foreground='#000000')
                
            logging.info("已應用亮色主題")
            print("已應用亮色主題")
            
        except Exception as e:
            logging.error(f"應用亮色主題時出錯: {str(e)}")
            import traceback
            traceback.print_exc()

    def save_settings(self):
        """保存設置到配置文件"""
        try:
            # 確保設置目錄存在
            settings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
            if not os.path.exists(settings_dir):
                os.makedirs(settings_dir)
                
            # 設置文件路徑
            settings_file = os.path.join(settings_dir, 'settings.json')
            
            # 保存設置
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
                
            logging.info(f"設置已保存到 {settings_file}")
            print(f"設置已保存到 {settings_file}")
            return True
            
        except Exception as e:
            logging.error(f"保存設置時出錯: {str(e)}")
            print(f"保存設置時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def load_settings(self):
        """從配置文件加載設置"""
        try:
            # 設置文件路徑
            settings_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
            settings_file = os.path.join(settings_dir, 'settings.json')
            
            # 如果設置文件存在，加載設置
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                logging.info(f"已從 {settings_file} 加載設置")
                print(f"已從 {settings_file} 加載設置")
                return settings
            else:
                # 返回默認設置
                default_settings = {
                    'language': 'zh_TW',
                    'theme': 'light',
                    'target_count': 1000,
                    'buffer_point': 950,
                    'roi_default_position': 0.5
                }
                logging.info("使用默認設置")
                print("使用默認設置")
                return default_settings
                
        except Exception as e:
            logging.error(f"加載設置時出錯: {str(e)}")
            print(f"加載設置時出錯: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 返回默認設置
            return {
                'language': 'zh_TW',
                'theme': 'light',
                'target_count': 1000,
                'buffer_point': 950,
                'roi_default_position': 0.5
            }