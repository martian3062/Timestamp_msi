from fastapi import APIRouter, HTTPException, Query

from app.models.experiments import (
    BestExperimentResponse,
    ExperimentActionResponse,
    ExperimentGridRequest,
    ExperimentPlanResponse,
    ExperimentRunRequest,
    ExperimentStatusResponse,
)
from app.services.experiments import ExperimentService

router = APIRouter()


@router.post("/plan", response_model=ExperimentPlanResponse)
def plan(request: ExperimentGridRequest) -> ExperimentPlanResponse:
    return ExperimentService().build_plan(request)


@router.post("/bootstrap", response_model=ExperimentActionResponse)
def bootstrap() -> ExperimentActionResponse:
    result = ExperimentService().bootstrap()
    if not result.ok:
        raise HTTPException(status_code=500, detail=result.stderr or result.stdout)
    return result


@router.post("/start", response_model=ExperimentActionResponse)
def start(request: ExperimentRunRequest) -> ExperimentActionResponse:
    result = ExperimentService().start_trial(request)
    if not result.ok:
        raise HTTPException(status_code=500, detail=result.stderr or result.stdout)
    return result


@router.get("/status/{trial_id}", response_model=ExperimentStatusResponse)
def status(trial_id: str) -> ExperimentStatusResponse:
    return ExperimentService().status(trial_id)


@router.get("/best", response_model=BestExperimentResponse)
def best(
    primary_metric: str = Query(default="mean_auroc"),
    metric_direction: str = Query(default="max", pattern="^(max|min)$"),
) -> BestExperimentResponse:
    return ExperimentService().best(primary_metric, metric_direction)
