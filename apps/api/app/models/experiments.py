from typing import Literal

from pydantic import BaseModel, Field


MetricDirection = Literal["max", "min"]


class ExperimentGridRequest(BaseModel):
    feature_extractors: list[str] = Field(
        default_factory=lambda: ["resnet50_imagenet", "uni", "uni_v2"]
    )
    mil_models: list[str] = Field(default_factory=lambda: ["attention_mil", "transmil"])
    learning_rates: list[float] = Field(default_factory=lambda: [1e-4, 5e-5])
    epochs: list[int] = Field(default_factory=lambda: [10, 20])
    seeds: list[int] = Field(default_factory=lambda: [310])
    folds: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    primary_metric: str = "mean_auroc"
    metric_direction: MetricDirection = "max"
    max_trials: int = 48


class ExperimentTrial(BaseModel):
    trial_id: str
    feature_extractor: str
    mil_model: str
    learning_rate: float
    epochs: int
    seed: int
    folds: list[int]
    primary_metric: str = "mean_auroc"
    metric_direction: MetricDirection = "max"


class ExperimentPlanResponse(BaseModel):
    trial_count: int
    primary_metric: str
    metric_direction: MetricDirection
    trials: list[ExperimentTrial]


class ExperimentRunRequest(BaseModel):
    trial: ExperimentTrial


class ExperimentActionResponse(BaseModel):
    ok: bool = True
    action: str
    trial_id: str | None = None
    stdout: str = ""
    stderr: str = ""


class ExperimentStatusResponse(ExperimentActionResponse):
    running: bool = False
    status_json: dict | None = None
    metrics_json: dict | None = None
    log_tail: str = ""


class ExperimentMetric(BaseModel):
    trial_id: str
    metric: str
    value: float
    metrics: dict


class BestExperimentResponse(BaseModel):
    ok: bool = True
    primary_metric: str
    metric_direction: MetricDirection
    best: ExperimentMetric | None = None
    completed_trials: int
