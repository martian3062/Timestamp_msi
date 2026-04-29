import os
import pandas as pd
try:
    import slideflow as sf
except ImportError:
    sf = None  # Mock if slideflow is not installed during local dev

from ..database.setup import SessionLocal
from ..database import models

DATA_DIR = "/data/slideflow"
WSI_DIR = "/data/slides"

def run_preprocessing(cohort: str, tile_size: int, tile_um: int):
    print(f"Starting preprocessing for cohort: {cohort}")
    if not sf:
        print("Slideflow not available. Preprocessing mocked.")
        return
        
    os.makedirs(DATA_DIR, exist_ok=True)
    P = sf.Project(DATA_DIR)
    
    # Generate annotations file from Database
    db = SessionLocal()
    slides = db.query(models.Slide).filter(models.Slide.cohort == cohort).all()
    
    # Create annotations dataframe expected by Slideflow
    data = []
    for s in slides:
        data.append({"slide": s.slide_id, "patient": s.patient_id, "msi_status": s.msi_status})
    df = pd.DataFrame(data)
    annotations_path = os.path.join(DATA_DIR, "annotations.csv")
    df.to_csv(annotations_path, index=False)
    
    P.annotations = annotations_path
    P.add_source('msi_dataset', slides=WSI_DIR, roi=None, 
                 filters={"cohort": cohort})

    print("Extracting tiles...")
    dataset = P.dataset(tile_px=tile_size, tile_um=tile_um)
    dataset.extract_tiles(qc='otsu')
    
    print("Preprocessing completed.")
    db.close()
