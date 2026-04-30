# Project 9 - Slideflow Studio Learning Companion

This mini project is for learning with one open-source `.svs` whole-slide image before jumping into the larger MSI training pipeline.

It keeps the flow simple:

1. Start with one `.svs` slide
2. Generate a thumbnail and quick quality-control views
3. Create a lightweight tissue mask and enhanced preview
4. Save simple metadata and a one-row manifest
5. Open or inspect the slide with Slideflow tools

## Good Use Case

Use this when you want to:

- understand how an `.svs` file is structured
- make a cleaner preview before deeper analysis
- practice with one slide only
- prepare a beginner-friendly input for Slideflow Studio

## Folder Layout

```text
project_9_slideflow_studio_learning_companion/
  README.md
  slideflow_studio_learning.ipynb
  scripts/
    prepare_single_svs_learning_case.py
    inspect_single_svs_slideflow_ready.py
    launch_slideflow_studio.py
  templates/
    single_slide_annotations_template.csv
```

## Main Entry Point

Use the notebook first:

`slideflow_studio_learning.ipynb`

That notebook now combines the core learning flow in one place:

- slide loading
- preview improvement
- tissue mask generation
- metadata summary
- manifest creation
- `import slideflow as sf`
- `sf.WSI(...).view()` example code
- exact Slideflow Studio launch commands

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

## Step 1 - Prepare A Slide

Run:

```bash
python scripts/prepare_single_svs_learning_case.py \
  --slide /path/to/your_slide.svs \
  --output-dir ./outputs/demo_slide
```

This creates:

- `thumbnail.png`
- `enhanced_preview.png`
- `tissue_mask.png`
- `tissue_overlay.png`
- `slide_summary.json`
- `single_slide_manifest.csv`

The original `.svs` file is not modified. This step improves the learning experience by creating easier preview assets around the slide.

## Step 2 - Inspect Slideflow Readiness

Run:

```bash
python scripts/inspect_single_svs_slideflow_ready.py \
  --slide /path/to/your_slide.svs \
  --manifest ./outputs/demo_slide/single_slide_manifest.csv
```

This checks:

- that the file can be opened
- basic OpenSlide metadata
- whether `slideflow` is installed
- the exact command to open Slideflow Studio

## Step 3 - Use Slideflow Studio

Run:

```bash
python scripts/launch_slideflow_studio.py \
  --slide /path/to/your_slide.svs \
  --manifest ./outputs/demo_slide/single_slide_manifest.csv
```

This prints:

- the exact local Studio command
- the exact VM Studio command
- the slide path you should open inside Studio
- the manifest path you can keep beside the slide while learning

If you want it to try launching Studio locally on a machine where Slideflow Studio is installed:

```bash
python scripts/launch_slideflow_studio.py \
  --slide /path/to/your_slide.svs \
  --manifest ./outputs/demo_slide/single_slide_manifest.csv \
  --run-local
```

## Windows PowerShell Example

```powershell
python .\scripts\prepare_single_svs_learning_case.py `
  --slide "E:\path\to\demo_slide.svs" `
  --output-dir ".\outputs\demo_slide"

python .\scripts\inspect_single_svs_slideflow_ready.py `
  --slide "E:\path\to\demo_slide.svs" `
  --manifest ".\outputs\demo_slide\single_slide_manifest.csv"

python .\scripts\launch_slideflow_studio.py `
  --slide "E:\path\to\demo_slide.svs" `
  --manifest ".\outputs\demo_slide\single_slide_manifest.csv"
```

## VM Example

After activating `pathology310`:

```bash
python scripts/prepare_single_svs_learning_case.py \
  --slide /home/pardeep/slides/demo_slide.svs \
  --output-dir ./outputs/demo_slide

python scripts/inspect_single_svs_slideflow_ready.py \
  --slide /home/pardeep/slides/demo_slide.svs \
  --manifest ./outputs/demo_slide/single_slide_manifest.csv

python scripts/launch_slideflow_studio.py \
  --slide /home/pardeep/slides/demo_slide.svs \
  --manifest ./outputs/demo_slide/single_slide_manifest.csv
```

## Open In Slideflow Studio

This mini project is meant to be used with Slideflow Studio after the preview assets are generated.

Local launch:

```bash
slideflow-studio
```

Or:

```bash
python -m slideflow.studio
```

Then open the `.svs` slide directly. Keep these files next to you while learning:

- `thumbnail.png`
- `enhanced_preview.png`
- `tissue_overlay.png`
- `slide_summary.json`
- `single_slide_manifest.csv`

Recommended Studio learning flow:

1. Open the original `.svs` slide in Studio
2. Compare it with `thumbnail.png` and `enhanced_preview.png`
3. Use `tissue_overlay.png` to understand where tissue is concentrated
4. Check `slide_summary.json` for magnification and metadata context
5. Use the manifest as a lightweight annotation reference

## VM Studio Note

On the VM, Studio is available inside `pathology310`, but the GUI only opens if X11 forwarding is active on your Windows machine.

Typical VM-side environment setup:

```bash
source /opt/miniforge3/etc/profile.d/conda.sh
conda activate /opt/miniforge3/envs/pathology310
slideflow-studio
```

If you connect from Windows, make sure you first start an X server like `VcXsrv` or `X410`, then connect with X forwarding from Windows PowerShell.

## Notes

- This is intentionally smaller than the TCGA MSI project.
- It is for learning slide structure, previews, tissue coverage, and metadata first.
- Once this feels comfortable, move to `project_1_slideflow_msi_tcga_crc`.
