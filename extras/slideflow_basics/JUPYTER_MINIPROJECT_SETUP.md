# Jupyter Setup: Single-Slide Morphology Clustering

This mini-project uses my personal `pathology310` environment on the VM.

Notebook:

```text
single_slide_morphology_clustering.ipynb
```

## 1. SSH Into The VM

Run this in **Windows PowerShell**. This is the only command in this section that should run on Windows:

```powershell
ssh -i "$env:USERPROFILE\.ssh\<ssh-private-key>" <vm-user>@<vm-host-or-ip>
```

After this command works, your terminal prompt should change from a Windows path like:

```text
PS E:\4basecare\third>
```

to a Linux VM shell prompt. The next commands must run inside that SSH session, not directly in Windows PowerShell.

## 2. Activate The Environment

Run these **inside the SSH VM terminal**:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
```

Check Python and GPU:

```bash
python --version
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Expected:

```text
Python 3.10.20
True
NVIDIA L4
```

## 3. Register A Jupyter Kernel

Run this once **inside the SSH VM terminal**:

```bash
python -m ipykernel install --user --name pathology310 --display-name "Python 3 (pathology310)"
```

## 4. Start JupyterLab

Run this **inside the SSH VM terminal**:

```bash
jupyter lab --no-browser --ip=0.0.0.0 --port=8888
```

Keep this terminal open.

Important: do not run this notebook with a local Windows Python kernel. `scanpy`, `lazyslide`, `torch`, and the GPU setup are inside the VM environment at:

```text
/opt/miniforge3/envs/pathology310
```

## 5. Open An SSH Tunnel

On your local Windows machine, open another PowerShell window. This command runs on **Windows PowerShell**, while the Jupyter server keeps running in the VM terminal:

```powershell
ssh -i "$env:USERPROFILE\.ssh\<ssh-private-key>" -L 8888:localhost:8888 <vm-user>@<vm-host-or-ip>
```

Then open:

```text
http://localhost:8888
```

Use the token printed in the VM Jupyter terminal.

## Common Windows Mistake

Do not run these commands directly in Windows PowerShell:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
jupyter lab --no-browser --ip=0.0.0.0 --port=8888
```

They are Linux VM commands. They only work after you SSH into the VM.

If you accidentally installed a local Windows kernel named `pathology310`, ignore it. It points to Windows Python, not the VM Python. The correct kernel must come from:

```text
/opt/miniforge3/envs/pathology310/bin/python
```

## 6. Open The Notebook

Open:

```text
single_slide_morphology_clustering.ipynb
```

Choose this kernel:

```text
Python 3 (pathology310)
```

If you are using Windows/Antigravity and see `ModuleNotFoundError: No module named 'scanpy'`, the selected kernel is wrong. Change the notebook kernel to `Python 3 (pathology310)`, restart the kernel, and run again from the first cell.

## 7. Run Inside Antigravity Instead Of Browser

Use Antigravity with the VM Jupyter server, not a local Windows kernel.

Current VM Jupyter URL:

```text
http://localhost:8888/lab?token=24170f48772db36f781d66147c73e7b194834368b31471e4
```

In Antigravity:

1. Open `single_slide_morphology_clustering.ipynb`.
2. Click the kernel selector in the top-right of the notebook.
3. Choose an option like `Select Another Kernel`, `Existing Jupyter Server`, or `Jupyter Server`.
4. Paste the local tunneled VM server URL:

```text
http://localhost:8888/?token=24170f48772db36f781d66147c73e7b194834368b31471e4
```

5. Select:

```text
Python 3 (pathology310)
```

6. Restart the kernel and run the notebook from the first cell.

Do not choose a local Windows Python interpreter. The correct Python path is:

```text
/opt/miniforge3/envs/pathology310/bin/python
```

## 8. What The Notebook Does

The notebook performs this workflow:

1. Loads one public GTEx WSI through LazySlide.
2. Detects tissue regions.
3. Tiles the tissue.
4. Extracts tile morphology features using `ctranspath`.
5. Runs PCA, nearest neighbors, UMAP, and Leiden clustering.
6. Saves a UMAP plot and spatial cluster map.
7. Saves tile-level cluster metadata.

The notebook also has an optional advanced CONCH section. CONCH uses `MahmoodLab/CONCH` from Hugging Face and requires accepted gated-model terms plus a valid `HF_TOKEN`. Leave `RUN_CONCH_EXPERIMENT = False` until that access is ready.

Output folder:

```text
single_slide_morphology_outputs/
```

## 8. Notes

- First run can be slow because the slide/model may need to download.
- Feature extraction is the slowest step.
- The NVIDIA L4 GPU should be used automatically by PyTorch.
- If the notebook says CUDA is not available, restart Jupyter from the activated `pathology310` environment.
- Do not upgrade core packages inside `/opt/miniforge3/envs/pathology310` while running this beginner project.
