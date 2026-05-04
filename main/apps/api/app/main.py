from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import vm
from app.approach_2.api import pipeline as approach_2_pipeline
from app.approach_2.database.setup import Base as Approach2Base
from app.approach_2.database.setup import engine as approach_2_engine
from app.core.config import get_settings

settings = get_settings()
Approach2Base.metadata.create_all(bind=approach_2_engine)
ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "storage"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="4basecare MSI TCGA API",
    description="Lean backend for the single Next.js plus Python TCGA DX1 MSI training and visualization system.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "ok": "true",
        "service": "4basecare-msi-tcga-api",
        "environment": settings.environment,
    }


app.include_router(vm.router, prefix="/vm", tags=["vm"])
app.include_router(approach_2_pipeline.router, prefix="/approach-2/pipeline", tags=["approach-2-pipeline"])
app.mount("/approach-2/artifacts", StaticFiles(directory=str(ARTIFACT_DIR)), name="approach-2-artifacts")
