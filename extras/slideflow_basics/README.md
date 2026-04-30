# Pathology310 Personal VM Environment Guide

This README documents my personal `pathology310` environment on the pathology VM. The setup is intended for whole-slide imaging, pathology AI, oncology, bioinformatics, medical imaging, foundation models, notebooks, dashboards, and general data science work.

## Projects In This Workspace

| Project | Entry point | Purpose |
| --- | --- | --- |
| Single-slide morphology clustering | `single_slide_morphology_clustering.ipynb` | Beginner WSI tiling, feature extraction, UMAP, and clustering. |
| Project 1 - Slideflow MSI TCGA-CRC | `slideflow_msi_tcga_crc_pipeline.ipynb` | Weakly supervised MSI-H vs MSS classifier with open TCGA/GDC cohort creation, patient-level CV, and attention heatmaps. |
| Project 1 - Tissue QC To Patch Classification | `project_1_tissue_qc_to_patch_classification/README.md` | Use LazySlide for tissue QC first, then Slideflow for patch extraction and classification. |
| Project 2 - Smart ROI Mining Before Training | `project_2_smart_roi_mining_before_training/README.md` | Mine tissue-rich ROIs with LazySlide before feeding data into Slideflow training. |
| Project 6 - Explainable MSI Mini Pipeline | `project_6_explainable_msi_mini_pipeline/README.md` | Connect LazySlide tissue understanding with Slideflow MSI prediction and heatmap interpretation. |
| Project 9 - Slideflow Studio Learning Companion | `project_9_slideflow_studio_learning_companion/README.md` | Beginner-friendly one-slide workflow for SVS preview improvement, Slideflow Studio exploration, and `sf.WSI(...).view()` learning. |

## VM Access

From Windows PowerShell:

```powershell
ssh -i "$env:USERPROFILE\.ssh\<ssh-private-key>" <vm-user>@<vm-host-or-ip>
```

From Windows Command Prompt:

```cmd
ssh -i "%USERPROFILE%\.ssh\<ssh-private-key>" <vm-user>@<vm-host-or-ip>
```

Replace:

| Placeholder | Meaning |
| --- | --- |
| `<ssh-private-key>` | Your SSH private key file name |
| `<vm-user>` | Your Linux username on the VM |
| `<vm-host-or-ip>` | VM hostname or public IP address |

Verified environment details:

| Item | Value |
| --- | --- |
| GPU | NVIDIA L4 |
| GPU memory | ~23 GB |
| NVIDIA driver | `580.126.09` |
| Environment name | `pathology310` |
| Environment path | `/opt/miniforge3/envs/pathology310` |
| Python | `3.10.20` |
| Installed Python packages | `571` |

## Environment Path

The environment is installed at:

```bash
/opt/miniforge3/envs/pathology310
```

The Python executable is:

```bash
/opt/miniforge3/envs/pathology310/bin/python
```

## Activate The Environment

After SSH login:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
```

Confirm that the correct Python is active:

```bash
which python
python --version
```

Expected:

```text
/opt/miniforge3/envs/pathology310/bin/python
Python 3.10.20
```

You can also run Python directly without activating Conda:

```bash
/opt/miniforge3/envs/pathology310/bin/python your_script.py
```

Or with `conda run`:

```bash
/opt/miniforge3/bin/conda run -p /opt/miniforge3/envs/pathology310 python your_script.py
```

## GPU Verification

Check the GPU from the shell:

```bash
nvidia-smi
```

Check CUDA from Python:

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.version.cuda); print(torch.cuda.get_device_name(0))"
```

Verified result:

```text
2.7.0+cu128
True
12.8
NVIDIA L4
```

## Main Library Groups

### GPU And Deep Learning

| Library | Version |
| --- | --- |
| `torch` | `2.7.0+cu128` |
| `torchvision` | `0.22.0+cu128` |
| `torchaudio` | `2.7.0+cu128` |
| `cupy` | `14.0.1` |
| `onnxruntime-gpu` | `1.23.2` |
| `monai` | `1.5.2` |
| `lightning` | `2.6.1` |
| `albumentations` | `2.0.8` |
| `captum` | `0.9.0` |

Use these for GPU model training, inference, medical AI, segmentation, augmentation, and model explainability.

### Pathology And Whole-Slide Imaging

