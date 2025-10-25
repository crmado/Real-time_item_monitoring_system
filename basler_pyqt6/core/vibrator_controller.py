"""
震動機控制器 - 工業級定量包裝系統
支援多種控制接口（模擬/串口/GPIO/Modbus）
"""

import logging
from enum import Enum
from typing import Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class VibratorSpeed(Enum):
    """震動機速度等級"""
    STOP = 0
    CREEP = 10      # 極慢速（10%）- 精細控制階段
    SLOW = 30       # 慢速（30%）- 接近目標
    MEDIUM = 60     # 中速（60%）- 逼近階段
    FULL = 100      # 全速（100%）- 初始填充

    def __str__(self):
        names = {
            VibratorSpeed.STOP: "停止",
            VibratorSpeed.CREEP: "極慢速",
            VibratorSpeed.SLOW: "慢速",
            VibratorSpeed.MEDIUM: "中速",
            VibratorSpeed.FULL: "全速"
        }
        return names.get(self, "未知")


class VibratorControllerBase:
    """
    震動機控制器基礎類
    定義標準控制接口，可由不同硬體實現繼承
    """

    def __init__(self, name: str = "震動機"):
        """
        初始化震動機控制器

        Args:
            name: 震動機名稱（用於日誌識別）
        """
        self.name = name
        self.current_speed: VibratorSpeed = VibratorSpeed.STOP
        self.is_running: bool = False
        self.total_runtime_seconds: float = 0.0
        self._start_time: Optional[datetime] = None

        # 速度變化回調（可選）
        self.on_speed_changed: Optional[Callable[[VibratorSpeed, VibratorSpeed], None]] = None

        logger.info(f"✅ [{self.name}] 控制器初始化完成")

    def set_speed(self, speed: VibratorSpeed) -> bool:
        """
        設定震動機速度（抽象接口）

        Args:
            speed: 目標速度等級

        Returns:
            是否設定成功
        """
        raise NotImplementedError("子類必須實現 set_speed 方法")

    def start(self) -> bool:
        """啟動震動機"""
        raise NotImplementedError("子類必須實現 start 方法")

    def stop(self) -> bool:
        """停止震動機"""
        raise NotImplementedError("子類必須實現 stop 方法")

    def get_status(self) -> dict:
        """
        獲取當前狀態

        Returns:
            狀態字典，包含：speed, is_running, runtime_seconds
        """
        return {
            'speed': self.current_speed,
            'speed_percent': self.current_speed.value,
            'is_running': self.is_running,
            'runtime_seconds': self.total_runtime_seconds
        }

    def _notify_speed_changed(self, old_speed: VibratorSpeed, new_speed: VibratorSpeed):
        """通知速度變化（觸發回調）"""
        if self.on_speed_changed:
            try:
                self.on_speed_changed(old_speed, new_speed)
            except Exception as e:
                logger.error(f"❌ 速度變化回調失敗: {e}")


class SimulatedVibratorController(VibratorControllerBase):
    """
    模擬震動機控制器
    透過文字日誌輸出模擬實際控制，用於開發測試階段
    """

    def __init__(self, name: str = "模擬震動機"):
        super().__init__(name)
        logger.info(f"🔧 [{self.name}] 運行於模擬模式（文字日誌輸出）")

    def set_speed(self, speed: VibratorSpeed) -> bool:
        """
        設定震動機速度（模擬）

        Args:
            speed: 目標速度等級

        Returns:
            總是返回 True（模擬必定成功）
        """
        old_speed = self.current_speed
        self.current_speed = speed

        # 模擬輸出
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        if speed == VibratorSpeed.STOP:
            logger.info(f"⏹️  [{self.name}] {timestamp} - 速度設定: {old_speed} → {speed} (0%)")
        elif speed == VibratorSpeed.CREEP:
            logger.info(f"🐌 [{self.name}] {timestamp} - 速度設定: {old_speed} → {speed} ({speed.value}%)")
        elif speed == VibratorSpeed.SLOW:
            logger.info(f"🔽 [{self.name}] {timestamp} - 速度設定: {old_speed} → {speed} ({speed.value}%)")
        elif speed == VibratorSpeed.MEDIUM:
            logger.info(f"⚡ [{self.name}] {timestamp} - 速度設定: {old_speed} → {speed} ({speed.value}%)")
        elif speed == VibratorSpeed.FULL:
            logger.info(f"🚀 [{self.name}] {timestamp} - 速度設定: {old_speed} → {speed} ({speed.value}%)")

        # 通知速度變化
        if old_speed != speed:
            self._notify_speed_changed(old_speed, speed)

        return True

    def start(self) -> bool:
        """啟動震動機（模擬）"""
        if not self.is_running:
            self.is_running = True
            self._start_time = datetime.now()
            logger.info(f"▶️  [{self.name}] 已啟動")
            return True
        else:
            logger.warning(f"⚠️  [{self.name}] 已經在運轉中")
            return False

    def stop(self) -> bool:
        """停止震動機（模擬）"""
        if self.is_running:
            self.is_running = False
            if self._start_time:
                elapsed = (datetime.now() - self._start_time).total_seconds()
                self.total_runtime_seconds += elapsed
                self._start_time = None
            self.current_speed = VibratorSpeed.STOP
            logger.info(f"⏹️  [{self.name}] 已停止（累計運轉: {self.total_runtime_seconds:.1f}秒）")
            return True
        else:
            logger.warning(f"⚠️  [{self.name}] 已經是停止狀態")
            return False


