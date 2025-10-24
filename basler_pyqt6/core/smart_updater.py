"""
智能更新器 - 自動選擇更新方式
- 源碼環境（Rock 5B）：使用 git pull
- 打包環境（Windows/macOS/Linux 二進制）：使用 HTTP 下載
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict
from enum import Enum

from basler_pyqt6.version import __version__
from basler_pyqt6.core.updater import AutoUpdater, UpdateInfo

logger = logging.getLogger(__name__)


class UpdateMode(Enum):
    """更新模式"""
    GIT = "git"      # Git 源碼更新（Rock 5B 等開發環境）
    OTA = "ota"      # OTA 更新（打包的二進制文件）
    NONE = "none"    # 無法更新


class SmartUpdater:
    """
    智能更新器 - 根據運行環境自動選擇更新方式

    運行環境檢測：
    1. 檢查 sys.frozen -> 打包環境 -> OTA 更新
    2. 檢查 .git 目錄 -> 源碼環境 -> Git 更新
    3. 其他 -> 無法自動更新
    """

    def __init__(self):
        self.mode = self._detect_update_mode()
        self.project_root = self._get_project_root()

        # OTA 更新器（僅在 OTA 模式下初始化）
        self.ota_updater = None
        if self.mode == UpdateMode.OTA:
            self.ota_updater = AutoUpdater()

        logger.info(f"智能更新器初始化: 模式={self.mode.value}, 根目錄={self.project_root}")

    def _get_project_root(self) -> Path:
        """獲取專案根目錄"""
        if getattr(sys, 'frozen', False):
            # 打包環境：執行檔所在目錄
            return Path(sys.executable).parent
        else:
            # 開發環境：basler_pyqt6 的上層目錄
            return Path(__file__).parent.parent.parent

    def _detect_update_mode(self) -> UpdateMode:
        """
        檢測更新模式

        Returns:
            UpdateMode: 更新模式
        """
        # 檢查是否為打包環境
        if getattr(sys, 'frozen', False):
            logger.info("檢測到打包環境 -> 使用 OTA 更新")
            return UpdateMode.OTA

        # 檢查是否為 Git 倉庫
        project_root = self._get_project_root()
        git_dir = project_root / ".git"

        if git_dir.exists():
            # 檢查 git 命令是否可用
            if self._check_git_available():
                logger.info("檢測到 Git 倉庫 -> 使用 Git 更新")
                return UpdateMode.GIT
            else:
                logger.warning("Git 倉庫存在但 git 命令不可用")

        logger.warning("無法檢測到有效的更新環境")
        return UpdateMode.NONE

    def _check_git_available(self) -> bool:
        """檢查 git 命令是否可用"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def check_for_updates(self) -> Optional[Dict]:
        """
        檢查更新

        Returns:
            Dict: 更新信息，無更新返回 None
            {
                'mode': 'git' | 'ota',
                'current_version': '2.0.5',
                'new_version': '2.0.6',
                'details': {...}  # Git: commit 信息, OTA: UpdateInfo
            }
        """
        if self.mode == UpdateMode.NONE:
            logger.warning("當前環境不支持自動更新")
            return None

        if self.mode == UpdateMode.GIT:
            return self._check_git_updates()
        elif self.mode == UpdateMode.OTA:
            return self._check_ota_updates()

    def _check_git_updates(self) -> Optional[Dict]:
        """
        檢查 Git 更新

        Returns:
            Dict: 更新信息
        """
        try:
            # 切換到專案目錄
            os.chdir(self.project_root)

            # 獲取當前分支
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10
            )
            current_branch = result.stdout.strip()

            # 獲取遠端更新
            subprocess.run(
                ["git", "fetch", "origin"],
                capture_output=True,
                timeout=30
            )

            # 檢查是否有新提交
            result = subprocess.run(
                ["git", "rev-list", "--count", f"HEAD..origin/{current_branch}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            new_commits = int(result.stdout.strip())

            if new_commits > 0:
                # 獲取更新詳情
                result = subprocess.run(
                    ["git", "log", f"HEAD..origin/{current_branch}", "--oneline", "-5"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                commit_log = result.stdout.strip()

                return {
                    'mode': 'git',
                    'current_version': __version__,
                    'new_commits': new_commits,
                    'branch': current_branch,
                    'commit_log': commit_log
                }

            logger.info("Git: 已是最新版本")
            return None

        except subprocess.TimeoutExpired:
            logger.error("Git 命令超時")
            return None
        except Exception as e:
            logger.error(f"檢查 Git 更新失敗: {e}")
            return None

    def _check_ota_updates(self) -> Optional[Dict]:
        """
        檢查 OTA 更新

        Returns:
            Dict: 更新信息
        """
        if not self.ota_updater:
            return None

        update_info = self.ota_updater.check_for_updates()

        if update_info:
            return {
                'mode': 'ota',
                'current_version': __version__,
                'new_version': update_info.version,
                'details': update_info
            }

        return None

    def perform_update(self, update_info: Dict, restart: bool = True) -> bool:
        """
        執行更新

        Args:
            update_info: 從 check_for_updates 返回的更新信息
            restart: 是否在更新後重啟（僅適用於 OTA）

        Returns:
            bool: 是否成功
        """
        mode = update_info.get('mode')

        if mode == 'git':
            return self._perform_git_update(update_info)
        elif mode == 'ota':
            return self._perform_ota_update(update_info, restart)

        return False

    def _perform_git_update(self, update_info: Dict) -> bool:
        """
        執行 Git 更新

        Args:
            update_info: Git 更新信息

        Returns:
            bool: 是否成功
        """
        try:
            os.chdir(self.project_root)

            branch = update_info.get('branch', 'master')

            # 執行 git pull
            result = subprocess.run(
                ["git", "pull", "origin", branch],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                logger.info("Git 更新成功")
                logger.info(f"更新輸出:\n{result.stdout}")

                # 檢查是否需要更新 Python 依賴
                if "requirements.txt" in result.stdout:
                    logger.warning("⚠️ requirements.txt 已更新，請手動運行: pip install -r requirements.txt")

                return True
            else:
                logger.error(f"Git 更新失敗: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Git pull 超時")
            return False
        except Exception as e:
            logger.error(f"執行 Git 更新失敗: {e}")
            return False

    def _perform_ota_update(self, update_info: Dict, restart: bool) -> bool:
        """
        執行 OTA 更新

        Args:
            update_info: OTA 更新信息
            restart: 是否重啟

        Returns:
            bool: 是否成功
        """
        if not self.ota_updater:
            return False

        details: UpdateInfo = update_info.get('details')
        if not details:
            return False

        # 下載更新
        logger.info(f"開始下載更新: {details.version}")
        download_path = self.ota_updater.download_update(details)

        if not download_path:
            logger.error("下載更新失敗")
            return False

        # 安裝更新
        logger.info("開始安裝更新...")
        return self.ota_updater.install_update(download_path, restart)

    def get_current_version(self) -> str:
        """獲取當前版本"""
        return __version__

    def get_update_mode_description(self) -> str:
        """獲取更新模式描述（給用戶看）"""
        descriptions = {
            UpdateMode.GIT: "Git 源碼更新（適用於開發環境）",
            UpdateMode.OTA: "OTA 遠端更新（適用於打包版本）",
            UpdateMode.NONE: "無法自動更新（請手動更新）"
        }
        return descriptions.get(self.mode, "未知模式")


# 全局單例
_smart_updater_instance = None


def get_smart_updater() -> SmartUpdater:
    """獲取智能更新器單例"""
    global _smart_updater_instance
    if _smart_updater_instance is None:
        _smart_updater_instance = SmartUpdater()
    return _smart_updater_instance