| Library | Version |
| --- | --- |
| `slideflow` | `3.0.2` |
| `openslide-python` | `1.4.3` |
| `tiffslide` | `2.5.1` |
| `wsidata` | `0.7.6` |
| `lazyslide` | `0.9.2` |
| `tiatoolbox` | `2.0.1` |
| `spatialdata` | `0.5.0` |
| `slideio` | `2.8.0` |
| `scanpy` | `1.11.5` |

Use these for WSI loading, tiling, tissue detection, patch extraction, spatial data analysis, and digital pathology workflows.

Quick test:

```bash
python -c "import slideflow, openslide, tiffslide, tiatoolbox; print('WSI stack OK')"
```

### Foundation Models, Transformers, And LLM

| Library | Version |
| --- | --- |
| `timm` | `1.0.25` |
| `transformers` | `5.3.0` |
| `huggingface-hub` | `1.7.1` |
| `open-clip-torch` | `3.3.0` |
| `sentence-transformers` | `5.4.1` |
| `evaluate` | `0.4.6` |
| `peft` | `0.19.1` |
| `trl` | `1.2.0` |
| `bertopic` | `0.17.4` |
| `openai` | `2.32.0` |
| `groq` | `1.1.2` |
| `anthropic` | `0.96.0` |
| `google-genai` | `1.73.1` |
| `litellm` | `1.83.0` |
| `faiss` | `1.13.2` |

Use these for embeddings, DINO/CLIP-style models, pathology foundation models, transformer inference, LLM APIs, fine-tuning helpers, and vector search.

### Optional CONCH Feature Extractor

The notebook includes an optional advanced CONCH section using `MahmoodLab/CONCH` from Hugging Face. CONCH is a multimodal pathology foundation model for histopathology image/text representation learning.

Keep `ctranspath` as the default beginner extractor because it runs cleanly in this VM without gated model access. Use CONCH only after:

1. Your Hugging Face account has accepted the `MahmoodLab/CONCH` model terms.
2. A valid `HF_TOKEN` is available to the notebook.
3. You set this in the optional CONCH cell:

```python
RUN_CONCH_EXPERIMENT = True
```

CONCH is gated and non-commercial; do not hardcode tokens into notebooks or commit tokens to Git.

### Bioinformatics, Omics, And Oncology

Installed libraries include:

```text
biopython
pyfaidx
pysam
pyBigWig
pyranges
cyvcf2
biom-format
goatools
gseapy
pybiomart
mudata
muon
scvelo
infercnvpy
scrublet
harmonypy
decoupler
loompy
igraph
leidenalg
```

Use these for genomics, FASTA/VCF/BAM files, gene set enrichment, single-cell analysis, CNV inference, trajectory analysis, and multi-omics workflows.

### Medical Imaging

| Library | Version |
| --- | --- |
| `SimpleITK` | `2.5.3` |
| `nibabel` | `5.4.2` |
| `torchio` | `1.0.2` |
| `segmentation-models-pytorch` | `0.5.0` |

Also included:

```text
nilearn
dipy
mahotas
pyfeats
torchstain
```

Use these for MRI/CT/NIfTI workflows, segmentation, image features, stain normalization, and medical image preprocessing.

### Data Science And Machine Learning

| Library | Version |
| --- | --- |
| `numpy` | `2.2.6` |
| `pandas` | `2.3.3` |
| `polars` | `1.39.3` |
| `duckdb` | `1.5.2` |
| `scipy` | `1.15.2` |
| `scikit-learn` | `1.7.2` |
| `scikit-image` | `0.25.2` |
| `statsmodels` | `0.14.6` |
| `lifelines` | `0.30.0` |
| `xgboost` | `3.2.0` |
| `lightgbm` | `4.6.0` |
| `catboost` | `1.2.10` |
| `optuna` | `4.8.0` |
| `shap` | `0.49.1` |
| `dask` | `2024.11.2` |
| `distributed` | `2024.11.2` |

Also included:

```text
imbalanced-learn
mlxtend
featuretools
feature-engine
category-encoders
sktime
tsfresh
pytorch-tabnet
skorch
statsforecast
sweetviz
ydata-profiling
pyod
```

Use these for tabular ML, survival analysis, feature engineering, model explanation, time series, profiling, anomaly detection, and large data processing.

### Visualization, Apps, And Dashboards

