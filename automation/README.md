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

Open API docs:

```text
http://127.0.0.1:8001/docs
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

Import and run this workflow first:

```text
automation/n8n/timestamp-msi-connection-check.json
```

It appears in n8n as `Timestamp_msi SAFE connection check`. This checks the
API, VM SSH status, VM runner bootstrap, trial-plan creation, and current best
result without starting GPU training.

Then import the single-trial launcher:

```text
automation/n8n/timestamp-msi-modular-training.json
```

It appears in n8n as `Timestamp_msi SAFE single trial launcher`. This starts
only one small trial: `resnet50_imagenet`, `attention_mil`, `lr=0.0001`,
`epochs=5`, and `fold=1`.

Additional workflows:

```text
automation/n8n/timestamp-msi-integrations-check.json
automation/n8n/timestamp-msi-gdc-10-svs-batch.json
automation/n8n/timestamp-msi-live-source-check.json
```

`Timestamp_msi integrations check` reports whether Hugging Face, Groq AI,
Zerve AI, Firecrawl, and Tinyfish keys are configured without printing the key
values.

`Timestamp_msi GDC 10 SVS batch` bootstraps a VM batch downloader and starts the
next 10 open TCGA-COAD/READ diagnostic SVS downloads. Its cleanup node is
disabled by default; enable it only after output files from the batch are saved.

`Timestamp_msi live source check` calls live public GDC and cBioPortal health
endpoints. Use it to confirm n8n can reach external data sources, not just local
project APIs.

## Workflow Safety

These workflows do not start GPU training:

- `Timestamp_msi live source check`
- `Timestamp_msi SAFE connection check`
- `Timestamp_msi integrations check`

This workflow downloads data to the VM:

- `Timestamp_msi GDC 10 SVS batch`

This workflow starts a real GPU training trial:

- `Timestamp_msi SAFE single trial launcher`

Avoid the older imported workflows without `SAFE` in the name. They may contain
broader grids from earlier iterations.

Or import from PowerShell:

```powershell
npx --yes n8n@1.114.4 import:workflow --input=automation\n8n\timestamp-msi-modular-training.json
npx --yes n8n@1.114.4 import:workflow --input=automation\n8n\timestamp-msi-integrations-check.json
npx --yes n8n@1.114.4 import:workflow --input=automation\n8n\timestamp-msi-gdc-10-svs-batch.json
npx --yes n8n@1.114.4 import:workflow --input=automation\n8n\timestamp-msi-live-source-check.json
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

## 10-SVS Batch Loop

The intended storage-safe loop is:

1. Run `Timestamp_msi GDC 10 SVS batch`.
2. Wait until `/data-batches/gdc/status` reports downloaded slides.
3. Run feature extraction or training for that batch.
4. Confirm batch outputs are saved under the VM project `output/` or
   `automation/results/` folders.
5. Enable/run cleanup to delete temporary `.svs` and `.part` files.
6. Repeat for the next 10 slides.

The source of truth for real WSI files is GDC open TCGA-COAD/READ diagnostic
SVS data. The source of truth for MSI labels is cBioPortal
`coadread_tcga_pan_can_atlas_2018`.
