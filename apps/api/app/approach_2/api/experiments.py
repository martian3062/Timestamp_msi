from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database.setup import get_db
from ..database import models
from ..schemas import schemas

router = APIRouter()

@router.get("/", response_model=List[schemas.ExperimentResponse])
def list_experiments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Experiment).order_by(models.Experiment.created_at.desc()).offset(skip).limit(limit).all()

@router.get("/{experiment_id}", response_model=schemas.ExperimentResponse)
def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    exp = db.query(models.Experiment).filter(models.Experiment.experiment_id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return exp
