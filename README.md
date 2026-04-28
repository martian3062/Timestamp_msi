# Timestamp_msi

Timestamp_msi is a local-first MSI-H vs MSS colorectal whole-slide-image
workstation for the 4basecare MSI experiments. It combines a premium Next.js
frontend, a FastAPI orchestration backend, a local SSH bridge, n8n automation,
and a remote pathology VM workflow.

The app is built around one practical rule: the browser should control the
workflow, but heavy pathology compute and large `.svs` files should stay on the
VM.

## Current State

The current branch exposes three separate workflow approaches from one UI:

- `Approach 1`: cohort/manifest validation, VM file upload, VM browsing, GDC
  downloader startup, Jupyter startup, SSH tunnel, and experiment-result view.
- `Approach 2`: imported platform backend from
  `E:\4basecare-MSI\Approach-2\backend\app`, mounted inside this FastAPI app
  under `/approach-2/*`.
- `Monte Carlo`: stochastic validation workflow for random search, MC dropout,
  bootstrap confidence intervals, stable model selection, and VM model-cache
  preparation.

The frontend is running on:

```text
http://127.0.0.1:3000
```

The FastAPI backend is expected on:

```text
http://127.0.0.1:8001
```

The app never invents clinical metrics. It shows values parsed from uploaded
files, returned by the backend, or read from VM-side artifacts.

## What This App Solves

MSI-H vs MSS WSI work has a lot of moving parts: open data, labels, manifests,
gigantic slide files, GPU feature extraction, MIL training, uncertainty
estimation, and repeatable experiment bookkeeping. This repo turns that into a
controlled local workstation:

- validate annotation and manifest files before GPU work starts
- keep `.svs` slides and model artifacts on the VM
- use fixed, allowlisted VM actions instead of arbitrary browser shell commands
- keep secrets in local `.env` files only
- run small batches first, then clean up raw slide storage when needed
- expose real backend routes that n8n and the frontend can both call
- support three experiment approaches without switching repos manually

## Architecture At A Glance

```text
Windows workstation
  |
  |  Browser UI
  v
apps/web  Next.js 16 / React 19 / Tailwind
  |
  |  HTTP to http://127.0.0.1:8001
  v
apps/api  FastAPI / Pydantic / SQLAlchemy / subprocess SSH
  |
  |  fixed SSH actions only
  v
Remote pathology VM
  |
  |  pathology310-run, Slideflow, Jupyter, GDC downloads
  v
TCGA CRC WSI pipeline artifacts
```

n8n is optional but supported:

```text
automation/n8n/start-local.ps1 -> http://127.0.0.1:5678
```

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
        approach_2/
          api/
            experiments.py
            pipeline.py
            slides.py
            webhook.py
          database/
            models.py
            setup.py
            supabase_client.py
          pipelines/
            feature_extractor.py
            inference.py
            mil_trainer.py
            project_setup.py
          schemas/
            schemas.py
          main.py
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
      .env.example
      pyproject.toml
      README.md
    web/
      public/
        assets/
          researching-cancer-msi-h.mp4
          snow-in-jinan.webm
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
      package.json
      README.md
  automation/
    n8n/
      docker-compose.yml
      start-local.ps1
      timestamp-msi-connection-check.json
      timestamp-msi-gdc-10-svs-batch.json
      timestamp-msi-integrations-check.json
      timestamp-msi-live-source-check.json
      timestamp-msi-modular-training.json
      timestamp-msi-monte-carlo-pipeline.json
    README.md
  configs/
    experiment_grid.example.json
    monte_carlo_search.example.json
  README.md
```

## Frontend Architecture

The frontend is a single workstation surface rendered by:

```text
apps/web/src/app/page.tsx
apps/web/src/components/msi-workbench.tsx
```

Main responsibilities:

- parse local CSV/TSV files in the browser
- detect required annotation and manifest fields
- show label and fold distributions
- switch between `Approach 1`, `Approach 2`, and `Monte Carlo`
- call the FastAPI backend on `http://127.0.0.1:8001`
- show optional integration status without revealing secret values
- expose practical VM controls for local development
- play the MSI-H/cancer research video in the hero media area

Frontend stack:

- Next.js `16.2.4`
- React `19.2.4`
- TypeScript `5`
- Tailwind CSS `4`
- Lucide React icons
- Recharts and D3 for static distributions
- Three.js dependencies are still installed, but the old hero visual has been
  replaced with `public/assets/researching-cancer-msi-h.mp4`

## Backend Architecture

The backend entrypoint is:

```text
apps/api/app/main.py
```

It registers:

