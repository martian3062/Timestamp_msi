from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class SlideBase(BaseModel):
    slide_id: str
    patient_id: str
    msi_status: str
    cohort: Optional[str] = "default"
    magnification: Optional[float] = None

class SlideCreate(SlideBase):
    file_path: Optional[str] = None

class SlideResponse(SlideBase):
    id: int
    status: str
    file_path: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PipelinePreprocessRequest(BaseModel):
    cohort: str = "default"
    tile_size: int = 256
    tile_um: int = 256

class PipelineFeaturesRequest(BaseModel):
    cohort: str = "default"
    feature_extractor: str = "resnet50" # resnet50, virchow, ctranspath

class TrainMilRequest(BaseModel):
    experiment_name: str
    model_type: str = "attention_mil"
    epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 1e-4

class ExperimentResponse(BaseModel):
    id: int
    experiment_id: str
    name: str
    status: str
    model_type: str
    metrics: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class PredictRequest(BaseModel):
    slide_id: str
    model_version: str

class PredictResponse(BaseModel):
    prediction: str
    probability: float
    heatmap_path: Optional[str] = None
    error: Optional[str] = None
