"""
卡爾曼濾波器追蹤器 - 用於小零件追蹤優化
基於 SORT (Simple Online and Realtime Tracking) 算法
"""

import numpy as np
from typing import Tuple, Optional


class KalmanBoxTracker:
    """
    使用卡爾曼濾波器追蹤單個物件的狀態

    狀態向量: [x, y, area, aspect_ratio, vx, vy, va]
    - x, y: 中心點座標
    - area: 面積
    - aspect_ratio: 長寬比
    - vx, vy, va: 速度分量
    """

    count = 0  # 追蹤器計數器

    def __init__(self, bbox: Tuple[float, float, float, float], track_id: Optional[int] = None):
        """
        初始化卡爾曼濾波器

        Args:
            bbox: (x, y, w, h) - 物件的邊界框
            track_id: 可選的追蹤 ID
        """
        # 狀態維度: 7 (x, y, area, aspect_ratio, vx, vy, va)
        # 觀測維度: 4 (x, y, area, aspect_ratio)
        from filterpy.kalman import KalmanFilter

        self.kf = KalmanFilter(dim_x=7, dim_z=4)

        # 狀態轉移矩陣 F
        self.kf.F = np.array([
            [1, 0, 0, 0, 1, 0, 0],  # x = x + vx
            [0, 1, 0, 0, 0, 1, 0],  # y = y + vy
            [0, 0, 1, 0, 0, 0, 1],  # area = area + va
            [0, 0, 0, 1, 0, 0, 0],  # aspect_ratio (constant)
            [0, 0, 0, 0, 1, 0, 0],  # vx
            [0, 0, 0, 0, 0, 1, 0],  # vy
            [0, 0, 0, 0, 0, 0, 1],  # va
        ])

        # 觀測矩陣 H
        self.kf.H = np.array([
            [1, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0],
        ])

        # 測量噪聲協方差矩陣 R
        self.kf.R[2:, 2:] *= 10.0  # 面積和長寬比的測量不確定性更高

        # 過程噪聲協方差矩陣 Q
        self.kf.P[4:, 4:] *= 1000.0  # 速度的初始不確定性很高
        self.kf.P *= 10.0

        self.kf.Q[-1, -1] *= 0.01  # 面積變化速度的過程噪聲
        self.kf.Q[4:, 4:] *= 0.01  # 速度的過程噪聲

        # 初始化狀態
        x, y, w, h = bbox
        area = w * h
        aspect_ratio = w / max(h, 1e-6)
        self.kf.x[:4] = [[x], [y], [area], [aspect_ratio]]

        # 追蹤器屬性
        self.id = track_id if track_id is not None else KalmanBoxTracker.count
        KalmanBoxTracker.count += 1

        self.time_since_update = 0
        self.hit_streak = 0
        self.age = 0
        self.history = []

        # 用於計數的屬性
        self.counted = False
        self.first_y = y
        self.max_y = y
        self.min_y = y
        self.positions = [(x, y)]
        self.in_roi_frames = 1

    def update(self, bbox: Tuple[float, float, float, float]):
        """
        使用觀測到的邊界框更新狀態

        Args:
            bbox: (x, y, w, h)
        """
        self.time_since_update = 0
        self.history = []
        self.hit_streak += 1

        x, y, w, h = bbox
        area = w * h
        aspect_ratio = w / max(h, 1e-6)

        # 卡爾曼更新
        self.kf.update([x, y, area, aspect_ratio])

        # 更新追蹤統計
        self.positions.append((x, y))
        if len(self.positions) > 50:  # 保留最近 50 個位置
            self.positions.pop(0)

        self.max_y = max(self.max_y, y)
        self.min_y = min(self.min_y, y)
        self.in_roi_frames += 1

    def predict(self) -> np.ndarray:
        """
        預測下一幀的狀態

        Returns:
            predicted_bbox: [x, y, w, h]
        """
        # 面積變化速度不應該太大
        if (self.kf.x[6] + self.kf.x[2]) <= 0:
            self.kf.x[6] *= 0.0

        # 卡爾曼預測
        self.kf.predict()
        self.age += 1

        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1

        self.history.append(self.get_state())
        return self.history[-1]

    def get_state(self) -> np.ndarray:
        """
        獲取當前狀態的邊界框

        Returns:
            bbox: [x, y, w, h]
        """
        x, y, area, aspect_ratio = self.kf.x[:4].flatten()

        # 從 area 和 aspect_ratio 還原 w, h
        w = np.sqrt(area * aspect_ratio)
        h = area / max(w, 1e-6)

        return np.array([x, y, w, h])

    def get_position(self) -> Tuple[float, float]:
        """獲取當前中心點位置"""
        return (float(self.kf.x[0]), float(self.kf.x[1]))

    def get_velocity(self) -> Tuple[float, float]:
        """獲取當前速度"""
        return (float(self.kf.x[4]), float(self.kf.x[5]))

    def get_y_travel(self) -> float:
        """獲取 Y 軸移動距離"""
        return self.max_y - self.min_y


