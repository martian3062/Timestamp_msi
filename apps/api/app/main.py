import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import cohort, data_batches, experiments, integrations, monte_carlo, vm
from app.approach_2.api import (
    experiments as approach_2_experiments,
    pipeline as approach_2_pipeline,
    slides as approach_2_slides,
    webhook as approach_2_webhook,
)
from app.approach_2.database.setup import Base as Approach2Base
from app.approach_2.database.setup import engine as approach_2_engine
from app.core.config import get_settings

settings = get_settings()
Approach2Base.metadata.create_all(bind=approach_2_engine)
os.makedirs("/data", exist_ok=True)

app = FastAPI(
    title="Timestamp_msi API",
    description="Backend for TCGA CRC MSI cohort validation and VM orchestration.",
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
        "service": "timestamp-msi-api",
        "environment": settings.environment,
    }


app.include_router(cohort.router, prefix="/cohort", tags=["cohort"])
app.include_router(vm.router, prefix="/vm", tags=["vm"])
app.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
app.include_router(monte_carlo.router, prefix="/experiments", tags=["monte-carlo"])
app.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
app.include_router(data_batches.router, prefix="/data-batches", tags=["data-batches"])
app.include_router(approach_2_slides.router, prefix="/approach-2/slides", tags=["approach-2-slides"])
app.include_router(approach_2_pipeline.router, prefix="/approach-2/pipeline", tags=["approach-2-pipeline"])
app.include_router(approach_2_experiments.router, prefix="/approach-2/experiments", tags=["approach-2-experiments"])
app.include_router(approach_2_webhook.router, prefix="/approach-2/webhook", tags=["approach-2-webhook"])
app.mount("/approach-2/artifacts", StaticFiles(directory="/data"), name="approach-2-artifacts")
