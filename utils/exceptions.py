"""
例外處理模組
定義系統專用的例外類別
"""


class ObjectDetectionError(Exception):
    """物件偵測系統基礎例外類別"""
    pass


class CameraError(ObjectDetectionError):
    """相機相關例外類別"""

    def __init__(self, message, camera_id=None):
        self.camera_id = camera_id
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        if self.camera_id is not None:
            return f"相機錯誤 (ID: {self.camera_id}): {self.message}"
        return f"相機錯誤: {self.message}"


class CameraOpenError(CameraError):
    """無法開啟相機的例外"""
    pass


class CameraNotFoundError(CameraError):
    """找不到相機的例外"""
    pass


class CameraDisconnectedError(CameraError):
    """相機連線中斷的例外"""
    pass


class ImageProcessingError(ObjectDetectionError):
    """影像處理相關例外類別"""

    def __init__(self, message, frame_id=None):
        self.frame_id = frame_id
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        if self.frame_id is not None:
            return f"影像處理錯誤 (幀: {self.frame_id}): {self.message}"
        return f"影像處理錯誤: {self.message}"


class ObjectTrackingError(ObjectDetectionError):
    """物件追蹤相關例外類別"""
    pass


class ConfigError(ObjectDetectionError):
    """配置相關例外類別"""

    def __init__(self, message, config_key=None):
        self.config_key = config_key
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        if self.config_key is not None:
            return f"配置錯誤 (鍵: {self.config_key}): {self.message}"
        return f"配置錯誤: {self.message}"


class InvalidSettingError(ConfigError):
    """無效設定值的例外"""
    pass