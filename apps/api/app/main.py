from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cohort, vm
from app.core.config import get_settings

settings = get_settings()

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

