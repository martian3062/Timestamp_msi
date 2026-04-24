# Timestamp_msi

Timestamp_msi is a local-first MSI-H vs MSS colorectal WSI workstation for the
4basecare Approach 1 project. It combines a Next.js frontend, a local Node API
bridge, and an SSH-connected pathology VM so the whole slide workflow can be
controlled from a simple browser GUI instead of repeatedly typing SSH commands.

The current app focuses on the TCGA colorectal cancer MSI workflow:

- validate MSI annotation files in the browser
- validate GDC diagnostic slide manifests in the browser
- inspect label and fold balance with static Recharts/D3 visualizations before
  model work
- connect to the pathology VM over SSH through a local API route
- browse the remote project folder
- upload selected annotation and manifest files to the VM project
- start or inspect the GDC slide downloader
- start Jupyter on the VM
- open a local SSH tunnel to Jupyter
- run n8n-driven automation checks, 10-SVS GDC batches, and small model trials

The frontend is intentionally honest: it does not invent model scores or fake
clinical outputs. It only displays values parsed from uploaded files or returned
by the live VM.

## Repository Layout

```text
Timestamp_msi/
  apps/
    api/
      app/
        api/routes/
          cohort.py
          data_batches.py
          experiments.py
          integrations.py
          monte_carlo.py
          vm.py
        core/
          config.py
        models/
          cohort.py
          data_batches.py
          experiments.py
          integrations.py
          monte_carlo.py
          vm.py
        services/
          cohort.py
          data_batches.py
          experiments.py
          monte_carlo.py
          vm.py
        main.py
      storage/
      tests/
      pyproject.toml
      README.md
    web/
      src/
        app/
          api/vm/route.ts
          globals.css
          layout.tsx
          page.tsx
        components/
          msi-workbench.tsx
          recharts-distribution.tsx
          winter-scene.tsx
      public/
      package.json
      package-lock.json
      README.md
      tsconfig.json
  automation/
    n8n/
      start-local.ps1
      timestamp-msi-connection-check.json
      timestamp-msi-gdc-10-svs-batch.json
      timestamp-msi-integrations-check.json
      timestamp-msi-live-source-check.json
      timestamp-msi-modular-training.json
      timestamp-msi-monte-carlo-pipeline.json
  configs/
    experiment_grid.example.json
    monte_carlo_search.example.json
  .gitignore
  README.md
```

`apps/web` is the browser workstation. `apps/api` is the FastAPI backend for
cohort validation, VM orchestration, n8n experiment endpoints, integration
checks, and GDC SVS batch control. `automation/n8n` contains importable n8n
workflows. `configs` stores shared experiment/runtime examples.

## What Was Used

Frontend stack:

- Next.js 16.2.4 with the App Router
- React 19.2.4
- TypeScript 5
- Tailwind CSS 4 through `@tailwindcss/postcss`
- Lucide React icons
- Recharts 3 and D3 7 for static charted outputs
- Three.js for the hero scene, with pointer-reactive motion disabled for layout
  stability
- Local browser file parsing for CSV and TSV files

Local server bridge:

- Next.js Route Handler at `apps/web/src/app/api/vm/route.ts`
- Node.js `child_process` for SSH execution
- Windows OpenSSH using the existing private key path
- Fixed action allowlist instead of arbitrary shell execution from the browser

Backend stack:

- FastAPI application at `apps/api/app/main.py`
- Pydantic request/response models
- `pydantic-settings` environment configuration
- Python `subprocess` SSH execution behind a fixed action allowlist
- Pytest coverage for the cohort parser and validation service
- n8n-facing endpoints for experiment planning, best-result lookup, integration
  status, and GDC 10-slide batch orchestration

Automation stack:

- n8n `1.114.4` launched through `automation/n8n/start-local.ps1`
- Safe connection, live-source, integration, GDC batch, and single-trial
  workflows
- GDC API for open TCGA-COAD/READ diagnostic `.svs` batches
- cBioPortal `coadread_tcga_pan_can_atlas_2018` as the MSI label source
- Optional Hugging Face, Zerve AI, Firecrawl, and Tinyfish keys via local
  `.env` only

Remote pathology VM:

- SSH command shape:

```powershell
ssh -i "%USERPROFILE%\.ssh\evolet_rsa" pardeep@34.55.157.128
```

- Project root on the VM:

```text
/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc
```

- Python/Jupyter wrapper used on the VM:

```text
pathology310-run
```

- Jupyter target:

```text
127.0.0.1:8888 on the VM, forwarded locally to http://127.0.0.1:8888
```

Dataset/workflow sources:

