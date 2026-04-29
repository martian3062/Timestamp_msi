# Project 1 - Slideflow MSI Pipeline (TCGA-CRC)

Automated end-to-end pipeline for classifying Microsatellite Instability (MSI-H vs MSS) from TCGA Colorectal Cancer diagnostic Whole Slide Images (WSIs).

## 🚀 Quick Start (Running on VM)

If the environment is set up, you can run the entire project with one command. This handles slide downloading, tile extraction, feature bagging using **Virchow** (or UNI/UNI-v2), 5-fold training, and advanced visualization.

```bash
# On the company VM (pathology310 environment)
cd ~/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc
python scripts/run_complete_pipeline.py --stage all
```

### Monitoring the Active Job
If you launched the job in the background, check progress here:
```bash
tail -f ~/pathology310_projects/single_slide_morphology/pipeline_output.log
```

## 📂 Project Structure

- **`annotations/`**: Contains `tcga_crc_msi_annotations.csv` with 60 slides (20 MSI-H, 40 MSS) and manifest files.
- **`scripts/`**: Core logic for the pipeline stages.
  - `run_complete_pipeline.py`: The main controller.
  - `generate_advanced_visualizations.py`: Creates high-quality ROC/PR curves and heatmaps.
- **`output/`**: (Generated) Final results, figures, and models are stored here.
  - `figures/`: Publication-quality plots (AUC, PR, Heatmaps).
  - `results/`: CSV summaries of metrics across folds.
  - `models/`: Trained MIL model weights.

## 🧠 Methodology

### 1. Data Source
- **Slides**: Open-access TCGA diagnostic slides (TCGA-COAD/TCGA-READ).
- **Labels**: MANTIS and MSIsensor scores from cBioPortal PanCancer Atlas.

### 2. Feature Extraction (Foundational Models)
The pipeline utilizes **Virchow** (by HistoAI/NVIDIA) as the preferred feature extractor. It provides rich, pathology-specific 1024-dimensional embeddings for each 256px tile.

```python
def build_extractor(sf):
    # Order of preference based on available SOTA pathology foundation models
    extractors_to_try = ["virchow", "uni_v2", "uni", "resnet50_imagenet"]
    for name in extractors_to_try:
        try:
            print(f"  [STATUS] Attempting to load feature extractor: {name}...")
            # For foundation models like virchow/uni, we often want mixed precision and resize=True
            return sf.build_feature_extractor(name, resize=True, mixed_precision=True), name
        except Exception as exc:
            print(f"  [INFO] Could not initialize {name}: {exc}")
    
    raise RuntimeError(f"Failed to initialize any of the preferred extractors ({extractors_to_try}). Please check your environment or HuggingFace credentials.")
```

### 3. Weakly Supervised Learning (MIL)
Uses **TransMIL** or **Attention MIL** to aggregate tile-level features into a whole-slide prediction. We use a **5-fold patient-level cross-validation** to ensure no data leakage.

## 📊 Results Summary
Results will be automatically aggregated into `output/results/cv_summary.json` including:
- Mean AUROC ± Std Dev
- Mean AUPRC (Avg Precision)
- Multi-fold ROC/PR Curves
- Attention-based ROI heatmaps

---
*Created for Advanced Pathology AI Workflows.*
