#!/usr/bin/env python3
"""
從測試影片提取 ROI 區域幀，用於 YOLO 訓練資料準備。

功能：
- 從影片中每 N 幀提取 ROI 區域圖片
- 支援 ROI 裁切 + 放大（匹配 C++ 推理前處理）
- 用幀差法跳過空白幀（無物件的幀不提取）

使用方式:
    python extract_frames.py --video path/to/video.mp4 --output ./frames
    python extract_frames.py --video path/to/video.mp4 --output ./frames --roi-y 0.12 --roi-h 120 --upscale 2.0
"""

import argparse
import cv2
import numpy as np
from pathlib import Path


def extract_frames(
    video_path: str,
    output_dir: str,
    every_n: int = 5,
    roi_position_ratio: float = 0.12,
    roi_height: int = 120,
    upscale_factor: float = 2.0,
    diff_threshold: float = 5.0,
    min_diff_area: float = 0.001,
):
    """
    從影片提取含物件的 ROI 幀。

    Args:
        video_path: 影片路徑
        output_dir: 輸出目錄
        every_n: 每 N 幀提取一次
        roi_position_ratio: ROI Y 位置比例（相對於影片高度）
        roi_height: ROI 高度（像素）
        upscale_factor: ROI 放大倍數
        diff_threshold: 幀差閾值（跳過空白幀）
        min_diff_area: 最小差異面積比例
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[ERROR] 無法開啟影片: {video_path}")
        return

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    roi_y = int(frame_h * roi_position_ratio)
    roi_h = min(roi_height, frame_h - roi_y)

    print(f"影片: {video_path}")
    print(f"總幀數: {total_frames}, 尺寸: {frame_w}x{frame_h}")
    print(f"ROI: y={roi_y}, h={roi_h}, 放大: {upscale_factor}x")
    print(f"每 {every_n} 幀提取一次")

    prev_roi = None
    extracted = 0
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1

        if frame_idx % every_n != 0:
            continue

        # 裁切 ROI
        roi = frame[roi_y : roi_y + roi_h, 0:frame_w]

        # 幀差法跳過空白幀
        if prev_roi is not None:
            diff = cv2.absdiff(
                cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(prev_roi, cv2.COLOR_BGR2GRAY),
            )
            _, diff_mask = cv2.threshold(diff, diff_threshold, 255, cv2.THRESH_BINARY)
            diff_ratio = np.count_nonzero(diff_mask) / diff_mask.size

            if diff_ratio < min_diff_area:
                prev_roi = roi.copy()
                continue

        prev_roi = roi.copy()

        # ROI 放大（匹配 C++ 推理前處理）
        if upscale_factor > 1.0:
            roi_upscaled = cv2.resize(
                roi,
                None,
                fx=upscale_factor,
                fy=upscale_factor,
                interpolation=cv2.INTER_LINEAR,
            )
        else:
            roi_upscaled = roi

        # 儲存
        filename = out_path / f"frame_{frame_idx:06d}.jpg"
        cv2.imwrite(str(filename), roi_upscaled)
        extracted += 1

        if extracted % 50 == 0:
            print(f"  已提取 {extracted} 幀 (frame {frame_idx}/{total_frames})")

    cap.release()
    print(f"\n完成! 共提取 {extracted} 幀到 {output_dir}")
    print(f"下一步: 使用標註工具（如 labelImg、CVAT）標註物件")


def main():
    parser = argparse.ArgumentParser(description="從測試影片提取 ROI 幀用於 YOLO 訓練")
    parser.add_argument("--video", "-v", required=True, help="輸入影片路徑")
    parser.add_argument("--output", "-o", default="./frames", help="輸出目錄")
    parser.add_argument("--every-n", type=int, default=5, help="每 N 幀提取一次")
    parser.add_argument(
        "--roi-y", type=float, default=0.12, help="ROI Y 位置比例 (0~1)"
    )
    parser.add_argument("--roi-h", type=int, default=120, help="ROI 高度 (像素)")
    parser.add_argument("--upscale", type=float, default=2.0, help="ROI 放大倍數")
    parser.add_argument(
        "--diff-threshold", type=float, default=5.0, help="幀差閾值 (跳過空白幀)"
    )

    args = parser.parse_args()

    extract_frames(
        video_path=args.video,
        output_dir=args.output,
        every_n=args.every_n,
        roi_position_ratio=args.roi_y,
        roi_height=args.roi_h,
        upscale_factor=args.upscale,
        diff_threshold=args.diff_threshold,
    )


if __name__ == "__main__":
    main()
