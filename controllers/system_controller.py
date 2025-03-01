"""
系統控制器
負責協調整個系統的運作，包括 UI 和偵測系統的互動
"""

import logging
import os
import subprocess
from tkinter import messagebox

from utils.language import get_text, change_language
from utils.theme_manager import ThemeManager


class SystemController:
    """系統控制器類別"""

    def __init__(self, main_window, detection_controller, config_manager):
        """
        初始化系統控制器

        Args:
            main_window: 主視窗實例
            detection_controller: 偵測控制器實例
            config_manager: 配置管理器實例
        """
        self.main_window = main_window
        self.detection_controller = detection_controller
        self.config_manager = config_manager
        self.version = "1.0.0"

        # 獲取UI組件
        self.components = main_window.get_components()

        # 設置可用的視訊來源
        available_sources = self.detection_controller.camera_manager.get_available_sources()
        self.components['control_panel'].set_camera_sources(available_sources)

        # 自動選擇上次使用的相機源
        last_source = self.config_manager.get('camera.last_source', None)
        if last_source and last_source in available_sources:
            self.components['control_panel'].select_source(last_source)

        # 綁定事件處理函數
        self.bind_events()

        # 註冊偵測控制器的回調函數
        self.register_detection_callbacks()

        # 初始化主題管理器
        self.theme_manager = ThemeManager(main_window.root)

        # 應用語言設定
        language = self.config_manager.get('system.language', 'zh_TW')
        change_language(language)
        self.main_window.on_language_changed(language)

    def bind_events(self):
        """綁定UI事件處理函數"""
        # 控制面板事件
        control_panel = self.components['control_panel']
        control_panel.set_callback('test', self.handle_camera_selected)
        control_panel.set_callback('start', self.handle_toggle_monitoring)
        control_panel.set_callback('mode_switch', self.handle_mode_switch)  # 新增：模式切換

        # 設定面板事件
        settings_panel = self.components['settings_panel']
        settings_panel.set_callback('settings_applied', self.handle_apply_settings)
        settings_panel.set_callback('language_changed', self.handle_language_change)

        # 視訊面板事件
        video_panel = self.components['video_panel']
        video_panel.set_callback('roi_drag_start', self.handle_roi_drag_start)
        video_panel.set_callback('roi_drag', self.handle_roi_drag)
        video_panel.set_callback('roi_drag_end', self.handle_roi_drag_end)

        # 拍照面板事件
        photo_panel = self.components.get('photo_panel')
        if photo_panel:
            photo_panel.set_callback('capture_photo', self.handle_capture_photo)
            photo_panel.set_callback('analyze_photo', self.handle_analyze_photo)

        # 主題變更事件
        settings_panel = self.components['settings_panel']
        settings_panel.set_callback('theme_changed', self.handle_theme_change)

    def register_detection_callbacks(self):
        """註冊偵測控制器的回調函數"""
        # 保留原有回調註冊
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

        # 新增拍照模式回調
        self.detection_controller.set_callback(
            'camera_preview_updated',
            lambda frame: self.components.get('photo_panel') and self.components['photo_panel'].update_camera_preview(
                frame)
        )

        self.detection_controller.set_callback(
            'photo_captured',
            lambda frame: self.components.get('photo_panel') and self.components['photo_panel'].update_photo_preview(
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
            self.main_window.log_message(get_text("error_source", "錯誤：請選擇視訊來源"))
            return

        # 輸出畫面到視窗
        self.detection_controller.test_camera(selected_source)

    def handle_toggle_monitoring(self):
        """處理開始/停止監測"""
        if not self.detection_controller.is_monitoring:
            selected_source = self.components['control_panel'].get_selected_source()
            if not selected_source:
                self.main_window.log_message(get_text("error_source", "錯誤：請選擇視訊來源"))
                return

            # 關鍵修改：先停止任何進行中的相機測試
            if self.detection_controller.is_testing:
                self.detection_controller.stop_camera_test()
                # 短暫暫停，確保測試完全停止
                import time
                time.sleep(0.5)

            if self.detection_controller.start_monitoring(selected_source):
                self.main_window.log_message(get_text("start_monitoring", "開始監測 - {}").format(selected_source))
            else:
                self.main_window.log_message(get_text("monitoring_failed", "監測啟動失敗"))
        else:
            self.detection_controller.stop_monitoring()
            self.main_window.log_message(get_text("stop_monitoring", "停止監測"))

    def handle_apply_settings(self):
        """處理應用設定"""
        settings = self.components['settings_panel'].get_settings()
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
                    self.config_manager.update(settings)

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

    def handle_camera_selected(self):
        """處理相機選擇變更 (自動測試)"""
        selected_source = self.components['control_panel'].get_selected_source()
        if not selected_source:
            self.main_window.log_message(get_text("error_source", "錯誤：請選擇視訊來源"))
            return

        # 自動開始測試選擇的相機
        self.detection_controller.test_camera(selected_source)
        self.main_window.log_message(f"已選擇並測試相機 - {selected_source}")

    def handle_theme_change(self, theme):
        """
        處理主題變更

        Args:
            theme: 主題名稱 ('light' 或 'dark')
        """
        success = self.theme_manager.apply_theme(theme)
        if success:
            self.main_window.log_message(get_text("theme_changed", "已切換至{}模式").format(
                get_text("light_theme", "亮色") if theme == "light" else get_text("dark_theme", "暗色")
            ))

    # ==========================================================================
    # 添加新部分：拍照模式處理
    # ==========================================================================

    def handle_mode_switch(self):
        """處理模式切換"""
        # 切換主視窗顯示模式
        self.main_window.toggle_mode()

        # 暫停任何進行中的測試或監測
        if self.detection_controller.is_monitoring:
            self.detection_controller.stop_monitoring()

        if self.detection_controller.is_testing:
            self.detection_controller.stop_camera_test()

        # 設置控制器狀態
        current_mode = self.main_window.current_mode
        self.detection_controller.is_photo_mode = current_mode == "photo"

        # 如果切換到拍照模式，啟動相機預覽
        if current_mode == "photo":
            self.start_photo_mode()
        elif current_mode == "monitoring":
            self.detection_controller.cleanup_photo_resources()

    def start_photo_mode(self):
        """啟動拍照模式"""
        try:
            # 顯示載入狀態
            photo_panel = self.components.get('photo_panel')
            if photo_panel:
                photo_panel.set_status(get_text("initializing_camera", "正在初始化相機..."))

            # 啟動相機預覽
            success = self.detection_controller.start_camera_preview()

            if success:
                if photo_panel:
                    photo_panel.set_status(get_text("camera_ready", "相機就緒，可以拍攝"))
            else:
                if photo_panel:
                    photo_panel.set_status(get_text("camera_error", "相機初始化失敗"))
                self.main_window.log_message(get_text("camera_error", "相機初始化失敗"))

        except Exception as e:
            self.main_window.log_message(f"啟動拍照模式失敗：{str(e)}")

    def start_photo_preview(self):
        """啟動拍照模式的相機預覽"""
        if not self.detection_controller.is_photo_mode:
            return

        def update_preview():
            if not self.detection_controller.is_photo_mode:
                return

            self.detection_controller.preview_camera_for_photo()
            self.main_window.root.after(30, update_preview)  # 約30fps

        update_preview()

    def handle_capture_photo(self):
        """處理拍照請求"""
        try:
            # 顯示狀態
            photo_panel = self.components.get('photo_panel')
            if photo_panel:
                photo_panel.set_status(get_text("capturing", "正在拍攝..."))

            # 拍攝照片
            success = self.detection_controller.capture_photo()

            if success:
                if photo_panel:
                    photo_panel.set_status(get_text("capture_success", "拍攝成功"))
                self.main_window.log_message(get_text("capture_success", "拍攝成功"))
            else:
                if photo_panel:
                    photo_panel.set_status(get_text("capture_failed", "拍攝失敗"))
                self.main_window.log_message(get_text("capture_failed", "拍攝失敗"))

        except Exception as e:
            self.main_window.log_message(f"拍照時發生錯誤：{str(e)}")

    def handle_analyze_photo(self):
        """處理分析照片請求"""
        try:
            # 顯示載入狀態
            photo_panel = self.components.get('photo_panel')
            if photo_panel:
                photo_panel.show_loading()

            # 分析照片
            success = self.detection_controller.analyze_photo()

            if not success:
                if photo_panel:
                    photo_panel.hide_loading()
                    photo_panel.set_status(get_text("analysis_failed", "分析照片失敗"))
                self.main_window.log_message(get_text("analysis_failed", "分析照片失敗"))

        except Exception as e:
            if photo_panel:
                photo_panel.hide_loading()
            self.main_window.log_message(f"分析照片時發生錯誤：{str(e)}")

    def handle_analysis_results(self, result):
        """處理分析結果"""
        try:
            # 隱藏載入狀態
            photo_panel = self.components.get('photo_panel')
            if photo_panel:
                photo_panel.hide_loading()

            # 顯示分析結果
            self.main_window.show_analysis_results(result)

            # 記錄日誌
            is_defective = result.get('is_defective', False)
            status = get_text("defective", "有缺陷") if is_defective else get_text("normal", "正常")
            self.main_window.log_message(f"分析完成，檢測狀態：{status}")

        except Exception as e:
            self.main_window.log_message(f"處理分析結果時發生錯誤：{str(e)}")

    def handle_analysis_error(self, error_msg):
        """處理分析錯誤"""
        try:
            # 隱藏載入狀態
            photo_panel = self.components.get('photo_panel')
            if photo_panel:
                photo_panel.hide_loading()
                photo_panel.set_status(f"{get_text('analysis_error', '分析錯誤')}: {error_msg}")

            # 記錄日誌
            self.main_window.log_message(f"分析錯誤：{error_msg}")

        except Exception as e:
            self.main_window.log_message(f"處理分析錯誤時發生錯誤：{str(e)}")