#!/usr/bin/env python3
"""
使用 ultralytics YOLOv8-nano 訓練小零件偵測模型。

前置需求:
    1. 使用 extract_frames.py 提取訓練幀
    2. 使用標註工具（labelImg / CVAT / Roboflow）標註物件
    3. 組織資料集為 YOLO 格式：
       dataset/
       ├── images/
       │   ├── train/   (80% 的標註圖片)
       │   └── val/     (20% 的標註圖片)
       └── labels/
           ├── train/   (對應的 .txt 標註檔)
           └── val/

使用方式:
    python train_yolo.py --data ./dataset --epochs 100
    python train_yolo.py --data ./dataset --epochs 200 --batch 16 --imgsz 640
"""

import argparse
import yaml
from pathlib import Path
from ultralytics import YOLO


def create_data_yaml(dataset_dir: str, output_path: str = None) -> str:
    """
    自動生成 data.yaml 設定檔。

    Args:
        dataset_dir: 資料集根目錄
        output_path: 輸出 yaml 路徑（預設在 dataset_dir 下）
    Returns:
        yaml 檔案路徑
    """
    dataset_path = Path(dataset_dir).resolve()

    if output_path is None:
        output_path = str(dataset_path / "data.yaml")

    data_config = {
        "path": str(dataset_path),
        "train": "images/train",
        "val": "images/val",
        "nc": 1,  # 單類別
        "names": ["small_part"],
    }

    with open(output_path, "w") as f:
        yaml.dump(data_config, f, default_flow_style=False)

    print(f"[INFO] data.yaml 已生成: {output_path}")
    return output_path


def train(
    dataset_dir: str,
    epochs: int = 100,
    batch_size: int = 16,
    img_size: int = 640,
    model_size: str = "n",
    device: str = "",
    project: str = "runs/train",
    name: str = "small_part",
):
    """
    訓練 YOLOv8 模型。

    Args:
        dataset_dir: 資料集目錄
        epochs: 訓練輪數
        batch_size: 批次大小
        img_size: 輸入圖片尺寸
        model_size: 模型大小 (n/s/m/l/x)
        device: 訓練裝置 ('', '0', 'cpu')
        project: 輸出專案目錄
        name: 實驗名稱
    """
    # 生成 data.yaml
    data_yaml = create_data_yaml(dataset_dir)

    # 載入預訓練模型
    model_name = f"yolov8{model_size}.pt"
    print(f"\n[INFO] 使用預訓練模型: {model_name}")
    model = YOLO(model_name)

    # 訓練
    print(f"[INFO] 開始訓練: epochs={epochs}, batch={batch_size}, imgsz={img_size}")
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch_size,
        imgsz=img_size,
        device=device,
        project=project,
        name=name,
        # 資料增強（針對小零件優化）
        hsv_h=0.015,  # 色調變化
        hsv_s=0.7,  # 飽和度變化
        hsv_v=0.4,  # 亮度變化
        degrees=180.0,  # 旋轉角度（零件方向任意）
        translate=0.1,  # 平移
        scale=0.5,  # 縮放
        fliplr=0.5,  # 水平翻轉
        flipud=0.5,  # 垂直翻轉（零件無固定方向）
        mosaic=1.0,  # Mosaic 增強
        mixup=0.1,  # MixUp 增強
        # 訓練策略
        patience=20,  # 早停耐心值
        optimizer="AdamW",
        lr0=0.01,
        lrf=0.01,
        warmup_epochs=3,
        # 輸出
        save=True,
        save_period=10,
        plots=True,
        verbose=True,
    )

    # 輸出最佳模型路徑
    best_model = Path(project) / name / "weights" / "best.pt"
    if best_model.exists():
        print(f"\n[SUCCESS] 最佳模型: {best_model}")
        print(f"[NEXT] 匯出 ONNX: python export_onnx.py --model {best_model}")
    else:
        print(f"\n[WARNING] 未找到最佳模型，請檢查訓練結果: {project}/{name}/")

    return results


def main():
    parser = argparse.ArgumentParser(description="訓練 YOLOv8 小零件偵測模型")
    parser.add_argument("--data", "-d", required=True, help="資料集目錄")
    parser.add_argument("--epochs", type=int, default=100, help="訓練輪數")
    parser.add_argument("--batch", type=int, default=16, help="批次大小")
    parser.add_argument("--imgsz", type=int, default=640, help="輸入圖片尺寸")
    parser.add_argument(
        "--model", default="n", choices=["n", "s", "m", "l", "x"], help="模型大小"
    )
    parser.add_argument("--device", default="", help="訓練裝置 (空=自動, 0=GPU, cpu)")
    parser.add_argument("--project", default="runs/train", help="輸出目錄")
    parser.add_argument("--name", default="small_part", help="實驗名稱")

    args = parser.parse_args()

    train(
        dataset_dir=args.data,
        epochs=args.epochs,
        batch_size=args.batch,
        img_size=args.imgsz,
        model_size=args.model,
        device=args.device,
        project=args.project,
        name=args.name,
    )


if __name__ == "__main__":
    main()
