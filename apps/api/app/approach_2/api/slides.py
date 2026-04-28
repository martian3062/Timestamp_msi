from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
from io import BytesIO

from ..database.setup import get_db
from ..database import models
from ..schemas import schemas

router = APIRouter()

@router.post("/register", response_model=schemas.SlideResponse)
def register_slide(slide: schemas.SlideCreate, db: Session = Depends(get_db)):
    db_slide = db.query(models.Slide).filter(models.Slide.slide_id == slide.slide_id).first()
    if db_slide:
        raise HTTPException(status_code=400, detail="Slide already registered")
    
    new_slide = models.Slide(**slide.model_dump())
    db.add(new_slide)
    db.commit()
    db.refresh(new_slide)
    return new_slide

@router.get("/", response_model=List[schemas.SlideResponse])
def list_slides(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Slide).offset(skip).limit(limit).all()

@router.post("/upload_csv")
async def upload_labels_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")
    
    contents = await file.read()
    df = pd.read_csv(BytesIO(contents))
    
    required_cols = {'slide_id', 'patient_id', 'msi_status'}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"CSV must contain columns: {required_cols}")
        
    added = 0
    for _, row in df.iterrows():
        db_slide = db.query(models.Slide).filter(models.Slide.slide_id == str(row['slide_id'])).first()
        if not db_slide:
            new_slide = models.Slide(
                slide_id=str(row['slide_id']),
                patient_id=str(row['patient_id']),
                msi_status=str(row['msi_status']),
                cohort=str(row.get('cohort', 'default')),
                magnification=float(row.get('magnification', 40.0) if not pd.isna(row.get('magnification')) else 40.0)
            )
            db.add(new_slide)
            added += 1
            
    db.commit()
    return {"message": f"Successfully parsed CSV and registered {added} slides"}