- core cohort validation routes
- VM SSH action routes
- n8n experiment routes
- Monte Carlo routes
- GDC batch routes
- integration status routes
- Approach 2 platform routes under `/approach-2/*`
- static Approach 2 artifact serving under `/approach-2/artifacts`

Backend stack:

- FastAPI
- Pydantic and Pydantic Settings
- SQLAlchemy for Approach 2 local experiment registry
- pandas and python-multipart for CSV upload handling
- Python subprocess SSH calls for VM operations
- pytest for backend tests

## Approach 1

Approach 1 is the local-first VM orchestration workflow. It is best when you
want to inspect and control TCGA CRC MSI data movement before training.

Key functions:

- load annotation CSV
- load GDC manifest CSV/TSV
- detect patient, slide, label, and fold fields
- detect GDC file id and filename fields
- count MSI-H/MSS label balance
- count fold balance
- upload selected files to the VM
- browse allowlisted VM project folders
- start the GDC downloader
- start VM Jupyter
- open a local Jupyter tunnel
- read best completed experiment metadata

Important frontend controls:

- `Check VM`
- `Browse project`
- `Upload annotations`
- `Upload manifest`
- `Start downloader`
- `Start Jupyter`
- `Open tunnel`

Important backend routes:

```text
POST /cohort/validate
GET  /vm/status
GET  /vm/files
POST /vm/upload
POST /vm/downloader/start
POST /vm/jupyter/start
POST /vm/tunnel/start
GET  /experiments/best
```

## Approach 2

Approach 2 is a platform-style backend imported from:

```text
E:\4basecare-MSI\Approach-2\backend\app
```

Inside this repo it lives at:

```text
apps/api/app/approach_2
```

It is mounted under:

```text
/approach-2/*
```

Approach 2 is useful when you want a more conventional platform API:

- register slides
- upload slide label CSV files
- trigger preprocessing
- trigger feature extraction
- start Attention MIL training
- run prediction
- sync and inspect experiment records
- trigger n8n/Optuna-style trial callbacks

Important routes:

```text
POST /approach-2/slides/register
GET  /approach-2/slides/
POST /approach-2/slides/upload_csv
POST /approach-2/pipeline/preprocess
POST /approach-2/pipeline/extract_features
POST /approach-2/pipeline/train
POST /approach-2/pipeline/predict
GET  /approach-2/experiments/
GET  /approach-2/experiments/{experiment_id}
POST /approach-2/webhook/start-automation
POST /approach-2/webhook/optuna/trial
```

Approach 2 stores local experiment metadata through SQLAlchemy. SQLite is used
by default unless `DATABASE_URL` points to another database.

## Monte Carlo Approach

Monte Carlo is now its own GUI mode. In this repo, "Monte Carlo" means
pathology experiment robustness methods: random hyperparameter search,
repeated-seed stability, MC dropout uncertainty, bootstrap confidence
intervals, and stable-best ranking.

It does not mean trading or HFT execution. The branch name `hft-methods` is only
the historical branch name for this experiment track.

Main Monte Carlo functions:

- create a random hyperparameter search plan
- bootstrap VM runner scripts for uncertainty jobs
- start MC dropout inference jobs
- fetch MC dropout uncertainty summaries
- start bootstrap confidence interval jobs
- fetch bootstrap CI summaries
- analyze seed stability
- select the stability-weighted best model
- prepare VM-side model storage folders

Important routes:

```text
POST /vm/monte-carlo/workspace
POST /experiments/monte-carlo-plan
POST /experiments/mc-bootstrap
POST /experiments/uncertainty/start
GET  /experiments/uncertainty/{trial_id}
POST /experiments/bootstrap-ci/start
GET  /experiments/bootstrap-ci/{trial_id}
POST /experiments/seed-stability
GET  /experiments/best-stable
```

The VM workspace prep route creates:

```text
models/huggingface_cache
models/monte_carlo
logs
configs
configs/ai_integrations.env.example
```

The stable-best formula defaults to:

```text
mean_auroc - 0.5 * sd_auroc
```

This is safer than choosing the highest single metric when the result may be a
lucky fold or seed.

## Data Flow

The intended pipeline is:

```text
GDC + cBioPortal
  -> annotation and manifest validation
  -> small VM batch download
  -> preprocessing / tiling
  -> feature extraction
  -> MIL training or inference
  -> metric persistence
  -> Monte Carlo uncertainty and stability checks
  -> cleanup of raw slide batches when storage is tight
```

The storage-aware rule is:

```text
download -> validate -> preprocess -> extract features -> train/infer -> persist outputs -> cleanup
```

