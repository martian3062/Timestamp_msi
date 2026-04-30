# Project 6 - Explainable MSI Mini Pipeline

This mini project uses `LazySlide` for slide understanding and `Slideflow` for MSI learning plus heatmap interpretation.

## Core Idea

- use `LazySlide` to understand tissue coverage and candidate regions first
- use `Slideflow` to train or load an MSI-H vs MSS model
- compare model heatmaps with the earlier tissue and ROI cues

## Open-Source Data Ideas

- `TCGA COAD/READ`
- the curated annotations already in `project_1_slideflow_msi_tcga_crc`
- `CRC-VAL-HE-7K` if you want a smaller patch-only warm-up

## Main Notebook

- `explainable_msi_mini_pipeline.ipynb`

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

1. choose a public MSI slide cohort
2. inspect tissue structure with `LazySlide`
3. connect labels and manifests
4. run a small `Slideflow` MSI experiment
5. inspect attention or prediction heatmaps
6. compare heatmaps against the earlier tissue cues
