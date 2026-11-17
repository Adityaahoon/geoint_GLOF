# GlacioGuard AI — Deep Learning & Machine Learning Evaluation Documentation

## 1. Glacial Lake Semantic Segmentation (`app/services/dl_service.py`)

### Architectures Implemented
1. **6-Band U-Net (Primary):** Encoder–decoder architecture (Ronneberger et al., 2015) ingesting 6 harmonised optical surface-reflectance bands (`blue, green, red, nir, swir1, swir2`) at $256\times 256$ spatial resolution with 4 downsampling stages (`32 → 64 → 128 → 256 → 512` channels), BatchNorm + ReLU double convolutions, transposed-convolution upsampling, and skip connections.
2. **6-Band DeepLabV3+ (Comparison Model):** Encoder with Atrous Spatial Pyramid Pooling (ASPP dilation rates `1, 6, 12, 18`) and low-level feature fusion decoder (Chen et al., 2018).

### Preventing Spatial & Temporal Data Leakage
Randomly splitting overlapping or adjacent image tiles from the same scene leaks local background texture and illumination into the test set, artificially inflating IoU and Dice scores. GlacioGuard AI enforces a **Geographic Longitudinal Block Split** (`_geographic_split` in `dl_service.py`):
- Tiles are sorted by their UTM Zone 44N Easting centroid and partitioned into three non-overlapping geographic blocks:
  - **West Block (60%):** Training set (augmented with random horizontal/vertical flips and $90^\circ$ rotations via Albumentations).
  - **Central Block (20%):** Validation set (used for checkpoint selection).
  - **East Block (20%):** Held-out test set.

### Loss Function & Evaluation Metrics
- **Loss:** $0.5 \times \text{BCEWithLogitsLoss} + 0.5 \times \text{SoftDiceLoss}$, balancing pixel-wise cross-entropy with class-imbalance-resilient overlap optimization.
- **Metrics Computed on Held-Out Validation & Test Splits:**
  - Intersection over Union ($\text{IoU} = \frac{TP}{TP + FP + FN}$)
  - Dice Coefficient ($\text{Dice} = \frac{2TP}{2TP + FP + FN}$)
  - Precision ($\frac{TP}{TP + FP}$), Recall ($\frac{TP}{TP + FN}$), F1-Score, Overall Pixel Accuracy, and full $2\times 2$ Confusion Matrix $\begin{bmatrix} TN & FP \\ FN & TP \end{bmatrix}$.

### Honest Operational Status Policy
- Until manually verified binary lake masks (`0` = background, `1` = glacial lake) are placed in `data/training/lake_segmentation/verified_masks/` and a training job completes, the segmentation model reports `status: "awaiting_training_data"`.
- No synthetic or fabricated accuracy numbers are ever displayed.

## 2. GLOF Susceptibility Assessment (`app/services/glof_service.py`)

### Preliminary Multi-Criteria Screening (`mcda_screening_v1`)
When a labelled regional historical GLOF training table is unavailable, GlacioGuard AI executes a transparent, literature-weighted multi-criteria screening framework grounded in GAPHAZ (2017), Huggel et al. (2002), Worni et al. (2013), and Allen et al. (2019):
- Evaluates 9 physical criteria: lake surface area (0.12), multi-temporal expansion rate (0.16), glacier proximity (0.16), steep ($30^\circ\text{–}60^\circ$) upslope avalanche source area within 1 km (0.18), surrounding 90th-percentile terrain slope (0.10), downstream outlet channel gradient (0.12), D8 stream connectivity (0.06), lake elevation (0.05), and moraine-dam geotechnical condition (0.05).
- Unobserved parameters (e.g. field-only moraine dam internal ice core / freeboard) are listed in `missing_parameters` and varied between `0.10` and `0.90` to report an explicit sensitivity interval (`score_range` and `category_range`).
- **Screening scores are normalized indices in $[0, 1]$, never statistical outburst probabilities.**

### Supervised Machine Learning Pipeline (Random Forest, XGBoost, MLP)
- Activated when a verified regional GLOF inventory CSV (`data/training/glof_susceptibility/verified_glof_events.csv`) containing $\ge 20$ documented historical outburst / non-outburst lakes with citations is provided.

