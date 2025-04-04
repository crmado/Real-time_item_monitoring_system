"""
API客戶端
負責與後端API通信和處理回傳數據
"""

import requests # type: ignore
import logging
import os
import threading
import json # type: ignore


class APIClient:
    """API客戶端類別"""

    # ==========================================================================
    # 第一部分：基本屬性和初始化
    # ==========================================================================
    def __init__(self, api_url="http://skaiqwenapi.skaispace.com:5002/api/inspect"):
        """
        初始化API客戶端

        Args:
            api_url: API端點URL
        """
        self.api_url = api_url
        self.callbacks = {}
        self.current_thread = None

    # ==========================================================================
    # 第二部分：API通信方法
    # ==========================================================================
    def inspect_image(self, image_path, success_callback=None, error_callback=None):
        """
        發送圖像到API進行檢測

        Args:
            image_path: 圖像文件路徑
            success_callback: 成功時的回調函數
            error_callback: 失敗時的回調函數
        """
        # 如果有正在運行的線程，則終止它
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread = None

        # 創建新線程進行API請求
        self.current_thread = threading.Thread(
            target=self._run_inspection,
            args=(image_path, success_callback, error_callback),
            daemon=True
        )
        self.current_thread.start()

    def _run_inspection(self, image_path, success_callback, error_callback):
        """
        執行API請求的線程函數

        Args:
            image_path: 圖像文件路徑
            success_callback: 成功時的回調函數
            error_callback: 失敗時的回調函數
        """
        try:
            if not os.path.exists(image_path):
                if error_callback:
                    error_callback("圖像文件不存在")
                return

            # 準備文件對象
            files = {'image': ('image.png', open(image_path, 'rb'), 'image/png')}

            # 發送API請求
            logging.info(f"發送請求到API: {self.api_url}")
            response = requests.post(self.api_url, files=files, timeout=300)

            if response.status_code == 200:
                # 解析JSON響應
                result = response.json()
                logging.info("收到API響應")

                # 檢查響應格式
                if 'images' not in result:
                    if error_callback:
                        error_callback("API回傳的數據缺少images欄位")
                    return

                # 回調成功函數
                if success_callback:
                    success_callback(result)
            else:
                error_msg = f"API請求失敗: HTTP {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                logging.error(error_msg)

                if error_callback:
                    error_callback(error_msg)

        except Exception as e:
            logging.error(f"API請求過程中發生錯誤: {str(e)}")
            if error_callback:
                error_callback(f"API請求錯誤: {str(e)}")

    # ==========================================================================
    # 第三部分：工具方法
    # ==========================================================================
    def save_temp_image(self, image, filename="temp_capture.png"):
        """
        保存臨時圖像文件

        Args:
            image: 圖像數據
            filename: 文件名

        Returns:
            str: 保存的文件路徑
        """
        try:
            import cv2 # type: ignore
            cv2.imwrite(filename, image)
            return filename
        except Exception as e:
            logging.error(f"保存臨時文件失敗: {str(e)}")
            raise Exception(f"保存臨時文件失敗: {str(e)}")

    def cleanup_temp_file(self, filename):
        """
        清理臨時文件

        Args:
            filename: 文件路徑
        """
        try:
            if os.path.exists(filename):
                os.remove(filename)
                logging.info(f"已清理臨時文件: {filename}")
        except Exception as e:
            logging.error(f"清理臨時文件失敗: {str(e)}")