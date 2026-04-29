# 4basecare-MSI

This repo is the final merged MSI workspace rooted at `E:\4basecare-MSI`. It combines the main workstation app, the Monte Carlo robustness lane, supporting baseline notebooks, local dataset pointers, and architecture assets into one repo that is easier to navigate and maintain.

## Main Structure

```text
4basecare-MSI/
  main/           Timestamp_msi workstation and orchestration app
  Monte_Carlo/    root entry for Monte Carlo files and references
  extras/         lazyslide and slideflow baseline experiments
  datasets/       local-only datasets and raw archives
  shared_assets/  advanced diagrams and flowcharts
```

## Final Repo Logic

### 1. `main`

This is the main product. It is the integrated `Timestamp_msi` workstation with:

- `Approach 1`: local-first orchestration, cohort validation, VM control, GDC/Jupyter workflow
- `Approach 2`: integrated platform-style API for patch and experiment runs
- `Monte Carlo`: uncertainty, bootstrap CI, repeated-seed stability, and search planning
- `Parallel Metrics`: truthful comparison across completed artifacts only

Primary code:

- `main/apps/api`
- `main/apps/web`
- `main/automation`
- `main/configs`

### 2. `Monte_Carlo`

This is the top-level pointer folder for the Monte Carlo lane. The actual runtime code still lives under `main`, but this folder makes the search/planning flow easier to find quickly.

### 3. `extras`

These are the supporting baseline and learning assets:

- `extras/lazyslide_basics`
- `extras/slideflow_basics`

Use them for notebook-driven exploration, open-data setup, and baseline pathology experiments that should stay visible but separate from the main app.

## Advanced Flowcharts

The higher-level system visuals are stored in:

- [advanced_msi_pipeline.png](</e:/4basecare-MSI/shared_assets/architecture/advanced_msi_pipeline.png>)
- [full model pipeline.png](</e:/4basecare-MSI/shared_assets/architecture/full model pipeline.png>)
- [msi_baseline_flowchart.svg](</e:/4basecare-MSI/shared_assets/architecture/msi_baseline_flowchart.svg>)
- [msi_multimodal_flowchart.svg](</e:/4basecare-MSI/shared_assets/architecture/msi_multimodal_flowchart.svg>)
- [msi_research_flowchart.svg](</e:/4basecare-MSI/shared_assets/architecture/msi_research_flowchart.svg>)
- [simple_msi_flowchart.png](</e:/4basecare-MSI/shared_assets/architecture/simple_msi_flowchart.png>)

How to read them:

- `baseline`: simplest deterministic lane from validated inputs to training output
- `advanced_msi_pipeline`: the broader orchestration picture with validation, compute, metrics, and automation
- `multimodal` and `research`: the more experimental long-range direction when morphology, embeddings, and advanced evaluation are combined
- `full model pipeline`: best when you want to explain the end-to-end training/inference surface in one visual

## Dataset Used

### Local active dataset

The current live dataset used by the integrated triad runner is:

```text
E:\4basecare-MSI\datasets\CRC-VAL-HE-7K
```

This is a patch-level folder-per-class dataset, not a raw whole-slide dataset.

Current class folders:

- `ADI`
- `BACK`
- `DEB`
- `LYM`
- `MUC`
- `MUS`
- `NORM`
- `STR`
- `TUM`

The default config for this lane lives at:

- [main/configs/crc_val_he_7k_patch_classifier.yaml](</e:/4basecare-MSI/main/configs/crc_val_he_7k_patch_classifier.yaml>)

### Supporting open-data lineage

The repo also keeps the open-data Slideflow baseline under:

- [extras/slideflow_basics](</e:/4basecare-MSI/extras/slideflow_basics>)

That lane is the WSI-oriented experimental foundation using open TCGA CRC materials, manifest-based download flow, and Slideflow notebooks/scripts for broader MSI work. In practice, the repo now contains both:

- a practical local patch dataset lane for fast integrated experimentation
- a larger WSI / Slideflow research lane for end-to-end pathology experiments