Prefer keeping features, metrics, model outputs, and manifests. Raw `.svs`
slides are expensive and should be processed in small batches when VM storage is
limited.

## External Data Sources

Primary sources:

- GDC diagnostic TCGA-COAD/READ `.svs` whole-slide images
- cBioPortal `coadread_tcga_pan_can_atlas_2018` MSI labels

The repo includes GDC batch automation and manifest-based VM downloading.
Patch-level or Kaggle datasets are not treated as replacements for real `.svs`
MIL work unless the experiment explicitly pivots to quick patch-level testing.

## AI And Integration Keys

Optional integrations are read from `apps/api/.env` using the `MSI_` prefix.
The status endpoint reports whether keys are configured, but never returns the
secret values.

Expected local keys:

```text
MSI_HF_TOKEN=<hugging-face-token>
MSI_GROQ_API_KEY=<groq-key>
MSI_ZERVE_API_KEY=<zerve-key>
MSI_FIRECRAWL_API_KEY=<firecrawl-key>
MSI_TINYFISH_API_KEY=<tinyfish-key>
```

Current integration status route:

```text
GET /integrations/status
```

Provider roles:

- Hugging Face: gated pathology models and model-cache storage
- Groq AI: fast LLM planning or experiment-summary generation
- Zerve AI: optional notebook/job orchestration bridge
- Firecrawl: optional research-source crawling and metadata extraction
- Tinyfish: optional browser/API automation for external checks

Important: keep real keys only in ignored local `.env` files or proper secret
stores. If keys were pasted into chat or logs, rotate them before production
use.

## VM Configuration

Default VM target:

```text
pardeep@34.55.157.128
```

Default SSH command:

```powershell
ssh -i "$env:USERPROFILE\.ssh\evolet_rsa" pardeep@34.55.157.128
```

Default project root on the VM:

```text
/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc
```

Default VM wrapper:

```text
pathology310-run
```

Backend environment values:

```powershell
$env:MSI_VM_USER = "pardeep"
$env:MSI_VM_HOST = "34.55.157.128"
$env:MSI_VM_KEY = "$env:USERPROFILE\.ssh\evolet_rsa"
$env:MSI_VM_PROJECT_ROOT = "/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc"
```

Jupyter runs on the VM at:

```text
127.0.0.1:8888
```

The local tunnel opens:

```text
http://127.0.0.1:8888
```

Latest local SSH check from this workstation timed out on port `22`. That means
VM routes are implemented, but remote operations need network/firewall/VPN
access before they can complete.

## Complete Backend Route Map

```text
GET  /health
POST /cohort/validate

GET  /vm/status
GET  /vm/files
POST /vm/upload
POST /vm/downloader/start
POST /vm/jupyter/start
POST /vm/tunnel/start
POST /vm/monte-carlo/workspace

POST /experiments/plan
POST /experiments/bootstrap
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

POST /approach-2/slides/register
GET  /approach-2/slides/
POST /approach-2/slides/upload_csv
POST /approach-2/pipeline/preprocess
POST /approach-2/pipeline/extract_features
POST /approach-2/pipeline/train
POST /approach-2/pipeline/predict
GET  /approach-2/experiments/
GET  /approach-2/experiments/{experiment_id}
POST /approach-2/webhook/start-automation
POST /approach-2/webhook/optuna/trial
```

OpenAPI docs:

```text
http://127.0.0.1:8001/docs
```

## Local Setup

### 1. Backend

Run in Windows PowerShell:

```powershell
cd E:\4basecare-MSI\Approach_1\apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Start the API:

```powershell
cd E:\4basecare-MSI\Approach_1\apps\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 2. Frontend

Run in Windows PowerShell:

```powershell
cd E:\4basecare-MSI\Approach_1\apps\web
npm.cmd install
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000
```

### 3. n8n

Run in Windows PowerShell:

```powershell
cd E:\4basecare-MSI\Approach_1
.\automation\n8n\start-local.ps1
```

Open:

```text
http://127.0.0.1:5678
```

Import workflows from:

```text
automation/n8n/
```

Recommended workflow order:

1. `Timestamp_msi live source check`
2. `Timestamp_msi SAFE connection check`
3. `Timestamp_msi integrations check`
4. `Timestamp_msi GDC 10 SVS batch`
5. `Timestamp_msi SAFE single trial launcher`
6. `Timestamp_msi Monte Carlo uncertainty pipeline`

## Validation Commands

Backend:

```powershell
cd E:\4basecare-MSI\Approach_1\apps\api
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall app
```

Frontend:

```powershell
cd E:\4basecare-MSI\Approach_1\apps\web
npm.cmd run lint
npm.cmd run build
```

