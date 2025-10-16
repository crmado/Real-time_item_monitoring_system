"""
檢測方法基礎架構
定義不同檢測意圖的抽象介面和具體實作
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple, Optional
from enum import Enum
import numpy as np


class DetectionIntent(Enum):
    """檢測意圖枚舉"""
    COUNTING = "counting"                    # 計數（定量包裝）
    DEFECT_DETECTION = "defect_detection"    # 瑕疵檢測（品質控制）
    SIZE_MEASUREMENT = "size_measurement"    # 尺寸測量（規格檢驗）
    CLASSIFICATION = "classification"        # 分類識別（多種類分揀）


class DetectionMethodBase(ABC):
    """
    檢測方法抽象基類

    所有檢測方法都必須實作此介面
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化檢測方法

        Args:
            config: 檢測方法的配置字典
        """
        self.config = config
        self.enabled = False
        self.method_id = config.get("method_id", "unknown")
        self.method_name = config.get("method_name", "Unknown Method")
        self.intent = config.get("intent", DetectionIntent.COUNTING)

    @abstractmethod
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        處理單幀影像

        Args:
            frame: 輸入影像（BGR 格式）

        Returns:
            Tuple[處理後的影像, 檢測結果字典]

        結果字典格式（依意圖不同而異）：
        - COUNTING: {"count": int, "crossing_count": int, "objects": List[Dict]}
        - DEFECT_DETECTION: {"defects": List[Dict], "is_defective": bool, "defect_types": List[str]}
        - SIZE_MEASUREMENT: {"measurements": Dict[str, float], "in_spec": bool}
        """
        pass

    @abstractmethod
    def enable(self):
        """啟用檢測"""
        self.enabled = True

    @abstractmethod
    def disable(self):
        """禁用檢測"""
        self.enabled = False

    @abstractmethod
    def reset(self):
        """重置檢測狀態（清除累計數據）"""
        pass

    @abstractmethod
    def get_results(self) -> Dict[str, Any]:
        """
        獲取當前檢測結果摘要

        Returns:
            檢測結果字典
        """
        pass

    @abstractmethod
    def update_config(self, **kwargs):
        """
        更新配置參數

        Args:
            **kwargs: 要更新的參數
        """
        pass

    def get_intent(self) -> DetectionIntent:
        """獲取檢測意圖"""
        return self.intent

    def get_method_info(self) -> Dict[str, str]:
        """獲取方法資訊"""
        return {
            "method_id": self.method_id,
            "method_name": self.method_name,
            "intent": self.intent.value
        }


