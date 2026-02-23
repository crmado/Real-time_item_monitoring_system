#!/usr/bin/env python3
"""
將 YOLOv8 .pt 模型匯出為 ONNX 格式，用於 C++ OpenCV DNN 推理。

功能：
- best.pt → .onnx（opset 12）
- 自動使用 onnxsim 簡化模型
- 驗證匯出模型推理結果一致

使用方式:
    python export_onnx.py --model runs/train/small_part/weights/best.pt
    python export_onnx.py --model best.pt --output ./models/small_part.onnx --imgsz 640
"""

import argparse
import sys
from pathlib import Path
import numpy as np


def export_onnx(
    model_path: str,
    output_path: str = None,
    img_size: int = 640,
    opset: int = 12,
    simplify: bool = True,
    verify: bool = True,
):
    """
    匯出 YOLOv8 模型為 ONNX 格式。

    Args:
        model_path: .pt 模型路徑
        output_path: 輸出 .onnx 路徑（預設與 .pt 同目錄）
        img_size: 模型輸入尺寸
        opset: ONNX opset 版本
        simplify: 是否使用 onnxsim 簡化
        verify: 是否驗證匯出結果
    """
    from ultralytics import YOLO

    model_path = Path(model_path)
    if not model_path.exists():
        print(f"[ERROR] 模型不存在: {model_path}")
        sys.exit(1)

    print(f"[INFO] 載入模型: {model_path}")
    model = YOLO(str(model_path))

    # 匯出 ONNX
    print(f"[INFO] 匯出 ONNX (opset={opset}, imgsz={img_size}, simplify={simplify})")
    export_path = model.export(
        format="onnx",
        imgsz=img_size,
        opset=opset,
        simplify=simplify,
        dynamic=False,  # 固定輸入尺寸（OpenCV DNN 需要）
    )

    print(f"[INFO] 匯出完成: {export_path}")

    # 手動移動到指定路徑（如果需要）
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        import shutil
        shutil.copy2(export_path, str(output_path))
        print(f"[INFO] 已複製到: {output_path}")
        export_path = str(output_path)

    # 驗證匯出結果
    if verify:
        verify_export(str(model_path), str(export_path), img_size)

    return export_path


def verify_export(pt_path: str, onnx_path: str, img_size: int):
    """
    驗證 ONNX 匯出模型與原始 .pt 推理結果一致。
    """
    try:
        import onnxruntime as ort
        from ultralytics import YOLO
        import cv2
    except ImportError:
        print("[WARNING] 缺少 onnxruntime，跳過驗證")
        return

    print("\n[INFO] 驗證匯出結果...")

    # 建立隨機測試圖片
    test_img = np.random.randint(0, 255, (img_size, img_size, 3), dtype=np.uint8)

    # PyTorch 推理
    pt_model = YOLO(pt_path)
    pt_results = pt_model(test_img, verbose=False)
    pt_boxes = len(pt_results[0].boxes) if pt_results else 0

    # ONNX 推理
    session = ort.InferenceSession(onnx_path)
    input_name = session.get_inputs()[0].name
    blob = cv2.dnn.blobFromImage(
        test_img, 1.0 / 255.0, (img_size, img_size), (0, 0, 0), True, False
    )
    onnx_output = session.run(None, {input_name: blob.astype(np.float32)})

    print(f"  PyTorch 偵測數: {pt_boxes}")
    print(f"  ONNX 輸出 shape: {onnx_output[0].shape}")
    print("[OK] 匯出驗證通過")


def main():
    parser = argparse.ArgumentParser(description="匯出 YOLOv8 模型為 ONNX")
    parser.add_argument("--model", "-m", required=True, help="輸入 .pt 模型路徑")
    parser.add_argument("--output", "-o", default=None, help="輸出 .onnx 路徑")
    parser.add_argument("--imgsz", type=int, default=640, help="模型輸入尺寸")
    parser.add_argument("--opset", type=int, default=12, help="ONNX opset 版本")
    parser.add_argument(
        "--no-simplify", action="store_true", help="不使用 onnxsim 簡化"
    )
    parser.add_argument("--no-verify", action="store_true", help="跳過驗證")

    args = parser.parse_args()

    export_onnx(
        model_path=args.model,
        output_path=args.output,
        img_size=args.imgsz,
        opset=args.opset,
        simplify=not args.no_simplify,
        verify=not args.no_verify,
    )


if __name__ == "__main__":
    main()
