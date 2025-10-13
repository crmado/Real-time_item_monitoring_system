"""
自動更新模組
負責檢查、下載和安裝軟件更新
"""

import os
import sys
import json
import logging
import requests
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urljoin

from basler_pyqt6.version import (
    __version__,
    UPDATE_SERVER_URL,
    compare_versions
)

logger = logging.getLogger(__name__)


class UpdateInfo:
    """更新信息數據類"""

    def __init__(self, data: Dict[str, Any]):
        self.version: str = data.get('version', '')
        self.release_date: str = data.get('release_date', '')
        self.download_url: str = data.get('download_url', '')
        self.changelog: str = data.get('changelog', '')
        self.file_size: int = data.get('file_size', 0)
        self.checksum: str = data.get('checksum', '')
        self.mandatory: bool = data.get('mandatory', False)

    def is_newer_than(self, current_version: str) -> bool:
        """檢查是否比當前版本新"""
        return compare_versions(current_version, self.version) < 0


class AutoUpdater:
    """自動更新器"""

    def __init__(self, update_url: str = None):
        """
        初始化更新器

        Args:
            update_url: 更新服務器 URL（如果為 None 則使用配置文件中的）
        """
        self.update_url = update_url or UPDATE_SERVER_URL
        self.current_version = __version__
        self.download_progress = 0

        # 臨時下載目錄
        self.temp_dir = Path(tempfile.gettempdir()) / "basler_updates"
        self.temp_dir.mkdir(exist_ok=True)

        logger.info(f"✅ 自動更新器初始化完成，當前版本: {self.current_version}")

    def check_for_updates(self, timeout: int = 10) -> Optional[UpdateInfo]:
        """
        檢查是否有可用更新

        Args:
            timeout: 請求超時時間（秒）

        Returns:
            UpdateInfo: 如果有更新返回更新信息，否則返回 None
        """
        try:
            # 構建檢查更新的 API 端點
            check_url = urljoin(self.update_url, f"/check_update?version={self.current_version}")

            logger.info(f"🔍 檢查更新: {check_url}")

            # 發送請求
            response = requests.get(
                check_url,
                timeout=timeout,
                headers={'User-Agent': f'BaslerVision/{self.current_version}'}
            )

            if response.status_code != 200:
                logger.warning(f"⚠️ 更新檢查失敗，狀態碼: {response.status_code}")
                return None

            # 解析響應
            data = response.json()

            if not data.get('update_available', False):
                logger.info("✅ 當前已是最新版本")
                return None

            # 創建更新信息對象
            update_info = UpdateInfo(data.get('update_info', {}))

            if update_info.is_newer_than(self.current_version):
                logger.info(f"🆕 發現新版本: {update_info.version}")
                return update_info
            else:
                logger.info("✅ 當前已是最新版本")
                return None

        except requests.exceptions.Timeout:
            logger.error("❌ 更新檢查超時")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("❌ 無法連接到更新服務器")
            return None
        except Exception as e:
            logger.error(f"❌ 檢查更新時發生錯誤: {str(e)}")
            return None

    def download_update(
        self,
        update_info: UpdateInfo,
        progress_callback=None
    ) -> Optional[Path]:
        """
        下載更新文件

        Args:
            update_info: 更新信息
            progress_callback: 進度回調函數 callback(current, total)

        Returns:
            Path: 下載文件的路徑，失敗返回 None
        """
        try:
            download_url = update_info.download_url
            filename = f"BaslerVisionSystem_v{update_info.version}.exe"
            download_path = self.temp_dir / filename

            logger.info(f"⬇️ 開始下載更新: {download_url}")

            # 流式下載
            response = requests.get(download_url, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # 更新進度
                        if progress_callback and total_size > 0:
                            progress_callback(downloaded_size, total_size)

                        self.download_progress = (downloaded_size / total_size * 100) if total_size > 0 else 0

            logger.info(f"✅ 下載完成: {download_path}")

            # TODO: 驗證 checksum
            # if update_info.checksum:
            #     if not self._verify_checksum(download_path, update_info.checksum):
            #         logger.error("❌ 文件校驗失敗")
            #         download_path.unlink()
            #         return None

            return download_path

        except Exception as e:
            logger.error(f"❌ 下載更新失敗: {str(e)}")
            return None

    def install_update(self, installer_path: Path) -> bool:
        """
        安裝更新（啟動安裝程序並退出當前應用）

        Args:
            installer_path: 安裝程序路徑

        Returns:
            bool: 是否成功啟動安裝程序
        """
        try:
            if not installer_path.exists():
                logger.error("❌ 安裝文件不存在")
                return False

            logger.info(f"🚀 啟動安裝程序: {installer_path}")

            # Windows: 啟動安裝程序
            if sys.platform == 'win32':
                # 使用 subprocess 在後台啟動安裝程序
                subprocess.Popen(
                    [str(installer_path)],
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                )
            # macOS
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', str(installer_path)])
            # Linux
            else:
                subprocess.Popen([str(installer_path)])

            logger.info("✅ 安裝程序已啟動，應用即將退出")
            return True

        except Exception as e:
            logger.error(f"❌ 啟動安裝程序失敗: {str(e)}")
            return False

    def cleanup(self):
        """清理臨時文件"""
        try:
            if self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                logger.info("✅ 清理臨時文件完成")
        except Exception as e:
            logger.warning(f"⚠️ 清理臨時文件失敗: {str(e)}")


# 便捷函數
def check_update() -> Optional[UpdateInfo]:
    """快速檢查更新"""
    updater = AutoUpdater()
    return updater.check_for_updates()
