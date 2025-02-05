"""
UI 管理器
負責管理所有使用者介面的樣式和主題
"""

from tkinter import ttk


class UIManager:
    """UI 管理類別"""

    def __init__(self):
        """初始化 UI 管理器"""
        self.style = ttk.Style()
        self.setup_styles()

    def setup_styles(self):
        """設置界面樣式"""
        # 影像顯示區域樣式
        self.style.configure(
            'Video.TFrame',
            background='#f0f0f0',
            borderwidth=2,
            relief='solid'
        )

        self.style.configure(
            'Video.TLabel',
            background='#e0e0e0',
            font=('Arial', 12)
        )

        # 計數器樣式
        self.style.configure(
            'Counter.TLabel',
            font=('Arial', 12, 'bold')
        )

        self.style.configure(
            'CounterNum.TLabel',
            font=('Arial', 14, 'bold'),
            foreground='#2E8B57'
        )

        # 按鈕樣式
        self.style.configure(
            'Accent.TButton',
            font=('Arial', 10, 'bold'),
            background='#2E8B57'
        )

        # 設定區域樣式
        self.style.configure(
            'Settings.TFrame',
            padding=5,
            relief='groove'
        )

        self.style.configure(
            'Settings.TLabel',
            font=('Arial', 10),
            padding=2
        )

        self.style.configure(
            'Settings.TEntry',
            padding=2
        )

    def get_style(self):
        """獲取樣式物件"""
        return self.style