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
DEFAULT_STABLE_RANK_FORMULA = (
    "0.40 * mean_auroc + 0.25 * mean_auprc + 0.15 * balanced_accuracy + "
    "0.10 * msi_h_sensitivity + 0.10 * calibration_score - 0.20 * seed_std"
)


# ---------------------------------------------------------------------------
# 1. Monte Carlo random search plan
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 1. Hyperparameter Sub-Configs
# ---------------------------------------------------------------------------

class DataConfig(BaseModel):
    split_type: str = "patient_level"
    num_folds: list[int] = Field(default_factory=lambda: [3, 5])
    test_size: list[float] = Field(default_factory=lambda: [0.15, 0.20, 0.25])
    val_size: list[float] = Field(default_factory=lambda: [0.10, 0.15, 0.20])
    stratify_by_label: bool = True
    stratify_by_site: list[bool] = Field(default_factory=lambda: [True, False])
    min_slides_per_class: list[int] = Field(default_factory=lambda: [10, 20, 30])
    class_balance_strategy: list[str] = Field(default_factory=lambda: ["weighted_loss", "weighted_sampler", "none"])
    label_noise_filter: list[bool] = Field(default_factory=lambda: [True, False])
    duplicate_patient_policy: list[str] = Field(default_factory=lambda: ["keep_first", "merge", "exclude"])

class TilingConfig(BaseModel):
    magnification: list[str] = Field(default_factory=lambda: ["5x", "10x", "20x", "40x"])
    tile_size: list[int] = Field(default_factory=lambda: [224, 256, 384, 512])
    stride: list[str] = Field(default_factory=lambda: ["tile_size", "tile_size/2"])
    overlap: list[float] = Field(default_factory=lambda: [0.0, 0.25, 0.5])
    mpp: list[float] = Field(default_factory=lambda: [0.25, 0.50, 1.0])
    max_tiles_per_slide: list[int] = Field(default_factory=lambda: [500, 1000, 2000, 5000])
    min_tiles_per_slide: list[int] = Field(default_factory=lambda: [50, 100, 200])
    tissue_threshold: list[float] = Field(default_factory=lambda: [0.40, 0.50, 0.60, 0.70])
    background_threshold: list[float] = Field(default_factory=lambda: [0.70, 0.80, 0.90])
    blur_threshold: list[int] = Field(default_factory=lambda: [50, 100, 150])
    saturation_threshold: list[int] = Field(default_factory=lambda: [5, 10, 15])
    artifact_filter: list[bool] = Field(default_factory=lambda: [True, False])
    pen_mark_filter: list[bool] = Field(default_factory=lambda: [True, False])
    save_tiles: bool = False
    save_tile_index: bool = True

class FeatureExtractionConfig(BaseModel):
    encoder_name: list[str] = Field(default_factory=lambda: ["UNI", "Virchow", "CTransPath", "PLIP", "H-optimus", "CONCH"])
    input_size: list[int] = Field(default_factory=lambda: [224, 256, 384])
    batch_size: list[int] = Field(default_factory=lambda: [16, 32, 64])
    normalize_features: list[bool] = Field(default_factory=lambda: [True, False])
    feature_dtype: list[str] = Field(default_factory=lambda: ["float16", "float32"])
    feature_pooling_before_mil: list[str] = Field(default_factory=lambda: ["none", "mean", "topk"])
    cache_features: bool = True
    freeze_encoder: bool = True
    fine_tune_last_layers: bool = False
    num_workers: list[int] = Field(default_factory=lambda: [2, 4, 6])
    prefetch_factor: list[int] = Field(default_factory=lambda: [2, 4])

class BaggingConfig(BaseModel):
    bag_size: list[int] = Field(default_factory=lambda: [128, 256, 512, 1024, 2048])
    bag_sampling: list[str] = Field(default_factory=lambda: ["random", "topk_attention", "balanced_random", "uncertainty_topk"])
    bags_per_slide: list[int] = Field(default_factory=lambda: [1, 2, 4, 8])
    positive_tile_boost: list[bool] = Field(default_factory=lambda: [True, False])
    tile_dropout: list[float] = Field(default_factory=lambda: [0.0, 0.05, 0.10, 0.20])
    min_bag_size: list[int] = Field(default_factory=lambda: [64, 128, 256])
    replace_sampling: list[bool] = Field(default_factory=lambda: [True, False])
    hard_tile_mining: list[bool] = Field(default_factory=lambda: [False, True])
    attention_topk: list[int] = Field(default_factory=lambda: [64, 128, 256])
    multi_scale_bagging: list[bool] = Field(default_factory=lambda: [False, True])