| Library | Version |
| --- | --- |
| `plotly` | `6.7.0` |
| `altair` | `6.0.0` |
| `panel` | `1.8.10` |
| `holoviews` | `1.22.1` |
| `hvplot` | `0.12.2` |
| `plotnine` | `0.15.3` |
| `dash` | `4.1.0` |
| `streamlit` | `1.56.0` |
| `gradio` | `6.12.0` |
| `folium` | `0.20.0` |
| `wordcloud` | `1.9.6` |
| `missingno` | `0.5.2` |

Use these for plots, dashboards, model demos, WSI apps, web reports, and exploratory visualization.

### NLP And Text

| Library | Version |
| --- | --- |
| `spacy` | `3.8.14` |
| `nltk` | `3.9.4` |
| `gensim` | `4.4.0` |
| `rank-bm25` | `0.2.2` |

Verified environment assets:

```text
SpaCy model: en_core_web_sm
NLTK data: tokenizers and corpora present
```

### Databases, Files, And Utilities

Installed libraries include:

```text
sqlalchemy
psycopg
pymongo
mysql-connector-python
orjson
ujson
faker
openpyxl
xlrd
xlsxwriter
```

Use these for databases, Excel files, JSON, and utility workflows.

### Media And Documents

Installed libraries include:

```text
librosa
soundfile
pdfplumber
tabula-py
pydub
```

Use these for audio, PDF extraction, table extraction, and document processing.

## Running JupyterLab

On the VM:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
jupyter lab --no-browser --ip=0.0.0.0 --port=8888
```

From local Windows PowerShell, create a tunnel:

```powershell
ssh -i "$env:USERPROFILE\.ssh\<ssh-private-key>" -L 8888:localhost:8888 <vm-user>@<vm-host-or-ip>
```

Open:

```text
http://localhost:8888
```

Use the token printed by Jupyter.

## Running Streamlit

On the VM:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

From local Windows PowerShell:

```powershell
ssh -i "$env:USERPROFILE\.ssh\<ssh-private-key>" -L 8501:localhost:8501 <vm-user>@<vm-host-or-ip>
```

Open:

```text
http://localhost:8501
```

## Running Gradio

In your Gradio app:

```python
demo.launch(server_name="0.0.0.0", server_port=7860)
```

Run it on the VM:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
python app.py
```

From local Windows PowerShell:

```powershell
ssh -i "$env:USERPROFILE\.ssh\<ssh-private-key>" -L 7860:localhost:7860 <vm-user>@<vm-host-or-ip>
```

Open:

```text
http://localhost:7860
```

## Useful Commands

Check Python:

```bash
/opt/miniforge3/envs/pathology310/bin/python --version
```

Check package count:

```bash
/opt/miniforge3/envs/pathology310/bin/python -m pip list --format=freeze | wc -l
```

List installed Python packages:

```bash
/opt/miniforge3/envs/pathology310/bin/python -m pip list
```

List Conda packages:

```bash
/opt/miniforge3/bin/conda list -p /opt/miniforge3/envs/pathology310
```

Check CUDA:

```bash
/opt/miniforge3/envs/pathology310/bin/python -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda); print(torch.cuda.get_device_name(0))"
```

Check WSI stack:

```bash
/opt/miniforge3/envs/pathology310/bin/python -c "import slideflow, openslide, tiffslide, tiatoolbox; print('WSI OK')"
```

Check ML stack:

```bash
/opt/miniforge3/envs/pathology310/bin/python -c "import pandas, numpy, sklearn, xgboost, lightgbm, catboost; print('ML OK')"
```

## Important Notes

### Alias Script Is Not Installed Yet

The original provisioning script mentions shortcuts:

```bash
pathology310-shell
pathology310-run
```

However, `/etc/profile.d/pathology310_env.sh` was not present when checked. Until that file is added, use direct Conda activation:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
```

### Dask Is Pinned

`dask` and `distributed` are pinned to:

```text
2024.11.2
```

This is intentional for compatibility with `spatialdata`, `wsidata`, and `lazyslide`. Avoid upgrading Dask unless the WSI and spatial libraries are tested again.

### Shared Root-Owned Environment

The environment is under `/opt/miniforge3` and is root-owned. Day-to-day usage works normally, but package installation or environment updates may require admin access.

Avoid installing experimental packages directly into this environment unless they are needed for the current VM project. For risky experiments, create a separate project environment.

## Quick Start

```bash
ssh -i "$env:USERPROFILE\.ssh\<ssh-private-key>" <vm-user>@<vm-host-or-ip>

source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310

python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Expected:

```text
True
NVIDIA L4
```
