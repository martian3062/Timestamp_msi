# End-to-End MSI Prediction Platform

A production-level web application and deep learning pipeline for predicting Microsatellite Instability (MSI) status from colorectal cancer whole slide images (WSIs). It integrates **Slideflow** for robust pathology AI, **FastAPI** for backend API and task routing, **MLflow** for experiment tracking, and **Next.js** for an interactive, dark-mode research dashboard.

## System Architecture
* **Backend:** Python 3.10, FastAPI, Slideflow/PyTorch, PostgreSQL, MLflow, Hydra
* **Frontend:** Next.js (App Router), Tailwind CSS, TypeScript, shadcn/ui

## Setup Instructions

### 1. Prerequisites
- Docker Engine & Docker Compose
- If running on a GPU VM, ensure `nvidia-docker2` (or the NVIDIA Container Toolkit) is installed and configured in Docker.

### 2. Environment Configurations
Clone this repository and create a `.env` file for any secret tokens or database overrides. The `docker-compose.yml` mounts local directories for code and slide data:

```bash
mkdir -p data/slides
mkdir -p data/slideflow
```

*Note: You must place your raw `.svs` or `.ndpi` WSI files inside `data/slides`.*

### 3. Deploy Stack
To run the full stack (FastAPI, Next.js dashboard, PostgreSQL, and MLflow tracking server):

```bash
docker-compose up --build -d
```
You can access the services here:
- **Next.js Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **MLflow Tracking**: [http://localhost:5000](http://localhost:5000)

---

## Complete Workflow Pipeline

### 1. Data Ingestion & Registration
1. In the Dashboard (http://localhost:3000/datasets), click **Register Slides** to upload your WSI label mapping.
2. Example Labels CSV mapping format:
```csv
slide_id,patient_id,msi_status,cohort,magnification
Slide_CRC_101,P_001,MSI-H,TCGA-CRC,40.0
Slide_CRC_102,P_002,MSS,TCGA-CRC,20.0
```

### 2. Job 1: Preprocessing (Tiling)
- Trigger preprocessing via the API or Frontend to extract tiled image patches from the `.svs` files.
- Command for manual triggering:
  `curl -X POST http://localhost:8000/pipeline/preprocess -H "Content-Type: application/json" -d '{"cohort": "TCGA-CRC", "tile_size": 256}'`

### 3. Job 2: Feature Extraction
- The platform uses `sf.build_feature_extractor` which downloads/uses models like ResNet50 (or CTransPath) to convert image tiles to feature embeddings (bags).
- Trigger:
  `curl -X POST http://localhost:8000/pipeline/extract_features -H "Content-Type: application/json" -d '{"cohort": "TCGA-CRC", "feature_extractor": "resnet50"}'`

### 4. Job 3: Training an MIL Model for MSI Prediction
- Trains an Attention-MIL / TransMIL model directly on the embedded bags.
- Tracks metrics straight into MLflow. Hyperparameters are governed by `configs/hydra/model/attention_mil.yaml`.
- Trigger:
  `curl -X POST http://localhost:8000/pipeline/train -H "Content-Type: application/json" -d '{"experiment_name": "Resnet50_Attn", "epochs": 15, "batch_size": 16}'`

### 5. Job 4: Inference
- Deploys highly-rated models in the registry to evaluate unlabelled WSIs and generate diagnostic **Attention Heatmaps** visualizing tumor regions associated with MSI-H phenotype.

---

## Modifying Remote VM Execution
If this repository is run directly on your VM:
1. SSH into the VM: `ssh -i "%USERPROFILE%\.ssh\evolet_rsa" pardeep@34.55.157.128`
2. Clone/Copy this repository onto the VM.
3. Depending on your GPU node sizes, configure the `docker-compose.yml` backend service to use the `deploy.resources.reservations.devices` block specifying `driver: nvidia`.
