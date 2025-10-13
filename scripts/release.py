#!/usr/bin/env python3
"""
發布腳本
將構建好的應用上傳到更新服務器
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional

import requests

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from basler_pyqt6.version import __version__, UPDATE_SERVER_URL


class ReleasePublisher:
    """發布管理器"""

    def __init__(self, server_url: str = UPDATE_SERVER_URL):
        self.server_url = server_url
        self.releases_dir = project_root / "releases"

    def find_latest_release(self) -> Optional[tuple]:
        """
        尋找最新的發布包

        Returns:
            (zip_path, info_path) 或 None
        """
        if not self.releases_dir.exists():
            print("❌ releases 目錄不存在")
            return None

        # 尋找所有 ZIP 文件
        zip_files = list(self.releases_dir.glob("*.zip"))
        if not zip_files:
            print("❌ 找不到發布包")
            return None

        # 按修改時間排序，取最新的
        latest_zip = max(zip_files, key=lambda p: p.stat().st_mtime)

        # 尋找對應的 info 文件
        info_file = latest_zip.parent / f"{latest_zip.stem}_info.json"

        if not info_file.exists():
            print(f"⚠️ 找不到信息文件: {info_file}")
            return latest_zip, None

        return latest_zip, info_file

    def upload_release(self, zip_path: Path, info_path: Optional[Path],
                      release_notes: str = "") -> bool:
        """
        上傳發布包到服務器

        Args:
            zip_path: ZIP 文件路徑
            info_path: 信息文件路徑
            release_notes: 發布說明

        Returns:
            是否上傳成功
        """
        print(f"📤 準備上傳發布包...")
        print(f"   文件: {zip_path.name}")

        # 讀取發布信息
        release_info = {}
        if info_path and info_path.exists():
            with open(info_path, 'r', encoding='utf-8') as f:
                release_info = json.load(f)

        # 準備上傳數據
        files = {
            'file': (zip_path.name, open(zip_path, 'rb'), 'application/zip')
        }

        data = {
            'version': release_info.get('version', __version__),
            'build_type': release_info.get('build_type', 'release'),
            'md5': release_info.get('md5', ''),
            'release_notes': release_notes,
        }

        try:
            # 上傳到服務器
            url = f"{self.server_url}/updates/upload"
            print(f"   上傳到: {url}")

            response = requests.post(url, files=files, data=data, timeout=300)
            response.raise_for_status()

            result = response.json()
            print(f"\n✅ 上傳成功!")
            print(f"   版本: {result.get('version')}")
            print(f"   下載 URL: {result.get('download_url')}")

            return True

        except requests.RequestException as e:
            print(f"\n❌ 上傳失敗: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"   錯誤詳情: {error_detail}")
                except:
                    print(f"   響應內容: {e.response.text}")
            return False
        except Exception as e:
            print(f"\n❌ 發生錯誤: {e}")
            return False
        finally:
            files['file'][1].close()

    def publish(self, release_notes: str = "", zip_path: Optional[str] = None) -> bool:
        """
        發布最新版本

        Args:
            release_notes: 發布說明
            zip_path: 指定要上傳的 ZIP 文件路徑（可選）

        Returns:
            是否發布成功
        """
        print("=" * 60)
        print(f"🚀 發布 Basler Vision System v{__version__}")
        print("=" * 60)
        print()

        # 尋找發布包
        if zip_path:
            zip_file = Path(zip_path)
            if not zip_file.exists():
                print(f"❌ 找不到指定的文件: {zip_path}")
                return False
            info_file = zip_file.parent / f"{zip_file.stem}_info.json"
            if not info_file.exists():
                info_file = None
        else:
            result = self.find_latest_release()
            if not result:
                return False
            zip_file, info_file = result

        print(f"📦 找到發布包: {zip_file.name}")
        print(f"   大小: {zip_file.stat().st_size / (1024*1024):.2f} MB")
        print()

        # 上傳
        success = self.upload_release(zip_file, info_file, release_notes)

        print()
        print("=" * 60)
        if success:
            print("🎉 發布成功!")
        else:
            print("❌ 發布失敗")
        print("=" * 60)

        return success


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="發布 Basler Vision System 應用")
    parser.add_argument('--notes', type=str, default="",
                       help='發布說明')
    parser.add_argument('--file', type=str, default=None,
                       help='指定要上傳的 ZIP 文件路徑')
    parser.add_argument('--server', type=str, default=UPDATE_SERVER_URL,
                       help='更新服務器 URL')

    args = parser.parse_args()

    publisher = ReleasePublisher(server_url=args.server)
    success = publisher.publish(release_notes=args.notes, zip_path=args.file)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
