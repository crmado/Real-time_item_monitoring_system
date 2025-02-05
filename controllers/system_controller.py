"""
系統控制器
負責協調整個系統的運作，包括 UI 和偵測系統的互動
"""

import logging
import os
import subprocess
from tkinter import messagebox

class SystemController:
    """系統控制器類別"""

    def __init__(self, main_window, detection_controller):
        """
        初始化系統控制器

        Args:
            main_window: 主視窗實例
            detection_controller: 偵測控制器實例
        """
        self.main_window = main_window
        self.detection_controller = detection_controller
        self.version = "1.0.1"

        # 獲取UI組件
        self.components = main_window.get_components()

        # 設置可用的視訊來源
        available_sources = self.detection_controller.camera_manager.get_available_sources()
        self.components['control_panel'].set_camera_sources(available_sources)

        # 綁定事件處理函數
        self.bind_events()

        # 註冊偵測控制器的回調函數
        self.register_detection_callbacks()

    def bind_events(self):
        """綁定UI事件處理函數"""
        # 控制面板事件
        control_panel = self.components['control_panel']
        control_panel.set_callback('test', self.handle_test_camera)
        control_panel.set_callback('start', self.handle_toggle_monitoring)

        # 設定面板事件
        settings_panel = self.components['settings_panel']
        settings_panel.set_callback(self.handle_apply_settings)

        # 視訊面板事件
        video_panel = self.components['video_panel']
        video_panel.set_callback('roi_drag_start', self.handle_roi_drag_start)
        video_panel.set_callback('roi_drag', self.handle_roi_drag)
        video_panel.set_callback('roi_drag_end', self.handle_roi_drag_end)

    def register_detection_callbacks(self):
        """註冊偵測控制器的回調函數"""
        self.detection_controller.set_callback(
            'monitoring_started',
            lambda: self.components['control_panel'].update_start_button_text(True)
        )

        self.detection_controller.set_callback(
            'monitoring_stopped',
            lambda: self.components['control_panel'].update_start_button_text(False)
        )

        self.detection_controller.set_callback(
            'count_updated',
            self.components['settings_panel'].update_count
        )

        self.detection_controller.set_callback(
            'frame_processed',
            self.components['video_panel'].update_image
        )

        self.detection_controller.set_callback(
            'test_started',
            lambda: self.main_window.control_panel.update_test_button_text(True)
        )

        self.detection_controller.set_callback(
            'test_stopped',
            lambda: self.main_window.control_panel.update_test_button_text(False)
        )

        # 設定視訊面板的滑鼠事件
        self.main_window.video_panel.set_callback(
            'roi_drag_start',
            lambda event: self.detection_controller.start_roi_drag(event.y)
        )

        self.main_window.video_panel.set_callback(
            'roi_drag',
            lambda event: self.detection_controller.update_roi_position(event.y)
        )

        self.main_window.video_panel.set_callback(
            'roi_drag_end',
            lambda event: self.detection_controller.stop_roi_drag()
        )

    def handle_test_camera(self):
        """處理測試攝影機"""
        selected_source = self.components['control_panel'].get_selected_source()
        if not selected_source:
            self.main_window.log_message("錯誤：請選擇視訊來源")
            return

        # 輸出畫面到視窗
        self.detection_controller.test_camera(selected_source)


    def handle_toggle_monitoring(self):
        """處理開始/停止監測"""
        if not self.detection_controller.is_monitoring:
            selected_source = self.components['control_panel'].get_selected_source()
            if not selected_source:
                self.main_window.log_message("錯誤：請選擇視訊來源")
                return

            if self.detection_controller.start_monitoring(selected_source):
                self.main_window.log_message(f"開始監測 - {selected_source}")
            else:
                self.main_window.log_message("啟動監測失敗")
        else:
            self.detection_controller.stop_monitoring()
            self.main_window.log_message("停止監測")

    def handle_apply_settings(self):
        """處理應用設定"""
        settings = self.components['settings_panel'].get_settings()
        if settings:
            if self.detection_controller.update_settings(
                settings['target_count'],
                settings['buffer_point']
            ):
                self.main_window.log_message(
                    f"更新設定 - 預計數量: {settings['target_count']}, "
                    f"緩衝點: {settings['buffer_point']}"
                )
            else:
                self.main_window.log_message("設定更新失敗")

    def handle_roi_drag_start(self, event):
        """
        處理 ROI 拖曳開始

        Args:
            event: 滑鼠事件
        """
        self.detection_controller.start_roi_drag(event.y)

    def handle_roi_drag(self, event):
        """
        處理 ROI 拖曳

        Args:
            event: 滑鼠事件
        """
        self.detection_controller.update_roi_position(event.y)

    def handle_roi_drag_end(self, event):
        """
        處理 ROI 拖曳結束

        Args:
            event: 滑鼠事件
        """
        self.detection_controller.stop_roi_drag()

    def check_for_updates(self):
        """檢查系統更新"""
        try:
            if not os.path.exists('.git'):
                self.main_window.log_message("未設定版本控制，跳過更新檢查")
                return

            result = subprocess.run(
                ['git', 'remote', '-v'],
                capture_output=True,
                text=True
            )

            if 'origin' not in result.stdout:
                self.main_window.log_message("未設定遠端倉庫，跳過更新檢查")
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
            self.main_window.log_message(f"檢查更新時發生錯誤：{str(e)}")

    def prompt_update(self):
        """提示更新"""
        if messagebox.askyesno("更新提示", "發現新版本，是否要更新？"):
            self.perform_update()

    def perform_update(self):
        """執行更新"""
        try:
            subprocess.run(['git', 'pull'], check=True)
            messagebox.showinfo("更新完成", "程式已更新，請重新啟動")
            self.main_window.root.quit()
        except Exception as e:
            messagebox.showerror(
                "更新失敗",
                f"更新過程中發生錯誤：{str(e)}"
            )