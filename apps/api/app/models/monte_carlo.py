"""Pydantic schemas for Monte Carlo experiment methods.

Covers:
  - Monte Carlo random hyperparameter search plan
  - MC dropout inference-time uncertainty estimation
  - Bootstrap confidence interval computation
  - Stability-weighted best model selection
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MetricDirection = Literal["max", "min"]


# ---------------------------------------------------------------------------
# 1. Monte Carlo random search plan
# ---------------------------------------------------------------------------

class MonteCarloSearchRequest(BaseModel):
    """Random hyperparameter sampling instead of exhaustive grid."""
    feature_extractors: list[str] = Field(
        default_factory=lambda: ["resnet50_imagenet", "uni", "uni_v2"]
    )
    mil_models: list[str] = Field(
        default_factory=lambda: ["attention_mil", "transmil"]
    )
    learning_rate_min: float = 1e-5
    learning_rate_max: float = 3e-4
    dropout_min: float = 0.1
    dropout_max: float = 0.5
    weight_decay_min: float = 1e-6
    weight_decay_max: float = 1e-3
    epoch_choices: list[int] = Field(default_factory=lambda: [5, 10, 20])
    seed_choices: list[int] = Field(
        default_factory=lambda: [310, 311, 312, 313, 314]
    )
    folds: list[int] = Field(default_factory=lambda: [1])
    samples: int = Field(default=8, ge=1, le=64)
    random_seed: int = 310
    primary_metric: str = "mean_auroc"
    metric_direction: MetricDirection = "max"
    rank_formula: str = "mean_auroc - 0.5 * sd_auroc"


class MonteCarloTrial(BaseModel):
    """One randomly sampled trial configuration."""
    trial_id: str
    feature_extractor: str
    mil_model: str
    learning_rate: float
    dropout: float
    weight_decay: float
    epochs: int
    seed: int
    folds: list[int]
    primary_metric: str = "mean_auroc"
    metric_direction: MetricDirection = "max"


class MonteCarloSearchResponse(BaseModel):
    """Response listing all randomly sampled trials."""
    trial_count: int
    random_seed: int
    rank_formula: str
    primary_metric: str
    metric_direction: MetricDirection
    trials: list[MonteCarloTrial]


# ---------------------------------------------------------------------------
# 2. MC Dropout uncertainty estimation
# ---------------------------------------------------------------------------

class MCDropoutRequest(BaseModel):
    """Request to run MC dropout inference on a trained model."""
    trial_id: str
    forward_passes: int = Field(default=30, ge=5, le=100)
    dropout_rate: float = Field(default=0.25, ge=0.05, le=0.8)


class SlideUncertainty(BaseModel):
    """Per-slide uncertainty from MC dropout."""
    slide_id: str
    mean_msi_probability: float
    std_uncertainty: float
    confidence: str  # "high", "medium", "low"
    n_passes: int


class MCDropoutResponse(BaseModel):
    """Aggregated MC dropout results for a trial."""
    ok: bool = True
    trial_id: str
    forward_passes: int
    dropout_rate: float
    slide_count: int
    mean_uncertainty: float
    high_confidence_pct: float
    medium_confidence_pct: float
    low_confidence_pct: float
    slides: list[SlideUncertainty]


# ---------------------------------------------------------------------------
# 3. Bootstrap confidence intervals
# ---------------------------------------------------------------------------

class BootstrapCIRequest(BaseModel):
    """Request to compute bootstrap CIs for a completed trial."""
    trial_id: str
    n_bootstrap: int = Field(default=1000, ge=100, le=10000)
    ci_level: float = Field(default=0.95, ge=0.80, le=0.99)


class MetricCI(BaseModel):
    """One metric with bootstrap confidence interval."""
    metric: str
    point_estimate: float
    ci_lower: float
    ci_upper: float
    ci_level: float
    std_error: float


class BootstrapCIResponse(BaseModel):
    """Bootstrap CI results for all metrics of a trial."""
    ok: bool = True
    trial_id: str
    n_bootstrap: int
    ci_level: float
    metrics: list[MetricCI]


# ---------------------------------------------------------------------------
# 4. Repeated seed stability analysis
# ---------------------------------------------------------------------------

class SeedStabilityRequest(BaseModel):
    """Analyse variance across repeated seed trainings."""
    trial_ids: list[str] = Field(
        ..., min_length=2, description="Trial IDs trained with different seeds"
    )
    primary_metric: str = "mean_auroc"


class SeedStabilityResult(BaseModel):
    """Aggregated stability results across seeds."""
    primary_metric: str
    trial_count: int
    mean_value: float
    std_value: float
    min_value: float
    max_value: float
    stability_score: float  # mean - 0.5 * std
    per_trial: list[dict]  # [{trial_id, seed, value, ...}]


class SeedStabilityResponse(BaseModel):
    """Response with seed stability analysis."""
    ok: bool = True
    result: SeedStabilityResult


# ---------------------------------------------------------------------------
# 5. Stable best model selection
# ---------------------------------------------------------------------------

class StableBestRequest(BaseModel):
    """Find the best model using stability-weighted scoring."""
    rank_formula: str = "mean_auroc - 0.5 * sd_auroc"
    min_completed_folds: int = 1


class StableBestCandidate(BaseModel):
    """One candidate with stability score."""
    trial_id: str
    mean_auroc: float
    sd_auroc: float
    mean_auprc: float
    sd_auprc: float
    stability_score: float
    folds_completed: int
    feature_extractor: str = ""
    mil_model: str = ""
    epochs: int = 0
    seed: int = 0


class StableBestResponse(BaseModel):
    """Response with ranked candidates by stability score."""
    ok: bool = True
    rank_formula: str
    candidates: list[StableBestCandidate]
    best: StableBestCandidate | None = None
    total_evaluated: int


# ---------------------------------------------------------------------------
# 6. Action responses
# ---------------------------------------------------------------------------

class MonteCarloActionResponse(BaseModel):
    """Generic action response for MC operations."""
    ok: bool = True
    action: str
    trial_id: str | None = None
    stdout: str = ""
    stderr: str = ""
