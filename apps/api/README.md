# Timestamp_msi API

FastAPI backend for the Timestamp_msi MSI-H vs MSS workstation.

This service gives the project a proper backend surface for:

- health checks
- annotation and GDC manifest validation
- label and fold distribution summaries
- VM status checks through SSH
- restricted VM project browsing
- uploading annotation and manifest files into the VM project
- starting the GDC downloader
- starting Jupyter on the VM
- opening the local Jupyter SSH tunnel
- preparing VM-side Hugging Face and Monte Carlo model-cache folders
- expanding n8n model/hyperparameter grids
- starting Slideflow experiment trials on the VM
- reading real trial status, logs, and completed metrics
- checking optional integration secrets without exposing values
- bootstrapping and running small GDC `.svs` batches on the VM
- serving the imported Approach 2 platform routes under `/approach-2/*`

The current Next.js frontend still has its own local route at
`apps/web/src/app/api/vm/route.ts`, but this backend is the cleaner long-term
API boundary. The frontend can later point to this service instead of keeping VM
logic inside the web app.

## Install

From `apps/api`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Open:

```text
http://127.0.0.1:8001/docs
```

## VM Configuration

Defaults match the local workstation flow:

```powershell
$env:MSI_VM_USER = "pardeep"
$env:MSI_VM_HOST = "34.55.157.128"
$env:MSI_VM_KEY = "$env:USERPROFILE\.ssh\evolet_rsa"
$env:MSI_VM_PROJECT_ROOT = "/home/pardeep/pathology310_projects/single_slide_morphology/project_1_slideflow_msi_tcga_crc"
```

The private key is never returned by the API. It is used server-side only.

Optional integration keys are read from local `.env` values:

```powershell
MSI_HF_TOKEN=<your-hugging-face-token>
MSI_GROQ_API_KEY=<your-groq-key>
MSI_ZERVE_API_KEY=<your-zerve-key>
MSI_FIRECRAWL_API_KEY=<your-firecrawl-key>
MSI_TINYFISH_API_KEY=<your-tinyfish-key>
```

Use `apps/api/.env.example` as the template. Never commit real tokens.

## Endpoints

```text
GET  /health
POST /cohort/validate
GET  /vm/status
GET  /vm/files?path=<allowed-vm-path>
POST /vm/upload
POST /vm/downloader/start
POST /vm/jupyter/start
POST /vm/tunnel/start
POST /vm/monte-carlo/workspace
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

## Current Integration Surface

- Approach 1 routes handle cohort validation, VM actions, GDC batches, and n8n
  training orchestration.
- Approach 2 routes are imported from `E:\4basecare-MSI\Approach-2\backend\app`
  and mounted under `/approach-2/*`.
- Monte Carlo is a distinct workflow exposed through `/experiments/*` plus
  `/vm/monte-carlo/workspace` for VM-side model cache setup.
- Integration status checks Hugging Face, Groq AI, Zerve AI, Firecrawl, and
  Tinyfish without returning secret values.

## Safety

The backend does not expose arbitrary shell execution. VM operations are
allowlisted, path browsing is restricted to the configured project folders, and
experiment endpoints only write known project files or run fixed VM runners
such as `scripts/run_n8n_msi_trial.py` and `scripts/run_gdc_svs_batch.py`. Run
this service locally unless you add authentication, authorization, audit
logging, and proper secret management.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```
