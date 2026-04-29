from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database.setup import engine, Base
from .api import slides, pipeline, experiments, webhook

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MSI Prediction Platform API",
    description="A platform for whole slide image processing and MSI prediction.",
    version="1.0.0"
)

# Allow Next.js frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, lock this down
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
import os

# Create artifacts dir if missing
os.makedirs("/data", exist_ok=True)

# Include routers
app.include_router(slides.router, prefix="/slides", tags=["Slides"])
app.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline"])
app.include_router(experiments.router, prefix="/experiments", tags=["Experiments"])
app.include_router(webhook.router, prefix="/webhook", tags=["Webhook"])

app.mount("/artifacts", StaticFiles(directory="/data"), name="artifacts")

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "MSI Prediction Platform Backend is running."}