class ModelConfig(BaseModel):
    mil_type: list[str] = Field(default_factory=lambda: ["attention_mil", "gated_attention_mil", "transformer_mil", "clam_sb", "clam_mb"])
    input_dim: list[int] = Field(default_factory=lambda: [768, 1024, 1280, 1536, 2560])
    hidden_dim: list[int] = Field(default_factory=lambda: [128, 256, 512, 768])
    attention_dim: list[int] = Field(default_factory=lambda: [128, 256, 512])
    num_attention_heads: list[int] = Field(default_factory=lambda: [1, 2, 4, 8])
    num_transformer_layers: list[int] = Field(default_factory=lambda: [1, 2, 4])
    mlp_layers: list[int] = Field(default_factory=lambda: [1, 2, 3])
    activation: list[str] = Field(default_factory=lambda: ["relu", "gelu", "silu"])
    dropout: list[float] = Field(default_factory=lambda: [0.0, 0.10, 0.20, 0.30, 0.50])
    attention_dropout: list[float] = Field(default_factory=lambda: [0.0, 0.10, 0.20])
    classifier_dropout: list[float] = Field(default_factory=lambda: [0.10, 0.20, 0.30])
    use_layernorm: list[bool] = Field(default_factory=lambda: [True, False])
    use_batchnorm: list[bool] = Field(default_factory=lambda: [True, False])
    pooling: list[str] = Field(default_factory=lambda: ["attention", "mean", "max", "mean_max", "topk_attention"])
    num_classes: int = 2
    label_smoothing: list[float] = Field(default_factory=lambda: [0.0, 0.05, 0.10])

class LossConfig(BaseModel):
    name: list[str] = Field(default_factory=lambda: ["cross_entropy", "weighted_cross_entropy", "focal_loss", "bce_with_logits"])
    class_weight_msi_h: list[float] = Field(default_factory=lambda: [1.0, 1.5, 2.0, 3.0, 5.0])
    class_weight_mss: float = 1.0
    focal_gamma: list[float] = Field(default_factory=lambda: [1.0, 2.0, 3.0])
    focal_alpha: list[float] = Field(default_factory=lambda: [0.25, 0.50, 0.75])
    label_smoothing: list[float] = Field(default_factory=lambda: [0.0, 0.05, 0.10])
    pos_weight: str = "class imbalance ratio"
    loss_reduction: str = "mean"

class OptimizerConfig(BaseModel):
    name: list[str] = Field(default_factory=lambda: ["adamw", "adam", "sgd", "lion"])
    learning_rate_min: float = 1e-5
    learning_rate_max: float = 3e-3
    weight_decay_min: float = 1e-6
    weight_decay_max: float = 1e-2
    gradient_clip_val: list[float] = Field(default_factory=lambda: [0.5, 1.0, 2.0, 5.0])

class SchedulerConfig(BaseModel):
    name: list[str] = Field(default_factory=lambda: ["cosine", "onecycle", "reduce_on_plateau", "none"])
    warmup_epochs: list[int] = Field(default_factory=lambda: [0, 1, 3, 5])
    min_lr: list[float] = Field(default_factory=lambda: [1e-7, 1e-6, 1e-5])
    patience: list[int] = Field(default_factory=lambda: [3, 5, 8])

class TrainerConfig(BaseModel):
    max_epochs: list[int] = Field(default_factory=lambda: [20, 30, 50, 80])
    batch_size: list[int] = Field(default_factory=lambda: [1, 2, 4, 8])
    accumulate_grad_batches: list[int] = Field(default_factory=lambda: [1, 2, 4, 8])
    precision: list[str] = Field(default_factory=lambda: ["16-mixed", "bf16-mixed", "32"])
    seed_choices: list[int] = Field(default_factory=lambda: [310, 42, 123, 2026, 777])
    early_stopping_patience: list[int] = Field(default_factory=lambda: [5, 8, 10])
    monitor_metric: list[str] = Field(default_factory=lambda: ["val_auroc", "val_auprc", "stable_score"])

