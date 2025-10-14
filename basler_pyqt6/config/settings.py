"""
basler_pyqt6 統一配置管理
整合所有檢測、UI、性能參數到單一配置檔案
基於 basler_mvc 的配置管理架構
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)

# 項目根目錄
PROJECT_ROOT = Path(__file__).parent.parent


# ==================== 檢測配置類 ====================

@dataclass
class DetectionConfig:
    """檢測參數配置 - 基於 basler_mvc 驗證參數"""

    # 🎯 面積過濾參數（極小零件優化）
    min_area: int = 2           # basler_mvc 驗證值：極小零件最小面積
    max_area: int = 3000        # basler_mvc 驗證值：最大面積

    # 物件形狀過濾參數（為小零件放寬條件）
    min_aspect_ratio: float = 0.001   # 極度寬鬆的長寬比
    max_aspect_ratio: float = 100.0
    min_extent: float = 0.001         # 極度降低填充比例要求
    max_solidity: float = 5.0         # 極度放寬結實性限制

    # 🎯 背景減除參數（basler_mvc 驗證的最佳參數）
    bg_history: int = 1000           # 大幅增加歷史幀數避免快速背景更新
    bg_var_threshold: int = 3        # basler_mvc 驗證值：極低閾值確保最高敏感度
    detect_shadows: bool = False
    bg_learning_rate: float = 0.001  # 極低學習率避免小零件被納入背景

    # 🎯 邊緣檢測參數（極高敏感度）
    gaussian_blur_kernel: tuple = (1, 1)  # 最小模糊保留最多細節
    canny_low_threshold: int = 2         # 極低閾值
    canny_high_threshold: int = 8        # 極低閾值
    binary_threshold: int = 1            # 極低閾值提高敏感度

    # 🔍 形態學處理參數（最小化處理保留小零件）
    dilate_kernel_size: tuple = (1, 1)
    dilate_iterations: int = 0
    close_kernel_size: tuple = (1, 1)
    enable_watershed_separation: bool = True
    opening_kernel_size: tuple = (1, 1)
    opening_iterations: int = 0
    connectivity: int = 4  # 4-連通或8-連通

    # 🎯 ROI 檢測區域參數
    roi_enabled: bool = True
    roi_height: int = 150              # ROI 區域高度
    roi_position_ratio: float = 0.10   # ROI 位置比例（0.0-1.0）

    # 🚀 高速模式參數
    ultra_high_speed_mode: bool = False
    target_fps: int = 280
    high_speed_bg_history: int = 100
    high_speed_bg_var_threshold: int = 8
    high_speed_min_area: int = 1
    high_speed_max_area: int = 2000
    high_speed_binary_threshold: int = 3


@dataclass
class GateConfig:
    """虛擬光柵計數參數配置"""

    # 🎯 虛擬光柵計數參數（工業級方案）
    enable_gate_counting: bool = True
    gate_line_position_ratio: float = 0.5  # 光柵線在 ROI 中的位置（0.5 = 中心線）
    gate_trigger_radius: int = 20          # 去重半徑（像素）
    gate_history_frames: int = 8           # 觸發歷史保持幀數（280fps下約28ms）


@dataclass
class UIConfig:
    """UI 參數配置（調試面板預設值）"""

    # 📏 面積範圍滑桿
    min_area_range: tuple = (1, 100)      # (最小值, 最大值)
    min_area_default: int = 2
    max_area_range: tuple = (500, 10000)
    max_area_default: int = 3000

    # 🎯 背景減除滑桿
    bg_var_threshold_range: tuple = (1, 20)
    bg_var_threshold_default: int = 3

    # 🎯 虛擬光柵滑桿
    min_track_frames_range: tuple = (3, 15)
    min_track_frames_default: int = 8
    duplicate_distance_range: tuple = (10, 40)
    duplicate_distance_default: int = 20

    # ⚡ 性能優化
    image_scale_options: list = field(default_factory=lambda: ["100% (原始)", "75%", "50%", "30%"])
    image_scale_default: str = "50%"
    skip_frames_range: tuple = (0, 10)
    skip_frames_default: int = 0

    # 📺 原始畫面顯示
    original_display_size: tuple = (360, 270)  # 4:3 比例
    original_display_height: int = 300


@dataclass
class PerformanceConfig:
    """性能優化配置"""

    # 圖像處理優化
    image_scale: float = 0.5        # 圖像縮放比例（0.3-1.0）
    skip_frames: int = 0            # 跳幀數（0=不跳幀）

    # 調試選項
    show_gray: bool = False
    show_binary: bool = False
    show_edges: bool = False
    show_coords: bool = False
    show_timing: bool = True


@dataclass
class DebugConfig:
    """調試配置"""

    # 📸 調試圖片保存
    debug_save_enabled: bool = False
    debug_save_dir: str = "basler_pyqt6/recordings/debug"
    max_debug_frames: int = 100


@dataclass
class PackagingConfig:
    """定量包裝控制配置（工業級震動機控制）"""

    # 🎯 包裝目標參數
    target_count: int = 150                    # 目標數量（顆）
    enable_auto_packaging: bool = False         # 是否啟用自動包裝模式

    # ⚡ 震動機速度控制閾值（百分比）
    speed_full_threshold: float = 0.85         # 全速運轉閾值（< 85% 時全速）
    speed_medium_threshold: float = 0.93       # 中速運轉閾值（85%-93% 時中速）
    speed_slow_threshold: float = 0.97         # 慢速運轉閾值（93%-97% 時慢速）
    # >= 97% 時極慢速，達到目標時停止

    # 🔧 震動機速度設定（百分比，0-100）
    vibrator_speed_full: int = 100             # 全速（100%）
    vibrator_speed_medium: int = 60            # 中速（60%）
    vibrator_speed_slow: int = 30              # 慢速（30%）
    vibrator_speed_creep: int = 10             # 極慢速（10%）

    # ⏱️ 反應時間補償
    stop_delay_frames: int = 10                # 停止延遲補償幀數（震動機慣性）
    advance_stop_count: int = 2                # 提前停止顆數（考慮飛行中零件）

    # 🔊 提示音設定
    enable_sound_alert: bool = True            # 啟用提示音
    alert_on_target_reached: bool = True       # 達到目標時提示
    alert_on_speed_change: bool = False        # 速度變化時提示

    # 📊 統計參數
    enable_batch_tracking: bool = True         # 啟用批次追蹤
    auto_reset_on_complete: bool = False       # 完成後自動重置


@dataclass
class AppConfig:
    """應用程序總配置"""

    detection: DetectionConfig = field(default_factory=DetectionConfig)
    gate: GateConfig = field(default_factory=GateConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)
    packaging: PackagingConfig = field(default_factory=PackagingConfig)

    # 配置檔案路徑
    config_file: Optional[Path] = None

    def __post_init__(self):
        """初始化後處理"""
        if self.config_file is None:
            self.config_file = PROJECT_ROOT / "config" / "detection_params.json"

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'detection': asdict(self.detection),
            'gate': asdict(self.gate),
            'ui': asdict(self.ui),
            'performance': asdict(self.performance),
            'debug': asdict(self.debug),
            'packaging': asdict(self.packaging)
        }

    def save(self, file_path: Optional[Path] = None) -> bool:
        """
        保存配置到 JSON 檔案

        Args:
            file_path: 配置檔案路徑（可選）

        Returns:
            是否保存成功
        """
        target_file = file_path or self.config_file

        try:
            # 確保目錄存在
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # 保存配置
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 配置已保存到: {target_file}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存配置失敗: {str(e)}")
            return False

    @classmethod
    def load(cls, file_path: Optional[Path] = None) -> 'AppConfig':
        """
        從 JSON 檔案載入配置

        Args:
            file_path: 配置檔案路徑（可選）

        Returns:
            AppConfig 實例
        """
        if file_path is None:
            file_path = PROJECT_ROOT / "config" / "detection_params.json"

        try:
            if not file_path.exists():
                logger.warning(f"⚠️ 配置檔案不存在，使用預設配置: {file_path}")
                return cls()

            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 從字典創建配置對象
            config = cls(
                detection=DetectionConfig(**data.get('detection', {})),
                gate=GateConfig(**data.get('gate', {})),
                ui=UIConfig(**data.get('ui', {})),
                performance=PerformanceConfig(**data.get('performance', {})),
                debug=DebugConfig(**data.get('debug', {})),
                packaging=PackagingConfig(**data.get('packaging', {})),
                config_file=file_path
            )

            logger.info(f"✅ 配置已從檔案載入: {file_path}")
            return config

        except Exception as e:
            logger.error(f"❌ 載入配置失敗: {str(e)}，使用預設配置")
            return cls()

    def update_detection_params(self, **kwargs) -> bool:
        """
        更新檢測參數

        Args:
            **kwargs: 要更新的參數

        Returns:
            是否成功
        """
        try:
            for key, value in kwargs.items():
                if hasattr(self.detection, key):
                    setattr(self.detection, key, value)
                    logger.info(f"參數更新: detection.{key} = {value}")
                else:
                    logger.warning(f"未知的檢測參數: {key}")
            return True
        except Exception as e:
            logger.error(f"更新檢測參數失敗: {str(e)}")
            return False

    def update_gate_params(self, **kwargs) -> bool:
        """更新虛擬光柵參數"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.gate, key):
                    setattr(self.gate, key, value)
                    logger.info(f"參數更新: gate.{key} = {value}")
            return True
        except Exception as e:
            logger.error(f"更新光柵參數失敗: {str(e)}")
            return False

    def update_performance_params(self, **kwargs) -> bool:
        """更新性能參數"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.performance, key):
                    setattr(self.performance, key, value)
                    logger.info(f"參數更新: performance.{key} = {value}")
            return True
        except Exception as e:
            logger.error(f"更新性能參數失敗: {str(e)}")
            return False

    def reset_to_default(self):
        """重置為預設配置"""
        self.detection = DetectionConfig()
        self.gate = GateConfig()
        self.ui = UIConfig()
        self.performance = PerformanceConfig()
        self.debug = DebugConfig()
        logger.info("🔄 配置已重置為預設值")


# ==================== 全局配置實例 ====================

_global_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """
    獲取全局配置實例

    Returns:
        AppConfig 實例
    """
    global _global_config
    if _global_config is None:
        _global_config = AppConfig.load()
    return _global_config


def init_config(config_file: Optional[Path] = None) -> AppConfig:
    """
    初始化全局配置

    Args:
        config_file: 配置檔案路徑（可選）

    Returns:
        AppConfig 實例
    """
    global _global_config
    _global_config = AppConfig.load(config_file)
    return _global_config


def save_config() -> bool:
    """保存當前配置到檔案"""
    config = get_config()
    return config.save()


# ==================== 配置驗證 ====================

def validate_config(config: AppConfig) -> bool:
    """
    驗證配置有效性

    Args:
        config: 要驗證的配置

    Returns:
        是否有效
    """
    try:
        # 檢查面積範圍
        if config.detection.min_area >= config.detection.max_area:
            logger.error("❌ 配置錯誤: min_area 必須小於 max_area")
            return False

        # 檢查 ROI 參數
        if not (0.0 <= config.detection.roi_position_ratio <= 1.0):
            logger.error("❌ 配置錯誤: roi_position_ratio 必須在 0.0-1.0 之間")
            return False

        # 檢查光柵參數
        if not (0.0 <= config.gate.gate_line_position_ratio <= 1.0):
            logger.error("❌ 配置錯誤: gate_line_position_ratio 必須在 0.0-1.0 之間")
            return False

        if config.gate.gate_trigger_radius <= 0:
            logger.error("❌ 配置錯誤: gate_trigger_radius 必須大於 0")
            return False

        # 檢查性能參數
        if not (0.1 <= config.performance.image_scale <= 1.0):
            logger.error("❌ 配置錯誤: image_scale 必須在 0.1-1.0 之間")
            return False

        logger.info("✅ 配置驗證通過")
        return True

    except Exception as e:
        logger.error(f"❌ 配置驗證失敗: {str(e)}")
        return False


# ==================== 初始化 ====================

if __name__ == "__main__":
    # 測試配置系統
    print("=" * 60)
    print("🔧 basler_pyqt6 配置系統測試")
    print("=" * 60)

    # 創建預設配置
    config = AppConfig()

    # 驗證配置
    if validate_config(config):
        print("✅ 配置驗證通過")

    # 顯示配置
    print("\n📋 當前配置:")
    print(json.dumps(config.to_dict(), indent=2, ensure_ascii=False))

    # 保存配置
    if config.save():
        print(f"\n✅ 配置已保存到: {config.config_file}")

    # 測試載入
    loaded_config = AppConfig.load(config.config_file)
    print(f"\n✅ 配置已重新載入")

    # 測試參數更新
    loaded_config.update_detection_params(min_area=5, max_area=2500)
    print("\n✅ 參數更新測試完成")

    print("\n" + "=" * 60)
    print("🎉 配置系統測試完成！")
    print("=" * 60)
