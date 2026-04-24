# Timestamp_msi Automation

This folder contains the n8n entrypoint for modular MSI model sweeps.

The orchestration is split on purpose:

- n8n decides when to run trials and how many to queue.
- FastAPI expands the model/hyperparameter grid and exposes safe endpoints.
- The pathology VM runs the actual Slideflow training.
- Metrics are read from real prediction files only. Missing predictions fail a
  trial instead of creating fake accuracy.

## Local Services

Start the API:

```powershell
cd apps\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Start n8n with the pinned local launcher. The latest `npx n8n` package can fail
on this Windows/Node setup, so this script uses `1.114.4`:

```powershell
cd E:\4basecare-MSI\Approach_1
.\automation\n8n\start-local.ps1
```

Open:

```text
http://127.0.0.1:5678
```

Import:

```text
automation/n8n/timestamp-msi-modular-training.json
```

Or import from PowerShell:

```powershell
npx --yes n8n@1.114.4 import:workflow --input=automation\n8n\timestamp-msi-modular-training.json
```

## API Flow Used By n8n

Bootstrap the VM runner script:

```http
POST http://127.0.0.1:8001/experiments/bootstrap
```

Build the trial grid:

```http
POST http://127.0.0.1:8001/experiments/plan
```

Body:

```json
{
  "feature_extractors": ["resnet50_imagenet", "uni", "uni_v2"],
  "mil_models": ["attention_mil", "transmil"],
  "learning_rates": [0.0001, 0.00005],
  "epochs": [10, 20],
  "seeds": [310],
  "folds": [1, 2, 3, 4, 5],
  "primary_metric": "mean_auroc",
  "metric_direction": "max",
  "max_trials": 24
}
```

Start one trial:

```http
POST http://127.0.0.1:8001/experiments/start
```

Check one trial:

```http
GET http://127.0.0.1:8001/experiments/status/trial_id_here
```

Select the best completed trial:

```http
GET http://127.0.0.1:8001/experiments/best?primary_metric=mean_auroc&metric_direction=max
```

## Remote VM Files

The bootstrap endpoint writes this runner on the VM:

```text
scripts/run_n8n_msi_trial.py
```

Each n8n trial writes under:

```text
automation/trials/<trial_id>/trial.json
automation/logs/<trial_id>.log
automation/status/<trial_id>.json
automation/results/<trial_id>/metrics.json
```

## First Sweep Recommendation

Start small before launching the full grid:

```json
{
  "feature_extractors": ["resnet50_imagenet"],
  "mil_models": ["attention_mil"],
  "learning_rates": [0.0001],
  "epochs": [5],
  "seeds": [310],
  "folds": [1],
  "primary_metric": "mean_auroc",
  "metric_direction": "max",
  "max_trials": 1
}
```

After that succeeds, increase folds to `[1, 2, 3, 4, 5]`, then widen models,
feature extractors, learning rates, and epochs.
