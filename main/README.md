# Timestamp_msi

`Timestamp_msi` is now a focused single-system TCGA colorectal MSI workstation.
The current branch is no longer the older four-mode UI described in previous
docs. The active app is:

- one Next.js dashboard in `apps/web`
- one lean FastAPI service in `apps/api`
- one VM-backed TCGA DX1 training pipeline
- one archive summary flow for completed TCGA batch runs

For the full framework-agnostic system reference, VM details, model/runtime
notes, and validated run conventions, see [generic.md](./generic.md).

The current frontend is built around one screen: `TCGA DX1 MSI Runner`.

## Current Branch Shape

What is active right now:

- the web UI polls backend health plus the latest TCGA bundle/archive summary
- the main launch action is `POST /approach-2/pipeline/train-tcga-slide-triad`
- live progress comes from `GET /approach-2/pipeline/train-tcga-slide-triad-latest`
- archived multi-batch summaries come from
  `GET /approach-2/pipeline/tcga-batch-archive-latest`
- VM utility actions still exist under `/vm/*`
- a CRC patch-classification path still exists for direct training and uploaded
  patch prediction

What is present in the repo but not mounted by the current FastAPI entrypoint:

- older cohort routes
- older experiments routes
- Monte Carlo route families
- parallel metrics route families
- integrations route families
- data-batch route families
- Approach 2 slide and webhook routers

Those files still exist in the tree, but `apps/api/app/main.py` currently mounts
only `/vm/*`, `/approach-2/pipeline/*`, and `/approach-2/artifacts`.

## Live System

The frontend is a single dashboard rendered from:

- `apps/web/src/app/page.tsx`
- `apps/web/src/components/msi-workbench.tsx`

It:

- launches one TCGA DX1 bundle
- refreshes every 30 seconds
- stores the latest tracked `bundle_id` in browser local storage
- shows live bundle state, ETA, label counts, archive summaries, and selected
  slide previews
- renders label balance with D3 and approach metrics with Recharts

The backend entrypoint is:

- `apps/api/app/main.py`

Its mounted surface is:

```text
GET  /health

GET  /vm/status
GET  /vm/files
POST /vm/upload
POST /vm/downloader/start
POST /vm/jupyter/start
POST /vm/tunnel/start
POST /vm/monte-carlo/workspace

POST /approach-2/pipeline/preprocess
POST /approach-2/pipeline/extract_features
POST /approach-2/pipeline/train
POST /approach-2/pipeline/train-triad
POST /approach-2/pipeline/train-tcga-slide-triad
GET  /approach-2/pipeline/train-tcga-slide-triad-latest
GET  /approach-2/pipeline/tcga-batch-archive-latest
GET  /approach-2/pipeline/train-tcga-slide-triad/{bundle_id}
POST /approach-2/pipeline/predict
POST /approach-2/pipeline/predict-upload

Static mount:
/approach-2/artifacts
```

## TCGA DX1 Runner

The current TCGA request schema lives in
`apps/api/app/approach_2/schemas/schemas.py`.

The default DX1 run parameters are effectively:

- `experiment_name`: `tcga-coad-dx1-single-system`
- `bucket_uri`: `gs://wsi_aiml_repo/TCGA/TCGA_COAD/TCGA_COAD`
- `slide_limit`: `110`
- `n_folds`: `2`
- `n_repeats`: `2`
- `preferred_slide_pattern`: `DX`
- `preferred_exact_suffix`: `DX1`
- `annotations_csv`: `annotations/tcga_coad_bucket_annotations_final_all3_live_dx1.csv`
- `feature_extractor`: `virchow,ctranspath`
- `allow_generic_fallback`: `false`
- `tile_px`: `256`
- `tile_um`: `128`
- `max_parallel_approaches`: `2`
- `max_tiles_per_slide`: `96`
- `mpp_override`: `0.25`
- `qc_method`: `otsu`

The TCGA automation runner in
`scripts/run_tcga_coad_automated_triad.py` performs this flow:

```text
match annotations to GCS slides
-> choose a balanced DX1 subset
-> download selected .svs files
-> create Slideflow project + TFRecords
-> generate feature bags
-> launch two MIL approaches in parallel
-> aggregate fold metrics
-> write final_summary.json
-> update status.json for the dashboard
```

Bundle states currently surfaced to the UI include:

- `matching_annotations`
- `downloading_slides`
- `extracting_tiles`
- `retrying_tiles`
- `generating_features`
- `prepared`
- `training_parallel`
- `completed`
- `failed`

## Active Approaches