- TCGA-COAD/READ diagnostic whole-slide images from GDC
- MSI labels from cBioPortal study `coadread_tcga_pan_can_atlas_2018`
- GDC manifest-driven `.svs` download
- Patient-level fold validation for MSI-H vs MSS experiments

## Application Features

### Cohort File Validation

The GUI accepts an annotation CSV and a GDC manifest CSV/TSV.

Annotation detection looks for:

- patient / case / submitter id
- slide / filename / file / image
- MSI / label / class / status
- fold / split

Manifest detection looks for:

- id / UUID / file id
- filename / file / name

After upload, the app shows:

- selected filename
- parsed row count
- detected columns
- missing required mappings
- MSI label distribution
- fold distribution
- best completed experiment result, model, feature extractor, and epoch count
  when VM metrics exist
- configured/missing state for optional integration keys without printing secret
  values

### VM Control Panel

The GUI provides buttons for common VM work:

- `Check VM`: shows hostname, user, GPU, disk, slide count, partial download
  count, slide folder size, and Jupyter/downloader processes.
- `Browse project`: lists files and folders in allowed VM project locations.
- `Upload annotations`: writes the selected annotation file to
  `annotations/tcga_crc_msi_annotations.csv` on the VM.
- `Upload manifest`: writes the selected manifest to
  `annotations/gdc_manifest_tcga_crc_msi.tsv` on the VM.
- `Start downloader`: starts `scripts/download_gdc_manifest.py` through
  `pathology310-run` and writes output to `logs/gdc_download.log`.
- `Start Jupyter`: starts Jupyter Lab on VM port `8888` through
  `pathology310-run`.
- `Open tunnel`: opens the local SSH tunnel from `http://127.0.0.1:8888` to
  the VM Jupyter port.

### FastAPI Backend

The backend in `apps/api` mirrors the workstation's core operations behind a
clean API boundary:

```text
GET  /health
POST /cohort/validate
GET  /vm/status
GET  /vm/files?path=<allowed-vm-path>
POST /vm/upload
POST /vm/downloader/start
POST /vm/jupyter/start
POST /vm/tunnel/start
POST /experiments/bootstrap
POST /experiments/plan
POST /experiments/start
GET  /experiments/status/{trial_id}
GET  /experiments/best
POST /experiments/monte-carlo-plan
POST /experiments/mc-bootstrap
POST /experiments/uncertainty/start
GET  /experiments/uncertainty/{trial_id}
POST /experiments/bootstrap-ci/start
GET  /experiments/bootstrap-ci/{trial_id}
POST /experiments/seed-stability
GET  /experiments/best-stable
GET  /integrations/status
POST /data-batches/gdc/bootstrap
POST /data-batches/gdc/start
GET  /data-batches/gdc/status
POST /data-batches/gdc/cleanup
```

The backend is structured by responsibility:

- `app/api/routes`: HTTP endpoints
- `app/core`: settings and shared configuration
- `app/models`: Pydantic schemas
- `app/services/cohort.py`: CSV/TSV parsing, field mapping, label counts, fold
  counts, and readiness checks
- `app/services/vm.py`: SSH command construction, path allowlisting, file
  upload, process startup, and tunnel startup
- `app/services/experiments.py`: n8n-facing model grid expansion, VM trial
  startup, trial status parsing, and best-metric selection
- `app/services/data_batches.py`: VM-side GDC TCGA-CRC `.svs` batch download,
  status, manifest tracking, and slide cleanup hooks
- `app/api/routes/integrations.py`: secret-safe status checks for Hugging Face,
  Zerve AI, Firecrawl, and Tinyfish environment keys
- `tests`: backend unit tests

### n8n Automation

The `automation` branch adds a modular n8n path for model and hyperparameter
sweeps. n8n calls the FastAPI experiment endpoints, while the VM runs the real
Slideflow training script. Results are selected only from completed
`metrics.json` files written by the VM trial runner.

Start n8n locally:

```powershell
cd E:\4basecare-MSI\Approach_1
.\automation\n8n\start-local.ps1
```

Then open:

```text
http://127.0.0.1:5678
```

Import these workflows:

```text
automation/n8n/timestamp-msi-connection-check.json
automation/n8n/timestamp-msi-integrations-check.json
automation/n8n/timestamp-msi-live-source-check.json
automation/n8n/timestamp-msi-gdc-10-svs-batch.json
automation/n8n/timestamp-msi-modular-training.json
```

Recommended order:

1. Run `Timestamp_msi live source check` to confirm GDC and cBioPortal are
   reachable.
2. Run `Timestamp_msi SAFE connection check` to confirm local API, VM SSH,
   runner bootstrap, and one-trial planning work.
