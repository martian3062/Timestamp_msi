from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any, Literal
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
    training_mode: Literal["mil", "patch_classification"] = "mil"
    approach_label: Literal["Approach1", "Approach2"] = "Approach2"
    dataset_source: Literal["workspace_root", "custom_path", "google_bucket"] = "workspace_root"
    workspace_root: Optional[str] = r"E:\4basecare-MSI"
    google_bucket_uri: Optional[str] = None
    model_type: str = "attention_mil"
    epochs: int = 10
    batch_size: int = 32
    learning_rate: float = 1e-4
    dataset_path: Optional[str] = None
    val_split: float = 0.2
    image_size: int = 224
    backbone: str = "resnet18"
    num_workers: int = 0
    output_dir: Optional[str] = None
    seed: int = 310
    use_pretrained: bool = True
    max_samples_per_class: Optional[int] = None

class ExperimentResponse(BaseModel):
    id: int
    experiment_id: str
    name: str
    status: str
    model_type: str
    metrics: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class PredictRequest(BaseModel):
    slide_id: str
    model_version: str


class TriadRunResponse(BaseModel):
    ok: bool = True
    message: str
    experiment_ids: List[str]


class TCGASlideTriadRequest(BaseModel):
    experiment_name: str = "tcga-coad-dx1-single-system"
    bucket_uri: str = "gs://wsi_aiml_repo/TCGA/TCGA_COAD/TCGA_COAD"
    slide_limit: int = 110
    n_folds: int = 2
    preferred_slide_pattern: str = "DX"
    preferred_exact_suffix: str = "DX1"
    annotations_csv: Optional[str] = "annotations/tcga_coad_bucket_annotations_final_all3_live_dx1.csv"
    feature_extractor: str = "ctranspath"
    tile_px: int = 256
    tile_um: int = 128
    max_parallel_approaches: int = 2


class TCGASlideTriadRunResponse(BaseModel):
    ok: bool = True
    message: str
    bundle_id: str
    experiment_ids: List[str]
    remote_status_path: str


class TCGASlideTriadStatusResponse(BaseModel):
    ok: bool = True
    bundle_id: str
    remote_status_path: str
    status: Dict[str, Any]


class LatestTCGASlideTriadStatusResponse(BaseModel):
    ok: bool = True
    bundle_id: str
    remote_status_path: str
    status: Dict[str, Any]


class LatestTCGABatchArchiveResponse(BaseModel):
    ok: bool = True
    archive_root: str
    summary: Dict[str, Any]


class UploadPredictResponse(BaseModel):
    experiment_id: str
    approach_label: str
    prediction: str
    probability: float
    probabilities: Dict[str, float]
    model_path: Optional[str] = None

class PredictResponse(BaseModel):
    prediction: str
    probability: float
    heatmap_path: Optional[str] = None
    error: Optional[str] = None
