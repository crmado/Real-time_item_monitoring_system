"""
自動更新模組
處理應用程式的版本檢查、下載和更新流程
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Callable
from urllib.parse import urljoin

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from basler_pyqt6.version import (
    __version__,
    UPDATE_SERVER_URL,
    compare_versions,
    APP_NAME
)


class UpdateChecker:
    """版本檢查器"""

    def __init__(self, server_url: str = UPDATE_SERVER_URL):
        """
        初始化更新檢查器

        Args:
            server_url: 更新服務器 URL
        """
        self.server_url = server_url
        self.timeout = 10  # 請求超時（秒）

    def check_for_updates(self) -> Optional[Dict]:
        """
        檢查是否有新版本

        Returns:
            如果有更新返回更新信息字典，否則返回 None
            {
                'version': '2.1.0',
                'download_url': 'http://...',
                'release_notes': '更新說明...',
                'file_size': 123456789,
                'md5': 'abc123...'
            }
        """
        try:
            # 請求更新信息
            url = urljoin(self.server_url, "/updates/latest")
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # 比較版本
            remote_version = data.get('version')
            if not remote_version:
                return None

            comparison = compare_versions(__version__, remote_version)

            # 如果遠程版本較新
            if comparison < 0:
                return {
                    'version': remote_version,
                    'download_url': data.get('download_url'),
                    'release_notes': data.get('release_notes', ''),
                    'file_size': data.get('file_size', 0),
                    'md5': data.get('md5', ''),
                    'publish_date': data.get('publish_date', '')
                }

            return None

        except requests.RequestException as e:
            print(f"檢查更新失敗: {e}")
            return None
        except Exception as e:
            print(f"檢查更新時發生錯誤: {e}")
            return None


class UpdateDownloader(QThread):
    """更新下載器（使用 QThread 在背景下載）"""

    # 信號
    progress = pyqtSignal(int, int)  # (已下載, 總大小)
    finished = pyqtSignal(str)  # 下載完成，返回文件路徑
    error = pyqtSignal(str)  # 下載錯誤

    def __init__(self, download_url: str, expected_md5: str = ""):
        super().__init__()
        self.download_url = download_url
        self.expected_md5 = expected_md5
        self.download_path = None
        self._is_cancelled = False

    def run(self):
        """執行下載"""
        try:
            # 創建臨時目錄
            temp_dir = tempfile.mkdtemp(prefix="basler_update_")
            filename = os.path.basename(self.download_url.split('?')[0])
            if not filename.endswith('.zip'):
                filename += '.zip'

            self.download_path = os.path.join(temp_dir, filename)

            # 開始下載
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(self.download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self._is_cancelled:
                        f.close()
                        os.remove(self.download_path)
                        return

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total_size)

            # 驗證 MD5（如果提供）
            if self.expected_md5:
                import hashlib
                md5_hash = hashlib.md5()
                with open(self.download_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        md5_hash.update(chunk)

                if md5_hash.hexdigest() != self.expected_md5:
                    raise ValueError("檔案 MD5 驗證失敗")

            self.finished.emit(self.download_path)

        except Exception as e:
            self.error.emit(str(e))

    def cancel(self):
        """取消下載"""
        self._is_cancelled = True


class UpdateInstaller:
    """更新安裝器"""

    @staticmethod
    def install_update(zip_path: str, restart_after_install: bool = True) -> bool:
        """
        安裝更新

        Args:
            zip_path: 更新包 ZIP 文件路徑
            restart_after_install: 安裝後是否重啟應用

        Returns:
            是否安裝成功
        """
        try:
            # 獲取當前應用程式目錄
            if getattr(sys, 'frozen', False):
                # 打包後的執行檔
                app_dir = os.path.dirname(sys.executable)
            else:
                # 開發環境
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # 創建備份目錄
            backup_dir = os.path.join(app_dir, 'backup_' + __version__)
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)

            # 備份當前版本
            print(f"備份當前版本到: {backup_dir}")
            shutil.copytree(app_dir, backup_dir,
                          ignore=shutil.ignore_patterns('backup_*', '*.log', '__pycache__'))

            # 解壓新版本
            print(f"解壓更新包: {zip_path}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 解壓到臨時目錄
                temp_extract_dir = tempfile.mkdtemp(prefix="basler_extract_")
                zip_ref.extractall(temp_extract_dir)

                # 尋找更新文件的根目錄（可能在 ZIP 內有一層文件夾）
                extracted_items = os.listdir(temp_extract_dir)
                if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_extract_dir, extracted_items[0])):
                    update_source = os.path.join(temp_extract_dir, extracted_items[0])
                else:
                    update_source = temp_extract_dir

                # 複製文件到應用目錄
                print(f"安裝更新到: {app_dir}")
                for item in os.listdir(update_source):
                    source = os.path.join(update_source, item)
                    dest = os.path.join(app_dir, item)

                    # 移除舊文件/目錄
                    if os.path.exists(dest):
                        if os.path.isdir(dest):
                            shutil.rmtree(dest)
                        else:
                            os.remove(dest)

                    # 複製新文件/目錄
                    if os.path.isdir(source):
                        shutil.copytree(source, dest)
                    else:
                        shutil.copy2(source, dest)

                # 清理臨時文件
                shutil.rmtree(temp_extract_dir)

            print("更新安裝完成")

            # 重啟應用
            if restart_after_install:
                UpdateInstaller.restart_application()

            return True

        except Exception as e:
            print(f"安裝更新失敗: {e}")
            # 恢復備份
            if os.path.exists(backup_dir):
                print("正在恢復備份...")
                # TODO: 實現備份恢復邏輯
            return False

    @staticmethod
    def restart_application():
        """重啟應用程式"""
        try:
            if getattr(sys, 'frozen', False):
                # 打包後的執行檔
                exe_path = sys.executable
            else:
                # 開發環境
                exe_path = sys.argv[0]

            # 使用 subprocess 啟動新進程
            if sys.platform == 'win32':
                subprocess.Popen([exe_path])
            else:
                subprocess.Popen([exe_path], start_new_session=True)

            # 退出當前進程
            sys.exit(0)

        except Exception as e:
            print(f"重啟應用失敗: {e}")


class AutoUpdater:
    """自動更新管理器（整合所有更新功能）"""

    def __init__(self):
        self.checker = UpdateChecker()
        self.downloader: Optional[UpdateDownloader] = None

    def check_updates(self) -> Optional[Dict]:
        """檢查更新"""
        return self.checker.check_for_updates()

    def download_update(self, update_info: Dict) -> UpdateDownloader:
        """
        下載更新

        Args:
            update_info: 從 check_updates 返回的更新信息

        Returns:
            UpdateDownloader 實例
        """
        self.downloader = UpdateDownloader(
            download_url=update_info['download_url'],
            expected_md5=update_info.get('md5', '')
        )
        return self.downloader

    def install_update(self, zip_path: str, restart: bool = True) -> bool:
        """安裝更新"""
        return UpdateInstaller.install_update(zip_path, restart)


# 便捷函數
def check_for_updates() -> Optional[Dict]:
    """檢查是否有可用更新"""
    updater = AutoUpdater()
    return updater.check_updates()


def get_current_version() -> str:
    """獲取當前版本"""
    return __version__