class AugmentationConfig(BaseModel):
    horizontal_flip_p: float = 0.5
    vertical_flip_p: float = 0.5
    rotate_p: list[float] = Field(default_factory=lambda: [0.25, 0.50])
    color_jitter_p: list[float] = Field(default_factory=lambda: [0.25, 0.50])
    brightness: list[float] = Field(default_factory=lambda: [0.05, 0.10, 0.20])
    contrast: list[float] = Field(default_factory=lambda: [0.05, 0.10, 0.20])
    stain_augmentation: list[bool] = Field(default_factory=lambda: [False, True])

class ValidationConfig(BaseModel):
    threshold_method: list[str] = Field(default_factory=lambda: ["0.5", "youden_j", "max_f1", "fixed_sensitivity"])
    bootstrap_samples: list[int] = Field(default_factory=lambda: [500, 1000, 2000])
    confidence_level: float = 0.95
    calibration_method: list[str] = Field(default_factory=lambda: ["none", "temperature_scaling", "isotonic"])
    primary_metric: list[str] = Field(default_factory=lambda: ["AUROC", "AUPRC", "balanced_accuracy"])

class MonteCarloUncertaintyConfig(BaseModel):
    mc_dropout_enabled: bool = True
    mc_dropout_rate: list[float] = Field(default_factory=lambda: [0.10, 0.20, 0.30, 0.50])
    mc_samples: list[int] = Field(default_factory=lambda: [20, 30, 50, 100])
    seed_values: list[int] = Field(default_factory=lambda: [310, 42, 123, 2026, 777])
    bootstrap_ci_samples: list[int] = Field(default_factory=lambda: [500, 1000, 2000])
    stable_best_penalty: list[float] = Field(default_factory=lambda: [0.25, 0.5, 1.0])

class OptunaConfig(BaseModel):
    n_trials_phase_1: int = 20
    n_trials_phase_2: int = 50
    timeout_hours: int = 8
    pruning: bool = True
    pruner: str = "median"
    sampler: str = "tpe"

class N8nConfig(BaseModel):
    batch_size_svs: list[int] = Field(default_factory=lambda: [5, 10, 15])
    max_parallel_trials: list[int] = Field(default_factory=lambda: [1, 2])
    status_poll_interval_min: list[int] = Field(default_factory=lambda: [5, 10, 15])
    retry_count: list[int] = Field(default_factory=lambda: [2, 3])
    cleanup_after_success: bool = True
    cleanup_raw_svs: bool = True
    minimum_free_storage_gb: list[int] = Field(default_factory=lambda: [20, 25, 30])

# ---------------------------------------------------------------------------
# 2. Monte Carlo random search plan
# ---------------------------------------------------------------------------

class MonteCarloSearchRequest(BaseModel):
    """Random hyperparameter sampling with comprehensive config structure."""
    data: DataConfig = Field(default_factory=DataConfig)
    tiling: TilingConfig = Field(default_factory=TilingConfig)
    feature_extraction: FeatureExtractionConfig = Field(default_factory=FeatureExtractionConfig)
    bagging: BaggingConfig = Field(default_factory=BaggingConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    loss: LossConfig = Field(default_factory=LossConfig)
    optimizer: OptimizerConfig = Field(default_factory=OptimizerConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    trainer: TrainerConfig = Field(default_factory=TrainerConfig)
    augmentation: AugmentationConfig = Field(default_factory=AugmentationConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    monte_carlo: MonteCarloUncertaintyConfig = Field(default_factory=MonteCarloUncertaintyConfig)
    optuna: OptunaConfig = Field(default_factory=OptunaConfig)
    n8n: N8nConfig = Field(default_factory=N8nConfig)
    
    samples: int = Field(default=8, ge=1, le=100)
    random_seed: int = 310
    primary_metric: str = "stable_score"
    metric_direction: MetricDirection = "max"
    rank_formula: str = DEFAULT_STABLE_RANK_FORMULA


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
    bag_size: int
    bags_per_slide: int
    hidden_dim: int
    attention_dim: int
    class_weight_msi_h: float
    scheduler: str
    warmup_epochs: int
    loss_name: str
    primary_metric: str = "stable_score"
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
    rank_formula: str = DEFAULT_STABLE_RANK_FORMULA
    min_completed_folds: int = 1


class StableBestCandidate(BaseModel):
    """One candidate with stability score."""
    trial_id: str
    mean_auroc: float
    sd_auroc: float
    mean_auprc: float
    sd_auprc: float
    balanced_accuracy: float = 0.0
    msi_h_sensitivity: float = 0.0
    calibration_score: float = 0.0
    seed_std: float = 0.0
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
