"""
語言模組
管理系統的多語言支援
"""

import os
import json
import logging


# 語言資源字典
_resources = {}
_current_language = 'zh_TW'

# 語言名稱對照表
LANGUAGE_NAMES = {
    'zh_TW': '繁體中文',
    'en_US': 'English',
    'zh_CN': '简体中文'
}

# 備用語言資源
FALLBACK_RESOURCES = {
    'app_title': '物件監測系統',
    'current_count': '目前數量：',
    'target_count': '預計數量：',
    'buffer_point': '緩衝點：',
    'language': '語言：',
    'apply_settings': '套用設定',
    'system_log': '系統日誌：',
    'current_time': '目前時間：',
    'select_source': '選擇視訊來源：',
    'test_button': '測試鏡頭',
    'stop_test': '停止測試',
    'start_button': '開始監測',
    'stop_button': '停止監測'
}


class LanguageManager:
    """語言管理類別"""

    def __init__(self, default_language='zh_TW'):
        """
        初始化語言管理器

        Args:
            default_language: 預設語言代碼
        """
        self.current_language = default_language
        self.languages = {}
        self.available_languages = []
        self.load_languages()

    def load_languages(self):
        """載入所有可用的語言檔案"""
        try:
            # 語言檔案目錄
            lang_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'languages'
            )

            # 確保目錄存在
            if not os.path.exists(lang_dir):
                os.makedirs(lang_dir)
                # 建立預設語言檔
                self._create_default_language_files(lang_dir)

            # 載入所有語言檔
            for file_name in os.listdir(lang_dir):
                if file_name.endswith('.json'):
                    language_code = file_name.split('.')[0]
                    self.available_languages.append(language_code)

                    with open(os.path.join(lang_dir, file_name), 'r', encoding='utf-8') as f:
                        self.languages[language_code] = json.load(f)

            logging.info(f"已載入 {len(self.available_languages)} 種語言: {', '.join(self.available_languages)}")

        except Exception as e:
            logging.error(f"載入語言檔案時發生錯誤：{str(e)}")
            # 確保至少有預設語言
            if not self.languages:
                self._create_fallback_language()

    def _create_default_language_files(self, lang_dir):
        """建立預設語言檔案"""
        # 繁體中文 (預設)
        zh_tw = {
            "app_title": "即時物件監測系統",
            "select_source": "選擇視訊來源：",
            "test_button": "測試鏡頭",
            "stop_test": "停止測試",
            "start_button": "開始監測",
            "stop_button": "停止監測",
            "current_count": "目前數量：",
            "target_count": "預計數量：",
            "buffer_point": "緩衝點：",
            "apply_settings": "套用設定",
            "system_log": "系統日誌：",
            "current_time": "目前時間：",
            "version": "版本：",
            "roi_position": "ROI位置：",
            "buffer_warning": "緩衝點警告",
            "buffer_warning_msg": "已達緩衝點 ({})，即將達到預計數量！",
            "target_reached": "完成通知",
            "target_reached_msg": "已達預計數量 ({})！",
            "error_source": "錯誤：請選擇視訊來源",
            "error_buffer_target": "錯誤：緩衝點必須小於預計數量",
            "error_negative": "錯誤：數值不能為負數",
            "error_invalid_number": "錯誤：請輸入有效數字",
            "start_monitoring": "開始監測 - {}",
            "stop_monitoring": "停止監測",
            "update_complete": "更新完成",
            "update_complete_msg": "程式已更新，請重新啟動",
            "update_failed": "更新失敗",
            "update_failed_msg": "更新過程中發生錯誤：{}",
            "update_tips": "更新提示",
            "update_tips_msg": "發現新版本，是否更新？",
            "roi_drag_hint": "拖曳綠線調整ROI位置",
            "theme": "主題：",
            "light_theme": "亮色模式",
            "dark_theme": "暗色模式",
            "theme_changed": "已切換至{}模式"
        }

        # 英文
        en_us = {
            "app_title": "Real-time Item Monitoring System",
            "select_source": "Select Video Source:",
            "test_button": "Test Lenses",
            "stop_test": "Stop Test",
            "start_button": "Start Monitoring",
            "stop_button": "Stop Monitoring",
            "current_count": "Current Count:",
            "target_count": "Estimated Quantity:",
            "buffer_point": "Buffer Point:",
            "apply_settings": "Apply Settings",
            "system_log": "System Log:",
            "current_time": "Current Time:",
            "version": "Version:",
            "roi_position": "ROI Position:",
            "buffer_warning": "Buffer Point Warning",
            "buffer_warning_msg": "Buffer point ({}) reached, estimated number almost reached!",
            "target_reached": "Completion Notification",
            "target_reached_msg": "The target number ({}) has been reached!",
            "error_source": "Error: Please select a video source",
            "error_buffer_target": "Error: Buffer points must be less than the expected number",
            "error_negative": "Error: Value cannot be negative",
            "error_invalid_number": "Error: Please enter a valid number",
            "start_monitoring": "Start monitoring - {}",
            "stop_monitoring": "Stop monitoring",
            "update_complete": "Update Complete",
            "update_complete_msg": "The program has been updated, please restart",
            "update_failed": "Update Failed",
            "update_failed_msg": "An error occurred during the update process: {}",
            "update_tips": "Update Tips",
            "update_tips_msg": "A new version has been found. Do you want to update?",
            "roi_drag_hint": "Drag the green line to adjust the ROI position",
            "theme": "Theme:",
            "light_theme": "Light Mode",
            "dark_theme": "Dark Mode",
            "theme_changed": "Switched to {} mode"
        }

        # 簡體中文
        zh_cn = {
            "app_title": "实时物体监测系统",
            "select_source": "选择视频源：",
            "test_button": "测试镜头",
            "stop_test": "停止测试",
            "start_button": "开始监测",
            "stop_button": "停止监测",
            "current_count": "当前数量：",
            "target_count": "预计数量：",
            "buffer_point": "缓冲点：",
            "apply_settings": "应用设置",
            "system_log": "系统日志：",
            "current_time": "当前时间：",
            "version": "版本：",
            "roi_position": "ROI位置：",
            "buffer_warning": "缓冲点警告",
            "buffer_warning_msg": "已达缓冲点 ({})，即将达到预计数量！",
            "target_reached": "完成通知",
            "target_reached_msg": "已达预计数量 ({})！",
            "error_source": "错误：请选择视频源",
            "error_buffer_target": "错误：缓冲点必须小于预计数量",
            "error_negative": "错误：数值不能为负数",
            "error_invalid_number": "错误：请输入有效数字",
            "start_monitoring": "开始监测 - {}",
            "stop_monitoring": "停止监测",
            "update_complete": "更新完成",
            "update_complete_msg": "程序已更新，请重新启动",
            "update_failed": "更新失败",
            "update_failed_msg": "更新过程中发生错误：{}",
            "update_tips": "更新提示",
            "update_tips_msg": "发现新版本，是否更新？",
            "roi_drag_hint": "拖拽绿线调整ROI位置",
            "theme": "主题：",
            "light_theme": "亮色模式",
            "dark_theme": "暗色模式",
            "theme_changed": "已切换至{}模式"
        }

        # 寫入語言檔案
        with open(os.path.join(lang_dir, 'zh_TW.json'), 'w', encoding='utf-8') as f:
            json.dump(zh_tw, f, ensure_ascii=False, indent=4)

        with open(os.path.join(lang_dir, 'en_US.json'), 'w', encoding='utf-8') as f:
            json.dump(en_us, f, ensure_ascii=False, indent=4)

        with open(os.path.join(lang_dir, 'zh_CN.json'), 'w', encoding='utf-8') as f:
            json.dump(zh_cn, f, ensure_ascii=False, indent=4)

    def _create_fallback_language(self):
        """建立備用語言資源（當無法載入語言檔時）"""
        self.languages['zh_TW'] = {
            "app_title": "即時物件監測系統",
            "select_source": "選擇視訊來源：",
            "start_button": "開始監測",
            "stop_button": "停止監測",
            # 基本必要的字串
        }
        self.available_languages = ['zh_TW']
        self.current_language = 'zh_TW'
        logging.warning("使用備用語言資源")

    def get_text(self, key, default=None):
        """
        取得指定鍵的文字

        Args:
            key: 文字鍵名
            default: 找不到時的預設值

        Returns:
            str: 對應的文字
        """
        if self.current_language in self.languages and key in self.languages[self.current_language]:
            return self.languages[self.current_language][key]

        # 如果當前語言找不到，嘗試使用默認語言
        if 'zh_TW' in self.languages and key in self.languages['zh_TW']:
            return self.languages['zh_TW'][key]

        # 如果還是找不到，返回默認值或鍵名
        return default if default is not None else key

    def change_language(self, language_code):
        """
        切換語言

        Args:
            language_code: 語言代碼

        Returns:
            bool: 是否成功切換
        """
        if language_code in self.available_languages:
            self.current_language = language_code
            logging.info(f"語言已切換為：{language_code}")
            return True
        else:
            logging.error(f"不支援的語言：{language_code}")
            return False

    def get_available_languages(self):
        """
        取得可用的語言列表

        Returns:
            list: 語言代碼列表
        """
        return self.available_languages


# 建立全域語言管理器實例
language_manager = LanguageManager()


def get_text(key, default=None):
    """
    便捷函數：取得指定鍵的文字

    Args:
        key: 文字鍵名
        default: 找不到時的預設值

    Returns:
        str: 對應的文字
    """
    return language_manager.get_text(key, default)


def change_language(language_code):
    """
    便捷函數：切換語言

    Args:
        language_code: 語言代碼

    Returns:
        bool: 是否成功切換
    """
    return language_manager.change_language(language_code)


def get_available_languages():
    """
    便捷函數：取得可用的語言列表

    Returns:
        list: 語言代碼列表
    """
    return language_manager.get_available_languages()


def get_language_name(lang_code):
    """
    獲取語言名稱

    Args:
        lang_code: 語言代碼

    Returns:
        str: 語言名稱
    """
    return LANGUAGE_NAMES.get(lang_code, lang_code)