def iou_batch(bboxes1: np.ndarray, bboxes2: np.ndarray) -> np.ndarray:
    """
    計算兩組邊界框之間的 IOU (Intersection over Union)

    Args:
        bboxes1: (N, 4) - [x, y, w, h]
        bboxes2: (M, 4) - [x, y, w, h]

    Returns:
        iou_matrix: (N, M) - IOU 矩陣
    """
    # 轉換為 [x1, y1, x2, y2] 格式
    bboxes1 = convert_bbox_to_xyxy(bboxes1)
    bboxes2 = convert_bbox_to_xyxy(bboxes2)

    # 計算交集
    xx1 = np.maximum(bboxes1[:, 0:1], bboxes2[:, 0])
    yy1 = np.maximum(bboxes1[:, 1:2], bboxes2[:, 1])
    xx2 = np.minimum(bboxes1[:, 2:3], bboxes2[:, 2])
    yy2 = np.minimum(bboxes1[:, 3:4], bboxes2[:, 3])

    w = np.maximum(0., xx2 - xx1)
    h = np.maximum(0., yy2 - yy1)
    intersection = w * h

    # 計算並集
    area1 = (bboxes1[:, 2] - bboxes1[:, 0]) * (bboxes1[:, 3] - bboxes1[:, 1])
    area2 = (bboxes2[:, 2] - bboxes2[:, 0]) * (bboxes2[:, 3] - bboxes2[:, 1])
    union = area1[:, np.newaxis] + area2 - intersection

    iou = intersection / np.maximum(union, 1e-6)
    return iou


def convert_bbox_to_xyxy(bboxes: np.ndarray) -> np.ndarray:
    """
    轉換邊界框格式：[x, y, w, h] -> [x1, y1, x2, y2]

    Args:
        bboxes: (N, 4) - [x, y, w, h] (中心點 + 寬高)

    Returns:
        bboxes_xyxy: (N, 4) - [x1, y1, x2, y2] (左上角 + 右下角)
    """
    bboxes_xyxy = np.copy(bboxes)
    bboxes_xyxy[:, 0] = bboxes[:, 0] - bboxes[:, 2] / 2  # x1 = x - w/2
    bboxes_xyxy[:, 1] = bboxes[:, 1] - bboxes[:, 3] / 2  # y1 = y - h/2
    bboxes_xyxy[:, 2] = bboxes[:, 0] + bboxes[:, 2] / 2  # x2 = x + w/2
    bboxes_xyxy[:, 3] = bboxes[:, 1] + bboxes[:, 3] / 2  # y2 = y + h/2
    return bboxes_xyxy


def associate_detections_to_trackers(
    detections: np.ndarray,
    trackers: np.ndarray,
    iou_threshold: float = 0.3
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    使用匈牙利算法將檢測結果匹配到追蹤器

    Args:
        detections: (N, 4) - 檢測到的邊界框
        trackers: (M, 4) - 追蹤器預測的邊界框
        iou_threshold: IOU 閾值

    Returns:
        matches: (K, 2) - 匹配對的索引 [[det_idx, trk_idx], ...]
        unmatched_detections: (N-K,) - 未匹配的檢測索引
        unmatched_trackers: (M-K,) - 未匹配的追蹤器索引
    """
    if len(trackers) == 0:
        return (
            np.empty((0, 2), dtype=int),
            np.arange(len(detections)),
            np.empty((0,), dtype=int)
        )

    # 計算 IOU 矩陣
    iou_matrix = iou_batch(detections, trackers)

    # 使用匈牙利算法求解最優匹配
    # cost_matrix = 1 - iou_matrix (轉換為代價矩陣)
    if min(iou_matrix.shape) > 0:
        from scipy.optimize import linear_sum_assignment

        # 匈牙利算法求最小代價
        matched_indices = np.array(linear_sum_assignment(-iou_matrix)).T
    else:
        matched_indices = np.empty((0, 2), dtype=int)

    # 過濾低 IOU 的匹配
    matches = []
    for m in matched_indices:
        if iou_matrix[m[0], m[1]] < iou_threshold:
            continue
        matches.append(m.reshape(1, 2))

    if len(matches) == 0:
        matches = np.empty((0, 2), dtype=int)
    else:
        matches = np.concatenate(matches, axis=0)

    # 找出未匹配的檢測和追蹤器
    unmatched_detections = []
    for d in range(len(detections)):
        if d not in matches[:, 0]:
            unmatched_detections.append(d)

    unmatched_trackers = []
    for t in range(len(trackers)):
        if t not in matches[:, 1]:
            unmatched_trackers.append(t)

    return (
        matches,
        np.array(unmatched_detections),
        np.array(unmatched_trackers)
    )
