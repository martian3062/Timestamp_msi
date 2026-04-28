from fastapi import APIRouter, HTTPException, Query

from app.models.vm import FileUploadRequest, VmActionResponse, VmFilesResponse
from app.services.vm import VmService

router = APIRouter()


@router.get("/status", response_model=VmActionResponse)
def status() -> VmActionResponse:
    return VmService().status()


@router.get("/files", response_model=VmFilesResponse)
def files(path: str | None = Query(default=None)) -> VmFilesResponse:
    try:
        return VmService().list_files(path)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/upload", response_model=VmActionResponse)
def upload(request: FileUploadRequest) -> VmActionResponse:
    return VmService().upload_file(request)


@router.post("/downloader/start", response_model=VmActionResponse)
def start_downloader() -> VmActionResponse:
    return VmService().start_downloader()


@router.post("/jupyter/start", response_model=VmActionResponse)
def start_jupyter() -> VmActionResponse:
    return VmService().start_jupyter()


@router.post("/tunnel/start", response_model=VmActionResponse)
def start_tunnel() -> VmActionResponse:
    return VmService().start_tunnel()


@router.post("/monte-carlo/workspace", response_model=VmActionResponse)
def prepare_monte_carlo_workspace() -> VmActionResponse:
    return VmService().prepare_monte_carlo_workspace()
