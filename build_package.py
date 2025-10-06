#!/usr/bin/env python3
"""
打包腳本
自動化構建應用程序
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


class PackageBuilder:
    """打包構建器"""

    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.spec_file = self.project_root / "basler_pyqt6.spec"

    def clean(self):
        """清理舊的構建文件"""
        print("🧹 清理舊的構建文件...")

        dirs_to_clean = [self.dist_dir, self.build_dir]

        for dir_path in dirs_to_clean:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                print(f"   ✓ 已刪除: {dir_path}")

        print("✅ 清理完成\n")

    def build(self):
        """執行打包"""
        print("📦 開始打包應用...")
        print(f"   規格文件: {self.spec_file}")

        if not self.spec_file.exists():
            print(f"❌ 規格文件不存在: {self.spec_file}")
            return False

        try:
            # 運行 PyInstaller
            cmd = [
                sys.executable,
                "-m", "PyInstaller",
                str(self.spec_file),
                "--clean",  # 清理臨時文件
                "--noconfirm",  # 不詢問覆蓋
            ]

            print(f"   執行命令: {' '.join(cmd)}\n")

            result = subprocess.run(cmd, cwd=self.project_root)

            if result.returncode != 0:
                print("❌ 打包失敗")
                return False

            print("\n✅ 打包完成")
            return True

        except Exception as e:
            print(f"❌ 打包過程出錯: {str(e)}")
            return False

    def create_installer(self):
        """創建安裝程序（可選）"""
        print("\n📦 創建安裝程序...")

        # 這裡可以整合 NSIS、Inno Setup 等工具
        # 示例：使用 NSIS
        nsis_script = self.project_root / "installer.nsi"

        if nsis_script.exists():
            try:
                subprocess.run(["makensis", str(nsis_script)])
                print("✅ 安裝程序創建完成")
            except FileNotFoundError:
                print("⚠️ NSIS 未安裝，跳過安裝程序創建")
        else:
            print("⚠️ 未找到 NSIS 腳本，跳過安裝程序創建")

    def package_release(self):
        """打包發布文件"""
        print("\n📂 打包發布文件...")

        # 獲取版本號
        version_file = self.project_root / "basler_pyqt6" / "version.py"
        version = "unknown"

        if version_file.exists():
            with open(version_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('__version__'):
                        version = line.split('=')[1].strip().strip('"\'')
                        break

        # 創建發布目錄
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        release_name = f"BaslerVisionSystem_v{version}_{timestamp}"
        release_dir = self.project_root / "releases" / release_name

        release_dir.mkdir(parents=True, exist_ok=True)

        # 複製打包好的文件
        dist_app_dir = self.dist_dir / "BaslerVisionSystem"

        if dist_app_dir.exists():
            shutil.copytree(
                dist_app_dir,
                release_dir / "BaslerVisionSystem",
                dirs_exist_ok=True
            )
            print(f"   ✓ 已複製: {dist_app_dir}")

        # 複製說明文件
        docs_to_copy = ["README.md", "QUICK_START.md", "requirements.txt"]

        for doc in docs_to_copy:
            doc_path = self.project_root / doc
            if doc_path.exists():
                shutil.copy2(doc_path, release_dir)
                print(f"   ✓ 已複製: {doc}")

        # 創建版本信息文件
        version_info_path = release_dir / "VERSION.txt"
        with open(version_info_path, 'w', encoding='utf-8') as f:
            f.write(f"Basler Vision System\n")
            f.write(f"版本: {version}\n")
            f.write(f"構建時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        print(f"✅ 發布包已創建: {release_dir}\n")

        return release_dir

    def run(self):
        """執行完整打包流程"""
        print("=" * 70)
        print("🏭 Basler Vision System - 打包工具")
        print("=" * 70)
        print()

        # 1. 清理
        self.clean()

        # 2. 打包
        if not self.build():
            print("\n❌ 打包失敗，流程終止")
            return False

        # 3. 創建安裝程序（可選）
        # self.create_installer()

        # 4. 打包發布文件
        release_dir = self.package_release()

        print("=" * 70)
        print("🎉 打包流程完成！")
        print("=" * 70)
        print(f"\n📁 發布文件位置: {release_dir}")
        print()

        return True


def main():
    """主函數"""
    builder = PackageBuilder()
    success = builder.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
