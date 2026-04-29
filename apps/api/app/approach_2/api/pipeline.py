import uuid

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..database.setup import get_db
from ..database import models
from ..schemas import schemas
from ..pipelines import feature_extractor, mil_trainer, patch_trainer, project_setup
from ..services import triad_runtime

router = APIRouter()

@router.post("/preprocess")
def trigger_preprocessing(req: schemas.PipelinePreprocessRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Background task to setup slideflow project and extract tiles."""
    background_tasks.add_task(project_setup.run_preprocessing, req.cohort, req.tile_size, req.tile_um)
    return {"message": "Preprocessing started in background", "cohort": req.cohort}

@router.post("/extract_features")
def trigger_feature_extraction(req: schemas.PipelineFeaturesRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Background task to extract features from tiles using a given feature extractor."""
    background_tasks.add_task(feature_extractor.run_feature_extraction, req.cohort, req.feature_extractor)
    return {"message": f"Feature extraction using {req.feature_extractor} started in background"}

@router.post("/train", response_model=schemas.ExperimentResponse)
def trigger_mil_training(req: schemas.TrainMilRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
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
        message="CRC complex triad queued on the VM using the full CRC-VAL-HE-7K class tree.",
        experiment_ids=[str(spec["experiment_id"]) for spec in triad_specs],
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
