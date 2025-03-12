"""
控制面板組件
包含視訊來源選擇和控制按鈕
"""
from tkinter import ttk
import tkinter as tk
from utils.language import get_text


class ControlPanel(ttk.Frame):
    """控制面板類別"""

    # ==========================================================================
    # 第一部分：基本屬性和初始化
    # ==========================================================================
    def __init__(self, parent, **kwargs):
        """
        初始化控制面板

        Args:
            parent: 父级窗口
            **kwargs: 其他参数
        """
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.callbacks = {}
        self.camera_sources = []
        self.selected_camera = tk.StringVar()
        self.current_mode = tk.StringVar(value="monitoring")  # 默认为监控模式
        
        # 创建UI组件
        self.create_widgets()
        
    # ==========================================================================
    # 第二部分：UI元件創建
    # ==========================================================================
    def create_widgets(self):
        """创建控制面板组件"""
        # 使用统一的样式
        self.configure(style='Control.TFrame')
        
        # 创建标题
        title_frame = ttk.Frame(self, style='ControlHeader.TFrame')
        title_frame.pack(fill=tk.X, padx=0, pady=0)
        
        title_label = ttk.Label(
            title_frame, 
            text=get_text("control_panel", "控制面板"),
            style='ControlTitle.TLabel'
        )
        title_label.pack(padx=10, pady=10)
        
        # 主控制区域
        main_controls = ttk.Frame(self, style='Control.TFrame')
        main_controls.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 相机选择区域
        camera_frame = ttk.LabelFrame(
            main_controls, 
            text=get_text("camera_selection", "相机选择")
        )
        camera_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 相机下拉菜单
        self.camera_combo = ttk.Combobox(
            camera_frame,
            textvariable=self.selected_camera,
            state="readonly"
        )
        self.camera_combo.pack(fill=tk.X, padx=10, pady=10)
        self.camera_combo.bind("<<ComboboxSelected>>", self._on_camera_selected)
        
        # 模式选择区域
        mode_frame = ttk.LabelFrame(
            main_controls, 
            text=get_text("mode_selection", "模式选择")
        )
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 模式选择按钮
        modes_container = ttk.Frame(mode_frame)
        modes_container.pack(fill=tk.X, padx=10, pady=10)
        
        self.monitoring_radio = ttk.Radiobutton(
            modes_container,
            text=get_text("monitoring_mode", "监控模式"),
            variable=self.current_mode,
            value="monitoring",
            command=self._on_mode_changed
        )
        self.monitoring_radio.pack(fill=tk.X, pady=2)
        
        self.photo_radio = ttk.Radiobutton(
            modes_container,
            text=get_text("photo_mode", "拍照模式"),
            variable=self.current_mode,
            value="photo",
            command=self._on_mode_changed
        )
        self.photo_radio.pack(fill=tk.X, pady=2)
        
        # 操作按钮区域
        action_frame = ttk.LabelFrame(
            main_controls, 
            text=get_text("actions", "操作")
        )
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 操作按钮
        buttons_container = ttk.Frame(action_frame)
        buttons_container.pack(fill=tk.X, padx=10, pady=10)
        
        self.start_btn = ttk.Button(
            buttons_container,
            text=get_text("start", "开始"),
            command=self._on_start,
            style='Accent.TButton'
        )
        self.start_btn.pack(fill=tk.X, pady=2)
        
        self.refresh_btn = ttk.Button(
            buttons_container,
            text=get_text("refresh_preview", "刷新預覽"),
            command=self._on_refresh_preview
        )
        self.refresh_btn.pack(fill=tk.X, pady=2)
        
        self.stop_btn = ttk.Button(
            buttons_container,
            text=get_text("stop", "停止"),
            command=self._on_stop,
            style='Accent.TButton',
            state=tk.DISABLED
        )
        self.stop_btn.pack(fill=tk.X, pady=2)
        
        self.settings_btn = ttk.Button(
            buttons_container,
            text=get_text("settings", "设置"),
            command=self._on_settings
        )
        self.settings_btn.pack(fill=tk.X, pady=2)
        
        # 状态显示区域
        status_frame = ttk.LabelFrame(
            main_controls, 
            text=get_text("status", "状态")
        )
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(
            status_frame,
            text=get_text("status_ready", "就绪")
        )
        self.status_label.pack(padx=10, pady=10)
        
    def set_camera_sources(self, sources):
        """
        設置相機源列表
        
        Args:
            sources: 相機源列表
        """
        if not sources:
            return
            
        # 清空下拉選單
        self.camera_combo['values'] = sources
        
        # 如果有值，選擇第一個
        if len(sources) > 0:
            self.selected_camera.set(sources[0])
            
    def set_camera_source(self, source):
        """
        设置当前选中的相机源
        
        Args:
            source: 相机源名称
        """
        if source in self.camera_sources:
            self.selected_camera.set(source)
            
    def set_callback(self, event_name, callback):
        """
        设置回调函数
        
        Args:
            event_name: 事件名称
            callback: 回调函数
        """
        self.callbacks[event_name] = callback
        
    def set_status(self, status_text):
        """
        设置状态文本
        
        Args:
            status_text: 状态文本
        """
        self.status_label.config(text=status_text)
        
    def update_button_states(self, is_running):
        """
        更新按钮状态
        
        Args:
            is_running: 是否正在运行
        """
        if is_running:
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
    def _on_camera_selected(self, event):
        """
        處理相機選擇事件
        
        Args:
            event: 事件對象
        """
        selected = self.selected_camera.get()
        if 'camera_selected' in self.callbacks and self.callbacks['camera_selected']:
            self.callbacks['camera_selected'](selected)
            
    def _on_mode_changed(self):
        """處理模式切換事件"""
        mode = self.current_mode.get()
        if 'mode_changed' in self.callbacks and self.callbacks['mode_changed']:
            self.callbacks['mode_changed'](mode)
            
    def _on_start(self):
        """處理開始按鈕點擊事件"""
        if 'start' in self.callbacks and self.callbacks['start']:
            self.callbacks['start']()
            
    def _on_stop(self):
        """處理停止按鈕點擊事件"""
        if 'stop' in self.callbacks and self.callbacks['stop']:
            self.callbacks['stop']()
            
    def _on_settings(self):
        """處理設置按鈕點擊事件"""
        if 'settings' in self.callbacks and self.callbacks['settings']:
            self.callbacks['settings']()

    def _on_refresh_preview(self):
        """處理刷新預覽按鈕點擊事件"""
        if 'refresh_preview' in self.callbacks:
            self.callbacks['refresh_preview']()

    def update_language(self):
        """更新語言"""
        # 更新標籤文字
        for child in self.winfo_children():
            if isinstance(child, ttk.Label):
                if "選擇視訊來源" in child.cget('text') or "Select Video Source" in child.cget('text'):
                    child.configure(text=get_text("select_source", "選擇視訊來源："))

        # 更新按鈕文字
        if "開始監測" in self.start_btn.cget('text') or "Start Monitoring" in self.start_btn.cget('text'):
            self.start_btn.configure(text=get_text("start_button", "開始監測"))
        elif "停止監測" in self.stop_btn.cget('text') or "Stop Monitoring" in self.stop_btn.cget('text'):
            self.stop_btn.configure(text=get_text("stop_button", "停止監測"))

        # 更新模式切換按鈕文字
        if "切換到拍照模式" in self.photo_radio.cget('text') or "Switch to Photo Mode" in self.photo_radio.cget('text'):
            self.photo_radio.configure(text=get_text("mode_switch", "切換到拍照模式"))
        elif "切換到監測模式" in self.monitoring_radio.cget('text') or "Switch to Monitoring Mode" in self.monitoring_radio.cget('text'):
            self.monitoring_radio.configure(text=get_text("mode_switch_back", "切換到監測模式"))
            
    def update_start_button_text(self, is_running):
        """
        更新開始按鈕文字
        
        Args:
            is_running: 是否正在運行
        """
        if is_running:
            self.start_btn.config(text=get_text("stop_monitoring", "停止監測"))
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(text=get_text("start_monitoring", "開始監測"))
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
        
        # 更新按鈕狀態
        self.update_button_states(is_running)
        
    def update_test_button_text(self, is_testing):
        """
        更新測試按鈕文字
        
        Args:
            is_testing: 是否正在測試
        """
        # 如果有測試按鈕，更新其文字
        if hasattr(self, 'test_btn'):
            if is_testing:
                self.test_btn.config(text=get_text("stop_test", "停止測試"))
            else:
                self.test_btn.config(text=get_text("test_camera", "測試相機"))
                
    def get_selected_source(self):
        """
        獲取當前選擇的相機源
        
        Returns:
            str: 相機源名稱
        """
        return self.selected_camera.get()

    def set_callbacks(self, callbacks):
        """
        設置回調函數

        Args:
            callbacks: 回調函數字典
        """
        self.callbacks = callbacks
        
        # 綁定相機選擇回調
        if 'camera_selected' in callbacks:
            self.camera_combo.bind("<<ComboboxSelected>>", 
                lambda e: callbacks['camera_selected'](self.selected_camera.get()))

    def update_ui_text(self):
        """更新控制面板中的所有文字"""
        # 更新標題
        if hasattr(self, 'title_label'):
            self.title_label.configure(text=get_text("control_panel", "控制面板"))
            
        # 更新相機源標籤
        if hasattr(self, 'camera_label'):
            self.camera_label.configure(text=get_text("select_source", "選擇視訊來源："))
            
        # 更新模式選擇標籤
        if hasattr(self, 'mode_label'):
            self.mode_label.configure(text=get_text("mode_selection", "模式選擇"))
            
        # 更新模式選項
        if hasattr(self, 'monitoring_radio'):
            self.monitoring_radio.configure(text=get_text("monitoring_mode", "監控模式"))
            
        if hasattr(self, 'photo_radio'):
            self.photo_radio.configure(text=get_text("photo_mode", "拍照模式"))
            
        # 更新操作標籤
        if hasattr(self, 'actions_label'):
            self.actions_label.configure(text=get_text("actions", "操作"))
            
        # 更新開始/停止按鈕
        if hasattr(self, 'start_button'):
            if self.is_running:
                self.start_button.configure(text=get_text("stop_button", "停止監測"))
            else:
                self.start_button.configure(text=get_text("start_button", "開始監測"))
                
        # 更新測試按鈕
        if hasattr(self, 'test_button'):
            if self.is_testing:
                self.test_button.configure(text=get_text("stop_test", "停止測試"))
            else:
                self.test_button.configure(text=get_text("test_button", "測試鏡頭"))
                
        # 更新刷新按鈕
        if hasattr(self, 'refresh_button'):
            self.refresh_button.configure(text=get_text("refresh_preview", "刷新預覽"))
            
        # 更新狀態標籤
        if hasattr(self, 'status_label'):
            self.status_label.configure(text=get_text("status", "狀態"))
            
        # 更新狀態值標籤
        if hasattr(self, 'status_value'):
            current_status = self.status_value.cget('text')
            if current_status == "就绪" or current_status == "就緒":
                self.status_value.configure(text=get_text("status_ready", "就緒"))
            elif current_status == "正在运行" or current_status == "正在運行":
                self.status_value.configure(text=get_text("status_running", "正在運行"))
            elif current_status == "已停止":
                self.status_value.configure(text=get_text("status_stopped", "已停止"))
            elif current_status == "监控模式" or current_status == "監控模式":
                self.status_value.configure(text=get_text("status_monitoring_mode", "監控模式"))
            elif current_status == "拍照模式":
                self.status_value.configure(text=get_text("status_photo_mode", "拍照模式"))