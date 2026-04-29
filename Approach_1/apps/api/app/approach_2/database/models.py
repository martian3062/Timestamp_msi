from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from datetime import datetime
from .setup import Base

class Slide(Base):
    __tablename__ = "slides"
    id = Column(Integer, primary_key=True, index=True)
    slide_id = Column(String, unique=True, index=True)
    patient_id = Column(String, index=True)
    msi_status = Column(String, index=True) # "MSI-H" or "MSS"
    cohort = Column(String, default="default")
    magnification = Column(Float, nullable=True)
    file_path = Column(String, nullable=True) # Remote or local file path
    status = Column(String, default="registered") # "registered", "tiled", "features_extracted", "error"
    created_at = Column(DateTime, default=datetime.utcnow)

class Experiment(Base):
    __tablename__ = "experiments"
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(String, unique=True, index=True)
    name = Column(String)
    status = Column(String, default="running") # "running", "completed", "failed"
    model_type = Column(String) # e.g. "attention_mil"
    parameters = Column(JSON, nullable=True) # JSON config snapshot
    metrics = Column(JSON, nullable=True) # JSON dict of AUC, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