## How Data Is Processed

### Approach 1 processing

Approach 1 is the orchestration-first lane.

Input:

- annotation CSV / TSV
- manifest CSV / TSV
- optional local files for upload
- VM project folders and experiment artifacts

Flow:

1. Validate annotation fields such as patient, slide, label, and fold.
2. Validate GDC manifest identifiers and filenames.
3. Show label/fold distributions before compute starts.
4. Upload selected metadata to the VM when needed.
5. Start controlled VM-side actions such as downloader, Jupyter, or tunnel.
6. Read completed experiment summaries back into the UI.

Why this approach exists:

- It reduces bad runs caused by broken metadata.
- It keeps heavy `.svs` movement off the browser machine.
- It gives a safer operational surface before expensive training starts.

### Approach 2 processing

Approach 2 is the platform-style training lane, integrated inside `main/apps/api/app/approach_2`.

Input:

- folder-per-class patch dataset
- training request from UI or API
- optional experiment metadata and output path settings

Flow:

1. Resolve dataset path from workspace root or explicit custom path.
2. Build a dataset by reading class folders and allowed image extensions.
3. Resize and augment images.
4. Split into train/validation subsets with a fixed seed.
5. Build a selected backbone model.
6. Fine-tune the classifier head for multi-class patch prediction.
7. Write metrics and artifacts to the experiment record.
8. Surface results through API and UI comparison views.

Core implementation:

- [main/apps/api/app/approach_2/pipelines/patch_trainer.py](</e:/4basecare-MSI/main/apps/api/app/approach_2/pipelines/patch_trainer.py>)
- [main/apps/api/app/approach_2/services/dataset_sources.py](</e:/4basecare-MSI/main/apps/api/app/approach_2/services/dataset_sources.py>)

### Monte Carlo processing

Monte Carlo is the robustness and uncertainty lane.

Input:

- experiment/search configuration
- completed model runs or candidate plans
- repeated seeds / dropout passes / bootstrap samples

Flow:

1. Generate or expand candidate search combinations.
2. Run repeated seed experiments instead of trusting one lucky run.
3. Apply MC dropout to estimate uncertainty spread.
4. Use bootstrap confidence intervals for more honest metric reporting.
5. Rank candidates using a stability-aware formula rather than raw peak score only.

Why this matters:

- MSI experiments can look strong on a single run and collapse across seeds.
- Clinical-facing work needs confidence, not only point estimates.
- The best practical model is often the most stable one, not the absolute highest single AUROC.

Main references:

- [main/configs/monte_carlo_search.example.json](</e:/4basecare-MSI/main/configs/monte_carlo_search.example.json>)
- [Monte_Carlo/README.md](</e:/4basecare-MSI/Monte_Carlo/README.md>)

## Hyperparameters Used

### Active patch-classification defaults

From `main/configs/crc_val_he_7k_patch_classifier.yaml`:

- `dataset_path`: `E:\4basecare-MSI\datasets\CRC-VAL-HE-7K`
- `layout`: `folder_per_class`
- `image_extensions`: `.tif`, `.tiff`
- `classes`: `ADI, BACK, DEB, LYM, MUC, MUS, NORM, STR, TUM`
- `val_split`: `0.20`
- `backbone`: `resnet18`
- `use_pretrained`: `true`
- `image_size`: `224`
- `epochs`: `10`
- `batch_size`: `32`
- `learning_rate`: `1e-4`
- `num_workers`: `0`
- `seed`: `310`
- `primary_metric`: `val_accuracy`
- `secondary_metrics`: `val_f1_macro`, `val_auroc_ovr_macro`

### Why these defaults were chosen

