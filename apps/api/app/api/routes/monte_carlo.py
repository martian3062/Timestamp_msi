"""Monte Carlo experiment API routes.

Endpoints:
  POST /experiments/monte-carlo-plan     — random hyperparameter search plan
  POST /experiments/mc-bootstrap         — deploy MC scripts to VM
  POST /experiments/uncertainty/start    — start MC dropout inference
  GET  /experiments/uncertainty/{id}     — get MC dropout results
  POST /experiments/bootstrap-ci/start   — start bootstrap CI
  GET  /experiments/bootstrap-ci/{id}    — get bootstrap CI results
  POST /experiments/seed-stability       — seed stability analysis
  GET  /experiments/best-stable          — stability-weighted ranking
"""
from fastapi import APIRouter, HTTPException

from app.models.monte_carlo import (
    BootstrapCIRequest,
    BootstrapCIResponse,
    MCDropoutRequest,
    MCDropoutResponse,
    MonteCarloActionResponse,
    MonteCarloSearchRequest,
    MonteCarloSearchResponse,
    SeedStabilityRequest,
    SeedStabilityResponse,
    StableBestRequest,
    StableBestResponse,
)
from app.services.monte_carlo import MonteCarloService

router = APIRouter()


@router.post("/monte-carlo-plan", response_model=MonteCarloSearchResponse)
def monte_carlo_plan(
    request: MonteCarloSearchRequest,
) -> MonteCarloSearchResponse:
    """Generate a random hyperparameter search plan (Monte Carlo sampling)."""
    return MonteCarloService().build_random_plan(request)


@router.post("/mc-bootstrap", response_model=MonteCarloActionResponse)
def mc_bootstrap() -> MonteCarloActionResponse:
    """Deploy MC dropout and bootstrap CI runner scripts to the VM."""
    result = MonteCarloService().bootstrap_runners()
    if not result.ok:
        raise HTTPException(status_code=500, detail=result.stderr or result.stdout)
    return result


@router.post("/uncertainty/start", response_model=MonteCarloActionResponse)
def start_uncertainty(request: MCDropoutRequest) -> MonteCarloActionResponse:
    """Start MC dropout uncertainty estimation on the VM."""
    result = MonteCarloService().start_mc_dropout(request)
    if not result.ok:
        raise HTTPException(status_code=500, detail=result.stderr or result.stdout)
    return result


@router.get("/uncertainty/{trial_id}", response_model=MCDropoutResponse)
def get_uncertainty(trial_id: str) -> MCDropoutResponse:
    """Read MC dropout uncertainty results for a trial."""
    return MonteCarloService().get_mc_dropout_results(trial_id)


@router.post("/bootstrap-ci/start", response_model=MonteCarloActionResponse)
def start_bootstrap_ci(request: BootstrapCIRequest) -> MonteCarloActionResponse:
    """Start bootstrap confidence interval computation on the VM."""
    result = MonteCarloService().start_bootstrap_ci(request)
    if not result.ok:
        raise HTTPException(status_code=500, detail=result.stderr or result.stdout)
    return result


@router.get("/bootstrap-ci/{trial_id}", response_model=BootstrapCIResponse)
def get_bootstrap_ci(trial_id: str) -> BootstrapCIResponse:
    """Read bootstrap CI results for a trial."""
    return MonteCarloService().get_bootstrap_ci_results(trial_id)


@router.post("/seed-stability", response_model=SeedStabilityResponse)
def seed_stability(request: SeedStabilityRequest) -> SeedStabilityResponse:
    """Analyse variance across trials trained with different seeds."""
    result = MonteCarloService().analyze_seed_stability(request)
    return result


@router.get("/best-stable", response_model=StableBestResponse)
def best_stable(
    rank_formula: str = "mean_auroc - 0.5 * sd_auroc",
    min_completed_folds: int = 1,
) -> StableBestResponse:
    """Find the best model using stability-weighted scoring."""
    return MonteCarloService().stable_best(
        StableBestRequest(
            rank_formula=rank_formula,
            min_completed_folds=min_completed_folds,
        )
    )
