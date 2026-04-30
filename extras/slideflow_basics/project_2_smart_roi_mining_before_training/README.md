# Project 2 - Smart ROI Mining Before Training

This mini project uses `LazySlide` to mine useful tissue regions before sending data into `Slideflow`.

## Core Idea

- `LazySlide` finds high-tissue and morphology-rich regions quickly
- `Slideflow` uses only those better regions for training
- this cuts blank-space patches and makes training more efficient

## Open-Source Data Ideas

- `TCGA COAD/READ` diagnostic slides
- `CAMELYON16`
- `PAIP` or other public WSI challenge slides if you want more ROI-style work

## Main Notebook

- `smart_roi_mining_before_training.ipynb`

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

1. load one or more public slides
2. detect tissue-rich or candidate ROI areas
3. export ROI summaries
4. create a filtered training manifest
5. compare training with full-slide patching vs ROI-only patching
