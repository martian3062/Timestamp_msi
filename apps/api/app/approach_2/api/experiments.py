from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database.setup import get_db
from ..database import models
from ..schemas import schemas
from ..services.experiment_labels import classify_experiment, normalize_approach_label

router = APIRouter()

@router.get("/", response_model=List[schemas.ExperimentResponse])
def list_experiments(
    skip: int = 0,
    limit: int = 100,
    approach_label: str | None = None,
    db: Session = Depends(get_db),
):
    experiments = (
        db.query(models.Experiment)
        .order_by(models.Experiment.created_at.desc())
        .all()
    )
    if approach_label:
        target = normalize_approach_label(approach_label)
        experiments = [
            exp
            for exp in experiments
            if classify_experiment(
                name=exp.name,
                model_type=exp.model_type,
                parameters=exp.parameters if isinstance(exp.parameters, dict) else None,
                metrics=exp.metrics if isinstance(exp.metrics, dict) else None,
            )
            == target
        ]
    return experiments[skip : skip + limit]

@router.get("/{experiment_id}", response_model=schemas.ExperimentResponse)
def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    exp = db.query(models.Experiment).filter(models.Experiment.experiment_id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp
