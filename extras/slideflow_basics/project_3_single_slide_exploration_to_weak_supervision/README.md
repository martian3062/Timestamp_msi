# Project 3 - Single-Slide Exploration To Weak Supervision

This mini project starts with one open `.svs` slide for visual understanding, then expands into a small weak-supervision workflow across a curated slide set.

## Top 3 Mixed Stack

This project uses the strongest practical mix from the earlier options:

1. `LazySlide`
2. `Slideflow`
3. `CTransPath`-style pathology feature extraction with an attention-MIL style downstream plan

## Why These 3

- `LazySlide` is excellent for fast single-slide exploration, thumbnails, tissue awareness, and slide-level intuition
- `Slideflow` is one of the cleanest ways to move from slide exploration into real pathology patch and training workflows
- `CTransPath`-style features are a strong pathology-specific representation choice before weak supervision

## Main Learning Goal

Use one `.svs` first to understand:

- tissue distribution
- patch locations
- morphology differences
- what should and should not become training signal

Then scale into:

- feature extraction
- bag-level learning
- weakly supervised MSI or phenotype prediction

## Main Notebook

- `single_slide_to_weak_supervision.ipynb`

## Suggested Algorithms

This notebook is designed around:

- slide exploration with `LazySlide`
- patch/manifest workflow with `Slideflow`
- pathology features from `CTransPath`
- weak supervision using:
  - `Attention MIL`
  - `CLAM`
  - `Slideflow` MIL-style workflow if available in your runtime

## Open-Source Data Options

- `TCGA COAD/READ`
- `CAMELYON16`
- `CRC-VAL-HE-7K` as a patch-level warm-up before WSI weak supervision

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

1. inspect one open `.svs` slide
2. generate thumbnail and region understanding notes
3. define a small curated slide cohort
4. connect slide labels and manifests
5. extract pathology features
6. organize weak-supervision bags
7. train or plan `Attention MIL` / `CLAM`
8. compare predictions back to the original single-slide intuition