3. Run `Timestamp_msi integrations check` after adding local secret values.
4. Run `Timestamp_msi GDC 10 SVS batch` when you want the next 10 open GDC
   diagnostic slides downloaded to the VM.
5. Run `Timestamp_msi SAFE single trial launcher` only when you are ready to
   start GPU training.

The example sweep grid lives at:

```text
configs/experiment_grid.example.json
```

The automation details and first small-test grid are documented in:

```text
automation/README.md
```

### Monte Carlo Methods (hft-methods branch)

The `hft-methods` branch adds Monte Carlo and Bayesian robustness methods to the
training pipeline. These methods make model selection more scientific by
accounting for uncertainty and variance, not just peak accuracy.

#### 1. Monte Carlo Random Hyperparameter Search

Instead of exhaustive grid search, randomly sample hyperparameters from
continuous distributions:

- learning rate: log-uniform between `1e-5` and `3e-4`
- dropout: uniform between `0.1` and `0.5`
- weight decay: log-uniform between `1e-6` and `1e-3`
- epochs, seed, model, extractor: random choice from lists

```text
POST /experiments/monte-carlo-plan
Body: configs/monte_carlo_search.example.json
```

This is more efficient than brute grid search when GPU time is limited.

#### 2. MC Dropout Uncertainty Estimation

Enable dropout at inference time and run the same slide through the model
multiple times (default: 30 forward passes):

```text
POST /experiments/mc-bootstrap     (deploy runner scripts to VM)
POST /experiments/uncertainty/start (start MC dropout inference)
GET  /experiments/uncertainty/{id}  (read per-slide uncertainty results)
```

Output per slide:

| Field | Description |
|-------|-------------|
| `slide_id` | WSI identifier |
| `mean_msi_probability` | Mean of N forward passes |
| `std_uncertainty` | Standard deviation across passes |
| `confidence` | `high` / `medium` / `low` |

This identifies slides where the model is unsure and needs clinical review.

#### 3. Bootstrap Confidence Intervals

For each trial, resample predictions 1000+ times to compute reliable CIs:

```text
POST /experiments/bootstrap-ci/start
GET  /experiments/bootstrap-ci/{id}
```

Output example:

```text
AUROC: 0.82
95% CI: 0.74 - 0.89
AUPRC: 0.71
95% CI: 0.62 - 0.79
```

This makes results publication-ready instead of reporting single point estimates.

#### 4. Stability-Weighted Best Model Selection

Standard best-metric selection picks whatever scored highest, which may be a
lucky outlier. The stability-weighted formula penalizes high variance:

```text
stability_score = mean_auroc - 0.5 * sd_auroc
```

```text
GET /experiments/best-stable?rank_formula=mean_auroc%20-%200.5%20*%20sd_auroc
POST /experiments/seed-stability
```

This picks the model that performs well **and** is stable.

#### Monte Carlo n8n Workflow

Import the workflow:

```text
automation/n8n/timestamp-msi-monte-carlo-pipeline.json
```

Flow: bootstrap MC runners → generate random plan → find stable best → report.

Example config:

```text
configs/monte_carlo_search.example.json
```

### Safety Model


The browser never receives the private SSH key. The key stays on the local
machine and is used by the local Next.js API route only.

The API route does not expose a free-form command box. It supports only a small
set of fixed actions:

- `status`
- `listFiles`
- `uploadFile`
- `startDownloader`
- `startJupyter`
- `startTunnel`

Project browsing is restricted to the configured VM project roots. This keeps
the GUI useful without turning it into a remote shell exposed to the browser.

Important: this app is meant to run locally on your Windows machine. Do not
deploy the VM SSH bridge route to a public hosting platform unless it is first
reworked with proper authentication, authorization, auditing, and secret
management.

## Runtime Flow

1. Start the local Next.js app.
2. Start the FastAPI automation backend on port `8001`.
3. Start n8n with the pinned local launcher.
4. Open the GUI in the browser.
5. Upload annotation and manifest files locally, or run the GDC 10-SVS n8n
   batch workflow.
6. Let the browser validate labels, folds, and required columns.
7. Use `Upload annotations` and `Upload manifest` to copy selected files to the
   VM when using manual files.
8. Use `Check VM` to confirm GPU, disk, slide count, and process status.
9. Use `Start Jupyter` and `Open tunnel`.
10. Run only small n8n trial plans first; broaden model, extractor, epoch, and
    fold grids after real metrics are written.

## Local Setup

From the web app folder:

```powershell
cd apps\web
npm.cmd install
npm.cmd run dev
```

Then open:

```text
http://127.0.0.1:3000
```

The development server can also appear as `http://localhost:3000`.

From the backend folder:

