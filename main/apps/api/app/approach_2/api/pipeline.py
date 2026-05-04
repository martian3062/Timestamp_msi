import uuid

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..database.setup import get_db
from ..database import models
from ..schemas import schemas
from ..services import triad_runtime

router = APIRouter()

@router.post("/preprocess")
def trigger_preprocessing(req: schemas.PipelinePreprocessRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Background task to setup slideflow project and extract tiles."""
    from ..pipelines import project_setup

    background_tasks.add_task(project_setup.run_preprocessing, req.cohort, req.tile_size, req.tile_um)
    return {"message": "Preprocessing started in background", "cohort": req.cohort}

@router.post("/extract_features")
def trigger_feature_extraction(req: schemas.PipelineFeaturesRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Background task to extract features from tiles using a given feature extractor."""
    from ..pipelines import feature_extractor

    background_tasks.add_task(feature_extractor.run_feature_extraction, req.cohort, req.feature_extractor)
    return {"message": f"Feature extraction using {req.feature_extractor} started in background"}

@router.post("/train", response_model=schemas.ExperimentResponse)
def trigger_mil_training(req: schemas.TrainMilRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from ..pipelines import mil_trainer, patch_trainer

    exp_id = str(uuid.uuid4())[:8]
    
    new_exp = models.Experiment(
        experiment_id=exp_id,
        name=req.experiment_name,
        model_type=req.training_mode if req.training_mode != "mil" else req.model_type,
        status="running",
        parameters=req.model_dump()
    )
    db.add(new_exp)
    db.commit()
    db.refresh(new_exp)
    
    if req.training_mode == "patch_classification":
        if req.dataset_source == "google_bucket":
            spec = triad_runtime.build_single_patch_spec(req.model_dump(), exp_id)
            background_tasks.add_task(triad_runtime.run_single_vm_patch_experiment, spec)
        else:
            background_tasks.add_task(patch_trainer.run_patch_training, exp_id, req.model_dump())
    else:
        background_tasks.add_task(mil_trainer.run_mil_training, exp_id, req.model_dump())
    
    return new_exp


@router.post("/train-triad", response_model=schemas.TriadRunResponse)
def trigger_crc_triad(req: schemas.TrainMilRequest, background_tasks: BackgroundTasks) -> schemas.TriadRunResponse:
    triad_specs = triad_runtime.build_triad_specs(req.model_dump())
    for spec in triad_specs:
        spec["experiment_id"] = str(uuid.uuid4())[:8]
    triad_runtime.enqueue_triad_experiments(triad_specs)
    background_tasks.add_task(triad_runtime.run_crc_triad_bundle, triad_specs)
    return schemas.TriadRunResponse(
        message="CRC two-approach runner queued on the VM using the full CRC-VAL-HE-7K class tree.",
        experiment_ids=[str(spec["experiment_id"]) for spec in triad_specs],
    )


@router.post("/train-tcga-slide-triad", response_model=schemas.TCGASlideTriadRunResponse)
def trigger_tcga_slide_triad(
    req: schemas.TCGASlideTriadRequest,
    background_tasks: BackgroundTasks,
) -> schemas.TCGASlideTriadRunResponse:
    bundle_id, triad_specs = triad_runtime.build_tcga_slide_triad_specs(req.model_dump())
    triad_runtime.enqueue_triad_experiments(triad_specs)
    background_tasks.add_task(triad_runtime.run_tcga_slide_triad_bundle, bundle_id, req.model_dump(), triad_specs)
    return schemas.TCGASlideTriadRunResponse(
        message="TCGA COAD two-approach runner queued on the VM. Matching annotations, downloading slides, preprocessing, pathology-first feature fallback, and two-approach training will run automatically.",
        bundle_id=bundle_id,
        experiment_ids=[str(spec["experiment_id"]) for spec in triad_specs],
        remote_status_path=triad_runtime.tcga_slide_triad_status_path(bundle_id),
    )


@router.get("/train-tcga-slide-triad-latest", response_model=schemas.LatestTCGASlideTriadStatusResponse)
def get_latest_tcga_slide_triad_status() -> schemas.LatestTCGASlideTriadStatusResponse:
    payload = triad_runtime.read_latest_tcga_slide_triad_status()
    return schemas.LatestTCGASlideTriadStatusResponse(
        bundle_id=str(payload.get("bundle_id") or ""),
        remote_status_path=str(payload.get("remote_status_path") or ""),
        status=payload.get("status") if isinstance(payload.get("status"), dict) else {},
    )


@router.get("/tcga-batch-archive-latest", response_model=schemas.LatestTCGABatchArchiveResponse)
def get_latest_tcga_batch_archive_summary() -> schemas.LatestTCGABatchArchiveResponse:
    payload = triad_runtime.read_latest_tcga_batch_archive_summary()
    return schemas.LatestTCGABatchArchiveResponse(
        archive_root=str(payload.get("archive_root") or ""),
        summary=payload.get("summary") if isinstance(payload.get("summary"), dict) else {},
    )


@router.get("/train-tcga-slide-triad/{bundle_id}", response_model=schemas.TCGASlideTriadStatusResponse)
def get_tcga_slide_triad_status(bundle_id: str) -> schemas.TCGASlideTriadStatusResponse:
    return schemas.TCGASlideTriadStatusResponse(
        bundle_id=bundle_id,
        remote_status_path=triad_runtime.tcga_slide_triad_status_path(bundle_id),
        status=triad_runtime.read_tcga_slide_triad_status(bundle_id),
    )

@router.post("/predict", response_model=schemas.PredictResponse)
def predict_slide(req: schemas.PredictRequest, db: Session = Depends(get_db)):
    """Run prediction on a single slide synchronously and return heatmap path."""
    from ..pipelines import inference
    result = inference.run_inference(req.slide_id, req.model_version)
    return result


@router.post("/predict-upload", response_model=schemas.UploadPredictResponse)
async def predict_uploaded_patch(
    file: UploadFile = File(...),
    experiment_id: str | None = Form(default=None),
    approach_label: str = Form(default="Approach2"),
) -> schemas.UploadPredictResponse:
    payload = triad_runtime.predict_uploaded_patch(
        file_bytes=await file.read(),
        filename=file.filename or "uploaded_patch.tif",
        experiment_id=experiment_id,
        approach_label=approach_label,
    )
    return schemas.UploadPredictResponse(**payload)
