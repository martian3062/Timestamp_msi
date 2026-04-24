from fastapi import APIRouter, HTTPException

from app.models.data_batches import DataBatchActionResponse, GdcBatchStartRequest
from app.services.data_batches import DataBatchService

router = APIRouter()


@router.post("/gdc/bootstrap", response_model=DataBatchActionResponse)
def bootstrap() -> DataBatchActionResponse:
    result = DataBatchService().bootstrap()
    if not result.ok:
        raise HTTPException(status_code=500, detail=result.stderr or result.stdout)
    return result


@router.post("/gdc/start", response_model=DataBatchActionResponse)
def start(request: GdcBatchStartRequest) -> DataBatchActionResponse:
    result = DataBatchService().start(request)
    if not result.ok:
        raise HTTPException(status_code=500, detail=result.stderr or result.stdout)
    return result


@router.get("/gdc/status", response_model=DataBatchActionResponse)
def status() -> DataBatchActionResponse:
    return DataBatchService().status()


@router.post("/gdc/cleanup", response_model=DataBatchActionResponse)
def cleanup() -> DataBatchActionResponse:
    result = DataBatchService().cleanup()
    if not result.ok:
        raise HTTPException(status_code=500, detail=result.stderr or result.stdout)
    return result
