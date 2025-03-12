"""
控制面板組件
包含視訊來源選擇和控制按鈕
"""
from tkinter import ttk
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
            parent: 父級視窗
            **kwargs: 其他參數
        """
        super().__init__(parent, style='Control.TFrame', **kwargs)
        self.mode_button = None
        self.start_button = None
        self.camera_combo = None
        self.parent = parent
        self.callbacks = {}
        self.create_widgets()

    # ==========================================================================
    # 第二部分：UI元件創建
    # ==========================================================================
    def create_widgets(self):
        """創建控制面板組件"""
        # 使用水平佈局
        # 視訊來源選擇
        source_frame = ttk.Frame(self, style='Control.TFrame')
        source_frame.pack(side='left', padx=5)
        
        ttk.Label(source_frame, text=get_text("select_source", "選擇視訊來源：")).pack(side='left')

        self.camera_combo = ttk.Combobox(source_frame, width=30)
        self.camera_combo.pack(side='left', padx=5)

        # 綁定選擇事件，當選擇變更時自動測試相機
        self.camera_combo.bind("<<ComboboxSelected>>", self._on_camera_selected)

        # # 測試按鈕
        # self.test_button = ttk.Button(
        #     self,
        #     text=get_text("test_button", "測試鏡頭"),
        #     style='Accent.TButton'
        # )
        # self.test_button.grid(row=0, column=2, padx=5)

        # 開始/停止按鈕
        self.start_button = ttk.Button(
            self,
            text=get_text("start_button", "開始監測"),
            style='Accent.TButton'
        )
        self.start_button.pack(side='left', padx=10)

        # 添加模式切換按鈕
        self.mode_button = ttk.Button(
            self,
            text=get_text("mode_switch", "切換到拍照模式"),
            command=self._on_mode_switch
        )
        self.mode_button.pack(side='left', padx=5)

    def set_camera_sources(self, sources):
        """
        設置可用的視訊來源

        Args:
            sources: 視訊來源列表
        """
        self.camera_combo['values'] = sources

    def get_selected_source(self):
        """
        獲取選擇的視訊來源

        Returns:
            str: 選擇的視訊來源名稱
        """
        return self.camera_combo.get()

    def set_callback(self, button_name, callback):
        """
        設置按鈕回調函數

        Args:
            button_name: 按鈕名稱
            callback: 回調函數
        """
        if button_name == 'start':
            self.start_button.configure(command=callback)
        elif button_name == 'mode':
            self.mode_button.configure(command=callback)
        elif button_name == 'camera_selected':
            self.callbacks['camera_selected'] = callback
        # if button_name == 'test':
        #     self.test_button.configure(command=callback)
        # elif button_name == 'start':
        #     self.start_button.configure(command=callback)

    def update_start_button_text(self, is_running):
        """
        更新開始/停止按鈕文字

        Args:
            is_running: 是否正在運行
        """
        if is_running:
            self.start_button.configure(text=get_text("stop_button", "停止監測"))
        else:
            self.start_button.configure(text=get_text("start_button", "開始監測"))

    def update_test_button_text(self, is_testing):
        """
        更新測試按鈕文字

        Args:
            is_testing: 是否正在測試
        """
        # 測試按鈕已移除，此方法保留為空
        pass

    def update_language(self):
        """更新語言"""
        # 更新標籤文字
        for child in self.winfo_children():
            if isinstance(child, ttk.Label):
                if "選擇視訊來源" in child.cget('text') or "Select Video Source" in child.cget('text'):
                    child.configure(text=get_text("select_source", "選擇視訊來源："))

        # 更新按鈕文字
        if "開始監測" in self.start_button.cget('text') or "Start Monitoring" in self.start_button.cget('text'):
            self.start_button.configure(text=get_text("start_button", "開始監測"))
        elif "停止監測" in self.start_button.cget('text') or "Stop Monitoring" in self.start_button.cget('text'):
            self.start_button.configure(text=get_text("stop_button", "停止監測"))

        # 更新模式切換按鈕文字
        if "切換到拍照模式" in self.mode_button.cget('text') or "Switch to Photo Mode" in self.mode_button.cget('text'):
            self.mode_button.configure(text=get_text("mode_switch", "切換到拍照模式"))
        elif "切換到監測模式" in self.mode_button.cget('text') or "Switch to Monitoring Mode" in self.mode_button.cget('text'):
            self.mode_button.configure(text=get_text("mode_switch_back", "切換到監測模式"))

    def _on_camera_selected(self, event):
        """
        相機選擇事件處理

        Args:
            event: 事件物件
        """
        if 'camera_selected' in self.callbacks:
            self.callbacks['camera_selected'](self.get_selected_source())

    def select_source(self, source):
        """
        選擇指定的視訊來源

        Args:
            source: 視訊來源名稱
        """
        if source in self.camera_combo['values']:
            self.camera_combo.set(source)
            # 如果已經設定了選擇變更回調，呼叫它
            if 'source_changed' in self.callbacks and self.callbacks['source_changed']:
                self.callbacks['source_changed'](source)

    # ==========================================================================
    # 第三部分：事件處理
    # ==========================================================================

    def _on_mode_switch(self):
        """模式切換按鈕點擊事件"""
        if 'mode_switch' in self.callbacks:
            self.callbacks['mode_switch']()

    def update_mode_button_text(self, is_photo_mode):
        """
        更新模式切換按鈕文字

        Args:
            is_photo_mode: 是否為拍照模式
        """
        if is_photo_mode:
            self.mode_button.configure(text=get_text("mode_switch_back", "切換到監測模式"))
        else:
            self.mode_button.configure(text=get_text("mode_switch", "切換到拍照模式"))