# Project 1 - Tissue QC To Patch Classification

This mini project combines `LazySlide` and `Slideflow` in the most practical beginner-to-intermediate way:

1. use `LazySlide` for slide preview, tissue coverage checks, and quick region quality control
2. use `Slideflow` for patch extraction and patch classification

## Why This Project

- `LazySlide` is fast and convenient for slide-level exploration
- `Slideflow` is strong for patch extraction and training workflows
- the combination reduces wasted background patches and makes the classifier cleaner

## Open-Source Data Ideas

- `CRC-VAL-HE-7K` for fast patch-level experiments
- `TCGA COAD/READ` `.svs` slides when you want real WSI input
- `CAMELYON16` if you want tumor vs non-tumor patch classification later

## Main Notebook

- `tissue_qc_to_patch_classification.ipynb`

## VM SSH

From Windows Command Prompt:

```cmd
ssh -i "%USERPROFILE%\.ssh\evolet_rsa" pardeep@34.59.145.240
```

After login:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
```

## Notebook Flow

1. load an open slide or patch dataset
2. inspect thumbnail and tissue-rich regions
3. define a lightweight ROI or tissue filter
4. generate a filtered manifest
5. train a simple patch classifier
6. compare baseline vs QC-filtered performance