class CountingMethod(DetectionMethodBase):
    """
    計數檢測方法

    使用背景減除 + 虛擬光柵實現高速計數
    適用於：定量包裝、流量統計
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化計數方法

        Args:
            config: 計數方法配置，包含：
                - detection_params: DetectionConfig 參數
                - gate_params: GateConfig 參數
                - packaging_params: PackagingConfig 參數（可選）
        """
        super().__init__(config)
        self.intent = DetectionIntent.COUNTING

        # 從配置提取參數
        det_params = config.get("detection_params", {})
        gate_params = config.get("gate_params", {})

        # === 檢測參數 ===
        self.min_area = det_params.get("min_area", 2)
        self.max_area = det_params.get("max_area", 3000)
        self.bg_var_threshold = det_params.get("bg_var_threshold", 3)
        self.bg_learning_rate = det_params.get("bg_learning_rate", 0.001)
        self.bg_history = det_params.get("bg_history", 1000)

        # === 虛擬光柵參數 ===
        self.gate_trigger_radius = gate_params.get("gate_trigger_radius", 20)
        self.gate_history_frames = gate_params.get("gate_history_frames", 8)
        self.gate_line_position_ratio = gate_params.get("gate_line_position_ratio", 0.5)

        # === ROI 參數 ===
        self.roi_enabled = det_params.get("roi_enabled", True)
        self.roi_height = det_params.get("roi_height", 150)
        self.roi_position_ratio = det_params.get("roi_position_ratio", 0.10)

        # === 檢測狀態 ===
        self.crossing_count = 0           # 穿越光柵的累計計數
        self.detected_objects = []        # 當前幀檢測到的物件
        self.gate_history = []            # 光柵觸發歷史

        # === 背景減除器 ===
        self.bg_subtractor = None
        self._init_background_subtractor()

    def _init_background_subtractor(self):
        """初始化背景減除器"""
        import cv2
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=self.bg_history,
            varThreshold=self.bg_var_threshold,
            detectShadows=False
        )

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        處理單幀影像（計數檢測）

        Args:
            frame: 輸入影像

        Returns:
            (標註後的影像, 檢測結果)
        """
        if not self.enabled:
            return frame, {"count": 0, "crossing_count": self.crossing_count, "objects": []}

        import cv2

        # 獲取影像尺寸
        frame_h, frame_w = frame.shape[:2]

        # === 1. ROI 提取 ===
        if self.roi_enabled:
            roi_y = int(frame_h * self.roi_position_ratio)
            roi_h = self.roi_height
            roi = frame[roi_y:roi_y + roi_h, :]

            # 計算虛擬光柵線位置（在 ROI 內）
            gate_y_in_roi = int(roi_h * self.gate_line_position_ratio)
            gate_y_global = roi_y + gate_y_in_roi
        else:
            roi = frame
            roi_y = 0
            roi_h = frame_h
            gate_y_global = int(frame_h * 0.5)

        # === 2. 背景減除 ===
        fg_mask = self.bg_subtractor.apply(roi, learningRate=self.bg_learning_rate)

        # === 3. 連通組件分析 ===
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            fg_mask, connectivity=4
        )

        # === 4. 過濾物件 ===
        self.detected_objects = []
        for i in range(1, num_labels):  # 跳過背景（label 0）
            area = stats[i, cv2.CC_STAT_AREA]

            if self.min_area <= area <= self.max_area:
                x = stats[i, cv2.CC_STAT_LEFT]
                y = stats[i, cv2.CC_STAT_TOP] + roi_y  # 轉換到全局座標
                w = stats[i, cv2.CC_STAT_WIDTH]
                h = stats[i, cv2.CC_STAT_HEIGHT]
                cx, cy = centroids[i][0], centroids[i][1] + roi_y

                self.detected_objects.append({
                    "bbox": (x, y, w, h),
                    "centroid": (cx, cy),
                    "area": area
                })

        # === 5. 虛擬光柵計數 ===
        new_crossings = 0
        for obj in self.detected_objects:
            cx, cy = obj["centroid"]

            # 檢查物件是否在光柵線附近
            if abs(cy - gate_y_global) < self.gate_trigger_radius:
                # 檢查去重歷史
                is_duplicate = False
                for hist_pos, hist_frame in self.gate_history:
                    hx, hy = hist_pos
                    distance = ((cx - hx)**2 + (cy - hy)**2) ** 0.5
                    if distance < self.gate_trigger_radius:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    # 新物件穿越光柵
                    self.gate_history.append(((cx, cy), 0))
                    new_crossings += 1

        # 更新累計計數
        self.crossing_count += new_crossings

        # 更新光柵歷史（遞增幀數，移除過期記錄）
        self.gate_history = [
            (pos, frames + 1)
            for pos, frames in self.gate_history
            if frames + 1 < self.gate_history_frames
        ]

        # === 6. 繪製標註 ===
        result_frame = frame.copy()

        # 繪製 ROI 區域
        if self.roi_enabled:
            cv2.rectangle(result_frame,
                         (0, roi_y), (frame_w, roi_y + roi_h),
                         (0, 255, 255), 2)

        # 繪製虛擬光柵線
        cv2.line(result_frame,
                (0, gate_y_global), (frame_w, gate_y_global),
                (0, 255, 0), 2)

        # 繪製檢測框
        for obj in self.detected_objects:
            x, y, w, h = obj["bbox"]
            cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # 繪製計數資訊
        cv2.putText(result_frame,
                   f"Count: {len(self.detected_objects)} | Total: {self.crossing_count}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        # === 7. 返回結果 ===
        return result_frame, {
            "count": len(self.detected_objects),
            "crossing_count": self.crossing_count,
            "objects": self.detected_objects,
            "new_crossings": new_crossings
        }

    def enable(self):
        """啟用計數檢測"""
        self.enabled = True

    def disable(self):
        """禁用計數檢測"""
        self.enabled = False

    def reset(self):
        """重置計數器"""
        self.crossing_count = 0
        self.detected_objects = []
        self.gate_history = []
        self._init_background_subtractor()

    def get_results(self) -> Dict[str, Any]:
        """獲取當前計數結果"""
        return {
            "crossing_count": self.crossing_count,
            "current_count": len(self.detected_objects),
            "gate_history_size": len(self.gate_history)
        }

    def update_config(self, **kwargs):
        """更新配置參數"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # 如果背景減除參數變更，重新初始化
        if any(k in kwargs for k in ["bg_history", "bg_var_threshold"]):
            self._init_background_subtractor()


class DefectDetectionMethod(DetectionMethodBase):
    """
    瑕疵檢測方法（框架）

    使用邊緣檢測 + 特徵分析實現表面瑕疵檢測
    適用於：品質控制、NG 品篩選

    注意：此為框架實作，具體演算法需根據實際需求開發
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.intent = DetectionIntent.DEFECT_DETECTION

        # TODO: 添加瑕疵檢測特定參數
        self.defect_threshold = config.get("defect_threshold", 0.5)
        self.defect_types = config.get("defect_types", ["scratch", "dent", "discoloration"])

        # 檢測狀態
        self.total_inspected = 0
        self.defective_count = 0
        self.defect_history = []

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        處理單幀影像（瑕疵檢測）

        TODO: 實作瑕疵檢測演算法
        """
        if not self.enabled:
            return frame, {"defects": [], "is_defective": False}

        # 框架實作：返回空結果
        result_frame = frame.copy()

        # TODO: 實作瑕疵檢測邏輯
        # 1. 影像預處理
        # 2. 特徵提取
        # 3. 瑕疵判定
        # 4. 結果標註

        return result_frame, {
            "defects": [],
            "is_defective": False,
            "defect_types": [],
            "confidence": 0.0
        }

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def reset(self):
        self.total_inspected = 0
        self.defective_count = 0
        self.defect_history = []

    def get_results(self) -> Dict[str, Any]:
        return {
            "total_inspected": self.total_inspected,
            "defective_count": self.defective_count,
            "defect_rate": self.defective_count / max(1, self.total_inspected)
        }

    def update_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


# 檢測方法工廠
def create_detection_method(method_id: str, config: Dict[str, Any]) -> DetectionMethodBase:
    """
    檢測方法工廠函數

    Args:
        method_id: 方法 ID
        config: 方法配置

    Returns:
        DetectionMethodBase 實例
    """
    method_registry = {
        "counting": CountingMethod,
        "defect_detection": DefectDetectionMethod,
    }

    method_class = method_registry.get(method_id)
    if method_class is None:
        raise ValueError(f"Unknown detection method: {method_id}")

    return method_class(config)
