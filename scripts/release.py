#!/usr/bin/env python3
"""
發布腳本 - SFTP 上傳版本
使用 SFTP 上傳發布包到遠端服務器並自動部署
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from basler_pyqt6.version import __version__, BUILD_TYPE, BUILD_DATE


class SFTPReleasePublisher:
    """SFTP 發布管理器"""

    def __init__(self):
        self.project_root = project_root
        self.releases_dir = project_root / "releases"
        self.sftp_config_path = project_root / ".vscode" / "sftp.json"
        self.sftp_config = None
        self.ssh = None
        self.sftp = None

    def load_sftp_config(self) -> dict:
        """載入 SFTP 配置"""
        if not self.sftp_config_path.exists():
            print(f"❌ 找不到 SFTP 配置文件: {self.sftp_config_path}")
            print("   請先創建 .vscode/sftp.json 配置文件")
            sys.exit(1)

        with open(self.sftp_config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        required_keys = ['host', 'username', 'password', 'remotePath']
        for key in required_keys:
            if key not in config:
                print(f"❌ SFTP 配置缺少必要字段: {key}")
                sys.exit(1)

        self.sftp_config = config
        return config

    def connect_sftp(self):
        """建立 SFTP 連接"""
        try:
            import paramiko
        except ImportError:
            print("❌ 缺少 paramiko 模組")
            print("   請安裝: pip install paramiko")
            sys.exit(1)

        config = self.sftp_config
        host = config['host']
        port = config.get('port', 22)
        username = config['username']
        password = config['password']

        print(f"🔗 連接到 {username}@{host}:{port}...")

        try:
            # 建立 SSH 連接
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=10
            )

            # 建立 SFTP 連接
            self.sftp = self.ssh.open_sftp()
            print(f"✅ 連接成功\n")
            return True

        except Exception as e:
            print(f"❌ 連接失敗: {e}")
            return False

    def close_connection(self):
        """關閉連接"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()

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

    def upload_file(self, local_path: Path, remote_path: str) -> bool:
        """
        上傳文件到遠端

        Args:
            local_path: 本地文件路徑
            remote_path: 遠端文件路徑

        Returns:
            是否上傳成功
        """
        try:
            file_size = local_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            print(f"📤 上傳: {local_path.name}")
            print(f"   大小: {file_size_mb:.2f} MB")
            print(f"   目標: {remote_path}")

            # 確保遠端目錄存在
            remote_dir = os.path.dirname(remote_path)
            try:
                self.sftp.stat(remote_dir)
            except FileNotFoundError:
                print(f"   創建遠端目錄: {remote_dir}")
                self.execute_remote_command(f"mkdir -p {remote_dir}")

            # 上傳文件（帶進度）
            uploaded = 0

            def progress_callback(transferred, total):
                nonlocal uploaded
                uploaded = transferred
                percent = (transferred / total) * 100 if total > 0 else 0
                print(f"\r   進度: {percent:.1f}% ({transferred}/{total} bytes)", end='', flush=True)

            self.sftp.put(str(local_path), remote_path, callback=progress_callback)
            print(f"\n✅ 上傳完成\n")
            return True

        except Exception as e:
            print(f"\n❌ 上傳失敗: {e}")
            return False

    def execute_remote_command(self, command: str) -> tuple:
        """
        在遠端執行命令

        Args:
            command: 要執行的命令

        Returns:
            (stdout, stderr, exit_code)
        """
        try:
            _, stdout, stderr = self.ssh.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            return stdout_text, stderr_text, exit_code
        except Exception as e:
            return "", str(e), 1

    def deploy_release(self, zip_path: Path, info_path: Optional[Path], release_notes: str = "") -> bool:
        """
        部署發布包到遠端服務器

        Args:
            zip_path: ZIP 文件路徑
            info_path: 信息文件路徑
            release_notes: 發布說明

        Returns:
            是否部署成功
        """
        config = self.sftp_config
        remote_dir = config['remotePath']
        remote_zip = f"{remote_dir}/{zip_path.name}"
        remote_info = f"{remote_dir}/{info_path.name}" if info_path else None

        print("=" * 60)
        print(f"🚀 開始部署版本 {__version__}")
        print("=" * 60)
        print()

        # 1. 上傳 ZIP 文件
        if not self.upload_file(zip_path, remote_zip):
            return False

        # 2. 上傳 info 文件（如果存在）
        if info_path and info_path.exists():
            if not self.upload_file(info_path, remote_info):
                return False

        # 3. 檢查並安裝 unzip
        print("🔍 檢查遠端環境...")
        stdout, _, _ = self.execute_remote_command("which unzip")

        if not stdout.strip():
            print("⚠️  遠端服務器缺少 unzip，嘗試安裝...")
            # 嘗試使用不同的包管理器安裝
            install_commands = [
                "apt-get update && apt-get install -y unzip",  # Debian/Ubuntu
                "yum install -y unzip",  # CentOS/RHEL
                "apk add unzip",  # Alpine
            ]

            installed = False
            for cmd in install_commands:
                print(f"   嘗試: {cmd.split()[0]}...")
                _, stderr, exit_code = self.execute_remote_command(f"sudo {cmd} 2>&1")
                if exit_code == 0:
                    print("   ✅ unzip 安裝成功")
                    installed = True
                    break

            if not installed:
                print("\n❌ 無法自動安裝 unzip")
                print("   請手動在服務器上執行以下命令之一:")
                print("   - Ubuntu/Debian: sudo apt-get install unzip")
                print("   - CentOS/RHEL: sudo yum install unzip")
                print("   - Alpine: sudo apk add unzip")
                print("\n   或使用 Python 解壓（見下方替代方案）")
                return False
        else:
            print("✅ unzip 已安裝")

        # 4. 在遠端解壓縮
        print("📦 在遠端解壓縮...")
        extract_dir = f"{remote_dir}/BaslerVisionSystem_v{__version__}"

        commands = [
            f"cd {remote_dir}",
            f"unzip -o {zip_path.name} -d {extract_dir}",
            f"echo '✅ 解壓縮完成'"
        ]

        _, stderr, exit_code = self.execute_remote_command(" && ".join(commands))

        if exit_code != 0:
            print(f"❌ 解壓縮失敗:")
            print(stderr)
            return False

        print(f"✅ 解壓縮完成: {extract_dir}\n")

        # 5. 創建/更新 update_manifest.json
        print("📝 更新版本清單...")
        manifest = self.create_update_manifest(zip_path, info_path, release_notes)

        # 將 manifest 寫入本地臨時文件
        temp_manifest = self.project_root / "temp_manifest.json"
        with open(temp_manifest, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # 上傳到遠端
        remote_manifest = f"{remote_dir}/update_manifest.json"
        if self.upload_file(temp_manifest, remote_manifest):
            temp_manifest.unlink()  # 刪除臨時文件
            print("✅ 版本清單已更新\n")
        else:
            return False

        # 6. 顯示部署結果
        print("=" * 60)
        print("🎉 部署成功!")
        print("=" * 60)
        print(f"📦 版本: {__version__}")
        print(f"🏷️  類型: {BUILD_TYPE}")
        print(f"📅 日期: {BUILD_DATE}")
        print(f"📁 位置: {extract_dir}")
        print(f"📋 清單: {remote_manifest}")
        print("=" * 60)

        return True

    def create_update_manifest(self, zip_path: Path, info_path: Optional[Path], release_notes: str) -> dict:
        """
        創建更新清單

        Args:
            zip_path: ZIP 文件路徑
            info_path: 信息文件路徑
            release_notes: 發布說明

        Returns:
            更新清單字典
        """
        # 讀取 info 文件（如果存在）
        release_info = {}
        if info_path and info_path.exists():
            with open(info_path, 'r', encoding='utf-8') as f:
                release_info = json.load(f)

        # 構建下載 URL
        config = self.sftp_config
        # 假設有一個 HTTP 服務器提供下載（稍後配置）
        download_url = f"http://{config['host']}/releases/{zip_path.name}"

        # 創建版本信息
        version_info = {
            "version": __version__,
            "release_date": BUILD_DATE,
            "download_url": download_url,
            "file_size": zip_path.stat().st_size,
            "md5": release_info.get('md5', ''),
            "changelog": release_notes or "版本更新",
            "mandatory": False,
            "build_type": BUILD_TYPE
        }

        # 嘗試讀取現有的 manifest
        manifest = {
            "latest_version": __version__,
            "versions": {
                __version__: version_info
            }
        }

        # 如果遠端已有 manifest，合併
        try:
            remote_manifest = f"{config['remotePath']}/update_manifest.json"
            temp_file = self.project_root / "temp_download_manifest.json"

            self.sftp.get(remote_manifest, str(temp_file))

            with open(temp_file, 'r', encoding='utf-8') as f:
                existing_manifest = json.load(f)

            # 合併版本信息
            manifest['versions'] = existing_manifest.get('versions', {})
            manifest['versions'][__version__] = version_info

            temp_file.unlink()

        except FileNotFoundError:
            # 首次創建，沒有現有 manifest
            pass
        except Exception as e:
            print(f"⚠️ 讀取現有 manifest 失敗: {e}")

        return manifest

    def publish(self, release_notes: str = "", zip_path: Optional[str] = None) -> bool:
        """
        發布最新版本

        Args:
            release_notes: 發布說明
            zip_path: 指定要上傳的 ZIP 文件路徑（可選）

        Returns:
            是否發布成功
        """
        # 載入 SFTP 配置
        self.load_sftp_config()

        # 建立連接
        if not self.connect_sftp():
            return False

        try:
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

            # 部署
            success = self.deploy_release(zip_file, info_file, release_notes)

            return success

        finally:
            # 關閉連接
            self.close_connection()


def show_version_info():
    """顯示當前版本信息"""
    print("=" * 60)
    print("📋 當前版本信息")
    print("=" * 60)
    print(f"版本: {__version__}")
    print(f"類型: {BUILD_TYPE}")
    print(f"日期: {BUILD_DATE}")
    print("=" * 60)
    print()


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="發布 Basler Vision System 應用（SFTP 版本）")
    parser.add_argument('--notes', type=str, default="",
                       help='發布說明')
    parser.add_argument('--file', type=str, default=None,
                       help='指定要上傳的 ZIP 文件路徑')
    parser.add_argument('--version', action='store_true',
                       help='顯示版本信息')

    args = parser.parse_args()

    # 顯示版本信息
    if args.version:
        show_version_info()
        sys.exit(0)

    # 顯示版本信息
    show_version_info()

    # 檢查是否安裝 paramiko
    try:
        import paramiko
    except ImportError:
        print("❌ 缺少 paramiko 模組")
        print("   請安裝: pip install paramiko")
        print()
        sys.exit(1)

    # 執行發布
    publisher = SFTPReleasePublisher()
    success = publisher.publish(release_notes=args.notes, zip_path=args.file)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
