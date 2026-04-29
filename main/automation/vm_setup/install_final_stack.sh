#!/bin/bash
# Final Combo Stack for MSI-H vs MSS WSI workstation VM
# Target VM Specs: L4 GPU + 32GB RAM + 100GB Storage
# 
# Included layers:
# WSI reading/tiling: slideflow, openslide-python, openslide-bin, tiatoolbox
# Feature extraction: torch, torchvision, timm, transformers, huggingface_hub, safetensors
# Training: pytorch-lightning, monai, einops
# Metrics/testing: torchmetrics, scikit-learn, scipy, statsmodels
# Experiment control: hydra-core, omegaconf, optuna, mlflow
# Feature storage: h5py, zarr, pyarrow, duckdb, polars, pandas
# Backend/API: fastapi, pydantic, sqlalchemy, python-multipart
# Testing/dev quality: pytest, pytest-cov, ruff, mypy, pandera, pre-commit, rich, tqdm, loguru

set -e

echo "Installing Final Combo Stack..."

pip install \
  torch torchvision torchaudio \
  pytorch-lightning torchmetrics monai einops \
  slideflow openslide-python openslide-bin tiatoolbox \
  opencv-python scikit-image albumentations \
  timm transformers huggingface_hub safetensors \
  pandas polars pyarrow duckdb h5py zarr \
  scikit-learn scipy statsmodels \
  optuna hydra-core omegaconf mlflow tensorboard \
  fastapi pydantic sqlalchemy python-multipart \
  pytest pytest-cov ruff mypy pandera pre-commit \
  rich tqdm loguru

# Optional: uncomment if CUDA setup supports cucim
# pip install cucim

echo "Installation complete!"
