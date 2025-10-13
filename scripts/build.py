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
from datetime import datetime
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from basler_pyqt6.version import __version__, APP_NAME_SHORT, BUILD_TYPE


class AppBuilder:
    """應用打包器"""

    def __init__(self):
        self.project_root = project_root
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.releases_dir = self.project_root / "releases"
        self.spec_file = self.project_root / "basler_pyqt6.spec"

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
            for root, dirs, files in os.walk(release_dir):
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

    def run(self, skip_clean=False):
        """執行完整的構建流程"""
        print("=" * 60)
        print(f"🚀 開始構建 {APP_NAME_SHORT} v{__version__}")
        print("=" * 60)
        print()

        try:
            if not skip_clean:
                self.clean()

            self.build()
            release_info = self.create_release_package()

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

    args = parser.parse_args()

    builder = AppBuilder()

    if args.no_package:
        if not args.skip_clean:
            builder.clean()
        builder.build()
    else:
        builder.run(skip_clean=args.skip_clean)


if __name__ == '__main__':
    main()