class SerialVibratorController(VibratorControllerBase):
    """
    串口震動機控制器（預留接口）
    實際串口控制需要在此實現具體通訊協議
    """

    def __init__(self, port: str, baudrate: int = 9600, name: str = "串口震動機"):
        super().__init__(name)
        self.port = port
        self.baudrate = baudrate
        logger.info(f"🔌 [{self.name}] 配置串口: {port} @ {baudrate} bps")
        logger.warning(f"⚠️  串口控制尚未實現，當前為預留接口")

    def set_speed(self, speed: VibratorSpeed) -> bool:
        """串口速度設定（待實現）"""
        logger.warning(f"⚠️  [{self.name}] 串口控制尚未實現")
        return False

    def start(self) -> bool:
        """串口啟動（待實現）"""
        logger.warning(f"⚠️  [{self.name}] 串口控制尚未實現")
        return False

    def stop(self) -> bool:
        """串口停止（待實現）"""
        logger.warning(f"⚠️  [{self.name}] 串口控制尚未實現")
        return False


class GPIOVibratorController(VibratorControllerBase):
    """
    GPIO 震動機控制器（預留接口）
    適用於 Raspberry Pi 等支援 GPIO 的平台
    """

    def __init__(self, pin: int, use_pwm: bool = True, name: str = "GPIO震動機"):
        super().__init__(name)
        self.pin = pin
        self.use_pwm = use_pwm
        logger.info(f"🔌 [{self.name}] 配置GPIO: Pin {pin}, PWM={'啟用' if use_pwm else '停用'}")
        logger.warning(f"⚠️  GPIO控制尚未實現，當前為預留接口")

    def set_speed(self, speed: VibratorSpeed) -> bool:
        """GPIO 速度設定（待實現）"""
        logger.warning(f"⚠️  [{self.name}] GPIO控制尚未實現")
        return False

    def start(self) -> bool:
        """GPIO 啟動（待實現）"""
        logger.warning(f"⚠️  [{self.name}] GPIO控制尚未實現")
        return False

    def stop(self) -> bool:
        """GPIO 停止（待實現）"""
        logger.warning(f"⚠️  [{self.name}] GPIO控制尚未實現")
        return False


# ==================== 工廠函數 ====================

def create_vibrator_controller(
    controller_type: str = "simulated",
    **kwargs
) -> VibratorControllerBase:
    """
    震動機控制器工廠函數

    Args:
        controller_type: 控制器類型 ("simulated", "serial", "gpio")
        **kwargs: 控制器特定參數

    Returns:
        震動機控制器實例

    Examples:
        # 模擬控制器（開發測試）
        vibrator = create_vibrator_controller("simulated")

        # 串口控制器（實際部署）
        vibrator = create_vibrator_controller("serial", port="/dev/ttyUSB0", baudrate=9600)

        # GPIO控制器（Raspberry Pi）
        vibrator = create_vibrator_controller("gpio", pin=17, use_pwm=True)
    """
    controller_type = controller_type.lower()

    if controller_type == "simulated":
        return SimulatedVibratorController(**kwargs)
    elif controller_type == "serial":
        return SerialVibratorController(**kwargs)
    elif controller_type == "gpio":
        return GPIOVibratorController(**kwargs)
    else:
        logger.error(f"❌ 未知的控制器類型: {controller_type}，使用模擬控制器")
        return SimulatedVibratorController()


# ==================== 雙震動機管理器 ====================

