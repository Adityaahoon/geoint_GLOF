"""Standalone U-Net / DeepLabV3+ training & evaluation script for glacial lake segmentation.

Usage:
    python backend/scripts/train_unet.py --model unet --epochs 30 --batch-size 4 --lr 1e-3

Enforces geographic longitudinal block splitting to prevent spatial data leakage and refuses
to train unless manually verified binary lake masks exist in
`data/training/lake_segmentation/verified_masks/`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.models import ModelTrainingRun
from app.services import dl_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Train U-Net or DeepLabV3+ on verified glacial lake masks")
    parser.add_argument("--model", choices=["unet", "deeplabv3plus"], default="unet")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    init_db()
    st = dl_service.dataset_status()
    if st["status"] != "ready":
        print(f"[AWAITING TRAINING DATA] Found {st['paired_verified_tiles']} verified mask tiles in {st['directory']}/verified_masks/.")
        for line in st["instructions"]:
            print(" ", line)
        sys.exit(1)

    db = SessionLocal()
    try:
        run = ModelTrainingRun(
            model_type=args.model,
            task="lake_segmentation",
            status="queued",
            hyperparameters={"epochs": args.epochs, "batch_size": args.batch_size, "learning_rate": args.lr},
            history=[],
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        res = dl_service.train_segmentation_model(
            db, run.id, model_type=args.model, epochs=args.epochs,
            batch_size=args.batch_size, learning_rate=args.lr,
            log=lambda m, p=None: print(f"[{(p or 0)*100:5.1f}%] {m}")
        )
        print("Training completed:", res)
    finally:
        db.close()


if __name__ == "__main__":
    main()

