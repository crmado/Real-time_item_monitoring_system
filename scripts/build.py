#!/usr/bin/env python3
"""
應用程式打包腳本
使用 PyInstaller 將應用打包成獨立可執行文件
"""

import os
import sys
import shutil
import hashlib
import zipfile
import platform
import subprocess
from datetime import datetime
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from basler_pyqt6.version import __version__, APP_NAME_SHORT, BUILD_TYPE


# 平台檢測
SYSTEM = platform.system().lower()  # 'windows', 'darwin', 'linux'
IS_WINDOWS = SYSTEM == 'windows'
IS_MACOS = SYSTEM == 'darwin'
IS_LINUX = SYSTEM == 'linux'


class AppBuilder:
    """應用打包器"""

    def __init__(self):
        self.project_root = project_root
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.releases_dir = self.project_root / "releases"
        self.spec_file = self.project_root / "basler_pyqt6.spec"
        self.installer_dir = self.project_root / "installer"

        # 平台相關配置
        self.platform_name = self._get_platform_name()
        self.installer_ext = self._get_installer_extension()

    def _get_platform_name(self):
        """獲取平台名稱"""
        if IS_WINDOWS:
            return "Windows"
        elif IS_MACOS:
            return "macOS"
        elif IS_LINUX:
            return "Linux"
        else:
            return "Unknown"

    def _get_installer_extension(self):
        """獲取安裝程序擴展名"""
        if IS_WINDOWS:
            return ".exe"
        elif IS_MACOS:
            return ".dmg"
        elif IS_LINUX:
            return ".AppImage"
        else:
            return ".zip"

    def clean(self):
        """清理舊的構建文件"""
        print("🧹 清理舊的構建文件...")

        for directory in [self.dist_dir, self.build_dir]:
            if directory.exists():
                print(f"   刪除: {directory}")
                shutil.rmtree(directory)

        print("✅ 清理完成\n")

    def build(self):
        """執行 PyInstaller 打包"""
        print("🔨 開始打包應用程式...")
        print(f"   版本: {__version__}")
        print(f"   平台: {self.platform_name}")
        print(f"   類型: {BUILD_TYPE}")

        # 執行 PyInstaller
        import PyInstaller.__main__

        PyInstaller.__main__.run([
            str(self.spec_file),
            '--clean',
            '--noconfirm',
        ])

        print("✅ 打包完成\n")

    def create_release_package(self):
        """創建發布包（ZIP）"""
        print("📦 創建發布包...")

        # 發布包名稱
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        release_name = f"{APP_NAME_SHORT}_v{__version__}_{timestamp}"
        release_dir = self.releases_dir / release_name

        # 創建發布目錄
        self.releases_dir.mkdir(exist_ok=True)
        if release_dir.exists():
            shutil.rmtree(release_dir)
        release_dir.mkdir()

        # 複製打包好的應用
        app_source = self.dist_dir / "BaslerVisionSystem"
        if not app_source.exists():
            print(f"❌ 錯誤: 找不到打包結果 {app_source}")
            return None

        app_dest = release_dir / "BaslerVisionSystem"
        print(f"   複製應用: {app_source} -> {app_dest}")
        shutil.copytree(app_source, app_dest)

        # 複製附加文件
        additional_files = [
            ("README.md", "README.md"),
            ("requirements.txt", "requirements.txt"),
        ]

        for src_name, dest_name in additional_files:
            src_path = self.project_root / src_name
            if src_path.exists():
                dest_path = release_dir / dest_name
                print(f"   複製文件: {src_name}")
                shutil.copy2(src_path, dest_path)

        # 創建版本信息文件
        version_file = release_dir / "VERSION.txt"
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(f"版本: {__version__}\n")
            f.write(f"構建類型: {BUILD_TYPE}\n")
            f.write(f"構建時間: {timestamp}\n")

        # 打包成 ZIP
        zip_path = self.releases_dir / f"{release_name}.zip"
        print(f"   創建 ZIP: {zip_path.name}")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(release_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(release_dir)
                    zipf.write(file_path, arcname)

        # 計算 MD5
        print("   計算 MD5 雜湊值...")
        md5_hash = hashlib.md5()
        with open(zip_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5_hash.update(chunk)
        md5_value = md5_hash.hexdigest()

        # 獲取文件大小
        file_size = zip_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # 創建發布信息文件
        release_info = {
            'version': __version__,
            'build_type': BUILD_TYPE,
            'timestamp': timestamp,
            'filename': zip_path.name,
            'file_size': file_size,
            'md5': md5_value,
        }

        info_file = self.releases_dir / f"{release_name}_info.json"
        import json
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(release_info, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 發布包創建完成!")
        print(f"   📁 位置: {zip_path}")
        print(f"   📊 大小: {file_size_mb:.2f} MB")
        print(f"   🔐 MD5: {md5_value}")
        print(f"   📄 信息: {info_file}")

        return release_info

    def create_installer(self):
        """創建平台特定的安裝程序"""
        print(f"🎁 創建 {self.platform_name} 安裝程序...")

        if IS_WINDOWS:
            return self._create_windows_installer()
        elif IS_MACOS:
            return self._create_macos_installer()
        elif IS_LINUX:
            return self._create_linux_installer()
        else:
            print("⚠️ 當前平台不支援自動創建安裝程序")
            return None

    def _create_windows_installer(self):
        """創建 Windows 安裝程序（使用 Inno Setup）"""
        iss_file = self.installer_dir / "windows_installer.iss"

        if not iss_file.exists():
            print("❌ 找不到 Inno Setup 配置文件")
            return None

        # 檢查 Inno Setup 是否安裝
        iscc_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
        ]

        iscc_exe = None
        for path in iscc_paths:
            if os.path.exists(path):
                iscc_exe = path
                break

        if not iscc_exe:
            print("⚠️ 未找到 Inno Setup，請從 https://jrsoftware.org/isdl.php 下載安裝")
            print("   或手動運行: iscc installer/windows_installer.iss")
            return None

        # 設置環境變量
        env = os.environ.copy()
        env['APP_VERSION'] = __version__

        # 執行編譯
        print(f"   使用 Inno Setup 編譯...")
        try:
            subprocess.run([iscc_exe, str(iss_file)],
                         env=env, check=True, capture_output=True)
            installer_name = f"BaslerVision_Setup_v{__version__}.exe"
            print(f"✅ Windows 安裝程序創建成功: {installer_name}")
            return self.releases_dir / installer_name
        except subprocess.CalledProcessError as e:
            print(f"❌ 創建安裝程序失敗: {e}")
            return None

    def _create_macos_installer(self):
        """創建 macOS DMG 安裝包"""
        print("   macOS DMG 創建需要在 GitHub Actions 或 macOS 機器上運行")
        print("   提示: 使用 'brew install create-dmg' 安裝工具")
        print("   或推送到 GitHub 讓 Actions 自動構建")
        return None

    def _create_linux_installer(self):
        """創建 Linux AppImage"""
        print("   Linux AppImage 創建需要在 GitHub Actions 或 Linux 機器上運行")
        print("   提示: 使用 linuxdeploy 工具")
        print("   或推送到 GitHub 讓 Actions 自動構建")
        return None

    def run(self, skip_clean=False, create_installer=True):
        """執行完整的構建流程"""
        print("=" * 60)
        print(f"🚀 開始構建 {APP_NAME_SHORT} v{__version__}")
        print(f"   平台: {self.platform_name}")
        print("=" * 60)
        print()

        try:
            if not skip_clean:
                self.clean()

            self.build()
            release_info = self.create_release_package()

            # 創建安裝程序（可選）
            if create_installer:
                installer_path = self.create_installer()
                if installer_path:
                    release_info['installer'] = str(installer_path)

            print()
            print("=" * 60)
            print("🎉 構建成功!")
            print("=" * 60)

            return release_info

        except Exception as e:
            print()
            print("=" * 60)
            print(f"❌ 構建失敗: {e}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            return None


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="打包 Basler Vision System 應用程式")
    parser.add_argument('--skip-clean', action='store_true',
                       help='跳過清理步驟')
    parser.add_argument('--no-package', action='store_true',
                       help='只打包不創建發布包')
    parser.add_argument('--no-installer', action='store_true',
                       help='不創建平台安裝程序')
    parser.add_argument('--show-platform', action='store_true',
                       help='顯示當前平台信息')

    args = parser.parse_args()

    builder = AppBuilder()

    # 顯示平台信息
    if args.show_platform:
        print(f"當前平台: {builder.platform_name}")
        print(f"系統: {SYSTEM}")
        print(f"安裝程序格式: {builder.installer_ext}")
        return

    if args.no_package:
        if not args.skip_clean:
            builder.clean()
        builder.build()
    else:
        builder.run(skip_clean=args.skip_clean,
                   create_installer=not args.no_installer)


if __name__ == '__main__':
    main()