```powershell
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Then open:

```text
http://127.0.0.1:8001/docs
```

From the repo root, start n8n:

```powershell
.\automation\n8n\start-local.ps1
```

Then open:

```text
http://127.0.0.1:5678
```

## Validation Commands

Run these from `apps/web`:

```powershell
npm.cmd run lint
npm.cmd run build
```

Both were passing after the VM GUI integration.

Run these from `apps/api`:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall app
```

The backend parser tests were passing after the FastAPI backend was added.

## VM Environment Overrides

The API route has defaults for the current VM, but each setting can be
overridden through environment variables before starting Next.js:

```powershell
$env:MSI_VM_USER = "pardeep"
$env:MSI_VM_HOST = "34.55.157.128"
$env:MSI_VM_KEY = "$env:USERPROFILE\.ssh\evolet_rsa"
$env:MSI_VM_PROJECT_ROOT = "/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc"
npm.cmd run dev
```

Optional backend integration keys are read from `apps/api/.env` using the
`MSI_` prefix. Keep real values local and rotate any key that was pasted into
chat or logs.

```powershell
MSI_HF_TOKEN=<fresh-hugging-face-token>
MSI_ZERVE_API_KEY=<fresh-zerve-key>
MSI_FIRECRAWL_API_KEY=<fresh-firecrawl-key>
MSI_TINYFISH_API_KEY=<fresh-tinyfish-key>
```

## Verified VM State

The latest live VM checks confirmed:

- host: `wsi-tca-experiments-3`
- GPU: NVIDIA L4
- slide folder: `slideflow_project/data/slides`
- completed slides: `0 .svs`
- partial downloads: `0 .part`
- slide folder size: about `24K`
- root disk: `484G` total, about `368G` used, about `116G` available
- local Jupyter tunnel: `http://127.0.0.1:8888`

These values are runtime state, so the GUI should be used as the source of
truth whenever you resume work.

## Frontend Stability Notes

The dashboard is intentionally static. Earlier pointer-reactive panels and
animated chart rendering made text/cards appear to slide or fall while loading.
Current behavior:

- no pointer-driven panel transforms
- no moving background block layer
- no Recharts animation
- static text and cards
- Three.js hero scene kept visually contained and no longer driven by pointer
  movement

If the browser still looks broken after pulling this branch, hard refresh the
page or restart the web dev server so old Turbopack/client chunks are not reused.

## Development Notes

Main files:

- `apps/api/app/main.py`: FastAPI application factory, CORS, health endpoint,
  and route registration.
- `apps/api/app/api/routes/cohort.py`: cohort validation endpoint.
- `apps/api/app/api/routes/vm.py`: VM status, browsing, upload, downloader,
  Jupyter, and tunnel endpoints.
- `apps/api/app/services/cohort.py`: backend CSV/TSV parser and validation
  logic.
- `apps/api/app/services/vm.py`: backend SSH action service.
- `apps/api/app/services/experiments.py`: n8n experiment planner, VM runner
  bootstrap, status, and best-result selection.
- `apps/api/app/models/monte_carlo.py`: Pydantic schemas for MC random search,
  MC dropout uncertainty, bootstrap CI, seed stability, and stable best ranking.
- `apps/api/app/services/monte_carlo.py`: Monte Carlo service with random HP
  sampling, MC dropout/bootstrap CI VM runners, seed stability analysis, and
  stability-weighted best model selection.
- `apps/api/app/api/routes/monte_carlo.py`: FastAPI endpoints for all Monte
  Carlo operations under `/experiments/`.
- `apps/api/app/services/data_batches.py`: GDC 10-SVS batch downloader bootstrap,
  status, and cleanup.
- `apps/web/src/components/msi-workbench.tsx`: browser UI, file parsing,
  cohort validation, VM action buttons, charted output panels, and automation
  status display.
- `apps/web/src/components/recharts-distribution.tsx`: client-only static
  Recharts charts for label/fold distributions.
- `automation/n8n/*.json`: importable n8n workflows for source checks, VM/API
  checks, integration checks, 10-SVS batches, safe single-trial training, and
  Monte Carlo uncertainty pipeline.
- `apps/web/src/app/api/vm/route.ts`: Node.js SSH bridge and fixed VM actions.
- `apps/web/src/app/page.tsx`: renders the workstation.
- `apps/web/src/app/layout.tsx`: metadata and app shell.
- `apps/web/src/app/globals.css`: global theme and base styling.
- `apps/web/README.md`: frontend-specific operating notes.

## GitHub Publish Commands

The repository target requested for this project is:

```text
https://github.com/martian3062/Timestamp_msi.git
```

Initial publish flow:

```powershell
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/martian3062/Timestamp_msi.git
git push -u origin main
```
