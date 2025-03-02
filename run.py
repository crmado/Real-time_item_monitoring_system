#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
改進的啟動程序
提供更好的錯誤處理和錯誤報告功能
"""

import os
import sys
import traceback
import logging
import datetime
import platform
from main import main as program_main
import cv2


def check_requirements():
    """檢查系統依賴是否滿足"""
    try:
        print("檢查系統需求...")

        # 檢查 Python 版本
        python_version = sys.version.split()[0]
        print(f"Python 版本: {python_version}")
        if not python_version.startswith("3."):
            print("警告：建議使用 Python 3.7 以上版本")

        # 檢查關鍵庫
        try:
            import tkinter
            print("Tkinter: 已安裝")
        except ImportError:
            print("錯誤：缺少 Tkinter 庫，這是必需的")
            return False

        try:
            print(f"OpenCV: 已安裝 (版本 {cv2.__version__})")
        except ImportError:
            print("錯誤：缺少 OpenCV 庫，這是必需的")
            return False

        try:
            from PIL import Image
            print("Pillow: 已安裝")
        except ImportError:
            print("錯誤：缺少 Pillow 庫，這是必需的")
            return False

        # 檢查作業系統
        print(f"作業系統: {platform.system()} {platform.release()}")

        return True

    except Exception as e:
        print(f"檢查系統需求時發生錯誤: {str(e)}")
        return False


def setup_error_logging():
    """設置錯誤日誌系統"""
    try:
        # 確保日誌目錄存在
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 創建錯誤日誌文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        error_log_file = os.path.join(log_dir, f"error_{timestamp}.log")

        # 設置基本日誌配置
        logging.basicConfig(
            filename=error_log_file,
            level=logging.ERROR,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 同時輸出到控制台
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

        return error_log_file

    except Exception as e:
        print(f"設置錯誤日誌系統時發生錯誤: {str(e)}")
        return None


def collect_system_info():
    """收集系統信息用於診斷"""
    info = []

    try:
        info.append(f"Python 版本: {sys.version}")
        info.append(f"平台: {platform.platform()}")

        # 收集庫版本
        try:
            import cv2
            info.append(f"OpenCV 版本: {cv2.__version__}")
        except:
            info.append("OpenCV: 未找到或無法匯入")

        try:
            import numpy
            info.append(f"NumPy 版本: {numpy.__version__}")
        except:
            info.append("NumPy: 未找到或無法匯入")

        try:
            import tkinter
            info.append(f"Tkinter: 已安裝 ({tkinter.TkVersion})")
        except:
            info.append("Tkinter: 未找到或無法匯入")

        try:
            from PIL import Image, __version__ as pil_version
            info.append(f"Pillow 版本: {pil_version}")
        except:
            info.append("Pillow: 未找到或無法匯入")

        # 嘗試收集資源信息
        import psutil
        info.append(f"CPU 核心數: {psutil.cpu_count(logical=True)}")
        memory = psutil.virtual_memory()
        info.append(f"記憶體: 總計 {memory.total / (1024 ** 3):.2f} GB，可用 {memory.available / (1024 ** 3):.2f} GB")

    except Exception as e:
        info.append(f"收集系統信息時發生錯誤: {str(e)}")

    return "\n".join(info)


def main():
    """主函數"""
    # 設置錯誤日誌
    error_log_file = setup_error_logging()

    try:
        # 檢查系統需求
        if not check_requirements():
            print("\n系統不滿足運行需求，程序將退出。")
            input("按任意鍵關閉...")
            return

        print("\n啟動物件監測系統...")

        # 導入主程序
        try:
            program_main()
        except ImportError:
            try:
                # 嘗試其他可能的主模塊
                program_main()
            except ImportError:
                raise ImportError("無法匯入主程序模塊，請確認程式檔案是否完整")

    except Exception as e:
        # 記錄錯誤
        logging.error(f"嚴重錯誤: {str(e)}")
        logging.error(traceback.format_exc())

        # 收集系統信息
        system_info = collect_system_info()
        logging.error("系統信息:\n" + system_info)

        # 準備錯誤報告
        error_report = f"""
錯誤報告
======================
時間: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
錯誤訊息: {str(e)}

詳細錯誤追踪:
{traceback.format_exc()}

系統信息:
{system_info}
======================

詳細日誌請查看: {error_log_file}
"""
        # 顯示錯誤報告
        print("\n" + "=" * 50)
        print("程序執行時發生錯誤!")
        print(error_report)

        # 嘗試顯示GUI錯誤對話框
        try:
            import tkinter as tk
            from tkinter import messagebox

            # 建立隱藏的根窗口
            root = tk.Tk()
            root.withdraw()

            messagebox.showerror(
                "系統錯誤",
                f"程序執行時發生錯誤:\n{str(e)}\n\n詳細日誌已保存到:\n{error_log_file}"
            )
        except:
            # 如果GUI錯誤顯示失敗，使用命令行模式
            print("\n請將以上錯誤信息提供給開發者以協助解決問題。")
            input("\n按任意鍵關閉...")


if __name__ == "__main__":
    main()