# Pathology310 VM User Guide

This guide is for users who have access to the shared pathology VM and want to run Python, Jupyter, Streamlit, Gradio, WSI pipelines, or AI workflows using the pre-installed `pathology310` environment.

## 1. Login To The VM

From Windows PowerShell:

```powershell
ssh -i "$vm stored key path" name@[IP_ADDRESS]
```

````

After login, you should be inside the Linux VM.

## 2. Activate The Shared Environment

Run:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
````

Check that it worked:

```bash
which python
python --version
```

Expected:

```text
/opt/miniforge3/envs/pathology310/bin/python
Python 3.10.20
```

## 3. Quick GPU Test

Run:

```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Expected:

```text
True
NVIDIA L4
```

If this prints `False`, the environment is still usable for CPU work, but GPU training/inference will not run correctly.

## 4. Run A Python Script

Activate the environment first:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
```

Then run:

```bash
python your_script.py
```

You can also run Python directly without activation:

```bash
/opt/miniforge3/envs/pathology310/bin/python your_script.py
```

## 5. Start JupyterLab

On the VM:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
jupyter lab --no-browser --ip=0.0.0.0 --port=8888
```

On your local Windows machine, open another PowerShell window and run:

```powershell
ssh -i "$env:USERPROFILE\.ssh\evolet_rsa" -L 8888:localhost:8888 pardeep@34.55.157.128
```

Then open this in your browser:

```text
http://localhost:8888
```

Use the token printed by Jupyter in the VM terminal.

## 6. Start Streamlit

On the VM:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

On your local Windows machine:

```powershell
ssh -i "$env:USERPROFILE\.ssh\evolet_rsa" -L 8501:localhost:8501 pardeep@34.55.157.128
```

Open:

```text
http://localhost:8501
```

## 7. Start Gradio

Your Gradio script should launch like this:

```python
demo.launch(server_name="0.0.0.0", server_port=7860)
```

Run the app on the VM:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
python app.py
```

On your local Windows machine:

```powershell
ssh -i "$env:USERPROFILE\.ssh\evolet_rsa" -L 7860:localhost:7860 pardeep@34.55.157.128
```

Open:

```text
http://localhost:7860
```

## 8. What Is Installed

The `pathology310` environment includes around 571 Python packages.

Main groups:

| Area                | Examples                                                                              |
| ------------------- | ------------------------------------------------------------------------------------- |
| GPU deep learning   | `torch`, `torchvision`, `torchaudio`, `cupy`, `onnxruntime-gpu`                       |
| Pathology / WSI     | `slideflow`, `openslide-python`, `tiffslide`, `tiatoolbox`, `wsidata`, `lazyslide`    |
| Foundation models   | `timm`, `transformers`, `huggingface-hub`, `open-clip-torch`, `sentence-transformers` |
| LLM APIs            | `openai`, `anthropic`, `groq`, `google-genai`, `litellm`                              |
| Bioinformatics      | `scanpy`, `mudata`, `muon`, `scvelo`, `infercnvpy`, `biopython`, `pysam`              |
| Medical imaging     | `SimpleITK`, `nibabel`, `torchio`, `monai`, `segmentation-models-pytorch`             |
| Data science        | `pandas`, `numpy`, `polars`, `duckdb`, `scikit-learn`, `scipy`                        |
| ML models           | `xgboost`, `lightgbm`, `catboost`, `optuna`, `shap`                                   |
| Visualization       | `plotly`, `altair`, `panel`, `holoviews`, `dash`, `streamlit`, `gradio`               |
| NLP                 | `spacy`, `nltk`, `gensim`, `rank-bm25`                                                |
| Files and databases | `sqlalchemy`, `psycopg`, `pymongo`, `openpyxl`, `xlsxwriter`                          |

For more detail, see:

```text
README.md
```

## 9. Common Checks

Check package count:

```bash
python -m pip list --format=freeze | wc -l
```

Check installed packages:

```bash
python -m pip list
```

Check WSI libraries:

```bash
python -c "import slideflow, openslide, tiffslide, tiatoolbox; print('WSI OK')"
```

Check ML libraries:

```bash
python -c "import pandas, numpy, sklearn, xgboost, lightgbm, catboost; print('ML OK')"
```

Check transformer libraries:

```bash
python -c "import torch, timm, transformers; print('AI stack OK')"
```

## 10. Shared Environment Rules

This is a shared environment. Please follow these rules:

1. Do not randomly upgrade major packages in `/opt/miniforge3/envs/pathology310`.
2. Do not run `pip install --upgrade` on core packages like `torch`, `numpy`, `dask`, `spatialdata`, `slideflow`, or `tiatoolbox` unless everyone agrees.
3. Use your project folder for scripts, notebooks, outputs, and experiments.
4. Keep large datasets in the agreed shared data location, not inside the Conda environment.
5. Avoid storing model checkpoints inside `/opt/miniforge3/envs/pathology310`.
6. If you need a new package for testing, create a separate environment or ask before changing the shared one.

## 11. Important Compatibility Note

`dask` and `distributed` are pinned to:

```text
2024.11.2
```

This is intentional for compatibility with pathology and spatial data tools such as:

```text
spatialdata
wsidata
lazyslide
```

Do not upgrade Dask casually.

## 12. Shortcut Aliases

The environment may eventually provide aliases like:

```bash
pathology310-shell
pathology310-run
```

At the time of verification, the alias file was not installed on the VM. Use this activation command instead:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
```

## 13. Quick Start

```bash
ssh -i "$env:USERPROFILE\.ssh\evolet_rsa" pardeep@34.55.157.128

source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310

python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Expected:

```text
True
NVIDIA L4
```