The current single-system TCGA run launches two MIL lanes:

- `Approach1`
  `transmil`
  `16` epochs
  seed `310`
- `Approach2`
  `attention_mil`
  `18` epochs
  seed `310`

Those presets are defined in
`apps/api/app/approach_2/services/triad_runtime.py`.

The summary endpoint returns aggregate metrics such as:

- `mean_auroc`
- `mean_f1_macro`
- `mean_f1_macro_default_threshold`
- `mean_best_threshold`
- `folds`
- artifact paths for predictions and fold summaries

## Batch Archive Runner

`scripts/run_tcga_coad_four_batches.py` is the sequential archive orchestrator.
It:

- splits a source annotation CSV into multiple balanced batches
- writes per-batch inputs under `automation/batch_inputs/`
- launches the TCGA bundle runner for each batch
- archives `status.json`, `final_summary.json`, `fold_metrics.csv`, and
  `runner.log`
- cleans the working bundle between runs
- writes `orchestration_status.json` for archive-level reporting

The dashboard reads the most recent archive summary through:

- `GET /approach-2/pipeline/tcga-batch-archive-latest`

## CRC Patch Path Still Present

The repo still has the earlier CRC patch-classification workflow. It is not the
main UI anymore, but it is still real code.

Relevant endpoints:

- `POST /approach-2/pipeline/train`
- `POST /approach-2/pipeline/train-triad`
- `POST /approach-2/pipeline/predict-upload`

Relevant files:

- `apps/api/app/approach_2/pipelines/patch_trainer.py`
- `apps/api/app/approach_2/services/triad_runtime.py`
- `scripts/run_crc_patch_training.py`
- `scripts/predict_crc_patch_image.py`

The uploaded patch prediction helper now falls back to the known VM CRC dataset
path if older experiment metadata does not carry `dataset_path`, so it no
longer sends a blank `--dataset-path`.

## Repository Layout

```text
main/
  apps/
    api/
      app/
        main.py
        api/routes/
          vm.py
        approach_2/
          api/
            pipeline.py
          database/
            models.py
            setup.py
          pipelines/
            patch_trainer.py
            mil_trainer.py
            feature_extractor.py
            project_setup.py
            inference.py
          schemas/
            schemas.py
          services/
            dataset_sources.py
            experiment_labels.py
            triad_runtime.py
      README.md
    web/
      src/
        app/
          page.tsx
          globals.css
        components/
          msi-workbench.tsx
      README.md
  automation/
    batch_inputs/
    n8n/
    tcga_slide_triads/
  scripts/
    run_tcga_coad_automated_triad.py
    run_tcga_coad_four_batches.py
    run_crc_patch_training.py
    predict_crc_patch_image.py
  annotations/
  datasets/
  README.md
```

## VM Defaults

Current VM defaults in the code/docs follow this shape:

```text
user: <vm-user>
host: <vm-host>
project root: /path/to/project/root
```

Expected local environment:

```powershell
$env:MSI_VM_USER = "<vm-user>"
$env:MSI_VM_HOST = "<vm-host>"
$env:MSI_VM_KEY = "<path-to-ssh-key>"
$env:MSI_VM_PROJECT_ROOT = "/path/to/project/root"
```

Latest live storage check I verified from this workstation on May 4, 2026:

```text
/dev/root  484G total  326G used  159G available  68% used
```

## Local Run

### Backend

```powershell
cd <repo-root>\main\apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### Frontend

```powershell
cd <repo-root>\main\apps\web
npm.cmd install
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

### URLs

```text
Frontend: http://127.0.0.1:3000
Backend:  http://127.0.0.1:8001
Docs:     http://127.0.0.1:8001/docs
```

## Validation

Backend:

```powershell
cd <repo-root>\main\apps\api
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall app
```

Frontend:

```powershell
cd <repo-root>\main\apps\web
npm.cmd run lint
npm.cmd run build
```

Quick API checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-RestMethod http://127.0.0.1:8001/approach-2/pipeline/train-tcga-slide-triad-latest
Invoke-RestMethod http://127.0.0.1:8001/approach-2/pipeline/tcga-batch-archive-latest
```

## Important Notes

- The current root README now reflects the mounted code, not the older broader
  workstation concept.
- The frontend is intentionally narrowed to one polished DX1 system, not the
  old multi-tab lab.
- The repo still contains older experiment modules. Treat them as dormant or
  branch-history code unless they are explicitly re-mounted in `app.main`.
- Keep large WSI work VM-centric. The browser is the controller surface, not
  the compute location.