Quick API checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-RestMethod http://127.0.0.1:8001/integrations/status
```

Quick Monte Carlo plan check:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8001/experiments/monte-carlo-plan `
  -ContentType "application/json" `
  -Body '{"samples":2,"random_seed":310,"folds":[1],"epoch_choices":[5],"seed_choices":[310]}'
```

## Safety Model

The browser must not become an open shell into the VM. VM actions are
allowlisted and implemented in backend services.

Allowlisted VM action families:

- status check
- limited project browsing
- annotation/manifest upload
- downloader startup
- Jupyter startup
- local tunnel startup
- Monte Carlo workspace preparation

Path browsing is restricted to configured project roots. Secrets are kept in
local `.env` files and are not returned by API responses.

Do not expose this local backend publicly without adding authentication,
authorization, request auditing, rate limits, and proper secret management.

## Important Files

Backend:

- `apps/api/app/main.py`: FastAPI app, CORS, health, route registration,
  Approach 2 mounting, artifact serving.
- `apps/api/app/core/config.py`: local `.env` settings and VM defaults.
- `apps/api/app/api/routes/vm.py`: VM action endpoints.
- `apps/api/app/services/vm.py`: SSH command construction and VM action logic.
- `apps/api/app/api/routes/experiments.py`: n8n experiment route surface.
- `apps/api/app/services/experiments.py`: experiment plan/bootstrap/start/status
  and best-result service logic.
- `apps/api/app/api/routes/monte_carlo.py`: Monte Carlo endpoints.
- `apps/api/app/services/monte_carlo.py`: random search, uncertainty, bootstrap
  CI, seed stability, stable-best logic.
- `apps/api/app/api/routes/integrations.py`: secret-safe integration status.
- `apps/api/app/services/data_batches.py`: GDC batch download/status/cleanup.
- `apps/api/app/approach_2`: imported Approach 2 backend package.

Frontend:

- `apps/web/src/components/msi-workbench.tsx`: main workstation UI.
- `apps/web/src/app/globals.css`: theme tokens and layout styling.
- `apps/web/public/assets/researching-cancer-msi-h.mp4`: hero media asset.
- `apps/web/src/components/recharts-distribution.tsx`: static chart wrapper.
- `apps/web/src/app/api/vm/route.ts`: legacy/local Next.js VM bridge.

Automation:

- `automation/n8n/start-local.ps1`: local n8n launcher.
- `automation/n8n/timestamp-msi-connection-check.json`: API/VM check.
- `automation/n8n/timestamp-msi-integrations-check.json`: provider status.
- `automation/n8n/timestamp-msi-gdc-10-svs-batch.json`: small GDC batch.
- `automation/n8n/timestamp-msi-modular-training.json`: training workflow.
- `automation/n8n/timestamp-msi-monte-carlo-pipeline.json`: MC workflow.

Configs:

- `configs/experiment_grid.example.json`: standard experiment grid example.
- `configs/monte_carlo_search.example.json`: random-search config example.

## Troubleshooting

### Frontend cannot reach backend

Check that the API is running:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

If the API runs on another port, set:

```powershell
$env:NEXT_PUBLIC_MSI_API_URL = "http://127.0.0.1:8001"
```

Then restart `npm.cmd run dev`.

### VM actions time out

Test SSH directly:

```powershell
ssh -i "$env:USERPROFILE\.ssh\evolet_rsa" pardeep@34.55.157.128
```

If port `22` times out, fix VM network/firewall/VPN access first. The app
cannot create remote folders or start remote jobs until SSH works.

### Jupyter does not open

Start Jupyter from the app or backend route first, then open the tunnel:

```text
Start Jupyter -> Open tunnel -> http://127.0.0.1:8888
```

### Integration shows missing

Add the key to `apps/api/.env`, restart FastAPI, then call:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/integrations/status
```

### SQLite database appears locally

Approach 2 uses SQLite by default when `DATABASE_URL` is not set. Local `.db`
files are ignored by git.

## Git And Publishing Notes

Current branch work has been happening on `hft-methods`.

Before publishing, inspect:

```powershell
git status --short --branch
git diff --stat
```

Do not commit:

- `.env`
- real API keys
- local SQLite databases
- node_modules
- `.venv`
- generated logs

## Current Local Verification Snapshot

Recent local checks passed:

```text
npm.cmd run lint
npm.cmd run build
.\.venv\Scripts\python.exe -m pytest
```

The frontend dev server is currently expected at:

```text
http://127.0.0.1:3000
```

The backend server is currently expected at:

```text
http://127.0.0.1:8001
```
