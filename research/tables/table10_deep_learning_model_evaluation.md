# Table 10: Deep Learning Glacial Lake Segmentation Evaluation (`U-Net` vs `DeepLabV3+`)

*Exported from GlacioGuard AI database (`table10_deep_learning_model_evaluation.csv`)*

| Run ID | Model | Split | Tile Count | Best Epoch | IoU | Dice | Precision | Recall | F1-Score | Pixel Accuracy | TN Pixels | FP Pixels | FN Pixels | TP Pixels |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | UNET | val | 13 | 32 | 0.452 | 0.6226 | 0.6383 | 0.6077 | 0.6226 | 0.992 | 209877 | 798 | 909 | 1408 |
| 1 | UNET | test | 13 | 32 | 0.6105 | 0.7582 | 0.8197 | 0.7052 | 0.7582 | 0.9857 | 205194 | 1047 | 1990 | 4761 |
| 2 | DEEPLABV3PLUS | val | 13 | 31 | 0.2547 | 0.406 | 0.3453 | 0.4924 | 0.406 | 0.9843 | 208512 | 2163 | 1176 | 1141 |
| 2 | DEEPLABV3PLUS | test | 13 | 31 | 0.4618 | 0.6319 | 0.6025 | 0.6642 | 0.6319 | 0.9755 | 203283 | 2958 | 2267 | 4484 |

### Notes
- Dataset partitioned via Geographic Longitudinal Block Split (West 60% train / Central 20% val / East 20% test) to prevent spatial autocorrelation leakage.
