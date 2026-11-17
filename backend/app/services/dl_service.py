"""Deep Learning module: Glacial lake semantic segmentation (U-Net & DeepLabV3+ in PyTorch).

Scientific integrity rules:
- Never claims a model is trained or operational unless a real training run has completed
  against verified masks in `data/training/lake_segmentation/verified_masks/`.
- Never fabricates accuracy, IoU, Dice or confusion matrices.
- Splits tiles geographically (west/central/east longitudinal blocks or distinct acquisition
  years) rather than random shuffling of overlapping neighbouring tiles, preventing spatial
  data leakage.
- Provides a tile-preparation tool that cuts 6-band optical composites into 256×256 GeoTIFF
  tiles alongside weak MNDWI pre-labels in `unverified_masks/` so a researcher can inspect
  and promote verified masks in QGIS before launching training.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from ..config import get_settings
from ..models import ModelEvaluation, ModelTrainingRun, RasterAsset

settings = get_settings()
SEG_DIR = settings.training_dir / "lake_segmentation"
IMAGES_DIR = SEG_DIR / "images"
VERIFIED_MASKS_DIR = SEG_DIR / "verified_masks"
UNVERIFIED_MASKS_DIR = SEG_DIR / "unverified_masks"


def torch_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


# ----------------------------------------------------------------------------- Architectures

class _DoubleConv(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        groups = min(8, out_ch)
        self.net = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False),
            nn.GroupNorm(groups, out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False),
            nn.GroupNorm(groups, out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.net(x)


class UNet(nn.Module):
    """6-band optical U-Net (Ronneberger et al., 2015) for glacial lake segmentation."""

    def __init__(self, in_channels: int = 6, base: int = 32):
        super().__init__()
        self.enc1 = _DoubleConv(in_channels, base)
        self.enc2 = _DoubleConv(base, base * 2)
        self.enc3 = _DoubleConv(base * 2, base * 4)
        self.enc4 = _DoubleConv(base * 4, base * 8)
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = _DoubleConv(base * 8, base * 16)
        self.up4 = nn.ConvTranspose2d(base * 16, base * 8, 2, stride=2)
        self.dec4 = _DoubleConv(base * 16, base * 8)
        self.up3 = nn.ConvTranspose2d(base * 8, base * 4, 2, stride=2)
        self.dec3 = _DoubleConv(base * 8, base * 4)
        self.up2 = nn.ConvTranspose2d(base * 4, base * 2, 2, stride=2)
        self.dec2 = _DoubleConv(base * 4, base * 2)
        self.up1 = nn.ConvTranspose2d(base * 2, base, 2, stride=2)
        self.dec1 = _DoubleConv(base * 2, base)
        self.head = nn.Conv2d(base, 1, 1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        b = self.bottleneck(self.pool(e4))
        d4 = self.dec4(torch.cat([self.up4(b), e4], dim=1))
        d3 = self.dec3(torch.cat([self.up3(d4), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.head(d1)


class _ASPP(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        g = min(8, out_ch)
        self.b0 = nn.Sequential(nn.Conv2d(in_ch, out_ch, 1, bias=False), nn.GroupNorm(g, out_ch), nn.ReLU(inplace=True))
        self.b1 = nn.Sequential(nn.Conv2d(in_ch, out_ch, 3, padding=6, dilation=6, bias=False), nn.GroupNorm(g, out_ch), nn.ReLU(inplace=True))
        self.b2 = nn.Sequential(nn.Conv2d(in_ch, out_ch, 3, padding=12, dilation=12, bias=False), nn.GroupNorm(g, out_ch), nn.ReLU(inplace=True))
        self.b3 = nn.Sequential(nn.Conv2d(in_ch, out_ch, 3, padding=18, dilation=18, bias=False), nn.GroupNorm(g, out_ch), nn.ReLU(inplace=True))
        self.project = nn.Sequential(nn.Conv2d(out_ch * 4, out_ch, 1, bias=False), nn.GroupNorm(g, out_ch), nn.ReLU(inplace=True))

    def forward(self, x):
        return self.project(torch.cat([self.b0(x), self.b1(x), self.b2(x), self.b3(x)], dim=1))


class DeepLabV3Plus(nn.Module):
    """Compact 6-band DeepLabV3+ (Chen et al., 2018) with ASPP + low-level skip connection."""

    def __init__(self, in_channels: int = 6, base: int = 32):
        super().__init__()
        self.stem = _DoubleConv(in_channels, base)
        self.low = _DoubleConv(base, base * 2)  # stride 2
        self.mid = _DoubleConv(base * 2, base * 4)  # stride 4
        self.high = _DoubleConv(base * 4, base * 8)  # stride 8
        self.pool = nn.MaxPool2d(2)
        self.aspp = _ASPP(base * 8, base * 4)
        self.low_proj = nn.Sequential(nn.Conv2d(base * 2, base, 1, bias=False), nn.GroupNorm(min(8, base), base), nn.ReLU(inplace=True))
        self.decoder = _DoubleConv(base * 4 + base, base * 2)
        self.head = nn.Conv2d(base * 2, 1, 1)

    def forward(self, x):
        s = self.stem(x)
        low = self.low(self.pool(s))
        mid = self.mid(self.pool(low))
        high = self.high(self.pool(mid))
        a = F.interpolate(self.aspp(high), size=low.shape[-2:], mode="bilinear", align_corners=False)
        d = self.decoder(torch.cat([a, self.low_proj(low)], dim=1))
        return F.interpolate(self.head(d), size=x.shape[-2:], mode="bilinear", align_corners=False)


def build_model(model_type: str = "unet", in_channels: int = 6) -> nn.Module:
    if model_type == "deeplabv3plus":
        return DeepLabV3Plus(in_channels=in_channels)
    return UNet(in_channels=in_channels)


# ----------------------------------------------------------------------------- Dataset & tiling

def dataset_status() -> dict:
    for d in (IMAGES_DIR, VERIFIED_MASKS_DIR, UNVERIFIED_MASKS_DIR):
        d.mkdir(parents=True, exist_ok=True)
    img_tiles = sorted(p.name for p in IMAGES_DIR.glob("*.tif"))
    ver_masks = sorted(p.name for p in VERIFIED_MASKS_DIR.glob("*.tif"))
    unver_masks = sorted(p.name for p in UNVERIFIED_MASKS_DIR.glob("*.tif"))
    paired = sorted(set(img_tiles).intersection(ver_masks))

    splits = _geographic_split(paired)
    ready = len(paired) >= 6 and len(splits["train"]) >= 4 and len(splits["val"]) >= 1 and len(splits["test"]) >= 1
    return {
        "status": "ready" if ready else "awaiting_training_data",
        "image_tiles": len(img_tiles),
        "verified_mask_tiles": len(ver_masks),
        "unverified_prelabel_tiles": len(unver_masks),
        "paired_verified_tiles": len(paired),
        "splits": {k: len(v) for k, v in splits.items()},
        "split_strategy": "Geographic longitudinal block split (West 60% train / Central 20% val / East 20% test) to prevent spatial autocorrelation leakage between adjacent tiles.",
        "directory": str(SEG_DIR),
        "instructions": [
            "1. Click 'Prepare Image Tiles from Composite' below (or run POST /api/models/prepare-tiles) to slice a 6-band satellite composite into 256×256 GeoTIFF tiles in data/training/lake_segmentation/images/ and weak MNDWI pre-labels in unverified_masks/.",
            "2. Inspect and manually verify/correct the binary lake masks (0=background, 1=glacial lake) in QGIS or your GIS editor, then save verified masks with matching filenames into data/training/lake_segmentation/verified_masks/.",
            "3. Once at least 6 verified image-mask pairs exist across the geographic blocks, U-Net and DeepLabV3+ training is unlocked.",
        ],
    }


def _geographic_split(filenames: list[str]) -> dict[str, list[str]]:
    """Split tiles by their UTM easting into non-overlapping West/Central/East blocks,
    stratified by whether a tile contains positive lake pixels so every split has foreground samples."""
    if not filenames:
        return {"train": [], "val": [], "test": []}
    pos_tiles, neg_tiles = [], []
    for fn in filenames:
        p = IMAGES_DIR / fn
        mp = VERIFIED_MASKS_DIR / fn
        try:
            with rasterio.open(p) as src:
                east = float((src.bounds.left + src.bounds.right) / 2.0)
            has_pos = False
            if mp.exists():
                with rasterio.open(mp) as msrc:
                    has_pos = bool((msrc.read(1) > 0).any())
        except Exception:
            east, has_pos = 0.0, False
        (pos_tiles if has_pos else neg_tiles).append((fn, east))

    def _partition(items):
        items.sort(key=lambda x: x[1])
        n = len(items)
        if n == 0:
            return [], [], []
        n_tr = max(1, int(round(n * 0.6)))
        n_va = max(1, int(round(n * 0.2))) if n >= 3 else 0
        return (
            [x[0] for x in items[:n_tr]],
            [x[0] for x in items[n_tr:n_tr + n_va]],
            [x[0] for x in items[n_tr + n_va:]],
        )

    tr_p, va_p, te_p = _partition(pos_tiles)
    tr_n, va_n, te_n = _partition(neg_tiles)
    return {"train": tr_p + tr_n, "val": va_p + va_n, "test": te_p + te_n}


def prepare_tiles_from_composite(db, composite_id: int, tile_size: int = 256, stride: int = 256, log=lambda m, p=None: None) -> dict:
    """Slice a 6-band composite into non-overlapping tile_size×tile_size GeoTIFFs + weak MNDWI pre-labels."""
    from .indices import mndwi
    comp = db.get(RasterAsset, composite_id)
    if comp is None or not Path(comp.path).exists():
        raise ValueError(f"Composite {composite_id} not found")
    for d in (IMAGES_DIR, VERIFIED_MASKS_DIR, UNVERIFIED_MASKS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    written = 0
    with rasterio.open(comp.path) as src:
        for r0 in range(0, src.height - tile_size + 1, stride):
            for c0 in range(0, src.width - tile_size + 1, stride):
                w = Window(c0, r0, tile_size, tile_size)
                data = src.read(indexes=list(range(1, min(7, src.count + 1))), window=w).astype("float32")
                if np.isfinite(data).mean() < 0.7:
                    continue
                t_transform = src.window_transform(w)
                stem = f"comp{comp.id}_y{comp.year or 0}_r{r0:04d}_c{c0:04d}.tif"
                img_path = IMAGES_DIR / stem
                profile = src.profile.copy()
                profile.update(width=tile_size, height=tile_size, count=data.shape[0], transform=t_transform, dtype="float32")
                with rasterio.open(img_path, "w", **profile) as dst:
                    dst.write(np.nan_to_num(data, nan=0.0))

                # Weak pre-label from MNDWI (band 2 = green, band 5 = swir1) stored in unverified_masks/
                if data.shape[0] >= 5:
                    m = mndwi(data[1], data[4])
                    pre = ((m > 0.08) & (data[3] < 0.22)).astype("uint8")
                    m_prof = profile.copy()
                    m_prof.update(count=1, dtype="uint8", nodata=255)
                    with rasterio.open(UNVERIFIED_MASKS_DIR / stem, "w", **m_prof) as mdst:
                        mdst.write(pre[None, ...])
                written += 1

    log(f"Prepared {written} tiles ({tile_size}×{tile_size}) in {IMAGES_DIR}", 1.0)
    return {"composite_id": composite_id, "tiles_written": written, "tile_size": tile_size, "status": dataset_status()}


class _LakeTileDataset(Dataset):
    def __init__(self, filenames: list[str], augment: bool = False):
        self.filenames = filenames
        self.augment = augment

    def __len__(self):
        return len(self.filenames)

    def __getitem__(self, idx: int):
        fn = self.filenames[idx]
        with rasterio.open(IMAGES_DIR / fn) as src:
            img = src.read().astype("float32")  # (C, H, W)
        with rasterio.open(VERIFIED_MASKS_DIR / fn) as msrc:
            mask = (msrc.read(1) > 0).astype("float32")  # (H, W)
        img = np.nan_to_num(img, nan=0.0)
        if self.augment:
            # Random flips & 90° rotations via Albumentations
            import albumentations as A
            aug = A.Compose([A.HorizontalFlip(p=0.5), A.VerticalFlip(p=0.5), A.RandomRotate90(p=0.5)])
            res = aug(image=np.moveaxis(img, 0, -1), mask=mask)
            img = np.moveaxis(res["image"], -1, 0)
            mask = res["mask"]
        return torch.from_numpy(img.copy()), torch.from_numpy(mask[None, ...].copy())


def _bce_dice_loss(logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    pos_weight = torch.tensor([6.0], device=logits.device, dtype=logits.dtype)
    bce = F.binary_cross_entropy_with_logits(logits, targets, pos_weight=pos_weight)
    probs = torch.sigmoid(logits)
    inter = (probs * targets).sum()
    denom = probs.sum() + targets.sum()
    dice = 1.0 - ((2.0 * inter + 1e-4) / (denom + 1e-4))
    return 0.35 * bce + 0.65 * dice


def _compute_metrics_from_counts(tp: int, fp: int, fn: int, tn: int) -> dict:
    eps = 1e-9
    iou = tp / (tp + fp + fn + eps)
    dice = (2 * tp) / (2 * tp + fp + fn + eps)
    precision = tp / (tp + fp + eps)
    recall = tp / (tp + fn + eps)
    f1 = (2 * precision * recall) / (precision + recall + eps)
    acc = (tp + tn) / (tp + tn + fp + fn + eps)
    return {
        "iou": round(float(iou), 4),
        "dice": round(float(dice), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "accuracy": round(float(acc), 4),
    }


def evaluate_model_on_split(model: nn.Module, filenames: list[str], device: str) -> tuple[dict, list[list[int]], float]:
    model.eval()
    ds = _LakeTileDataset(filenames, augment=False)
    loader = DataLoader(ds, batch_size=4, shuffle=False)
    tp = fp = fn = tn = 0
    total_loss = 0.0
    n_batches = 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            logits = model(x)
            total_loss += float(_bce_dice_loss(logits, y).item())
            n_batches += 1
            pred = (torch.sigmoid(logits) >= 0.5).long()
            t = (y >= 0.5).long()
            tp += int(((pred == 1) & (t == 1)).sum().item())
            fp += int(((pred == 1) & (t == 0)).sum().item())
            fn += int(((pred == 0) & (t == 1)).sum().item())
            tn += int(((pred == 0) & (t == 0)).sum().item())
    metrics = _compute_metrics_from_counts(tp, fp, fn, tn)
    cm = [[tn, fp], [fn, tp]]
    return metrics, cm, round(total_loss / max(n_batches, 1), 5)


def train_segmentation_model(
    db,
    run_id: int,
    model_type: str = "unet",
    epochs: int = 25,
    batch_size: int = 4,
    learning_rate: float = 1e-3,
    log=lambda m, p=None: None,
) -> dict:
    status = dataset_status()
    if status["status"] != "ready":
        raise RuntimeError(
            "Cannot start training: verified lake segmentation masks are not yet present in "
            f"{VERIFIED_MASKS_DIR}. Found {status['paired_verified_tiles']} verified pairs (minimum 6 required)."
        )

    paired = sorted(
        set(p.name for p in IMAGES_DIR.glob("*.tif")).intersection(p.name for p in VERIFIED_MASKS_DIR.glob("*.tif"))
    )
    splits = _geographic_split(paired)
    device = torch_device()
    model = build_model(model_type, in_channels=6).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)

    train_loader = DataLoader(_LakeTileDataset(splits["train"], augment=True), batch_size=batch_size, shuffle=True)
    history = []
    best_iou = -1.0
    best_epoch = 0
    ckpt_dir = settings.models_dir / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = ckpt_dir / f"{model_type}_run{run_id}_best.pt"

    run = db.get(ModelTrainingRun, run_id)
    run.status = "running"
    run.dataset_summary = {"splits": {k: len(v) for k, v in splits.items()}, "device": device}
    db.commit()

    for epoch in range(1, epochs + 1):
        model.train()
        tr_loss = 0.0
        nb = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            logits = model(x)
            loss = _bce_dice_loss(logits, y)
            loss.backward()
            opt.step()
            tr_loss += float(loss.item())
            nb += 1
        tr_loss = round(tr_loss / max(nb, 1), 5)
        val_metrics, val_cm, val_loss = evaluate_model_on_split(model, splits["val"], device)
        rec = {
            "epoch": epoch,
            "train_loss": tr_loss,
            "val_loss": val_loss,
            "val_iou": val_metrics["iou"],
            "val_dice": val_metrics["dice"],
        }
        history.append(rec)
        if val_metrics["iou"] > best_iou:
            best_iou = val_metrics["iou"]
            best_epoch = epoch
            torch.save({"model_type": model_type, "state_dict": model.state_dict(), "epoch": epoch, "val_metrics": val_metrics}, ckpt_path)
        run.history = list(history)
        run.best_epoch = best_epoch
        run.checkpoint_path = str(ckpt_path)
        db.commit()
        log(f"Epoch {epoch}/{epochs}: train_loss={tr_loss:.4f} val_loss={val_loss:.4f} val_IoU={val_metrics['iou']:.4f}", epoch / epochs)

    # Final evaluation on validation and held-out geographic test split using best checkpoint
    ckpt = torch.load(ckpt_path, map_location=device)
    model.load_state_dict(ckpt["state_dict"])
    for sp_name in ("val", "test"):
        m, cm, _ = evaluate_model_on_split(model, splits[sp_name], device)
        ev = ModelEvaluation(
            run_id=run.id, split=sp_name, metrics=m, confusion_matrix=cm, sample_count=len(splits[sp_name])
        )
        db.add(ev)
    run.status = "completed"
    run.finished_at = datetime.utcnow()
    db.commit()
    return {"run_id": run.id, "best_epoch": best_epoch, "best_val_iou": best_iou, "checkpoint_path": str(ckpt_path)}


def predict_composite_mask(db, comp: RasterAsset, model_type: str = "unet", tile_size: int = 256, prob_threshold: float = 0.5) -> tuple[np.ndarray, dict]:
    """Run sliding-window inference on a 6-band composite using the latest completed checkpoint."""
    run = (
        db.query(ModelTrainingRun)
        .filter_by(model_type=model_type, status="completed")
        .order_by(ModelTrainingRun.id.desc())
        .first()
    )
    if run is None or not run.checkpoint_path or not Path(run.checkpoint_path).exists():
        raise RuntimeError(
            f"No trained {model_type} checkpoint is available. Model status is 'awaiting_training_data' — "
            f"train {model_type} in Model Lab first or use 'mndwi_otsu' detection."
        )
    device = torch_device()
    model = build_model(model_type, in_channels=6).to(device)
    ckpt = torch.load(run.checkpoint_path, map_location=device)
    model.load_state_dict(ckpt["state_dict"])
    model.eval()

    with rasterio.open(comp.path) as src:
        data = src.read(indexes=list(range(1, 7))).astype("float32")
    _, h, w = data.shape
    prob = np.zeros((h, w), dtype="float32")
    counts = np.zeros((h, w), dtype="float32")
    with torch.no_grad():
        for r0 in range(0, h, tile_size):
            for c0 in range(0, w, tile_size):
                r1, c1 = min(h, r0 + tile_size), min(w, c0 + tile_size)
                patch = np.zeros((6, tile_size, tile_size), dtype="float32")
                sub = np.nan_to_num(data[:, r0:r1, c0:c1], nan=0.0)
                patch[:, : r1 - r0, : c1 - c0] = sub
                x = torch.from_numpy(patch[None, ...]).to(device)
                p = torch.sigmoid(model(x))[0, 0].cpu().numpy()
                prob[r0:r1, c0:c1] += p[: r1 - r0, : c1 - c0]
                counts[r0:r1, c0:c1] += 1.0
    prob /= np.maximum(counts, 1.0)
    return prob >= prob_threshold, {"run_id": run.id, "model_type": model_type, "probability_threshold": prob_threshold}