- `resnet18`: lighter and faster than deeper backbones, so it is a strong baseline for local and VM patch experiments before moving to bigger encoders.
- `use_pretrained=true`: transfers general visual features and reduces training instability on limited pathology subsets.
- `image_size=224`: standard for ResNet family and efficient for quick iteration.
- `epochs=10`: enough for a first pass without pretending early results are final research-grade convergence.
- `batch_size=32`: practical balance between throughput and memory for patch-level work.
- `learning_rate=1e-4`: conservative fine-tuning rate that usually behaves better than aggressive rates when reusing pretrained weights.
- `val_split=0.20`: keeps a meaningful holdout without wasting too much data.
- `num_workers=0`: more stable on Windows-local runs where dataloader multiprocessing can be brittle.
- `seed=310`: repo-wide consistent seed choice for reproducible comparisons.
- `val_f1_macro` and `val_auroc_ovr_macro`: useful because class imbalance can hide behind accuracy alone.

### Supported backbone choices in code

The current patch trainer supports:

- `resnet18`
- `resnet34`
- `resnet50`

These are defined in:

- [main/apps/api/app/approach_2/pipelines/patch_trainer.py](</e:/4basecare-MSI/main/apps/api/app/approach_2/pipelines/patch_trainer.py>)

### Monte Carlo search space

The example search config is intentionally broad and advanced. It covers:

- data split strategy
- tiling controls
- feature extractor selection
- bagging policy
- MIL model type and dimensions
- loss weighting and focal-loss options
- optimizer and scheduler ranges
- augmentation
- bootstrap validation
- MC dropout
- Optuna trial/pruning strategy
- n8n batch size and storage safety gates

Important example values from `main/configs/monte_carlo_search.example.json`:

- `samples`: `8`
- `random_seed`: `310`
- `primary_metric`: `stable_score`
- `metric_direction`: `max`
- ranking formula:

```text
0.40 * mean_auroc
+ 0.25 * mean_auprc
+ 0.15 * balanced_accuracy
+ 0.10 * msi_h_sensitivity
+ 0.10 * calibration_score
- 0.20 * seed_std
```

Why this formula matters:

- it rewards discrimination
- it still values minority-class sensitivity
- it includes calibration
- it penalizes unstable seed behavior

That is much better than picking the single best lucky run.

## End-to-End Experimental Story

### Lane A: practical integrated patch workflow

Use this when you want fast iteration inside the main app.

1. Open the workstation UI in `main/apps/web`.
2. Validate metadata through Approach 1.
3. Point the training lane to `datasets/CRC-VAL-HE-7K`.
4. Run the integrated Approach 2 patch trainer.
5. Compare outputs in Parallel Metrics.
6. Use Monte Carlo tools if you want stronger robustness evidence.

### Lane B: broader WSI research workflow

Use this when you want more pathology-native whole-slide experimentation.

1. Start from `extras/slideflow_basics`.
2. Use open-data manifests and annotations.
3. Download / stage slide data on the VM.
4. Run feature extraction / Slideflow notebooks.
5. Explore MSI-related experimental directions with larger pathology context.

## Which Approach To Use When

- Use `Approach 1` when the problem is operational control, validation, VM workflow, or safe staging.
- Use `Approach 2` when the problem is direct patch-model training and experiment bookkeeping.
- Use `Monte Carlo` when the problem is trustworthiness, stability, and uncertainty.
- Use `Parallel Metrics` when the problem is comparing completed outputs without inventing values.
- Use `extras/slideflow_basics` when the problem is broader WSI research rather than the integrated app path.

## Deep References

- [main/README.md](</e:/4basecare-MSI/main/README.md>)
- [main/apps/api/README.md](</e:/4basecare-MSI/main/apps/api/README.md>)
- [main/apps/web/README.md](</e:/4basecare-MSI/main/apps/web/README.md>)
- [main/configs/crc_val_he_7k_patch_classifier.yaml](</e:/4basecare-MSI/main/configs/crc_val_he_7k_patch_classifier.yaml>)
- [main/configs/monte_carlo_search.example.json](</e:/4basecare-MSI/main/configs/monte_carlo_search.example.json>)
- [extras/slideflow_basics/README.md](</e:/4basecare-MSI/extras/slideflow_basics/README.md>)

## Branch

This root follows:

```text
https://github.com/martian3062/Timestamp_msi
branch: complex-triad
```
