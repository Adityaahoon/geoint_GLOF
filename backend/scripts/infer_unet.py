"""Standalone U-Net / DeepLabV3+ sliding-window inference script for glacial lake detection.

Usage:
    python backend/scripts/infer_unet.py --composite-id 1 --model unet
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db
from app.services import lake_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Run trained U-Net/DeepLabV3+ inference on a satellite composite")
    parser.add_argument("--composite-id", type=int, required=True)
    parser.add_argument("--model", choices=["unet", "deeplabv3plus"], default="unet")
    parser.add_argument("--min-area-ha", type=float, default=0.5)
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        res = lake_service.detect_lakes_on_composite(
            db, composite_id=args.composite_id, method=args.model,
            min_area_ha=args.min_area_ha, log=lambda m, p=None: print(m)
        )
        print("Inference complete:", res)
    finally:
        db.close()


if __name__ == "__main__":
    main()