class DualVibratorManager:
    """
    雙震動機統一管理器
    同時控制兩台震動機，提供統一的控制接口
    """

    def __init__(
        self,
        vibrator1: VibratorControllerBase,
        vibrator2: VibratorControllerBase
    ):
        """
        初始化雙震動機管理器

        Args:
            vibrator1: 第一台震動機控制器
            vibrator2: 第二台震動機控制器
        """
        self.vibrator1 = vibrator1
        self.vibrator2 = vibrator2
        logger.info(f"✅ 雙震動機管理器初始化: [{vibrator1.name}] + [{vibrator2.name}]")

    def set_speed(self, speed: VibratorSpeed) -> tuple[bool, bool]:
        """
        同時設定兩台震動機速度

        Args:
            speed: 目標速度等級

        Returns:
            (vibrator1_success, vibrator2_success) 兩台震動機的設定結果
        """
        result1 = self.vibrator1.set_speed(speed)
        result2 = self.vibrator2.set_speed(speed)
        return (result1, result2)

    def start(self) -> tuple[bool, bool]:
        """
        啟動兩台震動機

        Returns:
            (vibrator1_success, vibrator2_success)
        """
        result1 = self.vibrator1.start()
        result2 = self.vibrator2.start()
        logger.info(f"▶️  雙震動機啟動: [{self.vibrator1.name}] {'✅' if result1 else '❌'} | [{self.vibrator2.name}] {'✅' if result2 else '❌'}")
        return (result1, result2)

    def stop(self) -> tuple[bool, bool]:
        """
        停止兩台震動機

        Returns:
            (vibrator1_success, vibrator2_success)
        """
        result1 = self.vibrator1.stop()
        result2 = self.vibrator2.stop()
        logger.info(f"⏹️  雙震動機停止: [{self.vibrator1.name}] {'✅' if result1 else '❌'} | [{self.vibrator2.name}] {'✅' if result2 else '❌'}")
        return (result1, result2)

    @property
    def is_running(self) -> bool:
        """
        檢查震動機是否運行中（任一台運行即為 True）

        Returns:
            True 如果任一震動機在運行中
        """
        return self.vibrator1.is_running or self.vibrator2.is_running

    def get_status(self) -> dict:
        """
        獲取兩台震動機的狀態

        Returns:
            包含兩台震動機狀態的字典
        """
        return {
            'vibrator1': self.vibrator1.get_status(),
            'vibrator2': self.vibrator2.get_status(),
            'is_running': self.is_running  # 添加整體運行狀態
        }

    def set_speed_independent(
        self,
        speed1: VibratorSpeed,
        speed2: VibratorSpeed
    ) -> tuple[bool, bool]:
        """
        獨立設定兩台震動機的速度（進階功能）

        Args:
            speed1: 震動機1的目標速度
            speed2: 震動機2的目標速度

        Returns:
            (vibrator1_success, vibrator2_success)
        """
        result1 = self.vibrator1.set_speed(speed1)
        result2 = self.vibrator2.set_speed(speed2)
        logger.info(f"⚙️  獨立速度設定: [{self.vibrator1.name}] {speed1} | [{self.vibrator2.name}] {speed2}")
        return (result1, result2)


def create_dual_vibrator_manager(
    controller_type: str = "simulated",
    name1: str = "震動機A",
    name2: str = "震動機B",
    **kwargs
) -> DualVibratorManager:
    """
    創建雙震動機管理器（工廠函數）

    Args:
        controller_type: 控制器類型
        name1: 第一台震動機名稱
        name2: 第二台震動機名稱
        **kwargs: 控制器特定參數

    Returns:
        雙震動機管理器實例

    Examples:
        # 創建兩台模擬震動機
        manager = create_dual_vibrator_manager("simulated", "震動機A", "震動機B")

        # 創建兩台串口震動機
        manager = create_dual_vibrator_manager(
            "serial",
            name1="震動機A",
            name2="震動機B",
            port1="/dev/ttyUSB0",
            port2="/dev/ttyUSB1"
        )
    """
    # 創建第一台震動機
    vibrator1_kwargs = {k.replace('1', ''): v for k, v in kwargs.items() if '1' in k}
    vibrator1_kwargs['name'] = name1
    vibrator1 = create_vibrator_controller(controller_type, **vibrator1_kwargs)

    # 創建第二台震動機
    vibrator2_kwargs = {k.replace('2', ''): v for k, v in kwargs.items() if '2' in k}
    vibrator2_kwargs['name'] = name2
    vibrator2 = create_vibrator_controller(controller_type, **vibrator2_kwargs)

    return DualVibratorManager(vibrator1, vibrator2)
