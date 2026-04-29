from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from ..database.setup import get_db
from ..database import models
from ..schemas import schemas
from ..pipelines import project_setup, feature_extractor, mil_trainer

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
    import uuid
    exp_id = str(uuid.uuid4())[:8]
    
    new_exp = models.Experiment(
        experiment_id=exp_id,
        name=req.experiment_name,
        model_type=req.model_type,
        status="running",
        parameters={"epochs": req.epochs, "batch_size": req.batch_size, "lr": req.learning_rate}
    )
    db.add(new_exp)
    db.commit()
    db.refresh(new_exp)
    
    background_tasks.add_task(mil_trainer.run_mil_training, exp_id, req.dict())
    
    return new_exp

@router.post("/predict", response_model=schemas.PredictResponse)
def predict_slide(req: schemas.PredictRequest, db: Session = Depends(get_db)):
    """Run prediction on a single slide synchronously and return heatmap path."""
    from ..pipelines import inference
    result = inference.run_inference(req.slide_id, req.model_version)
    return result
