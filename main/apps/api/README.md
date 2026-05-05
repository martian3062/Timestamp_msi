# Timestamp_msi API

This FastAPI app is now the lean backend for the single DX1 TCGA MSI system.

The current entrypoint is `app/main.py`, and it mounts only:

- `/health`
- `/vm/*`
- `/approach-2/pipeline/*`
- `/approach-2/artifacts`

Older route modules still exist in the repo, but they are not mounted by the
current backend entrypoint unless you wire them back in manually.

## Mounted Endpoints

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
```

## Main Responsibilities

- expose a clean health check for the Next.js dashboard
- manage VM utility actions through allowlisted SSH calls
- queue the TCGA DX1 bundle runner
- read the latest remote TCGA bundle status
- read the latest local/archived TCGA batch summary
- keep Approach 2 experiment metadata in the local SQLAlchemy database
- support the older CRC patch-classification training/prediction path

## Important Files

- `app/main.py`: actual mounted app surface
- `app/api/routes/vm.py`: VM utility endpoints
- `app/services/vm.py`: SSH action implementation
- `app/approach_2/api/pipeline.py`: active Approach 2 pipeline routes
- `app/approach_2/services/triad_runtime.py`: TCGA bundle and CRC patch runtime
- `app/approach_2/schemas/schemas.py`: request/response models
- `app/approach_2/database/models.py`: experiment registry model
- `app/approach_2/database/setup.py`: database setup

## VM Defaults

```powershell
$env:MSI_VM_USER = "<vm-user>"
$env:MSI_VM_HOST = "<vm-host>"
$env:MSI_VM_KEY = "<path-to-ssh-key>"
$env:MSI_VM_PROJECT_ROOT = "/path/to/project/root"
```

## Install

```powershell
cd <repo-root>\main\apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run

```powershell
cd <repo-root>\main\apps\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Open:

```text
http://127.0.0.1:8001/docs
```

## Validation

```powershell
cd <repo-root>\main\apps\api
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m compileall app
```

## Safety

This service is intended for local use. VM actions are allowlisted and tied to
known project paths, but the API should still not be exposed publicly without
auth, audit logging, and secret management.
