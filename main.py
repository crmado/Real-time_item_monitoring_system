"""
实时物品监测系统主程序入口
"""

import os
import sys
import logging
import traceback
import tkinter as tk
import cv2

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入自定义模块
from models.camera_manager import CameraManager
from controllers.system_controller import SystemController
from views.main_window import MainWindow
from utils.ui_style_manager import UIStyleManager
from utils.ui_theme import UITheme
from utils.language import set_language, get_text

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)

def check_camera_permission():
    """检查相机权限"""
    if sys.platform == 'darwin':  # macOS
        try:
            # 尝试打开相机以触发权限请求
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                ret, frame = cap.read()
                cap.release()
                if ret:
                    logging.info("相机权限已获得")
                    return True
            logging.warning("未能获得相机权限")
            return False
        except Exception as e:
            logging.error(f"检查相机权限时发生错误: {str(e)}")
            return False
    return True

def main():
    """主程序入口"""
    try:
        print("程序启动...")
        
        # 检查相机权限
        if not check_camera_permission():
            print("无法获得相机权限，程序将以受限模式运行")
            logging.error("无法获得相机权限，程序将以受限模式运行")
        
        # 创建Tkinter根窗口
        print("创建Tkinter根窗口...")
        root = tk.Tk()
        root.title(get_text("app_title", "实时物品监测系统"))
        root.geometry("1200x800")
        root.minsize(1000, 700)
        
        # 设置语言
        print("设置语言...")
        set_language("zh_CN")
        
        # 初始化UI样式
        print("初始化UI样式...")
        ui_style_manager = UIStyleManager(root)
        ui_style_manager.apply_theme()
        
        # 创建主窗口
        print("创建主窗口...")
        main_window = MainWindow(root)
        
        # 创建系统控制器
        print("创建系统控制器...")
        system_controller = SystemController(main_window)
        
        # 设置主窗口的系统控制器
        print("设置主窗口的系统控制器...")
        main_window.set_system_controller(system_controller)
        
        # 更新相机源列表
        print("更新相机源列表...")
        available_sources = system_controller.camera_manager.get_available_sources()
        print(f"可用相机源: {available_sources}")
        main_window.control_panel.set_camera_sources(available_sources)
        
        # 默认选择内置相机
        default_camera = None
        if "Built-in Camera" in available_sources:
            default_camera = "Built-in Camera"
        elif "USB Camera 0" in available_sources:
            default_camera = "USB Camera 0"
        elif available_sources:
            default_camera = available_sources[0]
            
        if default_camera:
            print(f"默认选择相机: {default_camera}")
            main_window.control_panel.set_camera_source(default_camera)
            # 自动打开相机
            print(f"自动打开相机: {default_camera}")
            system_controller.handle_camera_open(default_camera)
        else:
            print("没有可用的相机源")
        
        # 启动UI更新
        print("启动UI更新...")
        system_controller.start_ui_update()
        
        # 运行主循环
        print("运行主循环...")
        root.mainloop()
        
    except Exception as e:
        print(f"程序启动时发生错误: {str(e)}")
        logging.error(f"程序启动时发生错误: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()