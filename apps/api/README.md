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
- expanding n8n model/hyperparameter grids
- starting Slideflow experiment trials on the VM
- reading real trial status, logs, and completed metrics

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
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
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
POST /experiments/bootstrap
POST /experiments/plan
POST /experiments/start
GET  /experiments/status/{trial_id}
GET  /experiments/best
```

## Safety

The backend does not expose arbitrary shell execution. VM operations are
allowlisted, path browsing is restricted to the configured project folders, and
experiment endpoints only write known project files or run the fixed
`scripts/run_n8n_msi_trial.py` VM runner. Run this service locally unless you
add authentication, authorization, audit logging, and proper secret management.

## Test

```powershell
pytest
```
